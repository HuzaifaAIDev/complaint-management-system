from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import func

from app.extensions import db
from app.models import (
    ServiceRequest, Complaint, Feedback, Assignment, Invoice, Payment,
    AuditLog, ServiceCategory,
)
from app.models.base import as_aware, now_pk, to_pk_iso
from app.security.authz import login_required_api, roles_required

bp = Blueprint("dashboard", __name__)

OPEN_REQUEST_STATUSES = ("submitted", "assigned", "scheduled", "in_progress", "pending_customer", "reopened")


def _scoped_request_query():
    q = ServiceRequest.query
    if current_user.role == "customer":
        q = q.filter(ServiceRequest.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        q = q.filter(ServiceRequest.id.in_(assigned_ids))
    # supervisor/admin: unrestricted (role-appropriate operational oversight)
    return q


def _scoped_complaint_query():
    q = Complaint.query
    if current_user.role == "customer":
        q = q.filter(Complaint.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        q = q.filter(Complaint.service_request_id.in_(assigned_ids))
    return q


@bp.get("/summary")
@login_required_api
def summary():
    now = now_pk()

    req_q = _scoped_request_query()
    all_requests = req_q.all()

    open_requests = sum(1 for r in all_requests if r.status in OPEN_REQUEST_STATUSES)
    in_progress = sum(1 for r in all_requests if r.status == "in_progress")
    resolved = sum(1 for r in all_requests if r.status == "resolved")
    closed = sum(1 for r in all_requests if r.status == "closed")

    sla_breaches = sum(1 for r in all_requests if r.sla_state(now) == "breached")
    sla_at_risk = sum(1 for r in all_requests if r.sla_state(now) == "at_risk")

    today = now.date()
    resolved_today = sum(1 for r in all_requests if r.resolved_at and as_aware(r.resolved_at).date() == today)

    resolved_requests = [r for r in all_requests if r.resolved_at]
    resolution_times = [(as_aware(r.resolved_at) - as_aware(r.created_at)).total_seconds() / 3600 for r in resolved_requests]
    avg_resolution_hours = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

    responded_requests = [r for r in all_requests if r.responded_at]
    response_times = [(as_aware(r.responded_at) - as_aware(r.created_at)).total_seconds() / 3600 for r in responded_requests]
    avg_response_hours = round(sum(response_times) / len(response_times), 1) if response_times else None

    sla_eligible = [r for r in all_requests if r.sla_resolution_deadline and r.status in ("resolved", "closed")]
    breached_of_eligible = sum(
        1 for r in sla_eligible
        if r.is_breached(now) or (r.resolved_at and as_aware(r.resolved_at) > as_aware(r.sla_resolution_deadline))
    )
    sla_compliance_pct = round(100 * (1 - breached_of_eligible / len(sla_eligible)), 1) if sla_eligible else None

    comp_q = _scoped_complaint_query()
    all_complaints = comp_q.all()
    unresolved_complaints = sum(1 for c in all_complaints if c.status not in ("resolved", "closed"))

    feedback_q = db.session.query(func.avg(Feedback.rating)).join(ServiceRequest, Feedback.service_request_id == ServiceRequest.id)
    if current_user.role == "customer":
        feedback_q = feedback_q.filter(ServiceRequest.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        feedback_q = feedback_q.filter(ServiceRequest.id.in_(assigned_ids))
    avg_rating = feedback_q.scalar()

    return jsonify({
        "scope": current_user.role,
        "total_requests": len(all_requests),
        "open_requests": open_requests,
        "in_progress_requests": in_progress,
        "resolved_requests": resolved,
        "closed_requests": closed,
        "resolved_today": resolved_today,
        "total_complaints": len(all_complaints),
        "unresolved_complaints": unresolved_complaints,
        "sla_breaches": sla_breaches,
        "sla_at_risk": sla_at_risk,
        "sla_compliance_pct": sla_compliance_pct,
        "average_response_hours": avg_response_hours,
        "average_resolution_hours": avg_resolution_hours,
        "average_customer_satisfaction": round(avg_rating, 2) if avg_rating else None,
        "generated_at": to_pk_iso(now),
    })


@bp.get("/charts")
@login_required_api
def charts():
    """Chart-ready aggregates, scoped identically to /summary."""
    all_requests = _scoped_request_query().all()
    all_complaints = _scoped_complaint_query().all()

    def _count_by(items, attr):
        counts: dict = {}
        for item in items:
            key = getattr(item, attr)
            counts[key] = counts.get(key, 0) + 1
        return [{"key": k, "count": v} for k, v in sorted(counts.items())]

    categories = {c.id: c.name for c in ServiceCategory.query.all()}
    category_counts: dict = {}
    for r in all_requests:
        name = categories.get(r.category_id, "Unknown")
        category_counts[name] = category_counts.get(name, 0) + 1

    fourteen_days_ago = (now_pk() - timedelta(days=13)).date()
    day_counts: dict = {}
    for r in all_requests:
        d = as_aware(r.created_at).date()
        if d >= fourteen_days_ago:
            day_counts[d.isoformat()] = day_counts.get(d.isoformat(), 0) + 1
    requests_over_time = [
        {"date": (fourteen_days_ago + timedelta(days=i)).isoformat(), "count": day_counts.get((fourteen_days_ago + timedelta(days=i)).isoformat(), 0)}
        for i in range(14)
    ]

    return jsonify({
        "requests_by_status": _count_by(all_requests, "status"),
        "requests_by_priority": _count_by(all_requests, "priority"),
        "requests_by_category": [{"key": k, "count": v} for k, v in sorted(category_counts.items())],
        "requests_over_time": requests_over_time,
        "complaints_by_severity": _count_by(all_complaints, "severity"),
    })


@bp.get("/recent-activity")
@login_required_api
def recent_activity():
    """Recent activity feed. Customers/agents get their own scoped audit
    trail; only admin/supervisor see the unrestricted operational feed -
    audit detail is not handed out to every authenticated role."""
    limit = min(request.args.get("limit", 15, type=int) or 15, 50)

    q = AuditLog.query
    if current_user.role not in ("admin", "supervisor"):
        q = q.filter(AuditLog.user_id == current_user.id)

    entries = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({"items": [e.to_dict() for e in entries]})


@bp.get("/sla-monitoring")
@roles_required("admin", "supervisor", "agent")
def sla_monitoring():
    """SLA monitoring center: breached / at-risk / within-SLA buckets.
    Deliberately not exposed to customers - operational SLA detail across
    other customers' requests is staff-only."""
    now = now_pk()
    q = _scoped_request_query().filter(ServiceRequest.status.notin_(("resolved", "closed")))
    requests = q.all()

    buckets = {"breached": [], "at_risk": [], "within_sla": []}
    for r in requests:
        state = r.sla_state(now)
        if state is None:
            continue
        buckets[state].append({
            "id": r.id,
            "reference_number": r.reference_number,
            "category_name": r.category.name if r.category else None,
            "priority": r.priority,
            "status": r.status,
            "remaining_seconds": r.remaining_seconds(now),
            "sla_resolution_deadline": to_pk_iso(r.sla_resolution_deadline),
        })

    for key in buckets:
        buckets[key].sort(key=lambda x: x["remaining_seconds"] if x["remaining_seconds"] is not None else 0)

    total_with_sla = sum(len(v) for v in buckets.values())
    resolved_eligible = [r for r in _scoped_request_query().all() if r.sla_resolution_deadline and r.status in ("resolved", "closed")]
    breached_resolved = sum(
        1 for r in resolved_eligible
        if r.resolved_at and as_aware(r.resolved_at) > as_aware(r.sla_resolution_deadline)
    )
    all_eligible_count = total_with_sla + len(resolved_eligible)
    all_breached_count = len(buckets["breached"]) + breached_resolved
    compliance_pct = round(100 * (1 - all_breached_count / all_eligible_count), 1) if all_eligible_count else None

    return jsonify({
        "compliance_pct": compliance_pct,
        "breached": buckets["breached"],
        "at_risk": buckets["at_risk"],
        "within_sla": buckets["within_sla"],
        "generated_at": to_pk_iso(now),
    })
