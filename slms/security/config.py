"""Security configuration and middleware."""

from flask import request, g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis


def get_user_id():
    """Get current user ID for rate limiting."""
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user.id
    return get_remote_address()


def create_limiter(app):
    """Create and configure rate limiter."""
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/1')

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=redis_url,
        default_limits=["1000 per day", "100 per hour"]
    )

    return limiter


def configure_security_headers(app):
    """Configure security headers."""

    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Control referrer information
        response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'

        # XSS Protection (legacy, but still good to have)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "img-src 'self' data: https:",
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]

        # More restrictive CSP for production
        if app.config.get('ENV') == 'production':
            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",  # Bootstrap needs inline styles
                "img-src 'self' data:",
                "font-src 'self'",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]

        response.headers['Content-Security-Policy'] = "; ".join(csp_directives)

        # HSTS for HTTPS (only add if using HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    return app


def configure_secure_session(app):
    """Configure secure session settings."""
    # Session security
    app.config.update(
        SESSION_COOKIE_SECURE=app.config.get('ENV') == 'production',  # HTTPS only in production
        SESSION_COOKIE_HTTPONLY=True,  # Prevent JavaScript access
        SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=7200,  # 2 hours
    )

    # CSRF settings
    app.config.update(
        WTF_CSRF_TIME_LIMIT=3600,  # 1 hour CSRF token validity
        WTF_CSRF_SSL_STRICT=app.config.get('ENV') == 'production',
    )

    return app


def validate_input_length(app):
    """Middleware to validate request payload size."""
    @app.before_request
    def limit_request_size():
        # Limit JSON payload size to 1MB
        if request.content_length and request.content_length > 1024 * 1024:
            from flask import abort
            abort(413)  # Payload Too Large

    return app


def configure_password_policy():
    """Configure password complexity requirements."""
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = False  # Start with basic requirements

    return {
        'min_length': PASSWORD_MIN_LENGTH,
        'require_uppercase': PASSWORD_REQUIRE_UPPERCASE,
        'require_lowercase': PASSWORD_REQUIRE_LOWERCASE,
        'require_digits': PASSWORD_REQUIRE_DIGITS,
        'require_special': PASSWORD_REQUIRE_SPECIAL,
    }


def is_password_strong(password):
    """Validate password against policy."""
    policy = configure_password_policy()

    if len(password) < policy['min_length']:
        return False, f"Password must be at least {policy['min_length']} characters long"

    if policy['require_uppercase'] and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if policy['require_lowercase'] and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if policy['require_digits'] and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if policy['require_special']:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

    return True, "Password meets requirements"


# Rate limiting decorators
def auth_rate_limit():
    """Rate limit for authentication endpoints."""
    return "5 per minute"


def admin_rate_limit():
    """Rate limit for admin endpoints."""
    return "200 per hour"


def api_rate_limit():
    """Rate limit for API endpoints."""
    return "100 per hour"


def public_rate_limit():
    """Rate limit for public endpoints."""
    return "50 per minute"


__all__ = [
    'create_limiter',
    'configure_security_headers',
    'configure_secure_session',
    'validate_input_length',
    'is_password_strong',
    'auth_rate_limit',
    'admin_rate_limit',
    'api_rate_limit',
    'public_rate_limit'
]