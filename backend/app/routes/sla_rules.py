from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import SlaRule, ServiceCategory
from app.security.authz import roles_required, login_required_api
from app.services.audit import log_action
from app.utils.validation import require_fields, validate_priority, ValidationError

bp = Blueprint("sla_rules", __name__)


@bp.get("")
@login_required_api
def list_sla_rules():
    category_id = request.args.get("category_id", type=int)
    q = SlaRule.query
    if category_id:
        q = q.filter_by(category_id=category_id)
    return jsonify({"items": [r.to_dict() for r in q.all()]})


@bp.post("")
@roles_required("admin")
def create_sla_rule():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["category_id", "priority", "response_hours", "resolution_hours"])
    validate_priority(data["priority"])
    ServiceCategory.query.get_or_404(data["category_id"])

    if SlaRule.query.filter_by(category_id=data["category_id"], priority=data["priority"]).first():
        raise ValidationError({"priority": "A rule for this category/priority already exists"})

    rule = SlaRule(
        category_id=data["category_id"],
        priority=data["priority"],
        response_hours=int(data["response_hours"]),
        resolution_hours=int(data["resolution_hours"]),
    )
    db.session.add(rule)
    db.session.flush()
    log_action("create_sla_rule", "sla_rule", rule.id)
    db.session.commit()
    return jsonify({"rule": rule.to_dict()}), 201


@bp.patch("/<int:rule_id>")
@roles_required("admin")
def update_sla_rule(rule_id):
    rule = SlaRule.query.get_or_404(rule_id)
    data = request.get_json(silent=True) or {}
    if "response_hours" in data:
        rule.response_hours = int(data["response_hours"])
    if "resolution_hours" in data:
        rule.resolution_hours = int(data["resolution_hours"])
    log_action("update_sla_rule", "sla_rule", rule.id)
    db.session.commit()
    return jsonify({"rule": rule.to_dict()})


@bp.delete("/<int:rule_id>")
@roles_required("admin")
def delete_sla_rule(rule_id):
    rule = SlaRule.query.get_or_404(rule_id)
    log_action("delete_sla_rule", "sla_rule", rule.id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "deleted"})
