# Stove Switches

## Purpose

Specify Home Assistant switch entities and the existing stove power and error command mappings.

## Requirements

### Requirement: Switch inventory and identity

Every ready entry SHALL expose a state switch for reading `30001`. Full command mode (`mode: false`, the default) SHALL also expose an error switch for `30002`; legacy mode (`mode: true`) SHALL omit it. Switches SHALL use `<entry title> State` and `<entry title> Error` as names and `<entry title>_<reading ID>` as unique IDs. They SHALL use the same placeholder device metadata as sensors, and availability SHALL follow coordinator update success.

#### Scenario: Full and legacy entries expose different controls
- GIVEN a full-mode entry and a legacy-mode entry
- WHEN their switch platforms set up
- THEN both expose a state switch
- AND only the full-mode entry exposes an error switch

### Requirement: Reported switch state

The state switch SHALL be off when reading `30001` is absent or reports `0`, `7`, `8`, or `9`, and on otherwise. The error switch SHALL be off when reading `30002` is absent or equals zero and on otherwise. When available from the snapshot, the state switch SHALL expose `Num Val` and the mapped `Val text`, and the error switch SHALL expose `Num Val`. Failed attribute lookups SHALL return no attributes.

#### Scenario: Stove starts extinguishing while an error is present
- GIVEN state `7` and a nonzero error code
- WHEN switch states are evaluated
- THEN the state switch is off and the error switch is on
- AND the state switch exposes `7` and `Extinguishing`

### Requirement: Mode-dependent power and error commands

Switch and thermostat power commands and full-mode error clear SHALL use these frames:

| Action | Full mode | Legacy mode |
| --- | --- | --- |
| Power on | `["SEC","1","J30253000000000001"]` | `["SEC","1","0"]` |
| Power off | `["SEC","1","J30254000000000001"]` | `["SEC","1","1"]` |
| Clear error | `["SEC","1","J30255000000000001"]` | Not exposed |

#### Scenario: Legacy power off
- GIVEN a ready legacy-mode entry
- WHEN its state switch is turned off
- THEN the coordinator sends the legacy OFF frame and the switch requests a refresh
- AND the displayed state follows subsequent readings rather than the command itself

### Requirement: Switch actions and refresh

The state switch SHALL dispatch ON and OFF commands. Turning the error switch off SHALL request error clear; turning it on SHALL send no command. Each switch action SHALL request a refresh and write entity state afterward, in addition to any delayed command refresh. Switch state SHALL follow readings, not toggle optimistically.

#### Scenario: Full-mode error control
- GIVEN a ready full-mode entry with a nonzero error code
- WHEN its error switch is turned off
- THEN the coordinator requests an error clear and the switch requests a refresh
- WHEN its error switch is turned on
- THEN the switch requests a refresh without sending an error command
