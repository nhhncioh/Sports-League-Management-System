"""Security package for SLMS."""

from __future__ import annotations

from functools import wraps
from typing import Iterable

from flask import abort, current_app, g, redirect, request, url_for, session
from flask_login import current_user

from slms.models import UserRole


def _normalize_roles(roles: Iterable[UserRole | str]) -> set[str]:
    normalized: set[str] = set()
    for role in roles:
        if isinstance(role, UserRole):
            normalized.add(role.value)
        else:
            normalized.add(str(role))
    return normalized


def roles_required(*roles: UserRole | str):
    """Ensure the current user belongs to the tenant and has one of the roles."""

    required = _normalize_roles(roles)

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            org = getattr(g, "org", None)
            if org is None:
                abort(404)

            if not current_user.is_authenticated:
                login_view = current_app.login_manager.login_view or 'auth.login'
                return redirect(url_for(login_view, next=request.url))

            if getattr(current_user, "org_id", None) != org.id:
                # Developer-friendly fallback: align tenant to the user's organization when allowed
                allow_fallback = current_app.config.get('ALLOW_ORG_FALLBACK', current_app.debug)
                if allow_fallback and getattr(current_user, 'organization', None):
                    try:
                        g.org = current_user.organization
                        session['org_slug'] = getattr(current_user.organization, 'slug', None)
                    except Exception:
                        abort(403)
                else:
                    abort(403)

            user_role = (
                current_user.role.value
                if isinstance(current_user.role, UserRole)
                else str(current_user.role)
            )
            if required and user_role not in required:
                abort(403)

            return view_func(*args, **kwargs)

        return wrapped

    return decorator


__all__ = ["roles_required"]
