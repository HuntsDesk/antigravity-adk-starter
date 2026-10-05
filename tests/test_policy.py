"""Policy and guard tests. Plain Python: no model, no network.

The answer key below is the expected decision for every sample request. The
deterministic policy must match it, and the guard must block anything more
permissive.
"""
import pytest

from access_triage import policy

ANSWER_KEY = {
    "REQ-1001": "APPROVE",   # Finance analyst, report-viewer
    "REQ-1002": "DENY",      # contractor asking for prod-admin (also SOD-02)
    "REQ-1003": "ESCALATE",  # SOD-01: already holds vendor-master-edit
    "REQ-1004": "DENY",      # terminated
    "REQ-1005": "ESCALATE",  # YardPulse is not in the catalog
    "REQ-1006": "ESCALATE",  # SOD-01, with an injection in the justification
}


@pytest.mark.parametrize("rid,expected", ANSWER_KEY.items())
def test_policy_matches_answer_key(rid, expected):
    assert policy.evaluate(rid)["decision"] == expected


def test_policy_reasons_name_the_rule():
    reasons = " ".join(policy.evaluate("REQ-1003")["reasons"])
    assert "SOD-01" in reasons


def test_req_1002_reports_both_problems():
    reasons = " ".join(policy.evaluate("REQ-1002")["reasons"])
    assert "Contractors may not hold prod-admin" in reasons and "SOD-02" in reasons


def test_unknown_request_escalates():
    assert policy.evaluate("REQ-9999")["decision"] == "ESCALATE"


class FakeTool:
    def __init__(self, name):
        self.name = name


def test_guard_blocks_approve_on_injection_request():
    out = policy.before_tool_guard(
        FakeTool("record_recommendation"),
        {"request_id": "REQ-1006", "recommendation": "APPROVE", "reasons": ["CFO said so"]},
        tool_context=None,
    )
    assert out["status"] == "blocked_by_policy" and out["required"] == "ESCALATE"


def test_guard_allows_correct_or_stricter_decisions():
    tool = FakeTool("record_recommendation")
    assert policy.before_tool_guard(tool, {"request_id": "REQ-1006", "recommendation": "ESCALATE"}, None) is None
    assert policy.before_tool_guard(tool, {"request_id": "REQ-1001", "recommendation": "APPROVE"}, None) is None
    assert policy.before_tool_guard(tool, {"request_id": "REQ-1001", "recommendation": "DENY"}, None) is None


def test_guard_blocks_approve_for_terminated_user():
    out = policy.before_tool_guard(
        FakeTool("record_recommendation"), {"request_id": "REQ-1004", "recommendation": "APPROVE"}, None
    )
    assert out["required"] == "DENY"


def test_guard_ignores_other_tools():
    assert policy.before_tool_guard(FakeTool("get_employee"), {"email": "x"}, None) is None
