"""Combustion power control for opted-in 4Heat stoves."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .boiler import COMBUSTION_POWER_VALUES, combustion_power_option
from .const import DATA_COORDINATOR, DOMAIN, POWER_TYPE


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the combustion power selector for an opted-in entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    if coordinator.boiler_controls:
        async_add_entities([FourHeatCombustionPower(coordinator, entry.title)])


class FourHeatCombustionPower(CoordinatorEntity, SelectEntity):
    """Present the stove's configured level, not its instantaneous power."""

    _attr_options = list(COMBUSTION_POWER_VALUES)

    def __init__(self, coordinator, name):
        super().__init__(coordinator)
        self._attr_name = f"{name} Combustion power"
        self._attr_unique_id = f"{coordinator.stove_id}_combustion_power"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.can_set_combustion_power

    @property
    def current_option(self) -> str | None:
        reading = (self.coordinator.data or {}).get(POWER_TYPE)
        return combustion_power_option(reading[0]) if reading is not None else None

    async def async_select_option(self, option: str) -> None:
        if option not in COMBUSTION_POWER_VALUES:
            raise ServiceValidationError("Choose combustion power level 1 through 5 or Auto.")
        await self.coordinator.async_set_combustion_power(COMBUSTION_POWER_VALUES[option])
