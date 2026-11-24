""" Integration for 4heat"""
import voluptuous as vol
import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
)
import homeassistant.helpers.config_validation as cv

from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError


from .boiler import decimal_value
from .const import (
    ATTR_MARKER, ATTR_READING_ID, ATTR_STOVE_ID, BOILER_TARGET_ID, CONF_MODE,
    DATA_COORDINATOR, DOMAIN, POWER_TYPE,
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_BASE_PLATFORMS = ("sensor", "switch", "climate")
_BOILER_PLATFORMS = ("number", "select")

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_MODE, default=False): cv.boolean,
                vol.Optional(CONF_MONITORED_CONDITIONS): cv.ensure_list,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Platform setup, do nothing."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=dict(config[DOMAIN])
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Load the saved entities."""
    coordinator = FourHeatDataUpdateCoordinator(
        hass,
        config=entry.data,
        options=entry.options,
        id=entry.entry_id,
        config_entry=entry,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await coordinator.async_shutdown()
        raise

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }
    if not hass.services.has_service(DOMAIN, "set_value"):
        async def async_handle_set_value(call):
            await _async_handle_set_value(hass, call)

        hass.services.async_register(DOMAIN, "set_value", async_handle_set_value)

    await hass.config_entries.async_forward_entry_setups(entry, _platforms(coordinator))
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_handle_set_value(hass, call):
    """Route guarded writes before applying the legacy value conversion."""
    entity_id = call.data.get("entity_id", "")
    if not isinstance(entity_id, str) or not valid_entity_id(entity_id):
        _LOGGER.error('"%s" is no valid entity ID', entity_id)
        return

    state = hass.states.get(entity_id)
    if state is None:
        _LOGGER.error('"%s" is not valid to be set', entity_id)
        return
    attributes = state.attributes
    entry = hass.data[DOMAIN].get(attributes.get(ATTR_STOVE_ID))
    reading_id = attributes.get(ATTR_READING_ID)
    if entry is None or reading_id is None:
        _LOGGER.error('"%s" is not valid to be set', entity_id)
        return

    coordinator = entry[DATA_COORDINATOR]
    if coordinator.boiler_controls and reading_id in (BOILER_TARGET_ID, POWER_TYPE):
        if "value" not in call.data:
            raise ServiceValidationError("Provide a whole numeric value for this setting.")
        value = call.data["value"]
        # Home Assistant also considers decimal text such as "70.0" an entity ID.
        if isinstance(value, str) and decimal_value(value) is None and valid_entity_id(value):
            referenced = hass.states.get(value)
            if referenced is None:
                raise ServiceValidationError("The referenced entity does not have a numeric value.")
            value = referenced.state
        if reading_id == BOILER_TARGET_ID:
            await coordinator.async_set_boiler_target(value)
        else:
            await coordinator.async_set_combustion_power(value)
        return

    value = call.data.get("value", 5)
    if isinstance(value, str):
        if value.isnumeric():
            value = int(value)
        elif valid_entity_id(value):
            value = int(float(hass.states.get(value).state))
        else:
            value = 1

    marker = attributes.get(ATTR_MARKER)
    if marker == "B":
        await coordinator.async_set_value(reading_id, value)
    elif marker == "J" and reading_id == coordinator.setpoint_id:
        await coordinator.async_set_setpoint(value)
    else:
        _LOGGER.error('"%s" is not valid to be set', entity_id)


def _platforms(coordinator):
    """Return the platforms set up for this coordinator instance."""
    return _BASE_PLATFORMS + (_BOILER_PLATFORMS if coordinator.boiler_controls else ())


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply options to this stove only."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload platforms and retire pending work for this entry."""
    entries = hass.data[DOMAIN]
    coordinator = entries[entry.entry_id][DATA_COORDINATOR]
    if not await hass.config_entries.async_unload_platforms(entry, _platforms(coordinator)):
        return False

    await coordinator.async_shutdown()
    entries.pop(entry.entry_id)
    if not entries:
        hass.services.async_remove(DOMAIN, "set_value")
    return True
