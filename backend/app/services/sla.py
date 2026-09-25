"""
SLA engine.

Deadlines are computed server-side only, at request-creation time (and
recalculated if a supervisor/admin changes priority or category before
the request is assigned). The client never supplies a deadline.

Business-hours/holiday calendars are not defined anywhere in the original
specification, so - per instruction 15 ("use a clearly documented default
rather than inventing an unnecessarily complex enterprise calendar
system") - deadlines use simple wall-clock hours from the SLA rule.
"""
from datetime import timedelta, datetime
from flask import current_app
from app.models import SlaRule
from app.models.base import now_pk


def get_sla_targets(category_id: int, priority: str):
    """Returns (response_hours, resolution_hours) for a category/priority,
    falling back to the category default, then the global app default."""
    rule = SlaRule.query.filter_by(category_id=category_id, priority=priority).first()
    if rule:
        return rule.response_hours, rule.resolution_hours

    from app.models import ServiceCategory
    category = ServiceCategory.query.get(category_id)
    default_hours = category.default_sla_hours if category else current_app.config["DEFAULT_RESOLUTION_HOURS"]
    response_hours = current_app.config["DEFAULT_RESPONSE_HOURS"]
    return response_hours, default_hours


def compute_deadlines(category_id: int, priority: str, start_time: datetime = None):
    start_time = start_time or now_pk()
    response_hours, resolution_hours = get_sla_targets(category_id, priority)
    return (
        start_time + timedelta(hours=response_hours),
        start_time + timedelta(hours=resolution_hours),
    )
