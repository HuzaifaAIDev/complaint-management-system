from flask import Blueprint, request, jsonify
from app.models import AuditLog
from app.security.authz import roles_required
from app.utils.validation import parse_pagination

bp = Blueprint("audit_logs", __name__)


@bp.get("")
@roles_required("admin", "supervisor")
def list_audit_logs():
    """Read-only by design. There is intentionally no update/delete endpoint -
    audit records must be protected against unauthorized modification."""
    page, page_size = parse_pagination(request.args)
    q = AuditLog.query
    entity_type = request.args.get("entity_type")
    if entity_type:
        q = q.filter_by(entity_type=entity_type)
    user_id = request.args.get("user_id", type=int)
    if user_id:
        q = q.filter_by(user_id=user_id)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({"items": [a.to_dict() for a in items], "page": page, "page_size": page_size, "total": total})
