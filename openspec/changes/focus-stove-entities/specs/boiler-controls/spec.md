# Boiler Controls Delta

## MODIFIED Requirements

### Requirement: Opt-in native controls

An entry with boiler controls enabled SHALL expose a Celsius number slider named Boiler Target and a select entity named Combustion Power, on the same stove device as the sensors and switches. Both SHALL retain their existing entry-scoped IDs. Entries with the option disabled SHALL expose neither control. The controls SHALL use descriptive states and errors without raw register IDs, codes, or markers.

#### Scenario: Enable controls on one of two configured stoves
- GIVEN two configured entries and only one has the controls enabled
- WHEN Home Assistant sets up their platforms
- THEN only the enabled entry exposes the slider and selector
- AND no parameter write is sent during setup

### Requirement: Five-level combustion power

Combustion Power SHALL offer **Auto, P5, P4, P3, P2, P1** in that order. P1–P5 SHALL write values 1–5 respectively; Auto SHALL write 6. The control SHALL require a fresh `B20364` for writes. Reported 6 and 7 SHALL display as Auto; other unrecognized values SHALL not be shown as selectable settings.

#### Scenario: Auto returns a different code with the same meaning
- GIVEN the stove reports a fresh writable power setting
- WHEN the user selects Auto
- THEN the integration sends `["SEC","1","B20364000000000006"]`
- AND a follow-up reading of 7 displays as Auto

#### Scenario: Missing or non-writable power reading
- GIVEN the latest poll does not contain a `B20364` reading
- WHEN a power-setting change is requested
- THEN no power-setting command is sent

### Requirement: Reported state and feedback

Boiler and combustion controls SHALL show the requested value provisionally after validation without changing reported telemetry. A fresh readback SHALL replace the assumption; only a comparable fresh mismatch after the verification check SHALL send a failure notification. Missing or unusable readback SHALL clear the assumption without a mismatch notification. Existing eligibility rules SHALL still use fresh reported readings.

#### Scenario: A setting is not applied despite a reply
- GIVEN the reported option is P3 and the user requests Auto
- WHEN the command starts
- THEN the selector immediately shows Auto while the sensor still reports P3
- WHEN the verification poll still reports P3
- THEN the selector returns to P3 and the user is notified

#### Scenario: First failed poll still serves cached data
- GIVEN a poll fails and the coordinator retains cached data
- WHEN a new control write is attempted without a new valid poll
- THEN cached readings do not make the write eligible

#### Scenario: The stove omits the boiler target in its first reply
- GIVEN the reported target is 63 °C and the user requests 70 °C
- WHEN the scheduled verification poll does not include the target
- THEN the slider reverts to the last reported value without a failure notification
