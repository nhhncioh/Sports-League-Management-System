"""Email service with SMTP and template support."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional
from datetime import datetime

from flask import current_app, render_template, g
from jinja2 import Template

from slms.extensions import db
from slms.models import EmailMessage, EmailStatus, EmailType
from slms.blueprints.common.tenant import get_current_org


class EmailerError(Exception):
    """Raised when email operations fail."""
    pass


class EmailService:
    """Service for sending emails via SMTP with template support."""

    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'Sports League Management')

        if not all([self.smtp_host, self.smtp_username, self.smtp_password]):
            raise EmailerError("SMTP configuration incomplete. Check environment variables.")

    def send_email(
        self,
        to_email: str,
        subject: str,
        template_key: str,
        context: Dict = None,
        to_name: str = None,
        email_type: EmailType = EmailType.CUSTOM,
        user_id: str = None,
        game_id: str = None,
        registration_id: str = None
    ) -> EmailMessage:
        """
        Send an email using a template.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_key: Template filename without extension (e.g., 'registration_confirmation')
            context: Template context variables
            to_name: Recipient name (optional)
            email_type: Type of email for categorization
            user_id: Related user ID (optional)
            game_id: Related game ID (optional)
            registration_id: Related registration ID (optional)

        Returns:
            EmailMessage: The created email record
        """
        context = context or {}
        org = get_current_org()

        # Create email record
        email_message = EmailMessage(
            org_id=org.id,
            to_email=to_email,
            to_name=to_name,
            from_email=self.from_email,
            from_name=self.from_name,
            subject=subject,
            template_key=template_key,
            email_type=email_type,
            status=EmailStatus.QUEUED,
            context=context,
            user_id=user_id,
            game_id=game_id,
            registration_id=registration_id
        )

        try:
            # Render template
            html_content = self._render_template(template_key, context)
            email_message.html_content = html_content
            email_message.status = EmailStatus.SENDING

            db.session.add(email_message)
            db.session.commit()

            # Send email
            self._send_smtp_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_content=html_content
            )

            # Mark as sent
            email_message.status = EmailStatus.SENT
            email_message.sent_at = datetime.utcnow()
            db.session.commit()

            return email_message

        except Exception as e:
            # Mark as failed
            email_message.status = EmailStatus.FAILED
            email_message.error_message = str(e)
            db.session.commit()
            raise EmailerError(f"Failed to send email: {str(e)}")

    def _render_template(self, template_key: str, context: Dict) -> str:
        """Render email template with context."""
        try:
            # Add common context variables
            org = get_current_org()
            context.update({
                'organization': org,
                'org_name': org.name if org else 'Sports League Management',
                'base_url': current_app.config.get('BASE_URL', 'http://localhost:5000')
            })

            # Try to render from templates/email/ directory
            template_path = f'email/{template_key}.html'
            return render_template(template_path, **context)

        except Exception as e:
            # Fallback to simple template
            return self._render_fallback_template(template_key, context)

    def _render_fallback_template(self, template_key: str, context: Dict) -> str:
        """Render a basic fallback template."""
        fallback_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ subject }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #007bff; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f8f9fa; }
                .footer { padding: 10px; text-align: center; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ org_name }}</h1>
                </div>
                <div class="content">
                    <h2>{{ template_key.replace('_', ' ').title() }}</h2>
                    <p>This is an automated message from {{ org_name }}.</p>
                    {% for key, value in context.items() %}
                        {% if key not in ['organization', 'org_name', 'base_url'] %}
                            <p><strong>{{ key.replace('_', ' ').title() }}:</strong> {{ value }}</p>
                        {% endif %}
                    {% endfor %}
                </div>
                <div class="footer">
                    <p>© {{ org_name }}. This is an automated email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        template = Template(fallback_template)
        return template.render(**context)

    def _send_smtp_email(self, to_email: str, subject: str, html_content: str, to_name: str = None):
        """Send email via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send email
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

        except Exception as e:
            raise EmailerError(f"SMTP error: {str(e)}")

    def retry_failed_email(self, email_id: str) -> EmailMessage:
        """Retry sending a failed email."""
        email_message = db.session.get(EmailMessage, email_id)

        if not email_message:
            raise EmailerError("Email message not found")

        if email_message.retry_count >= email_message.max_retries:
            raise EmailerError("Maximum retries exceeded")

        try:
            email_message.retry_count += 1
            email_message.status = EmailStatus.SENDING
            email_message.error_message = None

            # Send email using existing content
            self._send_smtp_email(
                to_email=email_message.to_email,
                to_name=email_message.to_name,
                subject=email_message.subject,
                html_content=email_message.html_content
            )

            # Mark as sent
            email_message.status = EmailStatus.SENT
            email_message.sent_at = datetime.utcnow()
            db.session.commit()

            return email_message

        except Exception as e:
            email_message.status = EmailStatus.FAILED
            email_message.error_message = str(e)
            db.session.commit()
            raise EmailerError(f"Retry failed: {str(e)}")


# Global email service instance
email_service = EmailService()


def send_email(
    to_email: str,
    subject: str,
    template_key: str,
    context: Dict = None,
    **kwargs
) -> EmailMessage:
    """
    Convenience function to send emails.

    This function can be used directly or queued as a background job.
    """
    return email_service.send_email(
        to_email=to_email,
        subject=subject,
        template_key=template_key,
        context=context,
        **kwargs
    )


def send_registration_confirmation(registration_id: str, to_email: str, to_name: str = None):
    """Send registration confirmation email."""
    from slms.models import Registration

    registration = db.session.get(Registration, registration_id)
    if not registration:
        raise EmailerError("Registration not found")

    context = {
        'registration': registration,
        'season': registration.season,
        'league': registration.season.league if registration.season else None,
        'player_name': to_name or registration.player_name,
        'team_name': registration.team_name
    }

    return send_email(
        to_email=to_email,
        subject=f"Registration Confirmed - {registration.season.name if registration.season else 'League'}",
        template_key='registration_confirmation',
        context=context,
        to_name=to_name,
        email_type=EmailType.REGISTRATION_CONFIRMATION,
        registration_id=registration_id
    )


def send_game_reminder(game_id: str, to_email: str, to_name: str = None):
    """Send game reminder email (24h before game)."""
    from slms.models import Game

    game = db.session.get(Game, game_id)
    if not game:
        raise EmailerError("Game not found")

    context = {
        'game': game,
        'home_team': game.home_team,
        'away_team': game.away_team,
        'venue': game.venue,
        'season': game.season
    }

    return send_email(
        to_email=to_email,
        subject=f"Game Reminder - {game.home_team.name} vs {game.away_team.name}",
        template_key='game_reminder',
        context=context,
        to_name=to_name,
        email_type=EmailType.GAME_REMINDER,
        game_id=game_id
    )


def send_game_recap(game_id: str, to_email: str, to_name: str = None):
    """Send post-game recap email."""
    from slms.models import Game

    game = db.session.get(Game, game_id)
    if not game:
        raise EmailerError("Game not found")

    context = {
        'game': game,
        'home_team': game.home_team,
        'away_team': game.away_team,
        'venue': game.venue,
        'season': game.season,
        'final_score': f"{game.home_score}-{game.away_score}",
        'winner': game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team
    }

    return send_email(
        to_email=to_email,
        subject=f"Game Recap - {game.home_team.name} {game.home_score} - {game.away_score} {game.away_team.name}",
        template_key='game_recap',
        context=context,
        to_name=to_name,
        email_type=EmailType.GAME_RECAP,
        game_id=game_id
    )


__all__ = [
    'EmailService',
    'EmailerError',
    'email_service',
    'send_email',
    'send_registration_confirmation',
    'send_game_reminder',
    'send_game_recap'
]