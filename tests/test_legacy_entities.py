"""Ensure native Home Assistant APIs retain existing entity and action data."""

from datetime import timedelta
from importlib import import_module
import logging
from unittest.mock import Mock, patch

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntries
from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.entity_platform import EntityPlatform
import pytest

const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
sensor = import_module("custom_components.4heat.sensor")
switch = import_module("custom_components.4heat.switch")
select = import_module("custom_components.4heat.select")


@pytest.mark.asyncio
async def test_sensor_routing_attributes_are_published_in_home_assistant(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    if hasattr(device_registry, "async_setup"):
        device_registry.async_setup(hass)
    await device_registry.async_load(hass)
    await entity_registry.async_load(hass)
    coordinator = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"},
        options={const.CONF_BOILER_CONTROLS: False}, id="example",
    )
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="sensor",
        platform_name=const.DOMAIN,
        platform=sensor,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    try:
        coordinator.async_set_updated_data({
            const.POWER_TYPE: [6, "B"],
            const.BOILER_TARGET_ID: [70, "B"],
        })
        power = sensor.FourHeatDevice(coordinator, const.POWER_TYPE, "My stove")
        assert isinstance(power, SensorEntity)
        assert power.unique_id == "My stove_20364"
        assert power.native_value == "P6"
        assert power.device_info["identifiers"] == {(const.DOMAIN, "1")}
        # This standalone platform tests state publication, not device attachment.
        with patch.object(sensor.FourHeatDevice, "device_info", None):
            await platform.async_add_entities([power])
        assert power.entity_id is not None
        state = hass.states.get(power.entity_id)
        assert state.state == "P6"
        assert {key: state.attributes[key] for key in ("stove_id", "reading_id", "marker", "num_val")} == {
            "stove_id": "example", "reading_id": "20364", "marker": "B", "num_val": 6,
        }

        target = sensor.FourHeatDevice(coordinator, const.BOILER_TARGET_ID, "My stove")
        assert target.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert target.native_value == 70
    finally:
        await platform.async_reset()
        await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_combustion_selection_publishes_provisional_and_corrected_states(tmp_path, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    if hasattr(device_registry, "async_setup"):
        device_registry.async_setup(hass)
    await device_registry.async_load(hass)
    await entity_registry.async_load(hass)
    coordinator = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"}, options={}, id="example",
    )
    platform = EntityPlatform(
        hass=hass, logger=logging.getLogger(__name__), domain="select",
        platform_name=const.DOMAIN, platform=select, scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    exchange = Mock(side_effect=[
        '["SEC","1","B20364000000000003"]', '["ERR"]', '["SEC","1","B20364000000000002"]',
    ])
    timers = Mock(return_value=Mock())
    notify = Mock()
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    monkeypatch.setattr(coordinator_module, "async_call_later", timers)
    monkeypatch.setattr(coordinator_module.persistent_notification, "async_create", notify)
    try:
        await coordinator.async_refresh()
        power = select.FourHeatCombustionPower(coordinator, "My stove")
        with patch.object(select.FourHeatCombustionPower, "device_info", None):
            await platform.async_add_entities([power])
        assert hass.states.get(power.entity_id).state == "P3"
        await power.async_select_option("Auto")
        assert hass.states.get(power.entity_id).state == "Auto"
        notify.assert_not_called()
        check = timers.call_args_list[0].args[2]
        assert timers.call_args_list[0].args[1] == coordinator_module.CONFIRM_DELAY
        await check(None)
        assert hass.states.get(power.entity_id).state == "P2"
        notify.assert_called_once()
    finally:
        await platform.async_reset()
        await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_switch_keeps_diagnostics_for_an_unmapped_state(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    coordinator = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"}, options={}, id="example",
    )
    try:
        coordinator.async_set_updated_data({const.MODE_TYPE: [99, "I"]})
        entity = switch.FourHeatSwitch(coordinator, const.MODE_TYPE, "My stove")
        assert entity.unique_id == "My stove_30001"
        assert entity.is_on
        assert entity.extra_state_attributes == {"Num Val": 99, "Val text": "Unknown"}
    finally:
        await coordinator.async_shutdown()
