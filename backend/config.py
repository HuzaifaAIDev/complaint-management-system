import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def _bool(env_val, default=False):
    if env_val is None:
        return default
    return str(env_val).strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(basedir, "dev.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.path.abspath(os.environ.get("UPLOAD_FOLDER", os.path.join(basedir, "uploads")))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 15)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx", "txt", "csv"}

    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get("PERMANENT_SESSION_LIFETIME_MINUTES", 60)))

    # "Remember me" on login uses Flask-Login's separate long-lived cookie
    # rather than extending the session itself, so a stolen/replayed
    # session cookie doesn't silently gain a month of validity too.
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.environ.get("REMEMBER_COOKIE_DAYS", 30)))

    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # --- Email (OTP verification, password reset) ---
    # All credentials come from the environment - never hard-coded or committed.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = _bool(os.environ.get("MAIL_USE_TLS"), True)
    MAIL_USE_SSL = _bool(os.environ.get("MAIL_USE_SSL"), False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", os.environ.get("MAIL_USERNAME", ""))
    # If no MAIL_SERVER is configured (e.g. local development without a real
    # SMTP account), OTP codes are logged server-side instead of emailed, so
    # the app remains fully usable without requiring real credentials.
    MAIL_SUPPRESS_SEND = not bool(os.environ.get("MAIL_SERVER"))

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", 10))
    OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))

    # --- Google Sign-In (OAuth 2.0 authorization code flow) ---
    # Both must be set for the "Continue with Google" option to appear -
    # the frontend checks /api/auth/google/config and hides the button
    # entirely when this isn't configured, rather than showing a button
    # that would fail.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    DEFAULT_RESPONSE_HOURS = int(os.environ.get("DEFAULT_RESPONSE_HOURS", 24))
    DEFAULT_RESOLUTION_HOURS = int(os.environ.get("DEFAULT_RESOLUTION_HOURS", 72))
    REQUEST_REF_PREFIX = os.environ.get("REQUEST_REF_PREFIX", "SR")

    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-me"


class TestingConfig(BaseConfig):
    TESTING = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or "testing-secret-key-not-for-production"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set in production")
        if "sqlite" in os.environ.get("DATABASE_URL", ""):
            raise RuntimeError("SQLite is not permitted in production; configure DATABASE_URL for PostgreSQL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
