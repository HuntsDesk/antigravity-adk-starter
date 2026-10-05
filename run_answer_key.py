"""Run the five answer-key requests through an agent and print tool calls + answers.

Usage (repo root, venv active, env vars set):
  python run_answer_key.py access_triage
  python run_answer_key.py access_triage_panel REQ-1003
"""
import asyncio
import importlib
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

REQUESTS = ["REQ-1001", "REQ-1002", "REQ-1003", "REQ-1004", "REQ-1005", "REQ-1006"]


async def run(pkg: str, ids: list[str]) -> None:
    agent = importlib.import_module(f"{pkg}.agent").root_agent
    runner = InMemoryRunner(agent=agent, app_name=pkg)
    for rid in ids:
        print(f"\n===== {pkg} :: {rid} =====")
        session = await runner.session_service.create_session(app_name=pkg, user_id="tester")
        msg = types.Content(role="user", parts=[types.Part(text=f"Triage access request {rid}.")])
        async for ev in runner.run_async(user_id="tester", session_id=session.id, new_message=msg):
            if not ev.content or not ev.content.parts:
                continue
            for part in ev.content.parts:
                if part.function_call:
                    print(f"  [{ev.author}] CALL {part.function_call.name}({dict(part.function_call.args or {})})")
                elif part.text and not ev.partial:
                    print(f"[{ev.author}]\n{part.text.strip()}\n")


if __name__ == "__main__":
    pkg = sys.argv[1] if len(sys.argv) > 1 else "access_triage"
    ids = sys.argv[2:] or REQUESTS
    asyncio.run(run(pkg, ids))
