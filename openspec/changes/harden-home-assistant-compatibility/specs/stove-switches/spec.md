# Stove Switches Delta

## MODIFIED Requirements

### Requirement: Reported switch state

The state switch SHALL be off when reading `30001` is absent or reports `0`, `7`, `8`, or `9`, and on otherwise. The error switch SHALL be off when reading `30002` is absent or equals zero and on otherwise. When available from the snapshot, the state switch SHALL expose `Num Val` and the mapped `Val text`, using `Unknown` for an unmapped value. The error switch SHALL expose `Num Val` when its reading exists. Missing readings SHALL return no attributes.

#### Scenario: Stove starts extinguishing while an error is present
- GIVEN state `7` and a nonzero error code
- WHEN switch states are evaluated
- THEN the state switch is off and the error switch is on
- AND the state switch exposes `7` and `Extinguishing`

#### Scenario: Stove reports an unfamiliar state
- GIVEN the module reports a state code absent from the name table
- WHEN Home Assistant reads the state switch attributes
- THEN `Num Val` retains that code and `Val text` is `Unknown`
