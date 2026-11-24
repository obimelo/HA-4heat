"""Exercise entry setup, reload and unload without a real appliance."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_MONITORED_CONDITIONS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
import pytest

integration = import_module("custom_components.4heat")
const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
sensor = import_module("custom_components.4heat.sensor")


def _entry(entry_id, *, enabled=None):
    return SimpleNamespace(
        entry_id=entry_id,
        domain=const.DOMAIN,
        title=entry_id,
        state=ConfigEntryState.SETUP_IN_PROGRESS,
        data={CONF_HOST: entry_id, CONF_MONITORED_CONDITIONS: []},
        options={} if enabled is None else {const.CONF_BOILER_CONTROLS: enabled},
        async_on_unload=Mock(),
        add_update_listener=Mock(side_effect=lambda callback: callback),
    )


@pytest.mark.asyncio
async def test_initial_refresh_failure_leaves_entry_for_home_assistant_to_retry(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = SimpleNamespace(async_forward_entry_setups=AsyncMock())
    entry = _entry("unreachable")
    await integration.async_setup(hass, {})
    with patch.object(coordinator_module.FourHeatDataUpdateCoordinator, "_exchange",
                      side_effect=TimeoutError("simulated timeout")):
        with pytest.raises(ConfigEntryNotReady):
            await integration.async_setup_entry(hass, entry)
    assert entry.entry_id not in hass.data[const.DOMAIN]
    hass.config_entries.async_forward_entry_setups.assert_not_awaited()
    assert not hass.services.has_service(const.DOMAIN, "set_value")


@pytest.mark.asyncio
async def test_reload_and_unload_are_entry_scoped(tmp_path):
    """Unload the original platforms and cancel just that stove's timer."""
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(),
        async_reload=AsyncMock(),
        async_unload_platforms=AsyncMock(return_value=True),
    )
    old_entry = _entry("default-controls")
    other_entry = _entry("disabled-controls", enabled=False)
    await integration.async_setup(hass, {})

    with patch.object(coordinator_module.FourHeatDataUpdateCoordinator, "_exchange",
                      return_value='["SEC","1","B20364000000000003"]') as exchange:
        assert await integration.async_setup_entry(hass, old_entry)
        assert await integration.async_setup_entry(hass, other_entry)
    assert [call.args for call in exchange.call_args_list] == [(const.DATA_QUERY,)] * 2

    forwarded = hass.config_entries.async_forward_entry_setups.await_args_list
    assert tuple(forwarded[0].args[1]) == ("sensor", "switch", "number", "select")
    assert tuple(forwarded[1].args[1]) == ("sensor", "switch")
    entries = hass.data[const.DOMAIN]
    old = entries[old_entry.entry_id][const.DATA_COORDINATOR]
    other = entries[other_entry.entry_id][const.DATA_COORDINATOR]
    with patch.object(coordinator_module, "async_call_later", return_value=Mock()) as schedule:
        old._schedule_confirm()
        cancel_confirmation = schedule.return_value

    old_entry.options = {const.CONF_BOILER_CONTROLS: False}
    update = old_entry.add_update_listener.call_args.args[0]
    await update(hass, old_entry)
    hass.config_entries.async_reload.assert_awaited_once_with(old_entry.entry_id)
    assert await integration.async_unload_entry(hass, old_entry)
    assert "number" in hass.config_entries.async_unload_platforms.await_args.args[1]
    cancel_confirmation.assert_called_once_with()
    assert old._confirm_unsub is None

    hass.states.async_set("sensor.other_power", "P3", {
        const.ATTR_STOVE_ID: other_entry.entry_id,
        const.ATTR_READING_ID: const.POWER_TYPE,
        const.ATTR_MARKER: "B",
    })
    with patch.object(other, "async_set_value", new_callable=AsyncMock) as send:
        await hass.services.async_call(
            const.DOMAIN, "set_value", {"entity_id": "sensor.other_power", "value": 5},
            blocking=True,
        )
        send.assert_awaited_once_with(const.POWER_TYPE, 5)

    assert await integration.async_unload_entry(hass, other_entry)
    assert not hass.services.has_service(const.DOMAIN, "set_value")


@pytest.mark.asyncio
async def test_guarded_service_and_legacy_routes_coexist(tmp_path):
    """The option affects only the two selected writes and power display."""
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(),
        async_unload_platforms=AsyncMock(return_value=True),
    )
    opted_in = _entry("opt-in", enabled=True)
    legacy = _entry("legacy", enabled=False)
    frame_log = []

    def exchange(coordinator, payload):
        frame_log.append((coordinator.stove_id, payload))
        if payload == const.DATA_QUERY:
            return '["SEC","4","B20364000000000006","B20199000000000070","B20206000000000075","J30138000000000020"]'
        return '["SEC","0"]'

    await integration.async_setup(hass, {})
    with patch.object(coordinator_module.FourHeatDataUpdateCoordinator, "_exchange", exchange):
        assert await integration.async_setup_entry(hass, opted_in)
        assert await integration.async_setup_entry(hass, legacy)
        entries = hass.data[const.DOMAIN]
        profile = entries[opted_in.entry_id][const.DATA_COORDINATOR]
        other = entries[legacy.entry_id][const.DATA_COORDINATOR]
        assert sensor.FourHeatDevice(profile, const.POWER_TYPE, "Opted-in stove").state == "Auto"
        assert sensor.FourHeatDevice(other, const.POWER_TYPE, "Other stove").state == "P6"

        for entity_id, entry, reading_id, marker in [
            ("sensor.profile_target", opted_in, const.BOILER_TARGET_ID, "B"),
            ("sensor.profile_power", opted_in, const.POWER_TYPE, "B"),
            ("sensor.legacy_power", legacy, const.POWER_TYPE, "B"),
            ("sensor.room_target", opted_in, const.SETPOINT_ID, "J"),
        ]:
            hass.states.async_set(entity_id, "20", {
                const.ATTR_STOVE_ID: entry.entry_id,
                const.ATTR_READING_ID: reading_id,
                const.ATTR_MARKER: marker,
            })
        hass.states.async_set("input_number.water", "72.0")
        hass.states.async_set("input_number.fractional", "72.5")
        hass.states.async_set("input_number.room", "21.8")

        async def set_value(entity_id, **values):
            await hass.services.async_call(
                const.DOMAIN, "set_value", {"entity_id": entity_id, **values}, blocking=True,
            )

        try:
            for values in ({}, {"value": "Auto"}, {"value": 4.5}):
                with pytest.raises(ServiceValidationError):
                    await set_value("sensor.profile_power", **values)
            for value in (76, "70.5", "input_number.fractional", "input_number.missing"):
                with pytest.raises(ServiceValidationError):
                    await set_value("sensor.profile_target", value=value)
            assert len(frame_log) == 2

            await set_value("sensor.profile_power", value="7.0")
            await set_value("sensor.profile_target", value="71.0")
            await set_value("sensor.profile_target", value="input_number.water")
            assert profile.data[const.BOILER_TARGET_ID] == [70, "B"]
            await set_value("sensor.legacy_power")
            assert other.data[const.POWER_TYPE] == [5, "B"]
            await set_value("sensor.room_target", value="input_number.room")
            assert profile.data[const.SETPOINT_ID] == [21, "J"]

            assert frame_log == [
                (opted_in.entry_id, const.DATA_QUERY),
                (legacy.entry_id, const.DATA_QUERY),
                (opted_in.entry_id, b'["SEC","1","B20364000000000006"]'),
                (opted_in.entry_id, b'["SEC","1","B20199000000000071"]'),
                (opted_in.entry_id, b'["SEC","1","B20199000000000072"]'),
                (legacy.entry_id, b'["SEC","1","B20364000000000005"]'),
                (opted_in.entry_id, b'["SEC","1","J30138000000000021"]'),
            ]
        finally:
            await integration.async_unload_entry(hass, opted_in)
            await integration.async_unload_entry(hass, legacy)
