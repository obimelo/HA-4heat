## Why

The setup flow can accept a module that provides no usable readings or let a socket failure escape instead of showing a setup error. [Upstream PR #29](https://github.com/zaubererty/homeassistant-4heat/pull/29) also identifies Home Assistant API and dependency updates that can be adopted without disrupting existing installations.

## What Changes

- Validate the setup reply, show a translated connection error, and use the normal Home Assistant startup retry path.
- Use standard-library timeouts and current Home Assistant entity APIs.
- Preserve the `4heat` domain, existing IDs, action routing, legacy/YAML setup, and current polling, thermostat, and boiler behavior.

## Capabilities

### Modified Capabilities

- `integration-setup`: Validate probe readings, accept short valid replies, and report setup failures in the form.
- `stove-switches`: Retain the switch's numeric diagnostic when a state name is unknown.

## Impact

Updates setup, transport, entity state publication, action metadata, and regression tests. No new runtime package or minimum Home Assistant version change is required.
