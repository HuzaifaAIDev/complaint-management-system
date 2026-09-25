from tests.conftest import login, valid_request_payload
from app.extensions import db


def test_customer_cannot_access_sla_monitoring(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.get("/api/dashboard/sla-monitoring")
    assert resp.status_code == 403


def test_supervisor_can_access_sla_monitoring(client, seed_users):
    email, pw = seed_users["supervisor"]
    login(client, email, pw)
    resp = client.get("/api/dashboard/sla-monitoring")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "breached" in body and "at_risk" in body and "within_sla" in body


def test_customer_cannot_view_another_customers_360(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.get("/api/customers/me")
    my_id = resp.get_json()["customer"]["id"]
    client.post("/api/auth/logout")

    email2, pw2 = seed_users["customer2"]
    login(client, email2, pw2)
    resp = client.get(f"/api/customers/{my_id}/summary")
    assert resp.status_code == 403


def test_customer_can_view_own_360(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.get("/api/customers/me")
    my_id = resp.get_json()["customer"]["id"]
    resp = client.get(f"/api/customers/{my_id}/summary")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "summary" in body and "requests" in body and "complaints" in body


def test_agent_workload_admin_only(client, seed_users):
    email, pw = seed_users["agent"]
    login(client, email, pw)
    resp = client.get("/api/users/agents/workload")
    assert resp.status_code == 403

    client.post("/api/auth/logout")
    email, pw = seed_users["supervisor"]
    login(client, email, pw)
    resp = client.get("/api/users/agents/workload")
    assert resp.status_code == 200
    assert "items" in resp.get_json()


def test_global_search_scoped_to_own_requests_for_customer(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="unique-search-term-alpha"))
    assert resp.status_code == 201
    ref = resp.get_json()["service_request"]["reference_number"]

    resp = client.get("/api/search", query_string={"q": "unique-search-term-alpha"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert any(r["reference_number"] == ref for r in body["requests"])
    # Customers never get customer/user search groups
    assert body["customers"] == []
    assert body["users"] == []


def test_global_search_does_not_leak_other_customers_requests(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="leak-test-term-beta"))
    ref = resp.get_json()["service_request"]["reference_number"]
    client.post("/api/auth/logout")

    email2, pw2 = seed_users["customer2"]
    login(client, email2, pw2)
    resp = client.get("/api/search", query_string={"q": "leak-test-term-beta"})
    body = resp.get_json()
    assert not any(r["reference_number"] == ref for r in body["requests"])


def test_request_list_search_filter(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="findable widget issue"))
    client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="unrelated other thing"))

    resp = client.get("/api/service-requests", query_string={"search": "findable"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 1
    assert "findable" in body["items"][0]["description"]


def test_request_timeline_includes_creation_and_assignment(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="timeline test"))
    request_id = resp.get_json()["service_request"]["id"]
    client.post("/api/auth/logout")

    sup_email, sup_pw = seed_users["supervisor"]
    login(client, sup_email, sup_pw)
    agent_resp = client.get("/api/users", query_string={"role": "agent"})
    agent_id = agent_resp.get_json()["items"][0]["id"]
    client.post(f"/api/service-requests/{request_id}/assignments", json={"category_id": seed_users["category_id"], "agent_id": agent_id, "priority": "medium"})

    resp = client.get(f"/api/service-requests/{request_id}/timeline")
    assert resp.status_code == 200
    events = resp.get_json()["events"]
    types = [e["type"] for e in events]
    assert "created" in types
    assert "assignment" in types


def test_sla_rule_creation_blocks_duplicate_priority(client, seed_users):
    email, pw = seed_users["admin"]
    login(client, email, pw)
    # medium priority already seeded for this category in conftest
    resp = client.post("/api/sla-rules", json={
        "category_id": seed_users["category_id"], "priority": "medium",
        "response_hours": 4, "resolution_hours": 24,
    })
    assert resp.status_code == 400


def test_kanban_board_customer_forbidden(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.get("/api/service-requests/board")
    assert resp.status_code == 403


def test_kanban_board_supervisor_groups_by_status(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="board test"))
    client.post("/api/auth/logout")

    email, pw = seed_users["supervisor"]
    login(client, email, pw)
    resp = client.get("/api/service-requests/board")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "submitted" in body["columns"]
    assert len(body["columns"]["submitted"]) >= 1


def test_csv_export_requires_auth(client):
    resp = client.get("/api/service-requests/export")
    assert resp.status_code == 401


def test_csv_export_scoped_to_own_requests(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"], description="export test csv"))
    resp = client.get("/api/service-requests/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"export test csv" not in resp.data  # description isn't exported, only summary fields
    assert b"Reference" in resp.data


def test_profile_update_customer_can_change_own_name(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.patch("/api/auth/profile", json={"name": "Updated Name", "phone": "03009999999"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["name"] == "Updated Name"

    resp = client.get("/api/auth/me")
    assert resp.get_json()["user"]["phone"] == "03009999999"


def test_login_sets_last_login_at(client, seed_users):
    email, pw = seed_users["customer"]
    resp = login(client, email, pw)
    assert resp.status_code == 200
    resp = client.get("/api/auth/me")
    assert resp.get_json()["user"]["last_login_at"] is not None
