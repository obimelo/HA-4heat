"""The 4Heat integration."""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import MODE_NAMES, DOMAIN, DATA_COORDINATOR, MODE_TYPE, ERROR_TYPE
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_SWITCH_LABELS = {MODE_TYPE: "Power ON/OFF", ERROR_TYPE: "Clear Error"}


async def async_setup_entry(hass, entry, async_add_entities):
    """Add an FourHeat entry."""
    coordinator: FourHeatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    entities = []

    for sensorId in coordinator.swiches:
        try:
            entities.append(FourHeatSwitch(coordinator, sensorId, entry.title))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error adding switch %s: %s", sensorId, err)

    async_add_entities(entities)


class FourHeatSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a 4Heat device."""

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._label = _SWITCH_LABELS[sensor_type]
        self._name = name
        self.type = sensor_type
        self.coordinator = coordinator
        self._last_value = None
        self.serial_number = coordinator.serial_number
        self.model = coordinator.model
        _LOGGER.debug(self.coordinator)

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{self._name} {self._label}"

    @property
    def is_on(self):
        """Return true if switch is on."""
        reading = (self.coordinator.data or {}).get(self.type)
        if reading is None:
            return False
        if self.type == MODE_TYPE:
            return reading[0] not in (0, 7, 8, 9)
        return self.type == ERROR_TYPE and reading[0] != 0

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if self.type == MODE_TYPE:
            await self.coordinator.async_turn_on()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        if self.type == MODE_TYPE:
            await self.coordinator.async_turn_off()
        elif self.type == ERROR_TYPE:
            await self.coordinator.async_unblock()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()


    @property
    def unique_id(self):
        """Keep the existing ID used by the entity registry."""
        return f"{self._name}_{self.type}"

    @property
    def device_info(self):
        """Return information about the device."""
        return self.coordinator.stove_device_info(self._name)

    @property
    def extra_state_attributes(self):
        """Publish the existing diagnostic attributes without assuming a known state."""
        reading = (self.coordinator.data or {}).get(self.type)
        if reading is None:
            return None
        value = reading[0]
        if self.type == MODE_TYPE:
            return {"Num Val": value, "Val text": MODE_NAMES.get(value, "Unknown")}
        if self.type == ERROR_TYPE:
            return {"Num Val": value}
        return None
