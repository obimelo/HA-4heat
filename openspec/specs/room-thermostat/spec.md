# Room Thermostat

## Purpose

Specify the climate entity, temperature control, and the heuristic for retaining readings when the wireless room probe appears lost.

## Requirements

### Requirement: Thermostat creation, identity and availability

At climate platform setup, the integration SHALL create one thermostat per entry only if the initial snapshot contains reading ID `30138`. This check SHALL depend on the ID, not the reading's marker or the sensor selection. The thermostat SHALL be named `<entry title> thermostat` and use `<config entry ID>_climate` as its unique ID. It SHALL be available only while the coordinator reports update success and has nonempty data.

#### Scenario: Stove supports room setpoint
- GIVEN the initial snapshot contains `30138` and the saved sensor tokens omit it
- WHEN the climate platform sets up
- THEN it creates one thermostat for the entry

#### Scenario: Stove does not initially report room setpoint
- GIVEN the initial snapshot omits `30138`
- WHEN the climate platform sets up
- THEN no climate entity is created
- AND a later reading of that ID does not add an entity during polling

### Requirement: Climate modes and actions

The thermostat SHALL expose `off` and `heat`, plus target temperature and turn-on/turn-off controls. Reading `30001` SHALL determine the reported mode and action:

| Stove state code | HVAC mode | HVAC action |
| --- | --- | --- |
| Missing, `0`, `8`, `9` | `off` | `off` |
| `7`, `11` | `heat` | `idle` |
| Other values | `heat` | `heating` |

#### Scenario: Stove extinguishes
- GIVEN the stove reports state `7`
- WHEN Home Assistant reads the thermostat
- THEN it reports mode `heat` and action `idle`
- AND the separate state switch reports off

### Requirement: Climate power controls

Selecting `heat` or turning on SHALL send the configured ON command. Selecting `off` or turning off SHALL send the configured OFF command. Mode and action SHALL remain derived from stove readings rather than the requested mode.

#### Scenario: Home Assistant turns heating on with legacy mode enabled
- GIVEN a ready legacy-mode entry with a thermostat
- WHEN Home Assistant selects `heat`
- THEN it dispatches the legacy ON command
- AND the thermostat uses later stove readings to report mode and action

### Requirement: Temperature reporting and setpoint control

The thermostat SHALL report current temperature from `30006` and target temperature from `30138` in Celsius without scaling. An absent reading SHALL yield no temperature. The climate entity SHALL advertise 15–28 °C in 1 °C steps.

#### Scenario: Current room temperature is missing
- GIVEN the snapshot contains a target of 20 °C but no `30006`
- WHEN Home Assistant reads climate temperatures
- THEN the target is 20 °C and current temperature is unset

### Requirement: Setpoint control

The shared writer SHALL convert the requested temperature to a number, round it to a whole degree (ties to even), and clamp it to 5–30 °C. It SHALL write `J30138` in a `SEC` frame with a 12-character zero-padded integer field. The thermostat SHALL ignore a request with no temperature value.

#### Scenario: Set room target to 20 degrees
- GIVEN a thermostat that reports the room and setpoint readings
- WHEN Home Assistant requests 20 °C
- THEN the coordinator sends `["SEC","1","J30138000000000020"]`
- AND after a successful exchange the optimistic target becomes 20 °C pending readback

#### Scenario: Shared write bounds differ from the advertised range
- GIVEN a numeric request reaches the shared writer outside the advertised climate range
- WHEN the request is 33 °C
- THEN the writer sends 30 °C
- WHEN the request is 4.5 °C
- THEN it rounds and clamps the request to 5 °C

### Requirement: Room probe loss and recovery

On a successful poll the integration SHALL infer probe loss if the merged setpoint is outside 5–30 °C inclusive, or differs from the last trusted setpoint by at least 5 °C without matching the latest successful `J` write value. A matching write SHALL bypass only the jump check. No setpoint SHALL leave probe state unchanged.

#### Scenario: In-range setpoint jump from a Home Assistant write
- GIVEN a trusted setpoint of 20 °C and a successful Home Assistant write of 25 °C
- WHEN the next poll reports 25 °C
- THEN the five-degree jump is accepted and becomes trusted

#### Scenario: Unexplained in-range setpoint jump
- GIVEN a trusted setpoint of 20 °C and no matching Home Assistant write
- WHEN the next poll reports 25 °C
- THEN the five-degree jump is treated as probe loss

### Requirement: Preservation of trusted room readings

On entering probe loss, the integration SHALL save the detection time until recovery. While lost, it SHALL substitute trusted values for `30138` and `30006` where available without suppressing other readings. A setpoint that passes the probe checks SHALL clear the lost flag and timestamp and refresh trusted room readings from the available data.

#### Scenario: Internal probe fallback follows a valid poll
- GIVEN trusted target 20 °C and room temperature 21 °C
- WHEN the stove reports target 38 °C and room temperature 29 °C
- THEN the coordinator marks the probe lost and still publishes 20 °C and 21 °C
- AND subsequent polls that still fail the probe checks do not reset the first detection time
- WHEN a poll reports target 20 °C and room temperature 22 °C
- THEN the lost flag clears and the room temperature updates to 22 °C

#### Scenario: First reading is outside the trusted range
- GIVEN the coordinator has no trusted temperatures
- WHEN it receives its first setpoint at 38 °C
- THEN it marks the probe lost
- AND no trusted values are available to replace the reported temperatures

### Requirement: Thermostat diagnostics

The thermostat SHALL expose `stove_state` as a mapped state name or the raw code when unmapped; `setpoint_parameter` as `J30138`; `last_write` as the latest successful `J` write's `{id, value}` or null; `last_answer` as the most recent successful poll timestamp in ISO format or null; and `missed_polls` as the consecutive poll failure count. It SHALL expose `room_probe` as `lost since HH:MM` using local time while loss is flagged and dated, or `ok` otherwise.

#### Scenario: Probe loss is distinct from connectivity failure
- GIVEN a successful poll marks the probe lost at 14:05 local time
- WHEN Home Assistant reads diagnostic attributes
- THEN `room_probe` is `lost since 14:05`, `last_answer` records the successful poll, and `missed_polls` is zero
- AND the thermostat is still available if the snapshot is nonempty
