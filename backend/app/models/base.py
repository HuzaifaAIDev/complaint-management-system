from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.extensions import db

# The whole application operates on Pakistan Standard Time. All timestamps -
# creation times, status changes, SLA deadlines, "now" comparisons, etc. -
# are generated and displayed in this timezone rather than UTC.
PK_TZ = ZoneInfo("Asia/Karachi")


def now_pk():
    """Current date/time in Pakistan Standard Time (Asia/Karachi)."""
    return datetime.now(PK_TZ)


# Kept as an alias so any code that still imports `utcnow` keeps working,
# but it now returns Pakistan local time rather than UTC.
utcnow = now_pk


def as_aware(dt):
    """SQLite does not preserve tzinfo on DateTime(timezone=True) columns,
    so values read back from it come back naive. Every timestamp this app
    writes is Pakistan local time, so naive datetimes are interpreted as
    Asia/Karachi (not UTC) so comparisons/arithmetic are always safe
    regardless of which database backend is in use."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=PK_TZ)
    return dt.astimezone(PK_TZ)


def to_pk_iso(dt):
    """Serialize a datetime to an ISO-8601 string expressed in Pakistan
    local time. Use this instead of calling `.isoformat()` directly so
    every timestamp sent to the frontend is unambiguously Pakistani time."""
    dt = as_aware(dt)
    if dt is None:
        return None
    return dt.isoformat()


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=now_pk, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_pk, onupdate=now_pk, nullable=False)


# --- Controlled vocabularies (kept as string constants + CHECK constraints rather than
# a separate lookup table, since the original spec does not call for lookup tables here) ---

ROLES = ("customer", "agent", "supervisor", "admin")

REQUEST_STATUSES = (
    "submitted", "assigned", "scheduled", "in_progress",
    "pending_customer", "resolved", "closed", "reopened",
)

# Allowed forward transitions for a service request. Reopening is only permitted
# from resolved/closed, per the original document's reopening requirement.
REQUEST_TRANSITIONS = {
    "submitted": {"assigned", "closed"},
    "assigned": {"scheduled", "in_progress", "submitted"},
    "scheduled": {"in_progress", "assigned"},
    "in_progress": {"pending_customer", "resolved"},
    "pending_customer": {"in_progress", "resolved"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"assigned", "in_progress"},
}

COMPLAINT_STATUSES = ("open", "in_review", "escalated", "resolved", "closed", "reopened")

COMPLAINT_TRANSITIONS = {
    "open": {"in_review", "escalated"},
    "in_review": {"escalated", "resolved"},
    "escalated": {"in_review", "resolved"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"in_review"},
}

PRIORITIES = ("low", "medium", "high", "urgent")
SEVERITIES = ("minor", "moderate", "major", "critical")
ESCALATION_TYPES = ("sla_breach", "severe_complaint", "supervisor_intervention", "other")
APPOINTMENT_STATUSES = ("scheduled", "completed", "cancelled", "rescheduled")
WORK_ORDER_STATUSES = ("open", "in_progress", "completed", "cancelled")
PAYMENT_STATUSES = ("pending", "paid", "failed", "refunded")
