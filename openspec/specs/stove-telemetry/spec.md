# Stove Telemetry

## Purpose

Specify which sensor entities are exposed and how the module's readings are presented in Home Assistant.

## Requirements

### Requirement: Sensor creation from saved tokens

At sensor platform setup, the integration SHALL derive a reading ID from characters two through six of each saved monitored-condition token longer than five characters and attempt to create a sensor for it. Shorter tokens SHALL NOT produce entities. Sensor creation SHALL use the saved entry data rather than creating additional entities when new keys appear in later polls.

#### Scenario: Saved conditions contain headers, known and unknown readings
- GIVEN saved conditions include a short header token, a token for `30006`, and a token for an unrecognized ID
- WHEN the sensor platform sets up
- THEN it skips the header and attempts to create both reading sensors
- AND the unrecognized ID is not excluded just because no label is known

### Requirement: Sensor name, units and identity

The integration SHALL name a sensor `<entry title> <reading label>` and use `<entry title>_<reading ID>` as its unique ID. Known IDs SHALL use the labels, units and icon metadata in `SENSOR_TYPES`; unknown IDs SHALL use `UN <reading ID>` with no unit and an empty icon. Sensor device information SHALL use the entry title, manufacturer `4Heat`, model `Basic`, and the identifier pair `("4heat", "1")`, where `1` is a placeholder serial rather than a discovered value.

#### Scenario: Room temperature and an unknown reading are exposed
- GIVEN an entry titled `Living room` with saved tokens for `30006` and an unrecognized ID
- WHEN the entities are created
- THEN `Living room Room temperature` uses Celsius and unique ID `Living room_30006`
- AND the unknown reading uses the `UN <reading ID>` label without a unit

#### Scenario: Other configured measurement units
- GIVEN tokens for exhaust temperature `30005`, water pressure `30020`, airstream `30026`, and exhaust depression `30033`
- WHEN the sensors are set up
- THEN the units are Celsius, mbar, m³/h, and Pa respectively

### Requirement: Display value decoding and fallback

Sensors SHALL return raw integers except for state `30001`, error `30002`, and power setting `20364`, which SHALL use their lookup tables. Unmapped values SHALL use `Unknown_Mode_Name: `, `Unknown_Error_Name: `, or `Unknown_Power_Name: ` respectively, followed by the code.

#### Scenario: A stove reports state, error, and power codes
- GIVEN readings `30001 = 5`, `30002 = 0`, and `20364 = 7`
- WHEN Home Assistant evaluates their sensor states
- THEN the values are `Run`, `No`, and `Auto` respectively

### Requirement: Missing or invalid sensor values

A missing reading ID SHALL yield no state. A present but null or negative value, or an exception while evaluating a present reading, SHALL fall back to the sensor's last valid display value, which is initially unset.

#### Scenario: Negative or missing room temperature
- GIVEN a room sensor last displayed `20`
- WHEN the coordinator supplies a present but negative value for that reading
- THEN the sensor continues to display `20`
- WHEN the reading ID is absent from the snapshot instead
- THEN the sensor returns no state

### Requirement: Reading attributes and availability

For a reading present in coordinator data, the sensor SHALL expose `marker`, `reading_id`, and `stove_id` (the config entry ID). The state, error, and power sensors SHALL additionally expose their raw code as `num_val`. If the attribute lookup fails, the sensor SHALL return no attributes. Availability SHALL follow coordinator update success.

#### Scenario: A reported room setpoint can be addressed by the service
- GIVEN the snapshot stores `30138` as `[20, "J"]` for a configured stove
- WHEN Home Assistant reads that sensor's attributes
- THEN `marker` is `J`, `reading_id` is `30138`, and `stove_id` identifies that entry
- AND `num_val` is not added for that sensor
