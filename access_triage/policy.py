"""Deterministic access policy. Plain Python: no model, no ADK.

The agent's instructions describe these rules, but instructions are a request,
not a control. A prompt injection or a bad model turn can talk an agent out of
them. This module is the control: the same rules, in code, so a guard can check
every recommendation before it is recorded (see access_triage_guarded).

Pattern: the model proposes, code decides.
"""

from . import tools

# Order matters only for the reasons list. The strictest outcome wins.
_SEVERITY = {"APPROVE": 0, "ESCALATE": 1, "DENY": 2}


def evaluate(request_id: str) -> dict:
    """Return the decision the policy requires for one request.

    Returns:
        {"request_id", "decision": "APPROVE" | "DENY" | "ESCALATE", "reasons": [str]}
        or {"request_id", "decision": "ESCALATE", "reasons": ["request not found"]}.
    """
    req = tools.get_access_request(request_id)
    rid = request_id.strip().upper()
    if req["status"] != "found":
        return {"request_id": rid, "decision": "ESCALATE", "reasons": ["Request not found."]}

    decision, reasons = "APPROVE", []

    def raise_to(level: str, reason: str) -> None:
        nonlocal decision
        reasons.append(f"{level}: {reason}")
        if _SEVERITY[level] > _SEVERITY[decision]:
            decision = level

    person = tools.get_employee(req["requester"])
    if person["status"] != "found":
        raise_to("ESCALATE", f"Requester {req['requester']} is not in the directory.")
        return {"request_id": rid, "decision": decision, "reasons": reasons}

    if person["employment_status"] == "terminated":
        raise_to("DENY", "Requester is terminated.")

    policy = tools.get_app_policy(req["app"], req["role"])
    if policy["status"] == "app_not_in_catalog":
        raise_to("ESCALATE", f"{req['app']} is not in the app catalog.")
    elif policy["status"] == "role_not_found":
        raise_to("ESCALATE", f"Role {req['role']} does not exist in {req['app']}.")
    else:
        if person["department"] not in policy["allowed_departments"]:
            raise_to("DENY", f"Department {person['department']} is not allowed for {req['role']}.")
        if person["employment_type"] == "contractor":
            if not policy["contractors_allowed"]:
                raise_to("DENY", f"Contractors may not hold {req['role']}.")
            elif policy["max_days_contractor"] and req["duration_days"] > policy["max_days_contractor"]:
                raise_to("ESCALATE", f"{req['duration_days']} days exceeds the contractor limit of {policy['max_days_contractor']}.")

    # Separation of duties, checked here directly from the rules file. The guard
    # does not depend on any tool the model can call.
    requested = f"{req['app']}:{req['role']}"
    held = set(person.get("current_access", []))
    for rule in tools._load("sod_rules.json"):
        pair = {rule["role_a"], rule["role_b"]}
        if requested in pair and (pair - {requested}) & held:
            other = (pair - {requested}).pop()
            raise_to("ESCALATE", f"{rule['rule_id']}: already holds {other}. {rule['reason']}")

    return {"request_id": rid, "decision": decision, "reasons": reasons}


def guard_recommendation(request_id: str, recommendation: str) -> dict | None:
    """Check a proposed recommendation against the policy.

    Returns None if the recommendation is allowed. Returns a "blocked" result if
    the agent proposed something more permissive than the policy requires
    (for example APPROVE when the policy says ESCALATE or DENY).
    """
    proposed = (recommendation or "").strip().upper()
    required = evaluate(request_id)
    if _SEVERITY.get(proposed, -1) >= _SEVERITY[required["decision"]]:
        return None
    return {
        "status": "blocked_by_policy",
        "request_id": required["request_id"],
        "proposed": proposed or "(none)",
        "required": required["decision"],
        "reasons": required["reasons"],
        "note": "The policy guard blocked this recommendation. Nothing was recorded. "
        "Tell the user the required decision and the reasons.",
    }


def before_tool_guard(tool, args, tool_context):
    """ADK before_tool_callback. Runs before every tool call.

    Returning a dict skips the tool and hands the dict back to the model as the
    tool result. Returning None lets the tool run as normal.
    """
    if getattr(tool, "name", "") != "record_recommendation":
        return None
    return guard_recommendation(args.get("request_id", ""), args.get("recommendation", ""))
