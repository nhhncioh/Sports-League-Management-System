"""Tenant resolution and multi-tenant helpers."""

from __future__ import annotations

from functools import wraps
from typing import Type, TypeVar

from flask import abort, current_app, g, has_request_context, request, session
from sqlalchemy.orm import Query

from slms.extensions import db
from slms.models import Organization

Model = TypeVar("Model", bound=db.Model)


def init_tenant(app) -> None:
    """Register tenant resolution hooks with the Flask app."""

    @app.before_request
    def _load_tenant() -> None:
        resolve_tenant()


def resolve_tenant() -> Organization | None:
    """Resolve the active organization from headers, subdomain, or fallbacks.

    Order:
    1) X-Org-Slug header
    2) Subdomain based on TENANT_BASE_DOMAIN (e.g., demo.localhost)
    3) Query param ?org=slug (handy for localhost/dev)
    4) DEFAULT_ORG_SLUG from config
    5) In debug mode: first Organization in DB
    """

    slug = _extract_request_slug()
    # Fallback: query parameter
    if not slug:
        slug = request.args.get("org")
    # Fallback: config default
    if not slug:
        slug = current_app.config.get("DEFAULT_ORG_SLUG")
    # Fallback: session sticky org
    if not slug:
        slug = session.get("org_slug")

    organization: Organization | None = None
    if slug:
        organization = Organization.query.filter_by(slug=slug).first()

    # Development convenience: if still not found, attempt safe fallbacks
    if organization is None:
        # If in debug OR only one org exists (common for local dev), pick it
        try:
            query = Organization.query.order_by(Organization.created_at.asc())
            first = query.first()
            second = query.offset(1).first()
            only_one = first is not None and second is None
        except Exception:
            first = None
            only_one = False

        if current_app.debug or only_one:
            if first:
                organization = first
                slug = first.slug

    # Persist org in session for subsequent requests (helps when not using subdomains)
    if organization is not None:
        try:
            session["org_slug"] = slug
        except Exception:
            pass

    g.org = organization
    g.org_slug = slug
    return organization


def tenant_required(view):
    """Ensure a tenant is loaded before executing the view."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "org", None) is None:
            abort(404)
        return view(*args, **kwargs)

    return wrapped


def org_query(model: Type[Model]) -> Query:
    """Return a query for the current tenant for the provided model."""

    org = getattr(g, "org", None)
    if org is None:
        raise RuntimeError("Tenant context has not been resolved")
    return model.query.filter_by(org_id=org.id)


def get_object_or_404(model: Type[Model], object_id: str) -> Model:
    """Fetch an object for the current tenant or raise a 404."""

    return org_query(model).filter_by(id=object_id).first_or_404()


def _extract_request_slug() -> str | None:
    """Determine the organization slug from the request."""

    header_slug = request.headers.get("X-Org-Slug")
    if header_slug:
        return header_slug.strip().lower()

    host = request.host.split(":", 1)[0].lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return None

    parts = host.split(".")
    if len(parts) < 2:
        return None

    base_domain = current_app.config.get("TENANT_BASE_DOMAIN")
    if base_domain and host.endswith(base_domain):
        candidate = host[: -len(base_domain)].rstrip(".")
        return candidate.split(".")[0] if candidate else None

    return parts[0]


@db.event.listens_for(db.session, "before_flush")
def _inject_org_id(session, flush_context, instances) -> None:
    """Automatically assign org_id and guard cross-tenant writes."""

    if not has_request_context():
        return

    org = getattr(g, "org", None)
    if org is None:
        return

    for obj in session.new:
        if hasattr(obj, "org_id"):
            current_value = getattr(obj, "org_id", None)
            if current_value is None:
                setattr(obj, "org_id", org.id)
            elif current_value != org.id:
                raise PermissionError("Cross-organization insert blocked")

    for obj in session.dirty:
        if hasattr(obj, "org_id"):
            current_value = getattr(obj, "org_id", None)
            if current_value is not None and current_value != org.id:
                raise PermissionError("Cross-organization update blocked")


__all__ = [
    "init_tenant",
    "resolve_tenant",
    "tenant_required",
    "org_query",
    "get_object_or_404",
]
