from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, Feedback
from app.security.authz import roles_required, login_required_api, can_access_service_request
from app.services.audit import log_action
from app.utils.validation import require_fields, sanitize_text

bp = Blueprint("feedback", __name__)


@bp.post("/service-requests/<int:request_id>")
@roles_required("customer")
def submit_feedback(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if sr.customer_id != current_user.customer_profile.id:
        abort(403)
    if sr.status not in ("resolved", "closed"):
        abort(409, description="Feedback can only be submitted after the request is resolved")
    if Feedback.query.filter_by(service_request_id=sr.id).first():
        abort(409, description="Feedback has already been submitted for this request")

    data = request.get_json(silent=True) or {}
    require_fields(data, ["rating"])
    try:
        rating = int(data["rating"])
    except (TypeError, ValueError):
        abort(400, description="rating must be an integer between 1 and 5")
    if rating < 1 or rating > 5:
        abort(400, description="rating must be between 1 and 5")

    feedback = Feedback(service_request_id=sr.id, rating=rating, comments=sanitize_text(data.get("comments"), 2000))
    db.session.add(feedback)
    log_action("submit_feedback", "feedback", None, details=f"request={sr.id}")
    db.session.commit()
    return jsonify({"feedback": feedback.to_dict()}), 201


@bp.get("/service-requests/<int:request_id>")
@login_required_api
def get_feedback(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    feedback = Feedback.query.filter_by(service_request_id=sr.id).first()
    return jsonify({"feedback": feedback.to_dict() if feedback else None})
