from flask_login import UserMixin
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from app.extensions import db
from app.models.base import TimestampMixin, ROLES, now_pk, to_pk_iso

_ph = PasswordHasher()


class User(db.Model, TimestampMixin, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), db.CheckConstraint(f"role IN {ROLES}"), nullable=False)
    is_active_flag = db.Column("is_active", db.Boolean, default=True, nullable=False)

    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    password_changed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    auth_provider = db.Column(db.String(20), default="local", nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=True)

    customer_profile = db.relationship("Customer", back_populates="user", uselist=False)

    # --- Flask-Login required property (avoid shadowing the DB column name is_active) ---
    @property
    def is_active(self):
        return self.is_active_flag

    def set_password(self, raw_password: str):
        self.password_hash = _ph.hash(raw_password)
        self.password_changed_at = now_pk()

    def _rehash_password(self, raw_password: str):
        """Used only for the automatic upgrade-on-login rehash. Does not
        count as a user-initiated password change."""
        self.password_hash = _ph.hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        try:
            ok = _ph.verify(self.password_hash, raw_password)
        except (VerifyMismatchError, InvalidHashError, ValueError):
            return False
        if ok and _ph.check_needs_rehash(self.password_hash):
            self._rehash_password(raw_password)
        return ok

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active_flag,
            "created_at": to_pk_iso(self.created_at),
            "last_login_at": to_pk_iso(self.last_login_at),
            "password_changed_at": to_pk_iso(self.password_changed_at),
            "email_verified": self.email_verified,
            "must_change_password": self.must_change_password,
            "auth_provider": self.auth_provider,
        }


class Customer(db.Model, TimestampMixin):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    # "phone" and "address" are the DB column names kept for migration
    # safety; the user-facing label for `address` is "Location" everywhere
    # in the API responses and the frontend (see to_dict() below).
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="customer_profile")

    @property
    def profile_complete(self) -> bool:
        """A customer's profile is only complete once they have a valid
        phone number and a location on file. Google sign-ups start out
        incomplete (Google never supplies these) and are routed to the
        Complete Your Profile screen until this is true."""
        return bool(self.phone) and bool(self.address)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "location": self.address,
            "profile_complete": self.profile_complete,
            "email": self.user.email if self.user else None,
        }


class EmailOtp(db.Model):
    """One-time codes for email verification and password reset.

    The code itself is never stored in plaintext - only its hash - so a
    database read alone can never yield a usable code. Codes are single
    purpose, single use, short-lived, and attempt-limited."""
    __tablename__ = "email_otps"

    OTP_PURPOSES = ("signup_verification", "password_reset")

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    purpose = db.Column(db.String(30), db.CheckConstraint(f"purpose IN {OTP_PURPOSES}"), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=5, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    user = db.relationship("User")
