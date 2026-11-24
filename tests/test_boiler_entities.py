"""Verify native Home Assistant number and select behavior."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
number = import_module("custom_components.4heat.number")
select = import_module("custom_components.4heat.select")


@pytest.mark.asyncio
async def test_controls_use_reported_values_and_user_facing_names(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    instance = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"},
        options={const.CONF_BOILER_CONTROLS: True}, id="configured-stove",
    )
    hass.data[const.DOMAIN] = {instance.stove_id: {const.DATA_COORDINATOR: instance}}
    entry = SimpleNamespace(entry_id=instance.stove_id, title="My stove")
    exchange = Mock(side_effect=[
        '["SEC","1","I30001000000000000"]',
        '["SEC","0"]',
        '["SEC","3","B20199000000000070","B20364000000000002","B20206000000000075"]',
        '["SEC","0"]',
        '["SEC","1","B20364000000000007"]',
        TimeoutError("simulated timeout"),
    ])
    monkeypatch.setattr(instance, "_exchange", exchange)
    added = []
    await number.async_setup_entry(hass, entry, added.extend)
    await select.async_setup_entry(hass, entry, added.extend)
    target, power = added

    try:
        assert target.name == "My stove Boiler water target"
        assert power.name == "My stove Combustion power"
        assert target.unique_id == "configured-stove_boiler_target"
        assert power.unique_id == "configured-stove_combustion_power"
        assert target.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert target.native_step == 1
        assert power.options == ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5", "Auto"]
        assert not target.extra_state_attributes and not power.extra_state_attributes

        await instance.async_refresh()
        assert target.available and target.native_value is None
        assert (target.native_min_value, target.native_max_value) == (60, 80)
        assert not power.available
        await target.async_set_native_value(70)
        assert target.native_value is None

        await instance.async_refresh()
        assert target.native_value == 70 and target.native_max_value == 75
        assert power.available and power.current_option == "Level 2"
        with pytest.raises(ServiceValidationError, match="Choose combustion power"):
            await power.async_select_option("Level 6")
        await power.async_select_option("Auto")
        assert power.current_option == "Level 2"

        await instance.async_refresh()
        assert power.current_option == "Auto"
        assert target.native_value == 70 and not target.available
        await instance.async_refresh()
        assert not power.available
        assert power.current_option == "Auto"
        assert exchange.call_count == 6
    finally:
        await instance.async_shutdown()


@pytest.mark.asyncio
async def test_disabled_platforms_add_no_entities(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    instance = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"}, options={}, id="legacy",
    )
    hass.data[const.DOMAIN] = {instance.stove_id: {const.DATA_COORDINATOR: instance}}
    entry = SimpleNamespace(entry_id=instance.stove_id, title="Legacy stove")
    add_entities = Mock()
    try:
        await number.async_setup_entry(hass, entry, add_entities)
        await select.async_setup_entry(hass, entry, add_entities)
        add_entities.assert_not_called()
    finally:
        await instance.async_shutdown()
