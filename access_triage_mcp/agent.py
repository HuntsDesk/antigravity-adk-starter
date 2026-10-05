"""The access_triage agent, with its tools served over MCP.

Same instructions as access_triage. The difference: the agent has no Python
tools of its own. It starts mcp_server/server.py as a subprocess and gets the
tools from it over the Model Context Protocol (stdio transport).

In adk web, the event trace shows the same tool calls as access_triage. The
tools now live behind a protocol boundary, so you can swap the server for a real
system without touching the agent.

Deployment note: stdio servers run as a local subprocess. For a deployed agent,
host the MCP server separately and connect with StreamableHTTPConnectionParams.
"""

import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from access_triage.agent import INSTRUCTION, MODEL

SERVER = Path(__file__).resolve().parents[1] / "mcp_server" / "server.py"

root_agent = Agent(
    name="access_triage_mcp",
    model=MODEL,
    description="Access triage with its tools served by an MCP server.",
    instruction=INSTRUCTION,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,
                    args=[str(SERVER)],
                ),
                timeout=30,
            ),
        )
    ],
)
