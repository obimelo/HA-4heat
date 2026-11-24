## Why

Testing with the Windows 4Heat Controller identified a working boiler target and a five-level combustion power mapping for the tested stove. The current integration offers only generic writes for these settings, and enabling this mapping globally would change the meaning of power level 6 for other stoves.

## What Changes

- Add a per-stove option, off by default, that exposes Home Assistant controls for boiler water target and combustion power.
- Use a 60–80 °C boiler range, honor tighter limits reported by the stove, and allow changing the target while it is confirmed off without sending a power-on command.
- Offer Levels 1–5 and Auto; write Auto as 6 and read both 6 and 7 as Auto only for opted-in entries.
- Use the same compatibility checks for the affected `4heat.set_value` writes on opted-in entries, without changing writes for other stoves or registers.
- Document the protocol findings, including the model-specific zero room reading, without changing the existing thermostat or room sensor. Keep raw protocol details out of the new controls' user-facing states and messages.

## Capabilities

### New Capabilities

- `boiler-controls`: Optional native boiler water target and combustion power controls with guarded writes and readback.

### Modified Capabilities

- `integration-setup`: Add an opt-in setting for existing and new entries and specify platform reload and unload behavior.
- `stove-telemetry`: Decode the legacy power sensor consistently with the new controls only on opted-in entries.
- `parameter-write-service`: Apply the same validation and readback behavior to the two opted-in registers while preserving legacy behavior elsewhere.
- `module-communication`: Recognize explicit device rejections for the opted-in controls without changing success handling for legacy commands.

## Impact

The change affects config entry options and lifecycle, coordinator write handling, the existing power sensor, and two new Home Assistant platforms (`number` and `select`). No new third-party runtime dependencies or stove queries are required. Existing entries are unchanged until explicitly enabled. The Windows app is outside this change.
