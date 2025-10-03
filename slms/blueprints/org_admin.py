"""Organization administration blueprint."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional

from slms.auth import owner_required
from slms.extensions import limiter, db
from slms.models import Organization
from slms.services.organization import (
    create_organization,
    update_organization,
    get_organization_stats,
    validate_slug,
    slugify
)
from slms.security.config import is_password_strong


class OrganizationSignupForm(FlaskForm):
    """Form for creating a new organization."""
    org_name = StringField(
        "Organization Name",
        validators=[DataRequired(), Length(min=3, max=255)],
        render_kw={"placeholder": "Acme Sports League"}
    )
    org_slug = StringField(
        "URL Slug",
        validators=[Length(min=3, max=63)],
        render_kw={"placeholder": "acme-sports (leave blank to auto-generate)"}
    )
    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={"placeholder": "A brief description of your organization", "rows": 3}
    )

    # Owner account
    owner_email = StringField(
        "Your Email",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "admin@example.com"}
    )
    owner_password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8)],
        render_kw={"placeholder": "At least 8 characters"}
    )
    owner_password_confirm = PasswordField(
        "Confirm Password",
        validators=[DataRequired()],
        render_kw={"placeholder": "Re-enter password"}
    )

    # Optional contact info
    contact_email = StringField(
        "Organization Contact Email",
        validators=[Optional(), Email()],
        render_kw={"placeholder": "contact@example.com"}
    )
    contact_phone = StringField(
        "Phone Number",
        validators=[Optional(), Length(max=32)],
        render_kw={"placeholder": "+1 (555) 123-4567"}
    )
    website_url = StringField(
        "Website URL",
        validators=[Optional(), Length(max=512)],
        render_kw={"placeholder": "https://example.com"}
    )

    terms_accepted = BooleanField(
        "I accept the Terms of Service and Privacy Policy",
        validators=[DataRequired()]
    )


class OrganizationSettingsForm(FlaskForm):
    """Form for updating organization settings."""
    name = StringField("Organization Name", validators=[DataRequired(), Length(min=3, max=255)])
    slug = StringField("URL Slug", validators=[DataRequired(), Length(min=3, max=63)])
    description = TextAreaField("Description", validators=[Optional()])
    contact_email = StringField("Contact Email", validators=[Optional(), Email()])
    contact_phone = StringField("Phone Number", validators=[Optional(), Length(max=32)])
    website_url = StringField("Website URL", validators=[Optional(), Length(max=512)])


org_admin_bp = Blueprint("org_admin", __name__)


@org_admin_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def signup():
    """Self-service organization creation."""
    if current_user.is_authenticated:
        flash("You are already logged in. Log out first to create a new organization.", "info")
        return redirect(url_for("public.home", org=session.get('org_slug')))

    form = OrganizationSignupForm()

    if form.validate_on_submit():
        # Validate passwords match
        if form.owner_password.data != form.owner_password_confirm.data:
            flash("Passwords do not match.", "error")
            return render_template("org_signup.html", form=form)

        # Validate password strength
        is_strong, message = is_password_strong(form.owner_password.data)
        if not is_strong:
            flash(message, "error")
            return render_template("org_signup.html", form=form)

        # Get or generate slug
        slug = form.org_slug.data.strip() if form.org_slug.data else slugify(form.org_name.data)

        # Validate slug
        is_valid, error = validate_slug(slug)
        if not is_valid:
            flash(error, "error")
            return render_template("org_signup.html", form=form)

        # Create organization
        org, error = create_organization(
            name=form.org_name.data.strip(),
            slug=slug,
            owner_email=form.owner_email.data.strip().lower(),
            owner_password=form.owner_password.data,
            description=form.description.data.strip() if form.description.data else None,
            contact_email=form.contact_email.data.strip() if form.contact_email.data else None,
            contact_phone=form.contact_phone.data.strip() if form.contact_phone.data else None,
            website_url=form.website_url.data.strip() if form.website_url.data else None,
        )

        if error:
            flash(error, "error")
            return render_template("org_signup.html", form=form)

        # Log the owner in
        owner = org.users[0]  # First user is the owner
        login_user(owner)
        session["user_id"] = owner.id
        session["user_role"] = owner.role.value
        session["is_admin"] = True
        session["org_slug"] = org.slug

        # Log organization creation
        from slms.services.audit import log_security_event
        log_security_event(owner, "organization_created", f"Organization '{org.name}' created")

        flash(f"Welcome! Your organization '{org.name}' has been created successfully.", "success")
        return redirect(url_for("public.home", org=org.slug))

    return render_template("org_signup.html", form=form)


@org_admin_bp.route("/settings", methods=["GET", "POST"])
@owner_required
def settings():
    """Organization settings management."""
    from flask import g

    org = g.org
    if not org:
        flash("Organization not found.", "error")
        return redirect(url_for("public.landing"))

    form = OrganizationSettingsForm(obj=org)

    if form.validate_on_submit():
        # Build update dict
        updates = {
            'name': form.name.data.strip(),
            'slug': form.slug.data.strip().lower(),
            'description': form.description.data.strip() if form.description.data else None,
            'contact_email': form.contact_email.data.strip() if form.contact_email.data else None,
            'contact_phone': form.contact_phone.data.strip() if form.contact_phone.data else None,
            'website_url': form.website_url.data.strip() if form.website_url.data else None,
        }

        success, error = update_organization(org, **updates)

        if error:
            flash(error, "error")
        else:
            # Update session if slug changed
            if updates['slug'] != org.slug:
                session['org_slug'] = updates['slug']

            # Log the change
            from slms.services.audit import log_admin_action
            log_admin_action(current_user, "organization_updated", "organization", org.id)

            flash("Organization settings updated successfully.", "success")
            return redirect(url_for("org_admin.settings", org=updates['slug']))

    # Get organization stats
    stats = get_organization_stats(org)

    return render_template("org_settings.html", form=form, org=org, stats=stats)


__all__ = ["org_admin_bp"]
