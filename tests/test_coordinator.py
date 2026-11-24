"""Verify coordinator behavior with synthetic TCP replies only."""

import asyncio
from importlib import import_module
from unittest.mock import Mock

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest
import pytest_asyncio

const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
climate = import_module("custom_components.4heat.climate")


@pytest_asyncio.fixture
async def coordinator(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    instance = coordinator_module.FourHeatDataUpdateCoordinator(
        hass,
        config={CONF_HOST: "simulated.invalid"},
        options={const.CONF_BOILER_CONTROLS: True},
        id="simulated",
    )
    yield instance
    await instance.async_shutdown()


@pytest.mark.asyncio
async def test_latest_reply_is_separate_from_merged_data(coordinator, monkeypatch):
    exchange = Mock(side_effect=[
        '["SEC","2","B20364000000000003","B20199000000000070"]',
        '["SEC","1","I30001000000000000"]',
        TimeoutError("simulated timeout"),
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)

    await coordinator.async_refresh()
    assert coordinator._fresh_readings["20364"] == [3, "B"]

    await coordinator.async_refresh()
    assert coordinator._fresh_readings == {"30001": [0, "I"]}
    assert coordinator.data["20364"] == [3, "B"]

    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.failures == 1
    assert coordinator._fresh_readings == {}
    assert coordinator.data["30001"] == [0, "I"]
    assert coordinator.data["20199"] == [70, "B"]


@pytest.mark.asyncio
async def test_fallback_and_skipped_exchange_do_not_use_stale_registers(coordinator, monkeypatch):
    exchange = Mock(side_effect=[
        '["SEC","1","B20364000000000003"]',
        '["ERR"]',
        '["SEC","3","I30001000000000000","I30002000000000000","I30017000000000056"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    await coordinator.async_refresh()

    assert coordinator._fresh_readings == {
        "30001": [0, "I"], "30002": [0, "I"], "30017": [56, "I"],
    }
    assert coordinator.data["20364"] == [3, "B"]
    assert [call.args[0] for call in exchange.call_args_list] == [
        const.DATA_QUERY, const.DATA_QUERY, const.ERROR_QUERY,
    ]

    last_ok = coordinator.last_ok
    async with coordinator._lock:
        await coordinator.async_refresh()
    assert coordinator.last_ok == last_ok
    assert exchange.call_count == 3


@pytest.mark.asyncio
async def test_boiler_write_while_off_and_limits(coordinator, monkeypatch):
    exchange = Mock(side_effect=[
        '["SEC","1","I30001000000000000"]',
        '["SEC","0"]',
        '["SEC","3","B20199000000000070","B20206000000000075","B20005000000000062"]',
        '["SEC","0"]',
        '["SEC","3","B20199000000000075","B20205000000000076","B20206000000000075"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    assert coordinator.boiler_target_range == (60, 80)
    await coordinator.async_set_boiler_target(70)
    assert const.BOILER_TARGET_ID not in coordinator.data

    await coordinator.async_refresh()
    assert coordinator.boiler_target_range == (62, 75)
    for value in (59, 61, 76, 81, 70.5, "70.00000000000000000001", "NaN", True):
        with pytest.raises(ServiceValidationError):
            await coordinator.async_set_boiler_target(value)
    await coordinator.async_set_boiler_target(75.0)
    assert coordinator.data[const.BOILER_TARGET_ID] == [70, "B"]

    await coordinator.async_refresh()
    assert coordinator.boiler_target_range is None
    with pytest.raises(ServiceValidationError):
        await coordinator.async_set_boiler_target(75)
    assert [call.args[0] for call in exchange.call_args_list] == [
        const.DATA_QUERY, b'["SEC","1","B20199000000000070"]',
        const.DATA_QUERY, b'["SEC","1","B20199000000000075"]', const.DATA_QUERY,
    ]


@pytest.mark.asyncio
async def test_power_command_uses_fresh_marker_and_auto_mapping(coordinator, monkeypatch):
    exchange = Mock(side_effect=[
        '["SEC","2","B20364000000000003","I20199000000000072"]',
        '["SEC","0"]',
        '["SEC","2","B20364000000000007","I30001000000000000"]',
        '["SEC","0"]',
        '["SEC","1","J20364000000000004"]',
        '["SEC","1","I30002000000000000"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    assert not coordinator.boiler_target_range
    await coordinator.async_set_combustion_power(7)
    assert coordinator.data[const.POWER_TYPE] == [3, "B"]

    await coordinator.async_refresh()
    assert coordinator.data[const.POWER_TYPE] == [7, "B"]
    assert not coordinator.boiler_target_range  # Known non-B target stays protected while off.
    await coordinator.async_set_combustion_power(4)
    await coordinator.async_refresh()
    with pytest.raises(ServiceValidationError):
        await coordinator.async_set_combustion_power(5)
    await coordinator.async_refresh()
    with pytest.raises(ServiceValidationError):
        await coordinator.async_set_combustion_power(2)
    with pytest.raises(ServiceValidationError):
        await coordinator.async_set_boiler_target(70)

    assert [call.args[0] for call in exchange.call_args_list] == [
        const.DATA_QUERY, b'["SEC","1","B20364000000000006"]',
        const.DATA_QUERY, b'["SEC","1","B20364000000000004"]',
        const.DATA_QUERY, const.DATA_QUERY,
    ]


@pytest.mark.asyncio
async def test_waiting_command_rechecks_latest_eligibility(coordinator, monkeypatch):
    exchange = Mock(return_value='["SEC","1","B20364000000000003"]')
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    async with coordinator._lock:
        write = asyncio.create_task(coordinator.async_set_combustion_power(6))
        await asyncio.sleep(0)
        assert not write.done()
        coordinator._fresh_readings = {}
    with pytest.raises(ServiceValidationError):
        await write
    exchange.assert_called_once_with(const.DATA_QUERY)


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ['["ERR"]', "", TimeoutError("simulated")])
async def test_guarded_send_failure_keeps_reported_values_and_requests_refresh(
    coordinator, monkeypatch, reply,
):
    exchange = Mock(side_effect=[
        '["SEC","1","B20364000000000002"]', reply,
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    with pytest.raises(HomeAssistantError, match="did not accept or reply"):
        await coordinator.async_set_combustion_power(3)
    assert coordinator.data[const.POWER_TYPE] == [2, "B"]
    assert coordinator._confirm_unsub is not None
    assert coordinator.failures == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ['["ERR"]', ""])
async def test_legacy_send_ack_handling_is_unchanged(coordinator, monkeypatch, reply):
    exchange = Mock(side_effect=['["SEC","1","B20381000000000002"]', reply])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    assert await coordinator.async_set_value("20381", 3)
    assert coordinator.data["20381"] == [3, "B"]
    assert coordinator._confirm_unsub is not None


@pytest.mark.asyncio
async def test_boiler_opt_in_leaves_room_thermostat_and_probe_fallback_unchanged(
    coordinator, monkeypatch,
):
    exchange = Mock(side_effect=[
        '["SEC","2","I30006000000000000","J30138000000000020"]',
        '["SEC","2","I30006000000000021","J30138000000000020"]',
        '["SEC","2","I30006000000000029","J30138000000000038"]',
        '["SEC","2","I30006000000000022","J30138000000000020"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    thermostat = climate.FourHeatClimate(coordinator, "Test stove")

    await coordinator.async_refresh()
    assert thermostat.current_temperature == 0
    assert thermostat.target_temperature == 20
    await coordinator.async_refresh()
    assert thermostat.current_temperature == 21
    await coordinator.async_refresh()
    assert coordinator.probe_lost
    assert thermostat.current_temperature == 21
    assert thermostat.target_temperature == 20
    await coordinator.async_refresh()
    assert not coordinator.probe_lost
    assert thermostat.current_temperature == 22
    assert thermostat.target_temperature == 20
    assert [call.args[0] for call in exchange.call_args_list] == [const.DATA_QUERY] * 4
