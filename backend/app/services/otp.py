import secrets
from datetime import timedelta

from flask import current_app
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.extensions import db
from app.models import EmailOtp
from app.models.base import as_aware, now_pk

_ph = PasswordHasher()


class OtpError(Exception):
    pass


def _generate_code(length: int) -> str:
    # Numeric codes are easiest for a person to type accurately from an
    # email; secrets.choice is CSPRNG-backed, not the non-cryptographic
    # `random` module.
    return "".join(secrets.choice("0123456789") for _ in range(length))


def issue_otp(user, purpose: str) -> str:
    """Invalidates any previous unused OTPs of the same purpose for this
    user, creates a new one, and returns the plaintext code (the only time
    it ever exists outside a hash) so the caller can email it."""
    EmailOtp.query.filter_by(user_id=user.id, purpose=purpose, used_at=None).update({
        "used_at": now_pk()  # mark superseded codes as consumed
    })

    code = _generate_code(current_app.config["OTP_LENGTH"])
    expiry_minutes = current_app.config["OTP_EXPIRY_MINUTES"]
    otp = EmailOtp(
        user_id=user.id,
        purpose=purpose,
        code_hash=_ph.hash(code),
        max_attempts=current_app.config["OTP_MAX_ATTEMPTS"],
        expires_at=now_pk() + timedelta(minutes=expiry_minutes),
    )
    db.session.add(otp)
    db.session.flush()
    return code


def verify_otp(user, purpose: str, submitted_code: str) -> bool:
    """Verifies a submitted code against the most recent unused OTP for
    this user/purpose. Raises OtpError with a safe, generic message on any
    failure (expired, exhausted, wrong code, none pending) - the exact
    reason is never distinguishable to the caller, which prevents an
    attacker from using error responses to narrow down a valid code."""
    otp = (
        EmailOtp.query.filter_by(user_id=user.id, purpose=purpose, used_at=None)
        .order_by(EmailOtp.created_at.desc())
        .first()
    )
    if otp is None:
        raise OtpError("Invalid or expired code")

    now = now_pk()
    if as_aware(otp.expires_at) < now:
        raise OtpError("Invalid or expired code")

    if otp.attempts >= otp.max_attempts:
        raise OtpError("Invalid or expired code")

    otp.attempts += 1

    try:
        _ph.verify(otp.code_hash, submitted_code)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        db.session.commit()
        raise OtpError("Invalid or expired code")

    otp.used_at = now
    db.session.commit()
    return True
