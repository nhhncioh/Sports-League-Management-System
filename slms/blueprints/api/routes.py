"""Read-only JSON API blueprint."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from slms.blueprints.common.tenant import org_query, tenant_required
from slms.models import Game, League, Team

api_bp = Blueprint('api', __name__)


def serialize_league(league: League) -> dict:
    return {
        'id': league.id,
        'name': league.name,
        'sport': league.sport.value if hasattr(league.sport, 'value') else league.sport,
        'created_at': league.created_at.isoformat() if league.created_at else None,
    }


def serialize_team(team: Team) -> dict:
    return {
        'id': team.id,
        'name': team.name,
        'season_id': team.season_id,
        'coach_name': team.coach_name,
    }


def serialize_game(game: Game) -> dict:
    return {
        'id': game.id,
        'season_id': game.season_id,
        'home_team_id': game.home_team_id,
        'away_team_id': game.away_team_id,
        'start_time': game.start_time.isoformat() if game.start_time else None,
        'status': game.status.value if hasattr(game.status, 'value') else game.status,
        'home_score': game.home_score,
        'away_score': game.away_score,
    }


@api_bp.route('/leagues', methods=['GET'])
@tenant_required
def list_leagues():
    leagues = org_query(League).all()
    return jsonify({'items': [serialize_league(l) for l in leagues]})


@api_bp.route('/teams', methods=['GET'])
@tenant_required
def list_teams():
    teams = org_query(Team).all()
    return jsonify({'items': [serialize_team(t) for t in teams]})


@api_bp.route('/games', methods=['GET'])
@tenant_required
def list_games():
    games = org_query(Game).all()
    return jsonify({'items': [serialize_game(g) for g in games]})

