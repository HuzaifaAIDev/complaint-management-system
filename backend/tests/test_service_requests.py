from tests.conftest import login, valid_request_payload


def _create_request(client, category_id, priority="medium"):
    return client.post("/api/service-requests", json=valid_request_payload(category_id, priority=priority))


def test_customer_can_create_request_with_sla_deadline_set_by_server(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    assert resp.status_code == 201
    sr = resp.get_json()["service_request"]
    assert sr["reference_number"].startswith("SR-")
    assert sr["sla_resolution_deadline"] is not None
    assert sr["status"] == "submitted"


def test_client_supplied_sla_deadline_is_ignored(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json={
        **valid_request_payload(seed_users["category_id"]),
        "sla_resolution_deadline": "2099-01-01T00:00:00Z",  # attempted mass assignment
    })
    sr = resp.get_json()["service_request"]
    assert "2099" not in sr["sla_resolution_deadline"]


def test_customer_cannot_create_request_with_past_preferred_date(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json={
        **valid_request_payload(seed_users["category_id"]),
        "preferred_date": "2000-01-01",
    })
    assert resp.status_code == 400
    body = resp.get_json()
    assert "preferred_date" in body.get("fields", {})


def test_customer_can_create_request_with_todays_preferred_date(client, seed_users):
    from datetime import date
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json={
        **valid_request_payload(seed_users["category_id"]),
        "preferred_date": date.today().isoformat(),
    })
    assert resp.status_code == 201


def test_customer_cannot_access_another_customers_request(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    request_id = resp.get_json()["service_request"]["id"]
    client.post("/api/auth/logout")

    email2, pw2 = seed_users["customer2"]
    login(client, email2, pw2)
    resp = client.get(f"/api/service-requests/{request_id}")
    assert resp.status_code == 403


def test_customer_cannot_assign_agent(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    request_id = resp.get_json()["service_request"]["id"]

    resp = client.post(f"/api/service-requests/{request_id}/assignments", json={"category_id": seed_users["category_id"], "agent_id": 1, "priority": "medium"})
    assert resp.status_code == 403


def test_supervisor_can_assign_agent_and_status_moves_to_assigned(client, seed_users):
    from app.models import User
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    request_id = resp.get_json()["service_request"]["id"]
    client.post("/api/auth/logout")

    sup_email, sup_pw = seed_users["supervisor"]
    login(client, sup_email, sup_pw)

    from app import create_app
    agent_email, _ = seed_users["agent"]
    agent_user_resp = client.get("/api/users", query_string={"role": "agent"})
    agent_id = agent_user_resp.get_json()["items"][0]["id"]

    resp = client.post(f"/api/service-requests/{request_id}/assignments", json={
        "category_id": seed_users["category_id"], "agent_id": agent_id, "priority": "medium",
    })
    assert resp.status_code == 201
    assert resp.get_json()["service_request"]["status"] == "assigned"


def test_invalid_status_transition_rejected(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    request_id = resp.get_json()["service_request"]["id"]
    client.post("/api/auth/logout")

    sup_email, sup_pw = seed_users["supervisor"]
    login(client, sup_email, sup_pw)
    # submitted -> resolved is not a legal transition
    resp = client.post(f"/api/service-requests/{request_id}/status", json={"status": "resolved"})
    assert resp.status_code == 409


def test_customer_cannot_directly_change_status(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = _create_request(client, seed_users["category_id"])
    request_id = resp.get_json()["service_request"]["id"]
    resp = client.post(f"/api/service-requests/{request_id}/status", json={"status": "closed"})
    assert resp.status_code == 403
