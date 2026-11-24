# Integration Setup Delta

## ADDED Requirements

### Requirement: Per-entry boiler compatibility option

Each configured stove SHALL offer an option to enable the tested boiler target and five-level combustion power profile. The option SHALL default to disabled, including on upgrade of existing entries. Changing the option SHALL reload only the affected entry, without requiring deletion, YAML changes, or new setup.

#### Scenario: Upgrade an existing entry
- GIVEN an entry was configured before the boiler option existed
- WHEN Home Assistant first starts the upgraded integration
- THEN the boiler controls are disabled
- AND existing entities and thermostat behavior continue unchanged

#### Scenario: Toggle the option on an existing stove
- GIVEN a configured stove with the option disabled and another stove on the same integration
- WHEN the user enables the option in the first stove's integration settings
- THEN only that entry reloads and its new controls become available when telemetry permits
- WHEN the user disables it
- THEN those controls are no longer provided for that entry

### Requirement: Unloading an entry

The integration SHALL unload an entry's forwarded platforms before discarding its coordinator and canceling its pending command refresh. Unloading one entry SHALL NOT break service routing or polling for other loaded entries.

#### Scenario: Reload with a confirmation refresh pending
- GIVEN two entries are loaded and the first has a scheduled command refresh
- WHEN the first entry is unloaded
- THEN the old coordinator does not run the scheduled refresh
- AND actions for the second entry still route to its own coordinator

## MODIFIED Requirements

### Requirement: Entry readiness and platform forwarding

For each entry the integration SHALL create and refresh its coordinator before forwarding entity setup. An unsuccessful first refresh SHALL raise `ConfigEntryNotReady`. On success it SHALL publish the coordinator, register `4heat.set_value`, and forward `sensor`, `switch`, and `climate`; it SHALL also forward `number` and `select` when the entry has enabled the boiler compatibility option.

#### Scenario: Initial runtime poll fails
- GIVEN a saved entry exists but the module cannot be reached at startup
- WHEN entry setup performs its initial refresh
- THEN it is reported as not ready
- AND the entry's platforms are not forwarded on that attempt

#### Scenario: Initial runtime poll succeeds
- GIVEN a saved entry and a module that responds to polling
- WHEN entry setup completes
- THEN Home Assistant sets up sensor, switch, and climate against the same coordinator
- AND it sets up number and select for that entry only when opted in
