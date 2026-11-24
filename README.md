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

The integration is configurated via UI

For a compatible stove, open **Settings → Devices & services → 4Heat Stove** and
choose **Configure** on that stove's entry. Select **Enable boiler water and
five-level combustion controls** in the options. The entry reloads
automatically. Turn the option off again to restore the original behavior; you
do not need to remove or re-add the integration.

BETA * BETA * BETA - Not finished yet - BETA * BETA * BETA

### Boiler water and combustion power

The optional **Boiler water target** control uses whole degrees from 60–80 °C
and respects tighter limits reported by the stove. You can change the target
while the stove is confirmed off; the setting does not turn it on. A stove
that omits its target while off may not show the new value until it reports
it again.

**Combustion power** offers Level 1 through Level 5 and Auto. It changes the
configured setting, not the stove's on/off state or its measured power.
Both controls display what the stove reports instead of immediately showing
the requested value. The integration normally asks for a readback after
25 seconds.

Enable these controls only for a compatible model; leave them disabled if
your stove has a sixth manual power level. The option does not change
the existing room thermostat. See the [protocol findings](docs/boiler-controls-protocol.md)
for the technical mappings.

### Thermostat (room setpoint)

If the stove reports a room setpoint (`J30138`), a `climate` entity is created:
target temperature = J30138 (whole °C), current temperature = 30006, HVAC mode = ON/OFF.
The setpoint is written with `["SEC","1","J30138000000000020"]` (20 °C) and also works
through the `4heat.set_value` service on the `UN 30138` / `Room setpoint` sensor.

If the stove loses its wireless room probe it falls back to its internal probe and
reports wrong values (e.g. room 29 °C, setpoint 38 °C): the integration keeps the
last trusted values meanwhile and shows `room_probe: lost since HH:MM` on the thermostat.

### Connection to the Wi-Fi module

The module's local server saturates easily, so the integration makes only one TCP
exchange at a time, polls every 120 s, waits 5 min after a failure and re-reads the
stove 25 s after a command. Avoid sending read commands for ids the stove does not
report: on some modules this freezes the local server until a power cycle.

### Developer specification

See the [OpenSpec baseline](openspec/README.md) for the integration's behavior,
protocol, acceptance scenarios, and known limitations.

### Todo:
- [x] Monitorig of all status values
- [ ] Discover more sensor meanings
- [ ] Find a way to get model and serial
- [x] Add Service to set value like target temp
- [x] Add Icons


