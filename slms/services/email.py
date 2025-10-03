"""Email service for sending transactional emails."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from flask import current_app, url_for

if TYPE_CHECKING:
    from slms.models import User


def send_password_reset_email(user: User, token: str, org_slug: str | None = None) -> bool:
    """
    Send password reset email to user.

    Args:
        user: User model instance
        token: Password reset token
        org_slug: Organization slug for multi-tenant routing

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Generate reset URL
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        if org_slug:
            reset_url += f"?org={org_slug}"

        subject = "Password Reset Request"

        # HTML email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #007bff;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>You recently requested to reset your password for your Sports League Management account.</p>
                    <p>Click the button below to reset your password:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}"
                           style="background-color: #007bff; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 4px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #007bff;">{reset_url}</p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 0.9em;">
                        If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                    </p>
                    <p style="color: #666; font-size: 0.9em;">
                        This is an automated message, please do not reply.
                    </p>
                </div>
            </body>
        </html>
        """

        # Plain text version
        text_body = f"""
Password Reset Request

Hello,

You recently requested to reset your password for your Sports League Management account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email or contact support if you have concerns.

This is an automated message, please do not reply.
        """

        # Send email using configured email service
        return _send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        return False


def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Send email using configured email service.

    This is a placeholder that can be implemented with:
    - Flask-Mail (SMTP)
    - SendGrid
    - Amazon SES
    - Mailgun
    - etc.

    For development, it logs the email instead of sending.
    """
    # Check if email is configured
    email_enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'

    if not email_enabled:
        # Development mode - log email instead of sending
        current_app.logger.info(f"""
        ========== EMAIL (Development Mode) ==========
        To: {to_email}
        Subject: {subject}

        {text_body}
        ==============================================
        """)
        return True

    # Production mode - integrate with email service
    try:
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', 'noreply@example.com')

        if not all([smtp_host, smtp_user, smtp_password]):
            current_app.logger.warning("Email credentials not configured")
            return False

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        current_app.logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return False


def send_security_alert(user: User, event: str, details: str) -> bool:
    """
    Send security alert email to user.

    Args:
        user: User model instance
        event: Security event type (e.g., "Password Changed", "MFA Enabled")
        details: Additional details about the event

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = f"Security Alert: {event}"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #dc3545;">Security Alert</h2>
                    <p>Hello,</p>
                    <p>We detected a security-related change on your account:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0;">
                        <strong>{event}</strong><br>
                        {details}
                    </div>
                    <p>If you made this change, you can safely ignore this email.</p>
                    <p><strong>If you didn't make this change, please secure your account immediately:</strong></p>
                    <ol>
                        <li>Reset your password</li>
                        <li>Enable two-factor authentication</li>
                        <li>Contact support if you need assistance</li>
                    </ol>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 0.9em;">
                        This is an automated security notification.
                    </p>
                </div>
            </body>
        </html>
        """

        text_body = f"""
Security Alert: {event}

Hello,

We detected a security-related change on your account:

{event}
{details}

If you made this change, you can safely ignore this email.

If you didn't make this change, please secure your account immediately:
1. Reset your password
2. Enable two-factor authentication
3. Contact support if you need assistance

This is an automated security notification.
        """

        return _send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    except Exception as e:
        current_app.logger.error(f"Failed to send security alert email: {e}")
        return False


__all__ = ["send_password_reset_email", "send_security_alert"]
