from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, Assignment, User, Notification, ServiceCategory, AgentCategory
from app.models.base import now_pk, PRIORITIES
from app.security.authz import roles_required
from app.services.audit import log_action
from app.services.sla import compute_deadlines
from app.utils.validation import require_fields, validate_choice, ValidationError

bp = Blueprint("assignments", __name__)


def _require_agent_in_category(agent: User, category: ServiceCategory):
    """Backend-enforced pairing: the selected agent must actually belong
    to the selected category. This is checked here regardless of what the
    frontend dropdown filtering already did - a manually crafted API
    request with a mismatched category/agent pair must always be
    rejected, never just discouraged by the UI."""
    if agent.role != "agent":
        raise ValidationError({"agent_id": "Selected user is not an agent"})
    if not agent.is_active:
        raise ValidationError({"agent_id": "Selected agent is not active"})
    belongs = AgentCategory.query.filter_by(agent_id=agent.id, category_id=category.id).first()
    if not belongs:
        raise ValidationError({"agent_id": "The selected agent is not assigned to this category"})


def _assign_or_reassign(sr: ServiceRequest, category: ServiceCategory, agent: User, priority: str, actor):
    """Shared core for the initial assignment and any later
    reassignment/category/priority change. Always recalculates the SLA
    due date/time from the current server clock - the client never
    supplies a deadline."""
    now = now_pk()

    old_category_id = sr.category_id
    old_priority = sr.priority
    old_agent = next((a for a in sr.assignments if a.active), None)

    category_changed = old_category_id != category.id
    priority_changed = old_priority != priority
    agent_changed = old_agent is None or old_agent.agent_id != agent.id

    sr.category_id = category.id
    sr.priority = priority

    response_dl, resolution_dl = compute_deadlines(category.id, priority, now)
    sr.sla_response_deadline = response_dl
    sr.sla_resolution_deadline = resolution_dl
    sr.updated_by = actor.id

    if agent_changed:
        Assignment.query.filter_by(service_request_id=sr.id, active=True).update({"active": False})
        assignment = Assignment(service_request_id=sr.id, agent_id=agent.id, assigned_by=actor.id, assigned_at=now)
        db.session.add(assignment)
    else:
        assignment = old_agent

    if sr.status == "submitted":
        from app.models import RequestStatusHistory
        sr.status = "assigned"
        db.session.add(RequestStatusHistory(
            service_request_id=sr.id, old_status="submitted", new_status="assigned", changed_by=actor.id,
        ))

    if category_changed:
        log_action(
            "change_complaint_category", "service_request", sr.id,
            details=f"category {old_category_id}->{category.id}",
        )
    if priority_changed:
        log_action(
            "change_complaint_priority", "service_request", sr.id,
            details=f"priority {old_priority}->{priority}",
        )
        db.session.add(Notification(
            user_id=agent.id, type="priority_change",
            message=f"Priority for {sr.reference_number} changed to '{priority}'. New due date: {resolution_dl.strftime('%d %b %Y, %I:%M %p')}.",
        ))
    if agent_changed:
        db.session.flush()
        log_action(
            "assign_complaint", "assignment", assignment.id if assignment else None,
            details=f"request={sr.id} category={category.id} agent={agent.id} priority={priority}",
        )
        db.session.add(Notification(
            user_id=agent.id, type="assignment",
            message=f"You were assigned complaint {sr.reference_number} ({category.name}, priority: {priority}). Due: {resolution_dl.strftime('%d %b %Y, %I:%M %p')}.",
        ))

    db.session.commit()
    return assignment


@bp.post("/service-requests/<int:request_id>/assignments")
@roles_required("admin", "supervisor")
def assign_request(request_id):
    """Assignment workflow, in this exact order:
      1. category_id  - must exist and be active
      2. agent_id     - must be an active agent belonging to that category
      3. priority     - must be a valid priority level
    The server then computes the SLA/due date/time automatically from the
    category+priority SLA rule and the current server clock; the client
    can never supply its own deadline. Only admins/supervisors may call
    this - customers can never assign themselves or anyone else, and
    agents cannot self-assign."""
    sr = ServiceRequest.query.get_or_404(request_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["category_id", "agent_id", "priority"])
    validate_choice(data["priority"], PRIORITIES, "priority")

    category = db.session.get(ServiceCategory, data["category_id"])
    if category is None:
        raise ValidationError({"category_id": "Please select a category."})
    if not category.is_active:
        raise ValidationError({"category_id": "This category is not currently active."})

    agent = db.session.get(User, data["agent_id"])
    if agent is None:
        raise ValidationError({"agent_id": "Please select an available agent."})
    _require_agent_in_category(agent, category)

    assignment = _assign_or_reassign(sr, category, agent, data["priority"], current_user)
    return jsonify({"assignment": assignment.to_dict(), "service_request": sr.to_dict()}), 201


@bp.patch("/service-requests/<int:request_id>/assignments")
@roles_required("admin", "supervisor")
def update_assignment(request_id):
    """Reassignment / category / priority change after the initial
    assignment. Any of category_id, agent_id, priority may be supplied;
    omitted fields keep their current value. The category/agent pairing
    is re-validated every time - if the category changes and the current
    agent doesn't belong to the new category, a valid new agent_id must
    be supplied in the same request, or the change is rejected."""
    sr = ServiceRequest.query.get_or_404(request_id)
    data = request.get_json(silent=True) or {}

    category = sr.category
    if "category_id" in data:
        category = db.session.get(ServiceCategory, data["category_id"])
        if category is None:
            raise ValidationError({"category_id": "Please select a category."})
        if not category.is_active:
            raise ValidationError({"category_id": "This category is not currently active."})

    current_assignment = next((a for a in sr.assignments if a.active), None)
    agent = current_assignment.agent if current_assignment else None
    if "agent_id" in data:
        agent = db.session.get(User, data["agent_id"])
        if agent is None:
            raise ValidationError({"agent_id": "Please select an available agent."})

    if agent is None:
        raise ValidationError({"agent_id": "This complaint has not been assigned to an agent yet."})

    _require_agent_in_category(agent, category)

    priority = data.get("priority", sr.priority)
    if priority != sr.priority:
        validate_choice(priority, PRIORITIES, "priority")

    assignment = _assign_or_reassign(sr, category, agent, priority, current_user)
    return jsonify({"assignment": assignment.to_dict(), "service_request": sr.to_dict()})


@bp.get("/service-requests/<int:request_id>/assignments")
@roles_required("admin", "supervisor", "agent")
def list_assignments(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    return jsonify({"items": [a.to_dict() for a in sr.assignments]})
