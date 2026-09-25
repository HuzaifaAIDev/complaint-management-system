"""
Creates a set of seed data for local development/demo purposes: one user
per core role, several category-specialist agents, service categories,
SLA rules, and agent-category ("skills") links.

Usage:
    flask --app run.py shell   (or)
    python seed.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, Customer, ServiceCategory, SlaRule, AgentCategory  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))


def _make_agent(name, email):
    user = User(name=name, email=email, role="agent", email_verified=True)
    user.set_password("AgentPass123!")
    db.session.add(user)
    return user


def seed():
    with app.app_context():
        if User.query.filter_by(email="admin@example.com").first():
            print("Seed data already present, skipping.")
            return

        admin = User(name="Admin User", email="admin@example.com", role="admin", email_verified=True)
        admin.set_password("AdminPass123!")

        supervisor = User(name="Sam Supervisor", email="supervisor@example.com", role="supervisor", email_verified=True)
        supervisor.set_password("SuperviseMe123!")

        customer_user = User(name="Cara Customer", email="customer@example.com", role="customer", email_verified=True)
        customer_user.set_password("CustomerPass123!")

        db.session.add_all([admin, supervisor, customer_user])
        db.session.flush()

        customer = Customer(user_id=customer_user.id, full_name="Cara Customer", phone="03001234567", address="Karachi, Gulshan-e-Iqbal, Block 5")
        db.session.add(customer)

        categories = {
            "Plumbing": ServiceCategory(name="Plumbing", description="Leaks, blockages, pipe repairs", default_sla_hours=48),
            "Electrical": ServiceCategory(name="Electrical", description="Wiring, outages, electrical faults", default_sla_hours=48),
            "Gas": ServiceCategory(name="Gas", description="Gas supply and appliance issues", default_sla_hours=24),
            "Water": ServiceCategory(name="Water", description="Water supply and quality issues", default_sla_hours=48),
            "Internet": ServiceCategory(name="Internet", description="Connectivity and network faults", default_sla_hours=24),
            "Billing": ServiceCategory(name="Billing", description="Charges, invoices and payment issues", default_sla_hours=72),
            "Maintenance": ServiceCategory(name="Maintenance", description="General maintenance and repairs", default_sla_hours=72),
            "Technical Support": ServiceCategory(name="Technical Support", description="Technical / equipment issues", default_sla_hours=24),
            "Security": ServiceCategory(name="Security", description="Safety and security concerns", default_sla_hours=8),
            "Other": ServiceCategory(name="Other", description="Anything that doesn't fit another category", default_sla_hours=72),
        }
        db.session.add_all(categories.values())
        db.session.flush()

        # Centralized default SLA hours by priority, used as a fallback
        # whenever a category/priority pair has no explicit SlaRule (see
        # app/services/sla.py). Per-category rules below override these.
        default_sla_hours = {"low": 72, "medium": 48, "high": 24, "urgent": 8}
        for cat in categories.values():
            for priority, hours in default_sla_hours.items():
                db.session.add(SlaRule(
                    category_id=cat.id, priority=priority,
                    response_hours=max(1, hours // 4), resolution_hours=hours,
                ))

        # Agent roster matching the example categories/skills. An agent can
        # belong to multiple categories (e.g. Ahmed Raza handles both
        # Plumbing and Maintenance).
        ali_khan = _make_agent("Ali Khan", "ali.khan@example.com")
        ahmed_raza = _make_agent("Ahmed Raza", "ahmed.raza@example.com")
        usman_malik = _make_agent("Usman Malik", "usman.malik@example.com")
        bilal_ahmed = _make_agent("Bilal Ahmed", "bilal.ahmed@example.com")
        hamza_khan = _make_agent("Hamza Khan", "hamza.khan@example.com")
        salman_raza = _make_agent("Salman Raza", "salman.raza@example.com")
        ahsan_ali = _make_agent("Ahsan Ali", "ahsan.ali@example.com")
        fahad_ahmed = _make_agent("Fahad Ahmed", "fahad.ahmed@example.com")
        muhammad_usman = _make_agent("Muhammad Usman", "muhammad.usman@example.com")
        db.session.flush()

        agent_category_links = [
            (ali_khan, "Plumbing"),
            (ahmed_raza, "Plumbing"),
            (ahmed_raza, "Maintenance"),
            (usman_malik, "Plumbing"),
            (bilal_ahmed, "Electrical"),
            (hamza_khan, "Electrical"),
            (salman_raza, "Internet"),
            (ahsan_ali, "Internet"),
            (fahad_ahmed, "Billing"),
            (muhammad_usman, "Billing"),
        ]
        for agent, cat_name in agent_category_links:
            db.session.add(AgentCategory(agent_id=agent.id, category_id=categories[cat_name].id))

        db.session.commit()
        print("Seed data created:")
        print("  admin@example.com / AdminPass123!")
        print("  supervisor@example.com / SuperviseMe123!")
        print("  customer@example.com / CustomerPass123!")
        print("  Agents (all AgentPass123!):")
        for agent, cat_name in agent_category_links:
            print(f"    {agent.email} - {cat_name}")


if __name__ == "__main__":
    seed()
