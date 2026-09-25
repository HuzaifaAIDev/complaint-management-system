from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, WorkOrder, WorkNote, Assignment
from app.security.authz import login_required_api, can_manage_service_request, can_access_service_request
from app.services.audit import log_action
from app.utils.validation import validate_choice, sanitize_text, require_fields
from app.models.base import WORK_ORDER_STATUSES, now_pk

bp = Blueprint("work_orders", __name__)


def _can_touch_work_order(wo):
    if current_user.role in ("admin", "supervisor"):
        return True
    if current_user.role == "agent":
        return wo.agent_id == current_user.id
    return False


@bp.post("/service-requests/<int:request_id>/work-orders")
@login_required_api
def create_work_order(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_manage_service_request(sr):
        abort(403)

    data = request.get_json(silent=True) or {}
    agent_id = current_user.id if current_user.role == "agent" else data.get("agent_id")
    if current_user.role != "agent" and not agent_id:
        abort(400, description="agent_id is required")
    if current_user.role != "agent":
        assignment = Assignment.query.filter_by(service_request_id=sr.id, agent_id=agent_id, active=True).first()
        if not assignment:
            abort(400, description="Target agent is not assigned to this request")

    wo = WorkOrder(service_request_id=sr.id, agent_id=agent_id, status="open")
    db.session.add(wo)
    if sr.status in ("assigned", "scheduled"):
        sr.status = "in_progress"
    log_action("create_work_order", "work_order", None, details=f"request={sr.id}")
    db.session.commit()
    return jsonify({"work_order": wo.to_dict()}), 201


@bp.get("/service-requests/<int:request_id>/work-orders")
@login_required_api
def list_work_orders(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    return jsonify({"items": [w.to_dict() for w in sr.work_orders]})


@bp.patch("/work-orders/<int:work_order_id>")
@login_required_api
def update_work_order(work_order_id):
    wo = WorkOrder.query.get_or_404(work_order_id)
    if not _can_touch_work_order(wo):
        abort(403)
    data = request.get_json(silent=True) or {}
    if "status" in data:
        validate_choice(data["status"], WORK_ORDER_STATUSES, "status")
        wo.status = data["status"]
        now = now_pk()
        if data["status"] == "in_progress" and not wo.started_at:
            wo.started_at = now
        if data["status"] == "completed":
            wo.completed_at = now
    log_action("update_work_order", "work_order", wo.id)
    db.session.commit()
    return jsonify({"work_order": wo.to_dict()})


@bp.post("/work-orders/<int:work_order_id>/notes")
@login_required_api
def add_work_note(work_order_id):
    wo = WorkOrder.query.get_or_404(work_order_id)
    if not _can_touch_work_order(wo):
        abort(403)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["note"])
    note = WorkNote(work_order_id=wo.id, note=sanitize_text(data["note"], 3000), added_by=current_user.id)
    db.session.add(note)
    log_action("add_work_note", "work_note", None, details=f"work_order={wo.id}")
    db.session.commit()
    return jsonify({"note": note.to_dict()}), 201


@bp.get("/work-orders/<int:work_order_id>/notes")
@login_required_api
def list_work_notes(work_order_id):
    wo = WorkOrder.query.get_or_404(work_order_id)
    sr = ServiceRequest.query.get(wo.service_request_id)
    if not can_access_service_request(sr):
        abort(403)
    return jsonify({"items": [n.to_dict() for n in wo.notes]})
