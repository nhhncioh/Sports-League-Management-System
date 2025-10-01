"""Registration routes for public forms."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy.orm import joinedload

from slms.blueprints.common.tenant import org_query, tenant_required
from slms.extensions import db
from slms.forms.registration import TeamRegistrationForm, PlayerRegistrationForm
from slms.models import Registration, RegistrationMode, RegistrationStatus, Season, Waiver, PaymentStatus
from slms.services.queue import queue_service
from slms.services.uploads import save_upload


registration_bp = Blueprint('registration', __name__)


def get_active_waiver():
    """Get the active waiver for the organization."""
    return org_query(Waiver).filter(Waiver.is_active == True).first()


@registration_bp.route('/seasons/<season_id>/register/team', methods=['GET', 'POST'])
@tenant_required
def team_registration(season_id: str):
    """Team-based registration form."""
    season = (
        org_query(Season)
        .filter(Season.id == season_id)
        .options(joinedload(Season.league))
        .first_or_404()
    )

    # Check if registration is open and team-based
    if not season.registration_open:
        flash('Registration is not currently open for this season.', 'error')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    if season.registration_mode != RegistrationMode.TEAM_BASED:
        flash('This season uses individual player registration.', 'error')
        return redirect(url_for('registration.player_registration', season_id=season_id))

    # Get active waiver
    active_waiver = get_active_waiver()
    if not active_waiver:
        flash('No active waiver found. Please contact the administrator.', 'error')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    form = TeamRegistrationForm()

    if form.validate_on_submit():
        # Handle team logo upload
        team_logo_url = None
        if form.team_logo.data:
            team_logo_url = save_upload(form.team_logo.data, 'team_logos')

        # Create registration
        registration = Registration(
            org_id=season.org_id,
            season_id=season.id,
            waiver_id=active_waiver.id,
            # Contact information
            name=form.name.data,
            email=form.email.data.lower().strip(),
            phone=form.phone.data or None,
            # Team information
            team_name=form.team_name.data,
            team_size=form.team_size.data or None,
            team_logo_url=team_logo_url,
            skill_level=form.skill_level.data or None,
            # Division and preferences
            preferred_division=form.preferred_division.data or None,
            notes=form.notes.data or None,
            special_requirements=form.special_requirements.data or None,
            # Team colors
            primary_color=form.primary_color.data or None,
            secondary_color=form.secondary_color.data or None,
            accent_color=form.accent_color.data or None,
            # Emergency contact
            emergency_contact_name=form.emergency_contact_name.data or None,
            emergency_contact_phone=form.emergency_contact_phone.data or None,
            emergency_contact_relationship=form.emergency_contact_relationship.data or None,
            # Status and waiver
            status=RegistrationStatus.PENDING,
            waiver_signed=True,
            waiver_signed_at=datetime.utcnow(),
            payment_status=PaymentStatus.UNPAID
        )

        db.session.add(registration)
        db.session.commit()

        # Queue registration confirmation email
        try:
            queue_service.enqueue_registration_confirmation(
                registration_id=registration.id,
                to_email=registration.contact_email,
                to_name=registration.team_name
            )
        except Exception as e:
            print(f"Failed to queue registration confirmation email: {e}")

        flash('Registration submitted successfully! You will be contacted about payment details.', 'success')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    return render_template(
        'public/registration/team_form.html',
        form=form,
        season=season,
        waiver=active_waiver
    )


@registration_bp.route('/seasons/<season_id>/register/player', methods=['GET', 'POST'])
@tenant_required
def player_registration(season_id: str):
    """Individual player registration form."""
    season = (
        org_query(Season)
        .filter(Season.id == season_id)
        .options(joinedload(Season.league))
        .first_or_404()
    )

    # Check if registration is open and player-based
    if not season.registration_open:
        flash('Registration is not currently open for this season.', 'error')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    if season.registration_mode != RegistrationMode.PLAYER_BASED:
        flash('This season uses team-based registration.', 'error')
        return redirect(url_for('registration.team_registration', season_id=season_id))

    # Get active waiver
    active_waiver = get_active_waiver()
    if not active_waiver:
        flash('No active waiver found. Please contact the administrator.', 'error')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    form = PlayerRegistrationForm()

    if form.validate_on_submit():
        # Handle player photo upload
        player_photo_url = None
        if form.player_photo.data:
            player_photo_url = save_upload(form.player_photo.data, 'player_photos')

        # Create registration
        registration = Registration(
            org_id=season.org_id,
            season_id=season.id,
            waiver_id=active_waiver.id,
            # Personal information
            name=form.name.data,
            email=form.email.data.lower().strip(),
            phone=form.phone.data or None,
            date_of_birth=form.date_of_birth.data or None,
            gender=form.gender.data or None,
            player_photo_url=player_photo_url,
            # Player details
            skill_level=form.skill_level.data or None,
            jersey_size=form.jersey_size.data or None,
            jersey_number_preference=form.jersey_number_preference.data or None,
            # Preferences
            preferred_division=form.preferred_division.data or None,
            notes=form.notes.data or None,
            special_requirements=form.special_requirements.data or None,
            # Emergency contact
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            emergency_contact_relationship=form.emergency_contact_relationship.data or None,
            # Medical information
            medical_conditions=form.medical_conditions.data or None,
            allergies=form.allergies.data or None,
            # Status and waiver
            status=RegistrationStatus.PENDING,
            waiver_signed=True,
            waiver_signed_at=datetime.utcnow(),
            payment_status=PaymentStatus.UNPAID
        )

        db.session.add(registration)
        db.session.commit()

        # Queue registration confirmation email
        try:
            queue_service.enqueue_registration_confirmation(
                registration_id=registration.id,
                to_email=registration.contact_email,
                to_name=registration.name
            )
        except Exception as e:
            print(f"Failed to queue registration confirmation email: {e}")

        flash('Registration submitted successfully! You will be contacted about payment details.', 'success')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    return render_template(
        'public/registration/player_form.html',
        form=form,
        season=season,
        waiver=active_waiver
    )


@registration_bp.route('/seasons/<season_id>/register')
@tenant_required
def registration_info(season_id: str):
    """Registration information and redirect to appropriate form."""
    season = (
        org_query(Season)
        .filter(Season.id == season_id)
        .options(joinedload(Season.league))
        .first_or_404()
    )

    if not season.registration_open:
        flash('Registration is not currently open for this season.', 'info')
        return redirect(url_for('portal.season_standings', season_id=season_id))

    # Redirect to appropriate registration form based on mode
    if season.registration_mode == RegistrationMode.TEAM_BASED:
        return redirect(url_for('registration.team_registration', season_id=season_id))
    elif season.registration_mode == RegistrationMode.PLAYER_BASED:
        return redirect(url_for('registration.player_registration', season_id=season_id))
    else:
        flash('Registration mode not configured for this season.', 'error')
        return redirect(url_for('portal.season_standings', season_id=season_id))


__all__ = ['registration_bp']