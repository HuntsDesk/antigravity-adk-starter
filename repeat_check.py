"""Run one request N times and count the recommendations. Use it to see how stable a demo beat is.

Usage (repo root, venv active, env vars set):
  python repeat_check.py access_triage REQ-1003 10

WHY THIS EXISTS
    Models do not always give the same answer to the same question. Before you
    rely on a result in a demo or in production, run it many times and count.
    If 9 runs out of 10 agree, you know the tenth can happen in front of people.
"""
import asyncio
import collections
import importlib
import sys

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv()  # read GOOGLE_CLOUD_PROJECT etc. from the repo-root .env, like adk web does


async def run(pkg: str, rid: str, n: int) -> None:
    # Load the agent the same way adk web does (see run_answer_key.py).
    agent = importlib.import_module(f"{pkg}.agent").root_agent
    runner = InMemoryRunner(agent=agent, app_name=pkg)
    # Counter keeps a running total, for example {"ESCALATE": 9, "APPROVE": 1}.
    tally = collections.Counter()
    for i in range(n):
        # A fresh session every run, so no run remembers the one before.
        session = await runner.session_service.create_session(app_name=pkg, user_id="tester")
        msg = types.Content(role="user", parts=[types.Part(text=f"Triage access request {rid}.")])
        rec, mentions_sod = "NONE", False
        async for ev in runner.run_async(user_id="tester", session_id=session.id, new_message=msg):
            for part in (ev.content.parts if ev.content else []) or []:
                # The recommendation is the argument the model passed to
                # record_recommendation, not the wording of its final answer.
                if part.function_call and part.function_call.name == "record_recommendation":
                    rec = str((part.function_call.args or {}).get("recommendation", "?")).upper()
                # Also note whether the answer mentions the SoD conflict at all.
                if part.text and not ev.partial:
                    t = part.text.lower()
                    mentions_sod = mentions_sod or "vendor-master-edit" in t or "separation" in t
        tally[rec] += 1
        print(f"run {i + 1}: {rec}{'  (mentions vendor-master-edit / separation of duties)' if mentions_sod else ''}")
    print("\nTotals:", dict(tally))


if __name__ == "__main__":
    # Arguments: agent folder, request ID, and how many runs (default 10).
    asyncio.run(run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10))
