"""Webhook and automation service for external integrations."""
from __future__ import annotations

import hmac
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from enum import Enum

import requests
from flask import current_app
from sqlalchemy import select, and_

from slms.extensions import db
from slms.models.models import TimestampedBase


class WebhookEventType(Enum):
    """Types of webhook events."""
    # Game events
    GAME_CREATED = "game.created"
    GAME_UPDATED = "game.updated"
    GAME_STARTED = "game.started"
    GAME_ENDED = "game.ended"
    SCORE_UPDATED = "score.updated"

    # Team events
    TEAM_CREATED = "team.created"
    TEAM_UPDATED = "team.updated"
    TEAM_DELETED = "team.deleted"

    # Player events
    PLAYER_CREATED = "player.created"
    PLAYER_UPDATED = "player.updated"
    PLAYER_DELETED = "player.deleted"

    # Registration events
    REGISTRATION_CREATED = "registration.created"
    REGISTRATION_APPROVED = "registration.approved"
    REGISTRATION_REJECTED = "registration.rejected"

    # Content events
    ARTICLE_PUBLISHED = "article.published"
    ARTICLE_UNPUBLISHED = "article.unpublished"


class WebhookStatus(Enum):
    """Status of webhook deliveries."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


class Webhook(TimestampedBase):
    """Webhook subscription model."""
    __tablename__ = "webhook"

    org_id: str = db.Column(db.String(36), db.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False, index=True)
    name: str = db.Column(db.String(255), nullable=False)
    url: str = db.Column(db.String(1000), nullable=False)
    secret: str = db.Column(db.String(255), nullable=False)

    # Event filters (JSONB array of event types)
    events: list[str] = db.Column(db.JSON, nullable=False)

    # Settings
    is_active: bool = db.Column(db.Boolean, nullable=False, default=True)
    retry_count: int = db.Column(db.Integer, nullable=False, default=3)
    timeout: int = db.Column(db.Integer, nullable=False, default=30)  # seconds

    # Headers to send with webhook (JSONB)
    custom_headers: dict = db.Column(db.JSON, nullable=True)

    # Statistics
    success_count: int = db.Column(db.Integer, nullable=False, default=0)
    failure_count: int = db.Column(db.Integer, nullable=False, default=0)
    last_triggered_at: datetime | None = db.Column(db.DateTime(timezone=True), nullable=True)
    last_success_at: datetime | None = db.Column(db.DateTime(timezone=True), nullable=True)
    last_failure_at: datetime | None = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    organization = db.relationship('Organization', backref='webhooks')


class WebhookDelivery(TimestampedBase):
    """Record of webhook delivery attempts."""
    __tablename__ = "webhook_delivery"

    webhook_id: str = db.Column(db.String(36), db.ForeignKey('webhook.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type: str = db.Column(db.String(100), nullable=False)
    payload: dict = db.Column(db.JSON, nullable=False)

    # Delivery status
    status: WebhookStatus = db.Column(db.Enum(WebhookStatus), nullable=False, default=WebhookStatus.PENDING)
    attempts: int = db.Column(db.Integer, nullable=False, default=0)

    # Response details
    response_status: int | None = db.Column(db.Integer, nullable=True)
    response_body: str | None = db.Column(db.Text, nullable=True)
    error_message: str | None = db.Column(db.Text, nullable=True)

    # Timing
    next_retry_at: datetime | None = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at: datetime | None = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    webhook = db.relationship('Webhook', backref='deliveries')

    __table_args__ = (
        db.Index('ix_webhook_delivery_status', 'status'),
        db.Index('ix_webhook_delivery_next_retry', 'next_retry_at'),
    )


class WebhookService:
    """Service for managing webhooks and deliveries."""

    @staticmethod
    def create_webhook(
        org_id: str,
        name: str,
        url: str,
        events: list[str],
        custom_headers: dict | None = None
    ) -> Webhook:
        """
        Create a new webhook subscription.

        Args:
            org_id: Organization ID
            name: Webhook name
            url: Target URL
            events: List of event types to subscribe to
            custom_headers: Optional custom headers

        Returns:
            Created webhook
        """
        # Generate secret for webhook signing
        secret = hashlib.sha256(uuid.uuid4().bytes).hexdigest()

        webhook = Webhook(
            org_id=org_id,
            name=name,
            url=url,
            secret=secret,
            events=events,
            custom_headers=custom_headers or {}
        )

        db.session.add(webhook)
        db.session.commit()

        return webhook

    @staticmethod
    def update_webhook(
        webhook_id: str,
        **updates
    ) -> Webhook | None:
        """Update webhook settings."""
        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return None

        for key, value in updates.items():
            if hasattr(webhook, key) and key not in ['id', 'org_id', 'secret', 'created_at']:
                setattr(webhook, key, value)

        db.session.commit()
        return webhook

    @staticmethod
    def delete_webhook(webhook_id: str) -> bool:
        """Delete a webhook."""
        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return False

        db.session.delete(webhook)
        db.session.commit()
        return True

    @staticmethod
    def trigger_event(
        org_id: str,
        event_type: WebhookEventType,
        payload: Dict[str, Any]
    ):
        """
        Trigger webhook event for all subscribed webhooks.

        Args:
            org_id: Organization ID
            event_type: Type of event
            payload: Event data
        """
        # Find all active webhooks subscribed to this event
        stmt = (
            select(Webhook)
            .where(and_(
                Webhook.org_id == org_id,
                Webhook.is_active == True,
                Webhook.events.contains([event_type.value])
            ))
        )
        webhooks = db.session.execute(stmt).scalars().all()

        for webhook in webhooks:
            WebhookService._queue_delivery(webhook, event_type.value, payload)

    @staticmethod
    def _queue_delivery(webhook: Webhook, event_type: str, payload: Dict[str, Any]):
        """Queue a webhook delivery."""
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
            status=WebhookStatus.PENDING
        )

        db.session.add(delivery)
        db.session.commit()

        # Attempt immediate delivery
        WebhookService._deliver_webhook(delivery)

    @staticmethod
    def _deliver_webhook(delivery: WebhookDelivery):
        """
        Attempt to deliver a webhook.

        Args:
            delivery: WebhookDelivery instance
        """
        webhook = delivery.webhook

        try:
            # Prepare payload
            full_payload = {
                'event': delivery.event_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': delivery.payload
            }

            # Generate signature
            signature = WebhookService._generate_signature(
                json.dumps(full_payload),
                webhook.secret
            )

            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Webhook-Event': delivery.event_type,
                'X-Webhook-ID': webhook.id,
                'X-Delivery-ID': delivery.id,
            }

            # Add custom headers
            if webhook.custom_headers:
                headers.update(webhook.custom_headers)

            # Send request
            response = requests.post(
                webhook.url,
                json=full_payload,
                headers=headers,
                timeout=webhook.timeout
            )

            # Update delivery status
            delivery.attempts += 1
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit size

            if 200 <= response.status_code < 300:
                delivery.status = WebhookStatus.SUCCESS
                delivery.completed_at = datetime.now(timezone.utc)

                webhook.success_count += 1
                webhook.last_success_at = datetime.now(timezone.utc)
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            delivery.attempts += 1
            delivery.error_message = str(e)[:1000]

            webhook.failure_count += 1
            webhook.last_failure_at = datetime.now(timezone.utc)

            # Schedule retry if under limit
            if delivery.attempts < webhook.retry_count:
                delivery.status = WebhookStatus.RETRY
                # Exponential backoff: 1min, 5min, 15min
                retry_delay = timedelta(minutes=5 ** delivery.attempts)
                delivery.next_retry_at = datetime.now(timezone.utc) + retry_delay
            else:
                delivery.status = WebhookStatus.FAILED
                delivery.completed_at = datetime.now(timezone.utc)

        finally:
            webhook.last_triggered_at = datetime.now(timezone.utc)
            db.session.commit()

    @staticmethod
    def retry_failed_deliveries():
        """Retry failed webhook deliveries that are due."""
        now = datetime.now(timezone.utc)

        stmt = (
            select(WebhookDelivery)
            .where(and_(
                WebhookDelivery.status == WebhookStatus.RETRY,
                WebhookDelivery.next_retry_at <= now
            ))
        )
        deliveries = db.session.execute(stmt).scalars().all()

        for delivery in deliveries:
            WebhookService._deliver_webhook(delivery)

    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        """
        Generate HMAC signature for webhook payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            Hex signature
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: JSON payload string
            signature: Provided signature
            secret: Webhook secret

        Returns:
            True if valid
        """
        expected_signature = WebhookService._generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    def get_webhook_stats(webhook_id: str) -> dict:
        """Get statistics for a webhook."""
        webhook = db.session.get(Webhook, webhook_id)
        if not webhook:
            return {}

        # Get recent deliveries
        stmt = (
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(100)
        )
        recent_deliveries = db.session.execute(stmt).scalars().all()

        success_rate = 0
        if webhook.success_count + webhook.failure_count > 0:
            success_rate = (webhook.success_count / (webhook.success_count + webhook.failure_count)) * 100

        return {
            'total_deliveries': webhook.success_count + webhook.failure_count,
            'success_count': webhook.success_count,
            'failure_count': webhook.failure_count,
            'success_rate': round(success_rate, 2),
            'last_triggered_at': webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
            'last_success_at': webhook.last_success_at.isoformat() if webhook.last_success_at else None,
            'last_failure_at': webhook.last_failure_at.isoformat() if webhook.last_failure_at else None,
            'recent_deliveries': len(recent_deliveries)
        }


# Helper functions for common integrations

def trigger_game_event(game, event_type: WebhookEventType):
    """Trigger webhook for game events."""
    payload = {
        'game_id': game.id,
        'season_id': game.season_id,
        'home_team_id': game.home_team_id,
        'away_team_id': game.away_team_id,
        'home_score': game.home_score,
        'away_score': game.away_score,
        'status': game.status.value if hasattr(game.status, 'value') else game.status,
        'start_time': game.start_time.isoformat() if game.start_time else None,
    }

    WebhookService.trigger_event(game.org_id, event_type, payload)


def trigger_team_event(team, event_type: WebhookEventType):
    """Trigger webhook for team events."""
    payload = {
        'team_id': team.id,
        'name': team.name,
        'season_id': team.season_id,
        'wins': team.wins,
        'losses': team.losses,
        'ties': team.ties,
    }

    WebhookService.trigger_event(team.org_id, event_type, payload)


def trigger_player_event(player, event_type: WebhookEventType):
    """Trigger webhook for player events."""
    payload = {
        'player_id': player.id,
        'first_name': player.first_name,
        'last_name': player.last_name,
        'email': player.email,
        'team_id': player.team_id,
        'jersey_number': player.jersey_number,
    }

    WebhookService.trigger_event(player.org_id, event_type, payload)


def trigger_registration_event(registration, event_type: WebhookEventType):
    """Trigger webhook for registration events."""
    payload = {
        'registration_id': registration.id,
        'first_name': registration.first_name,
        'last_name': registration.last_name,
        'email': registration.email,
        'team_id': registration.team_id,
        'payment_status': registration.payment_status.value if hasattr(registration.payment_status, 'value') else registration.payment_status,
    }

    WebhookService.trigger_event(registration.org_id, event_type, payload)


def trigger_article_event(article, event_type: WebhookEventType):
    """Trigger webhook for article events."""
    payload = {
        'article_id': article.id,
        'title': article.title,
        'slug': article.slug,
        'excerpt': article.excerpt,
        'status': article.status.value if hasattr(article.status, 'value') else article.status,
        'published_at': article.published_at.isoformat() if article.published_at else None,
        'view_count': article.view_count,
    }

    WebhookService.trigger_event(article.org_id, event_type, payload)
