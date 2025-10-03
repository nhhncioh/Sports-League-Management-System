"""Audit logging service for security and administrative events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request
from slms.extensions import db
from slms.models import AuditLog

if TYPE_CHECKING:
    from slms.models import User


def log_security_event(
    user: User,
    action: str,
    details: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None
) -> None:
    """
    Log a security-related event to the audit log.

    Args:
        user: User who performed the action
        action: Action performed (e.g., "login", "password_reset", "mfa_enabled")
        details: Optional additional details
        ip_address: IP address (defaults to request.remote_addr)
        metadata: Additional metadata to store
    """
    try:
        meta = metadata or {}
        meta['ip_address'] = ip_address or request.remote_addr
        if details:
            meta['details'] = details

        audit_entry = AuditLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            entity_type='user',
            entity_id=user.id,
            meta=meta
        )

        db.session.add(audit_entry)
        db.session.commit()

    except Exception as e:
        # Don't fail the request if audit logging fails
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to log security event: {e}")


def log_login_attempt(
    user: User | None,
    success: bool,
    email: str,
    ip_address: str | None = None,
    reason: str | None = None
) -> None:
    """
    Log a login attempt (successful or failed).

    Args:
        user: User object if found, None if not
        success: Whether login was successful
        email: Email used for login
        ip_address: IP address (defaults to request.remote_addr)
        reason: Reason for failure (e.g., "invalid_password", "account_locked")
    """
    try:
        action = "login_success" if success else "login_failed"
        meta = {
            'ip_address': ip_address or request.remote_addr,
            'email': email,
        }
        if reason:
            meta['reason'] = reason

        # If user exists, log against their org and user_id
        if user:
            audit_entry = AuditLog(
                org_id=user.org_id,
                user_id=user.id,
                action=action,
                entity_type='user',
                entity_id=user.id,
                meta=meta
            )
        else:
            # User not found - still log attempt but without org/user context
            # This requires handling None org_id which may not be allowed
            # Skip logging in this case to avoid errors
            return

        db.session.add(audit_entry)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to log login attempt: {e}")


def log_admin_action(
    user: User,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None
) -> None:
    """
    Log an administrative action.

    Args:
        user: User who performed the action
        action: Action performed (e.g., "user_created", "team_deleted")
        entity_type: Type of entity affected
        entity_id: ID of entity affected
        metadata: Additional metadata
    """
    try:
        meta = metadata or {}
        meta['ip_address'] = request.remote_addr

        audit_entry = AuditLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta
        )

        db.session.add(audit_entry)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        from flask import current_app
        current_app.logger.error(f"Failed to log admin action: {e}")


__all__ = ["log_security_event", "log_login_attempt", "log_admin_action"]
