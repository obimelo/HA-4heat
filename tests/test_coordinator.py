"""Verify coordinator behavior with synthetic TCP replies only."""

import asyncio
from importlib import import_module
from unittest.mock import AsyncMock, Mock

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
import pytest_asyncio

const = import_module("custom_components.4heat.const")
coordinator_module = import_module("custom_components.4heat.coordinator")
climate = import_module("custom_components.4heat.climate")
switch = import_module("custom_components.4heat.switch")
number = import_module("custom_components.4heat.number")
select = import_module("custom_components.4heat.select")
sensor = import_module("custom_components.4heat.sensor")


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


@pytest.fixture
def control_feedback(coordinator, monkeypatch):
    """Capture notification and timer changes without waiting on wall time."""
    timers = {}

    def schedule(_hass, delay, callback):
        key = object()
        timers[key] = (delay, callback)

        def cancel():
            timers.pop(key, None)

        return cancel

    monkeypatch.setattr(coordinator_module, "async_call_later", schedule)
    refresh = AsyncMock(wraps=coordinator.async_refresh)
    monkeypatch.setattr(coordinator, "async_request_refresh", refresh)
    create = Mock()
    monkeypatch.setattr(coordinator_module.persistent_notification, "async_create", create)
    return timers, refresh, create


def take_check(timers, delay):
    key = next(key for key, (seconds, _) in timers.items() if seconds == delay)
    return timers.pop(key)[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("ack", ['["SEC","0"]', '["ERR"]', TimeoutError("send timeout")])
async def test_matching_readback_clears_assumption_without_notifying(
    coordinator, monkeypatch, control_feedback, ack,
):
    timers, refresh, create = control_feedback
    original = '["SEC","1","B20364000000000003"]'
    applied = '["SEC","1","B20364000000000007"]'
    exchange = Mock(side_effect=[original, ack, original, applied])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    entity = select.FourHeatCombustionPower(coordinator, "Test stove")
    reported = sensor.FourHeatDevice(coordinator, const.POWER_TYPE, "Test stove")
    published = []
    unsubscribe = coordinator.async_add_listener(lambda: published.append((entity.current_option, reported.native_value)))
    try:
        await entity.async_select_option("Auto")
        assert published == [("Auto", "P3")]
    finally:
        unsubscribe()
    create.assert_not_called()
    assert coordinator.data[const.POWER_TYPE] == [3, "B"]
    await coordinator.async_set_combustion_power(7)
    assert exchange.call_count == 2  # Re-selecting the pending option is not another write.

    await coordinator.async_refresh()  # A routine poll may still see the old value.
    assert (entity.current_option, reported.native_value) == ("Auto", "P3")
    create.assert_not_called()
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    assert coordinator.data[const.POWER_TYPE] == [7, "B"]
    assert coordinator.assumed_control_value(const.POWER_TYPE) is None
    assert (entity.current_option, reported.native_value) == ("Auto", "Auto")
    refresh.assert_awaited_once()
    create.assert_not_called()
    assert not timers


@pytest.mark.asyncio
@pytest.mark.parametrize("ack", ['["SEC","0"]', '["ERR"]', "", TimeoutError("send timeout")])
async def test_notify_only_after_readback_confirms_a_mismatch(
    coordinator, monkeypatch, control_feedback, ack,
):
    timers, refresh, create = control_feedback
    exchange = Mock(side_effect=[
        '["SEC","1","B20364000000000003"]', ack, '["SEC","1","B20364000000000002"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    entity = select.FourHeatCombustionPower(coordinator, "Test stove")
    await entity.async_select_option("Auto")
    assert entity.current_option == "Auto"
    create.assert_not_called()
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    assert entity.current_option == "P2"
    refresh.assert_awaited_once()
    create.assert_called_once()
    assert "Requested **Auto**, but the stove reports **P2**" in create.call_args.args[1]
    assert [call.args[0] for call in exchange.call_args_list] == [
        const.DATA_QUERY, b'["SEC","1","B20364000000000006"]', const.DATA_QUERY,
    ]
    assert not timers


@pytest.mark.asyncio
@pytest.mark.parametrize("readback", [
    (TimeoutError("read timeout"),),
    ('["SEC","1","I30001000000000000"]',),
    ('["ERR"]', '["ERR","B20364000000000003"]'),
    (),
])
async def test_unverified_value_is_removed_without_a_mismatch_notice(
    coordinator, monkeypatch, control_feedback, readback,
):
    timers, refresh, create = control_feedback
    exchange = Mock(side_effect=['["SEC","1","B20364000000000003"]', '["SEC","0"]', *readback])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    if not readback:
        monkeypatch.setattr(coordinator, "async_request_refresh", AsyncMock())  # Deferred by HA.
    await coordinator.async_refresh()
    entity = select.FourHeatCombustionPower(coordinator, "Test stove")
    await entity.async_select_option("Auto")
    assert entity.current_option == "Auto"
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    if not readback:
        assert entity.current_option == "Auto"
        await take_check(timers, coordinator_module.CONTROL_CONFIRM_TIMEOUT)(None)
        refresh.assert_not_awaited()
    assert entity.current_option == "P3"
    create.assert_not_called()
    assert not timers


@pytest.mark.asyncio
async def test_new_power_request_replaces_pending_feedback_and_unload_stops_checks(
    coordinator, monkeypatch, control_feedback,
):
    timers, refresh, create = control_feedback
    exchange = Mock(side_effect=['["SEC","1","B20364000000000003"]', '["SEC","0"]', '["SEC","0"]'])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    await coordinator.async_set_combustion_power(6)
    old_check = take_check(timers, coordinator_module.CONFIRM_DELAY)
    await coordinator.async_set_combustion_power(5)
    await old_check(None)
    refresh.assert_not_awaited()
    assert coordinator.assumed_control_value(const.POWER_TYPE) == 5

    check = take_check(timers, coordinator_module.CONFIRM_DELAY)
    await coordinator.async_shutdown()
    await check(None)
    refresh.assert_not_awaited()
    assert not timers
    create.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action,args,assumed,frame,before,after",
    [
        ("async_set_native_value", (70,), 70, b'["SEC","1","B20199000000000070"]',
         "B20199000000000063", "B20199000000000070"),
        ("async_turn_on", (), True, const.ON_CMD,
         "I30001000000000000", "I30001000000000002"),
        ("async_turn_off", (), False, const.OFF_CMD,
         "I30001000000000005", "I30001000000000007"),
        ("async_turn_off", (), False, const.UNBLOCK_CMD,
         "I30002000000000012", "I30002000000000000"),
    ],
)
async def test_other_controls_confirm_only_from_fresh_readings(
    coordinator, monkeypatch, control_feedback, action, args, assumed, frame, before, after,
):
    timers, refresh, create = control_feedback
    exchange = Mock(side_effect=[f'["SEC","1","{before}"]', '["SEC","0"]', f'["SEC","1","{after}"]'])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    reading_id = before[1:6]
    if reading_id in (const.MODE_TYPE, const.ERROR_TYPE):
        entity = switch.FourHeatSwitch(coordinator, reading_id, "Test stove")
        attribute = "is_on"
    else:
        entity = number.FourHeatBoilerTarget(coordinator, "Test stove")
        attribute = "native_value"
    assert getattr(entity, attribute) != assumed
    await getattr(entity, action)(*args)
    assert getattr(entity, attribute) == assumed
    create.assert_not_called()
    assert coordinator.data[reading_id][0] == int(before[7:])
    refresh.assert_not_awaited()
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    assert coordinator.data[reading_id][0] == int(after[7:])
    assert getattr(entity, attribute) == assumed
    assert coordinator.assumed_control_value(reading_id) is None
    create.assert_not_called()
    assert not timers
    refresh.assert_awaited_once()
    assert [call.args[0] for call in exchange.call_args_list] == [
        const.DATA_QUERY, frame, const.DATA_QUERY,
    ]


@pytest.mark.asyncio
async def test_one_control_confirming_does_not_cancel_other_checks(coordinator, monkeypatch, control_feedback):
    timers, _, create = control_feedback
    exchange = Mock(side_effect=[
        '["SEC","2","I30001000000000005","I30002000000000012"]',
        '["SEC","0"]', '["SEC","0"]', '["SEC","1","I30001000000000007"]',
        '["SEC","1","I30002000000000000"]',
    ])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    await coordinator.async_refresh()
    await coordinator.async_turn_off()
    await coordinator.async_unblock()
    assert len(timers) == 4
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    assert set(coordinator._confirmations) == {const.ERROR_TYPE}
    assert len(timers) == 2
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    create.assert_not_called()
    assert not timers


@pytest.mark.asyncio
async def test_rejected_switch_command_has_no_pending_notice(coordinator, monkeypatch, control_feedback):
    timers, _, create = control_feedback
    exchange = Mock(side_effect=['["ERR"]', '["SEC","1","I30001000000000007"]'])
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    assert not await coordinator.async_turn_off()
    exchange.assert_called_once_with(const.OFF_CMD)
    await take_check(timers, coordinator_module.CONFIRM_DELAY)(None)
    assert coordinator.assumed_control_value(const.MODE_TYPE) is None
    create.assert_not_called()


@pytest.mark.asyncio
async def test_clear_error_turn_on_only_refreshes(coordinator, monkeypatch, control_feedback):
    timers, refresh, create = control_feedback
    exchange = Mock(return_value='["SEC","1","I30002000000000000"]')
    monkeypatch.setattr(coordinator, "_exchange", exchange)
    entity = switch.FourHeatSwitch(coordinator, const.ERROR_TYPE, "Test stove")
    await entity.async_turn_on()
    refresh.assert_awaited_once()
    exchange.assert_called_once_with(const.DATA_QUERY)
    create.assert_not_called()
    assert not timers


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
