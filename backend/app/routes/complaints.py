from flask import Blueprint, request, jsonify, abort
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import Complaint, ComplaintStatusHistory, ServiceRequest, Notification, Customer
from app.models.base import now_pk, to_pk_iso
from app.security.authz import login_required_api, roles_required, can_access_complaint
from app.services.audit import log_action
from app.services.workflow import assert_valid_complaint_transition, generate_complaint_reference
from app.utils.validation import (
    require_fields, validate_severity, validate_date, validate_contact_number,
    parse_pagination, sanitize_text, ValidationError,
)

bp = Blueprint("complaints", __name__)

COMPLAINT_CATEGORIES = {"delay", "quality", "staff_behavior", "billing", "incomplete_work", "other"}


def _visible_query():
    q = Complaint.query
    if current_user.role == "customer":
        q = q.filter(Complaint.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        from app.models import Assignment
        request_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        q = q.filter(Complaint.service_request_id.in_(request_ids))
    return q


def _serialize_for_list(c):
    data = c.to_dict()
    data["customer_name"] = c.customer.full_name if c.customer else None
    return data


@bp.get("")
@login_required_api
def list_complaints():
    page, page_size = parse_pagination(request.args)
    q = _visible_query()
    status = request.args.get("status")
    if status:
        q = q.filter(Complaint.status == status)
    severity = request.args.get("severity")
    if severity:
        q = q.filter(Complaint.severity == severity)
    category = request.args.get("category")
    if category:
        q = q.filter(Complaint.category == category)
    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        q = q.filter(Complaint.customer_id == customer_id)

    date_from = validate_date(request.args.get("date_from"), "date_from")
    if date_from:
        q = q.filter(db.func.date(Complaint.created_at) >= date_from)
    date_to = validate_date(request.args.get("date_to"), "date_to")
    if date_to:
        q = q.filter(db.func.date(Complaint.created_at) <= date_to)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        q = q.join(Customer, Complaint.customer_id == Customer.id).filter(
            or_(
                Complaint.reference_number.ilike(like),
                Complaint.description.ilike(like),
                Customer.full_name.ilike(like),
            )
        )

    sort = request.args.get("sort", "-created_at")
    sort_field = sort.lstrip("-")
    allowed_sorts = {"created_at", "severity", "status"}
    if sort_field not in allowed_sorts:
        sort_field = "created_at"
    column = getattr(Complaint, sort_field)
    column = column.desc() if sort.startswith("-") else column.asc()

    total = q.order_by(None).count()
    items = q.order_by(column).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({"items": [_serialize_for_list(c) for c in items], "page": page, "page_size": page_size, "total": total})


@bp.post("")
@roles_required("customer")
def create_complaint():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["description", "category", "severity", "requested_resolution", "contact_number"])

    category = data["category"]
    if category not in COMPLAINT_CATEGORIES:
        raise ValidationError({"category": f"Must be one of: {', '.join(sorted(COMPLAINT_CATEGORIES))}"})
    severity = data["severity"]
    validate_severity(severity)
    contact_number = validate_contact_number(data["contact_number"])

    service_request_id = data.get("service_request_id")
    if service_request_id:
        sr = ServiceRequest.query.get_or_404(service_request_id)
        if sr.customer_id != current_user.customer_profile.id:
            abort(403, description="You may only lodge complaints against your own requests")

    complaint = Complaint(
        reference_number=generate_complaint_reference(),
        customer_id=current_user.customer_profile.id,
        service_request_id=service_request_id,
        description=sanitize_text(data["description"], 5000),
        category=category,
        severity=severity,
        requested_resolution=sanitize_text(data.get("requested_resolution"), 2000),
        contact_number=contact_number,
        status="open",
    )
    db.session.add(complaint)
    db.session.flush()
    db.session.add(ComplaintStatusHistory(complaint_id=complaint.id, old_status=None, new_status="open", changed_by=current_user.id))
    log_action("create_complaint", "complaint", complaint.id)
    db.session.commit()
    return jsonify({"complaint": complaint.to_dict()}), 201


@bp.get("/export")
@login_required_api
def export_complaints_csv():
    """CSV export of complaints, honoring the same visibility/filter rules
    as the list endpoint."""
    import csv
    import io
    from flask import Response

    q = _visible_query()
    status = request.args.get("status")
    if status:
        q = q.filter(Complaint.status == status)
    severity = request.args.get("severity")
    if severity:
        q = q.filter(Complaint.severity == severity)

    rows = q.order_by(Complaint.created_at.desc()).limit(5000).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Reference", "Customer", "Category", "Severity", "Status", "Created At", "Resolved At"])
    for c in rows:
        writer.writerow([
            c.reference_number,
            c.customer.full_name if c.customer else "",
            c.category, c.severity, c.status,
            to_pk_iso(c.created_at),
            to_pk_iso(c.resolved_at) or "",
        ])

    log_action("export_complaints_csv", "complaint", None, details=f"count={len(rows)}")
    db.session.commit()

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=complaints_export.csv"},
    )


@bp.get("/<int:complaint_id>")
@login_required_api
def get_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    if not can_access_complaint(complaint):
        abort(403)
    return jsonify({
        "complaint": complaint.to_dict(),
        "status_history": [h.to_dict() for h in complaint.status_history],
        "escalations": [e.to_dict() for e in complaint.escalations],
    })


@bp.post("/<int:complaint_id>/status")
@roles_required("admin", "supervisor")
def change_complaint_status(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["status"])
    new_status = data["status"]

    if new_status in ("resolved", "closed") and not (complaint.resolution or data.get("resolution")):
        abort(409, description="A complaint cannot be resolved or closed without a recorded resolution")

    assert_valid_complaint_transition(complaint.status, new_status)

    old_status = complaint.status
    complaint.status = new_status
    if data.get("resolution"):
        complaint.resolution = sanitize_text(data["resolution"], 3000)
    if new_status == "resolved":
        complaint.resolved_at = now_pk()

    db.session.add(ComplaintStatusHistory(complaint_id=complaint.id, old_status=old_status, new_status=new_status, changed_by=current_user.id))
    db.session.add(Notification(
        user_id=complaint.customer.user_id, type="complaint_update",
        message=f"Your complaint {complaint.reference_number} is now '{new_status}'.",
    ))
    log_action("change_complaint_status", "complaint", complaint.id, details=f"{old_status}->{new_status}")
    db.session.commit()
    return jsonify({"complaint": complaint.to_dict()})


# NOTE: Customers are intentionally not able to reopen a complaint - once a
# complaint reaches 'resolved'/'closed' it stays there unless a supervisor
# or admin acts on it via change_complaint_status(). There is deliberately
# no customer-facing reopen endpoint.
