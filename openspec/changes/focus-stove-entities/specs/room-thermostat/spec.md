# Room Thermostat Delta

## REMOVED Requirements

### Requirement: Thermostat creation, identity and availability
**Reason**: The stove device no longer exposes a room thermostat.
**Migration**: Remove or replace cards and automations using the retired climate entity.

### Requirement: Climate modes and actions
**Reason**: No climate entity is exposed.
**Migration**: Use the State sensor and Power ON/OFF switch for stove status and power.

### Requirement: Climate power controls
**Reason**: Power is exposed through the Power ON/OFF switch.
**Migration**: Use `switch.turn_on` or `switch.turn_off` on the Power ON/OFF switch.

### Requirement: Temperature reporting and setpoint control
**Reason**: The room sensor and thermostat are not exposed.
**Migration**: Use a separate room temperature sensor if needed. Boiler target adjusts water temperature, not room temperature.

### Requirement: Thermostat diagnostics
**Reason**: The retired climate entity no longer exposes diagnostics.
**Migration**: Use the State and Error Message sensors for device status.
