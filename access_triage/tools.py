"""Function tools for the Cymbal Logistics access-request triage agent.

ADK reads each function's name, type hints and docstring and turns them into
the tool definition the model sees. Keep docstrings precise: they are the
model's only instructions for when and how to call a tool.

All data is fictional and ships inside this package (data/), so the agent
behaves the same locally (adk web) and when deployed to Agent Runtime.
"""

import json
from datetime import date
from pathlib import Path

_DATA = Path(__file__).parent / "data"


def _load(name: str):
    with open(_DATA / name, encoding="utf-8") as f:
        return json.load(f)


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
    req = requests.get(request_id.strip().upper())
    if req is None:
        return {"status": "not_found", "request_id": request_id}
    return {**req, "status": "found", "request_id": request_id.strip().upper()}


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
    person = directory.get(email.strip().lower())
    if person is None:
        return {"status": "not_found", "email": email}
    return {**person, "status": "found", "email": email.strip().lower()}


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
    if app_policy is None:
        return {
            "status": "app_not_in_catalog",
            "app": app,
            "known_apps": sorted(policies.keys()),
        }
    role_policy = app_policy["roles"].get(role)
    if role_policy is None:
        return {
            "status": "role_not_found",
            "app": app,
            "role": role,
            "valid_roles": sorted(app_policy["roles"].keys()),
        }
    return {
        **role_policy,
        "status": "found",
        "app": app,
        "role": role,
        "sensitivity": app_policy["sensitivity"],
    }


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
    person = get_employee(email)
    if person["status"] != "found":
        return {"status": "not_found", "email": email}
    requested = f"{app}:{role}"
    held = set(person.get("current_access", []))
    violations = []
    for rule in _load("sod_rules.json"):
        pair = {rule["role_a"], rule["role_b"]}
        if requested in pair:
            other = (pair - {requested}).pop()
            if other in held:
                violations.append(
                    {"rule_id": rule["rule_id"], "already_holds": other, "reason": rule["reason"]}
                )
    return {"status": "checked", "requested": requested, "conflict": bool(violations), "violations": violations}


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
    if rec not in {"APPROVE", "DENY", "ESCALATE"}:
        return {"status": "rejected", "error": "recommendation must be APPROVE, DENY or ESCALATE"}
    return {
        "status": "recorded",
        "confirmation_id": f"TRI-{request_id.strip().upper()}-{date.today():%Y%m%d}",
        "request_id": request_id.strip().upper(),
        "recommendation": rec,
        "reasons": reasons,
        "note": "Recommendation filed for human approval. No access was changed.",
    }
