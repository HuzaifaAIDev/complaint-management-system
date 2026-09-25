from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import ServiceCategory
from app.security.authz import roles_required, login_required_api
from app.services.audit import log_action
from app.utils.validation import require_fields, ValidationError

bp = Blueprint("service_categories", __name__)


@bp.get("")
@login_required_api
def list_categories():
    active_only = request.args.get("active_only", "true").lower() != "false"
    q = ServiceCategory.query
    if active_only:
        q = q.filter_by(is_active=True)
    items = q.order_by(ServiceCategory.name).all()
    return jsonify({"items": [c.to_dict() for c in items]})


@bp.post("")
@roles_required("admin")
def create_category():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name"])
    if ServiceCategory.query.filter_by(name=data["name"]).first():
        raise ValidationError({"name": "A category with this name already exists"})
    category = ServiceCategory(
        name=data["name"].strip()[:120],
        description=data.get("description"),
        default_sla_hours=int(data.get("default_sla_hours", 72)),
        estimated_duration_minutes=data.get("estimated_duration_minutes"),
        base_price=data.get("base_price"),
    )
    db.session.add(category)
    db.session.flush()
    log_action("create_category", "service_category", category.id)
    db.session.commit()
    return jsonify({"category": category.to_dict()}), 201


@bp.patch("/<int:category_id>")
@roles_required("admin")
def update_category(category_id):
    category = ServiceCategory.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    for field in ("name", "description"):
        if field in data and data[field] is not None:
            setattr(category, field, data[field])
    if "default_sla_hours" in data:
        category.default_sla_hours = int(data["default_sla_hours"])
    if "estimated_duration_minutes" in data:
        category.estimated_duration_minutes = data["estimated_duration_minutes"]
    if "base_price" in data:
        category.base_price = data["base_price"]
    if "is_active" in data:
        category.is_active = bool(data["is_active"])
    log_action("update_category", "service_category", category.id)
    db.session.commit()
    return jsonify({"category": category.to_dict()})
