"""Tool tests. Plain Python: no model, no network.
Run from the repo root:  python -m pytest -q
"""
import pytest

from access_triage import tools as t


def test_request_lookup_is_case_insensitive():
    assert t.get_access_request("req-1001")["status"] == "found"
    assert t.get_access_request("REQ-9999")["status"] == "not_found"


def test_all_requesters_exist_in_directory():
    for rid in ["REQ-1001", "REQ-1002", "REQ-1003", "REQ-1004", "REQ-1005", "REQ-1006"]:
        req = t.get_access_request(rid)
        assert t.get_employee(req["requester"])["status"] == "found", rid


def _needs_sod():
    if not hasattr(t, "check_sod_conflicts"):
        pytest.skip("check_sod_conflicts is not added yet (live-start branch)")


def test_req_1001_clean():
    _needs_sod()
    p = t.get_app_policy("FreightLedger", "report-viewer")
    assert p["status"] == "found" and "Finance" in p["allowed_departments"]
    assert t.check_sod_conflicts("priya.nair@cymbal-logistics.example", "FreightLedger", "report-viewer")["conflict"] is False


def test_req_1002_contractor_blocked_from_prod_admin():
    _needs_sod()
    e = t.get_employee("dev.okafor@cymbal-logistics.example")
    p = t.get_app_policy("RouteMaster", "prod-admin")
    assert e["employment_type"] == "contractor" and p["contractors_allowed"] is False
    # Also an SoD hit: already holds staging-deployer
    s = t.check_sod_conflicts(e["email"], "RouteMaster", "prod-admin")
    assert s["conflict"] and s["violations"][0]["rule_id"] == "SOD-02"


def test_req_1003_sod_conflict_and_manager_cover():
    _needs_sod()
    s = t.check_sod_conflicts("tomas.reyes@cymbal-logistics.example", "FreightLedger", "payables-approver")
    assert s["conflict"] and s["violations"][0]["rule_id"] == "SOD-01"
    assert t.get_employee("tomas.reyes@cymbal-logistics.example")["manager"] == "marcus.webb@cymbal-logistics.example"


def test_req_1004_terminated_still_holds_access():
    e = t.get_employee("hana.sato@cymbal-logistics.example")
    assert e["employment_status"] == "terminated"
    assert "RouteMaster:dispatcher" in e["current_access"]  # planted orphaned access


def test_req_1005_unknown_app():
    p = t.get_app_policy("YardPulse", "admin")
    assert p["status"] == "app_not_in_catalog" and "DockView" in p["known_apps"]


def test_role_not_found():
    assert t.get_app_policy("DockView", "admin")["status"] == "role_not_found"


def test_record_recommendation_validates():
    assert t.record_recommendation("REQ-1001", "maybe", ["x"])["status"] == "rejected"
    r = t.record_recommendation("req-1001", "approve", ["policy ok"])
    assert r["status"] == "recorded" and r["recommendation"] == "APPROVE"
    assert r["confirmation_id"].startswith("TRI-REQ-1001-")

