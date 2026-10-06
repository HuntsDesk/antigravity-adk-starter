"""Run the six answer-key requests through an agent and print tool calls + answers.

Usage (repo root, venv active, env vars set):
  python run_answer_key.py access_triage
  python run_answer_key.py access_triage_panel REQ-1003

WHAT THIS SHOWS
    A fourth way to run an agent: from your own Python code, with a Runner.
    adk web and adk run use a Runner too, behind the scenes. Here you drive it
    yourself, which is how you would run an agent from a script, a test, a
    scheduled job or another program.
"""
import asyncio
import importlib
import sys

from dotenv import load_dotenv
# InMemoryRunner runs an agent and keeps its sessions in memory (lost on exit).
from google.adk.runners import InMemoryRunner
# types holds the message format the model uses (Content made of Parts).
from google.genai import types

load_dotenv()  # read GOOGLE_CLOUD_PROJECT etc. from the repo-root .env, like adk web does

# The six test requests. Compare the answers with the answer key in the README.
REQUESTS = ["REQ-1001", "REQ-1002", "REQ-1003", "REQ-1004", "REQ-1005", "REQ-1006"]


async def run(pkg: str, ids: list[str]) -> None:
    # Load <pkg>/agent.py and take its root_agent, the same way adk web does.
    agent = importlib.import_module(f"{pkg}.agent").root_agent
    runner = InMemoryRunner(agent=agent, app_name=pkg)
    for rid in ids:
        print(f"\n===== {pkg} :: {rid} =====")
        # A new session for each request, so one answer cannot affect the next.
        # This is the same as clicking New Session in adk web.
        session = await runner.session_service.create_session(app_name=pkg, user_id="tester")
        # The user message, exactly as you would type it in adk web.
        msg = types.Content(role="user", parts=[types.Part(text=f"Triage access request {rid}.")])
        # run_async streams events: the same events adk web lists on the left.
        async for ev in runner.run_async(user_id="tester", session_id=session.id, new_message=msg):
            if not ev.content or not ev.content.parts:
                continue
            for part in ev.content.parts:
                # A function_call part is the model asking for a tool.
                if part.function_call:
                    print(f"  [{ev.author}] CALL {part.function_call.name}({dict(part.function_call.args or {})})")
                # A text part is the model's answer. Skip partial (streaming) pieces.
                elif part.text and not ev.partial:
                    print(f"[{ev.author}]\n{part.text.strip()}\n")


if __name__ == "__main__":
    # First argument: the agent folder (default access_triage).
    # Any more arguments: the request IDs to run (default all six).
    pkg = sys.argv[1] if len(sys.argv) > 1 else "access_triage"
    ids = sys.argv[2:] or REQUESTS
    asyncio.run(run(pkg, ids))
