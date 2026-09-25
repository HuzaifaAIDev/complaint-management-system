from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import Complaint, Escalation, User, Notification
from app.security.authz import roles_required, login_required_api, can_access_complaint
from app.services.audit import log_action
from app.utils.validation import require_fields, validate_choice, sanitize_text
from app.models.base import ESCALATION_TYPES, now_pk

bp = Blueprint("escalations", __name__)


@bp.post("/complaints/<int:complaint_id>/escalations")
@roles_required("admin", "supervisor", "agent")
def create_escalation(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["escalated_to", "reason"])

    target = User.query.get_or_404(data["escalated_to"])
    if target.role not in ("supervisor", "admin"):
        abort(400, description="Escalations must be directed to a supervisor or administrator")

    escalation_type = data.get("escalation_type", "other")
    validate_choice(escalation_type, ESCALATION_TYPES, "escalation_type")

    escalation = Escalation(
        complaint_id=complaint.id,
        escalation_type=escalation_type,
        escalated_by=current_user.id,
        escalated_to=target.id,
        reason=sanitize_text(data["reason"], 2000),
    )
    db.session.add(escalation)
    if complaint.status not in ("escalated",):
        from app.models import ComplaintStatusHistory
        old_status = complaint.status
        complaint.status = "escalated"
        db.session.add(ComplaintStatusHistory(complaint_id=complaint.id, old_status=old_status, new_status="escalated", changed_by=current_user.id))

    db.session.add(Notification(user_id=target.id, type="escalation", message=f"Complaint {complaint.reference_number} was escalated to you."))
    log_action("create_escalation", "escalation", None, details=f"complaint={complaint.id}")
    db.session.commit()
    return jsonify({"escalation": escalation.to_dict()}), 201


@bp.get("/complaints/<int:complaint_id>/escalations")
@login_required_api
def list_escalations(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    if not can_access_complaint(complaint):
        abort(403)
    return jsonify({"items": [e.to_dict() for e in complaint.escalations]})


@bp.post("/escalations/<int:escalation_id>/resolve")
@roles_required("admin", "supervisor")
def resolve_escalation(escalation_id):
    escalation = Escalation.query.get_or_404(escalation_id)
    if current_user.role == "supervisor" and escalation.escalated_to != current_user.id:
        abort(403)
    data = request.get_json(silent=True) or {}
    escalation.resolved_at = now_pk()
    escalation.resolution_notes = sanitize_text(data.get("resolution_notes"), 2000)
    log_action("resolve_escalation", "escalation", escalation.id)
    db.session.commit()
    return jsonify({"escalation": escalation.to_dict()})
