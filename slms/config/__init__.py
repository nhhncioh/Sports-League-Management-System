import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Provide a safe development fallback to avoid 500s when SECRET_KEY is missing.
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-me'
    DATABASE_URL = os.getenv('DATABASE_URL')
    FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///slms.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None

    # Multi-tenant host/path configuration
    # Example: TENANT_BASE_DOMAIN=".localhost" allows demo.localhost to resolve slug "demo"
    TENANT_BASE_DOMAIN = os.getenv('TENANT_BASE_DOMAIN')
    # Default org slug to use when none can be resolved (useful in development on localhost)
    DEFAULT_ORG_SLUG = os.getenv('DEFAULT_ORG_SLUG')
    # Allow aligning tenant to the authenticated user's organization on mismatch (dev convenience)
    ALLOW_ORG_FALLBACK = os.getenv('ALLOW_ORG_FALLBACK', 'true').lower() in ('1', 'true', 'yes')

