# Stove Telemetry Delta

## MODIFIED Requirements

### Requirement: Sensor creation from saved tokens

The integration SHALL derive reading IDs from the saved monitored conditions and add only State, Error Message, Exhaust temperature, Combustion Power, Boiler water, Water pressure, and Boiler target when reported. It SHALL add each at most once, using `20199` for Boiler target when present and `20180` otherwise. New poll keys SHALL NOT dynamically add sensors.

#### Scenario: Saved conditions contain headers, known and unknown readings
- GIVEN an inventory containing the seven supported readings as well as headers, room, pump, and unknown readings
- WHEN the sensor platform sets up
- THEN only the seven supported sensors are created

#### Scenario: Both boiler target registers are reported
- WHEN the inventory contains both `20199` and `20180`
- THEN the only Boiler target sensor uses `20199`

## REMOVED Requirements

### Requirement: Sensor name, units and identity
**Reason**: The identity requirement assumed all readings were exposed.
**Migration**: Use supported sensor entities; their names and unique IDs are unchanged.

### Requirement: Missing or invalid sensor values
**Reason**: The room temperature sensor used by this scenario is no longer exposed.
**Migration**: The same handling applies to supported sensor values.

### Requirement: Reading attributes and availability
**Reason**: The room setpoint sensor used by this scenario is no longer exposed.
**Migration**: Use the supported Boiler target sensor for water target attributes.

## ADDED Requirements

### Requirement: Avoid duplicate setting displays

An entry with boiler controls enabled SHALL hide the read-only Combustion Power and Boiler target sensors from the device page without disabling or removing them. The integration SHALL undo its own hides when the option is turned off and SHALL preserve sensors hidden by the user.

#### Scenario: Enable the controls on an existing entry
- GIVEN an entry already has visible combustion power and boiler target sensors
- WHEN the entry reloads with the boiler controls enabled
- THEN the native selector and slider replace the read-only displays on the device page
- AND the existing sensor IDs remain usable by automations

#### Scenario: Disable the controls again
- WHEN the entry reloads with the boiler controls disabled
- THEN sensors hidden by the integration become visible again
- AND sensors hidden by the user remain hidden

### Requirement: Supported sensor name, units and identity

The integration SHALL name supported sensors `<entry title> <reading label>` and use `<entry title>_<reading ID>` as their unique ID. It SHALL preserve their configured units and the existing stove device identity.

#### Scenario: Supported measurements retain their units and identity
- GIVEN an entry named `Salamandra` reports `30005`, `30017`, and `30020`
- WHEN the sensors are set up
- THEN exhaust temperature and boiler water are reported in Celsius and water pressure in mbar
- AND the boiler water sensor keeps unique ID `Salamandra_30017`

### Requirement: Missing or invalid supported sensor values

A missing reading ID SHALL yield no state. A present but null or negative value, or an error while evaluating a present reading, SHALL fall back to the sensor's last valid value, initially unset.

#### Scenario: Negative or missing boiler temperature
- GIVEN the boiler water sensor last displayed `19`
- WHEN a negative boiler water value is present
- THEN it continues to display `19`
- WHEN the reading ID is absent instead
- THEN the sensor returns no state

### Requirement: Supported reading attributes and availability

For a reading present in coordinator data, the sensor SHALL expose `marker`, `reading_id`, and `stove_id` (the config entry ID). The state, error, and power sensors SHALL additionally expose the raw code as `num_val`. If the attribute lookup fails, the sensor SHALL return no attributes. Availability SHALL follow coordinator update success.

#### Scenario: A reported boiler target can be addressed by the service
- GIVEN the snapshot contains a reading for `20199`
- WHEN Home Assistant reads the Boiler target sensor's attributes
- THEN they identify the marker, reading, and entry without `num_val`
