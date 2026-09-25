import pytest
from app import create_app
from app.extensions import db
from app.models import User, Customer, ServiceCategory, SlaRule, AgentCategory


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(role, email, password="TestPass123!"):
    user = User(name=f"Test {role}", email=email, role=role, email_verified=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    if role == "customer":
        db.session.add(Customer(user_id=user.id, full_name=f"Test {role}", phone="03001234567", address="Karachi, Test Area"))
    db.session.commit()
    return user, password


@pytest.fixture
def seed_users(app):
    with app.app_context():
        admin, admin_pw = _create_user("admin", "admin@test.com")
        supervisor, sup_pw = _create_user("supervisor", "supervisor@test.com")
        agent, agent_pw = _create_user("agent", "agent@test.com")
        customer, cust_pw = _create_user("customer", "customer@test.com")
        customer2, cust2_pw = _create_user("customer", "customer2@test.com")

        category = ServiceCategory(name="General Repair", default_sla_hours=48)
        db.session.add(category)
        db.session.flush()
        db.session.add(SlaRule(category_id=category.id, priority="medium", response_hours=8, resolution_hours=48))
        db.session.add(SlaRule(category_id=category.id, priority="urgent", response_hours=1, resolution_hours=8))
        db.session.add(SlaRule(category_id=category.id, priority="high", response_hours=4, resolution_hours=24))
        db.session.add(SlaRule(category_id=category.id, priority="low", response_hours=24, resolution_hours=96))
        db.session.add(AgentCategory(agent_id=agent.id, category_id=category.id))
        db.session.commit()

        return {
            "admin": ("admin@test.com", admin_pw),
            "supervisor": ("supervisor@test.com", sup_pw),
            "agent": ("agent@test.com", agent_pw),
            "customer": ("customer@test.com", cust_pw),
            "customer2": ("customer2@test.com", cust2_pw),
            "category_id": category.id,
        }


def login(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return resp


def valid_request_payload(category_id, **overrides):
    payload = {
        "category_id": category_id,
        "description": "Test service request description",
        "location": "123 Main St",
        "priority": "medium",
        "preferred_date": "2099-12-01",
        "contact_number": "03001234567",
    }
    payload.update(overrides)
    return payload


def valid_complaint_payload(**overrides):
    payload = {
        "description": "Test complaint description",
        "category": "delay",
        "severity": "minor",
        "requested_resolution": "Please resolve promptly",
        "contact_number": "03001234567",
    }
    payload.update(overrides)
    return payload
