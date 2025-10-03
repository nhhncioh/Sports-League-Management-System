"""Live game console service for real-time score reporting."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from slms.extensions import db
from slms.models.models import (
    Game, GameStatus, GameEvent, PlayerGameStat, Penalty,
    ScoreUpdate, Player, Team, PeriodType, StatType
)


class LiveGameService:
    """Service for live game operations."""

    @staticmethod
    def start_game(game_id: str, org_id: str, user_id: str) -> Game | None:
        """Start a game (move to IN_PROGRESS status)."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        if game.status != GameStatus.SCHEDULED:
            return None

        game.status = GameStatus.IN_PROGRESS
        game.current_period = 1
        game.last_score_update = datetime.now(timezone.utc)

        # Create period start event
        event = GameEvent(
            org_id=org_id,
            game_id=game_id,
            event_type='period_start',
            period=1,
            period_type=PeriodType.REGULATION,
            description='Game started'
        )
        db.session.add(event)
        db.session.commit()
        return game

    @staticmethod
    def update_score(
        game_id: str,
        org_id: str,
        user_id: str,
        home_score: int,
        away_score: int,
        update_type: str = 'live_update',
        notes: str | None = None
    ) -> Game | None:
        """Update game score with audit trail."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        # Record score update for audit
        update = ScoreUpdate(
            org_id=org_id,
            game_id=game_id,
            user_id=user_id,
            previous_home_score=game.home_score,
            previous_away_score=game.away_score,
            new_home_score=home_score,
            new_away_score=away_score,
            update_type=update_type,
            notes=notes
        )

        game.home_score = home_score
        game.away_score = away_score
        game.last_score_update = datetime.now(timezone.utc)

        db.session.add(update)
        db.session.commit()
        return game

    @staticmethod
    def add_game_event(
        game_id: str,
        org_id: str,
        event_type: str,
        team_id: str | None = None,
        player_id: str | None = None,
        period: int | None = None,
        period_type: PeriodType | None = None,
        game_clock: str | None = None,
        details: dict | None = None,
        description: str | None = None
    ) -> GameEvent:
        """Add a game event (goal, timeout, substitution, etc.)."""
        event = GameEvent(
            org_id=org_id,
            game_id=game_id,
            event_type=event_type,
            team_id=team_id,
            player_id=player_id,
            period=period,
            period_type=period_type,
            game_clock=game_clock,
            details=details or {},
            description=description
        )
        db.session.add(event)
        db.session.commit()
        return event

    @staticmethod
    def record_penalty(
        game_id: str,
        org_id: str,
        team_id: str,
        penalty_type: str,
        player_id: str | None = None,
        period: int | None = None,
        game_clock: str | None = None,
        minutes: int | None = None,
        severity: str | None = None,
        description: str | None = None,
        resulted_in_ejection: bool = False
    ) -> Penalty:
        """Record a penalty/foul."""
        penalty = Penalty(
            org_id=org_id,
            game_id=game_id,
            team_id=team_id,
            player_id=player_id,
            penalty_type=penalty_type,
            period=period,
            game_clock=game_clock,
            minutes=minutes,
            severity=severity,
            description=description,
            resulted_in_ejection=resulted_in_ejection
        )
        db.session.add(penalty)

        # Also create a game event for the penalty
        LiveGameService.add_game_event(
            game_id=game_id,
            org_id=org_id,
            event_type='penalty',
            team_id=team_id,
            player_id=player_id,
            period=period,
            game_clock=game_clock,
            details={'penalty_type': penalty_type, 'severity': severity},
            description=description
        )

        db.session.commit()
        return penalty

    @staticmethod
    def update_player_stat(
        game_id: str,
        org_id: str,
        player_id: str,
        team_id: str,
        stat_type: StatType,
        value: int
    ) -> PlayerGameStat:
        """Update or create a player stat for the game."""
        # Try to find existing stat
        stmt = (
            select(PlayerGameStat)
            .where(PlayerGameStat.game_id == game_id)
            .where(PlayerGameStat.player_id == player_id)
            .where(PlayerGameStat.stat_type == stat_type)
        )
        stat = db.session.execute(stmt).scalar_one_or_none()

        if stat:
            stat.value = value
        else:
            stat = PlayerGameStat(
                org_id=org_id,
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                stat_type=stat_type,
                value=value
            )
            db.session.add(stat)

        db.session.commit()
        return stat

    @staticmethod
    def increment_player_stat(
        game_id: str,
        org_id: str,
        player_id: str,
        team_id: str,
        stat_type: StatType,
        increment: int = 1
    ) -> PlayerGameStat:
        """Increment a player stat by a value."""
        stmt = (
            select(PlayerGameStat)
            .where(PlayerGameStat.game_id == game_id)
            .where(PlayerGameStat.player_id == player_id)
            .where(PlayerGameStat.stat_type == stat_type)
        )
        stat = db.session.execute(stmt).scalar_one_or_none()

        if stat:
            stat.value += increment
        else:
            stat = PlayerGameStat(
                org_id=org_id,
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                stat_type=stat_type,
                value=increment
            )
            db.session.add(stat)

        db.session.commit()
        return stat

    @staticmethod
    def set_halftime(game_id: str, org_id: str) -> Game | None:
        """Set game to halftime status."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        game.status = GameStatus.HALFTIME

        # Create halftime event
        LiveGameService.add_game_event(
            game_id=game_id,
            org_id=org_id,
            event_type='period_end',
            description='Halftime'
        )

        db.session.commit()
        return game

    @staticmethod
    def resume_from_halftime(game_id: str, org_id: str, second_half_period: int = 2) -> Game | None:
        """Resume game from halftime."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        game.status = GameStatus.IN_PROGRESS
        game.current_period = second_half_period

        LiveGameService.add_game_event(
            game_id=game_id,
            org_id=org_id,
            event_type='period_start',
            period=second_half_period,
            description=f'Period {second_half_period} started'
        )

        db.session.commit()
        return game

    @staticmethod
    def start_overtime(game_id: str, org_id: str) -> Game | None:
        """Start overtime period."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        game.status = GameStatus.OVERTIME
        game.went_to_overtime = True
        game.overtime_periods += 1

        # Save regulation scores
        if game.home_score_regulation is None:
            game.home_score_regulation = game.home_score
            game.away_score_regulation = game.away_score

        LiveGameService.add_game_event(
            game_id=game_id,
            org_id=org_id,
            event_type='overtime_start',
            period_type=PeriodType.OVERTIME,
            description=f'Overtime period {game.overtime_periods} started'
        )

        db.session.commit()
        return game

    @staticmethod
    def end_game(game_id: str, org_id: str, user_id: str) -> Game | None:
        """End game and set to FINAL status."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        game.status = GameStatus.FINAL
        game.last_score_update = datetime.now(timezone.utc)

        LiveGameService.add_game_event(
            game_id=game_id,
            org_id=org_id,
            event_type='game_end',
            description='Game ended'
        )

        db.session.commit()
        return game

    @staticmethod
    def reconcile_game(game_id: str, org_id: str, user_id: str) -> Game | None:
        """Mark game as reconciled (final score confirmed)."""
        game = db.session.get(Game, game_id)
        if not game or game.org_id != org_id:
            return None

        if game.status != GameStatus.FINAL:
            return None

        game.is_reconciled = True
        game.reconciled_at = datetime.now(timezone.utc)
        game.reconciled_by_user_id = user_id

        db.session.commit()
        return game

    @staticmethod
    def get_game_with_details(game_id: str, org_id: str) -> Game | None:
        """Get game with all related data loaded."""
        stmt = (
            select(Game)
            .where(Game.id == game_id)
            .where(Game.org_id == org_id)
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team),
                joinedload(Game.venue),
                joinedload(Game.game_events),
                joinedload(Game.player_stats),
                joinedload(Game.penalties)
            )
        )
        return db.session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_game_events(game_id: str, org_id: str) -> list[GameEvent]:
        """Get all events for a game ordered by time."""
        stmt = (
            select(GameEvent)
            .where(GameEvent.game_id == game_id)
            .where(GameEvent.org_id == org_id)
            .order_by(GameEvent.event_time.desc())
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def get_player_stats(game_id: str, org_id: str) -> list[PlayerGameStat]:
        """Get all player stats for a game."""
        stmt = (
            select(PlayerGameStat)
            .where(PlayerGameStat.game_id == game_id)
            .where(PlayerGameStat.org_id == org_id)
            .options(joinedload(PlayerGameStat.player), joinedload(PlayerGameStat.team))
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def get_penalties(game_id: str, org_id: str) -> list[Penalty]:
        """Get all penalties for a game."""
        stmt = (
            select(Penalty)
            .where(Penalty.game_id == game_id)
            .where(Penalty.org_id == org_id)
            .options(joinedload(Penalty.player), joinedload(Penalty.team))
            .order_by(Penalty.created_at)
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def get_score_history(game_id: str, org_id: str) -> list[ScoreUpdate]:
        """Get score update history for reconciliation."""
        stmt = (
            select(ScoreUpdate)
            .where(ScoreUpdate.game_id == game_id)
            .where(ScoreUpdate.org_id == org_id)
            .order_by(ScoreUpdate.created_at)
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def validate_score(game: Game) -> dict[str, Any]:
        """Validate game score against events and stats."""
        issues = []
        warnings = []

        # Check if score matches player stats (for basketball/soccer)
        player_stats = LiveGameService.get_player_stats(game.id, game.org_id)

        home_points = sum(
            s.value for s in player_stats
            if s.team_id == game.home_team_id and s.stat_type in [StatType.POINTS, StatType.GOALS]
        )
        away_points = sum(
            s.value for s in player_stats
            if s.team_id == game.away_team_id and s.stat_type in [StatType.POINTS, StatType.GOALS]
        )

        if home_points > 0 and home_points != game.home_score:
            warnings.append(f'Home score ({game.home_score}) does not match player stats total ({home_points})')

        if away_points > 0 and away_points != game.away_score:
            warnings.append(f'Away score ({game.away_score}) does not match player stats total ({away_points})')

        # Check for tied game in non-tie leagues
        if game.home_score == game.away_score and game.status == GameStatus.FINAL:
            # This would need season rules check
            warnings.append('Game ended in a tie - verify if ties are allowed')

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
