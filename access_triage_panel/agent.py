"""Cymbal Logistics access-review panel: three specialist reviewers run in parallel,
then a decider merges their findings. Uses the tools and data in access_triage (one copy, imported).

Pattern: SequentialAgent[ ParallelAgent[policy, identity, sod], decider ]
Each reviewer writes its finding to session state (output_key). The decider
reads those keys through {placeholders} in its instruction.

THE SHAPE, AS A PICTURE
    access_review_panel (SequentialAgent: runs its steps in order)
     |
     +-- 1. review_panel (ParallelAgent: runs all three at the same time)
     |        +-- policy_reviewer    -> saves its finding as "policy_finding"
     |        +-- identity_reviewer  -> saves its finding as "identity_finding"
     |        +-- sod_reviewer       -> saves its finding as "sod_finding"
     |
     +-- 2. decider (reads the three findings, decides, records)

TWO KINDS OF AGENT
    LlmAgent is a model-led agent: a model reads instructions and decides what
    to do next. SequentialAgent and ParallelAgent are workflow agents: plain
    code, no model. They always run every sub-agent, in a fixed order or all
    at once. Use a workflow agent when every step must run every time.

SESSION STATE
    A shared notepad for one conversation. output_key="policy_finding" means
    "save this agent's final answer in state under the name policy_finding".
    {policy_finding} in the decider's instruction means "paste that saved
    answer here before the model reads it". In adk web, click State to see it.

NOTE
    This file imports check_sod_conflicts. On the live-start branch that tool
    only exists after Play 3, so this agent loads after Play 3, not before.
"""

import os

# LlmAgent is the same class as Agent: a model-led agent.
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from access_triage.tools import (
    check_sod_conflicts,
    get_access_request,
    get_app_policy,
    get_employee,
    record_recommendation,
)

MODEL = os.getenv("TRIAGE_MODEL", "gemini-2.5-flash")

# Instructions every reviewer shares. Each reviewer adds its own job below.
SHARED = """
You are one reviewer on the Cymbal Logistics access-review panel.
Find the request ID in the user's message and call get_access_request first.
Call every tool your job needs before you answer, and wait for the results.
Give PASS when the tool results show every check in your job passes.
UNSURE means the tool results do not settle the question. It never means you
have not called a tool yet.
Base every statement on a tool result. Never invent facts.
Reply in 3 to 5 short bullets. Start with a verdict line:
Verdict: PASS, FAIL or UNSURE.
"""

# --- Reviewer 1: policy fit ------------------------------------------------
# Gets only the tools its job needs. A narrow job and few tools make a
# reviewer more reliable.
policy_reviewer = LlmAgent(
    name="policy_reviewer",
    model=MODEL,
    description="Checks the request against the app and role policy.",
    instruction=SHARED + """
Your only job: policy fit.
Call get_employee and get_app_policy. Check department, contractor rules,
contractor day limits, and which approvals the role requires.
""",
    tools=[get_access_request, get_employee, get_app_policy],
    # Save the final answer in session state as "policy_finding".
    output_key="policy_finding",
)

# --- Reviewer 2: identity risk ---------------------------------------------
identity_reviewer = LlmAgent(
    name="identity_reviewer",
    model=MODEL,
    description="Checks the requester's identity status and existing access.",
    instruction=SHARED + """
Your only job: identity risk.
Call get_employee. Check employment_status, employment_type, end_date, and whether the
justification makes sense for this person's title. Flag any access a
terminated person still holds.
""",
    tools=[get_access_request, get_employee],
    output_key="identity_finding",
)

# --- Reviewer 3: separation of duties --------------------------------------
# Also checks for a conflict of interest: REQ-1003 says Tomas is covering for
# Marcus, and Marcus is Tomas's own manager. The single agent misses this.
sod_reviewer = LlmAgent(
    name="sod_reviewer",
    model=MODEL,
    description="Checks separation-of-duties conflicts.",
    instruction=SHARED + """
Your only job: separation of duties.
Call check_sod_conflicts. Then call get_employee for the requester.
If the justification says the requester is covering for someone, compare that
name with the requester's manager field. If it is the requester's own manager,
FAIL and report a conflict of interest: the requester would take over an
approval that normally belongs to their manager.
""",
    tools=[get_access_request, get_employee, check_sod_conflicts],
    output_key="sod_finding",
)

# --- Step 1: run the three reviewers at the same time ----------------------
# ParallelAgent has no model. It starts every sub-agent at once and waits for
# all of them. None of them can be skipped.
review_panel = ParallelAgent(
    name="review_panel",
    sub_agents=[policy_reviewer, identity_reviewer, sod_reviewer],
    description="Runs the three reviews at the same time.",
)

# --- Step 2: the decider ---------------------------------------------------
# Before the model reads this instruction, ADK replaces {policy_finding},
# {identity_finding} and {sod_finding} with the answers saved in state.
# The decider has one tool: it can record a decision, but it cannot look
# anything up. It must work from the findings.
decider = LlmAgent(
    name="decider",
    model=MODEL,
    description="Merges the panel findings into one recommendation.",
    instruction="""
You are the panel chair. Merge the three findings below into one recommendation.

Policy finding:
{policy_finding}

Identity finding:
{identity_finding}

Separation-of-duties finding:
{sod_finding}

Rules:
- Any FAIL on identity (terminated) or policy (department, contractor) means DENY.
- Any FAIL on separation of duties, or any UNSURE, means ESCALATE.
- Three PASS verdicts mean APPROVE.
- In Reasons, include every problem any reviewer reports, including conflicts of interest.
- Do not add facts that are not in the findings.

Call record_recommendation, then answer:
Recommendation: APPROVE, DENY or ESCALATE
Panel: one line per reviewer with its verdict
Reasons: short bullets
Confirmation: the confirmation_id
""",
    tools=[record_recommendation],
)

# --- The whole panel -------------------------------------------------------
# SequentialAgent has no model either. It runs review_panel, then decider,
# always in that order. adk web looks for root_agent.
root_agent = SequentialAgent(
    name="access_review_panel",
    sub_agents=[review_panel, decider],
    description="Parallel three-reviewer access review for Cymbal Logistics.",
)
