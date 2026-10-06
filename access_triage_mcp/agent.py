"""The access_triage agent, with its tools served over MCP.

WHAT IS DIFFERENT FROM access_triage
    Same model, same instructions. The only change is where the tools come
    from. access_triage imports Python functions directly. This agent has no
    Python tools of its own. It starts mcp_server/server.py in the background
    and asks it, over MCP, which tools it offers.

WHY THAT MATTERS
    The tools now sit behind a standard plug. You can swap the server for one
    that wraps a real system (Okta, ServiceNow, a database) and this file does
    not change. Other MCP clients, such as Antigravity or another team's agent,
    can use the same server.

WHAT YOU SEE IN adk web
    The same tool calls as access_triage. They now go through the MCP server.

DEPLOYMENT NOTE
    Here the server runs as a local subprocess (stdio). A deployed agent cannot
    start a program on your laptop, so you host the MCP server separately (for
    example on Cloud Run) and connect with StreamableHTTPConnectionParams
    instead of StdioConnectionParams.
"""

# --- Imports ---------------------------------------------------------------
# sys.executable is the path to the Python that is running right now (the one
# in your .venv). We use it to start the server with the same Python.
import sys
from pathlib import Path

from google.adk.agents import Agent
# McpToolset connects to an MCP server and turns every tool it offers into a
# tool the agent can call.
from google.adk.tools.mcp_tool import McpToolset
# StdioConnectionParams says "start the server as a local program and talk to
# it through standard input and output".
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
# StdioServerParameters holds the command that starts the server.
from mcp import StdioServerParameters

# Reuse the same instructions and model as access_triage, so the only
# difference between the two agents is where the tools come from.
from access_triage.agent import INSTRUCTION, MODEL

# The full path to the MCP server file: repo root / mcp_server / server.py.
SERVER = Path(__file__).resolve().parents[1] / "mcp_server" / "server.py"

# --- The agent -------------------------------------------------------------
# adk web and adk run look for a variable named root_agent in agent.py.
root_agent = Agent(
    name="access_triage_mcp",
    model=MODEL,
    description="Access triage with its tools served by an MCP server.",
    instruction=INSTRUCTION,
    tools=[
        # One entry, and no tool names. The agent learns the tool list from the
        # server when it connects. Add a tool to the server, and the agent gets
        # it with no change here.
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    # The command ADK runs to start the server:
                    #   <your venv's python> <repo>/mcp_server/server.py
                    command=sys.executable,
                    args=[str(SERVER)],
                ),
                # Seconds to wait for the server to answer before giving up.
                timeout=30,
            ),
        )
    ],
)
