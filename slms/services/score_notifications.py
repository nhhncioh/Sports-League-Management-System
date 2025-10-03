"""Score update notifications service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from flask import current_app

from slms.extensions import db
from slms.models.models import Game

if TYPE_CHECKING:
    from slms.models.models import Team


class ScoreNotificationService:
    """Service for broadcasting score updates to various surfaces."""

    @staticmethod
    def notify_score_update(game: Game, update_type: str = 'score_change'):
        """Notify all surfaces about a score update."""
        # Prepare notification payload
        payload = ScoreNotificationService._build_payload(game, update_type)

        # Update ticker
        ScoreNotificationService._update_ticker(payload)

        # Update standings cache
        ScoreNotificationService._invalidate_standings(game)

        # Send webhooks (if configured)
        ScoreNotificationService._send_webhooks(payload)

        # Log notification
        current_app.logger.info(f'Score notification sent for game {game.id}: {update_type}')

    @staticmethod
    def _build_payload(game: Game, update_type: str) -> dict:
        """Build notification payload."""
        return {
            'game_id': game.id,
            'season_id': game.season_id,
            'update_type': update_type,
            'status': game.status.value,
            'home_team': {
                'id': game.home_team_id,
                'name': game.home_team.name if game.home_team else None,
                'score': game.home_score
            },
            'away_team': {
                'id': game.away_team_id,
                'name': game.away_team.name if game.away_team else None,
                'score': game.away_score
            },
            'went_to_overtime': game.went_to_overtime,
            'overtime_periods': game.overtime_periods,
            'current_period': game.current_period,
            'game_clock': game.game_clock,
            'is_reconciled': game.is_reconciled,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def _update_ticker(payload: dict):
        """Update live ticker/scoreboard data."""
        # This would typically update a Redis cache or similar
        # For now, we'll just mark it as updated
        try:
            from flask import current_app
            cache_key = f"ticker:game:{payload['game_id']}"
            # If using Redis: redis_client.set(cache_key, json.dumps(payload), ex=3600)
            current_app.logger.debug(f'Ticker updated: {cache_key}')
        except Exception as e:
            current_app.logger.error(f'Failed to update ticker: {e}')

    @staticmethod
    def _invalidate_standings(game: Game):
        """Invalidate standings cache for the season."""
        try:
            from flask import current_app
            cache_key = f"standings:season:{game.season_id}"
            # If using Redis: redis_client.delete(cache_key)
            current_app.logger.debug(f'Standings cache invalidated: {cache_key}')
        except Exception as e:
            current_app.logger.error(f'Failed to invalidate standings: {e}')

    @staticmethod
    def _send_webhooks(payload: dict):
        """Send score update to configured webhooks."""
        # This would send HTTP POST to configured webhook URLs
        # For now, just log
        try:
            from flask import current_app
            current_app.logger.debug(f'Webhook payload prepared: {payload}')
            # Future: Send to webhook URLs from organization settings
        except Exception as e:
            current_app.logger.error(f'Failed to send webhooks: {e}')

    @staticmethod
    def notify_game_start(game: Game):
        """Notify that a game has started."""
        ScoreNotificationService.notify_score_update(game, 'game_start')

    @staticmethod
    def notify_game_end(game: Game):
        """Notify that a game has ended."""
        ScoreNotificationService.notify_score_update(game, 'game_end')

    @staticmethod
    def notify_overtime(game: Game):
        """Notify that game has entered overtime."""
        ScoreNotificationService.notify_score_update(game, 'overtime')

    @staticmethod
    def notify_reconciliation(game: Game):
        """Notify that a game has been reconciled."""
        ScoreNotificationService.notify_score_update(game, 'reconciled')
