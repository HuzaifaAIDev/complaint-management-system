from flask import Blueprint, request, jsonify, abort, send_file
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db, limiter
from app.models import (
    ServiceRequest, ServiceCategory, RequestAttachment, RequestStatusHistory, Notification,
    Assignment, Customer, User, Appointment, WorkOrder, Complaint, Escalation,
)
from app.models.base import now_pk, to_pk_iso
from app.security.authz import login_required_api, roles_required, can_access_service_request, can_manage_service_request
from app.services.audit import log_action
from app.services.sla import compute_deadlines
from app.services.workflow import assert_valid_request_transition, generate_request_reference
from app.utils.files import validate_and_store, resolve_safe_path, UploadRejected
from app.utils.validation import (
    require_fields, validate_priority, validate_date, validate_datetime, validate_contact_number,
    validate_not_past_date, parse_pagination, sanitize_text, ValidationError,
)

bp = Blueprint("service_requests", __name__)

SLA_STATES = ("within_sla", "at_risk", "breached")


def _visible_query():
    q = ServiceRequest.query
    if current_user.role == "customer":
        q = q.filter(ServiceRequest.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        agent_request_ids = db.session.query(Assignment.service_request_id).filter_by(
            agent_id=current_user.id, active=True
        )
        q = q.filter(ServiceRequest.id.in_(agent_request_ids))
    # supervisor/admin see all
    return q


def _serialize_for_list(sr, now):
    """List views show a few denormalized display fields (customer name,
    category name, assigned agent) so the frontend never has to make N+1
    calls per row. This is purely presentational - every authorization
    decision already happened in _visible_query()/can_access_service_request."""
    data = sr.to_dict(now)
    data["customer_name"] = sr.customer.full_name if sr.customer else None
    data["category_name"] = sr.category.name if sr.category else None
    active_assignment = next((a for a in sr.assignments if a.active), None)
    data["assigned_agent_id"] = active_assignment.agent_id if active_assignment else None
    data["assigned_agent_name"] = active_assignment.agent.name if active_assignment and active_assignment.agent else None
    data["assigned_at"] = to_pk_iso(active_assignment.assigned_at) if active_assignment else None
    return data


@bp.get("")
@login_required_api
def list_requests():
    page, page_size = parse_pagination(request.args)
    q = _visible_query()

    status = request.args.get("status")
    if status:
        q = q.filter(ServiceRequest.status == status)
    priority = request.args.get("priority")
    if priority:
        q = q.filter(ServiceRequest.priority == priority)
    category_id = request.args.get("category_id", type=int)
    if category_id:
        q = q.filter(ServiceRequest.category_id == category_id)

    assigned_agent_id = request.args.get("assigned_agent_id", type=int)
    if assigned_agent_id:
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(
            agent_id=assigned_agent_id, active=True
        )
        q = q.filter(ServiceRequest.id.in_(assigned_ids))

    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        # Customers may only ever see their own id anyway (enforced by _visible_query),
        # but staff filtering by a specific customer is a legitimate operational need.
        q = q.filter(ServiceRequest.customer_id == customer_id)

    date_from = validate_date(request.args.get("date_from"), "date_from")
    if date_from:
        q = q.filter(db.func.date(ServiceRequest.created_at) >= date_from)
    date_to = validate_date(request.args.get("date_to"), "date_to")
    if date_to:
        q = q.filter(db.func.date(ServiceRequest.created_at) <= date_to)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        q = q.join(Customer, ServiceRequest.customer_id == Customer.id).filter(
            or_(
                ServiceRequest.reference_number.ilike(like),
                ServiceRequest.description.ilike(like),
                Customer.full_name.ilike(like),
            )
        )

    sla_status = request.args.get("sla_status")
    if sla_status:
        if sla_status not in SLA_STATES:
            raise ValidationError({"sla_status": f"Must be one of: {', '.join(SLA_STATES)}"})
        # SLA state is computed dynamically (deadline vs. now), so filter in Python
        # after a bounded fetch rather than in SQL - the candidate set is already
        # narrowed by every other filter above.
        now = now_pk()
        candidate_ids = [sr.id for sr in q.all() if sr.sla_state(now) == sla_status]
        q = ServiceRequest.query.filter(ServiceRequest.id.in_(candidate_ids))

    sort = request.args.get("sort", "-created_at")
    sort_field = sort.lstrip("-")
    allowed_sorts = {"created_at", "updated_at", "priority", "status", "sla_resolution_deadline"}
    if sort_field not in allowed_sorts:
        sort_field = "created_at"
    column = getattr(ServiceRequest, sort_field)
    column = column.desc() if sort.startswith("-") else column.asc()

    total = q.order_by(None).count()
    items = q.order_by(column).offset((page - 1) * page_size).limit(page_size).all()
    now = now_pk()
    return jsonify({
        "items": [_serialize_for_list(r, now) for r in items],
        "page": page, "page_size": page_size, "total": total,
    })


@bp.post("")
@roles_required("customer")
@limiter.limit("20 per hour")
def create_request():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["category_id", "description", "location", "priority", "preferred_date", "contact_number"])
    category = ServiceCategory.query.get_or_404(data["category_id"])
    if not category.is_active:
        abort(400, description="This service category is not currently available")

    priority = data["priority"]
    validate_priority(priority)
    contact_number = validate_contact_number(data["contact_number"])
    # Preferred date is the customer's chosen date for the service to take
    # place. It must be today (Pakistan time) or later - never a date that
    # has already passed.
    preferred_date = validate_not_past_date(data["preferred_date"], "preferred_date")

    now = now_pk()
    response_dl, resolution_dl = compute_deadlines(category.id, priority, now)

    sr = ServiceRequest(
        reference_number=generate_request_reference(),
        customer_id=current_user.customer_profile.id,
        category_id=category.id,
        description=sanitize_text(data["description"], 5000),
        location=sanitize_text(data.get("location"), 255),
        priority=priority,
        preferred_date=preferred_date,
        contact_number=contact_number,
        status="submitted",
        sla_response_deadline=response_dl,
        sla_resolution_deadline=resolution_dl,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.session.add(sr)
    db.session.flush()
    db.session.add(RequestStatusHistory(service_request_id=sr.id, old_status=None, new_status="submitted", changed_by=current_user.id))
    log_action("create_service_request", "service_request", sr.id)
    db.session.commit()
    return jsonify({"service_request": sr.to_dict()}), 201


@bp.get("/<int:request_id>")
@login_required_api
def get_request(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    active_assignment = next((a for a in sr.assignments if a.active), None)
    return jsonify({
        "service_request": _serialize_for_list(sr, now_pk()),
        "customer": sr.customer.to_dict() if sr.customer else None,
        "category": sr.category.to_dict() if sr.category else None,
        "assigned_agent": {"id": active_assignment.agent_id, "name": active_assignment.agent.name} if active_assignment and active_assignment.agent else None,
        "attachments": [a.to_dict() for a in sr.attachments],
        "status_history": [h.to_dict() for h in sr.status_history],
    })


@bp.patch("/<int:request_id>")
@login_required_api
def update_request(request_id):
    """Limited field edits (not status/assignment - those have dedicated
    endpoints so that mass-assignment of privileged fields is impossible)."""
    sr = ServiceRequest.query.get_or_404(request_id)
    data = request.get_json(silent=True) or {}

    is_owner_customer = current_user.role == "customer" and sr.customer_id == current_user.customer_profile.id
    if not (is_owner_customer or can_manage_service_request(sr) or current_user.role == "admin"):
        abort(403)

    # Customers may only edit their own request pre-assignment, and only non-privileged fields.
    if is_owner_customer and sr.status not in ("submitted",):
        abort(409, description="Request can no longer be edited by the customer")

    if "description" in data:
        sr.description = sanitize_text(data["description"], 5000)
    if "location" in data:
        sr.location = sanitize_text(data["location"], 255)
    # NOTE: priority/category changes go through PATCH
    # /service-requests/<id>/assignments instead of this endpoint, since
    # changing either must re-validate the agent/category pairing, recompute
    # the SLA due date/time from the current server clock, write a
    # dedicated audit entry, and notify the assigned agent - all of which
    # live in one place in assignments.py rather than being duplicated here.

    sr.updated_by = current_user.id
    log_action("update_service_request", "service_request", sr.id)
    db.session.commit()
    return jsonify({"service_request": sr.to_dict()})


@bp.post("/<int:request_id>/status")
@login_required_api
def change_status(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_manage_service_request(sr):
        abort(403)

    data = request.get_json(silent=True) or {}
    require_fields(data, ["status"])
    new_status = data["status"]

    # Customers can only request reopening or confirm resolution via dedicated endpoints, not here.
    if current_user.role == "customer":
        abort(403)

    assert_valid_request_transition(sr.status, new_status)

    old_status = sr.status
    sr.status = new_status
    sr.updated_by = current_user.id
    now = now_pk()
    if new_status in ("assigned", "in_progress") and sr.responded_at is None:
        sr.responded_at = now
    if new_status == "resolved":
        sr.resolved_at = now

    db.session.add(RequestStatusHistory(
        service_request_id=sr.id, old_status=old_status, new_status=new_status,
        changed_by=current_user.id, note=sanitize_text(data.get("note"), 1000),
    ))
    db.session.add(Notification(
        user_id=sr.customer.user_id, type="status_change",
        message=f"Your request {sr.reference_number} is now '{new_status}'.",
    ))
    log_action("change_request_status", "service_request", sr.id, details=f"{old_status}->{new_status}")
    db.session.commit()
    return jsonify({"service_request": sr.to_dict()})


@bp.post("/<int:request_id>/confirm")
@roles_required("customer")
def confirm_resolution(request_id):
    """Customer confirms resolution and closes the request. Customers are
    intentionally not able to reopen a request from here - once closed it
    stays closed unless a supervisor/admin acts on it separately."""
    sr = ServiceRequest.query.get_or_404(request_id)
    if sr.customer_id != current_user.customer_profile.id:
        abort(403)

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action != "confirm":
        abort(400, description="action must be 'confirm'")

    new_status = "closed"
    assert_valid_request_transition(sr.status, new_status)

    old_status = sr.status
    sr.status = new_status
    sr.updated_by = current_user.id
    db.session.add(RequestStatusHistory(
        service_request_id=sr.id, old_status=old_status, new_status=new_status,
        changed_by=current_user.id, note=sanitize_text(data.get("note"), 1000),
    ))
    log_action("customer_confirm_request", "service_request", sr.id, details=f"{old_status}->{new_status}")
    db.session.commit()
    return jsonify({"service_request": sr.to_dict()})


@bp.post("/<int:request_id>/attachments")
@login_required_api
@limiter.limit("30 per hour")
def upload_attachment(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    # Agents and supervisors are view-only for attachments - they can see
    # and download what's there, but never add or replace files. Only the
    # customer who owns the request and admins may upload.
    if current_user.role in ("agent", "supervisor"):
        abort(403, description="Agents and supervisors cannot upload attachments; view only")

    file_storage = request.files.get("file")
    meta = validate_and_store(file_storage, subdirectory=f"requests/{sr.id}")
    attachment = RequestAttachment(
        service_request_id=sr.id, uploaded_by=current_user.id, **meta,
    )
    db.session.add(attachment)
    log_action("upload_attachment", "request_attachment", None, details=f"request_id={sr.id}")
    db.session.commit()
    return jsonify({"attachment": attachment.to_dict()}), 201


@bp.get("/board")
@roles_required("admin", "supervisor", "agent")
def board_view():
    """Kanban board data: requests grouped by status, scoped by the same
    visibility rules as the regular list endpoint. Customers don't get a
    board view - this is an operational tool, not a customer-facing one."""
    from app.models.base import REQUEST_STATUSES
    q = _visible_query().filter(ServiceRequest.status != "reopened")
    now = now_pk()

    columns = {s: [] for s in ("submitted", "assigned", "scheduled", "in_progress", "pending_customer", "resolved", "closed")}
    for sr in q.order_by(ServiceRequest.priority.desc(), ServiceRequest.created_at.desc()).all():
        if sr.status not in columns:
            continue
        active_assignment = next((a for a in sr.assignments if a.active), None)
        columns[sr.status].append({
            "id": sr.id,
            "reference_number": sr.reference_number,
            "customer_name": sr.customer.full_name if sr.customer else None,
            "category_name": sr.category.name if sr.category else None,
            "priority": sr.priority,
            "assigned_agent_name": active_assignment.agent.name if active_assignment and active_assignment.agent else None,
            "sla_state": sr.sla_state(now),
        })

    return jsonify({"columns": columns})


@bp.get("/export")
@login_required_api
def export_requests_csv():
    """CSV export of service requests, honoring the exact same visibility
    and filter rules as the list endpoint - an export can never surface
    more than the equivalent list view would."""
    import csv
    import io
    from flask import Response

    q = _visible_query()
    status = request.args.get("status")
    if status:
        q = q.filter(ServiceRequest.status == status)
    priority = request.args.get("priority")
    if priority:
        q = q.filter(ServiceRequest.priority == priority)
    category_id = request.args.get("category_id", type=int)
    if category_id:
        q = q.filter(ServiceRequest.category_id == category_id)
    date_from = validate_date(request.args.get("date_from"), "date_from")
    if date_from:
        q = q.filter(db.func.date(ServiceRequest.created_at) >= date_from)
    date_to = validate_date(request.args.get("date_to"), "date_to")
    if date_to:
        q = q.filter(db.func.date(ServiceRequest.created_at) <= date_to)

    rows = q.order_by(ServiceRequest.created_at.desc()).limit(5000).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Reference", "Customer", "Category", "Priority", "Status", "Created At", "Resolved At", "SLA Breached"])
    now = now_pk()
    for r in rows:
        writer.writerow([
            r.reference_number,
            r.customer.full_name if r.customer else "",
            r.category.name if r.category else "",
            r.priority, r.status,
            to_pk_iso(r.created_at),
            to_pk_iso(r.resolved_at) or "",
            "Yes" if r.is_breached(now) else "No",
        ])

    log_action("export_service_requests_csv", "service_request", None, details=f"count={len(rows)}")
    db.session.commit()

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=service_requests_export.csv"},
    )


@bp.get("/<int:request_id>/attachments/<int:attachment_id>/download")
@login_required_api
def download_attachment(request_id, attachment_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)
    attachment = RequestAttachment.query.filter_by(id=attachment_id, service_request_id=sr.id).first_or_404()
    try:
        path = resolve_safe_path(attachment.file_path)
    except UploadRejected:
        abort(404)
    log_action("download_attachment", "request_attachment", attachment.id)
    db.session.commit()
    return send_file(path, as_attachment=True, download_name=attachment.original_filename)


@bp.get("/<int:request_id>/timeline")
@login_required_api
def request_timeline(request_id):
    """A single chronological view of everything that happened to a request,
    assembled from the existing history tables (status history, assignments,
    appointments, work orders, linked complaints/escalations) rather than a
    separate duplicate timeline table."""
    sr = ServiceRequest.query.get_or_404(request_id)
    if not can_access_service_request(sr):
        abort(403)

    events = []

    for h in sr.status_history:
        events.append({
            "type": "status_change" if h.old_status else "created",
            "label": f"Status changed to {h.new_status.replace('_', ' ')}" if h.old_status else "Request created",
            "status": h.new_status,
            "user_id": h.changed_by,
            "note": h.note,
            "at": to_pk_iso(h.changed_at),
        })

    for a in sr.assignments:
        events.append({
            "type": "assignment",
            "label": f"Assigned to {a.agent.name}" if a.agent else "Assigned",
            "user_id": a.assigned_by,
            "at": to_pk_iso(a.assigned_at),
        })

    for appt in sr.appointments:
        events.append({
            "type": "appointment",
            "label": f"Appointment {appt.status} for {appt.scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            "at": to_pk_iso(appt.created_at),
        })

    for wo in sr.work_orders:
        events.append({"type": "work_order", "label": f"Work order opened (status: {wo.status})", "at": to_pk_iso(wo.created_at)})
        if wo.completed_at:
            events.append({"type": "work_order", "label": "Work order completed", "at": to_pk_iso(wo.completed_at)})

    linked_complaints = Complaint.query.filter_by(service_request_id=sr.id).all()
    for c in linked_complaints:
        events.append({"type": "complaint", "label": f"Complaint {c.reference_number} filed", "at": to_pk_iso(c.created_at)})
        for esc in c.escalations:
            events.append({
                "type": "escalation",
                "label": f"Escalated ({esc.escalation_type.replace('_', ' ')}) to supervisor",
                "at": to_pk_iso(esc.escalated_at),
            })

    now = now_pk()
    sla_state = sr.sla_state(now)
    if sla_state == "breached" and sr.sla_resolution_deadline:
        events.append({"type": "sla_breach", "label": "SLA resolution deadline breached", "at": to_pk_iso(sr.sla_resolution_deadline)})
    elif sla_state == "at_risk":
        events.append({"type": "sla_risk", "label": "SLA approaching deadline", "at": to_pk_iso(now)})

    events.sort(key=lambda e: e["at"])
    return jsonify({"events": events})
