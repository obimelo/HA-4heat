# Parameter Write Service

## Purpose

Specify how Home Assistant calls `4heat.set_value` and how it routes sensor-based writes and exposes their results.

## Requirements

### Requirement: Service arguments and value resolution

The integration SHALL provide `4heat.set_value` with `entity_id` and `value` fields. It SHALL default a missing value to `5`. It SHALL convert numeric strings using `int`, resolve a string recognized as a Home Assistant entity ID to the referenced entity's state with `int(float(state))`, and pass non-string inputs to the target writer. Other strings SHALL resolve to `1`. Conversion or lookup errors are not normalized by the service.

#### Scenario: Use a helper's state as a setpoint
- GIVEN a writable room-setpoint sensor and `input_number.room_target` whose state is `21.8`
- WHEN the service is called with that sensor as `entity_id` and the helper ID as `value`
- THEN the effective value is `21` before the shared setpoint handler runs

#### Scenario: Omitted service value
- GIVEN a writable `B` sensor
- WHEN the service is called without `value`
- THEN the service uses `5`

### Requirement: Target selection by sensor attributes

The service SHALL route writes by `stove_id`, `reading_id`, and `marker` on the target's state. `B` SHALL dispatch a generic parameter write; `J` SHALL dispatch the shared thermostat setpoint writer only for ID `30138`. Unsupported markers, other `J` IDs, and syntactically invalid entity IDs SHALL be logged and SHALL NOT send a command.

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

A generic write SHALL send `["SEC","1","B<reading ID><value>"]` with the value converted to an integer and zero-padded to 12 characters, without the thermostat's range clamp. A successful exchange SHALL optimistically replace the target value in coordinator data and publish the data if the reading already exists, retaining the stored marker. An unsuccessful send SHALL not apply the optimistic change.

#### Scenario: Generic write changes an existing parameter
- GIVEN the snapshot contains `20364` with marker `B`
- WHEN a service request for value `5` completes its exchange successfully
- THEN the frame sent was `["SEC","1","B20364000000000005"]`
- AND the coordinator publishes `[5, "B"]` for that reading before confirmation

### Requirement: Setpoint write feedback and confirmation

After a successful `J30138` exchange, the coordinator SHALL record the reading ID and effective whole-degree value as `last_write`. If coordinator data exists, it SHALL publish the optimistic setpoint with marker `J`. A failed exchange SHALL not change `last_write` or optimistically update the setpoint. Both generic and setpoint send attempts SHALL use the coordinator's delayed confirmation refresh; the service SHALL not return a device acknowledgment to the caller.

#### Scenario: Setpoint exchange fails
- GIVEN a current target of 20 °C with a previously recorded write
- WHEN the service requests 22 °C and the command socket raises an exception
- THEN the target and previous `last_write` are unchanged
- AND the coordinator still schedules the delayed refresh
