# Boiler Controls Delta

## Purpose

Expose native Home Assistant controls for the water target and combustion power on stoves compatible with the tested five-level boiler controls.

## ADDED Requirements

### Requirement: Opt-in native controls

An opted-in 4Heat entry SHALL expose a Celsius number entity named Boiler water target and a select entity named Combustion power, with stable entry-scoped IDs. Entries that have not opted in SHALL expose neither entity. The new controls SHALL use descriptive states and errors without raw register IDs, codes, or markers.

#### Scenario: Enable controls on one of two configured stoves
- GIVEN two configured entries and the option is enabled only on the first
- WHEN Home Assistant sets up their platforms
- THEN only the first exposes the new number and select entities
- AND no parameter write is sent during setup

### Requirement: Boiler target limits

The boiler control SHALL accept whole-degree values in the inclusive range 60–80 °C, narrowed by any positive minimum or maximum limits reported in the latest exchange (`20205`/`20206`, `20005`/`20006`). It SHALL reject an out-of-range or fractional target rather than rounding or clamping it. If the constraints do not overlap, the control SHALL remain unavailable for writes.

#### Scenario: The stove reports a tighter range
- GIVEN the stove reports a writable water target and a maximum of 75 °C
- WHEN the user tries to set 76 °C
- THEN no write is sent
- WHEN the user sets 75 °C
- THEN the integration sends `["SEC","1","B20199000000000075"]`

#### Scenario: Reported limits conflict
- GIVEN the stove reports a minimum of 76 °C and a maximum of 75 °C
- WHEN a target write is requested
- THEN no write is sent

### Requirement: Boiler target while off

The boiler target writer SHALL require a fresh reading of `B20199`, or a fresh Off state (`30001 = 0`) if the target is omitted. A known non-`B` marker SHALL block the write. The value shown SHALL represent the last reported target, not the measured water temperature or an unconfirmed request. A target change SHALL send no ON or OFF command.

#### Scenario: First poll after startup confirms Off but omits the target
- GIVEN an opted-in entry whose latest poll reports Off without a target or explicit limits
- WHEN the user requests 70 °C
- THEN the integration sends only the boiler target command
- AND it leaves the target unset until the stove reports one

#### Scenario: A previous Off reading is not fresh
- GIVEN the current snapshot retains Off from an earlier reading
- WHEN the latest poll fails or omits both stove state and target
- THEN the boiler target control does not permit a write

### Requirement: Five-level combustion power

Combustion power SHALL offer Level 1 through Level 5 and Auto. Levels 1–5 SHALL write those numeric values; Auto SHALL write 6. The control SHALL require a fresh `B20364` reading to write. Reported values 6 and 7 SHALL both display as Auto; other unrecognized values SHALL not be shown as a selectable setting.

#### Scenario: Auto returns a different code with the same meaning
- GIVEN the stove reports a fresh writable power setting
- WHEN the user selects Auto
- THEN the integration sends `["SEC","1","B20364000000000006"]`
- AND a follow-up reading of 7 is displayed as Auto

#### Scenario: Missing or non-writable power reading
- GIVEN the latest poll does not contain a `B20364` reading
- WHEN a combustion power change is requested
- THEN no power-setting command is sent

### Requirement: Reported state and feedback

New controls and their corresponding guarded service writes SHALL use the latest actual bulk or fallback reply for write eligibility and SHALL NOT publish requested values optimistically. If a send times out or is rejected, Home Assistant SHALL report a user-facing error. The next readback SHALL reflect what the stove reports, even if it disagrees with the request.

#### Scenario: A setting is not applied despite a reply
- GIVEN the stove previously reported Level 2
- WHEN a Level 3 command receives a non-error reply but the follow-up poll still reports Level 2
- THEN the entity continues to display Level 2 without publishing Level 3 as confirmed

#### Scenario: First failed poll still serves cached data
- GIVEN the coordinator still exposes cached readings after a failed poll
- WHEN a new control write is attempted before another valid poll
- THEN those cached readings do not make the write eligible
