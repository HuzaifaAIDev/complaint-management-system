from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import Notification
from app.security.authz import login_required_api, can_access_notification
from app.utils.validation import parse_pagination

bp = Blueprint("notifications", __name__)


@bp.get("")
@login_required_api
def list_notifications():
    page, page_size = parse_pagination(request.args)
    q = Notification.query.filter_by(user_id=current_user.id)
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    if unread_only:
        q = q.filter_by(is_read=False)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({"items": [n.to_dict() for n in items], "page": page, "page_size": page_size, "total": total})


@bp.post("/<int:notification_id>/read")
@login_required_api
def mark_read(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    if not can_access_notification(notif):
        abort(403)
    notif.is_read = True
    db.session.commit()
    return jsonify({"notification": notif.to_dict()})


@bp.post("/read-all")
@login_required_api
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"})
