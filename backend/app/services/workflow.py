import uuid
from flask import current_app

from app.models.base import REQUEST_TRANSITIONS, COMPLAINT_TRANSITIONS, now_pk


class InvalidTransition(Exception):
    pass


def assert_valid_request_transition(old_status, new_status):
    allowed = REQUEST_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise InvalidTransition(f"Cannot move service request from '{old_status}' to '{new_status}'")


def assert_valid_complaint_transition(old_status, new_status):
    allowed = COMPLAINT_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise InvalidTransition(f"Cannot move complaint from '{old_status}' to '{new_status}'")


def generate_request_reference():
    prefix = current_app.config["REQUEST_REF_PREFIX"]
    year = now_pk().year
    return f"{prefix}-{year}-{uuid.uuid4().hex[:8].upper()}"


def generate_complaint_reference():
    year = now_pk().year
    return f"CMP-{year}-{uuid.uuid4().hex[:8].upper()}"


def generate_invoice_number():
    year = now_pk().year
    return f"INV-{year}-{uuid.uuid4().hex[:8].upper()}"
