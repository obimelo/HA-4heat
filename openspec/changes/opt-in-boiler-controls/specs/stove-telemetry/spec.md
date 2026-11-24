# Stove Telemetry Delta

## MODIFIED Requirements

### Requirement: Display value decoding and fallback

Sensors SHALL return raw integers except for state `30001`, error `30002`, and power setting `20364`, which SHALL use their lookup tables. Unmapped values SHALL use `Unknown_Mode_Name: `, `Unknown_Error_Name: `, or `Unknown_Power_Name: ` respectively, followed by the code. On opted-in boiler entries, the power sensor SHALL display both 6 and 7 as Auto; other entries SHALL preserve their existing mappings.

#### Scenario: A stove reports state, error, and power codes
- GIVEN readings `30001 = 5`, `30002 = 0`, and `20364 = 7`
- WHEN Home Assistant evaluates their sensor states
- THEN the values are `Run`, `No`, and `Auto` respectively

#### Scenario: Code six differs between profiles
- GIVEN two entries report `20364 = 6` and only one has opted in
- WHEN Home Assistant evaluates their Power Setting sensors
- THEN the opted-in entry shows `Auto`
- AND the other entry still shows `P6`
