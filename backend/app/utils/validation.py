import re
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

from app.models.base import PRIORITIES, SEVERITIES, ROLES

_PHONE_RE = re.compile(r"^\+?[0-9 ()\-]{7,20}$")

# Pakistani mobile numbers: exactly 11 digits, numeric only, must start with "03"
# (e.g. 03001234567). Used for the contact number captured on every service
# request and complaint.
_PK_CONTACT_RE = re.compile(r"^03[0-9]{9}$")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, dict) else {"error": errors}
        super().__init__(str(self.errors))


def require_fields(data: dict, fields: list):
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        raise ValidationError({f: "This field is required" for f in missing})


def validate_email_field(value: str) -> str:
    try:
        result = validate_email(value, check_deliverability=False)
        return result.normalized
    except EmailNotValidError as e:
        raise ValidationError({"email": str(e)})


def validate_password_strength(value: str):
    if not isinstance(value, str) or len(value) < 8:
        raise ValidationError({"password": "Password must be at least 8 characters long"})
    if not re.search(r"[a-z]", value):
        raise ValidationError({"password": "Password must contain at least one lowercase letter"})
    if not re.search(r"[A-Z]", value):
        raise ValidationError({"password": "Password must contain at least one uppercase letter"})
    if not re.search(r"[0-9]", value):
        raise ValidationError({"password": "Password must contain at least one digit"})
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValidationError({"password": "Password must contain at least one special character"})


def validate_phone(value: str):
    if value and not _PHONE_RE.match(value):
        raise ValidationError({"phone": "Invalid phone number format"})


# Message text mandated for the customer-facing phone field (registration,
# Google "Complete Your Profile", and profile edits). Independently
# enforced here server-side - the frontend also validates immediately for
# UX, but the backend never trusts it.
PHONE_ERROR_MESSAGE = "Phone number must be exactly 11 digits and start with 03."


def validate_customer_phone(value: str, field_name: str = "phone") -> str:
    """Required Pakistani mobile number for customer accounts: exactly 11
    digits, numeric only, must start with '03' (e.g. 03001234567)."""
    if not value or not isinstance(value, str):
        raise ValidationError({field_name: PHONE_ERROR_MESSAGE})
    value = value.strip()
    if not _PK_CONTACT_RE.match(value):
        raise ValidationError({field_name: PHONE_ERROR_MESSAGE})
    return value


def validate_location(value: str, field_name: str = "location") -> str:
    if not value or not isinstance(value, str) or not value.strip():
        raise ValidationError({field_name: "Location is required"})
    return value.strip()[:255]


def validate_contact_number(value: str, field_name: str = "contact_number"):
    """Validates a Pakistani contact number: digits only, exactly 11 digits,
    and must start with '03' (e.g. 03001234567). Required for every
    service request and complaint so staff always have a way to reach
    the customer."""
    if not value or not isinstance(value, str):
        raise ValidationError({field_name: "Contact number is required"})
    value = value.strip()
    if not value.isdigit():
        raise ValidationError({field_name: "Contact number must contain digits only"})
    if not _PK_CONTACT_RE.match(value):
        raise ValidationError({field_name: "Contact number must be 11 digits and start with '03' (e.g. 03001234567)"})
    return value


def validate_choice(value, choices, field_name):
    if value not in choices:
        raise ValidationError({field_name: f"Must be one of: {', '.join(choices)}"})


def validate_role(value):
    validate_choice(value, ROLES, "role")


def validate_priority(value):
    validate_choice(value, PRIORITIES, "priority")


def validate_severity(value):
    validate_choice(value, SEVERITIES, "severity")


def validate_date(value: str, field_name="date"):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({field_name: "Expected format YYYY-MM-DD"})


def validate_not_past_date(value: str, field_name="preferred_date"):
    """Parses a YYYY-MM-DD date and rejects anything before today in
    Pakistan Standard Time - customers may pick today or any future date
    as their preferred service date, but never a date that has already
    passed."""
    from app.models.base import now_pk

    date_value = validate_date(value, field_name)
    if date_value is None:
        raise ValidationError({field_name: "This field is required"})
    today_pk = now_pk().date()
    if date_value < today_pk:
        raise ValidationError({field_name: "Preferred date cannot be in the past"})
    return date_value


def validate_datetime(value: str, field_name="datetime"):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ValidationError({field_name: "Expected ISO-8601 datetime"})


def parse_pagination(args):
    try:
        page = max(1, int(args.get("page", 1)))
    except (TypeError, ValueError):
        raise ValidationError({"page": "Must be a positive integer"})
    try:
        page_size = int(args.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        raise ValidationError({"page_size": "Must be a positive integer"})
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    return page, page_size


def sanitize_text(value: str, max_len: int = 5000) -> str:
    """Trims and length-limits free text. Output encoding/escaping happens
    at render time in React (which auto-escapes by default); this just
    guards against absurd payload sizes and stray control characters."""
    if value is None:
        return value
    value = value.strip()
    value = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return value[:max_len]
