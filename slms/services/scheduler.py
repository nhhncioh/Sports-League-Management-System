"""Schedule generation service with constraint handling."""

from __future__ import annotations

import itertools
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from typing import List, Tuple, Optional, Dict, Set

from sqlalchemy.orm import joinedload

from slms.blueprints.common.tenant import org_query
from slms.extensions import db
from slms.models import Game, GameStatus, Season, Team, Venue, Blackout, BlackoutScope


class ScheduleConstraintError(Exception):
    """Raised when schedule constraints cannot be satisfied."""
    pass


class ScheduleSlot:
    """Represents a potential game slot."""

    def __init__(self, date: date, start_time: str, venue: Venue):
        self.date = date
        self.start_time = start_time  # "HH:MM" format
        self.venue = venue
        self.datetime = self._to_datetime()

    def _to_datetime(self) -> datetime:
        """Convert date and start_time to datetime."""
        hour, minute = map(int, self.start_time.split(':'))
        return datetime.combine(self.date, time(hour, minute))

    def __str__(self):
        return f"{self.date} {self.start_time} at {self.venue.name}"


class TeamScheduleTracker:
    """Tracks team scheduling to enforce constraints."""

    def __init__(self):
        self.team_games: Dict[str, List[datetime]] = defaultdict(list)
        self.team_last_game: Dict[str, datetime] = {}

    def can_schedule_team(self, team_id: str, slot: ScheduleSlot, min_gap_days: int = 2) -> bool:
        """Check if team can play at this slot."""
        # Check if team already has a game on this date
        for game_time in self.team_games[team_id]:
            if game_time.date() == slot.date:
                return False

        # Check minimum gap between games
        if team_id in self.team_last_game:
            days_since_last = (slot.datetime.date() - self.team_last_game[team_id].date()).days
            if days_since_last < min_gap_days:
                return False

        return True

    def schedule_team(self, team_id: str, slot: ScheduleSlot):
        """Record that a team is scheduled for this slot."""
        self.team_games[team_id].append(slot.datetime)
        self.team_last_game[team_id] = slot.datetime


class ScheduleGenerator:
    """Generates game schedules with constraint satisfaction."""

    def __init__(self, season_id: str):
        self.season_id = season_id
        self.season = None
        self.teams = []
        self.venues = []
        self.blackouts = []
        self.tracker = TeamScheduleTracker()

    def generate_schedule(
        self,
        start_date: date,
        end_date: date,
        preferred_weekdays: List[int],  # 0=Monday, 6=Sunday
        preferred_start_times: List[str],  # ["18:00", "19:00"]
        selected_venue_ids: List[str],
        rounds: int = 1  # 1=single RR, 2=double RR
    ) -> List[Dict]:
        """
        Generate a schedule with the given constraints.

        Returns:
            List of game dictionaries with home_team, away_team, datetime, venue
        """
        # Load season data
        self._load_season_data(selected_venue_ids)

        # Generate round-robin matchups
        matchups = self._generate_round_robin_matchups(rounds)

        # Generate available time slots
        slots = self._generate_time_slots(
            start_date, end_date, preferred_weekdays, preferred_start_times
        )

        # Assign matchups to slots using greedy algorithm
        scheduled_games = self._assign_matchups_to_slots(matchups, slots)

        return scheduled_games

    def _load_season_data(self, selected_venue_ids: List[str]):
        """Load season, teams, venues, and blackouts."""
        # Load season with teams
        self.season = (
            org_query(Season)
            .filter(Season.id == self.season_id)
            .options(joinedload(Season.teams))
            .first()
        )

        if not self.season:
            raise ScheduleConstraintError(f"Season {self.season_id} not found")

        self.teams = self.season.teams

        if len(self.teams) < 2:
            raise ScheduleConstraintError("Need at least 2 teams to generate schedule")

        # Load selected venues
        self.venues = (
            org_query(Venue)
            .filter(Venue.id.in_(selected_venue_ids))
            .all()
        )

        if not self.venues:
            raise ScheduleConstraintError("No venues selected")

        # Load blackouts for the date range
        self.blackouts = (
            org_query(Blackout)
            .options(joinedload(Blackout.venue), joinedload(Blackout.team))
            .all()
        )

    def _generate_round_robin_matchups(self, rounds: int) -> List[Tuple[Team, Team]]:
        """Generate round-robin matchups between all teams."""
        matchups = []

        for _ in range(rounds):
            # Generate all possible pairings
            for home_team, away_team in itertools.combinations(self.teams, 2):
                matchups.append((home_team, away_team))
                # For double round-robin, add the reverse matchup
                if rounds == 2:
                    matchups.append((away_team, home_team))

        return matchups

    def _generate_time_slots(
        self,
        start_date: date,
        end_date: date,
        preferred_weekdays: List[int],
        preferred_start_times: List[str]
    ) -> List[ScheduleSlot]:
        """Generate all available time slots within constraints."""
        slots = []
        current_date = start_date

        while current_date <= end_date:
            # Check if this is a preferred weekday
            if current_date.weekday() in preferred_weekdays:
                # Generate slots for each venue and time combination
                for venue in self.venues:
                    for start_time in preferred_start_times:
                        if self._is_slot_available(current_date, start_time, venue):
                            slots.append(ScheduleSlot(current_date, start_time, venue))

            current_date += timedelta(days=1)

        return slots

    def _is_slot_available(self, slot_date: date, start_time: str, venue: Venue) -> bool:
        """Check if a specific slot is available based on constraints."""
        # Check venue operating hours
        if venue.open_time and venue.close_time:
            if start_time < venue.open_time or start_time > venue.close_time:
                return False

        # Check venue blackouts
        for blackout in self.blackouts:
            if (blackout.scope == BlackoutScope.VENUE and
                blackout.venue_id == venue.id and
                blackout.date == slot_date):
                return False

        return True

    def _is_team_blackout(self, team_id: str, slot_date: date) -> bool:
        """Check if team has a blackout on this date."""
        for blackout in self.blackouts:
            if (blackout.scope == BlackoutScope.TEAM and
                blackout.team_id == team_id and
                blackout.date == slot_date):
                return True
        return False

    def _assign_matchups_to_slots(
        self,
        matchups: List[Tuple[Team, Team]],
        slots: List[ScheduleSlot]
    ) -> List[Dict]:
        """Assign matchups to slots using greedy algorithm."""
        scheduled_games = []
        used_slots = set()

        # Sort matchups to prioritize certain pairings if needed
        # For now, use original order

        for home_team, away_team in matchups:
            assigned = False

            # Try to find a suitable slot
            for slot in slots:
                slot_key = (slot.date, slot.start_time, slot.venue.id)

                # Skip if slot already used
                if slot_key in used_slots:
                    continue

                # Check team constraints
                if not self.tracker.can_schedule_team(home_team.id, slot):
                    continue

                if not self.tracker.can_schedule_team(away_team.id, slot):
                    continue

                # Check team blackouts
                if self._is_team_blackout(home_team.id, slot.date):
                    continue

                if self._is_team_blackout(away_team.id, slot.date):
                    continue

                # Assign the game to this slot
                self.tracker.schedule_team(home_team.id, slot)
                self.tracker.schedule_team(away_team.id, slot)
                used_slots.add(slot_key)

                scheduled_games.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'datetime': slot.datetime,
                    'venue': slot.venue,
                    'slot': slot
                })

                assigned = True
                break

            if not assigned:
                raise ScheduleConstraintError(
                    f"Could not schedule {home_team.name} vs {away_team.name}. "
                    f"Consider adjusting date range, venues, or time slots."
                )

        return scheduled_games

    def persist_schedule(self, scheduled_games: List[Dict]) -> List[Game]:
        """Save the generated schedule to the database."""
        games = []

        for game_data in scheduled_games:
            game = Game(
                org_id=self.season.org_id,
                season_id=self.season.id,
                home_team_id=game_data['home_team'].id,
                away_team_id=game_data['away_team'].id,
                venue_id=game_data['venue'].id,
                start_time=game_data['datetime'],
                status=GameStatus.SCHEDULED
            )

            db.session.add(game)
            games.append(game)

        db.session.commit()
        return games


def generate_season_schedule(
    season_id: str,
    start_date: date,
    end_date: date,
    preferred_weekdays: List[int],
    preferred_start_times: List[str],
    selected_venue_ids: List[str],
    rounds: int = 1,
    persist: bool = False
) -> List[Dict]:
    """
    Convenience function to generate a season schedule.

    Args:
        season_id: Season to generate schedule for
        start_date: First possible game date
        end_date: Last possible game date
        preferred_weekdays: List of weekday numbers (0=Monday, 6=Sunday)
        preferred_start_times: List of time strings (e.g. ["18:00", "19:00"])
        selected_venue_ids: List of venue IDs to use
        rounds: Number of round-robin rounds (1 or 2)
        persist: Whether to save to database

    Returns:
        List of scheduled game dictionaries
    """
    generator = ScheduleGenerator(season_id)

    scheduled_games = generator.generate_schedule(
        start_date=start_date,
        end_date=end_date,
        preferred_weekdays=preferred_weekdays,
        preferred_start_times=preferred_start_times,
        selected_venue_ids=selected_venue_ids,
        rounds=rounds
    )

    if persist:
        generator.persist_schedule(scheduled_games)

    return scheduled_games


__all__ = ['ScheduleGenerator', 'ScheduleConstraintError', 'generate_season_schedule']