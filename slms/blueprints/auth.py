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


class PasswordResetRequestForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


class PasswordResetForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    password_confirm = PasswordField("Confirm Password", validators=[DataRequired()])


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
        if user:
            # Check if account is locked
            if user.is_account_locked():
                from slms.extensions import db
                db.session.commit()  # Save unlock if lock expired
                flash("Account is locked due to too many failed login attempts. Try again later.", "error")
                return render_template("login.html", form=form)

            if not user.is_active:
                flash("Account is inactive. Contact your administrator.", "error")
                return render_template("login.html", form=form)

            if user.check_password(form.password.data):
                # Password correct - check if MFA is enabled
                if user.two_factor_enabled:
                    # Store user ID in session and redirect to MFA verification
                    session['mfa_pending_user_id'] = user.id
                    session['mfa_remember_me'] = form.remember_me.data
                    session['mfa_next_url'] = request.args.get("next")
                    return redirect(url_for('auth.mfa_verify'))

                # No MFA - complete login
                from datetime import datetime, timezone
                user.reset_failed_login_attempts()
                user.last_login_at = datetime.now(timezone.utc)
                user.last_login_ip = request.remote_addr

                from slms.extensions import db
                db.session.commit()

                # Log successful login
                from slms.services.audit import log_security_event
                log_security_event(user, "login_success", "User logged in successfully")

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
                # Password incorrect - record failed attempt
                user.record_failed_login()
                from slms.extensions import db
                db.session.commit()

                # Log failed login
                from slms.services.audit import log_security_event
                log_security_event(user, "login_failed", "Invalid password")

                flash("Invalid email or password", "error")
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


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def forgot_password():
    """Request a password reset."""
    if current_user.is_authenticated:
        return redirect(url_for("public.home", org=session.get('org_slug')))

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        # Find user - don't reveal if email exists or not
        org = None
        org_slug = request.args.get('org') or session.get('org_slug')
        if org_slug:
            org = Organization.query.filter_by(slug=org_slug).first()

        if org:
            user = User.query.filter_by(org_id=org.id).filter(User.email.ilike(email)).first()
        else:
            # Try to find user across all orgs if exactly one match
            matches = User.query.filter(User.email.ilike(email)).all()
            user = matches[0] if len(matches) == 1 else None

        if user and user.is_active:
            # Generate reset token
            import secrets
            from datetime import datetime, timezone, timedelta
            from slms.extensions import db

            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            db.session.commit()

            # Send password reset email
            from slms.services.email import send_password_reset_email
            org_slug = org.slug if org else None
            send_password_reset_email(user, token, org_slug)

        # Always show same message to prevent email enumeration
        flash("If an account exists with that email, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for("public.home", org=session.get('org_slug')))

    user = User.query.filter_by(password_reset_token=token).first()

    if not user or not user.password_reset_expires:
        flash("Invalid or expired password reset link.", "error")
        return redirect(url_for("auth.login"))

    from datetime import datetime, timezone
    if datetime.now(timezone.utc) > user.password_reset_expires:
        flash("Password reset link has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = PasswordResetForm()
    if form.validate_on_submit():
        if form.password.data != form.password_confirm.data:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html", form=form, token=token)

        # Validate password strength
        from slms.security.config import is_password_strong
        is_strong, message = is_password_strong(form.password.data)
        if not is_strong:
            flash(message, "error")
            return render_template("reset_password.html", form=form, token=token)

        # Reset password
        from slms.extensions import db
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.reset_failed_login_attempts()  # Unlock account if locked
        db.session.commit()

        # Log password reset
        from slms.services.audit import log_security_event
        log_security_event(user, "password_reset", "Password reset via email link")

        # Send security alert
        from slms.services.email import send_security_alert
        send_security_alert(user, "Password Changed", f"Your password was reset from IP: {request.remote_addr}")

        flash("Your password has been reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login", org=session.get('org_slug')))

    return render_template("reset_password.html", form=form, token=token)


@auth_bp.route("/mfa/setup", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def mfa_setup():
    """Setup MFA for current user."""
    from flask_login import login_required
    from slms.auth import login_required_with_message

    if not current_user.is_authenticated:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    from slms.extensions import db

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        if not token:
            flash("Please enter the verification code.", "error")
            return redirect(url_for("auth.mfa_setup"))

        if current_user.verify_mfa_token(token):
            # MFA verified - enable it and generate recovery codes
            current_user.two_factor_enabled = True
            recovery_codes = current_user.generate_recovery_codes()
            db.session.commit()

            # Log MFA enablement
            from slms.services.audit import log_security_event
            log_security_event(current_user, "mfa_enabled", "Two-factor authentication enabled")

            # Send security alert
            from slms.services.email import send_security_alert
            send_security_alert(current_user, "Two-Factor Authentication Enabled",
                              f"2FA was enabled on your account from IP: {request.remote_addr}")

            # Show recovery codes to user (they should save these)
            return render_template("mfa_recovery_codes.html", recovery_codes=recovery_codes)
        else:
            flash("Invalid verification code. Please try again.", "error")
            return redirect(url_for("auth.mfa_setup"))

    # Generate new secret if not already set
    if not current_user.mfa_secret:
        current_user.generate_mfa_secret()
        db.session.commit()

    # Generate QR code
    from slms.services.mfa import generate_qr_code
    org_name = current_user.organization.name if current_user.organization else None
    qr_code = generate_qr_code(current_user, org_name)

    # Convert to base64 for embedding in HTML
    import base64
    qr_code_b64 = base64.b64encode(qr_code).decode('utf-8')

    return render_template("mfa_setup.html", qr_code=qr_code_b64, secret=current_user.mfa_secret)


@auth_bp.route("/mfa/disable", methods=["POST"])
@limiter.limit("5 per hour")
def mfa_disable():
    """Disable MFA for current user."""
    if not current_user.is_authenticated:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    password = request.form.get("password", "")
    if not password or not current_user.check_password(password):
        flash("Invalid password. MFA was not disabled.", "error")
        return redirect(url_for("public.home", org=session.get('org_slug')))

    from slms.extensions import db
    current_user.two_factor_enabled = False
    current_user.mfa_secret = None
    current_user.mfa_recovery_codes = None
    db.session.commit()

    # Log MFA disable
    from slms.services.audit import log_security_event
    log_security_event(current_user, "mfa_disabled", "Two-factor authentication disabled")

    # Send security alert
    from slms.services.email import send_security_alert
    send_security_alert(current_user, "Two-Factor Authentication Disabled",
                       f"2FA was disabled on your account from IP: {request.remote_addr}")

    flash("Two-factor authentication has been disabled.", "success")
    return redirect(url_for("public.home", org=session.get('org_slug')))


@auth_bp.route("/mfa/verify", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def mfa_verify():
    """Verify MFA token during login."""
    # Check if user is in MFA verification state
    pending_user_id = session.get('mfa_pending_user_id')
    if not pending_user_id:
        flash("No MFA verification pending.", "error")
        return redirect(url_for("auth.login"))

    user = User.query.get(pending_user_id)
    if not user or not user.two_factor_enabled:
        session.pop('mfa_pending_user_id', None)
        flash("Invalid MFA state.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        token = request.form.get("token", "").strip()
        use_recovery = request.form.get("use_recovery") == "1"

        verified = False
        if use_recovery:
            # Verify recovery code
            verified = user.verify_recovery_code(token)
            if verified:
                flash("Recovery code accepted. Please set up MFA again.", "warning")
        else:
            # Verify TOTP token
            verified = user.verify_mfa_token(token)

        if verified:
            from datetime import datetime, timezone
            from slms.extensions import db

            user.reset_failed_login_attempts()
            user.last_login_at = datetime.now(timezone.utc)
            user.last_login_ip = request.remote_addr
            db.session.commit()

            # Log successful MFA verification
            from slms.services.audit import log_security_event
            event_type = "mfa_verified_recovery" if use_recovery else "mfa_verified"
            log_security_event(user, event_type, "MFA verification successful")

            # Complete login
            login_user(user, remember=session.get('mfa_remember_me', False))
            session["user_id"] = user.id
            session["user_role"] = user.role.value if isinstance(user.role, UserRole) else str(user.role)
            session["is_admin"] = user.has_role(UserRole.OWNER, UserRole.ADMIN)

            # Clear MFA session data
            session.pop('mfa_pending_user_id', None)
            session.pop('mfa_remember_me', None)
            next_url = session.pop('mfa_next_url', None)

            target = next_url or url_for("public.home", org=session.get('org_slug'))
            flash("Login successful!", "success")
            return redirect(target)
        else:
            user.record_failed_login()
            from slms.extensions import db
            db.session.commit()
            flash("Invalid verification code.", "error")

    return render_template("mfa_verify.html")


__all__ = ["auth_bp", "LoginForm", "PasswordResetRequestForm", "PasswordResetForm"]
