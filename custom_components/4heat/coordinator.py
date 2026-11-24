"""DataUpdateCoordinator for the 4heat Wi-Fi module.

Notes on the module (tested on a Fogo Montanha Square D pellet insert):
- the module's local server saturates easily: only one TCP exchange is made at a
  time (shared lock between polling and commands), polling runs every 120 s and
  backs off to 5 min after a failure;
- every socket call runs in the executor (no blocking I/O in the event loop);
- the room setpoint is reported as J30138 and can be written with the same frame
  shape as the ON/OFF commands: ["SEC","1","J30138000000000020"] -> 20 °C;
- when the stove loses its wireless room probe it falls back to its internal probe
  and reports wrong values (e.g. room 29 °C, setpoint 38 °C). This is detected on
  the setpoint (out of range, or a jump without a write from HA) and the last
  trusted setpoint / room values are kept until the probe is back.
"""
import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .boiler import (
    BOILER_MAXIMUM_IDS, BOILER_MINIMUM_IDS, BOILER_TARGET_RANGE,
    COMBUSTION_POWER_VALUES, combustion_power_option, whole_value,
)
from .const import (
    DOMAIN, SOCKET_TIMEOUT, DATA_QUERY, ERROR_QUERY,
    RESULT_ERROR, CONF_MODE, CONF_BOILER_CONTROLS, MODES, MODE_TYPE, ERROR_TYPE,
    SETPOINT_ID, ROOM_TEMP_ID, BOILER_TARGET_ID, POWER_TYPE,
)
from .transport import exchange, reply_tokens

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=120)
BACKOFF_INTERVAL = timedelta(minutes=5)
FAILURES_BEFORE_UNAVAILABLE = 3      # keep last data for a couple of missed polls
CONFIRM_DELAY = 25                   # s, re-read after a command
SETPOINT_RANGE = (5, 30)             # °C, outside = internal probe fallback
SETPOINT_JUMP = 5                    # °C, jump without a write = probe lost


class FourHeatDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching 4heat data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        config: dict,
        options: dict,
        id: str,
        config_entry: ConfigEntry | None = None,
    ):
        """Initialize global 4heat data updater."""
        self._host = config[CONF_HOST]
        self._mode = False
        self._lock = asyncio.Lock()
        self._confirm_unsub = None
        self._retired = False
        self.boiler_controls = options.get(CONF_BOILER_CONTROLS, False)
        self.swiches = [MODE_TYPE]
        self.stove_id = id

        if CONF_MODE in config:
            self._mode = config[CONF_MODE]

        if self._mode == False:
            self._on_cmd = MODES[0][0]
            self._off_cmd = MODES[0][1]
            self._unblock_cmd = MODES[0][2]
            self.swiches.append(ERROR_TYPE)
        else:
            self._on_cmd = MODES[1][0]
            self._off_cmd = MODES[1][1]
            self._unblock_cmd = MODES[1][2]

        self.model = "Basic"
        self.serial_number = "1"
        self.last_successful_data = None
        self._fresh_readings = {}
        self.failures = 0
        self.last_ok = None
        self.last_write = None
        self.setpoint_id = SETPOINT_ID
        self.probe_lost = False
        self.probe_lost_since = None
        self._trusted = {}

        super().__init__(
            hass, _LOGGER, config_entry=config_entry, name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )

    # ------------------------------------------------------------------ network
    def _exchange(self, payload: bytes) -> str:
        """One TCP request/response with the module (runs in the executor)."""
        return exchange(self._host, payload)

    async def _send(self, payload: bytes, label: str) -> bool:
        """Send a command, serialized with polling."""
        if payload is None:
            return False
        async with self._lock:
            if self._retired:
                return False
            return await self._send_locked(payload, label)

    async def _send_locked(self, payload: bytes, label: str, *, check_reply=False) -> bool:
        """Send a frame while the caller holds the exchange lock."""
        try:
            async with asyncio.timeout(SOCKET_TIMEOUT + 5):
                answer = await self.hass.async_add_executor_job(self._exchange, payload)
        except Exception as ex:  # noqa: BLE001
            _LOGGER.error("4heat: %s failed: %s", label, ex)
            return False

        _LOGGER.debug("4heat %s -> %s", label, answer)
        if check_reply and reply_tokens(answer)[0] in ("", RESULT_ERROR):
            _LOGGER.warning("4heat: %s received an empty or rejected reply", label)
            return False
        return True

    # ------------------------------------------------------------------ polling
    async def _async_update_data(self) -> dict:
        """Fetch data from 4heat."""

        def _read_current_reply() -> dict:
            items = reply_tokens(self._exchange(DATA_QUERY))
            if not items or items[0] == "":
                raise UpdateFailed("Empty answer from the 4heat module")
            if items[0] == RESULT_ERROR:
                items = reply_tokens(self._exchange(ERROR_QUERY))
            readings = {}
            for item in items:
                if len(item) > 3:
                    try:
                        readings[item[1:6]] = [int(item[7:]), item[0]]
                    except ValueError:
                        _LOGGER.debug("4heat: cannot parse %s", item)
            return readings

        if self._lock.locked():
            # A command is being sent: do not open a second connection.
            if self.last_successful_data is None:
                raise UpdateFailed("4heat exchange already in progress")
            return self.last_successful_data

        try:
            async with self._lock:
                async with asyncio.timeout(SOCKET_TIMEOUT + 5):
                    fresh_readings = await self.hass.async_add_executor_job(_read_current_reply)
                self._fresh_readings = fresh_readings
        except Exception as err:  # noqa: BLE001
            self._fresh_readings = {}
            self.update_interval = BACKOFF_INTERVAL
            self.failures += 1
            if self.last_successful_data is None or self.failures >= FAILURES_BEFORE_UNAVAILABLE:
                self.last_successful_data = None
                raise UpdateFailed(f"4heat module unreachable: {err}") from err
            _LOGGER.debug("4heat: poll failed (%s), keeping last data", err)
            return self.last_successful_data

        data = {**(self.data or {}), **fresh_readings}
        self._check_room_probe(data)
        self.last_successful_data = data
        self.failures = 0
        self.last_ok = dt_util.now()
        self.update_interval = POLL_INTERVAL
        return data

    def _check_room_probe(self, data: dict) -> None:
        """Detect the internal probe fallback and keep trusted values meanwhile."""
        sp = data.get(self.setpoint_id)
        if not sp:
            return
        trusted_sp = self._trusted.get(self.setpoint_id)
        written = self.last_write is not None and sp[0] == self.last_write.get("value")
        lost = not (SETPOINT_RANGE[0] <= sp[0] <= SETPOINT_RANGE[1]) or (
            trusted_sp is not None and not written and abs(sp[0] - trusted_sp[0]) >= SETPOINT_JUMP
        )
        if lost:
            if not self.probe_lost:
                self.probe_lost_since = dt_util.now()
                _LOGGER.warning(
                    "4heat: room probe lost (setpoint read %s, room %s), keeping last trusted values",
                    sp[0], (data.get(ROOM_TEMP_ID) or [None])[0],
                )
            self.probe_lost = True
            for key in (self.setpoint_id, ROOM_TEMP_ID):
                if key in self._trusted:
                    data[key] = list(self._trusted[key])
        else:
            if self.probe_lost:
                _LOGGER.info("4heat: room probe back")
            self.probe_lost = False
            self.probe_lost_since = None
            for key in (self.setpoint_id, ROOM_TEMP_ID):
                if key in data:
                    self._trusted[key] = list(data[key])

    def _schedule_confirm(self) -> None:
        """Re-read the stove a little after a command instead of immediately."""
        if self._retired:
            return
        if self._confirm_unsub:
            self._confirm_unsub()

        async def _later(_now):
            self._confirm_unsub = None
            await self.async_request_refresh()

        self._confirm_unsub = async_call_later(self.hass, CONFIRM_DELAY, _later)

    async def async_shutdown(self) -> None:
        """Cancel this stove's delayed command refresh before retiring it."""
        self._retired = True
        if self._confirm_unsub:
            self._confirm_unsub()
            self._confirm_unsub = None
        await super().async_shutdown()

    # ------------------------------------------------------------------ commands
    async def async_turn_on(self) -> bool:
        ok = await self._send(self._on_cmd, "ON")
        self._schedule_confirm()
        return ok

    async def async_turn_off(self) -> bool:
        ok = await self._send(self._off_cmd, "OFF")
        self._schedule_confirm()
        return ok

    async def async_unblock(self) -> bool:
        ok = await self._send(self._unblock_cmd, "UNBLOCK")
        self._schedule_confirm()
        return ok

    async def async_set_value(self, id, value) -> bool:
        payload = f'["SEC","1","B{id}{str(int(value)).zfill(12)}"]'.encode()
        ok = await self._send(payload, f"B{id}={value}")
        if ok and self.data is not None and id in self.data:
            self.data[id] = [int(value), self.data[id][1]]
            self.async_set_updated_data(self.data)
        self._schedule_confirm()
        return ok

    @property
    def boiler_target_range(self) -> tuple[int, int] | None:
        """Return the range only if a boiler target write is currently eligible."""
        if not self.boiler_controls or self._retired:
            return None
        target = self._fresh_readings.get(BOILER_TARGET_ID)
        if target is None:
            state = self._fresh_readings.get(MODE_TYPE)
            if state is None or state[0] != 0:
                return None
            target = (self.data or {}).get(BOILER_TARGET_ID)
        if target is not None and target[1] != "B":
            return None

        low, high = BOILER_TARGET_RANGE
        for reading_id in BOILER_MINIMUM_IDS:
            reading = self._fresh_readings.get(reading_id)
            if reading and reading[0] > 0:
                low = max(low, reading[0])
        for reading_id in BOILER_MAXIMUM_IDS:
            reading = self._fresh_readings.get(reading_id)
            if reading and reading[0] > 0:
                high = min(high, reading[0])
        return (low, high) if low <= high else None

    @property
    def can_set_combustion_power(self) -> bool:
        """Whether the latest exchange reported a writable power setting."""
        reading = self._fresh_readings.get(POWER_TYPE)
        return (
            self.boiler_controls and not self._retired
            and reading is not None and reading[1] == "B"
        )

    async def async_set_boiler_target(self, value) -> None:
        """Write a supported boiler target without changing the stove's power state."""
        await self._async_set_boiler_control(BOILER_TARGET_ID, value)

    async def async_set_combustion_power(self, value) -> None:
        """Write a supported power level; accept either numeric Auto code as input."""
        await self._async_set_boiler_control(POWER_TYPE, value)

    async def _async_set_boiler_control(self, reading_id: str, value) -> None:
        """Recheck the current reply under lock, then request eventual readback."""
        async with self._lock:
            if reading_id == BOILER_TARGET_ID:
                limits = self.boiler_target_range
                if limits is None:
                    raise ServiceValidationError("The boiler water target is not writable right now.")
                low, high = limits
                wire_value = whole_value(value, low, high)
                if wire_value is None:
                    raise ServiceValidationError(f"Enter a whole-degree boiler target from {low} to {high} °C.")
            else:
                if not self.can_set_combustion_power:
                    raise ServiceValidationError("Combustion power is not writable right now.")
                option = combustion_power_option(whole_value(value, 1, 7))
                if option is None:
                    raise ServiceValidationError("Choose combustion power level 1 through 5 or Auto.")
                wire_value = COMBUSTION_POWER_VALUES[option]

            setting = f"B{reading_id}{wire_value:012d}"
            ok = await self._send_locked(
                f'["SEC","1","{setting}"]'.encode(), setting, check_reply=True,
            )
            self._schedule_confirm()

        if not ok:
            raise HomeAssistantError("The stove did not accept or reply to the setting change.")

    async def async_set_j(self, id, value) -> bool:
        """Write a value reported with the 'J' marker (e.g. room setpoint J30138)."""
        value = int(value)
        payload = f'["SEC","1","J{id}{str(value).zfill(12)}"]'.encode()
        ok = await self._send(payload, f"J{id}={value}")
        if ok:
            self.last_write = {"id": id, "value": value}
            if self.data is not None:
                self.data[id] = [value, "J"]
                self.async_set_updated_data(self.data)
        self._schedule_confirm()
        return ok

    async def async_set_setpoint(self, value) -> bool:
        low, high = SETPOINT_RANGE
        return await self.async_set_j(self.setpoint_id, max(low, min(high, int(round(float(value))))))
