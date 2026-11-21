"""Integration test verifying full REST API lifecycle, RBAC enforcement, and audit logging."""

from fastapi.testclient import TestClient
from inveniq_api.main import app

client = TestClient(app)


def test_health_endpoints() -> None:
    res = client.get("/api/v1/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ALIVE"

    res_ready = client.get("/api/v1/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"


def test_auth_login_and_rbac_flow() -> None:
    # 1. Login as Buyer
    login_buyer = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@tbo.com", "password": "InvenIQ2026!"},
    )
    assert login_buyer.status_code == 200
    buyer_token = login_buyer.json()["access_token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

    # 2. Check /auth/me
    res_me = client.get("/api/v1/auth/me", headers=buyer_headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "buyer@tbo.com"
    assert res_me.json()["role"] == "buyer"

    # 3. Unauthenticated request to /optimization/runs must fail
    res_unauth = client.post(
        "/api/v1/optimization/runs",
        json={"budget_inr": 500000.0, "risk_appetite": "BALANCED"},
    )
    assert res_unauth.status_code == 401

    # 4. Submit optimization run as Buyer (with Idempotency Key)
    idempotency_key = "test-key-uuid-12345"
    submit_headers = {**buyer_headers, "X-Idempotency-Key": idempotency_key}

    res_submit = client.post(
        "/api/v1/optimization/runs?sync=true",
        json={
            "budget_inr": 500000.0,
            "risk_appetite": "BALANCED",
            "dest_exposure_cap": 0.60,
        },
        headers=submit_headers,
    )
    assert res_submit.status_code == 202
    run_data = res_submit.json()
    run_id = run_data["run_id"]
    assert run_id.startswith("RUN_")
    assert run_data["status"] in ("COMPLETED_AWAITING_APPROVAL", "APPROVED")
    assert len(run_data["recommendations"]) > 0

    # 5. Test Idempotency: re-submitting with identical idempotency key returns exact same run!
    res_dup = client.post(
        "/api/v1/optimization/runs?sync=true",
        json={
            "budget_inr": 500000.0,
            "risk_appetite": "BALANCED",
        },
        headers=submit_headers,
    )
    assert res_dup.status_code == 202
    assert res_dup.json()["run_id"] == run_id

    # 6. Test RBAC: Buyer attempts to approve run -> HTTP 403 Forbidden!
    res_buyer_approve = client.post(
        f"/api/v1/optimization/runs/{run_id}/approve",
        json={"approved": True, "notes": "Buyer approving their own run"},
        headers=buyer_headers,
    )
    assert res_buyer_approve.status_code == 403
    assert "Access forbidden" in res_buyer_approve.json()["detail"]

    # 7. Login as Finance Approver
    login_finance = client.post(
        "/api/v1/auth/login",
        json={"email": "finance@tbo.com", "password": "InvenIQ2026!"},
    )
    assert login_finance.status_code == 200
    finance_token = login_finance.json()["access_token"]
    finance_headers = {"Authorization": f"Bearer {finance_token}"}

    # 8. Finance Approver approves run -> HTTP 200 OK!
    res_finance_approve = client.post(
        f"/api/v1/optimization/runs/{run_id}/approve",
        json={"approved": True, "notes": "Approved for Q1 capital disbursement"},
        headers=finance_headers,
    )
    assert res_finance_approve.status_code == 200
    approved_run = res_finance_approve.json()
    assert approved_run["status"] == "APPROVED"
    assert approved_run["approver_notes"] == "Approved for Q1 capital disbursement"

    # 9. Verify Immutable Audit Trail
    res_audit = client.get("/api/v1/audit/logs", headers=finance_headers)
    assert res_audit.status_code == 200
    audit_logs = res_audit.json()
    assert len(audit_logs) >= 2
    actions = [a["action"] for a in audit_logs]
    assert "SUBMIT_RUN" in actions
    assert "APPROVE_RUN" in actions


    # 10. Test Risk Endpoints
    res_frontier = client.get("/api/v1/risk/frontier?points=3", headers=buyer_headers)
    assert res_frontier.status_code == 200
    assert len(res_frontier.json()) == 3

    res_sens = client.get("/api/v1/risk/sensitivity", headers=buyer_headers)
    assert res_sens.status_code == 200
    assert len(res_sens.json()) > 0
