"""Admin routes for managing registrations."""

from __future__ import annotations

from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from slms.blueprints.common.tenant import org_query
from slms.extensions import db
from slms.models import Registration, RegistrationStatus, PaymentStatus, Season, User, UserRole
from slms.services.queue import queue_service


def admin_required(f):
    """Decorator to ensure user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if current_user.role not in [UserRole.ADMIN, UserRole.OWNER]:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('portal.index'))
        # Store current_user in request for use in functions
        request.current_user = current_user
        return f(*args, **kwargs)
    return decorated_function


registration_admin_bp = Blueprint('registration_admin', __name__, url_prefix='/admin/registrations')


@registration_admin_bp.route('/')
@admin_required
def list_registrations():
    """List all registrations with filtering."""
    # Get filter parameters
    status_filter = request.args.get('status', '')
    season_id = request.args.get('season_id', '')
    payment_status_filter = request.args.get('payment_status', '')
    search = request.args.get('search', '')

    # Base query
    query = org_query(Registration).options(
        joinedload(Registration.season).joinedload(Season.league),
        joinedload(Registration.reviewed_by)
    )

    # Apply filters
    if status_filter:
        query = query.filter(Registration.status == RegistrationStatus[status_filter.upper()])

    if season_id:
        query = query.filter(Registration.season_id == season_id)

    if payment_status_filter:
        query = query.filter(Registration.payment_status == PaymentStatus[payment_status_filter.upper()])

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Registration.name.ilike(search_term),
                Registration.email.ilike(search_term),
                Registration.team_name.ilike(search_term)
            )
        )

    # Order by newest first
    registrations = query.order_by(Registration.created_at.desc()).all()

    # Get all seasons for filter dropdown
    seasons = org_query(Season).order_by(Season.created_at.desc()).all()

    # Get statistics
    stats = {
        'total': org_query(Registration).count(),
        'pending': org_query(Registration).filter(Registration.status == RegistrationStatus.PENDING).count(),
        'approved': org_query(Registration).filter(Registration.status == RegistrationStatus.APPROVED).count(),
        'rejected': org_query(Registration).filter(Registration.status == RegistrationStatus.REJECTED).count(),
        'unpaid': org_query(Registration).filter(Registration.payment_status == PaymentStatus.UNPAID).count(),
    }

    return render_template(
        'admin/registrations/list.html',
        registrations=registrations,
        seasons=seasons,
        stats=stats,
        status_filter=status_filter,
        season_id=season_id,
        payment_status_filter=payment_status_filter,
        search=search
    )


@registration_admin_bp.route('/<registration_id>')
@admin_required
def view_registration(registration_id: str):
    """View detailed registration information."""
    registration = org_query(Registration).options(
        joinedload(Registration.season).joinedload(Season.league),
        joinedload(Registration.waiver),
        joinedload(Registration.reviewed_by)
    ).filter(Registration.id == registration_id).first_or_404()

    return render_template(
        'admin/registrations/view.html',
        registration=registration
    )


@registration_admin_bp.route('/<registration_id>/approve', methods=['POST'])
@admin_required
def approve_registration(registration_id: str):
    """Approve a pending registration."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    if registration.status != RegistrationStatus.PENDING:
        flash('Only pending registrations can be approved.', 'error')
        return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))

    # Update status
    registration.status = RegistrationStatus.APPROVED
    registration.reviewed_by_user_id = request.current_user.id
    registration.reviewed_at = datetime.utcnow()

    # Get admin notes if provided
    admin_notes = request.form.get('admin_notes', '').strip()
    if admin_notes:
        registration.admin_notes = admin_notes

    db.session.commit()

    # Send approval email
    try:
        queue_service.enqueue_email(
            to_email=registration.email,
            to_name=registration.name,
            subject=f"Registration Approved - {registration.season.name}",
            html_content=f"""
                <p>Hi {registration.name},</p>
                <p>Great news! Your registration for <strong>{registration.season.name}</strong> has been approved.</p>
                {'<p><strong>Team:</strong> ' + registration.team_name + '</p>' if registration.team_name else ''}
                <p>Next steps:</p>
                <ul>
                    <li>Complete payment if not already done</li>
                    <li>Watch for schedule information</li>
                    <li>Check your email for updates</li>
                </ul>
                <p>We look forward to seeing you on the field!</p>
            """
        )
    except Exception as e:
        print(f"Failed to send approval email: {e}")

    flash('Registration approved successfully!', 'success')
    return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))


@registration_admin_bp.route('/<registration_id>/reject', methods=['POST'])
@admin_required
def reject_registration(registration_id: str):
    """Reject a pending registration."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    if registration.status != RegistrationStatus.PENDING:
        flash('Only pending registrations can be rejected.', 'error')
        return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))

    # Get rejection reason (required)
    rejection_reason = request.form.get('rejection_reason', '').strip()
    if not rejection_reason:
        flash('Rejection reason is required.', 'error')
        return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))

    # Update status
    registration.status = RegistrationStatus.REJECTED
    registration.reviewed_by_user_id = request.current_user.id
    registration.reviewed_at = datetime.utcnow()
    registration.rejection_reason = rejection_reason

    # Get admin notes if provided
    admin_notes = request.form.get('admin_notes', '').strip()
    if admin_notes:
        registration.admin_notes = admin_notes

    db.session.commit()

    # Send rejection email
    try:
        queue_service.enqueue_email(
            to_email=registration.email,
            to_name=registration.name,
            subject=f"Registration Update - {registration.season.name}",
            html_content=f"""
                <p>Hi {registration.name},</p>
                <p>Thank you for your interest in <strong>{registration.season.name}</strong>.</p>
                <p>Unfortunately, we are unable to approve your registration at this time.</p>
                <p><strong>Reason:</strong> {rejection_reason}</p>
                <p>If you have any questions, please don't hesitate to contact us.</p>
            """
        )
    except Exception as e:
        print(f"Failed to send rejection email: {e}")

    flash('Registration rejected.', 'info')
    return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))


@registration_admin_bp.route('/<registration_id>/waitlist', methods=['POST'])
@admin_required
def waitlist_registration(registration_id: str):
    """Move registration to waitlist."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    registration.status = RegistrationStatus.WAITLISTED
    registration.reviewed_by_user_id = request.current_user.id
    registration.reviewed_at = datetime.utcnow()

    admin_notes = request.form.get('admin_notes', '').strip()
    if admin_notes:
        registration.admin_notes = admin_notes

    db.session.commit()

    # Send waitlist email
    try:
        queue_service.enqueue_email(
            to_email=registration.email,
            to_name=registration.name,
            subject=f"Waitlist Status - {registration.season.name}",
            html_content=f"""
                <p>Hi {registration.name},</p>
                <p>Thank you for registering for <strong>{registration.season.name}</strong>.</p>
                <p>You have been placed on the waitlist. We will notify you if a spot becomes available.</p>
                <p>Thank you for your patience!</p>
            """
        )
    except Exception as e:
        print(f"Failed to send waitlist email: {e}")

    flash('Registration moved to waitlist.', 'info')
    return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))


@registration_admin_bp.route('/<registration_id>/mark-paid', methods=['POST'])
@admin_required
def mark_paid(registration_id: str):
    """Mark registration as paid."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    payment_method = request.form.get('payment_method', '').strip()
    payment_notes = request.form.get('payment_notes', '').strip()
    transaction_id = request.form.get('transaction_id', '').strip()

    registration.payment_status = PaymentStatus.PAID
    registration.paid_at = datetime.utcnow()
    registration.payment_method = payment_method or None
    registration.payment_transaction_id = transaction_id or None

    if payment_notes:
        if registration.payment_notes:
            registration.payment_notes += f"\n\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}: {payment_notes}"
        else:
            registration.payment_notes = payment_notes

    db.session.commit()

    # Send payment confirmation email
    try:
        queue_service.enqueue_email(
            to_email=registration.email,
            to_name=registration.name,
            subject=f"Payment Confirmed - {registration.season.name}",
            html_content=f"""
                <p>Hi {registration.name},</p>
                <p>We have received your payment for <strong>{registration.season.name}</strong>.</p>
                {'<p><strong>Transaction ID:</strong> ' + transaction_id + '</p>' if transaction_id else ''}
                <p>You're all set! We'll send you the schedule and additional information soon.</p>
                <p>See you on the field!</p>
            """
        )
    except Exception as e:
        print(f"Failed to send payment confirmation email: {e}")

    flash('Registration marked as paid.', 'success')
    return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))


@registration_admin_bp.route('/<registration_id>/add-note', methods=['POST'])
@admin_required
def add_note(registration_id: str):
    """Add an admin note to a registration."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    note = request.form.get('note', '').strip()
    if not note:
        flash('Note cannot be empty.', 'error')
        return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))

    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
    new_note = f"{timestamp} ({request.current_user.name}): {note}"

    if registration.admin_notes:
        registration.admin_notes += f"\n\n{new_note}"
    else:
        registration.admin_notes = new_note

    db.session.commit()

    flash('Note added successfully.', 'success')
    return redirect(url_for('registration_admin.view_registration', registration_id=registration_id))


@registration_admin_bp.route('/<registration_id>/delete', methods=['POST'])
@admin_required
def delete_registration(registration_id: str):
    """Delete a registration (use with caution)."""
    registration = org_query(Registration).filter(
        Registration.id == registration_id
    ).first_or_404()

    # Store season_id before deletion
    season_id = registration.season_id

    # Delete uploaded files if they exist
    from slms.services.uploads import delete_upload
    if registration.team_logo_url:
        delete_upload(registration.team_logo_url)
    if registration.player_photo_url:
        delete_upload(registration.player_photo_url)

    db.session.delete(registration)
    db.session.commit()

    flash('Registration deleted successfully.', 'success')
    return redirect(url_for('registration_admin.list_registrations'))


__all__ = ['registration_admin_bp']
