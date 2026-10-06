"""Function tools for the Cymbal Logistics access-request triage agent.

ADK reads each function's name, type hints and docstring and turns them into
the tool definition the model sees. Keep docstrings precise: they are the
model's only instructions for when and how to call a tool.

All data is fictional and ships inside this package (data/), so the agent
behaves the same locally (adk web) and when deployed to Agent Runtime.

HOW TO READ THIS FILE
    Each tool is a plain Python function. Three parts matter:
      1. The function name and parameters (with type hints such as str).
         ADK turns these into the tool's name and inputs.
      2. The docstring (the text in triple quotes under the def line).
         ADK sends it to the model as the tool's description. The model reads
         it to decide when to call the tool and what to pass in.
      3. The body. This is ordinary code. The model never sees it and never
         runs it. ADK runs it when the model asks for the tool.
    Comments that start with # are for people. ADK does not send them to the
    model. That is why the comments explain the code, and the docstrings
    explain the tool to the model.

WHERE THE DATA COMES FROM
    Four JSON files in access_triage/data/:
      requests.json      the pending access requests (REQ-1001 to REQ-1006)
      directory.json     the people: title, department, manager, current access
      app_policies.json  each app's roles and who may hold them
      sod_rules.json     separation-of-duties rules: pairs of roles one
                         person may not hold together
    In a real project, each function would call your own system (an API or a
    database) instead of reading a file. The docstring would stay the same.

WHO ELSE USES THESE FUNCTIONS
    access_triage/agent.py      calls them directly as function tools
    mcp_server/server.py        serves them over MCP (Play 4)
    access_triage_panel/agent.py  gives a few to each reviewer (Play 4)
    access_triage/policy.py     reuses them for the code-based guard (Play 4)
"""

import json
from datetime import date
from pathlib import Path

# The folder that holds the JSON data files, next to this file.
_DATA = Path(__file__).parent / "data"


# A helper, not a tool. The leading underscore means "internal". It is not in
# the agent's TOOLS list, so the model never sees it.
def _load(name: str):
    """Read one JSON file from the data folder and return its contents."""
    with open(_DATA / name, encoding="utf-8") as f:
        return json.load(f)


# --- Tool 1: get_access_request --------------------------------------------
# The first tool the agent calls. It turns a request ID into the details:
# who is asking, for which app and role, for how long, and why.
def get_access_request(request_id: str) -> dict:
    """Look up a pending access request by its ID.

    Args:
        request_id: The request ID, for example "REQ-1001".

    Returns:
        A dict with status "found" and the request details (requester email,
        app, role, duration_days, justification, submitted date), or status
        "not_found".
    """
    requests = _load("requests.json")
    # strip() removes spaces and upper() makes "req-1001" match "REQ-1001",
    # so small typos from the model or the user do not break the lookup.
    req = requests.get(request_id.strip().upper())
    if req is None:
        # Return a clear status instead of raising an error. The model reads
        # this result and can tell the user the request was not found.
        return {"status": "not_found", "request_id": request_id}
    # {**req, ...} copies every field of the request and adds two more.
    return {**req, "status": "found", "request_id": request_id.strip().upper()}


# --- Tool 2: get_employee --------------------------------------------------
# Looks up the requester in the directory. The decision rules depend on what
# this returns: employment status, contractor or employee, department, and the
# access the person already holds (current_access).
def get_employee(email: str) -> dict:
    """Look up an employee or contractor in the Cymbal Logistics directory.

    Args:
        email: The person's work email address.

    Returns:
        A dict with status "found" and the person's name, title, department,
        employment_type ("employee" or "contractor"), employment_status ("active" or
        "terminated"), manager, start_date, end_date and current_access
        (a list of "App:role" entitlements they hold today), or status
        "not_found".
    """
    directory = _load("directory.json")
    # Emails are stored in lower case, so normalise the input the same way.
    person = directory.get(email.strip().lower())
    if person is None:
        return {"status": "not_found", "email": email}
    return {**person, "status": "found", "email": email.strip().lower()}


# --- Tool 3: get_app_policy ------------------------------------------------
# Returns the rules for one role in one app: which departments may hold it,
# whether contractors may hold it and for how long, and which approvals it
# needs. It has three possible outcomes, and each one tells the model exactly
# what went wrong, so the model can ESCALATE with a clear reason.
def get_app_policy(app: str, role: str) -> dict:
    """Get the access policy for one role in one application.

    Args:
        app: The application name, for example "FreightLedger".
        role: The role requested in that application, for example "report-viewer".

    Returns:
        A dict with status "found" and the app sensitivity, allowed_departments,
        contractors_allowed, max_days_contractor and the approvals the role
        requires. Returns status "app_not_in_catalog" if the application is not
        a governed app, or "role_not_found" (with the valid roles) if the role
        does not exist.
    """
    policies = _load("app_policies.json")
    app_policy = policies.get(app)
    # Outcome 1: the app is not in the catalog at all.
    if app_policy is None:
        return {
            "status": "app_not_in_catalog",
            "app": app,
            "known_apps": sorted(policies.keys()),
        }
    role_policy = app_policy["roles"].get(role)
    # Outcome 2: the app exists, but the role does not. We also return the
    # valid roles, so the model can explain what the requester could ask for.
    if role_policy is None:
        return {
            "status": "role_not_found",
            "app": app,
            "role": role,
            "valid_roles": sorted(app_policy["roles"].keys()),
        }
    # Outcome 3: found. Return the role's rules plus the app's sensitivity.
    return {
        **role_policy,
        "status": "found",
        "app": app,
        "role": role,
        "sensitivity": app_policy["sensitivity"],
    }


# --- Tool 4: check_sod_conflicts (Play 3) ----------------------------------
# Separation of duties (SoD): some pairs of roles must never be held by the
# same person. Example, rule SOD-01: a person who holds
# FreightLedger:vendor-master-edit must not also hold
# FreightLedger:payables-approver, or they could create a fake vendor and
# approve payments to it. This tool checks the requested role against every rule.
# On the live-start branch this function does not exist yet. Antigravity
# writes it in Play 3, which is why the agent first gets REQ-1003 wrong.
def check_sod_conflicts(email: str, app: str, role: str) -> dict:
    """Check separation-of-duties (SoD) rules for a requested role.

    Compares the requested "app:role" with everything the person already holds.

    Args:
        email: The requester's work email address.
        app: The application name.
        role: The role being requested.

    Returns:
        A dict with "conflict" (true or false) and, when true, the list of
        violated rules with rule_id, the entitlement already held, and the reason.
    """
    # Reuse Tool 2 to get what the person already holds.
    person = get_employee(email)
    if person["status"] != "found":
        return {"status": "not_found", "email": email}
    # Entitlements are written "App:role", for example "FreightLedger:payables-approver".
    requested = f"{app}:{role}"
    held = set(person.get("current_access", []))
    violations = []
    for rule in _load("sod_rules.json"):
        # Each rule names two roles (role_a and role_b) that clash.
        pair = {rule["role_a"], rule["role_b"]}
        if requested in pair:
            # The requested role is half of this rule. Find the other half...
            other = (pair - {requested}).pop()
            # ...and check whether the person already holds it.
            if other in held:
                violations.append(
                    {"rule_id": rule["rule_id"], "already_holds": other, "reason": rule["reason"]}
                )
    # conflict is True when at least one rule was broken.
    return {"status": "checked", "requested": requested, "conflict": bool(violations), "violations": violations}


# --- Tool 5: record_recommendation -----------------------------------------
# The last tool the agent calls. It files the recommendation for a human. It
# deliberately cannot grant or remove access: the agent recommends, a person
# decides. In Play 4, the policy guard checks every call to this tool before it
# runs (see access_triage/policy.py).
def record_recommendation(request_id: str, recommendation: str, reasons: list[str]) -> dict:
    """Record the triage recommendation for a request so a human approver can act on it.

    This does NOT grant or remove access. It only files a recommendation.

    Args:
        request_id: The request ID, for example "REQ-1001".
        recommendation: One of "APPROVE", "DENY" or "ESCALATE".
        reasons: Short reasons, each citing the policy, rule or fact it is based on.

    Returns:
        A dict with a confirmation ID and the recorded recommendation.
    """
    rec = recommendation.strip().upper()
    # Code-level check: refuse anything that is not one of the three allowed
    # values, even if the model sends something else.
    if rec not in {"APPROVE", "DENY", "ESCALATE"}:
        return {"status": "rejected", "error": "recommendation must be APPROVE, DENY or ESCALATE"}
    return {
        "status": "recorded",
        # A made-up confirmation ID, for example TRI-REQ-1003-20261008.
        # A real version would write to a ticketing system and return its ID.
        "confirmation_id": f"TRI-{request_id.strip().upper()}-{date.today():%Y%m%d}",
        "request_id": request_id.strip().upper(),
        "recommendation": rec,
        "reasons": reasons,
        "note": "Recommendation filed for human approval. No access was changed.",
    }
