"""Tests for the opt-in 4Heat profile."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

config_flow = import_module("custom_components.4heat.config_flow")
const = import_module("custom_components.4heat.const")


@pytest.mark.asyncio
async def test_existing_entry_defaults_to_disabled_and_preserves_options():
    """An upgrade does not opt a stove in or overwrite unrelated options."""
    entry = SimpleNamespace(options={"other_option": "keep"})
    flow = config_flow.FourHeatConfigFlow.async_get_options_flow(entry)
    flow.flow_id = "test-options"
    flow.handler = "existing-entry"

    with patch.object(config_flow.FourHeatOptionsFlow, "config_entry", entry):
        form = await flow.async_step_init()
        assert form["data_schema"]({}) == {const.CONF_BOILER_CONTROLS: False}

        result = await flow.async_step_init({const.CONF_BOILER_CONTROLS: True})
        assert result["data"] == {"other_option": "keep", const.CONF_BOILER_CONTROLS: True}
