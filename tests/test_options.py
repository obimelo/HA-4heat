"""Tests for the 4Heat boiler profile option."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

config_flow = import_module("custom_components.4heat.config_flow")
const = import_module("custom_components.4heat.const")


@pytest.mark.asyncio
@pytest.mark.parametrize("saved,expected", [(None, True), (False, False), (True, True)])
async def test_boiler_option_defaults_to_enabled_and_respects_saved_choices(saved, expected):
    options = {"other_option": "keep"}
    if saved is not None:
        options[const.CONF_BOILER_CONTROLS] = saved
    entry = SimpleNamespace(options=options)
    flow = config_flow.FourHeatConfigFlow.async_get_options_flow(entry)
    flow.flow_id = "test-options"
    flow.handler = "existing-entry"

    with patch.object(config_flow.FourHeatOptionsFlow, "config_entry", entry):
        form = await flow.async_step_init()
        assert form["data_schema"]({}) == {const.CONF_BOILER_CONTROLS: expected}

        result = await flow.async_step_init({const.CONF_BOILER_CONTROLS: not expected})
        assert result["data"] == {"other_option": "keep", const.CONF_BOILER_CONTROLS: not expected}
