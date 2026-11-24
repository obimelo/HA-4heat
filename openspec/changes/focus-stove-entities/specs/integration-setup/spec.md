# Integration Setup Delta

## MODIFIED Requirements

### Requirement: Entry readiness and platform forwarding

For each entry the integration SHALL create and refresh its coordinator before forwarding entity setup. An unsuccessful first refresh SHALL raise `ConfigEntryNotReady`. On success it SHALL publish the coordinator, register `4heat.set_value`, and forward `sensor` and `switch`. It SHALL forward `number` and `select` only when the boiler compatibility option is enabled. It SHALL NOT forward `climate`.

#### Scenario: Initial runtime poll fails
- GIVEN a saved entry exists but the module cannot be reached at startup
- WHEN entry setup performs its initial refresh
- THEN it is reported as not ready and no platform is forwarded

#### Scenario: Initial runtime poll succeeds
- GIVEN a saved entry and a module that responds to polling
- WHEN entry setup completes
- THEN Home Assistant sets up sensor and switch against the same coordinator
- AND it sets up number and select for that entry unless the boiler option is disabled
- AND it does not start the climate platform

### Requirement: Per-entry boiler compatibility option

Each configured stove SHALL offer an option to enable the tested boiler target and five-level combustion power profile. The option SHALL default to enabled when no choice is saved, including on upgrades, and SHALL honor an explicit saved choice. Changing the option SHALL reload only the affected entry.

#### Scenario: Upgrade an existing entry
- GIVEN an existing entry with no saved boiler option
- WHEN Home Assistant starts the upgraded integration
- THEN the boiler controls are enabled and the supported sensors and switches retain their IDs

#### Scenario: An explicit opt-out survives an upgrade
- GIVEN an existing entry with the boiler option saved as disabled
- WHEN Home Assistant starts the upgraded integration
- THEN the boiler controls stay disabled

#### Scenario: Toggle the option on an existing stove
- GIVEN a configured stove with the option disabled and another stove on the same integration
- WHEN the user enables the option in the first stove's integration settings
- THEN only that entry reloads and its controls become available when telemetry permits
- WHEN the user disables it
- THEN those controls are no longer provided for that entry
