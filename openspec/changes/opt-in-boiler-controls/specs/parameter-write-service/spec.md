# Parameter Write Service Delta

## MODIFIED Requirements

### Requirement: Service arguments and value resolution

`4heat.set_value` SHALL provide `entity_id` and `value`. For generic writes it SHALL default a missing value to `5`, convert numeric strings with `int`, resolve entity IDs with `int(float(state))`, pass non-string values through, and use `1` for other strings. Generic lookup and conversion errors are not normalized. Guarded boiler and power writes SHALL require an explicit value and SHALL NOT use a fallback or truncate fractional values.

#### Scenario: Use a helper's state as a setpoint
- GIVEN a writable room-setpoint sensor and `input_number.room_target` whose state is `21.8`
- WHEN the service is called with that sensor as `entity_id` and the helper ID as `value`
- THEN the effective value is `21` before the shared setpoint handler runs

#### Scenario: Omitted service value
- GIVEN a writable generic `B` sensor
- WHEN the service is called without `value`
- THEN the service uses `5`

#### Scenario: Omitted value for a guarded write
- GIVEN an opted-in power setting sensor
- WHEN the service is called without `value`
- THEN the service reports a validation error and sends no frame

### Requirement: Target selection by sensor attributes

The service SHALL route writes using the target state's `stove_id`, `reading_id`, and `marker`. Barring the opted-in guarded routes, `B` SHALL dispatch a generic write and `J` SHALL dispatch a thermostat write only for `30138`. Unsupported markers, other `J` IDs, and invalid target IDs SHALL be logged without sending a command.

#### Scenario: Service writes to the targeted stove
- GIVEN there are two configured stoves and the target sensor carries the second stove's entry ID, marker `J`, and reading ID `30138`
- WHEN the service is called with value `20`
- THEN only the second stove's coordinator sends the room setpoint write

#### Scenario: Service targets an unsupported register
- GIVEN a sensor with marker `J` for an ID other than `30138`
- WHEN the service is called for that sensor
- THEN the service logs that the entity cannot be set
- AND it sends no frame

### Requirement: Generic parameter write encoding

A generic write SHALL send `["SEC","1","B<reading ID><value>"]` with the value converted to an integer and zero-padded to 12 characters, without the thermostat's range clamp. On success, it SHALL optimistically publish the new value for an existing reading and retain its marker. On failure it SHALL NOT update the value. Opted-in boiler and power writes SHALL use their guarded behavior instead.

#### Scenario: Generic write changes an existing parameter
- GIVEN an entry that has not opted in and a snapshot containing `20364` with marker `B`
- WHEN a service request for value `5` completes its exchange successfully
- THEN the frame sent was `["SEC","1","B20364000000000005"]`
- AND the coordinator publishes `[5, "B"]` for that reading before confirmation

## ADDED Requirements

### Requirement: Guarded service routes

For opted-in entries, service writes targeting `20199` and `20364` SHALL share the native controls' validation, eligibility, and readback. Accept explicit whole numeric values, including numeric text or a referenced numeric entity state. Power values 6 and 7 SHALL both request Auto and send 6. Invalid values SHALL raise a user-facing error without a write.

#### Scenario: Preserve an existing automation's Auto value
- GIVEN an opted-in stove reporting a writable power setting
- WHEN a service call supplies numeric value `7` for the power setting sensor
- THEN the integration sends Auto using wire value `6`
- AND it waits for the stove's reported setting before changing state

#### Scenario: Do not bypass native boiler limits
- GIVEN an opted-in stove whose reported boiler maximum is 75 °C
- WHEN a service call supplies `76` or `70.5` for the boiler target
- THEN it reports a validation error and sends no frame
