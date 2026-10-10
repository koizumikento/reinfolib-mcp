"""Synthetic HTTP contract checks; never contacts MLIT or Sites."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from starlette.testclient import TestClient

from reinfolib_mcp.client import API_CONTRACTS, ReinfiolibClient
from reinfolib_mcp.mcp_server import create_mcp_server
from reinfolib_mcp.sites_backend import ServiceTokenVerifier, create_app

TOKEN = "synthetic-service-token-for-tests-only"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-03-26",
}


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("REINFOLIB_BACKEND_TOKEN", TOKEN)
    monkeypatch.setenv("REINFOLIB_BACKEND_HOST", "testserver")
    monkeypatch.setenv("REINFOLIB_API_KEY", "synthetic-api-key")


def rpc(client, method, params=None):
    return client.post(
        "/mcp",
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


@pytest.mark.asyncio
async def test_service_token():
    verifier = ServiceTokenVerifier(TOKEN)
    assert await verifier.verify_token("wrong") is None
    token = await verifier.verify_token(TOKEN)
    assert token.client_id == "sites-worker"
    assert token.subject is None
    with pytest.raises(ValueError, match="32 characters"):
        ServiceTokenVerifier("short")


def test_backend_fail_closed(configured, monkeypatch):
    monkeypatch.delenv("REINFOLIB_BACKEND_TOKEN")
    with pytest.raises(KeyError):
        create_app()


def test_backend_authorization_and_protocol(configured):
    with TestClient(create_app()) as client:
        assert client.post("/mcp", json={}).status_code == 401
        assert (
            client.post(
                "/mcp", json={}, headers={**HEADERS, "Authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/mcp",
                json={},
                headers={**HEADERS, "Origin": "https://attacker.invalid"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/mcp", json={}, headers={**HEADERS, "Host": "attacker.invalid"}
            ).status_code
            == 421
        )
        initialized = rpc(
            client,
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "fixture", "version": "1"},
            },
        )
        assert initialized.status_code == 200
        assert "tools" in initialized.json()["result"]["capabilities"]
        assert "mcp-session-id" not in initialized.headers
        assert rpc(client, "ping").json()["result"] == {}
        assert len(rpc(client, "tools/list").json()["result"]["tools"]) == 13
        invalid = rpc(client, "tools/call", {"name": "reinfolib_get_api_data"})
        assert invalid.json()["result"]["isError"]
        assert rpc(client, "unknown").json()["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_backend_matches_python_discovery(configured):
    expected = [
        tool.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
        for tool in await create_mcp_server("synthetic").list_tools()
    ]
    with TestClient(create_app()) as client:
        tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert tools == expected


@pytest.mark.parametrize("api_id", list(API_CONTRACTS))
def test_all_api_contracts_over_http(configured, api_id):
    contract = API_CONTRACTS[api_id]
    values = {
        "year": 2025,
        "area": "13",
        "division": "00",
        "response_format": "geojson",
        "z": 14,
        "x": 14624,
        "y": 6016,
        "from": "20251",
        "to": "20252",
    }
    parameters = {key: values[key] for key in contract.required}
    if contract.one_of:
        parameters["area"] = "13"
    fixture = {"type": "FeatureCollection", "features": [], "source": api_id}
    upstream = AsyncMock(return_value=fixture)
    with patch.object(ReinfiolibClient, "_make_request", upstream):
        with TestClient(create_app()) as client:
            result = rpc(
                client,
                "tools/call",
                {
                    "name": "reinfolib_get_api_data",
                    "arguments": {"api_id": api_id, "parameters": parameters},
                },
            ).json()["result"]
    assert not result.get("isError", False)
    assert json.loads(result["content"][0]["text"]) == fixture
    upstream.assert_awaited_once_with(f"/{api_id}", parameters)


@pytest.mark.parametrize(
    "status,error_type",
    [(401, "AuthenticationError"), (429, "RateLimitError"), (500, "ServerError")],
)
def test_upstream_errors_preserved(configured, status, error_type):
    response = httpx.Response(status)
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=response)):
        with TestClient(create_app()) as client:
            result = rpc(
                client,
                "tools/call",
                {
                    "name": "reinfolib_get_api_data",
                    "arguments": {"api_id": "XIT002", "parameters": {"area": "13"}},
                },
            ).json()["result"]
    assert json.loads(result["content"][0]["text"])["error_type"] == error_type
    assert TOKEN not in json.dumps(result)


def test_binary_tile_over_http(configured):
    response = httpx.Response(200, content=b"\x00\xff\x80tile")
    with patch("httpx.AsyncClient.get", AsyncMock(return_value=response)):
        with TestClient(create_app()) as client:
            result = rpc(
                client,
                "tools/call",
                {
                    "name": "reinfolib_get_api_data",
                    "arguments": {
                        "api_id": "XKT026",
                        "parameters": {
                            "response_format": "pbf",
                            "z": 14,
                            "x": 14624,
                            "y": 6016,
                        },
                    },
                },
            ).json()["result"]
    assert not result.get("isError", False), result
    tile = json.loads(result["content"][0]["text"])
    assert tile == {"format": "pbf", "data": "AP+AdGlsZQ==", "encoding": "base64"}


@pytest.mark.asyncio
async def test_library_preserves_binary_tile():
    binary = b"\x00\xff\x80tile"
    with patch(
        "httpx.AsyncClient.get",
        AsyncMock(return_value=httpx.Response(200, content=binary)),
    ):
        async with ReinfiolibClient("synthetic-api-key") as api:
            result = await api.request_api(
                "XKT026", response_format="pbf", z=14, x=14624, y=6016
            )
    assert result == {"format": "pbf", "data": binary}


def test_backend_closes_upstream_client(configured):
    close = AsyncMock()
    with patch.object(ReinfiolibClient, "close", close):
        with TestClient(create_app()) as client:
            assert rpc(client, "ping").status_code == 200
    close.assert_awaited_once()
