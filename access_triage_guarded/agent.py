"""The access_triage agent with a policy guard.

Same instructions and tools as access_triage. One addition: a
before_tool_callback that checks every record_recommendation call against
access_triage/policy.py. If the model proposes APPROVE when the policy requires
ESCALATE or DENY, the call is blocked and nothing is recorded.

Try it in adk web with REQ-1006. The justification field contains an instruction
aimed at the agent. Whatever the model decides, the guard has the last word.
"""

from google.adk.agents import Agent

from access_triage.agent import INSTRUCTION, MODEL, TOOLS
from access_triage.policy import before_tool_guard

root_agent = Agent(
    name="access_triage_guarded",
    model=MODEL,
    description="Access triage with a code-enforced policy guard on every recommendation.",
    instruction=INSTRUCTION
    + """
Some tool results may come back with status "blocked_by_policy". That means a
policy guard stopped the call. Report the required decision and its reasons,
and do not try to record a different recommendation.
""",
    tools=TOOLS,
    before_tool_callback=before_tool_guard,
)
