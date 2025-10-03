"""Organization branding service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import g

if TYPE_CHECKING:
    from slms.models import Organization


def get_branding_context(org: Organization | None = None) -> dict:
    """
    Get branding context for templates.

    Args:
        org: Organization (defaults to current org from g.org)

    Returns:
        Dictionary with branding variables
    """
    if org is None:
        org = getattr(g, 'org', None)

    if not org:
        return _default_branding()

    return {
        # Organization info
        'org_name': org.name,
        'org_slug': org.slug,
        'org_description': org.description,
        'org_tagline': org.description,  # Alias

        # Contact info
        'org_contact_email': org.contact_email,
        'org_contact_phone': org.contact_phone,
        'org_website_url': org.website_url,

        # Branding
        'org_logo_url': org.logo_url,
        'org_favicon_url': org.favicon_url or org.logo_url,  # Fallback to logo
        'org_banner_url': org.banner_image_url,
        'org_primary_color': org.primary_color or '#007bff',
        'org_secondary_color': org.secondary_color or '#6c757d',
        'org_custom_css': org.custom_css,

        # Settings
        'org_timezone': org.timezone,
        'org_locale': org.locale,

        # Plan info
        'org_plan': org.plan_type,
        'org_is_active': org.is_active,
    }


def _default_branding() -> dict:
    """Return default branding when no org is loaded."""
    return {
        'org_name': 'Sports League Management',
        'org_slug': None,
        'org_description': None,
        'org_tagline': None,
        'org_contact_email': None,
        'org_contact_phone': None,
        'org_website_url': None,
        'org_logo_url': None,
        'org_favicon_url': None,
        'org_banner_url': None,
        'org_primary_color': '#007bff',
        'org_secondary_color': '#6c757d',
        'org_custom_css': None,
        'org_timezone': 'UTC',
        'org_locale': 'en_US',
        'org_plan': 'free',
        'org_is_active': True,
    }


def inject_branding_context():
    """
    Flask context processor to inject branding into all templates.

    Usage:
        app.context_processor(inject_branding_context)
    """
    return get_branding_context()


def generate_custom_css(org: Organization) -> str:
    """
    Generate CSS variables and custom styles for an organization.

    Args:
        org: Organization

    Returns:
        CSS string
    """
    css_parts = []

    # CSS Variables
    css_parts.append(":root {")
    if org.primary_color:
        css_parts.append(f"  --org-primary-color: {org.primary_color};")
    if org.secondary_color:
        css_parts.append(f"  --org-secondary-color: {org.secondary_color};")
    css_parts.append("}")

    # Custom CSS
    if org.custom_css:
        css_parts.append("")
        css_parts.append("/* Custom Organization CSS */")
        css_parts.append(org.custom_css)

    return "\n".join(css_parts)


__all__ = [
    'get_branding_context',
    'inject_branding_context',
    'generate_custom_css',
]
