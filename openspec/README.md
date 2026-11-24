# HA-4heat OpenSpec baseline

This is a source-derived baseline of `883c8f0` (`climate-setpoint-stability`, integration manifest version `0.7.0`). Requirements describe behavior in that revision, not proposed fixes or a guarantee of compatibility with every stove. Known limitations are listed separately below. The source was analyzed without connecting to Home Assistant or a stove.

| Capability | Scope | Implementation sources |
| --- | --- | --- |
| [Integration setup](specs/integration-setup/spec.md) | Packaging, UI and YAML entry creation, duplicate hosts, startup retry | `manifest.json`, `hacs.json`, `config_flow.py`, `__init__.py` |
| [Module communication](specs/module-communication/spec.md) | TCP protocol, parsing, polling, backoff, command refresh | `const.py`, `coordinator.py` |
| [Stove telemetry](specs/stove-telemetry/spec.md) | Sensor discovery, names and units, state decoding, entity metadata | `sensor.py`, `const.py` |
| [Stove switches](specs/stove-switches/spec.md) | Power and error switches, full and legacy command modes | `switch.py`, `coordinator.py`, `const.py` |
| [Room thermostat](specs/room-thermostat/spec.md) | Climate state and controls, setpoint writes, room-probe fallback | `climate.py`, `coordinator.py` |
| [Parameter write service](specs/parameter-write-service/spec.md) | `4heat.set_value` input handling, dispatch and feedback | `__init__.py`, `services.yaml`, `coordinator.py`, `sensor.py` |

## Runtime map

```text
UI or YAML import -> config entry -> per-entry coordinator -> local 4Heat TCP module
                                       |
                                       +-> sensor, switch and climate entities
                                       +<- set_value service (routes by target sensor)
```

The coordinator owns the snapshot shared by all three platforms for one entry. At runtime the stove supplies telemetry; Home Assistant sends manual or automation commands but does not run its own room-temperature control loop. No cloud API, credential flow, or automatic discovery is implemented. `SENSOR_TYPES`, `MODE_NAMES`, `ERROR_NAMES`, and `POWER_NAMES` in `const.py` are the complete lookup tables; the specs describe their role and representative values rather than duplicating them.

## Known limitations and review notes

These are findings from source inspection, not approved behavior changes.

| Area | Finding |
| --- | --- |
| Setup validation | The config flow's connection check can accept a short or empty decoded reply and only explicitly catches `ConnectTimeout` and `HTTPError`, not normal socket errors. Its `could_not_connect` key does not match `cannot_connect` in `strings.json`. The first runtime refresh is the separate readiness check. |
| Entry lifecycle and identity | There is no integration-provided unload, reload, options, or reconfigure flow. The service is registered during each successful entry setup. Sensor and switch IDs depend on the entry title and reading ID; same-title entries can collide within a platform. Their device identifiers all use the placeholder serial `1`, so separate stoves can share a device registry identity. |
| Transport limits | The coordinator uses one send and one receive of at most 1,024 bytes, with no framing or multi-read assembly. Partial or malformed nonempty replies can be treated as successful while retaining stale readings; missing registers have no per-reading expiry. The lock is per coordinator, excludes the setup probe, and can be released after an outer timeout while an executor thread is still finishing. |
| Command confirmation | A decoded response, including an empty string or a device error token, can count as send success. Optimistic writes are not confirmation that the stove accepted a value. The switch also requests an immediate refresh, despite the README describing delayed confirmation. |
| Thermostat range and probe | Climate advertises 15–28 °C, while shared write validation clamps to 5–30 °C. Probe loss is inferred from setpoint alone: a large legitimate external change can look like probe loss, a retained value can look like recovery, and the last successful `J` write has no expiry. Startup with no trusted sample cannot hide fallback readings. The thermostat is created only at platform setup and is gated by reading ID, not by marker. |
| Service input | The YAML file describes the service but is not a runtime schema. Missing entity states/attributes, invalid referenced states, and values that cannot be converted can raise errors. Unrecognized non-entity strings currently fall back to `1`; targets with unsupported markers are logged and not written. |
| Packaging and verification | HACS metadata lists only `sensor` and `switch`, although runtime also forwards `climate`. The repository has hassfest and CodeQL workflows but no checked-in runtime test suite. The manifest version alone does not identify the thermostat-enabled revision. |

## Validate or extend

With the [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec) available, run:

```text
openspec list --specs
openspec validate --specs --strict
```

CLI validation checks document structure, not runtime conformance. For implementation verification, use a Home Assistant test instance with fake TCP replies, controllable time, and synthetic entity states. Assert commands against the fake module, including full versus legacy mode, and verify stale-data and probe transitions with sequential replies. Do not send exploratory register reads to hardware; the project reports that some modules stop responding when queried for unreported IDs. The coordinator notes describe testing on a Fogo Montanha Square D pellet insert, not universal hardware validation.

Run the checked-in mocked integration tests in an isolated Python 3.13 environment:

```text
python -m pip install -r tests/requirements.txt
python -m pytest -o asyncio_default_fixture_loop_scope=function tests
```

The suite instantiates Home Assistant core objects with simulated module replies; it does not need a running Home Assistant installation or a stove. On Windows, the pinned Home Assistant dependencies may require C++ Build Tools if prebuilt wheels are unavailable.

To check the newer compatibility target, use a separate Python 3.14 environment with `homeassistant==2026.11.3`, `pytest`, and `pytest-asyncio`, then run the same test command.

For future behavior changes, create an OpenSpec change under `openspec/changes/`, describe only the affected requirements in delta specs, and archive the change after implementation and verification. This initial documentation does not introduce a pending runtime change.
