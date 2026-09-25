from flask import Blueprint, request, jsonify
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import ServiceRequest, Complaint, Customer, User, Assignment
from app.security.authz import login_required_api

bp = Blueprint("search", __name__)

MAX_RESULTS_PER_GROUP = 6


@bp.get("")
@login_required_api
def global_search():
    """Server-side, role-scoped search across requests, complaints,
    customers and users. Never returns more than a handful of results per
    group - this is a navigation aid, not a data export, and every group
    is filtered through the same visibility rules as the regular list
    endpoints so a search can't be used to enumerate records a role
    wouldn't otherwise be allowed to see."""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"requests": [], "complaints": [], "customers": [], "users": []})

    like = f"%{query}%"
    results = {"requests": [], "complaints": [], "customers": [], "users": []}

    # --- Service requests ---
    req_q = ServiceRequest.query
    if current_user.role == "customer":
        req_q = req_q.filter(ServiceRequest.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        assigned_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        req_q = req_q.filter(ServiceRequest.id.in_(assigned_ids))
    req_q = req_q.filter(or_(
        ServiceRequest.reference_number.ilike(like),
        ServiceRequest.description.ilike(like),
    ))
    for r in req_q.order_by(ServiceRequest.created_at.desc()).limit(MAX_RESULTS_PER_GROUP).all():
        results["requests"].append({
            "id": r.id, "reference_number": r.reference_number,
            "description": r.description[:80], "status": r.status,
        })

    # --- Complaints ---
    comp_q = Complaint.query
    if current_user.role == "customer":
        comp_q = comp_q.filter(Complaint.customer_id == current_user.customer_profile.id)
    elif current_user.role == "agent":
        assigned_req_ids = db.session.query(Assignment.service_request_id).filter_by(agent_id=current_user.id, active=True)
        comp_q = comp_q.filter(Complaint.service_request_id.in_(assigned_req_ids))
    comp_q = comp_q.filter(or_(
        Complaint.reference_number.ilike(like),
        Complaint.description.ilike(like),
    ))
    for c in comp_q.order_by(Complaint.created_at.desc()).limit(MAX_RESULTS_PER_GROUP).all():
        results["complaints"].append({
            "id": c.id, "reference_number": c.reference_number,
            "description": c.description[:80], "status": c.status,
        })

    # --- Customers (staff only - a customer has no business searching other customers) ---
    if current_user.role in ("admin", "supervisor", "agent"):
        cust_q = Customer.query.join(User, Customer.user_id == User.id).filter(or_(
            Customer.full_name.ilike(like),
            Customer.phone.ilike(like),
            User.email.ilike(like),
        ))
        for cust in cust_q.limit(MAX_RESULTS_PER_GROUP).all():
            results["customers"].append({
                "id": cust.id, "full_name": cust.full_name,
                "email": cust.user.email if cust.user else None,
            })

    # --- Users (admin/supervisor only) ---
    if current_user.role in ("admin", "supervisor"):
        user_q = User.query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
        for u in user_q.limit(MAX_RESULTS_PER_GROUP).all():
            results["users"].append({"id": u.id, "name": u.name, "email": u.email, "role": u.role})

    return jsonify(results)
