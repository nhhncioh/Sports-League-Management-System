"""Public portal routes with optimized queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, abort
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from slms.blueprints.common.tenant import org_query, tenant_required
from slms.extensions import db
from slms.models import Game, GameStatus, League, Player, Season, Team


# Serve portal pages under /portal to avoid clashing with public landing at /
portal_bp = Blueprint('portal', __name__, url_prefix='/portal')


def compute_standings(season: Season) -> list[dict]:
    """Compute team standings from completed games."""
    # Get all completed games for this season
    games = (
        org_query(Game)
        .filter(
            Game.season_id == season.id,
            Game.status.in_([GameStatus.FINAL, GameStatus.FORFEIT])
        )
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team)
        )
        .all()
    )

    # Initialize team stats
    team_stats = {}
    season_teams = org_query(Team).filter(Team.season_id == season.id).all()

    for team in season_teams:
        team_stats[team.id] = {
            'team': team,
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'points_for': 0,
            'points_against': 0,
            'recent_form': []
        }

    # Process each completed game
    for game in games:
        if not game.home_team or not game.away_team:
            continue

        home_score = game.home_score or 0
        away_score = game.away_score or 0

        # Update team stats
        if game.home_team.id in team_stats:
            team_stats[game.home_team.id]['games_played'] += 1
            team_stats[game.home_team.id]['points_for'] += home_score
            team_stats[game.home_team.id]['points_against'] += away_score

            if home_score > away_score:
                team_stats[game.home_team.id]['wins'] += 1
                team_stats[game.home_team.id]['recent_form'].append('W')
            else:
                team_stats[game.home_team.id]['losses'] += 1
                team_stats[game.home_team.id]['recent_form'].append('L')

        if game.away_team.id in team_stats:
            team_stats[game.away_team.id]['games_played'] += 1
            team_stats[game.away_team.id]['points_for'] += away_score
            team_stats[game.away_team.id]['points_against'] += home_score

            if away_score > home_score:
                team_stats[game.away_team.id]['wins'] += 1
                team_stats[game.away_team.id]['recent_form'].append('W')
            else:
                team_stats[game.away_team.id]['losses'] += 1
                team_stats[game.away_team.id]['recent_form'].append('L')

    # Calculate additional stats and sort
    standings = []
    for team_id, stats in team_stats.items():
        # Calculate win percentage
        games_played = stats['games_played']
        win_percentage = stats['wins'] / games_played if games_played > 0 else 0

        # Calculate point differential
        point_differential = stats['points_for'] - stats['points_against']

        # Keep only last 5 games for form
        stats['recent_form'] = stats['recent_form'][-5:]

        standings.append({
            'team': stats['team'],
            'games_played': games_played,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_percentage': win_percentage,
            'points_for': stats['points_for'],
            'points_against': stats['points_against'],
            'point_differential': point_differential,
            'recent_form': stats['recent_form']
        })

    # Sort by win percentage (desc), then by point differential (desc)
    standings.sort(key=lambda x: (-x['win_percentage'], -x['point_differential']))

    return standings


@portal_bp.route('/')
@tenant_required
def index():
    """Homepage with leagues and seasons."""
    try:
        leagues = (
            org_query(League)
            .options(joinedload(League.seasons))
            .all()
        )
        recent_games = (
            org_query(Game)
            .filter(Game.status.in_([GameStatus.FINAL, GameStatus.FORFEIT]))
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team),
                joinedload(Game.season)
            )
            .order_by(Game.start_time.desc())
            .limit(6)
            .all()
        )
    except Exception:
        leagues = []
        recent_games = []

    return render_template('public/index.html', leagues=leagues, recent_games=recent_games)


@portal_bp.route('/seasons/<season_id>/schedule')
@tenant_required
def season_schedule(season_id: str):
    """Season schedule grouped by date."""
    season = org_query(Season).filter(Season.id == season_id).first_or_404()

    # Get all games for this season with optimized loading
    games = (
        org_query(Game)
        .filter(Game.season_id == season_id)
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team),
            joinedload(Game.venue)
        )
        .order_by(Game.start_time.asc())
        .all()
    )

    # Group games by date
    games_by_date = defaultdict(list)
    for game in games:
        if game.start_time:
            date = game.start_time.date()
            games_by_date[date].append(game)

    # Convert to ordered dict
    games_by_date = dict(sorted(games_by_date.items()))

    return render_template(
        'public/season_schedule.html',
        season=season,
        games_by_date=games_by_date
    )


@portal_bp.route('/seasons/<season_id>/standings')
@tenant_required
def season_standings(season_id: str):
    """Season standings computed from game results."""
    season = (
        org_query(Season)
        .filter(Season.id == season_id)
        .options(joinedload(Season.league))
        .first_or_404()
    )

    standings = compute_standings(season)

    return render_template(
        'public/season_standings.html',
        season=season,
        standings=standings
    )


@portal_bp.route('/teams/<team_id>')
@tenant_required
def team_detail(team_id: str):
    """Team profile with roster, fixtures, and results."""
    team = (
        org_query(Team)
        .filter(Team.id == team_id)
        .options(
            joinedload(Team.players),
            joinedload(Team.season)
        )
        .first_or_404()
    )

    # Get team's games with optimized loading
    recent_games = (
        org_query(Game)
        .filter(
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
            Game.status.in_([GameStatus.FINAL, GameStatus.FORFEIT])
        )
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team)
        )
        .order_by(Game.start_time.desc())
        .limit(10)
        .all()
    )

    # Get upcoming games
    upcoming_games = (
        org_query(Game)
        .filter(
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
            Game.status == GameStatus.SCHEDULED,
            Game.start_time > datetime.utcnow()
        )
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team)
        )
        .order_by(Game.start_time.asc())
        .limit(5)
        .all()
    )

    # Compute team stats if they have a season
    team_stats = None
    if team.season:
        standings = compute_standings(team.season)
        team_stats = next((s for s in standings if s['team'].id == team_id), None)

    return render_template(
        'public/team_detail.html',
        team=team,
        roster=team.players,
        recent_games=recent_games,
        upcoming_games=upcoming_games,
        team_stats=team_stats
    )


@portal_bp.route('/games/<game_id>')
@tenant_required
def game_detail(game_id: str):
    """Game details with scores, status, and notes."""
    game = (
        org_query(Game)
        .filter(Game.id == game_id)
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team),
            joinedload(Game.season).joinedload(Season.league),
            joinedload(Game.venue)
        )
        .first_or_404()
    )

    # Get related games between these teams
    related_games = []
    if game.home_team and game.away_team:
        related_games = (
            org_query(Game)
            .filter(
                Game.id != game_id,
                or_(
                    and_(
                        Game.home_team_id == game.home_team_id,
                        Game.away_team_id == game.away_team_id
                    ),
                    and_(
                        Game.home_team_id == game.away_team_id,
                        Game.away_team_id == game.home_team_id
                    )
                ),
                Game.status.in_([GameStatus.FINAL, GameStatus.FORFEIT])
            )
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team)
            )
            .order_by(Game.start_time.desc())
            .limit(5)
            .all()
        )

    return render_template(
        'public/game_detail.html',
        game=game,
        related_games=related_games
    )


__all__ = ['portal_bp']
