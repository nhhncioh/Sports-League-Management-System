"""Domain-based theme and organization loader."""

from flask import request, g
from slms.extensions import db
from slms.models.models import Organization
import json


def load_org_by_domain():
    """
    Load organization based on the request domain.
    Checks custom_domain first, then falls back to slug-based routing.
    """
    host = request.host.lower()

    # Remove port if present
    if ':' in host:
        host = host.split(':')[0]

    # Try to find org by custom domain
    org = Organization.query.filter(
        Organization.custom_domain == host,
        Organization.is_active == True
    ).first()

    if org:
        return org, 'custom_domain'

    # Check if it's a subdomain pattern (e.g., myorg.sportslms.com)
    if '.' in host:
        subdomain = host.split('.')[0]
        org = Organization.query.filter(
            Organization.slug == subdomain,
            Organization.is_active == True
        ).first()

        if org:
            return org, 'subdomain'

    # Fall back to slug in URL path or session
    return None, None


def get_org_theme(org):
    """
    Get the theme configuration for an organization.
    Returns a merged theme with defaults.
    """
    default_theme = {
        'palette': {
            'primary': '#667eea',
            'secondary': '#6c757d',
            'accent': '#f97316',
            'background': '#f5f6fa',
            'surface': '#ffffff',
            'text': '#1f2937',
            'muted': '#6b7280',
            'heading': '#111827',
            'gradient_start': '#667eea',
            'gradient_end': '#764ba2',
        },
        'typography': {
            'base_family': 'Inter, system-ui, sans-serif',
            'heading_family': 'Inter, system-ui, sans-serif',
            'base_size': '16px',
            'line_height': 1.6,
        },
        'components': {
            'button_shape': 'rounded',
            'border_radius_scale': 'md',
            'card_shadow': 'medium',
        }
    }

    # If org has custom_css or theme settings, merge them
    if org:
        # You can extend this to load from a themes table or JSON field
        if hasattr(org, 'primary_color') and org.primary_color:
            default_theme['palette']['primary'] = org.primary_color
        if hasattr(org, 'secondary_color') and org.secondary_color:
            default_theme['palette']['secondary'] = org.secondary_color

    return default_theme


def get_org_hero_config(org):
    """
    Get hero section configuration for organization.
    """
    default_hero = {
        'title': org.name if org else 'Welcome to Your League',
        'subtitle': org.description if org and org.description else 'Experience world-class sports management',
        'gradient_start': '#667eea',
        'gradient_end': '#764ba2',
        'text_color': 'white',
        'background_image': org.banner_image_url if org and hasattr(org, 'banner_image_url') and org.banner_image_url else None,
        'hero_image': None,
        'primary_cta_text': 'View Standings',
        'primary_cta_url': '/standings',
        'primary_cta_icon': 'trophy',
        'secondary_cta_text': 'Stat Leaders',
        'secondary_cta_url': '/leaderboards',
        'secondary_cta_icon': 'chart-line',
        'features': [
            'Real-time Updates',
            'Complete Statistics',
            'Fan Engagement'
        ]
    }

    # Load from org settings if available
    # This could be extended to load from a JSON field in the org model

    return default_hero


def get_org_modules(org):
    """
    Get landing page modules for organization.
    Modules are configurable sections like features, testimonials, etc.
    """
    default_modules = [
        {
            'type': 'features',
            'title': 'Everything You Need',
            'subtitle': 'Comprehensive tools for managing your sports organization',
            'background': '#f8f9fa',
            'features': [
                {
                    'icon': 'trophy',
                    'color': '#667eea',
                    'title': 'Live Standings',
                    'description': 'Real-time standings updates with automatic calculation from game results.'
                },
                {
                    'icon': 'chart-line',
                    'color': '#10b981',
                    'title': 'Statistics',
                    'description': 'Comprehensive player and team statistics across all seasons.'
                },
                {
                    'icon': 'calendar',
                    'color': '#f59e0b',
                    'title': 'Schedule Management',
                    'description': 'Advanced scheduling with conflict detection and venue management.'
                },
                {
                    'icon': 'users',
                    'color': '#06b6d4',
                    'title': 'Team Management',
                    'description': 'Complete roster management with player profiles and media galleries.'
                },
                {
                    'icon': 'broadcast',
                    'color': '#8b5cf6',
                    'title': 'Live Scoring',
                    'description': 'Real-time score updates with play-by-play commentary.'
                },
                {
                    'icon': 'images',
                    'color': '#ec4899',
                    'title': 'Media Library',
                    'description': 'Rich media galleries for teams, players, and games.'
                }
            ]
        }
    ]

    # Load custom modules from org settings
    # This could be extended to load from a database table

    return default_modules


def get_org_stats(org):
    """
    Get organization statistics for display.
    """
    from slms.models.models import Team, Game, Player, Season

    stats = {
        'teams': 0,
        'games': 0,
        'players': 0,
        'seasons': 0
    }

    if org:
        stats['teams'] = Team.query.filter_by(org_id=org.id).count()
        stats['games'] = Game.query.filter_by(org_id=org.id).count()
        stats['players'] = Player.query.filter_by(org_id=org.id).count()
        stats['seasons'] = Season.query.filter_by(org_id=org.id, is_active=True).count()

    return stats


def get_footer_cta(org):
    """
    Get footer CTA configuration.
    """
    default_cta = {
        'title': 'Ready to Join?',
        'description': 'Be part of our growing sports community.',
        'cta_text': 'Get Started',
        'cta_url': '/auth/login'
    }

    return default_cta


def inject_org_branding():
    """
    Flask before_request handler to inject org branding into g object.
    Should be registered in app factory.
    """
    org, source = load_org_by_domain()

    if org:
        g.org = org
        g.org_source = source
        g.theme = get_org_theme(org)
        g.hero = get_org_hero_config(org)
        g.modules = get_org_modules(org)
        g.stats = get_org_stats(org)
        g.footer_cta = get_footer_cta(org)
    else:
        # Set defaults when no org is found
        g.org = None
        g.org_source = None
        g.theme = get_org_theme(None)
        g.hero = get_org_hero_config(None)
        g.modules = get_org_modules(None)
        g.stats = {'teams': 0, 'games': 0, 'players': 0, 'seasons': 0}
        g.footer_cta = get_footer_cta(None)


def register_domain_loader(app):
    """
    Register the domain loader with the Flask app.
    """
    @app.before_request
    def before_request_domain_loader():
        inject_org_branding()
