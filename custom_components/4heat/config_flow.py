"""Config flow for the 4Heat integration."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_MONITORED_CONDITIONS
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_BOILER_CONTROLS,
    CONF_MODE,
    DATA_QUERY,
    DEFAULT_BOILER_CONTROLS,
    DOMAIN,
    ERROR_QUERY,
    RESULT_ERROR,
)
from .transport import exchange, is_reading_token, reply_tokens

_LOGGER = logging.getLogger(__name__)


@callback
def four_heat_entries(hass: HomeAssistant):
    """Return the hosts for the domain."""
    return {
        entry.data[CONF_HOST]
        for entry in hass.config_entries.async_entries(DOMAIN)
        if CONF_HOST in entry.data
    }


class FourHeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """4Heat config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Configure optional controls for an existing entry."""
        return FourHeatOptionsFlow()

    @staticmethod
    def _check_host(host: str) -> list[str]:
        """Return reported reading tokens, or an empty list if the probe fails."""
        try:
            tokens = reply_tokens(exchange(host, DATA_QUERY))
            if tokens[0] == RESULT_ERROR:
                tokens = reply_tokens(exchange(host, ERROR_QUERY))
        except (OSError, UnicodeError) as err:
            _LOGGER.debug("Could not read stove at %s: %s", host, err)
            return []
        if tokens[0] == RESULT_ERROR:
            return []
        return [token for token in tokens if is_reading_token(token)]

    async def async_step_user(self, user_input=None):
        """Set up a stove only after a successful probe."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            if host in four_heat_entries(self.hass):
                errors[CONF_HOST] = "host_exists"
            else:
                conditions = await self.hass.async_add_executor_job(
                    self._check_host, host
                )
                if conditions:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_HOST: host,
                            CONF_MODE: user_input.get(CONF_MODE, False),
                            CONF_MONITORED_CONDITIONS: conditions,
                        },
                    )
                errors[CONF_HOST] = "cannot_connect"

        values = user_input or {}
        setup_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=values.get(CONF_NAME, "Stove")): str,
                vol.Required(CONF_HOST, default=values.get(CONF_HOST, "192.168.0.0")): str,
                vol.Optional(CONF_MODE, default=values.get(CONF_MODE, False)): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=errors
        )

    async def async_step_import(self, user_input):
        """Import a config entry."""
        if user_input[CONF_HOST] in four_heat_entries(self.hass):
            return self.async_abort(reason="host_exists")
        return await self.async_step_user(user_input)


class FourHeatOptionsFlow(config_entries.OptionsFlow):
    """Configure stove-specific compatibility options."""

    async def async_step_init(self, user_input=None):
        """Show or save the per-entry boiler compatibility option."""
        options = self.config_entry.options
        if user_input is not None:
            return self.async_create_entry(title="", data={**options, **user_input})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_BOILER_CONTROLS,
                    default=options.get(CONF_BOILER_CONTROLS, DEFAULT_BOILER_CONTROLS),
                ): bool,
            }),
        )
