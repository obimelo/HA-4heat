# Proposal

## Why

The stove device page mixes useful boiler controls with readings that are unsupported or have no known meaning.

## What Changes

- Limit the device to the requested stove and boiler readings; do not load the room thermostat.
- Rename the State and Error switches to Power ON/OFF and Clear Error without changing command-mode behavior.
- Show the Combustion Power selector and Boiler Target slider on the stove device by default, unless the controls have been explicitly disabled.
- Label the read-only fault sensor Error Message to distinguish it from the Clear Error switch.
- Hide the corresponding read-only sensors from the device page while the controls are enabled, without removing them from automations.

## Capabilities

### Modified Capabilities

- `integration-setup`: Forward only the supported entity platforms.
- `stove-telemetry`: Publish a fixed sensor list with at most one boiler-target sensor.
- `room-thermostat`: Remove the Home Assistant climate entity.
- `stove-switches`: Distinguish the Power ON/OFF switch from the State sensor.
- `boiler-controls`: Present the requested slider and power options on the stove device.

## Impact

Existing dashboards using removed entities may need updates. Automations selecting `Level 1` through `Level 5` must use `P1` through `P5`. Transport, stored setup settings, and write eligibility are unchanged.
