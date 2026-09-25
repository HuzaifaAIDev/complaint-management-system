from tests.conftest import login
from app.extensions import db
from app.models import User, EmailOtp


def _get_otp_plaintext(app, email, purpose):
    """Test helper: extracts the current OTP by regenerating it through the
    service and reading the hash is not directly possible (by design), so
    instead we monkeypatch by reading the app logger isn't practical here -
    tests instead call issue_otp directly against the real user to obtain
    a code for verification, mirroring what the email body would contain."""
    from app.services.otp import issue_otp
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        code = issue_otp(user, purpose)
        db.session.commit()
        return code


def test_register_requires_strong_password(client):
    resp = client.post("/api/auth/register", json={
        "name": "New Customer", "email": "weakpw@test.com", "password": "StrongPass123",  # no special char
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400


def test_register_creates_unverified_user_and_blocks_login(client, app):
    resp = client.post("/api/auth/register", json={
        "name": "New Customer", "email": "new@test.com", "password": "StrongPass123!",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 201

    # Cannot log in until verified
    resp = client.post("/api/auth/login", json={"email": "new@test.com", "password": "StrongPass123!"})
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "email_not_verified"


def test_verify_email_with_correct_otp_allows_login(client, app):
    client.post("/api/auth/register", json={
        "name": "New Customer", "email": "verifyme@test.com", "password": "StrongPass123!",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    with app.app_context():
        user = User.query.filter_by(email="verifyme@test.com").first()
        otp = EmailOtp.query.filter_by(user_id=user.id, purpose="signup_verification").first()
        assert otp is not None
        # Re-issue through the service to obtain a plaintext code (hash is one-way).
        from app.services.otp import issue_otp
        code = issue_otp(user, "signup_verification")
        db.session.commit()

    resp = client.post("/api/auth/verify-email", json={"email": "verifyme@test.com", "code": code})
    assert resp.status_code == 200

    resp = client.post("/api/auth/login", json={"email": "verifyme@test.com", "password": "StrongPass123!"})
    assert resp.status_code == 200


def test_verify_email_wrong_code_rejected(client, app):
    client.post("/api/auth/register", json={
        "name": "New Customer", "email": "wrongcode@test.com", "password": "StrongPass123!",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    resp = client.post("/api/auth/verify-email", json={"email": "wrongcode@test.com", "code": "000000"})
    assert resp.status_code == 400


def test_login_invalid_credentials_generic_message(client, seed_users):
    email, _ = seed_users["customer"]
    resp = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword1!"})
    assert resp.status_code == 401
    assert "incorrect" in resp.get_json()["message"].lower()


def test_login_lockout_after_repeated_failures(client, seed_users):
    email, _ = seed_users["customer"]
    for _ in range(5):
        client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    resp = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    assert resp.status_code == 423


def test_login_with_remember_sets_remember_cookie(client, seed_users):
    email, password = seed_users["customer"]
    resp = client.post("/api/auth/login", json={"email": email, "password": password, "remember": True})
    assert resp.status_code == 200
    assert client.get_cookie("remember_token") is not None


def test_login_without_remember_does_not_set_remember_cookie(client, seed_users):
    email, password = seed_users["customer"]
    resp = client.post("/api/auth/login", json={"email": email, "password": password, "remember": False})
    assert resp.status_code == 200
    assert client.get_cookie("remember_token") is None


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/service-requests")
    assert resp.status_code == 401


def test_weak_password_rejected(client):
    resp = client.post("/api/auth/register", json={
        "name": "X", "email": "weak@test.com", "password": "abc",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400


def test_password_never_returned(client, seed_users):
    email, pw = seed_users["admin"]
    login(client, email, pw)
    resp = client.get("/api/auth/me")
    body = resp.get_json()
    assert "password_hash" not in body["user"]
    assert "password" not in body["user"]


def test_forgot_password_generic_response_for_unknown_email(client):
    resp = client.post("/api/auth/forgot-password", json={"email": "doesnotexist@test.com"})
    assert resp.status_code == 200
    assert "message" in resp.get_json()


def test_forgot_password_issues_temp_password_and_forces_change(client, seed_users, app):
    email, _old_pw = seed_users["customer"]
    resp = client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email=email).first()
        assert user.must_change_password is True

    # Old password no longer works
    resp = client.post("/api/auth/login", json={"email": email, "password": _old_pw})
    assert resp.status_code == 401


def test_must_change_password_blocks_other_endpoints(client, seed_users, app):
    email, _old_pw = seed_users["customer"]
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        user.must_change_password = True
        user.set_password("TempPass123!")
        user.must_change_password = True  # set_password doesn't touch this flag
        db.session.commit()

    resp = client.post("/api/auth/login", json={"email": email, "password": "TempPass123!"})
    assert resp.status_code == 200

    # Any non-auth endpoint is blocked until password is changed
    resp = client.get("/api/service-requests")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "password_change_required"

    # Changing the password clears the restriction
    resp = client.post("/api/auth/change-password", json={"current_password": "TempPass123!", "new_password": "BrandNewPass123!"})
    assert resp.status_code == 200

    resp = client.get("/api/service-requests")
    assert resp.status_code == 200


def test_google_config_disabled_by_default(client):
    resp = client.get("/api/auth/google/config")
    assert resp.status_code == 200
    assert resp.get_json()["enabled"] is False


def test_google_login_returns_404_when_not_configured(client):
    resp = client.get("/api/auth/google/login")
    assert resp.status_code == 404


def test_google_callback_rejects_missing_state_when_configured(client, app):
    app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
    app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
    app.config["GOOGLE_REDIRECT_URI"] = "http://localhost:5000/api/auth/google/callback"
    try:
        resp = client.get("/api/auth/google/callback?code=abc123")  # no state at all
        assert resp.status_code == 302
        assert "error=oauth_failed" in resp.headers["Location"]
    finally:
        app.config["GOOGLE_CLIENT_ID"] = ""
        app.config["GOOGLE_CLIENT_SECRET"] = ""
        app.config["GOOGLE_REDIRECT_URI"] = ""


def test_google_callback_rejects_mismatched_state(client, app):
    app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
    app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
    app.config["GOOGLE_REDIRECT_URI"] = "http://localhost:5000/api/auth/google/callback"
    try:
        # Prime a real oauth_state in the session via /google/login
        login_resp = client.get("/api/auth/google/login")
        assert login_resp.status_code == 302

        resp = client.get("/api/auth/google/callback?code=abc123&state=totally-wrong-state")
        assert resp.status_code == 302
        assert "error=oauth_failed" in resp.headers["Location"]
    finally:
        app.config["GOOGLE_CLIENT_ID"] = ""
        app.config["GOOGLE_CLIENT_SECRET"] = ""
        app.config["GOOGLE_REDIRECT_URI"] = ""


def test_google_only_account_cannot_login_with_password(client, app):
    with app.app_context():
        user = User(name="Google User", email="googleuser@test.com", role="customer", email_verified=True, auth_provider="google")
        user.set_password(secrets_token())
        db.session.add(user)
        db.session.flush()
        from app.models import Customer
        db.session.add(Customer(user_id=user.id, full_name="Google User"))
        db.session.commit()

    resp = client.post("/api/auth/login", json={"email": "googleuser@test.com", "password": "anything"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "google_account"


def secrets_token():
    import secrets
    return secrets.token_urlsafe(32)


def test_register_requires_phone(client):
    resp = client.post("/api/auth/register", json={
        "name": "No Phone", "email": "nophone@test.com", "password": "StrongPass123!",
        "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400
    assert "phone" in resp.get_json().get("fields", resp.get_json())


def test_register_requires_location(client):
    resp = client.post("/api/auth/register", json={
        "name": "No Location", "email": "nolocation@test.com", "password": "StrongPass123!",
        "phone": "03001234567",
    })
    assert resp.status_code == 400
    assert "location" in resp.get_json().get("fields", resp.get_json())


def test_register_rejects_phone_without_leading_zero3(client):
    resp = client.post("/api/auth/register", json={
        "name": "Bad Phone", "email": "badphone1@test.com", "password": "StrongPass123!",
        "phone": "3001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400
    assert "Phone number must be exactly 11 digits and start with 03." in str(resp.get_json())


def test_register_rejects_phone_too_short(client):
    resp = client.post("/api/auth/register", json={
        "name": "Bad Phone", "email": "badphone2@test.com", "password": "StrongPass123!",
        "phone": "0300123456", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400


def test_register_rejects_phone_too_long(client):
    resp = client.post("/api/auth/register", json={
        "name": "Bad Phone", "email": "badphone3@test.com", "password": "StrongPass123!",
        "phone": "030012345678", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400


def test_register_rejects_phone_with_country_code(client):
    resp = client.post("/api/auth/register", json={
        "name": "Bad Phone", "email": "badphone4@test.com", "password": "StrongPass123!",
        "phone": "+923001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 400


def test_register_accepts_valid_phone_and_location(client):
    resp = client.post("/api/auth/register", json={
        "name": "Test User", "email": "test.valid@test.com", "password": "StrongPass123!",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 201


def test_register_does_not_require_residence_id(client):
    """Residence ID has been removed entirely from the application; a
    registration payload with no residence_id field at all must succeed
    as long as phone/location are supplied."""
    resp = client.post("/api/auth/register", json={
        "name": "No Residence Needed", "email": "noresidenceneeded@test.com", "password": "StrongPass123!",
        "phone": "03001234567", "location": "Karachi, Gulshan",
    })
    assert resp.status_code == 201
    assert "residence_id" not in resp.get_json()
