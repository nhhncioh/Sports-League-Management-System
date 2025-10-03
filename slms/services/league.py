"""League lifecycle management service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from slms.extensions import db
from slms.models.models import League, LeagueStatus, Season, SeasonStatus, Organization


class LeagueService:
    """Service for league lifecycle operations."""

    @staticmethod
    def create_league(
        org_id: str,
        name: str,
        sport: str,
        description: str | None = None,
        league_timezone: str = 'UTC',
        settings: dict | None = None,
    ) -> League:
        """Create a new league in draft status."""
        league = League(
            org_id=org_id,
            name=name,
            sport=sport,
            description=description,
            status=LeagueStatus.DRAFT,
            timezone=league_timezone,
            settings=settings or {},
        )
        db.session.add(league)
        db.session.commit()
        return league

    @staticmethod
    def update_league(
        league_id: str,
        org_id: str,
        **updates: Any,
    ) -> League | None:
        """Update league details."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None

        for key, value in updates.items():
            if hasattr(league, key) and key not in ['id', 'org_id', 'created_at']:
                setattr(league, key, value)

        db.session.commit()
        return league

    @staticmethod
    def activate_league(league_id: str, org_id: str) -> League | None:
        """Activate a league (move from draft to active)."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None

        league.status = LeagueStatus.ACTIVE
        db.session.commit()
        return league

    @staticmethod
    def archive_league(league_id: str, org_id: str) -> League | None:
        """Archive a league and all its seasons."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None

        league.status = LeagueStatus.ARCHIVED
        league.archived_at = datetime.now(timezone.utc)

        # Archive all seasons in this league
        for season in league.seasons:
            if season.status != SeasonStatus.ARCHIVED:
                season.status = SeasonStatus.ARCHIVED
                season.archived_at = datetime.now(timezone.utc)

        db.session.commit()
        return league

    @staticmethod
    def restore_league(league_id: str, org_id: str) -> League | None:
        """Restore an archived league."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None

        league.status = LeagueStatus.ACTIVE
        league.archived_at = None
        db.session.commit()
        return league

    @staticmethod
    def get_league(league_id: str, org_id: str) -> League | None:
        """Get a league by ID with authorization check."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None
        return league

    @staticmethod
    def list_leagues(
        org_id: str,
        status: LeagueStatus | None = None,
        include_archived: bool = False,
    ) -> list[League]:
        """List leagues for an organization."""
        query = select(League).where(League.org_id == org_id)

        if status:
            query = query.where(League.status == status)
        elif not include_archived:
            query = query.where(League.status != LeagueStatus.ARCHIVED)

        query = query.order_by(League.created_at.desc())
        return list(db.session.execute(query).scalars())

    @staticmethod
    def delete_league(league_id: str, org_id: str) -> bool:
        """Permanently delete a league (should only be used for draft leagues)."""
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return False

        # Only allow deletion of draft leagues
        if league.status != LeagueStatus.DRAFT:
            return False

        db.session.delete(league)
        db.session.commit()
        return True


class SeasonService:
    """Service for season lifecycle operations."""

    @staticmethod
    def create_season(
        org_id: str,
        league_id: str,
        name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        rules: dict | None = None,
        season_timezone: str | None = None,
        **kwargs: Any,
    ) -> Season | None:
        """Create a new season in draft status."""
        # Verify league exists and belongs to org
        league = db.session.get(League, league_id)
        if not league or league.org_id != org_id:
            return None

        season = Season(
            org_id=org_id,
            league_id=league_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=SeasonStatus.DRAFT,
            rules=rules or {},
            timezone=season_timezone,
            **kwargs,
        )
        db.session.add(season)
        db.session.commit()
        return season

    @staticmethod
    def update_season(
        season_id: str,
        org_id: str,
        **updates: Any,
    ) -> Season | None:
        """Update season details."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        for key, value in updates.items():
            if hasattr(season, key) and key not in ['id', 'org_id', 'league_id', 'created_at']:
                setattr(season, key, value)

        db.session.commit()
        return season

    @staticmethod
    def activate_season(season_id: str, org_id: str) -> Season | None:
        """Activate a season (move from draft to active)."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        # Deactivate other active seasons in the same league
        stmt = (
            select(Season)
            .where(Season.league_id == season.league_id)
            .where(Season.status == SeasonStatus.ACTIVE)
            .where(Season.id != season_id)
        )
        other_active_seasons = db.session.execute(stmt).scalars()
        for other_season in other_active_seasons:
            other_season.is_active = False

        season.status = SeasonStatus.ACTIVE
        season.is_active = True
        db.session.commit()
        return season

    @staticmethod
    def set_off_season(season_id: str, org_id: str, message: str | None = None) -> Season | None:
        """Move season to off-season state."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        season.status = SeasonStatus.OFF_SEASON
        if message:
            season.off_season_message = message
        db.session.commit()
        return season

    @staticmethod
    def complete_season(season_id: str, org_id: str) -> Season | None:
        """Mark season as completed."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        season.status = SeasonStatus.COMPLETED
        season.is_active = False
        db.session.commit()
        return season

    @staticmethod
    def archive_season(season_id: str, org_id: str) -> Season | None:
        """Archive a season."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        season.status = SeasonStatus.ARCHIVED
        season.archived_at = datetime.now(timezone.utc)
        season.is_active = False
        db.session.commit()
        return season

    @staticmethod
    def restore_season(season_id: str, org_id: str) -> Season | None:
        """Restore an archived season to completed state."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None

        season.status = SeasonStatus.COMPLETED
        season.archived_at = None
        db.session.commit()
        return season

    @staticmethod
    def get_season(season_id: str, org_id: str) -> Season | None:
        """Get a season by ID with authorization check."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return None
        return season

    @staticmethod
    def list_seasons(
        org_id: str,
        league_id: str | None = None,
        status: SeasonStatus | None = None,
        include_archived: bool = False,
    ) -> list[Season]:
        """List seasons for an organization or league."""
        query = select(Season).where(Season.org_id == org_id)

        if league_id:
            query = query.where(Season.league_id == league_id)

        if status:
            query = query.where(Season.status == status)
        elif not include_archived:
            query = query.where(Season.status != SeasonStatus.ARCHIVED)

        query = query.options(joinedload(Season.league)).order_by(Season.start_date.desc())
        return list(db.session.execute(query).scalars())

    @staticmethod
    def delete_season(season_id: str, org_id: str) -> bool:
        """Permanently delete a season (should only be used for draft seasons)."""
        season = db.session.get(Season, season_id)
        if not season or season.org_id != org_id:
            return False

        # Only allow deletion of draft seasons
        if season.status != SeasonStatus.DRAFT:
            return False

        db.session.delete(season)
        db.session.commit()
        return True

    @staticmethod
    def get_effective_timezone(season: Season) -> str:
        """Get the effective timezone for a season (season > league > org)."""
        if season.timezone:
            return season.timezone
        if season.league and season.league.timezone:
            return season.league.timezone
        return 'UTC'
