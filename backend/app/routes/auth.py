import secrets
import string
from datetime import timedelta
from flask import Blueprint, request, jsonify, session, redirect
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import User, Customer
from app.models.base import now_pk
from app.security.authz import login_required_api
from app.services.audit import log_action
from app.services.otp import issue_otp, verify_otp, OtpError
from app.services.email import send_otp_email, send_temporary_password_email
from app.services import google_oauth
from app.utils.validation import (
    ValidationError, require_fields, validate_email_field,
    validate_password_strength, validate_customer_phone, validate_location,
)

bp = Blueprint("auth", __name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _generate_temp_password(length: int = 14) -> str:
    """Generates a random password guaranteed to satisfy the same
    complexity policy required at signup (upper/lower/digit/special)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in "!@#$%^&*" for c in candidate)
        ):
            return candidate


@bp.get("/csrf-token")
def csrf_token():
    """React fetches this once on load and attaches the value as the
    X-CSRFToken header on every state-changing request."""
    return jsonify({"csrf_token": generate_csrf()})


@bp.post("/register")
@limiter.limit("10 per hour")
def register():
    """Customer self-registration. Required fields: full name, email,
    password, phone number, and location. There is no residence/unit
    verification step - registration is open to anyone."""
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "email", "password", "phone", "location"])

    email = validate_email_field(data["email"])
    validate_password_strength(data["password"])
    phone = validate_customer_phone(data.get("phone"))
    location = validate_location(data.get("location"))

    if User.query.filter_by(email=email).first():
        # Generic message: do not reveal whether the account exists.
        raise ValidationError({"email": "Registration could not be completed with the supplied details"})

    user = User(name=data["name"].strip()[:120], email=email, role="customer", email_verified=False)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()

    customer = Customer(
        user_id=user.id,
        full_name=data["name"].strip()[:120],
        phone=phone,
        address=location,
    )
    db.session.add(customer)
    db.session.flush()

    code = issue_otp(user, "signup_verification")
    log_action("register", "user", user.id)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError({"email": "Registration could not be completed with the supplied details"})

    send_otp_email(user.email, code, "signup_verification")

    return jsonify({
        "message": "Registration successful. A verification code has been sent to your email.",
        "email": user.email,
    }), 201


@bp.post("/verify-email")
@limiter.limit("10 per hour")
def verify_email():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email", "code"])
    email = (data["email"] or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({"error": "invalid_code", "message": "Invalid or expired code"}), 400
    if user.email_verified:
        return jsonify({"message": "Email already verified. You can log in."})

    try:
        verify_otp(user, "signup_verification", str(data["code"]).strip())
    except OtpError as e:
        return jsonify({"error": "invalid_code", "message": str(e)}), 400

    user.email_verified = True
    log_action("verify_email", "user", user.id)
    db.session.commit()
    return jsonify({"message": "Email verified successfully. You can now log in."})


@bp.post("/resend-verification")
@limiter.limit("5 per hour")
def resend_verification():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email"])
    email = (data["email"] or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    # Generic response regardless of whether the account exists or is
    # already verified, to avoid leaking account existence.
    generic = {"message": "If that email requires verification, a new code has been sent."}
    if user is None or user.email_verified:
        return jsonify(generic)

    code = issue_otp(user, "signup_verification")
    db.session.commit()
    send_otp_email(user.email, code, "signup_verification")
    return jsonify(generic)


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email", "password"])
    email = (data["email"] or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    generic_error = ("invalid_credentials", "Incorrect email or password")

    if user is None:
        return jsonify({"error": generic_error[0], "message": generic_error[1]}), 401

    if user.locked_until:
        from app.models.base import as_aware
        if as_aware(user.locked_until) > now_pk():
            return jsonify({"error": "account_locked", "message": "Account temporarily locked. Try again later."}), 423

    if not user.is_active_flag:
        return jsonify({"error": generic_error[0], "message": generic_error[1]}), 401

    if user.auth_provider == "google":
        return jsonify({
            "error": "google_account",
            "message": "This account uses Google Sign-In. Please continue with Google to log in.",
        }), 401

    if not user.check_password(data["password"]):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now_pk() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        db.session.commit()
        return jsonify({"error": generic_error[0], "message": generic_error[1]}), 401

    if not user.email_verified:
        return jsonify({
            "error": "email_not_verified",
            "message": "Please verify your email before logging in.",
            "email": user.email,
        }), 403

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now_pk()
    login_user(user, remember=bool(data.get("remember")))
    session.permanent = True
    log_action("login", "user", user.id)
    db.session.commit()

    return jsonify({"user": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    log_action("logout", "user", current_user.id)
    db.session.commit()
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out"})


@bp.get("/me")
@login_required_api
def me():
    data = current_user.to_dict()
    if current_user.role == "customer" and current_user.customer_profile:
        data["phone"] = current_user.customer_profile.phone
        data["location"] = current_user.customer_profile.address
        data["profile_complete"] = current_user.customer_profile.profile_complete
    return jsonify({"user": data})


@bp.patch("/profile")
@login_required_api
def update_profile():
    """Self-service profile edit. Deliberately narrow: name and (for
    customers) phone/location only. Role, email, and active status are not
    editable here - those remain admin-controlled via /api/users.

    Also used as the "Complete Your Profile" endpoint after Google
    Sign-In, where phone and location are required (Google never
    supplies either), so any supplied value is independently re-validated
    server-side regardless of what the frontend already checked."""
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"]:
        current_user.name = data["name"].strip()[:120]

    if current_user.role == "customer" and current_user.customer_profile:
        customer = current_user.customer_profile
        if "phone" in data:
            customer.phone = validate_customer_phone(data["phone"])
        if "location" in data:
            customer.address = validate_location(data["location"])
        customer.full_name = current_user.name

    log_action("update_profile", "user", current_user.id)
    db.session.commit()
    data = current_user.to_dict()
    if current_user.role == "customer" and current_user.customer_profile:
        data["phone"] = current_user.customer_profile.phone
        data["location"] = current_user.customer_profile.address
        data["profile_complete"] = current_user.customer_profile.profile_complete
    return jsonify({"user": data})


@bp.post("/change-password")
@login_required_api
@limiter.limit("5 per hour")
def change_password():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["current_password", "new_password"])

    if not current_user.check_password(data["current_password"]):
        return jsonify({"error": "invalid_credentials", "message": "Current password is incorrect"}), 401

    validate_password_strength(data["new_password"])
    current_user.set_password(data["new_password"])
    current_user.must_change_password = False
    log_action("change_password", "user", current_user.id)
    db.session.commit()
    return jsonify({"message": "Password updated"})


@bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    """Issues a temporary password and emails it, rather than a reset
    link, per the required flow. The response is identical whether or not
    the email is registered, so this endpoint cannot be used to enumerate
    accounts."""
    data = request.get_json(silent=True) or {}
    require_fields(data, ["email"])
    email = (data["email"] or "").strip().lower()

    generic = {"message": "If that email is registered, a temporary password has been sent."}

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_active_flag:
        return jsonify(generic)

    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.must_change_password = True
    user.failed_login_count = 0
    user.locked_until = None
    log_action("forgot_password_temp_issued", "user", user.id)
    db.session.commit()

    send_temporary_password_email(user.email, temp_password)
    return jsonify(generic)


@bp.get("/google/config")
def google_config():
    """The frontend calls this to decide whether to render the
    "Continue with Google" button at all - never showing a button that
    would just fail because credentials aren't configured."""
    return jsonify({"enabled": google_oauth.is_configured()})


@bp.get("/google/login")
@limiter.limit("20 per hour")
def google_login():
    if not google_oauth.is_configured():
        return jsonify({"error": "not_configured", "message": "Google Sign-In is not configured"}), 404

    state = google_oauth.generate_state()
    session["oauth_state"] = state
    return redirect(google_oauth.build_consent_url(state))


@bp.get("/google/callback")
def google_callback():
    frontend_url = current_app_config_frontend_url()

    if not google_oauth.is_configured():
        return redirect(f"{frontend_url}/login?error=oauth_unavailable")

    expected_state = session.pop("oauth_state", None)
    submitted_state = request.args.get("state")
    code = request.args.get("code")

    if not code or not submitted_state or not expected_state or not secrets.compare_digest(submitted_state, expected_state):
        return redirect(f"{frontend_url}/login?error=oauth_failed")

    try:
        identity = google_oauth.exchange_code_for_identity(code)
    except google_oauth.GoogleOAuthError:
        return redirect(f"{frontend_url}/login?error=oauth_failed")

    user = User.query.filter_by(email=identity["email"]).first()

    if user is None:
        # New account, created directly from a verified Google identity -
        # no separate email-OTP step is needed since Google already
        # verified ownership of the address.
        user = User(
            name=identity["name"][:120],
            email=identity["email"],
            role="customer",
            email_verified=True,
            auth_provider="google",
            google_id=identity["google_id"],
        )
        # A random, never-disclosed password satisfies the NOT NULL
        # column and guarantees password-based login can never succeed
        # for this account - only /google/login can authenticate it.
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.flush()
        db.session.add(Customer(user_id=user.id, full_name=identity["name"][:120]))
        log_action("register_via_google", "user", user.id)
    else:
        # Existing account with this email: Google has already proven
        # ownership of the address, so it's safe to treat this as a
        # legitimate login and (if needed) link the Google identity.
        if not user.is_active_flag:
            return redirect(f"{frontend_url}/login?error=oauth_failed")
        if user.google_id is None:
            user.google_id = identity["google_id"]
        user.email_verified = True

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now_pk()
    login_user(user, remember=False)
    session.permanent = True
    log_action("login_via_google", "user", user.id)
    db.session.commit()

    return redirect(f"{frontend_url}/oauth/callback")


def current_app_config_frontend_url():
    from flask import current_app
    return current_app.config["FRONTEND_URL"].rstrip("/")
