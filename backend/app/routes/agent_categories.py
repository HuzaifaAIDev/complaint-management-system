"""Agent <-> category ("skills") management.

An agent must belong to one or more service categories before they can be
assigned complaints in that category. Admins manage these links here;
the category-filtered agent picker used during assignment (see
assignments.py) is powered by the same data.
"""
from flask import Blueprint, request, jsonify, abort
from app.extensions import db
from app.models import User, ServiceCategory, AgentCategory
from app.security.authz import roles_required
from app.services.audit import log_action
from app.utils.validation import require_fields, ValidationError

bp = Blueprint("agent_categories", __name__)


@bp.get("/users/<int:agent_id>/categories")
@roles_required("admin", "supervisor")
def list_agent_categories(agent_id):
    agent = User.query.get_or_404(agent_id)
    if agent.role != "agent":
        abort(400, description="This user is not an agent")
    links = AgentCategory.query.filter_by(agent_id=agent.id).all()
    return jsonify({"items": [l.to_dict() for l in links]})


@bp.post("/users/<int:agent_id>/categories")
@roles_required("admin")
def add_agent_category(agent_id):
    agent = User.query.get_or_404(agent_id)
    if agent.role != "agent":
        abort(400, description="Categories/skills can only be assigned to agents")

    data = request.get_json(silent=True) or {}
    require_fields(data, ["category_id"])
    category = ServiceCategory.query.get_or_404(data["category_id"])

    if AgentCategory.query.filter_by(agent_id=agent.id, category_id=category.id).first():
        raise ValidationError({"category_id": "Agent already belongs to this category"})

    link = AgentCategory(agent_id=agent.id, category_id=category.id)
    db.session.add(link)
    db.session.flush()
    log_action("add_agent_category", "agent_category", link.id, details=f"agent={agent.id} category={category.id}")
    db.session.commit()
    return jsonify({"item": link.to_dict()}), 201


@bp.delete("/users/<int:agent_id>/categories/<int:category_id>")
@roles_required("admin")
def remove_agent_category(agent_id, category_id):
    link = AgentCategory.query.filter_by(agent_id=agent_id, category_id=category_id).first_or_404()
    log_action("remove_agent_category", "agent_category", link.id, details=f"agent={agent_id} category={category_id}")
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "removed"})


@bp.get("/service-categories/<int:category_id>/agents")
@roles_required("admin", "supervisor")
def list_agents_for_category(category_id):
    """Powers the category-filtered agent dropdown in the assignment
    workflow: only active agents who actually belong to this category are
    ever returned. The frontend must never fall back to showing all
    agents - if this list is empty, none are available for that category."""
    category = ServiceCategory.query.get_or_404(category_id)
    agents = (
        User.query.join(AgentCategory, AgentCategory.agent_id == User.id)
        .filter(AgentCategory.category_id == category.id, User.role == "agent", User.is_active_flag.is_(True))
        .order_by(User.name)
        .all()
    )
    return jsonify({"items": [a.to_dict() for a in agents]})
