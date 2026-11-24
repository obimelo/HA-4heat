"""Verify native Home Assistant number and select behavior."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.components.number import NumberMode
from homeassistant.config_entries import ConfigEntries
from homeassistant.const import CONF_HOST, CONF_MONITORED_CONDITIONS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest

const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
number = import_module("custom_components.4heat.number")
select = import_module("custom_components.4heat.select")
sensor = import_module("custom_components.4heat.sensor")
switch = import_module("custom_components.4heat.switch")


async def load_registries(hass):
    hass.config_entries = ConfigEntries(hass, {})
    await hass.config_entries.async_initialize()
    if hasattr(dr, "async_setup"):
        dr.async_setup(hass)
    await dr.async_load(hass)
    await er.async_load(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("primary_reported", [False, True])
async def test_only_selected_readings_and_switches_are_exposed(tmp_path, primary_reported):
    hass = HomeAssistant(str(tmp_path))
    await load_registries(hass)
    instance = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"}, options={}, id="configured-stove",
    )
    hass.data[const.DOMAIN] = {instance.stove_id: {const.DATA_COORDINATOR: instance}}
    reported = [
        "30001", "30002", "30005", "20364", "30017", "30020", "20180",
        "30006", "30138", "30084", "20365", "40007", "30001",
    ]
    if primary_reported:
        reported.append("20199")
    entry = SimpleNamespace(
        entry_id=instance.stove_id, title="My stove",
        data={CONF_MONITORED_CONDITIONS: [f"B{reading_id}000000000001" for reading_id in reported]},
    )
    added = []
    try:
        await sensor.async_setup_entry(hass, entry, added.extend)
        assert [item.type for item in added] == [
            "30001", "30002", "30005", "20364", "30017", "30020",
            "20199" if primary_reported else "20180",
        ]
        assert added[-1].name == "My stove Boiler target"
        switches = []
        await switch.async_setup_entry(hass, entry, switches.extend)
        assert [item.type for item in switches] == ["30001", "30002"]
        assert [item.name for item in switches] == ["My stove Power ON/OFF", "My stove Clear Error"]
        assert switches[1].unique_id == "My stove_30002"
        assert switches[0].unique_id == added[0].unique_id == "My stove_30001"
        assert added[0].name == "My stove State"
        assert added[1].name == "My stove Error Message"
        assert added[1].unique_id == "My stove_30002"
        assert added[3].name == "My stove Combustion Power"
        assert added[3].unique_id == "My stove_20364"
    finally:
        await instance.async_shutdown()


@pytest.mark.asyncio
async def test_duplicate_sensors_are_hidden_not_removed_when_controls_are_enabled(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    await load_registries(hass)
    entry = SimpleNamespace(
        entry_id="example", title="My stove", pref_disable_new_entities=False, disabled_by=None,
        data={CONF_MONITORED_CONDITIONS: [
            "B20364000000000003", "B20199000000000070", "I30017000000000065",
        ]},
    )
    other = SimpleNamespace(entry_id="other", pref_disable_new_entities=False, disabled_by=None)
    hass.config_entries = SimpleNamespace(
        async_get_entry={entry.entry_id: entry, other.entry_id: other}.get,
    )
    registry = er.async_get(hass)
    power = registry.async_get_or_create(
        "sensor", const.DOMAIN, "My stove_20364", config_entry=entry,
    )
    target = registry.async_get_or_create(
        "sensor", const.DOMAIN, "My stove_20199", config_entry=entry,
    )
    user_hidden = registry.async_get_or_create(
        "sensor", const.DOMAIN, "My stove_20180", config_entry=entry,
        hidden_by=er.RegistryEntryHider.USER,
    )
    other_power = registry.async_get_or_create(
        "sensor", const.DOMAIN, "Other stove_20364", config_entry=other,
    )
    instance = coordinator_module.FourHeatDataUpdateCoordinator(
        hass, config={CONF_HOST: "simulated.invalid"},
        options={const.CONF_BOILER_CONTROLS: True}, id=entry.entry_id,
    )
    hass.data[const.DOMAIN] = {entry.entry_id: {const.DATA_COORDINATOR: instance}}
    try:
        added = []
        instance.async_set_updated_data({const.POWER_TYPE: [3, "B"], const.BOILER_TARGET_ID: [70, "B"]})
        await sensor.async_setup_entry(hass, entry, added.extend)
        assert [(item.entity_registry_visible_default, item.native_value) for item in added] == [
            (False, "P3"), (False, 70), (True, None),
        ]
        for duplicate in (power, target):
            registered = registry.async_get(duplicate.entity_id)
            assert registered.hidden_by == er.RegistryEntryHider.INTEGRATION
            assert registered.disabled_by is None
        assert registry.async_get(user_hidden.entity_id).hidden_by == er.RegistryEntryHider.USER
        assert registry.async_get(other_power.entity_id).hidden_by is None

        instance.boiler_controls = False
        added.clear()
        await sensor.async_setup_entry(hass, entry, added.extend)
        assert all(item.entity_registry_visible_default for item in added)
        assert registry.async_get(power.entity_id).hidden_by is None
        assert registry.async_get(target.entity_id).hidden_by is None
        assert registry.async_get(user_hidden.entity_id).hidden_by == er.RegistryEntryHider.USER
    finally:
        await instance.async_shutdown()


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
        assert target.name == "My stove Boiler Target"
        assert power.name == "My stove Combustion Power"
        assert target.unique_id == "configured-stove_boiler_target"
        assert power.unique_id == "configured-stove_combustion_power"
        assert target.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert target.native_step == 1
        assert target.mode == NumberMode.SLIDER
        assert power.options == ["Auto", "P5", "P4", "P3", "P2", "P1"]
        expected_device = sensor.FourHeatDevice(instance, const.MODE_TYPE, entry.title).device_info
        assert target.device_info == power.device_info == expected_device
        assert not target.extra_state_attributes and not power.extra_state_attributes

        await instance.async_refresh()
        assert target.available and target.native_value is None
        assert (target.native_min_value, target.native_max_value) == (60, 80)
        assert not power.available
        await target.async_set_native_value(70)
        assert target.native_value is None

        await instance.async_refresh()
        assert target.native_value == 70 and target.native_max_value == 75
        assert power.available and power.current_option == "P2"
        with pytest.raises(ServiceValidationError, match="Choose combustion power"):
            await power.async_select_option("P6")
        await power.async_select_option("Auto")
        assert power.current_option == "P2"

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
        hass, config={CONF_HOST: "simulated.invalid"},
        options={const.CONF_BOILER_CONTROLS: False}, id="legacy",
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
