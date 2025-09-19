"""Site settings service with navigation support."""

from __future__ import annotations

import json
from typing import Any, Dict, List

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


def _ensure_site_settings_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS site_settings (
            id SERIAL PRIMARY KEY,
            site_title TEXT DEFAULT 'Sports League Management System',
            brand_image_url TEXT,
            primary_color TEXT DEFAULT '#343a40',
            nav_layout TEXT DEFAULT 'top',
            navigation_json TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    existing_columns = set()
    try:
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
    if 'nav_layout' not in existing_columns:
        cur.execute("ALTER TABLE site_settings ADD COLUMN nav_layout TEXT DEFAULT 'top'")
    if 'navigation_json' not in existing_columns:
        cur.execute("ALTER TABLE site_settings ADD COLUMN navigation_json TEXT")


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

    try:
        db = get_db()
        cur = db.cursor()
        _ensure_site_settings_schema(cur)
        cur.execute(
            "SELECT id, site_title, brand_image_url, primary_color, nav_layout, navigation_json FROM site_settings ORDER BY id ASC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO site_settings (site_title, brand_image_url, primary_color, nav_layout, navigation_json) VALUES (%s, %s, %s, %s, %s) RETURNING id, site_title, brand_image_url, primary_color, nav_layout, navigation_json",
                (
                    "Sports League Management System",
                    None,
                    DEFAULT_PRIMARY_COLOR,
                    "top",
                    json.dumps(DEFAULT_NAV_LINKS),
                ),
            )
            row = cur.fetchone()
            db.commit()
        cur.close()

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

        settings = {
            "id": row[0],
            "site_title": row[1],
            "brand_image_url": row[2],
            "primary_color": row[3] or DEFAULT_PRIMARY_COLOR,
            "nav_layout": row[4] or "top",
            "navigation_links_raw": raw_links,
            "navigation_links": _resolve_nav_links(raw_links),
        }
        g._site_settings_cache = settings  # type: ignore[attr-defined]
        return settings
    except Exception:
        fallback_links = _default_nav_links()
        settings = {
            "site_title": "Sports League Management System",
            "brand_image_url": None,
            "primary_color": DEFAULT_PRIMARY_COLOR,
            "nav_layout": "top",
            "navigation_links_raw": fallback_links,
            "navigation_links": _resolve_nav_links(fallback_links),
        }
        g._site_settings_cache = settings  # type: ignore[attr-defined]
        return settings


def invalidate_site_settings_cache() -> None:
    if hasattr(g, "_site_settings_cache"):
        delattr(g, "_site_settings_cache")


def inject_site_settings():
    settings = _load_site_settings()
    return dict(
        site_title=settings.get("site_title", "Sports League Management System"),
        brand_image_url=settings.get("brand_image_url"),
        primary_color=settings.get("primary_color", DEFAULT_PRIMARY_COLOR),
        nav_layout=settings.get("nav_layout", "top"),
        navigation_links=settings.get("navigation_links", []),
    )
