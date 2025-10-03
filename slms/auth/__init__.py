"""Authentication helpers shared across blueprints."""

from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, cast

from flask import flash, redirect, request, session, url_for, abort
from flask_login import current_user, login_required

from slms.models import UserRole

F = TypeVar('F', bound=Callable[..., object])


def login_required_with_message(func: F) -> F:
    """Decorator requiring authentication with custom flash message."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return func(*args, **kwargs)
    return cast(F, wrapper)


def admin_required(func: F) -> F:
    """Decorator to ensure the current user has admin/owner privileges."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.has_role(UserRole.OWNER, UserRole.ADMIN):
            flash('You need administrator privileges to access this page', 'error')
            return redirect(url_for('public.home', org=session.get('org_slug')))

        return func(*args, **kwargs)

    return cast(F, wrapper)


def role_required(*required_roles: UserRole | str):
    """Decorator factory to require specific roles."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            if not current_user.has_role(*required_roles):
                flash('You do not have permission to access this page', 'error')
                return redirect(url_for('public.home', org=session.get('org_slug')))

            return func(*args, **kwargs)
        return cast(F, wrapper)
    return decorator


def owner_required(func: F) -> F:
    """Decorator to ensure the current user is an owner."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.has_role(UserRole.OWNER):
            flash('Only organization owners can access this page', 'error')
            return redirect(url_for('public.home', org=session.get('org_slug')))

        return func(*args, **kwargs)

    return cast(F, wrapper)


def active_user_required(func: F) -> F:
    """Decorator to ensure the current user is active."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_active:
            flash('Your account is inactive. Please contact your administrator.', 'error')
            from flask_login import logout_user
            logout_user()
            session.clear()
            return redirect(url_for('auth.login'))

        return func(*args, **kwargs)

    return cast(F, wrapper)


__all__ = [
    'login_required_with_message',
    'admin_required',
    'role_required',
    'owner_required',
    'active_user_required'
]
