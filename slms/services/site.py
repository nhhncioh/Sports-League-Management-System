"""Site settings service with navigation support."""

from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Optional, Set

from flask import g, url_for

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
    theme = settings.get("theme", DEFAULT_THEME_CONFIG)
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
        site_icon_class=icon_class,
    )

