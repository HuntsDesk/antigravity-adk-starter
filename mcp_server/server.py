"""A small MCP server that serves the Cymbal access tools.

The same five Python functions the access_triage agent calls directly are served
here over the Model Context Protocol. Any MCP client can now use them: the ADK
agent in access_triage_mcp, Antigravity, or another team's agent.

Run it on its own (it speaks MCP over stdio, so it waits for a client):
    python mcp_server/server.py

In a real project, this is where you would wrap your own system: an internal
API, a ticketing tool, a database. The agent does not change.
"""

import importlib.util
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Load access_triage/tools.py directly, so the server does not import ADK.
_TOOLS_PATH = Path(__file__).resolve().parents[1] / "access_triage" / "tools.py"
_spec = importlib.util.spec_from_file_location("cymbal_tools", _TOOLS_PATH)
tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tools)

mcp = FastMCP("cymbal-access")

for fn in (
    tools.get_access_request,
    tools.get_employee,
    tools.get_app_policy,
    tools.check_sod_conflicts,
    tools.record_recommendation,
):
    # FastMCP builds each tool's schema from the type hints and docstring,
    # the same way ADK does for function tools.
    mcp.tool()(fn)

if __name__ == "__main__":
    mcp.run()  # stdio transport by default
