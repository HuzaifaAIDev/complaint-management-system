from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db, limiter
from app.models import Message, User, ServiceRequest, Notification
from app.security.authz import login_required_api, can_access_message_thread, can_access_service_request
from app.services.audit import log_action
from app.utils.validation import require_fields, sanitize_text, parse_pagination

bp = Blueprint("messages", __name__)


@bp.post("")
@login_required_api
@limiter.limit("60 per hour")
def send_message():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["receiver_id", "body"])

    receiver = User.query.get_or_404(data["receiver_id"])
    service_request_id = data.get("service_request_id")

    if service_request_id:
        sr = ServiceRequest.query.get_or_404(service_request_id)
        # Both sender and receiver must legitimately relate to this request.
        if not can_access_service_request(sr):
            abort(403)
    elif current_user.role == "customer" and receiver.role == "customer":
        abort(403, description="Customers may only message assigned staff")

    body = sanitize_text(data["body"], 4000)
    if not body:
        abort(400, description="Message body cannot be empty")

    message = Message(sender_id=current_user.id, receiver_id=receiver.id, service_request_id=service_request_id, body=body)
    db.session.add(message)
    db.session.add(Notification(user_id=receiver.id, type="message", message=f"New message from {current_user.name}."))
    log_action("send_message", "message", None)
    db.session.commit()
    return jsonify({"message_obj": message.to_dict()}), 201


@bp.get("")
@login_required_api
def list_messages():
    page, page_size = parse_pagination(request.args)
    other_user_id = request.args.get("with_user_id", type=int)
    service_request_id = request.args.get("service_request_id", type=int)

    q = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    )
    if other_user_id:
        q = q.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user_id)) |
            ((Message.sender_id == other_user_id) & (Message.receiver_id == current_user.id))
        )
    if service_request_id:
        q = q.filter(Message.service_request_id == service_request_id)

    total = q.count()
    items = q.order_by(Message.sent_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({"items": [m.to_dict() for m in items], "page": page, "page_size": page_size, "total": total})
