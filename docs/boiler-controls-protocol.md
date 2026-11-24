# Boiler control protocol findings

These findings come from testing the sibling 4Heat Controller Windows app with one stove. They are not a device detection rule or a guarantee that another 4Heat model implements the same controls. HA-4heat uses them only when its boiler compatibility option is enabled for that entry.

| Register | Role on the tested setup |
| --- | --- |
| `30017` | Measured boiler water temperature in °C, not a target |
| `20199` | Boiler target (the working target B in the Windows app) |
| `20180` | Alternative boiler target listed by the legacy sensor table; the new control does not use it |
| `20205`/`20206`, `20005`/`20006` | Minimum/maximum limits; positive limits from the latest reply may narrow 60–80 °C |
| `20364` | Configured combustion power, not instantaneous combustion power (`30011`) |

Both writes use `["SEC","1","B<id><12-digit value>"]`. Neither sends a power-on or power-off command.

- **Water target:** `["SEC","1","B20199000000000070"]` sets 70 °C. A fresh `B20199` authorizes a write, as does a fresh Off state (`30001 = 0`) when `20199` is omitted and no contradictory marker is known. The stove may omit the target from readback while off; Home Assistant displays only the last reported target, if any.
- **Combustion power:** requires fresh `B20364`. Levels 1–5 use the same wire values. Auto writes `6` (`["SEC","1","B20364000000000006"]`); reported `6` or `7` means Auto for the opt-in profile. Without the profile, existing telemetry continues to map `6` to P6 and `7` to Auto.

For either register on an opted-in entry, `4heat.set_value` follows the same checks as the native control. It requires an explicit whole numeric value (a number, numeric text, or a reference to a numeric entity state). A power value of `7` is accepted from existing automations but sent as `6`. Other entries and registers retain the generic service's original behavior.

No ad hoc register queries are needed. Polling uses the existing bulk query and its fixed error fallback. An empty response, `ERR`, or transport error fails an opted-in write; even a successful exchange is not proof of application. The integration reads back later rather than reporting the requested value optimistically.

During Windows testing, the module returned `0` for `30006` while the official app showed about 20 °C. The source of the discrepancy was not verified; HA-4heat's existing room sensor and thermostat are unchanged. Do not assume that `0` is invalid on every model.
