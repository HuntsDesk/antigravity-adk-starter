"""Cymbal Logistics access-review panel: three specialist reviewers run in parallel,
then a decider merges their findings. Uses the tools and data in access_triage (one copy, imported).

Pattern: SequentialAgent[ ParallelAgent[policy, identity, sod], decider ]
Each reviewer writes its finding to session state (output_key). The decider
reads those keys through {placeholders} in its instruction.
"""

import os

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from access_triage.tools import (
    check_sod_conflicts,
    get_access_request,
    get_app_policy,
    get_employee,
    record_recommendation,
)

MODEL = os.getenv("TRIAGE_MODEL", "gemini-2.5-flash")

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
    output_key="policy_finding",
)

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

review_panel = ParallelAgent(
    name="review_panel",
    sub_agents=[policy_reviewer, identity_reviewer, sod_reviewer],
    description="Runs the three reviews at the same time.",
)

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

root_agent = SequentialAgent(
    name="access_review_panel",
    sub_agents=[review_panel, decider],
    description="Parallel three-reviewer access review for Cymbal Logistics.",
)
