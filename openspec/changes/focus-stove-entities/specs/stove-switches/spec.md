# Stove Switches Delta

## MODIFIED Requirements

### Requirement: Switch inventory and identity

Every ready entry SHALL expose a Power ON/OFF switch for reading `30001`. Full command mode (`mode: false`, the default) SHALL also expose a Clear Error switch for `30002`; legacy mode SHALL omit it. Switch names SHALL use `<entry title> Power ON/OFF` and `<entry title> Clear Error`; unique IDs SHALL remain `<entry title>_<reading ID>`. The switches SHALL keep the shared stove device metadata and follow coordinator availability.

#### Scenario: Full and legacy entries expose different controls
- GIVEN a full-mode entry and a legacy-mode entry
- WHEN their switch platforms set up
- THEN both expose a Power ON/OFF switch
- AND only the full-mode entry exposes a Clear Error switch
- AND the separate State sensor retains its name

### Requirement: Switch actions and refresh

The power switch SHALL send its ON or OFF command. Turning Clear Error off SHALL request clearing the fault; turning it on SHALL only request a refresh. Switches SHALL show the requested state provisionally, then return to the reported state after verification. Read-only State and Error Message sensors SHALL remain driven by reported readings.

#### Scenario: Full-mode error control
- GIVEN the stove reports an active fault
- WHEN Clear Error is turned off
- THEN the switch shows Off provisionally
- AND a fresh error reading of zero confirms it without a notification
- WHEN Clear Error is turned on
- THEN the switch requests a refresh without sending an error command

#### Scenario: Power off begins shutdown
- GIVEN a successful power-off command
- WHEN a fresh state reading reports Extinguishing
- THEN the power-off request is confirmed without reporting that the stove is already Off
