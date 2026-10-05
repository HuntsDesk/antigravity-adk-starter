"""Checks that the MCP server exposes all five tools and that a call works.
Skipped if the mcp package is not installed.
"""
import asyncio
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("mcp")

SERVER = Path(__file__).resolve().parents[1] / "mcp_server" / "server.py"


def _load_server():
    spec = importlib.util.spec_from_file_location("cymbal_mcp_server", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_server_lists_all_tools():
    server = _load_server()
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {
        "get_access_request",
        "get_employee",
        "get_app_policy",
        "check_sod_conflicts",
        "record_recommendation",
    }


def test_server_tool_call_returns_data():
    server = _load_server()
    result = asyncio.run(server.mcp.call_tool("get_access_request", {"request_id": "REQ-1003"}))
    assert "tomas.reyes" in str(result)
