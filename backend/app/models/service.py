from app.extensions import db
from app.models.base import TimestampMixin, PRIORITIES, REQUEST_STATUSES, now_pk, to_pk_iso, PK_TZ


class ServiceCategory(db.Model, TimestampMixin):
    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    default_sla_hours = db.Column(db.Integer, nullable=False, default=72)
    estimated_duration_minutes = db.Column(db.Integer, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    sla_rules = db.relationship("SlaRule", back_populates="category", cascade="all, delete-orphan")
    agent_links = db.relationship("AgentCategory", back_populates="category", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_sla_hours": self.default_sla_hours,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "base_price": float(self.base_price) if self.base_price is not None else None,
            "is_active": self.is_active,
        }


class AgentCategory(db.Model):
    """Which service categories/skills an agent belongs to. An agent can
    belong to multiple categories; a category can have multiple agents.
    Used to filter the agent picker during complaint assignment so a
    supervisor/admin can only ever assign a complaint to an agent who
    actually handles that category - enforced here in the data model and
    again server-side in the assignment endpoint, never only in the UI."""
    __tablename__ = "agent_categories"
    __table_args__ = (db.UniqueConstraint("agent_id", "category_id", name="uq_agent_category"),)

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_pk, nullable=False)

    agent = db.relationship("User")
    category = db.relationship("ServiceCategory", back_populates="agent_links")

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
        }


class SlaRule(db.Model, TimestampMixin):
    __tablename__ = "sla_rules"
    __table_args__ = (db.UniqueConstraint("category_id", "priority", name="uq_sla_category_priority"),)

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)
    priority = db.Column(db.String(20), db.CheckConstraint(f"priority IN {PRIORITIES}"), nullable=False)
    response_hours = db.Column(db.Integer, nullable=False)
    resolution_hours = db.Column(db.Integer, nullable=False)

    category = db.relationship("ServiceCategory", back_populates="sla_rules")

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "priority": self.priority,
            "response_hours": self.response_hours,
            "resolution_hours": self.resolution_hours,
        }


class ServiceRequest(db.Model, TimestampMixin):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    priority = db.Column(db.String(20), db.CheckConstraint(f"priority IN {PRIORITIES}"), nullable=False, default="medium")
    preferred_date = db.Column(db.Date, nullable=True)
    contact_number = db.Column(db.String(11), nullable=False)
    status = db.Column(db.String(20), db.CheckConstraint(f"status IN {REQUEST_STATUSES}"), nullable=False, default="submitted")

    sla_response_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    sla_resolution_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    responded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    customer = db.relationship("Customer")
    category = db.relationship("ServiceCategory")
    attachments = db.relationship("RequestAttachment", backref="service_request", cascade="all, delete-orphan")
    status_history = db.relationship("RequestStatusHistory", backref="service_request", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", backref="service_request", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="service_request", cascade="all, delete-orphan")
    work_orders = db.relationship("WorkOrder", backref="service_request", cascade="all, delete-orphan")

    def is_breached(self, now):
        if self.status in ("resolved", "closed"):
            return False
        from app.models.base import as_aware
        deadline = as_aware(self.sla_resolution_deadline)
        now = as_aware(now)
        if deadline is None:
            return False
        return now > deadline

    def sla_state(self, now, at_risk_ratio: float = 0.2):
        """Returns one of 'breached', 'at_risk', 'within_sla', or None (no
        deadline / already closed out). 'at_risk' means the remaining time
        to the resolution deadline has dropped under `at_risk_ratio` of the
        total allotted window - e.g. 20% of the time budget left."""
        from app.models.base import as_aware
        if self.status in ("resolved", "closed"):
            return None
        deadline = as_aware(self.sla_resolution_deadline)
        if deadline is None:
            return None
        now = as_aware(now)
        if now > deadline:
            return "breached"
        total_window = (deadline - as_aware(self.created_at)).total_seconds()
        remaining = (deadline - now).total_seconds()
        if total_window > 0 and remaining <= total_window * at_risk_ratio:
            return "at_risk"
        return "within_sla"

    def remaining_seconds(self, now):
        from app.models.base import as_aware
        deadline = as_aware(self.sla_resolution_deadline)
        if deadline is None:
            return None
        return (deadline - as_aware(now)).total_seconds()

    def to_dict(self, now=None):
        now = now or now_pk()
        return {
            "id": self.id,
            "reference_number": self.reference_number,
            "customer_id": self.customer_id,
            "category_id": self.category_id,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
            "preferred_date": self.preferred_date.isoformat() if self.preferred_date else None,
            "contact_number": self.contact_number,
            "status": self.status,
            "sla_response_deadline": to_pk_iso(self.sla_response_deadline),
            "sla_resolution_deadline": to_pk_iso(self.sla_resolution_deadline),
            "is_breached": self.is_breached(now),
            "sla_state": self.sla_state(now),
            "remaining_seconds": self.remaining_seconds(now),
            "created_at": to_pk_iso(self.created_at),
            "updated_at": to_pk_iso(self.updated_at),
        }


class RequestAttachment(db.Model, TimestampMixin):
    __tablename__ = "request_attachments"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "uploaded_at": to_pk_iso(self.uploaded_at),
        }


class RequestStatusHistory(db.Model):
    __tablename__ = "request_status_history"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "changed_at": to_pk_iso(self.changed_at),
            "note": self.note,
        }


class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_pk)
    active = db.Column(db.Boolean, default=True, nullable=False)

    agent = db.relationship("User", foreign_keys=[agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent.name if self.agent else None,
            "assigned_by": self.assigned_by,
            "assigned_at": to_pk_iso(self.assigned_at),
            "active": self.active,
        }


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "service_request_id": self.service_request_id,
            "scheduled_at": to_pk_iso(self.scheduled_at),
            "location": self.location,
            "status": self.status,
            "assigned_staff_id": self.assigned_staff_id,
        }
