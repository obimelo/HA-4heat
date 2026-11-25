# Tasks

## 1. Stove device

- [x] 1.1 Filter sensors and stop forwarding climate; verify the retained sensors, both switch types in standard mode, and both boiler-target inventory cases by mock.
- [x] 1.2 Expose the opt-in slider and selector on the stove device; verify range, option ordering, stable IDs, and guarded readbacks by mock.
- [x] 1.3 Document the new device list and the upgrade impact; verify the integration suite on Core 2025.1.4 and 2026.11.3.
- [x] 1.4 Hide duplicate setting sensors when the native controls are enabled; verify existing IDs, unhide on opt-out, and preservation of user-hidden and other-stove entities on both Core versions.
- [x] 1.5 Enable boiler controls by default; verify saved opt-outs remain disabled and setup sends no write on both Core versions.
- [x] 1.6 Show provisional values on the four native controls and notify only on a fresh mismatch. Verify optimistic state publication, rollback, failed or missing replies, concurrent controls, and unload on both Core versions.
