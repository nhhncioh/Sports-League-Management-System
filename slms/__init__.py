"""Application factory for Sports League Management System."""

from __future__ import annotations

import os
from flask import Flask, render_template, request, redirect, url_for

from slms.blueprints.admin import admin_bp, registration_admin_bp
from slms.blueprints.public import public_bp, portal_bp, registration_bp
from slms.blueprints.api import api_bp
from slms.blueprints.auth import auth_bp
from slms.blueprints.schedule_mgmt import schedule_mgmt_bp
from slms.blueprints.org_admin import org_admin_bp
from slms.blueprints.league_mgmt import league_mgmt_bp
from slms.blueprints.live_scoring import live_scoring_bp
from slms.blueprints.content_mgmt import content_mgmt_bp
from slms.config import Config
from slms.extensions import (
    db,
    migrate,
    login_manager,
    csrf,
    limiter,
)
from slms.models import User
from slms.blueprints.common.tenant import init_tenant
from slms.services.db import close_db, ensure_minimum_schema, ensure_core_tables
from slms.security.config import (
    configure_security_headers,
    configure_secure_session,
    validate_input_length
)


def create_app(config_class=Config):
    """Create Flask application."""
    # Use package-relative templates/static so Jinja can find files in slms/templates
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    limiter.init_app(app)
    init_tenant(app)

    # Safety nets for development environments without migrations
    if os.getenv('SLMS_SKIP_BOOTSTRAP', '0') != '1':
        try:
            with app.app_context():
                ensure_core_tables()
                ensure_minimum_schema()
        except Exception:
            pass

    # Configure security
    configure_security_headers(app)
    configure_secure_session(app)
    validate_input_length(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, user_id)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        return redirect(url_for('auth.login', next=request.url))

    # Ensure models are registered for migrations
    import slms.models  # noqa: F401

    # Enable live reload and disable caching in development
    if os.getenv("FLASK_ENV") == "development":
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        app.jinja_env.auto_reload = True

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(org_admin_bp, url_prefix='/org')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(schedule_mgmt_bp)  # Schedule management routes
    app.register_blueprint(league_mgmt_bp)  # League lifecycle management routes
    app.register_blueprint(live_scoring_bp)  # Live scoring console routes
    app.register_blueprint(content_mgmt_bp)  # Content management routes
    app.register_blueprint(registration_admin_bp)  # Registration admin routes
    app.register_blueprint(portal_bp)  # Portal routes at root
    app.register_blueprint(registration_bp)  # Registration routes at root
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    @app.teardown_appcontext
    def teardown_db(exception):
        close_db()

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    # Site settings and branding processors (can be skipped for CLI/migrations)
    if os.getenv('SLMS_SKIP_SITE', '0') != '1':
        from slms.services.site import inject_site_settings
        app.context_processor(inject_site_settings)

        from slms.services.branding import inject_branding_context
        app.context_processor(inject_branding_context)

    # Register CLI commands
    from slms.commands import register_commands
    register_commands(app)

    return app









