from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, Appointment
from app.security.authz import login_required_api, can_access_service_request, can_manage_service_request
from app.services.audit import log_action
from app.utils.validation import require_fields, validate_datetime, validate_choice, sanitize_text
from app.models.base import APPOINTMENT_STATUSES

bp = Blueprint("appointments", __name__)


@bp.post("/service-requests/<int:request_id>/appointments")
@login_required_api
def create_appointment(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_manage_service_request(sr):
        abort(403)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["scheduled_at"])
    scheduled_at = validate_datetime(data["scheduled_at"], "scheduled_at")

    appt = Appointment(
        service_request_id=sr.id,
        scheduled_at=scheduled_at,
        location=sanitize_text(data.get("location"), 255),
        assigned_staff_id=current_user.id if current_user.role == "agent" else data.get("assigned_staff_id"),
    )
    db.session.add(appt)
    if sr.status in ("assigned",):
        sr.status = "scheduled"
    log_action("create_appointment", "appointment", None, details=f"request={sr.id}")
    db.session.commit()
    return jsonify({"appointment": appt.to_dict()}), 201


@bp.get("/service-requests/<int:request_id>/appointments")
@login_required_api
def list_appointments(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    return jsonify({"items": [a.to_dict() for a in sr.appointments]})


@bp.patch("/appointments/<int:appointment_id>")
@login_required_api
def update_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    sr = ServiceRequest.query.get_or_404(appt.service_request_id)
    if not can_manage_service_request(sr):
        abort(403)

    data = request.get_json(silent=True) or {}
    if "scheduled_at" in data:
        appt.scheduled_at = validate_datetime(data["scheduled_at"], "scheduled_at")
    if "location" in data:
        appt.location = sanitize_text(data["location"], 255)
    if "status" in data:
        validate_choice(data["status"], APPOINTMENT_STATUSES, "status")
        appt.status = data["status"]

    log_action("update_appointment", "appointment", appt.id)
    db.session.commit()
    return jsonify({"appointment": appt.to_dict()})
