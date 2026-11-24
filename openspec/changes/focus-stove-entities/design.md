# Design

## Context

The coordinator still needs the full module reply for write limits, freshness checks, and command verification. The setup and boiler-control deltas from earlier work are pending archival.

## Decisions

- Apply the sensor allowlist to the saved inventory, not to the poll. Prefer the working boiler target when both known target readings are present.
- Stop forwarding the climate platform, but retain internal protocol behavior and do not delete existing registry entries or automations.
- Keep the compatibility option and write guards. Enable the option when no choice is saved, but keep explicit opt-outs. Use native `number` slider mode and a `select` with the requested ordering. Match the existing stove device identity and entity IDs.

## Migration Plan

Review dashboards and automations for retired entities and option labels. Archive the prior compatibility and boiler-control changes before syncing or archiving this delta so their older platform and control descriptions cannot overwrite it.
