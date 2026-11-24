# Tasks

## 1. Per-entry compatibility option

- [x] 1.1 Add a disabled-by-default option for configured entries and its translations; verify upgrading an existing entry does not enable it and an options update preserves unrelated settings.
- [x] 1.2 Wire conditional platform setup and normal entry reload/unload; verify with two entries that only the changed entry reloads, the old confirmation timer is canceled, and the other entry's service routing still works. Document how to enable and disable the option.

## 2. Guarded controls and transport

- [x] 2.1 Separate latest parsed reply readings from the merged coordinator snapshot; test omitted registers, cached reads after a failed poll, and the fixed fallback reply using fake exchanges.
- [x] 2.2 Implement guarded boiler and combustion power writes under the coordinator lock; verify exact frames, 60–80 °C limits, tighter bounds, fractional rejection, fresh Off without a target, stale or non-writable conditions, and Auto `6`/`7` readback. Document the register mappings and the observed model-specific room reading without changing climate behavior.
- [x] 2.3 Check rejection, empty reply, and timeout handling; verify that these do not publish an optimistic result, that send attempts still schedule delayed readback, and that legacy commands keep their original behavior.

## 3. Entity and service integration

- [x] 3.1 Add stable Celsius number and combustion power select entities for opted-in entries; verify availability, readback, labels, and that the new controls show no protocol details. Add end-user usage and compatibility guidance to the README.
- [x] 3.2 Update the opted-in legacy power sensor decoding and route the two opted-in sensor service writes to the shared guarded setters; test legacy P6, routed explicit numeric and referenced values, rejection of missing or fractional values, and normal generic and thermostat routes.

## 4. Integration verification

- [x] 4.1 Run the mocked test suite and OpenSpec strict validation. Verify an opted-in entry and an unchanged entry together; confirm no extra queries, no ignition command when changing either setting, and no changes to the thermostat or room-value fallback. Report any Home Assistant runtime or hardware checks not performed.
