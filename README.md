# homeassistant-4heat

Home Assistant Component for 4heat stove devices

<a href="https://www.buymeacoffee.com/zauberertz" target="_blank"><img height="41px" width="167px" src="https://cdn.buymeacoffee.com/buttons/default-blue.png" alt="Buy Me A Coffee"></a>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

### Installation

Copy the repository's `custom_components/4heat/` directory to
`<config_dir>/custom_components/4heat/`.

Running Home Assistant in Docker? See the [Home Assistant Container installation guide](docs/home-assistant-container.md)
for deployment, configuration, troubleshooting, and rollback.

### HACS
Search for 4Heat

### Configuration

Add the integration in the Home Assistant UI. It exposes these readings when
reported: **State**, **Error Message**, **Exhaust temperature**, **Combustion Power**,
**Boiler water**, **Water pressure**, and **Boiler target**. Other readings and
the room thermostat are no longer added.

The **Power ON/OFF** switch starts or stops the stove. The **Clear Error** switch sends an
unblock command when switched off; it does not mute alerts. Legacy command
mode still provides only the power switch.

**Enable boiler water and five-level combustion controls** defaults to on for
entries with no saved choice. An explicit off setting is preserved. To change
it, open **Settings → Devices & services → 4Heat Stove** and choose
**Configure** on that stove's entry. The entry reloads automatically.

With the option enabled, the read-only **Combustion Power** and **Boiler target**
sensors are hidden from the device page because the controls show the reported
values. The sensors keep their IDs and remain usable by automations.

BETA * BETA * BETA - Not finished yet - BETA * BETA * BETA

### Boiler water and combustion power

The optional **Boiler Target** slider uses whole degrees from 60–80 °C
and respects tighter limits reported by the stove. You can change the target
while the stove is confirmed off; the setting does not turn it on. A stove
that omits its target while off may not show the new value until it reports
it again.

The **Combustion Power** dropdown offers **Auto, P5, P4, P3, P2, P1** in that order. It changes the
configured setting, not the stove's on/off state or its measured power.
Both controls display what the stove reports instead of immediately showing
the requested value. The integration normally asks for a readback after
25 seconds.

Turn these controls off if your stove has a sixth manual power level or lacks
compatible boiler controls. See the [protocol findings](docs/boiler-controls-protocol.md)
for the technical mappings.

### Upgrading an existing entry

Check dashboards and automations that referenced the removed entities. Old
registry entries can remain unavailable until removed in Home Assistant. In
automations that call `select.select_option`, replace `Level 1`–`Level 5` with
`P1`–`P5`; `Auto` is unchanged.

### Connection to the Wi-Fi module

The module's local server saturates easily, so the integration makes only one TCP
exchange at a time, polls every 120 s, waits 5 min after a failure and re-reads the
stove 25 s after a command. Avoid sending read commands for ids the stove does not
report: on some modules this freezes the local server until a power cycle.

### Developer specification

See the [OpenSpec baseline](openspec/README.md) for the integration's behavior,
protocol, acceptance scenarios, and known limitations.

### Todo:
- [x] Monitor the supported stove and boiler readings
- [ ] Find a way to get model and serial
- [x] Add Service to set value like target temp
- [x] Add Icons


