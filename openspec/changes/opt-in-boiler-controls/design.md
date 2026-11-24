# Design

## Context

See [proposal.md](proposal.md) for motivation. The coordinator currently merges replies into cached data, so the presence of a register in the public snapshot does not show that it was in the latest reply. The legacy service accepts generic `B` writes and updates cached values optimistically. The current config flow does not expose entry options or an unload path.

## Goals / Non-Goals

**Goals**

- Provide two native entities with one validation path shared by their setters and the legacy service's opted-in routes.
- Preserve existing entry and entity IDs and existing interoperability with stoves that use power code `6` for P6.
- Keep failed or unconfirmed commands distinguishable from the values actually reported by the stove.

**Non-Goals**

- No automatic model discovery, per-register probe, new dependency, or Windows-app change.
- No room temperature or thermostat changes, no new generic write feature, and no changes to legacy ON/OFF or error switch behavior.
- No separate error history store; Home Assistant already has state history facilities.

## Decisions

1. **Make the tested behavior an explicit per-entry option.** Show a descriptive compatibility option in Home Assistant's configuration dialog, defaulting to false. This is safer than inferring compatibility from register presence because the existing integration and the tested stove interpret code `6` differently. Keep the original config entry version, preserve unrelated options, and use the normal reload path so existing entries can enable the controls. Unload the platforms and retire the old coordinator's delayed callback only after successful platform unload. Keep the domain service usable by other loaded entries.
2. **Use a native number and select, backed by the same coordinator as existing entities.** Give them entry-scoped stable IDs, independent of the title and initial register inventory, so a setting that is missing at setup can become available later. The number displays degrees Celsius and the writable interval; it may be available with unknown value when a fresh state confirms Off. The select shows only supported named options. Update the existing power sensor's decoding per entry; do not change its attributes or the global legacy table.
3. **Track fresh readings separately from the merged snapshot.** Retain the registers parsed from the latest actual bulk or fallback reply and clear them after an attempted poll failure. An exchange skipped because the lock is occupied does not produce fresh data. Reuse the fresh snapshot for availability and validate again under the shared exchange lock before writing. An omitted boiler target can be written only with fresh Off state and no known contradictory marker. A missing power target never enables a write. Existing display and room-probe behavior continues to use the merged snapshot.
4. **Use dedicated guarded setters instead of adding unrestricted writes.** Derive blanket limits from 60–80 °C and intersect them with all positive reported lower and upper bounds. Accept only integral finite values for opted-in service routes, with no silent fallback on missing or nonnumeric values. Centralize Auto encoding (`6`) and decoding (`6` or `7`). Match the guarded routes by entry and reading ID, not by a potentially cached sensor marker; the coordinator owns the marker and freshness checks. Keep the current service parsing and optimism for all other routes.
5. **Use eventual readback without optimistic state.** An opted-in write uses the existing executor and lock, checks for empty or `ERR` replies, and schedules the existing delayed refresh even after send failure. A local validation failure sends no frame and requires no additional refresh. The new controls display the actual reported state; no new polling interval, automatic retry, or power command is needed. Surface failures as Home Assistant errors in plain language; keep protocol details in documentation and debug logs.

## Risks / Trade-offs

- **Unverified firmware may reinterpret the same register.** Leave the option disabled by default, document the tested mapping separately from broader compatibility, and require live eligibility checks.
- **A stove may suppress the target even after a successful write while off.** Leave the previous reported value or unknown value visible until the stove provides a reading.
- **A write can change a parameter even if the transport times out.** Report the failed exchange, then request delayed readback; do not retry automatically.
- **A skipped or failed poll may leave apparently usable cached readings.** Keep stale values for display but never use them in place of required fresh observations.

## Migration Plan

Upgrade without enabling the option to keep current behavior. For a known compatible stove, enable the option in Home Assistant and let that entry reload. Disable it to remove the extra runtime controls and restore the existing interpretation of code `6` and generic service behavior. No data migration or rollback write to the appliance is needed.
