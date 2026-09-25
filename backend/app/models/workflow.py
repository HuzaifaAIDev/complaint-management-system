from app.extensions import db
from app.models.base import (
    TimestampMixin, COMPLAINT_STATUSES, SEVERITIES, ESCALATION_TYPES,
    WORK_ORDER_STATUSES, PAYMENT_STATUSES, now_pk, to_pk_iso,
)


class WorkOrder(db.Model, TimestampMixin):
    __tablename__ = "work_orders"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), db.CheckConstraint(f"status IN {WORK_ORDER_STATUSES}"), nullable=False, default="open")
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    notes = db.relationship("WorkNote", backref="work_order", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "started_at": to_pk_iso(self.started_at),
            "completed_at": to_pk_iso(self.completed_at),
        }


class WorkNote(db.Model):
    __tablename__ = "work_notes"

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey("work_orders.id"), nullable=False)
    note = db.Column(db.Text, nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_id": self.work_order_id,
            "note": self.note,
            "added_by": self.added_by,
            "added_at": to_pk_iso(self.added_at),
        }


class RequestDocument(db.Model):
    __tablename__ = "request_documents"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False, default="other")
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    service_request = db.relationship("ServiceRequest")

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "original_filename": self.original_filename,
            "doc_type": self.doc_type,
            "uploaded_at": to_pk_iso(self.uploaded_at),
        }


class Complaint(db.Model, TimestampMixin):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default="other")  # delay, quality, staff_behavior, billing, incomplete_work, other
    severity = db.Column(db.String(20), db.CheckConstraint(f"severity IN {SEVERITIES}"), nullable=False, default="minor")
    requested_resolution = db.Column(db.Text, nullable=True)
    contact_number = db.Column(db.String(11), nullable=False)
    status = db.Column(db.String(20), db.CheckConstraint(f"status IN {COMPLAINT_STATUSES}"), nullable=False, default="open")
    resolution = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    status_history = db.relationship("ComplaintStatusHistory", backref="complaint", cascade="all, delete-orphan")
    escalations = db.relationship("Escalation", backref="complaint", cascade="all, delete-orphan")
    customer = db.relationship("Customer")
    service_request = db.relationship("ServiceRequest")

    def to_dict(self):
        return {
            "id": self.id,
            "reference_number": self.reference_number,
            "customer_id": self.customer_id,
            "service_request_id": self.service_request_id,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "requested_resolution": self.requested_resolution,
            "contact_number": self.contact_number,
            "status": self.status,
            "resolution": self.resolution,
            "resolved_at": to_pk_iso(self.resolved_at),
            "created_at": to_pk_iso(self.created_at),
        }


class ComplaintStatusHistory(db.Model):
    __tablename__ = "complaint_status_history"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "changed_at": to_pk_iso(self.changed_at),
        }


class Escalation(db.Model):
    __tablename__ = "escalations"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False)
    escalation_type = db.Column(db.String(30), db.CheckConstraint(f"escalation_type IN {ESCALATION_TYPES}"), nullable=False, default="other")
    escalated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    escalated_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    escalated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "escalation_type": self.escalation_type,
            "escalated_by": self.escalated_by,
            "escalated_to": self.escalated_to,
            "reason": self.reason,
            "escalated_at": to_pk_iso(self.escalated_at),
            "resolved_at": to_pk_iso(self.resolved_at),
            "resolution_notes": self.resolution_notes,
        }


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "service_request_id": self.service_request_id,
            "body": self.body,
            "sent_at": to_pk_iso(self.sent_at),
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="general")
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": to_pk_iso(self.created_at),
        }


class Invoice(db.Model, TimestampMixin):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    invoice_no = db.Column(db.String(40), unique=True, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan")
    service_request = db.relationship("ServiceRequest")

    def to_dict(self):
        paid = sum(float(p.amount) for p in self.payments if p.status == "paid")
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "invoice_no": self.invoice_no,
            "total_amount": float(self.total_amount),
            "amount_paid": paid,
            "issued_at": to_pk_iso(self.issued_at),
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(30), nullable=False, default="manual")
    status = db.Column(db.String(20), db.CheckConstraint(f"status IN {PAYMENT_STATUSES}"), nullable=False, default="pending")
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "amount": float(self.amount),
            "method": self.method,
            "status": self.status,
            "paid_at": to_pk_iso(self.paid_at),
        }


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), unique=True, nullable=False)
    rating = db.Column(db.Integer, db.CheckConstraint("rating BETWEEN 1 AND 5"), nullable=False)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "rating": self.rating,
            "comments": self.comments,
            "created_at": to_pk_iso(self.created_at),
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(60), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    result = db.Column(db.String(20), nullable=False, default="success")
    ip_address = db.Column(db.String(64), nullable=True)
    request_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "result": self.result,
            "created_at": to_pk_iso(self.created_at),
        }
