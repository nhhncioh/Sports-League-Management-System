"""Authentication blueprint for SLMS."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired, Email

from slms.blueprints.common.tenant import org_query
from slms.models import User, UserRole, Organization
from slms.extensions import limiter


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")


auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        next_url = request.args.get("next")
        org_slug = session.get('org_slug')
        if next_url:
            return redirect(next_url)
        return redirect(url_for("public.home", org=org_slug) if org_slug else url_for("public.home"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        # 1) Try unique-by-email login across all orgs. If exactly one match, use it.
        matches = User.query.filter(User.email.ilike(email)).all()
        user = None
        if len(matches) == 1:
            user = matches[0]
            try:
                org = user.organization
                session['org_slug'] = org.slug  # stick user's org
            except Exception:
                org = None
        else:
            # 2) Resolve org for login if multiple or none found by email-only
            org = None
            org_slug = request.args.get('org') or session.get('org_slug')
            try:
                from flask import g
                org = getattr(g, 'org', None)
                if org is None and org_slug:
                    org = Organization.query.filter_by(slug=org_slug).first()
            except Exception:
                pass

            if org is None and org_slug:
                org = Organization.query.filter_by(slug=org_slug).first()

            if org is None:
                # Fallback to first/only org (dev convenience)
                org = Organization.query.order_by(Organization.created_at.asc()).first()
                if org is None:
                    flash("No organization configured. Create an organization first.", "error")
                    return render_template("login.html", form=form)

            try:
                session['org_slug'] = org.slug
            except Exception:
                pass

            user = (
                User.query.filter_by(org_id=org.id)
                .filter(User.email.ilike(email))
                .first()
            )
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Account is inactive. Contact your administrator.", "error")
            else:
                login_user(user, remember=form.remember_me.data)
                session["user_id"] = user.id
                session["user_role"] = (
                    user.role.value if isinstance(user.role, UserRole) else str(user.role)
                )
                session["is_admin"] = user.has_role(UserRole.OWNER, UserRole.ADMIN)
                next_url = request.args.get("next")
                # Always include org in the redirect to keep tenant context sticky across hosts
                target = next_url or url_for("public.home", org=session.get('org_slug'))
                return redirect(target)
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.landing"))


__all__ = ["auth_bp", "LoginForm"]
