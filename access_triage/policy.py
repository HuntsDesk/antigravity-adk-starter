"""Deterministic access policy. Plain Python: no model, no ADK.

The agent's instructions describe these rules, but instructions are a request,
not a control. A prompt injection or a bad model turn can talk an agent out of
them. This module is the control: the same rules, in code, so a guard can check
every recommendation before it is recorded (see access_triage_guarded).

Pattern: the model proposes, code decides.

WHAT IS IN THIS FILE
    evaluate()             works out the decision the rules require for one
                           request, the same way every time.
    guard_recommendation() compares the model's proposed decision with
                           evaluate(), and blocks it if the model was too lenient.
    before_tool_guard()    the hook ADK calls before every tool call. It only
                           acts on record_recommendation.

WHY "DETERMINISTIC"
    Same input, same output, every time. A model can give different answers to
    the same question. This code cannot. Use code for the decisions that must
    never depend on the model alone.
"""

# Reuse the same tool functions the agent calls, so the guard reads the same data.
from . import tools

# The three outcomes, ranked from least to most strict. A higher number is
# stricter. "The strictest wins" means: keep the highest number seen so far.
_SEVERITY = {"APPROVE": 0, "ESCALATE": 1, "DENY": 2}


# --- evaluate: the rules, in code ------------------------------------------
# This is the code version of the "Decision rules" in access_triage/agent.py.
def evaluate(request_id: str) -> dict:
    """Return the decision the policy requires for one request.

    Returns:
        {"request_id", "decision": "APPROVE" | "DENY" | "ESCALATE", "reasons": [str]}
        or {"request_id", "decision": "ESCALATE", "reasons": ["request not found"]}.
    """
    req = tools.get_access_request(request_id)
    rid = request_id.strip().upper()
    # No request, nothing to check: send it to a human.
    if req["status"] != "found":
        return {"request_id": rid, "decision": "ESCALATE", "reasons": ["Request not found."]}

    # Start at APPROVE. Each rule that applies can only make it stricter.
    decision, reasons = "APPROVE", []

    # Small helper: record a reason, and raise the decision if this rule is
    # stricter than the current one. It never lowers the decision.
    def raise_to(level: str, reason: str) -> None:
        nonlocal decision
        reasons.append(f"{level}: {reason}")
        if _SEVERITY[level] > _SEVERITY[decision]:
            decision = level

    # Rule: the requester must be in the directory.
    person = tools.get_employee(req["requester"])
    if person["status"] != "found":
        raise_to("ESCALATE", f"Requester {req['requester']} is not in the directory.")
        return {"request_id": rid, "decision": decision, "reasons": reasons}

    # Rule: terminated people get nothing.
    if person["employment_status"] == "terminated":
        raise_to("DENY", "Requester is terminated.")

    # Rules from the app's policy: catalog, role, department, contractor limits.
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
    # (So the guard works on the live-start branch too, before check_sod_conflicts exists.)
    requested = f"{req['app']}:{req['role']}"
    held = set(person.get("current_access", []))
    for rule in tools._load("sod_rules.json"):
        pair = {rule["role_a"], rule["role_b"]}
        # "& held" keeps only the other role if the person already holds it.
        if requested in pair and (pair - {requested}) & held:
            other = (pair - {requested}).pop()
            raise_to("ESCALATE", f"{rule['rule_id']}: already holds {other}. {rule['reason']}")

    return {"request_id": rid, "decision": decision, "reasons": reasons}


# --- guard_recommendation: compare the model with the rules ----------------
def guard_recommendation(request_id: str, recommendation: str) -> dict | None:
    """Check a proposed recommendation against the policy.

    Returns None if the recommendation is allowed. Returns a "blocked" result if
    the agent proposed something more permissive than the policy requires
    (for example APPROVE when the policy says ESCALATE or DENY).
    """
    proposed = (recommendation or "").strip().upper()
    required = evaluate(request_id)
    # Allow the model's choice if it is at least as strict as the rules require.
    # A stricter choice (ESCALATE when the rules say APPROVE) is fine: a human
    # will look at it. A more lenient choice is blocked. An unknown value gets
    # -1, so it is always blocked.
    if _SEVERITY.get(proposed, -1) >= _SEVERITY[required["decision"]]:
        return None
    # Blocked. This dict goes back to the model in place of the tool result,
    # and the note tells the model what to say to the user.
    return {
        "status": "blocked_by_policy",
        "request_id": required["request_id"],
        "proposed": proposed or "(none)",
        "required": required["decision"],
        "reasons": required["reasons"],
        "note": "The policy guard blocked this recommendation. Nothing was recorded. "
        "Tell the user the required decision and the reasons.",
    }


# --- before_tool_guard: the hook ADK calls ---------------------------------
# access_triage_guarded/agent.py passes this function to the agent as
# before_tool_callback. ADK then calls it before EVERY tool call, with:
#   tool          the tool about to run
#   args          the arguments the model chose
#   tool_context  session details (not used here)
def before_tool_guard(tool, args, tool_context):
    """ADK before_tool_callback. Runs before every tool call.

    Returning a dict skips the tool and hands the dict back to the model as the
    tool result. Returning None lets the tool run as normal.
    """
    # Only check the tool that files a decision. Let every lookup run as normal.
    if getattr(tool, "name", "") != "record_recommendation":
        return None
    return guard_recommendation(args.get("request_id", ""), args.get("recommendation", ""))
