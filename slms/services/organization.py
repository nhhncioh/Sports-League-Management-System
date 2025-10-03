"""Organization management service."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from slms.extensions import db
from slms.models import Organization, User, UserRole

if TYPE_CHECKING:
    from slms.models import User as UserType


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    # Convert to lowercase
    text = text.lower()
    # Remove special characters, keep alphanumeric and hyphens
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def validate_slug(slug: str) -> tuple[bool, str | None]:
    """
    Validate organization slug.

    Returns:
        (is_valid, error_message)
    """
    if not slug:
        return False, "Slug cannot be empty"

    if len(slug) < 3:
        return False, "Slug must be at least 3 characters long"

    if len(slug) > 63:
        return False, "Slug must be 63 characters or less"

    if not re.match(r'^[a-z0-9-]+$', slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"

    if slug.startswith('-') or slug.endswith('-'):
        return False, "Slug cannot start or end with a hyphen"

    if '--' in slug:
        return False, "Slug cannot contain consecutive hyphens"

    # Reserved slugs
    reserved = {
        'admin', 'api', 'auth', 'public', 'static', 'assets',
        'login', 'logout', 'register', 'signup', 'www', 'mail',
        'ftp', 'smtp', 'pop', 'imap', 'webmail', 'cpanel',
        'system', 'root', 'test', 'demo', 'staging', 'prod',
    }
    if slug in reserved:
        return False, f"'{slug}' is a reserved slug and cannot be used"

    # Check if slug already exists
    if Organization.query.filter_by(slug=slug).first():
        return False, "This slug is already taken"

    return True, None


def create_organization(
    name: str,
    slug: str | None = None,
    owner_email: str | None = None,
    owner_password: str | None = None,
    description: str | None = None,
    **kwargs
) -> tuple[Organization | None, str | None]:
    """
    Create a new organization with an owner user.

    Args:
        name: Organization name
        slug: URL slug (auto-generated from name if not provided)
        owner_email: Owner's email address
        owner_password: Owner's password
        description: Organization description
        **kwargs: Additional organization fields

    Returns:
        (organization, error_message)
    """
    try:
        # Generate slug if not provided
        if not slug:
            slug = slugify(name)

        # Validate slug
        is_valid, error = validate_slug(slug)
        if not is_valid:
            return None, error

        # Create organization
        org = Organization(
            name=name,
            slug=slug,
            description=description,
            **{k: v for k, v in kwargs.items() if hasattr(Organization, k)}
        )
        db.session.add(org)
        db.session.flush()  # Get org.id

        # Create owner user if credentials provided
        if owner_email and owner_password:
            owner = User(
                org_id=org.id,
                email=owner_email.strip().lower(),
                role=UserRole.OWNER,
                is_active=True
            )
            owner.set_password(owner_password)
            db.session.add(owner)

        db.session.commit()
        return org, None

    except IntegrityError as e:
        db.session.rollback()
        if 'slug' in str(e):
            return None, "This slug is already taken"
        if 'email' in str(e):
            return None, "An account with this email already exists in this organization"
        return None, "Failed to create organization due to a database error"

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to create organization: {e}")
        return None, "An unexpected error occurred"


def update_organization(org: Organization, **kwargs) -> tuple[bool, str | None]:
    """
    Update organization fields.

    Args:
        org: Organization to update
        **kwargs: Fields to update

    Returns:
        (success, error_message)
    """
    try:
        # If slug is being changed, validate it
        if 'slug' in kwargs and kwargs['slug'] != org.slug:
            is_valid, error = validate_slug(kwargs['slug'])
            if not is_valid:
                return False, error

        # Update allowed fields
        for key, value in kwargs.items():
            if hasattr(org, key) and key not in ('id', 'created_at', 'updated_at'):
                setattr(org, key, value)

        db.session.commit()
        return True, None

    except IntegrityError:
        db.session.rollback()
        return False, "Failed to update organization (duplicate value)"

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to update organization: {e}")
        return False, "An unexpected error occurred"


def delete_organization(org: Organization) -> tuple[bool, str | None]:
    """
    Delete an organization and all its data.

    Args:
        org: Organization to delete

    Returns:
        (success, error_message)
    """
    try:
        db.session.delete(org)
        db.session.commit()
        return True, None

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to delete organization: {e}")
        return False, "An unexpected error occurred"


def get_organization_stats(org: Organization) -> dict:
    """
    Get statistics for an organization.

    Args:
        org: Organization

    Returns:
        Dictionary with organization stats
    """
    from slms.models import League, Team, Game, Season

    return {
        'users': len(org.users),
        'leagues': org_query(League).count(),
        'teams': org_query(Team).count(),
        'seasons': org_query(Season).count(),
        'games': org_query(Game).count(),
        'storage_used': org.storage_used,
        'storage_quota': org.storage_quota,
        'storage_percent': (org.storage_used / org.storage_quota * 100) if org.storage_quota else 0,
    }


def org_query(model):
    """Helper to get current org (placeholder - should import from tenant.py)."""
    from flask import g
    from slms.blueprints.common.tenant import org_query as _org_query
    return _org_query(model)


__all__ = [
    'slugify',
    'validate_slug',
    'create_organization',
    'update_organization',
    'delete_organization',
    'get_organization_stats',
]
