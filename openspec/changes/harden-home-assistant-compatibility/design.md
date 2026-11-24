# Design

## Decisions

- Share a context-managed IPv4 socket exchange between the config flow and runtime. Use `sendall` for the existing frame; keep the single receive, socket timeout, executor, shared runtime lock, outer timeout, and poll/backoff intervals.
- During setup, accept any reply containing at least one valid reading token. Use the existing fixed fallback only after `ERR`. Save the supported reading tokens as the inventory; remove the unused selection field without changing YAML import.
- Use `async_config_entry_first_refresh()` with the explicit config entry and shut down on setup failure. Replace `async_timeout` with `asyncio.timeout()` and get local polling metadata from the manifest.
- Use native sensor properties and publish legacy attributes via `extra_state_attributes` without changing registry identities. Keep the action's text input compatible with both numeric values and helper entity IDs instead of copying the upstream 0–10 selector.

## Compatibility

Do not adopt the upstream domain rename, shorter poll interval, retry loop, country restriction, or placeholder-based entity IDs. Existing entries do not require migration.
