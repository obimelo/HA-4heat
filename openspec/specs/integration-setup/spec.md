# Integration Setup

## Purpose

Describe how users install and configure a local 4Heat stove and how Home Assistant starts its entities.

## Requirements

### Requirement: Home Assistant integration identity

The project SHALL provide a custom integration under `custom_components/4heat/`, with domain `4heat`, display name `4Heat Stove`, UI config flow enabled, and IoT class `local_polling`. It SHALL connect to the configured host directly without requiring a cloud account or credentials. Manual installation places the integration directory at `<config_dir>/custom_components/4heat/`. The HACS metadata SHALL identify the project as `4heat stove` and declare Home Assistant `2025.1` as its minimum.

#### Scenario: Integration is discovered after installation
- GIVEN the integration directory is installed in Home Assistant's custom components directory
- WHEN Home Assistant loads its integration metadata
- THEN it identifies the integration by domain `4heat` and offers its configuration flow
- AND the flow requests no account or authentication fields

### Requirement: User-configured entry

The UI flow SHALL accept a display name, host and legacy command mode, initially `Stove`, `192.168.0.0`, and `false`. For a new host it SHALL probe with `["SEL","0"]` over TCP port 80 off the event loop. If the check passes, it SHALL use the name as the entry title and save the host, mode and comma-separated reply tokens as monitored conditions, ignoring any submitted condition selection.

#### Scenario: Successful UI setup
- GIVEN `192.168.1.20` is not configured
- WHEN the user submits the name `Living room`, that host and legacy mode `false`, and the module returns a decoded probe reply
- THEN the entry is titled `Living room` and stores the host and mode
- AND its monitored conditions are taken from the probe response

### Requirement: Duplicate host prevention

The flow SHALL reject a host string already saved for domain `4heat`. Duplicate UI submissions SHALL show `host_exists` on the host field; duplicate YAML imports SHALL abort with `host_exists`. The comparison SHALL use the configured strings, not resolved network addresses or hardware identity.

#### Scenario: UI resubmits an existing host
- GIVEN an entry already uses `192.168.1.20`
- WHEN a different name is submitted for the same host
- THEN the UI reports `host_exists` without a new probe or entry

#### Scenario: YAML imports an existing host
- GIVEN an entry already uses `192.168.1.20`
- WHEN a YAML import is started for that host
- THEN the flow aborts with `host_exists`

### Requirement: YAML import

The integration SHALL accept a `4heat` YAML mapping with required `name` and `host`, optional boolean `mode` defaulting to `false`, and optional `monitored_conditions` accepted as a list. If the mapping is present, Home Assistant startup SHALL schedule a config-entry import that uses the user flow after duplicate checking. If the mapping is absent, startup SHALL not schedule an import.

#### Scenario: One-time YAML entry creation
- GIVEN YAML defines a named stove with a new host and no mode
- WHEN Home Assistant starts and the host probe passes
- THEN the import creates a config entry in full command mode
- AND the monitored conditions are recorded from the probe, just as in UI setup

### Requirement: Entry readiness and platform forwarding

For each entry the integration SHALL create a coordinator keyed by that config entry's ID and refresh it before forwarding entity setup. If the first refresh is unsuccessful, entry setup SHALL raise `ConfigEntryNotReady` so Home Assistant can retry. After a successful refresh the integration SHALL publish the coordinator for that entry, register `4heat.set_value`, and forward setup to `sensor`, `switch`, and `climate`.

#### Scenario: Initial runtime poll fails
- GIVEN a saved entry exists but the module cannot be reached at startup
- WHEN entry setup performs its initial refresh
- THEN it is reported as not ready
- AND the entry's platforms are not forwarded on that attempt

#### Scenario: Initial runtime poll succeeds
- GIVEN a saved entry and a module that responds to polling
- WHEN entry setup completes
- THEN Home Assistant can set up all three platforms against the same coordinator for that entry
