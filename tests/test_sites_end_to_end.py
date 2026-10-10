"""Real loopback HTTP + SDK + Worker; identity/upstream are synthetic."""

import asyncio
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastmcp import Client

from reinfolib_mcp.client import API_CONTRACTS

BACKEND_FIXTURE = """
from unittest.mock import patch
import httpx
import uvicorn
from reinfolib_mcp.sites_backend import create_app
async def fixture_get(self, url, **kwargs):
    if kwargs['params'].get('response_format') == 'pbf':
        return httpx.Response(200, content=b'\\x00\\xff\\x80tile')
    return httpx.Response(200, json={'type': 'FeatureCollection', 'features': [],
                                   'source': 'synthetic-2026-10-10', 'data': []})
with patch('httpx.AsyncClient.get', fixture_get):
    uvicorn.run(create_app, factory=True, host='127.0.0.1',
                port=int(__import__('os').environ['FIXTURE_BACKEND_PORT']),
                access_log=False, log_level='error')
"""


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_worker_backend_sdk_and_cleanup():
    node = shutil.which("node")
    assert node, "Node.js 22+ is required for the Sites integration check"
    backend_port, gateway_port = free_port(), free_port()
    env = {
        **os.environ,
        "REINFOLIB_API_KEY": "synthetic-api-key",
        "REINFOLIB_BACKEND_TOKEN": "synthetic-service-token-for-tests-only",
        "REINFOLIB_BACKEND_HOST": f"127.0.0.1:{backend_port}",
        "FIXTURE_BACKEND_PORT": str(backend_port),
        "FIXTURE_GATEWAY_PORT": str(gateway_port),
        "PYTHONUTF8": "1",
    }
    root = Path(__file__).resolve().parents[1]
    processes = []
    try:
        for command in [
            [sys.executable, "-c", BACKEND_FIXTURE],
            [node, str(root / "sites/tests/local-gateway.mjs")],
        ]:
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
        async with httpx.AsyncClient() as probe:
            for _ in range(100):
                assert all(p.poll() is None for p in processes)
                try:
                    responses = await asyncio.gather(
                        *[
                            probe.get(f"http://127.0.0.1:{port}/mcp")
                            for port in [backend_port, gateway_port]
                        ]
                    )
                    if all(r.status_code < 500 for r in responses):
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(0.1)
            else:
                pytest.fail("Fixture HTTP processes did not start")
        for mode in ["auto", "legacy"]:
            async with Client(
                f"http://127.0.0.1:{gateway_port}/mcp", mode=mode
            ) as client:
                assert client.protocol_version == (
                    "2026-07-28" if mode == "auto" else "2025-11-25"
                )
                assert len(await client.list_tools()) == 13
                status = await client.call_tool("reinfolib_server_status", {})
                assert status.data["available_endpoints"] == 35
                assert set(status.data["endpoints"]) == set(API_CONTRACTS)
                tile = await client.call_tool(
                    "reinfolib_get_api_data",
                    {
                        "api_id": "XKT026",
                        "parameters": {
                            "response_format": "pbf",
                            "z": 14,
                            "x": 14624,
                            "y": 6016,
                        },
                    },
                )
                assert tile.data == {
                    "format": "pbf",
                    "data": "AP+AdGlsZQ==",
                    "encoding": "base64",
                }
                geo = await client.call_tool(
                    "reinfolib_get_geospatial_data",
                    {
                        "latitude": 35.6851,
                        "longitude": 139.7514,
                        "year": 2025,
                        "response_format": "pbf",
                    },
                )
                assert geo.data["data"]["land_price"] == tile.data
                invalid = await client.call_tool(
                    "reinfolib_get_api_data",
                    {
                        "api_id": "PRIVATE",
                        "parameters": {},
                    },
                )
                assert invalid.data["error_type"] == "InvalidParameterError"
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            assert process.poll() is not None
