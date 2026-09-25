from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import Customer
from app.security.authz import roles_required, login_required_api
from app.services.audit import log_action
from app.utils.validation import parse_pagination, validate_customer_phone, validate_location

bp = Blueprint("customers", __name__)


@bp.get("")
@roles_required("admin", "supervisor", "agent")
def list_customers():
    page, page_size = parse_pagination(request.args)
    q = Customer.query
    total = q.count()
    items = q.order_by(Customer.id).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({"items": [c.to_dict() for c in items], "page": page, "page_size": page_size, "total": total})


@bp.get("/me")
@login_required_api
def my_profile():
    if current_user.role != "customer" or not current_user.customer_profile:
        abort(404)
    return jsonify({"customer": current_user.customer_profile.to_dict()})


@bp.get("/<int:customer_id>")
@login_required_api
def get_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if current_user.role == "customer" and customer.user_id != current_user.id:
        abort(403)
    elif current_user.role not in ("admin", "supervisor", "agent", "customer"):
        abort(403)
    return jsonify({"customer": customer.to_dict()})


@bp.get("/<int:customer_id>/summary")
@login_required_api
def customer_summary(customer_id):
    """Customer 360: aggregated operational summary plus request/complaint
    history for one customer. Staff roles may view any customer; a
    customer may only view their own summary - never another customer's."""
    customer = Customer.query.get_or_404(customer_id)
    if current_user.role == "customer" and customer.user_id != current_user.id:
        abort(403)
    elif current_user.role not in ("admin", "supervisor", "agent", "customer"):
        abort(403)

    from app.models import ServiceRequest, Complaint, Feedback
    from app.models.base import now_pk, to_pk_iso
    now = now_pk()

    requests_q = ServiceRequest.query.filter_by(customer_id=customer.id)
    if current_user.role == "agent":
        from app.models import Assignment
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        requests_q = requests_q.filter(ServiceRequest.id.in_(assigned_ids))

    all_requests = requests_q.order_by(ServiceRequest.created_at.desc()).all()
    open_statuses = ("submitted", "assigned", "scheduled", "in_progress", "pending_customer", "reopened")

    resolved_requests = [r for r in all_requests if r.resolved_at]
    from app.models.base import as_aware
    resolution_times = [(as_aware(r.resolved_at) - as_aware(r.created_at)).total_seconds() / 3600 for r in resolved_requests]
    breached_count = sum(1 for r in all_requests if r.is_breached(now))
    sla_eligible = [r for r in all_requests if r.sla_resolution_deadline]
    sla_compliance = round(100 * (1 - breached_count / len(sla_eligible)), 1) if sla_eligible else None

    complaints_q = Complaint.query.filter_by(customer_id=customer.id)
    all_complaints = complaints_q.order_by(Complaint.created_at.desc()).all()

    return jsonify({
        "customer": customer.to_dict(),
        "summary": {
            "total_requests": len(all_requests),
            "open_requests": sum(1 for r in all_requests if r.status in open_statuses),
            "resolved_requests": sum(1 for r in all_requests if r.status == "resolved"),
            "closed_requests": sum(1 for r in all_requests if r.status == "closed"),
            "total_complaints": len(all_complaints),
            "open_complaints": sum(1 for c in all_complaints if c.status not in ("resolved", "closed")),
            "sla_compliance_pct": sla_compliance,
            "average_resolution_hours": round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None,
        },
        "requests": [{
            "id": r.id, "reference_number": r.reference_number, "category_name": r.category.name if r.category else None,
            "priority": r.priority, "status": r.status, "created_at": to_pk_iso(r.created_at),
            "resolved_at": to_pk_iso(r.resolved_at),
        } for r in all_requests[:25]],
        "complaints": [{
            "id": c.id, "reference_number": c.reference_number, "category": c.category,
            "severity": c.severity, "status": c.status, "resolution": c.resolution,
        } for c in all_complaints[:25]],
    })


@bp.patch("/me")
@login_required_api
def update_my_profile():
    if current_user.role != "customer" or not current_user.customer_profile:
        abort(404)
    customer = current_user.customer_profile
    data = request.get_json(silent=True) or {}
    if "full_name" in data and data["full_name"]:
        customer.full_name = data["full_name"].strip()[:120]
    if "phone" in data:
        customer.phone = validate_customer_phone(data["phone"])
    if "location" in data:
        customer.address = validate_location(data["location"])
    log_action("update_customer_profile", "customer", customer.id)
    db.session.commit()
    return jsonify({"customer": customer.to_dict()})
