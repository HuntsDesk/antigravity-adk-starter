"""A small MCP server that serves the Cymbal access tools.

WHAT THIS FILE DOES, IN ONE SENTENCE
    It takes the plain Python functions in access_triage/tools.py and offers
    them to any AI app through MCP (the Model Context Protocol).

WHERE THE TOOL DETAILS LIVE
    Not here. This file holds no tool logic at all. Everything about each tool
    lives in access_triage/tools.py:
      - the name           -> the function name (get_employee)
      - the inputs         -> the parameters and their type hints (email: str)
      - the description    -> the docstring (the text in triple quotes)
      - what it does       -> the function body
      - the data it reads  -> the JSON files in access_triage/data/
    This file only wraps those functions so they can be reached over MCP.

HOW IT IS USED IN THIS REPO
    You never start this file yourself in the session. The agent in
    access_triage_mcp/agent.py starts it in the background and talks to it.
    You can run it on its own to check it starts (it then waits for a client):
        python mcp_server/server.py

IN A REAL PROJECT
    This is where you would wrap your own system: an internal API, a ticketing
    tool, a database. The agent does not change.
"""

# --- Imports ---------------------------------------------------------------
# importlib.util lets us load a Python file by its path (see Step 1).
import importlib.util
# Path builds file paths that work on Mac, Windows and Linux.
from pathlib import Path

# FastMCP is a small library that turns Python functions into MCP tools.
# It handles the protocol for us, so this file stays short.
from mcp.server.fastmcp import FastMCP

# --- Step 1: load the tool functions ---------------------------------------
# Find access_triage/tools.py. __file__ is this file, parents[1] is the repo
# root, and from there we walk to access_triage/tools.py.
_TOOLS_PATH = Path(__file__).resolve().parents[1] / "access_triage" / "tools.py"

# Load that file as a module named "tools". We load it by path, not with a
# normal "import access_triage.tools", because a normal import would also load
# access_triage/agent.py and the whole ADK framework. The server only needs the
# plain functions, so it stays small and fast to start.
_spec = importlib.util.spec_from_file_location("cymbal_tools", _TOOLS_PATH)
tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tools)
# From here on, tools.get_employee, tools.get_app_policy and so on are the same
# functions the access_triage agent calls directly.

# --- Step 2: create the MCP server -----------------------------------------
# "cymbal-access" is the server's name. MCP clients see it when they connect.
mcp = FastMCP("cymbal-access")

# --- Step 3: register each function as an MCP tool -------------------------
# This is the list of tools the server offers. To offer a new tool, write the
# function in access_triage/tools.py, then add its name here.
for name in (
    "get_access_request",
    "get_employee",
    "get_app_policy",
    "check_sod_conflicts",  # not on the live-start branch until you add it in Play 3
    "record_recommendation",
):
    # Skip any name that does not exist yet. On the live-start branch,
    # check_sod_conflicts does not exist until Antigravity writes it in Play 3.
    # After that, the server serves it with no change to this file.
    if not hasattr(tools, name):
        continue
    fn = getattr(tools, name)
    # Register the function. FastMCP reads the function name, the type hints
    # and the docstring, and builds the tool description that clients see.
    # This is the same thing ADK does for function tools, so the model sees the
    # same description either way.
    mcp.tool()(fn)

# --- Step 4: start the server ----------------------------------------------
# This runs only when the file is started as a program (python server.py or
# when access_triage_mcp starts it), not when another file imports it.
# "stdio" means the server talks through its standard input and output, like a
# command-line program. The client starts it as a subprocess and they exchange
# messages that way. A deployed server would use HTTP instead.
if __name__ == "__main__":
    mcp.run()  # stdio transport by default
