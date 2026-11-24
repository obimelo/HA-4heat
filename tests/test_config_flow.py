"""Verify connection validation, retry errors, and existing host handling."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from homeassistant.const import CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_NAME
from homeassistant.core import HomeAssistant
import pytest

config_flow = import_module("custom_components.4heat.config_flow")
const = import_module("custom_components.4heat.const")
transport = import_module("custom_components.4heat.transport")
HOST = "simulated.invalid"
INPUT = {CONF_NAME: "Test Stove", CONF_HOST: HOST}


def make_flow(tmp_path, entries=()):
    flow = config_flow.FourHeatConfigFlow()
    flow.hass = HomeAssistant(str(tmp_path))
    flow.hass.config_entries = SimpleNamespace(async_entries=Mock(return_value=entries))
    flow.flow_id = "test-config"
    flow.handler = const.DOMAIN
    return flow


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["", '["SEC","0"]', '["not","a","stove","reply"]'])
async def test_setup_rejects_empty_or_malformed_reply_and_clears_retry_error(tmp_path, monkeypatch, reply):
    exchange = Mock(side_effect=[reply, '[ "SEC", "1", "B20364000000000003" ]'])
    monkeypatch.setattr(config_flow, "exchange", exchange)
    flow = make_flow(tmp_path)

    result = await flow.async_step_user(INPUT)
    assert result["errors"] == {CONF_HOST: "cannot_connect"}
    assert result["data_schema"]({})[CONF_HOST] == HOST

    result = await flow.async_step_user(INPUT)
    assert result["data"] == {
        CONF_HOST: HOST,
        const.CONF_MODE: False,
        CONF_MONITORED_CONDITIONS: ["B20364000000000003"],
    }
    assert [call.args for call in exchange.call_args_list] == [(HOST, const.DATA_QUERY)] * 2


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [ConnectionRefusedError(), TimeoutError(), b"\xff"])
async def test_socket_failure_is_translated_and_connection_is_closed(tmp_path, monkeypatch, failure):
    factory = MagicMock()
    socket = factory.return_value.__enter__.return_value
    if isinstance(failure, OSError):
        socket.connect.side_effect = failure
    else:
        socket.recv.return_value = failure
    monkeypatch.setattr(transport.socket, "socket", factory)

    result = await make_flow(tmp_path).async_step_user(INPUT)
    assert result["errors"] == {CONF_HOST: "cannot_connect"}
    socket.connect.assert_called_once_with((HOST, const.TCP_PORT))
    factory.return_value.__exit__.assert_called_once()


@pytest.mark.asyncio
async def test_import_uses_only_the_fixed_fallback_on_err(tmp_path, monkeypatch):
    exchange = Mock(side_effect=['["ERR"]', '["SEC","1","I30001000000000000"]'])
    monkeypatch.setattr(config_flow, "exchange", exchange)
    result = await make_flow(tmp_path).async_step_import(INPUT)
    assert result["data"][CONF_MONITORED_CONDITIONS] == ["I30001000000000000"]
    assert [call.args for call in exchange.call_args_list] == [
        (HOST, const.DATA_QUERY), (HOST, const.ERROR_QUERY),
    ]


@pytest.mark.asyncio
async def test_invalid_fallback_is_rejected_without_retrying(tmp_path, monkeypatch):
    exchange = Mock(side_effect=['["ERR"]', '["SEC","1","B2036400000000000x"]'])
    monkeypatch.setattr(config_flow, "exchange", exchange)
    assert (await make_flow(tmp_path).async_step_user(INPUT))["errors"] == {
        CONF_HOST: "cannot_connect",
    }
    assert exchange.call_count == 2


@pytest.mark.asyncio
async def test_duplicate_stove_does_not_probe(tmp_path, monkeypatch):
    exchange = Mock()
    monkeypatch.setattr(config_flow, "exchange", exchange)
    flow = make_flow(tmp_path, [SimpleNamespace(data={CONF_HOST: HOST})])
    assert (await flow.async_step_user(INPUT))["errors"] == {CONF_HOST: "host_exists"}
    assert (await flow.async_step_import(INPUT))["reason"] == "host_exists"
    exchange.assert_not_called()
