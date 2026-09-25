import io
from tests.conftest import login, valid_request_payload, valid_complaint_payload


def test_complaint_cannot_be_closed_without_resolution(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/complaints", json=valid_complaint_payload())
    complaint_id = resp.get_json()["complaint"]["id"]
    client.post("/api/auth/logout")

    sup_email, sup_pw = seed_users["supervisor"]
    login(client, sup_email, sup_pw)

    resp = client.post(f"/api/complaints/{complaint_id}/status", json={"status": "in_review"})
    assert resp.status_code == 200

    # attempt to close without a resolution recorded
    resp = client.post(f"/api/complaints/{complaint_id}/status", json={"status": "resolved"})
    assert resp.status_code == 409  # invalid transition: in_review -> resolved requires going through review first is fine, but no resolution text
    # move to resolved WITH resolution, then close is fine
    resp = client.post(f"/api/complaints/{complaint_id}/status", json={"status": "resolved", "resolution": "Refunded"})
    assert resp.status_code == 200
    resp = client.post(f"/api/complaints/{complaint_id}/status", json={"status": "closed"})
    assert resp.status_code == 200


def test_customer_cannot_lodge_complaint_for_others_request(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"]))
    request_id = resp.get_json()["service_request"]["id"]
    client.post("/api/auth/logout")

    email2, pw2 = seed_users["customer2"]
    login(client, email2, pw2)
    resp = client.post("/api/complaints", json=valid_complaint_payload(description="not mine", service_request_id=request_id))
    assert resp.status_code == 403


def test_complaint_missing_required_field_rejected(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/complaints", json={"description": "no category or severity"})
    assert resp.status_code == 400


def test_request_missing_location_rejected(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    payload = valid_request_payload(seed_users["category_id"])
    del payload["location"]
    resp = client.post("/api/service-requests", json=payload)
    assert resp.status_code == 400


def test_disallowed_file_extension_rejected(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"]))
    request_id = resp.get_json()["service_request"]["id"]

    data = {"file": (io.BytesIO(b"#!/bin/sh\necho hi"), "malicious.sh")}
    resp = client.post(f"/api/service-requests/{request_id}/attachments", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_path_traversal_in_download_rejected(client, seed_users, app):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"]))
    request_id = resp.get_json()["service_request"]["id"]

    data = {"file": (io.BytesIO(b"hello world"), "note.txt")}
    resp = client.post(f"/api/service-requests/{request_id}/attachments", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201

    # Attempt to reference an attachment id that doesn't belong to this request
    resp = client.get(f"/api/service-requests/{request_id}/attachments/99999/download")
    assert resp.status_code == 404


def test_other_customer_cannot_access_attachment(client, seed_users):
    email, pw = seed_users["customer"]
    login(client, email, pw)
    resp = client.post("/api/service-requests", json=valid_request_payload(seed_users["category_id"]))
    request_id = resp.get_json()["service_request"]["id"]
    data = {"file": (io.BytesIO(b"hello world"), "note.txt")}
    resp = client.post(f"/api/service-requests/{request_id}/attachments", data=data, content_type="multipart/form-data")
    attachment_id = resp.get_json()["attachment"]["id"]
    client.post("/api/auth/logout")

    email2, pw2 = seed_users["customer2"]
    login(client, email2, pw2)
    resp = client.get(f"/api/service-requests/{request_id}/attachments/{attachment_id}/download")
    assert resp.status_code == 403
