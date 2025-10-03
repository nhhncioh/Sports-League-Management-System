"""Site settings service with navigation support."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from flask import g, url_for, session

from slms.services.db import get_db

DEFAULT_PRIMARY_COLOR = "#343a40"

_ALLOWED_AUDIENCES = {"everyone", "auth", "guest", "admin"}
DEFAULT_NAV_LINKS: List[Dict[str, Any]] = [
    {
        "label": "Home",
        "type": "endpoint",
        "value": "public.landing",
        "icon": "ph ph-house",
        "audience": "everyone",
        "open_in_new": False,
    },
    {
        "label": "Portal",
        "type": "endpoint",
        "value": "portal.index",
        "icon": "ph ph-squares-four",
        "audience": "everyone",
        "open_in_new": False,
    },
    {
        "label": "Admin",
        "type": "endpoint",
        "value": "admin.admin_dashboard",
        "icon": "ph ph-speedometer",
        "audience": "admin",
        "open_in_new": False,
    },
]
LEGACY_ICON_MAP = {
    'bi-house': 'ph ph-house',
    'bi-grid': 'ph ph-squares-four',
    'bi-speedometer2': 'ph ph-speedometer',
    'bi-people': 'ph ph-users-three',
    'bi-trophy': 'ph ph-trophy',
    'bi-gear': 'ph ph-gear-six',
    'bi-calendar-event': 'ph ph-calendar-dots',
    'bi-clipboard-data': 'ph ph-clipboard',
    'bi-lightning': 'ph ph-lightning',
    'bi-star': 'ph ph-star',
    'bi-life-preserver': 'ph ph-lifebuoy',
    'bi-flag': 'ph ph-flag',
    'bi-whistle': 'ph ph-megaphone',
    'bi-house-door': 'ph ph-house',
    'bi-arrow-left': 'ph ph-arrow-left',
    'bi-lightbulb': 'ph ph-lightbulb',
    'bi-plus-lg': 'ph ph-plus',
    'bi-x-lg': 'ph ph-x',
    'bi-person-circle': 'ph ph-user-circle',
    'bi-box-arrow-right': 'ph ph-sign-out',
    'bi-box-arrow-in-right': 'ph ph-sign-in',
    'bi-arrow-up-right': 'ph ph-trend-up',
    'bi-arrow-down-right': 'ph ph-trend-down',
    'bi-compass': 'ph ph-compass',
    'bi-shield': 'ph ph-shield',
    'bi-person-badge': 'ph ph-identification-badge',
    'bi-magic': 'ph ph-magic-wand',
    'bi-arrow-repeat': 'ph ph-arrow-clockwise',
    'bi-cash-coin': 'ph ph-coins',
    'bi-layout-text-window': 'ph ph-browser',
    'bi-sliders': 'ph ph-sliders',
    'bi-calendar3': 'ph ph-calendar',
    'bi-geo-alt': 'ph ph-map-pin',
    'bi-list-ol': 'ph ph-list-numbers',
    'bi-lightning-charge': 'ph ph-lightning',
    'bi-calendar2-week': 'ph ph-calendar-dots',
    'bi-chevron-right': 'ph ph-caret-right',
    'bi-calendar-week': 'ph ph-calendar-dots',
    # Additional common Bootstrap Icons → Phosphor mappings
    'bi-search': 'ph ph-magnifying-glass',
    'bi-plus': 'ph ph-plus',
    'bi-plus-circle': 'ph ph-plus-circle',
    'bi-x': 'ph ph-x',
    'bi-trash': 'ph ph-trash',
    'bi-pencil': 'ph ph-pencil',
    'bi-eye': 'ph ph-eye',
    'bi-download': 'ph ph-download',
    'bi-upload': 'ph ph-upload',
    'bi-check': 'ph ph-check',
    'bi-check-circle': 'ph ph-check-circle',
    'bi-x-circle': 'ph ph-x-circle',
    'bi-info-circle': 'ph ph-info',
    'bi-exclamation-triangle': 'ph ph-warning',
    'bi-exclamation-circle': 'ph ph-warning-circle',
    'bi-arrow-left': 'ph ph-arrow-left',
    'bi-arrow-right': 'ph ph-arrow-right',
    'bi-arrow-clockwise': 'ph ph-arrow-clockwise',
    'bi-envelope': 'ph ph-envelope',
    'bi-envelope-open': 'ph ph-envelope-open',
    'bi-calendar-plus': 'ph ph-calendar-plus',
    'bi-calendar-day': 'ph ph-calendar',
    'bi-calendar-x': 'ph ph-calendar-x',
    'bi-clock': 'ph ph-clock',
    'bi-clock-history': 'ph ph-clock-countdown',
    'bi-people': 'ph ph-users',
    'bi-person-plus': 'ph ph-user-plus',
    'bi-credit-card': 'ph ph-credit-card',
    'bi-list-ul': 'ph ph-list-bullets',
    'bi-send': 'ph ph-paper-plane-tilt',
    'bi-printer': 'ph ph-printer',
    'bi-broadcast': 'ph ph-broadcast',
    'bi-table': 'ph ph-table',
    'bi-arrow-down-up': 'ph ph-arrows-vertical',
    'bi-funnel': 'ph ph-funnel',
    'bi-inbox': 'ph ph-tray',
    'bi-gift': 'ph ph-gift',
    'bi-file-text': 'ph ph-file-text',
    'bi-file-code': 'ph ph-file-code',
    'bi-file-earmark-x': 'ph ph-file-x',
    'bi-file-earmark-spreadsheet': 'ph ph-file-csv',
    'bi-envelope-x': 'ph ph-envelope-x',
    'bi-envelope-check': 'ph ph-envelope-simple-check',
    'bi-building': 'ph ph-buildings',
    'bi-bar-chart': 'ph ph-chart-bar',
    'bi-tag': 'ph ph-tag',
    'bi-pause': 'ph ph-pause',
    'bi-shield-check': 'ph ph-shield-check',
    'bi-magic': 'ph ph-magic-wand',
    'bi-code': 'ph ph-code',
    'bi-link': 'ph ph-link',
}




DEFAULT_SOCIAL_KEYS: List[str] = [
    "facebook",
    "instagram",
    "twitter",
    "youtube",
    "tiktok",
    "linkedin",
    "twitch",
    "custom_1",
    "custom_2",
]

DEFAULT_SOCIAL_LINKS: Dict[str, Optional[str]] = {key: None for key in DEFAULT_SOCIAL_KEYS}

DEFAULT_FEATURE_FLAGS: Dict[str, bool] = {
    "show_hero": True,
    "show_stats": True,
    "show_leagues": True,
    "show_recent_games": True,
    "show_cta_panel": True,
    "show_team_logos": True,
    "show_breadcrumbs": True,
    "show_footer_social": True,
    "enable_dark_mode": False,
    "show_season_filter": True,
    "show_live_scores": True,
    "show_venue_details": True,
    "show_player_stats": True,
    "show_standings_preview": True,
    "show_featured_players": True,
    "show_latest_results": True,
    "show_highlight_reel": False,
    "show_partner_logos": False,
    "show_match_filters": True,
    "enable_animated_icons": False,
    "enable_card_glow": False,
}

DEFAULT_THEME_CONFIG: Dict[str, Any] = {
    "palette": {
        "primary": DEFAULT_PRIMARY_COLOR,
        "secondary": "#6c757d",
        "accent": "#f97316",
        "neutral": "#f5f7fb",
        "surface": "#ffffff",
        "background": "#f5f6fa",
        "text": "#1f2937",
        "muted": "#6b7280",
        "heading": "#111827",
        "nav_background": None,
        "nav_text": "#ffffff",
        "nav_hover": "rgba(255, 255, 255, 0.85)",
        "card_border": "#d0d5dd",
        "success": "#198754",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#0dcaf0",
        "gradient_start": "#2563eb",
        "gradient_end": "#9333ea",
        "highlight": "#fde68a",
        "shadow": "rgba(15, 23, 42, 0.12)",
    },
    "typography": {
        "base_family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif",
        "heading_family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif",
        "base_size": "16px",
        "scale": 1.0,
        "base_weight": "400",
        "heading_weight": "600",
        "letter_spacing": "normal",
        "heading_letter_spacing": "0.01em",
        "heading_transform": "none",
        "line_height": "1.6",
        "heading_line_height": "1.3",
    },
    "iconography": {
        "weight": "regular",
        "primary_color": None,
        "accent_color": None,
        "size_scale": 1.0,
        "hover_color": None,
        "active_color": None,
    },
    "components": {
        "button_shape": "rounded",
        "button_style": "solid",
        "button_text_transform": "none",
        "card_style": "elevated",
        "card_shadow": "medium",
        "input_style": "soft",
        "border_radius_scale": "md",
        "layout_density": "comfortable",
        "nav_style": "glass",
        "navbar_transparency": 0.9,
        "navbar_blur": "18px",
        "use_gradients": True,
        "section_dividers": False,
        "surface_tint": "subtle",
        "card_border": "1px solid rgba(15, 23, 42, 0.08)",
        "chip_style": "soft",
        "button_glow": False,
    },
    "custom_css": "",
    "social_labels": {
        "custom_1": "Custom Link 1",
        "custom_2": "Custom Link 2",
    },
}

CTA_SLOT_KEYS: tuple[str, ...] = (
    "hero_primary",
    "hero_secondary",
    "footer_primary",
    "footer_secondary",
)

CTA_ALLOWED_STYLES: Set[str] = {"primary", "secondary", "outline", "ghost", "link"}
CTA_ALLOWED_URL_SCHEMES: Set[str] = {"http", "https", "mailto", "tel"}
CTA_LABEL_MAX_LENGTH = 80
CTA_ICON_MAX_LENGTH = 80
CTA_URL_MAX_LENGTH = 500

DEFAULT_THEME_CTA_SLOTS: Dict[str, Dict[str, Any]] = {
    "hero_primary": {
        "label": "View Schedule",
        "url": "/schedule",
        "style": "primary",
        "icon": "ph ph-calendar-dots",
        "enabled": True,
        "new_tab": False,
    },
    "hero_secondary": {
        "label": "Register Team",
        "url": "/register",
        "style": "outline",
        "icon": "ph ph-users-three",
        "enabled": True,
        "new_tab": False,
    },
    "footer_primary": {
        "label": "Contact League Office",
        "url": "/contact",
        "style": "secondary",
        "icon": "ph ph-envelope",
        "enabled": True,
        "new_tab": False,
    },
    "footer_secondary": {
        "label": "Download Schedule",
        "url": "/downloads/schedule.pdf",
        "style": "ghost",
        "icon": "ph ph-arrow-square-out",
        "enabled": False,
        "new_tab": True,
    },
}


def default_cta_slots() -> Dict[str, Dict[str, Any]]:
    return {key: copy.deepcopy(value) for key, value in DEFAULT_THEME_CTA_SLOTS.items()}


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in {"true", "1", "yes", "on"}:
            return True
        if candidate in {"false", "0", "no", "off"}:
            return False
    return fallback


def _clean_cta_text(value: Any, fallback: str, limit: int) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        candidate = fallback
    return candidate[:limit]


def _clean_cta_url(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return fallback
    if candidate.startswith(('#', '/')):
        return candidate[:CTA_URL_MAX_LENGTH]
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.scheme.lower() in CTA_ALLOWED_URL_SCHEMES and parsed.netloc:
        return candidate[:CTA_URL_MAX_LENGTH]
    return fallback


def _normalize_cta_slot(data: Any, defaults: Dict[str, Any]) -> Dict[str, Any]:
    base = copy.deepcopy(defaults)
    if not isinstance(data, dict):
        return base
    base['label'] = _clean_cta_text(data.get('label'), base.get('label', ''), CTA_LABEL_MAX_LENGTH)
    default_url = base.get('url') or '#'
    base['url'] = _clean_cta_url(data.get('url'), default_url)
    style = str(data.get('style') or base.get('style') or 'primary').strip().lower()
    if style in CTA_ALLOWED_STYLES:
        base['style'] = style
    icon_value = _clean_cta_text(data.get('icon'), base.get('icon', ''), CTA_ICON_MAX_LENGTH)
    base['icon'] = icon_value or None
    base['enabled'] = _as_bool(data.get('enabled'), bool(base.get('enabled', True)))
    base['new_tab'] = _as_bool(data.get('new_tab'), bool(base.get('new_tab', False)))
    return base


def normalize_cta_slots(slots: Any, *, include_defaults: bool = True) -> Dict[str, Dict[str, Any]]:
    source = slots if isinstance(slots, dict) else {}
    normalized: Dict[str, Dict[str, Any]] = {}
    fallback_defaults = DEFAULT_THEME_CTA_SLOTS['hero_primary']
    if include_defaults:
        keys = list(DEFAULT_THEME_CTA_SLOTS.keys())
    else:
        keys = list(source.keys())
    for key in keys:
        defaults = DEFAULT_THEME_CTA_SLOTS.get(key, fallback_defaults)
        normalized[key] = _normalize_cta_slot(source.get(key), defaults)
    for key, value in source.items():
        if key in normalized:
            continue
        defaults = DEFAULT_THEME_CTA_SLOTS.get(key, fallback_defaults)
        normalized[key] = _normalize_cta_slot(value, defaults)
    return normalized


def ensure_theme_cta_slots(theme_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    slots = normalize_cta_slots(theme_config.get('cta_slots'), include_defaults=True)
    theme_config['cta_slots'] = slots
    return slots


def merge_theme_cta_slots(theme_config: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    existing = normalize_cta_slots(theme_config.get('cta_slots'), include_defaults=True)
    incoming = normalize_cta_slots(updates, include_defaults=False)
    if incoming:
        existing.update(incoming)
    theme_config['cta_slots'] = existing
    return existing


def get_theme_cta_slots(settings: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    if settings is None:
        settings = _load_site_settings()
    theme = copy.deepcopy(settings.get('theme', DEFAULT_THEME_CONFIG))
    return ensure_theme_cta_slots(theme)




def _merge_nested(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep merged copy of default with values from override."""
    result = copy.deepcopy(default)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_nested(result[key], value)
        else:
            result[key] = value
    return result

def _ensure_site_settings_schema(cur) -> None:
    session = getattr(cur, "_session", None)
    dialect_name = ""
    if session is not None:
        try:
            bind = session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "") or ""
        except Exception:
            dialect_name = ""
    dialect_name = dialect_name.lower()

    if dialect_name == "sqlite":
        create_sql = """
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_title TEXT DEFAULT 'Sports League Management System',
            brand_image_url TEXT,
            primary_color TEXT DEFAULT '#343a40',
            nav_layout TEXT DEFAULT 'top',
            navigation_json TEXT,
            favicon_url TEXT,
            league_tagline TEXT,
            contact_email TEXT,
            social_links_json TEXT,
            feature_flags_json TEXT,
            theme_config_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS site_settings (
            id SERIAL PRIMARY KEY,
            site_title TEXT DEFAULT 'Sports League Management System',
            brand_image_url TEXT,
            primary_color TEXT DEFAULT '#343a40',
            nav_layout TEXT DEFAULT 'top',
            navigation_json TEXT,
            favicon_url TEXT,
            league_tagline TEXT,
            contact_email TEXT,
            social_links_json TEXT,
            feature_flags_json TEXT,
            theme_config_json TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """

    cur.execute(create_sql)
    if dialect_name == "sqlite":
        create_versions_sql = """
        CREATE TABLE IF NOT EXISTS site_theme_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_settings_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'preview',
            label TEXT,
            author_id INTEGER,
            payload TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP,
            FOREIGN KEY(site_settings_id) REFERENCES site_settings(id) ON DELETE CASCADE
        );
        """
        create_media_sql = """
        CREATE TABLE IF NOT EXISTS site_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_settings_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            original_name TEXT,
            mime_type TEXT,
            file_size INTEGER,
            url TEXT NOT NULL,
            alt_text TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY(site_settings_id) REFERENCES site_settings(id) ON DELETE CASCADE
        );
        """
    else:
        create_versions_sql = """
        CREATE TABLE IF NOT EXISTS site_theme_versions (
            id SERIAL PRIMARY KEY,
            site_settings_id INTEGER NOT NULL REFERENCES site_settings(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'preview',
            label TEXT,
            author_id INTEGER,
            payload TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP WITH TIME ZONE
        );
        """
        create_media_sql = """
        CREATE TABLE IF NOT EXISTS site_media (
            id SERIAL PRIMARY KEY,
            site_settings_id INTEGER NOT NULL REFERENCES site_settings(id) ON DELETE CASCADE,
            file_name TEXT NOT NULL,
            original_name TEXT,
            mime_type TEXT,
            file_size BIGINT,
            url TEXT NOT NULL,
            alt_text TEXT,
            category TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER
        );
        """

    cur.execute(create_versions_sql)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_site_theme_versions_status ON site_theme_versions(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_site_theme_versions_created ON site_theme_versions(created_at)")

    cur.execute(create_media_sql)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_site_media_created ON site_media(created_at)")

    existing_columns: Set[str] = set()
    try:
        if dialect_name == "sqlite":
            cur.execute("PRAGMA table_info('site_settings')")
            existing_columns = {row[1] for row in cur.fetchall()}
        else:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'site_settings'
                """
            )
            existing_columns = {row[0] for row in cur.fetchall()}
    except Exception:
        existing_columns = set()

    migrations = {
        'nav_layout': "ALTER TABLE site_settings ADD COLUMN nav_layout TEXT DEFAULT 'top'",
        'navigation_json': "ALTER TABLE site_settings ADD COLUMN navigation_json TEXT",
        'favicon_url': "ALTER TABLE site_settings ADD COLUMN favicon_url TEXT",
        'league_tagline': "ALTER TABLE site_settings ADD COLUMN league_tagline TEXT",
        'contact_email': "ALTER TABLE site_settings ADD COLUMN contact_email TEXT",
        'social_links_json': "ALTER TABLE site_settings ADD COLUMN social_links_json TEXT",
        'feature_flags_json': "ALTER TABLE site_settings ADD COLUMN feature_flags_json TEXT",
        'theme_config_json': "ALTER TABLE site_settings ADD COLUMN theme_config_json TEXT",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            cur.execute(statement)

def _sanitize_nav_link(entry: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    label = str(entry.get("label", "")).strip()
    raw_value = str(entry.get("value", "")).strip()
    if not label or not raw_value:
        return None
    nav_type = str(entry.get("type", "url")).strip().lower()
    if nav_type not in {"url", "endpoint"}:
        nav_type = "url"
    icon = str(entry.get("icon", "")).strip() or None
    if icon and icon in LEGACY_ICON_MAP:
        icon = LEGACY_ICON_MAP[icon]
    audience = str(entry.get("audience", "everyone")).strip().lower()
    if audience not in _ALLOWED_AUDIENCES:
        audience = "everyone"
    open_in_new = bool(entry.get("open_in_new", False))
    return {
        "label": label,
        "type": nav_type,
        "value": raw_value,
        "icon": icon,
        "audience": audience,
        "open_in_new": open_in_new,
    }


def _resolve_nav_links(raw_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    resolved: List[Dict[str, Any]] = []
    for item in raw_links:
        nav = dict(item)
        href = "#"
        broken = False
        if nav["type"] == "endpoint":
            try:
                href = url_for(nav["value"])  # type: ignore[arg-type]
            except Exception:
                href = "/"
        else:
            href = nav["value"]
        nav.update({"href": href, "broken": False})
        resolved.append(nav)
    return resolved


def _default_nav_links() -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for item in DEFAULT_NAV_LINKS:
        sanitized = _sanitize_nav_link(item)
        if sanitized:
            links.append(sanitized)
    return links


def _load_site_settings() -> Dict[str, Any]:
    if hasattr(g, "_site_settings_cache"):
        return g._site_settings_cache  # type: ignore[attr-defined]

    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            return lowered in {"1", "true", "yes", "on"}
        return default

    try:
        db = get_db()
        cur = db.cursor()
        _ensure_site_settings_schema(cur)
        cur.execute(
            """
            SELECT
                id,
                site_title,
                brand_image_url,
                primary_color,
                nav_layout,
                navigation_json,
                favicon_url,
                league_tagline,
                contact_email,
                social_links_json,
                feature_flags_json,
                theme_config_json
            FROM site_settings
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            navigation_json = json.dumps(DEFAULT_NAV_LINKS)
            social_json = json.dumps(DEFAULT_SOCIAL_LINKS)
            feature_json = json.dumps(DEFAULT_FEATURE_FLAGS)
            theme_json = json.dumps(DEFAULT_THEME_CONFIG)
            cur.execute(
                """
                INSERT INTO site_settings (
                    site_title,
                    brand_image_url,
                    primary_color,
                    nav_layout,
                    navigation_json,
                    favicon_url,
                    league_tagline,
                    contact_email,
                    social_links_json,
                    feature_flags_json,
                    theme_config_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, site_title, brand_image_url, primary_color, nav_layout, navigation_json, favicon_url,
                          league_tagline, contact_email, social_links_json, feature_flags_json, theme_config_json
                """,
                (
                    "Sports League Management System",
                    None,
                    DEFAULT_PRIMARY_COLOR,
                    "top",
                    navigation_json,
                    None,
                    None,
                    None,
                    social_json,
                    feature_json,
                    theme_json,
                ),
            )
            row = cur.fetchone()
            db.commit()

        navigation_json = row[5] or json.dumps(DEFAULT_NAV_LINKS)
        try:
            parsed_nav = json.loads(navigation_json)
        except (TypeError, json.JSONDecodeError):
            parsed_nav = DEFAULT_NAV_LINKS

        raw_links: List[Dict[str, Any]] = []
        for entry in parsed_nav:
            sanitized = _sanitize_nav_link(entry)
            if sanitized:
                raw_links.append(sanitized)
        if not raw_links:
            raw_links = _default_nav_links()

        social_links = dict(DEFAULT_SOCIAL_LINKS)
        raw_social = row[9]
        if raw_social:
            try:
                loaded_social = json.loads(raw_social)
                if isinstance(loaded_social, dict):
                    for key, value in loaded_social.items():
                        social_links[key] = value or None
            except (TypeError, json.JSONDecodeError):
                pass

        feature_flags = dict(DEFAULT_FEATURE_FLAGS)
        raw_flags = row[10]
        if raw_flags:
            try:
                loaded_flags = json.loads(raw_flags)
                if isinstance(loaded_flags, dict):
                    for key, value in loaded_flags.items():
                        feature_flags[key] = _coerce_bool(value, feature_flags.get(key, False))
            except (TypeError, json.JSONDecodeError):
                pass

        theme_config = copy.deepcopy(DEFAULT_THEME_CONFIG)
        raw_theme = row[11]
        if raw_theme:
            try:
                parsed_theme = json.loads(raw_theme)
                if isinstance(parsed_theme, dict):
                    theme_config = _merge_nested(DEFAULT_THEME_CONFIG, parsed_theme)
                else:
                    theme_config = copy.deepcopy(DEFAULT_THEME_CONFIG)
            except (TypeError, json.JSONDecodeError):
                theme_config = copy.deepcopy(DEFAULT_THEME_CONFIG)

        palette = theme_config.setdefault("palette", {})
        typography = theme_config.setdefault("typography", {})
        iconography = theme_config.setdefault("iconography", {})
        components = theme_config.setdefault("components", {})

        palette.setdefault("primary", row[3] or DEFAULT_PRIMARY_COLOR)
        if not palette.get("primary"):
            palette["primary"] = DEFAULT_PRIMARY_COLOR
        if row[3] and palette["primary"] != row[3]:
            palette["primary"] = row[3]
        for key, default_value in DEFAULT_THEME_CONFIG["palette"].items():
            palette.setdefault(key, default_value)
        for key, default_value in DEFAULT_THEME_CONFIG["typography"].items():
            typography.setdefault(key, default_value)
        for key, default_value in DEFAULT_THEME_CONFIG["iconography"].items():
            iconography.setdefault(key, default_value)
        for key, default_value in DEFAULT_THEME_CONFIG["components"].items():
            components.setdefault(key, default_value)
        cta_slots = ensure_theme_cta_slots(theme_config)
        if "custom_css" not in theme_config:
            theme_config["custom_css"] = ""
        if "social_labels" not in theme_config or not isinstance(theme_config.get("social_labels"), dict):
            theme_config["social_labels"] = {"custom_1": "Custom Link 1", "custom_2": "Custom Link 2"}

        settings = {
            "id": row[0],
            "site_title": row[1],
            "brand_image_url": row[2],
            "primary_color": palette.get("primary", DEFAULT_PRIMARY_COLOR),
            "nav_layout": row[4] or "top",
            "navigation_links_raw": raw_links,
            "navigation_links": _resolve_nav_links(raw_links),
            "favicon_url": row[6],
            "league_tagline": row[7],
            "contact_email": row[8],
            "social_links": social_links,
            "feature_flags": feature_flags,
            "theme": theme_config,
            "cta_slots": cta_slots,
        }

        for palette_key, palette_value in palette.items():
            settings[f"{palette_key}_color"] = palette_value
        for key, value in social_links.items():
            settings[f"{key}_url"] = value
        for key, value in feature_flags.items():
            settings[key] = value
        settings["custom_css"] = theme_config.get("custom_css", "")

        g._site_settings_cache = settings  # type: ignore[attr-defined]
        return settings
    except Exception:
        fallback_links = _default_nav_links()
        fallback_theme = copy.deepcopy(DEFAULT_THEME_CONFIG)
        fallback_cta_slots = ensure_theme_cta_slots(fallback_theme)
        settings = {
            "site_title": "Sports League Management System",
            "brand_image_url": None,
            "primary_color": DEFAULT_PRIMARY_COLOR,
            "nav_layout": "top",
            "navigation_links_raw": fallback_links,
            "navigation_links": _resolve_nav_links(fallback_links),
            "favicon_url": None,
            "league_tagline": None,
            "contact_email": None,
            "social_links": dict(DEFAULT_SOCIAL_LINKS),
            "feature_flags": dict(DEFAULT_FEATURE_FLAGS),
            "theme": fallback_theme,
            "custom_css": fallback_theme.get("custom_css", ""),
            "cta_slots": fallback_cta_slots,
        }
        for key, value in settings["social_links"].items():
            settings[f"{key}_url"] = value
        for key, value in settings["feature_flags"].items():
            settings[key] = value
        g._site_settings_cache = settings  # type: ignore[attr-defined]
        return settings


def invalidate_site_settings_cache() -> None:
    if hasattr(g, "_site_settings_cache"):
        delattr(g, "_site_settings_cache")


def inject_site_settings():
    settings = _load_site_settings()
    preview_active = False
    if session.get('theme_preview_active') and session.get('is_admin'):
        preview = get_site_theme_preview()
        if preview:
            settings = _apply_payload_to_settings(settings, preview['payload'])
            preview_active = True
        else:
            session.pop('theme_preview_active', None)
    theme = settings.get("theme", DEFAULT_THEME_CONFIG)
    if not isinstance(theme, dict):
        theme = copy.deepcopy(DEFAULT_THEME_CONFIG)
    cta_slots = ensure_theme_cta_slots(theme)
    palette = theme.get("palette", {})
    iconography = theme.get("iconography", {})
    weight = str(iconography.get("weight", "regular")).lower()
    icon_weight_map = {
        "thin": "ph-thin",
        "light": "ph-light",
        "regular": "ph",
        "bold": "ph-bold",
        "fill": "ph-fill",
        "duotone": "ph-duotone",
    }
    icon_class = icon_weight_map.get(weight, "ph")

    return dict(
        site_title=settings.get("site_title", "Sports League Management System"),
        site_tagline=settings.get("league_tagline"),
        brand_image_url=settings.get("brand_image_url"),
        favicon_url=settings.get("favicon_url"),
        contact_email=settings.get("contact_email"),
        primary_color=palette.get("primary", DEFAULT_PRIMARY_COLOR),
        secondary_color=palette.get("secondary"),
        nav_layout=settings.get("nav_layout", "top"),
        navigation_links=settings.get("navigation_links", []),
        site_social_links=settings.get("social_links", {}),
        site_feature_flags=settings.get("feature_flags", {}),
        site_theme=theme,
        site_cta_slots=cta_slots,
        site_icon_class=icon_class,
        theme_preview_active=preview_active,
    )




def _get_site_settings_id(cur) -> Optional[int]:
    cur.execute('SELECT id FROM site_settings ORDER BY id ASC LIMIT 1')
    row = cur.fetchone()
    return row[0] if row else None


def _serialize_settings_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, separators=(',', ':'), ensure_ascii=False)


def get_site_theme_preview() -> Optional[Dict[str, Any]]:
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT id, payload, label, author_id, status, created_at
            FROM site_theme_versions
            WHERE status = 'preview'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        payload = json.loads(row[1]) if row[1] else {}
        created_at = row[5]
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None
        return {
            'id': row[0],
            'payload': payload,
            'label': row[2],
            'author_id': row[3],
            'status': row[4],
            'created_at': created_at,
        }
    finally:
        cur.close()


def list_site_theme_versions(limit: int = 20) -> List[Dict[str, Any]]:
    db = get_db()
    cur = db.cursor()
    results: List[Dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT v.id, v.status, v.label, v.author_id, v.payload, v.created_at, v.published_at,
                   u.first_name, u.last_name, u.email
            FROM site_theme_versions v
            LEFT JOIN "user" u ON v.author_id = u.id
            ORDER BY v.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

        for row in cur.fetchall():
            author_label = None
            if row[7] or row[8] or row[9]:
                names = [n for n in (row[7], row[8]) if n]
                if names:
                    author_label = ' '.join(names)
                elif row[9]:
                    author_label = row[9]
            created_at = row[5]
            published_at = row[6]
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = None
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at)
                except ValueError:
                    published_at = None
            results.append(
                {
                    'id': row[0],
                    'status': row[1],
                    'label': row[2],
                    'author_id': row[3],
                    'created_at': created_at,
                    'published_at': published_at,
                    'author_label': author_label,
                }
            )
    finally:
        cur.close()
    return results


def get_site_theme_version(version_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT id, status, payload, label, author_id FROM site_theme_versions WHERE id = %s",
            (version_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row[0],
            'status': row[1],
            'payload': json.loads(row[2]) if row[2] else {},
            'label': row[3],
            'author_id': row[4],
        }
    finally:
        cur.close()


def save_site_theme_preview(payload: Dict[str, Any], author_id: Optional[int] = None, label: Optional[str] = None) -> None:
    db = get_db()
    cur = db.cursor()
    try:
        site_id = _get_site_settings_id(cur)
        if site_id is None:
            return
        payload_json = _serialize_settings_payload(payload)
        label = label or f"Preview {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        cur.execute(
            "SELECT id FROM site_theme_versions WHERE site_settings_id = %s AND status = 'preview' ORDER BY created_at DESC LIMIT 1",
            (site_id,),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                """
                UPDATE site_theme_versions
                SET payload = %s, label = %s, author_id = %s, created_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (payload_json, label, author_id, row[0]),
            )
        else:
            cur.execute(
                """
                INSERT INTO site_theme_versions (site_settings_id, status, label, author_id, payload)
                VALUES (%s, 'preview', %s, %s, %s)
                """,
                (site_id, label, author_id, payload_json),
            )
        db.commit()
    finally:
        cur.close()
    invalidate_site_settings_cache()


def discard_site_theme_preview() -> None:
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM site_theme_versions WHERE status = 'preview'")
        db.commit()
    finally:
        cur.close()
    invalidate_site_settings_cache()


def _apply_payload_to_settings(settings: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(settings)
    simple_keys = [
        'site_title',
        'brand_image_url',
        'primary_color',
        'favicon_url',
        'league_tagline',
        'contact_email',
        'nav_layout',
        'custom_css',
    ]
    for key in simple_keys:
        if key in payload:
            merged[key] = payload[key]
    if 'social_links' in payload:
        merged['social_links'] = payload['social_links']
    if 'feature_flags' in payload:
        merged['feature_flags'] = payload['feature_flags']
    if 'theme' in payload:
        merged['theme'] = _merge_nested(DEFAULT_THEME_CONFIG, payload['theme'])
    theme_ref = merged.get('theme')
    if isinstance(theme_ref, dict):
        merged['cta_slots'] = ensure_theme_cta_slots(theme_ref)
    if 'navigation_links_raw' in payload:
        merged['navigation_links_raw'] = payload['navigation_links_raw']
        merged['navigation_links'] = _resolve_nav_links(payload['navigation_links_raw'])
    return merged


def _record_site_theme_version(status: str, payload: Dict[str, Any], author_id: Optional[int], label: Optional[str]) -> int:
    db = get_db()
    cur = db.cursor()
    try:
        site_id = _get_site_settings_id(cur)
        if site_id is None:
            return 0
        payload_json = _serialize_settings_payload(payload)
        label = label or f"{status.title()} {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        cur.execute(
            """
            INSERT INTO site_theme_versions (site_settings_id, status, label, author_id, payload, published_at)
            VALUES (%s, %s, %s, %s, %s, CASE WHEN %s = 'published' THEN CURRENT_TIMESTAMP ELSE NULL END)
            RETURNING id
            """,
            (site_id, status, label, author_id, payload_json, status),
        )
        version_id = cur.fetchone()[0]
        db.commit()
        return version_id
    finally:
        cur.close()


def publish_site_theme(payload: Dict[str, Any], author_id: Optional[int], label: Optional[str]) -> int:
    version_id = _record_site_theme_version('published', payload, author_id, label)
    discard_site_theme_preview()
    return version_id


def get_active_preview_payload() -> Optional[Dict[str, Any]]:
    preview = get_site_theme_preview()
    if not preview:
        return None
    return preview['payload']


def list_site_media_assets() -> List[Dict[str, Any]]:
    db = get_db()
    cur = db.cursor()
    items: List[Dict[str, Any]] = []
    try:
        cur.execute(
            """
            SELECT id, file_name, original_name, mime_type, file_size, url, alt_text, category, created_at
            FROM site_media
            ORDER BY created_at DESC
            """
        )
        for row in cur.fetchall():
            items.append(
                {
                    'id': row[0],
                    'file_name': row[1],
                    'original_name': row[2],
                    'mime_type': row[3],
                    'file_size': row[4],
                    'url': row[5],
                    'alt_text': row[6],
                    'category': row[7],
                    'created_at': row[8],
                }
            )
    finally:
        cur.close()
    return items


def add_site_media_record(record: Dict[str, Any]) -> None:
    db = get_db()
    cur = db.cursor()
    try:
        site_id = _get_site_settings_id(cur)
        if site_id is None:
            return
        cur.execute(
            """
            INSERT INTO site_media (site_settings_id, file_name, original_name, mime_type, file_size, url, alt_text, category, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                site_id,
                record['file_name'],
                record.get('original_name'),
                record.get('mime_type'),
                record.get('file_size'),
                record['url'],
                record.get('alt_text'),
                record.get('category'),
                record.get('uploaded_by'),
            ),
        )
        db.commit()
    finally:
        cur.close()


def delete_site_media_record(media_id: int) -> None:
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute('DELETE FROM site_media WHERE id = %s', (media_id,))
        db.commit()
    finally:
        cur.close()



def apply_site_payload(payload: Dict[str, Any]) -> None:
    """Persist a full site settings payload and refresh caches."""
    db = get_db()
    cur = db.cursor()
    try:
        site_id = _get_site_settings_id(cur)
        timestamp = datetime.now(timezone.utc)
        social_links = payload.get('social_links') or {}
        feature_flags = payload.get('feature_flags') or {}
        theme_payload = _merge_nested(DEFAULT_THEME_CONFIG, payload.get('theme', {}))
        ensure_theme_cta_slots(theme_payload)
        base_payload = (
            payload.get('site_title', 'Sports League Management System'),
            payload.get('brand_image_url'),
            payload.get('primary_color', DEFAULT_PRIMARY_COLOR),
            payload.get('favicon_url'),
            payload.get('league_tagline'),
            payload.get('contact_email'),
            json.dumps(social_links),
            json.dumps(feature_flags),
            json.dumps(theme_payload),
        )
        if site_id:
            cur.execute(
                """
                UPDATE site_settings
                SET site_title = %s,
                    brand_image_url = %s,
                    primary_color = %s,
                    favicon_url = %s,
                    league_tagline = %s,
                    contact_email = %s,
                    social_links_json = %s,
                    feature_flags_json = %s,
                    theme_config_json = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                base_payload + (timestamp, site_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO site_settings (
                    site_title,
                    brand_image_url,
                    primary_color,
                    favicon_url,
                    league_tagline,
                    contact_email,
                    social_links_json,
                    feature_flags_json,
                    theme_config_json,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                base_payload + (timestamp,),
            )
        db.commit()
    finally:
        cur.close()
    invalidate_site_settings_cache()

