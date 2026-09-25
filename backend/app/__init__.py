import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, cors, limiter, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    cfg = config_by_name[config_name]
    app.config.from_object(cfg() if config_name == "production" else cfg)

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_password_change_enforcement(app)
    _register_security_headers(app)

    return app


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRFToken"],
    )

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "authentication_required", "message": "Login required"}), 401


def _register_blueprints(app):
    from app.routes.auth import bp as auth_bp
    from app.routes.users import bp as users_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.service_categories import bp as categories_bp
    from app.routes.sla_rules import bp as sla_bp
    from app.routes.service_requests import bp as requests_bp
    from app.routes.assignments import bp as assignments_bp
    from app.routes.appointments import bp as appointments_bp
    from app.routes.work_orders import bp as work_orders_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.complaints import bp as complaints_bp
    from app.routes.escalations import bp as escalations_bp
    from app.routes.messages import bp as messages_bp
    from app.routes.notifications import bp as notifications_bp
    from app.routes.finance import bp as finance_bp
    from app.routes.feedback import bp as feedback_bp
    from app.routes.audit_logs import bp as audit_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.search import bp as search_bp
    from app.routes.agent_categories import bp as agent_categories_bp

    api_prefix = "/api"
    app.register_blueprint(auth_bp, url_prefix=f"{api_prefix}/auth")
    app.register_blueprint(users_bp, url_prefix=f"{api_prefix}/users")
    app.register_blueprint(customers_bp, url_prefix=f"{api_prefix}/customers")
    app.register_blueprint(categories_bp, url_prefix=f"{api_prefix}/service-categories")
    app.register_blueprint(sla_bp, url_prefix=f"{api_prefix}/sla-rules")
    app.register_blueprint(requests_bp, url_prefix=f"{api_prefix}/service-requests")
    app.register_blueprint(assignments_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(appointments_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(work_orders_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(documents_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(complaints_bp, url_prefix=f"{api_prefix}/complaints")
    app.register_blueprint(escalations_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(messages_bp, url_prefix=f"{api_prefix}/messages")
    app.register_blueprint(notifications_bp, url_prefix=f"{api_prefix}/notifications")
    app.register_blueprint(finance_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(feedback_bp, url_prefix=f"{api_prefix}/feedback")
    app.register_blueprint(audit_bp, url_prefix=f"{api_prefix}/audit-logs")
    app.register_blueprint(dashboard_bp, url_prefix=f"{api_prefix}/dashboard")
    app.register_blueprint(search_bp, url_prefix=f"{api_prefix}/search")
    app.register_blueprint(agent_categories_bp, url_prefix=f"{api_prefix}")


def _register_error_handlers(app):
    from app.utils.validation import ValidationError
    from app.utils.files import UploadRejected
    from app.services.workflow import InvalidTransition

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"error": "validation_error", "fields": e.errors}), 400

    @app.errorhandler(UploadRejected)
    def handle_upload_rejected(e):
        return jsonify({"error": "upload_rejected", "message": str(e)}), 400

    @app.errorhandler(InvalidTransition)
    def handle_invalid_transition(e):
        return jsonify({"error": "invalid_transition", "message": str(e)}), 409

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({"error": e.name.lower().replace(" ", "_"), "message": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        # Never leak stack traces / internals to the client. Log server-side only.
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "internal_server_error", "message": "An unexpected error occurred"}), 500


def _register_password_change_enforcement(app):
    from flask_login import current_user

    @app.before_request
    def enforce_password_change():
        """A user who was issued a temporary password (via forgot-password)
        must change it before doing anything else. Enforced here, server-side,
        for every API request - not just as a frontend redirect - so the
        restriction can't be bypassed by calling the API directly."""
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        if request.blueprint == "auth":
            return None
        if current_user.is_authenticated and getattr(current_user, "must_change_password", False):
            return jsonify({
                "error": "password_change_required",
                "message": "You must change your temporary password before continuing.",
            }), 403
        return None


def _register_security_headers(app):
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
