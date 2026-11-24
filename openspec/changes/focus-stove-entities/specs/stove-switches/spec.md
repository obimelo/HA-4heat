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
