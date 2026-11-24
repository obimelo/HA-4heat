"""Boiler water target for opted-in 4Heat stoves."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .boiler import BOILER_TARGET_RANGE
from .const import BOILER_TARGET_ID, DATA_COORDINATOR, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the boiler water target for an opted-in entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    if coordinator.boiler_controls:
        async_add_entities([FourHeatBoilerTarget(coordinator, entry.title)])


class FourHeatBoilerTarget(CoordinatorEntity, NumberEntity):
    """A reported boiler water target and a guarded whole-degree setter."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1

    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self._attr_name = f"{name} Boiler Target"
        self._attr_unique_id = f"{coordinator.stove_id}_boiler_target"
        self._attr_device_info = coordinator.stove_device_info(name)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.boiler_target_range is not None

    @property
    def native_min_value(self) -> float:
        return (self.coordinator.boiler_target_range or BOILER_TARGET_RANGE)[0]

    @property
    def native_max_value(self) -> float:
        return (self.coordinator.boiler_target_range or BOILER_TARGET_RANGE)[1]

    @property
    def native_value(self) -> float | None:
        reading = (self.coordinator.data or {}).get(BOILER_TARGET_ID)
        return reading[0] if reading is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_boiler_target(value)
