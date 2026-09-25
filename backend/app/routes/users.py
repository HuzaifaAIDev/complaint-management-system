from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.models import User
from app.security.authz import roles_required
from app.services.audit import log_action
from app.utils.validation import (
    require_fields, validate_email_field, validate_password_strength,
    validate_role, parse_pagination, ValidationError,
)

bp = Blueprint("users", __name__)


@bp.get("")
@roles_required("admin", "supervisor")
def list_users():
    page, page_size = parse_pagination(request.args)
    q = User.query
    role = request.args.get("role")
    if role:
        validate_role(role)
        q = q.filter_by(role=role)
    total = q.count()
    items = q.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({
        "items": [u.to_dict() for u in items],
        "page": page, "page_size": page_size, "total": total,
    })


@bp.post("")
@roles_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "email", "password", "role"])
    email = validate_email_field(data["email"])
    validate_password_strength(data["password"])
    validate_role(data["role"])

    if User.query.filter_by(email=email).first():
        raise ValidationError({"email": "A user with this email already exists"})

    user = User(name=data["name"].strip()[:120], email=email, role=data["role"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()
    log_action("create_user", "user", user.id, details=f"role={data['role']}")
    db.session.commit()
    return jsonify({"user": user.to_dict()}), 201


@bp.get("/<int:user_id>")
@roles_required("admin", "supervisor")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({"user": user.to_dict()})


@bp.patch("/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if "name" in data and data["name"]:
        user.name = data["name"].strip()[:120]
    if "role" in data:
        validate_role(data["role"])
        user.role = data["role"]
    if "is_active" in data:
        user.is_active_flag = bool(data["is_active"])
        if not user.is_active_flag:
            user.locked_until = None

    log_action("update_user", "user", user.id)
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@bp.post("/<int:user_id>/unlock")
@roles_required("admin")
def unlock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.locked_until = None
    user.failed_login_count = 0
    log_action("unlock_user", "user", user.id)
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@bp.get("/staff-roles")
@roles_required("admin", "supervisor")
def staff_roles():
    """Returns the set of staff roles (created/assigned by the admin) that
    currently have at least one active user - used to drive the two-step
    'select role, then select agent' assignment workflow. Only roles that
    can actually be assigned work (agent, supervisor) are ever returned;
    'customer' and 'admin' are excluded on purpose."""
    ASSIGNABLE_ROLES = ("agent", "supervisor")
    present = (
        db.session.query(User.role)
        .filter(User.role.in_(ASSIGNABLE_ROLES), User.is_active_flag.is_(True))
        .distinct()
        .all()
    )
    present_roles = {r[0] for r in present}
    ordered = [r for r in ASSIGNABLE_ROLES if r in present_roles]
    return jsonify({"roles": ordered})


@bp.get("/agents/workload")
@roles_required("admin", "supervisor")
def agent_workload():
    """Aggregated per-agent workload for supervisors/admins to spot
    overload and SLA risk concentration. Never exposed to agents about
    each other, or to any non-operational role."""
    from app.models import Assignment, ServiceRequest
    from app.models.base import now_pk

    now = now_pk()
    agents = User.query.filter_by(role="agent", is_active=True).order_by(User.name).all()

    result = []
    for agent in agents:
        assigned_request_ids = db.session.query(Assignment.service_request_id).filter_by(
            agent_id=agent.id, active=True
        )
        requests = ServiceRequest.query.filter(ServiceRequest.id.in_(assigned_request_ids)).all()

        open_statuses = ("submitted", "assigned", "scheduled", "pending_customer", "reopened")
        in_progress = [r for r in requests if r.status == "in_progress"]
        completed = [r for r in requests if r.status in ("resolved", "closed")]
        sla_risk = sum(1 for r in requests if r.sla_state(now) == "at_risk")
        sla_breached = sum(1 for r in requests if r.sla_state(now) == "breached")

        from app.models.base import as_aware
        resolved = [r for r in requests if r.resolved_at]
        resolution_times = [(as_aware(r.resolved_at) - as_aware(r.created_at)).total_seconds() / 3600 for r in resolved]
        sla_eligible = [r for r in requests if r.sla_resolution_deadline and r.status in ("resolved", "closed")]
        breached_of_eligible = sum(1 for r in sla_eligible if r.is_breached(now) or (r.resolved_at and as_aware(r.resolved_at) > as_aware(r.sla_resolution_deadline)))
        compliance = round(100 * (1 - breached_of_eligible / len(sla_eligible)), 1) if sla_eligible else None

        result.append({
            "agent_id": agent.id,
            "agent_name": agent.name,
            "open": sum(1 for r in requests if r.status in open_statuses),
            "in_progress": len(in_progress),
            "sla_at_risk": sla_risk,
            "sla_breached": sla_breached,
            "completed": len(completed),
            "total_assigned": len(requests),
            "average_resolution_hours": round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None,
            "sla_compliance_pct": compliance,
        })

    return jsonify({"items": result})
