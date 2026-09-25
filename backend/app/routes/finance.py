from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from app.extensions import db
from app.models import ServiceRequest, Invoice, Payment
from app.security.authz import roles_required, login_required_api, can_access_invoice
from app.services.audit import log_action
from app.services.workflow import generate_invoice_number
from app.utils.validation import require_fields, validate_choice
from app.models.base import PAYMENT_STATUSES, now_pk

bp = Blueprint("finance", __name__)


@bp.post("/service-requests/<int:request_id>/invoices")
@roles_required("admin")
def create_invoice(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["total_amount"])
    try:
        amount = float(data["total_amount"])
    except (TypeError, ValueError):
        abort(400, description="total_amount must be numeric")
    if amount < 0:
        abort(400, description="total_amount cannot be negative")

    invoice = Invoice(service_request_id=sr.id, invoice_no=generate_invoice_number(), total_amount=amount, issued_by=current_user.id)
    db.session.add(invoice)
    log_action("create_invoice", "invoice", None, details=f"request={sr.id}")
    db.session.commit()
    return jsonify({"invoice": invoice.to_dict()}), 201


@bp.get("/service-requests/<int:request_id>/invoices")
@login_required_api
def list_invoices(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)
    invoices = Invoice.query.filter_by(service_request_id=sr.id).all()
    invoices = [i for i in invoices if can_access_invoice(i)]
    return jsonify({"items": [i.to_dict() for i in invoices]})


@bp.get("/invoices/<int:invoice_id>")
@login_required_api
def get_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    if not can_access_invoice(invoice):
        abort(403)
    return jsonify({"invoice": invoice.to_dict(), "payments": [p.to_dict() for p in invoice.payments]})


@bp.post("/invoices/<int:invoice_id>/payments")
@roles_required("admin")
def record_payment(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["amount"])
    try:
        amount = float(data["amount"])
    except (TypeError, ValueError):
        abort(400, description="amount must be numeric")
    if amount <= 0:
        abort(400, description="amount must be positive")

    status = data.get("status", "paid")
    validate_choice(status, PAYMENT_STATUSES, "status")

    payment = Payment(
        invoice_id=invoice.id, amount=amount, method=data.get("method", "manual"),
        status=status, recorded_by=current_user.id,
        paid_at=now_pk() if status == "paid" else None,
    )
    db.session.add(payment)
    log_action("record_payment", "payment", None, details=f"invoice={invoice.id} status={status}")
    db.session.commit()
    return jsonify({"payment": payment.to_dict()}), 201
