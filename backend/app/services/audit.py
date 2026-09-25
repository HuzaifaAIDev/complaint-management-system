from flask import request
from flask_login import current_user
from app.extensions import db
from app.models import AuditLog


def log_action(action, entity_type, entity_id=None, result="success", details=None):
    entry = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        ip_address=request.remote_addr if request else None,
        request_id=request.headers.get("X-Request-Id") if request else None,
        details=details,
    )
    db.session.add(entry)
    # Caller is responsible for committing as part of its own transaction.
