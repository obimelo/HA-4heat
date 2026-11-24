"""The 4Heat integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .boiler import combustion_power_option
from .const import (
    MODE_NAMES, ERROR_NAMES, POWER_NAMES,
    MODE_TYPE, ERROR_TYPE, POWER_TYPE,
    SENSOR_TYPES, DOMAIN, DATA_COORDINATOR,
    ATTR_MARKER, ATTR_NUM_VAL, ATTR_READING_ID, ATTR_STOVE_ID
)
from .coordinator import FourHeatDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Add an FourHeat entry."""
    coordinator: FourHeatDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    entities = []
    for token in entry.data.get(CONF_MONITORED_CONDITIONS, ()):
        if isinstance(token, str) and len(token) > 5:
            entities.append(FourHeatDevice(coordinator, token[1:6], entry.title))

    async_add_entities(entities)


class FourHeatDevice(CoordinatorEntity, SensorEntity):
    """Representation of a 4Heat device."""

    def __init__(self, coordinator, sensor_type, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor, self._attr_native_unit_of_measurement, self._attr_icon = (
            SENSOR_TYPES.get(sensor_type, (f"UN {sensor_type}", None, ""))
        )
        self._name = name
        self.type = sensor_type
        self.coordinator = coordinator
        self._last_value = None
        self.serial_number = coordinator.serial_number
        self.model = coordinator.model

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._sensor}"

    @property
    def native_value(self):
        """Return the measured value or decoded status."""
        data = self.coordinator.data or {}
        if self.type not in data:
            return None

        try:
            raw_value = data[self.type][0]

            # Controlla se il valore è None o non valido
            if raw_value is None:
                _LOGGER.warning(f"Valore nullo per il sensore {self.name}, non inviato.")
                return self._last_value  # Mantiene l'ultimo valore valido

            if isinstance(raw_value, (int, float)) and raw_value < 0:  # Aggiungi altri controlli se necessario
                _LOGGER.warning(f"Valore negativo per {self.name}: {raw_value}, non inviato.")
                return self._last_value

            # Mappa il valore grezzo nei nomi, se necessario
            if self.type == MODE_TYPE:
                state = MODE_NAMES.get(raw_value, "Unknown_Mode_Name: " + str(raw_value))
            elif self.type == ERROR_TYPE:
                state = ERROR_NAMES.get(raw_value, "Unknown_Error_Name: " + str(raw_value))
            elif self.type == POWER_TYPE:
                if self.coordinator.boiler_controls and combustion_power_option(raw_value) == "Auto":
                    state = "Auto"
                else:
                    state = POWER_NAMES.get(raw_value, "Unknown_Power_Name: " + str(raw_value))
            else:
                state = raw_value

            self._last_value = state  # Aggiorna solo se valido
            return state

        except Exception as ex:
            _LOGGER.error(f"Errore durante la lettura dello stato di {self.name}: {ex}")
            return self._last_value  # Evita di inviare dati errati



    @property
    def unique_id(self):
        """Keep the existing ID used by the entity registry."""
        return f"{self._name}_{self.type}"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self.serial_number)},
            "name": self._name,
            "manufacturer": "4Heat",
            "model": self.model,
        }

    @property
    def extra_state_attributes(self):
        """Keep the routing and diagnostic attributes used by existing actions."""
        reading = (self.coordinator.data or {}).get(self.type)
        if reading is None:
            return None
        attributes = {
            ATTR_MARKER: reading[1],
            ATTR_READING_ID: self.type,
            ATTR_STOVE_ID: self.coordinator.stove_id,
        }
        if self.type in (MODE_TYPE, ERROR_TYPE, POWER_TYPE):
            attributes[ATTR_NUM_VAL] = reading[0]
        return attributes
