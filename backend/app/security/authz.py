"""
Role-based and object-level authorization.

RBAC: use @roles_required(...) on routes to restrict by role.
Object-level: use the can_access_* helpers before returning/mutating any
specific record. Knowing an ID must never be sufficient on its own -
every one of these checks the actual relationship between the current
user and the record.
"""
from functools import wraps
from flask import abort
from flask_login import current_user

from app.models import Assignment


class Forbidden(Exception):
    pass


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def login_required_api(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return fn(*args, **kwargs)
    return wrapper


def _is_staff():
    return current_user.role in ("supervisor", "admin")


def can_access_service_request(sr):
    if current_user.role == "admin" or current_user.role == "supervisor":
        return True
    if current_user.role == "customer":
        return sr.customer.user_id == current_user.id
    if current_user.role == "agent":
        return Assignment.query.filter_by(
            service_request_id=sr.id, agent_id=current_user.id, active=True
        ).first() is not None
    return False


def can_manage_service_request(sr):
    """Status changes, assignment-affecting edits."""
    if current_user.role in ("admin", "supervisor"):
        return True
    if current_user.role == "agent":
        return Assignment.query.filter_by(
            service_request_id=sr.id, agent_id=current_user.id, active=True
        ).first() is not None
    return False


def can_access_complaint(c):
    if current_user.role in ("admin", "supervisor"):
        return True
    if current_user.role == "customer":
        return c.customer.user_id == current_user.id
    if current_user.role == "agent":
        # agents may view complaints tied to requests they're assigned to
        if c.service_request_id is None:
            return False
        return Assignment.query.filter_by(
            service_request_id=c.service_request_id, agent_id=current_user.id, active=True
        ).first() is not None
    return False


def can_access_message_thread(msg):
    if current_user.role == "admin":
        return True
    return current_user.id in (msg.sender_id, msg.receiver_id)


def can_access_invoice(invoice):
    if current_user.role in ("admin", "supervisor"):
        return True
    if current_user.role == "customer":
        return invoice.service_request.customer.user_id == current_user.id
    return False


def can_access_notification(notif):
    return current_user.role == "admin" or notif.user_id == current_user.id


def can_access_document(doc, sr=None):
    sr = sr or doc.service_request
    return can_access_service_request(sr)
