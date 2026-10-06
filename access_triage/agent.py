"""Cymbal Logistics access-request triage agent (single agent, five function tools).

HOW AN ADK AGENT IS PUT TOGETHER
    An agent is three things:
      1. A model     - the LLM that reads the request and decides what to do.
      2. Instructions - plain-English text: the job, the steps, the rules and
                        the answer format. The model reads it on every turn.
      3. Tools       - Python functions the model may ask ADK to run
                        (see access_triage/tools.py).
    adk web and adk run look for a variable named root_agent in this file.

HOW A REQUEST FLOWS
    You type "Triage access request REQ-1003."
    -> The model reads the instructions and the tool descriptions.
    -> It asks for get_access_request("REQ-1003"). ADK runs the function and
       sends the result back to the model.
    -> It repeats that for each tool it needs, then decides.
    -> It calls record_recommendation and writes the answer.
    In adk web, every one of those steps is an event you can click.
"""

import os

# Agent is ADK's standard model-driven agent (the same class as LlmAgent).
from google.adk.agents import Agent

# The tool functions. The leading dot means "from this same folder".
from .tools import (
    check_sod_conflicts,
    get_access_request,
    get_app_policy,
    get_employee,
    record_recommendation,
)

# --- 1. The model ----------------------------------------------------------
# Read the model name from the TRIAGE_MODEL environment variable, and use
# gemini-2.5-flash if it is not set. Change the model without changing code.
MODEL = os.getenv("TRIAGE_MODEL", "gemini-2.5-flash")

# --- 2. The instructions ---------------------------------------------------
# Everything between the triple quotes is sent to the model as-is.
# It has four parts: the role, the steps (which tools to call, in order), the
# decision rules, and the answer format.
# Note: these rules are a request to the model, not a control. Play 4 shows
# the same rules written in code (access_triage/policy.py).
INSTRUCTION = """
You are the access-request triage assistant for Cymbal Logistics.
You review access requests and recommend APPROVE, DENY or ESCALATE.
You never grant access yourself. A human approver makes the final decision.

For every request:
1. Call get_access_request to load the request.
2. Call get_employee for the requester.
3. Call get_app_policy for the app and role.
4. Call check_sod_conflicts for the requester, app and role.
5. Decide, then call record_recommendation.

Decision rules:
- DENY if the requester employment_status is "terminated".
- DENY if the role does not allow contractors and the requester is a contractor.
- DENY if the requester's department is not in allowed_departments.
- ESCALATE if check_sod_conflicts returns a conflict.
- ESCALATE if the app is not in the catalog or the role is not found.
- ESCALATE if a contractor asks for more days than max_days_contractor.
- Otherwise APPROVE, and list the approvals the policy still requires.
- If more than one rule applies, the strictest wins: DENY over ESCALATE, ESCALATE over APPROVE.

Rules you must follow:
- Base every reason on a tool result. Name the field, policy or rule_id.
- Never invent apps, roles, people, policies or approvals.
- If a tool returns not_found or app_not_in_catalog, say so plainly.
- Flag anything else a security reviewer should see, even if it does not change
  the decision. For example, a terminated person who still holds access.

Answer format:
Recommendation: APPROVE, DENY or ESCALATE
Reasons: a short bullet list with the evidence for each reason
Required next steps: who must act, and what they must do
Confirmation: the confirmation_id from record_recommendation
"""

# --- 3. The tools ----------------------------------------------------------
# The list of functions the model is allowed to call. A function that exists
# in tools.py but is not in this list is invisible to the model.
# Other agents in this repo import this list, so they share the same tools.
TOOLS = [
    get_access_request,
    get_employee,
    get_app_policy,
    check_sod_conflicts,
    record_recommendation,
]

# --- The agent itself ------------------------------------------------------
root_agent = Agent(
    # The name shown in the adk web agent list. Letters, numbers and _ only.
    name="access_triage",
    model=MODEL,
    # A one-line summary. Other agents read it when they decide whether to hand
    # work to this agent, so write it for a reader, not a filing system.
    description="Reviews Cymbal Logistics access requests against policy and recommends approve, deny or escalate.",
    instruction=INSTRUCTION,
    tools=TOOLS,
)
