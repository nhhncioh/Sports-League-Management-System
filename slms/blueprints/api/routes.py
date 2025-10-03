"""Tenant-aware JSON API blueprint."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from slms.blueprints.common.tenant import org_query, tenant_required
from slms.models import Game, League, MediaAsset, Team
from slms.services.media_library import (
    create_media_asset,
    delete_media_asset,
    serialize_media_asset,
    serialize_media_collection,
)

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


@api_bp.route('/games/live', methods=['GET'])
@tenant_required
def live_games():
    """Get all currently live games with score updates."""
    from slms.models import GameStatus
    live_games = org_query(Game).filter(
        Game.status.in_([GameStatus.IN_PROGRESS, GameStatus.HALFTIME, GameStatus.OVERTIME])
    ).order_by(Game.start_time).all()

    result = []
    for game in live_games:
        result.append({
            'id': game.id,
            'home_team': {
                'id': game.home_team_id,
                'name': game.home_team.name if game.home_team else 'TBD',
            },
            'away_team': {
                'id': game.away_team_id,
                'name': game.away_team.name if game.away_team else 'TBD',
            },
            'home_score': game.home_score,
            'away_score': game.away_score,
            'status': game.status.value if hasattr(game.status, 'value') else game.status,
            'current_period': game.current_period,
            'game_clock': game.game_clock,
            'last_update': game.last_score_update.isoformat() if game.last_score_update else None,
            'venue': game.venue.name if game.venue else None,
        })

    return jsonify({'items': result})


@api_bp.route('/games/<game_id>', methods=['GET'])
@tenant_required
def game_detail(game_id):
    """Get detailed game information including events and player stats."""
    game = org_query(Game).filter(Game.id == game_id).first()
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    # Get game events (timeline)
    from slms.models import GameEvent
    events = org_query(GameEvent).filter(
        GameEvent.game_id == game_id
    ).order_by(GameEvent.event_time).all()

    event_list = []
    for event in events:
        event_list.append({
            'id': event.id,
            'event_type': event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
            'period': event.period,
            'game_clock': event.game_clock,
            'event_time': event.event_time.isoformat() if event.event_time else None,
            'description': event.description,
            'player_id': event.player_id,
        })

    return jsonify({
        'game': {
            'id': game.id,
            'season_id': game.season_id,
            'home_team': {
                'id': game.home_team_id,
                'name': game.home_team.name if game.home_team else 'TBD',
            },
            'away_team': {
                'id': game.away_team_id,
                'name': game.away_team.name if game.away_team else 'TBD',
            },
            'venue': {
                'id': game.venue_id,
                'name': game.venue.name if game.venue else None,
                'address': game.venue.address if game.venue else None,
            },
            'start_time': game.start_time.isoformat() if game.start_time else None,
            'status': game.status.value if hasattr(game.status, 'value') else game.status,
            'home_score': game.home_score,
            'away_score': game.away_score,
            'current_period': game.current_period,
            'game_clock': game.game_clock,
            'period_scores': game.period_scores,
            'went_to_overtime': game.went_to_overtime,
        },
        'events': event_list,
    })


@api_bp.route('/standings', methods=['GET'])
@tenant_required
def standings():
    """Get standings with optional filters."""
    season_id = request.args.get('season_id')
    division = request.args.get('division')

    from slms.models import Standing
    query = org_query(Standing)

    if season_id:
        query = query.filter(Standing.season_id == season_id)
    if division:
        query = query.filter(Standing.division == division)

    standings = query.order_by(Standing.position).all()

    result = []
    for standing in standings:
        result.append({
            'position': standing.position,
            'team': {
                'id': standing.team_id,
                'name': standing.team.name if standing.team else 'Unknown',
            },
            'games_played': standing.games_played,
            'wins': standing.wins,
            'losses': standing.losses,
            'ties': standing.ties,
            'points': standing.points,
            'goals_for': standing.goals_for,
            'goals_against': standing.goals_against,
            'goal_difference': standing.goal_difference,
        })

    return jsonify({'items': result})


@api_bp.route('/stats/leaders', methods=['GET'])
@tenant_required
def stat_leaders():
    """Get statistical leaders for various categories."""
    season_id = request.args.get('season_id')
    stat_type = request.args.get('stat_type', 'points')
    limit = int(request.args.get('limit', 10))

    from slms.models import PlayerSeasonStat, Player
    from sqlalchemy import desc

    query = org_query(PlayerSeasonStat).join(Player)

    if season_id:
        query = query.filter(PlayerSeasonStat.season_id == season_id)

    # Map stat type to column
    stat_column_map = {
        'points': PlayerSeasonStat.total_points,
        'goals': PlayerSeasonStat.total_goals,
        'assists': PlayerSeasonStat.total_assists,
        'rebounds': PlayerSeasonStat.total_rebounds,
        'steals': PlayerSeasonStat.total_steals,
        'blocks': PlayerSeasonStat.total_blocks,
    }

    stat_column = stat_column_map.get(stat_type, PlayerSeasonStat.total_points)
    leaders = query.order_by(desc(stat_column)).limit(limit).all()

    result = []
    for stat in leaders:
        result.append({
            'player': {
                'id': stat.player_id,
                'name': f"{stat.player.first_name} {stat.player.last_name}" if stat.player else 'Unknown',
                'team_id': stat.player.team_id if stat.player else None,
            },
            'value': getattr(stat, f'total_{stat_type}', 0),
            'games_played': stat.games_played,
        })

    return jsonify({'items': result, 'stat_type': stat_type})


@api_bp.route('/media-assets', methods=['GET'])
@login_required
@tenant_required
def list_media_assets():
    query = org_query(MediaAsset)
    media_type = (request.args.get('media_type') or '').strip()
    category = (request.args.get('category') or '').strip()

    if media_type:
        query = query.filter(MediaAsset.media_type == media_type)
    if category:
        query = query.filter(MediaAsset.category == category)

    assets = query.order_by(MediaAsset.created_at.desc()).all()
    return jsonify({'items': serialize_media_collection(assets)})


@api_bp.route('/media-assets', methods=['POST'])
@login_required
@tenant_required
def create_media_asset_endpoint():
    file = request.files.get('file')
    source_url = request.form.get('source_url')

    if (not file or not file.filename) and not (source_url and source_url.strip()):
        return jsonify({'error': 'Provide an image upload or a source URL.'}), 400

    try:
        asset = create_media_asset(
            title=request.form.get('title', ''),
            description=request.form.get('description'),
            category=request.form.get('category'),
            media_type=request.form.get('media_type'),
            file=file if file and file.filename else None,
            source_url=source_url,
            alt_text=request.form.get('alt_text'),
            uploaded_by_user_id=getattr(current_user, 'id', None),
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({'item': serialize_media_asset(asset)}), 201


@api_bp.route('/media-assets/<asset_id>', methods=['GET'])
@login_required
@tenant_required
def get_media_asset(asset_id: str):
    asset = org_query(MediaAsset).filter_by(id=asset_id).first_or_404()
    return jsonify({'item': serialize_media_asset(asset)})


@api_bp.route('/media-assets/<asset_id>', methods=['DELETE'])
@login_required
@tenant_required
def delete_media_asset_endpoint(asset_id: str):
    asset = org_query(MediaAsset).filter_by(id=asset_id).first_or_404()
    delete_media_asset(asset)
    return jsonify({'success': True})


# ============================================================================
# CRUD ENDPOINTS - Teams, Players, Coaches, Referees, Venues, Sponsors, Transactions
# ============================================================================

from slms.auth import admin_required
from slms.services.crud import CRUDService
from slms.models import Player, Coach, CoachAssignment, Referee, GameOfficials, Sponsor, Transaction, Venue


# Serializers
def serialize_player(player: Player) -> dict:
    return {
        'id': player.id,
        'first_name': player.first_name,
        'last_name': player.last_name,
        'email': player.email,
        'jersey_number': player.jersey_number,
        'birthdate': player.birthdate.isoformat() if player.birthdate else None,
        'team_id': player.team_id,
        'created_at': player.created_at.isoformat() if player.created_at else None,
    }


def serialize_coach(coach: Coach) -> dict:
    return {
        'id': coach.id,
        'first_name': coach.first_name,
        'last_name': coach.last_name,
        'email': coach.email,
        'phone': coach.phone,
        'bio': coach.bio,
        'certification_level': coach.certification_level,
        'years_experience': coach.years_experience,
        'is_active': coach.is_active,
        'created_at': coach.created_at.isoformat() if coach.created_at else None,
    }


def serialize_referee(referee: Referee) -> dict:
    return {
        'id': referee.id,
        'first_name': referee.first_name,
        'last_name': referee.last_name,
        'email': referee.email,
        'phone': referee.phone,
        'certification_level': referee.certification_level,
        'license_number': referee.license_number,
        'is_active': referee.is_active,
        'created_at': referee.created_at.isoformat() if referee.created_at else None,
    }


def serialize_sponsor(sponsor: Sponsor) -> dict:
    return {
        'id': sponsor.id,
        'name': sponsor.name,
        'contact_name': sponsor.contact_name,
        'contact_email': sponsor.contact_email,
        'contact_phone': sponsor.contact_phone,
        'website_url': sponsor.website_url,
        'logo_url': sponsor.logo_url,
        'tier': sponsor.tier,
        'contract_start': sponsor.contract_start.isoformat() if sponsor.contract_start else None,
        'contract_end': sponsor.contract_end.isoformat() if sponsor.contract_end else None,
        'sponsorship_amount': sponsor.sponsorship_amount,
        'benefits': sponsor.benefits,
        'is_active': sponsor.is_active,
        'team_id': sponsor.team_id,
        'created_at': sponsor.created_at.isoformat() if sponsor.created_at else None,
    }


def serialize_transaction(txn: Transaction) -> dict:
    return {
        'id': txn.id,
        'transaction_date': txn.transaction_date.isoformat() if txn.transaction_date else None,
        'category': txn.category,
        'description': txn.description,
        'amount': txn.amount,
        'payment_method': txn.payment_method,
        'reference_number': txn.reference_number,
        'notes': txn.notes,
        'team_id': txn.team_id,
        'registration_id': txn.registration_id,
        'sponsor_id': txn.sponsor_id,
        'created_at': txn.created_at.isoformat() if txn.created_at else None,
    }


def serialize_venue(venue: Venue) -> dict:
    return {
        'id': venue.id,
        'name': venue.name,
        'address': venue.address,
        'city': venue.city,
        'timezone': venue.timezone,
        'court_label': venue.court_label,
        'open_time': venue.open_time,
        'close_time': venue.close_time,
        'created_at': venue.created_at.isoformat() if venue.created_at else None,
    }


# ============================================================================
# TEAMS
# ============================================================================

@api_bp.route('/teams-crud', methods=['GET'])
@tenant_required
def list_teams_crud():
    """List all teams (CRUD version)."""
    season_id = request.args.get('season_id')
    filters = {'season_id': season_id} if season_id else None

    teams = CRUDService(Team).list_all(filters=filters, order_by=Team.name)
    return jsonify({'teams': [serialize_team(t) for t in teams]})


@api_bp.route('/teams-crud', methods=['POST'])
@admin_required
@tenant_required
def create_team_crud():
    """Create a new team."""
    team, error = CRUDService(Team).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'team': serialize_team(team)}), 201


@api_bp.route('/teams-crud/<team_id>', methods=['GET'])
@tenant_required
def get_team_crud(team_id: str):
    """Get a single team."""
    team = CRUDService(Team).get_by_id(team_id)
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    return jsonify({'team': serialize_team(team)})


@api_bp.route('/teams-crud/<team_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_team_crud(team_id: str):
    """Update a team."""
    success, error = CRUDService(Team).update(team_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    team = CRUDService(Team).get_by_id(team_id)
    return jsonify({'team': serialize_team(team)})


@api_bp.route('/teams-crud/<team_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_team_crud(team_id: str):
    """Delete a team."""
    success, error = CRUDService(Team).delete(team_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


@api_bp.route('/teams-crud/bulk', methods=['POST'])
@admin_required
@tenant_required
def bulk_create_teams_crud():
    """Bulk create teams."""
    items = request.json.get('teams', [])
    created, errors = CRUDService(Team).bulk_create(items, user=current_user)
    return jsonify({
        'created': [serialize_team(t) for t in created],
        'errors': errors
    }), 201 if not errors else 207


# ============================================================================
# PLAYERS
# ============================================================================

@api_bp.route('/players', methods=['GET'])
@tenant_required
def list_players():
    """List all players."""
    team_id = request.args.get('team_id')
    filters = {'team_id': team_id} if team_id else None

    players = CRUDService(Player).list_all(filters=filters, order_by=Player.last_name)
    return jsonify({'players': [serialize_player(p) for p in players]})


@api_bp.route('/players', methods=['POST'])
@admin_required
@tenant_required
def create_player():
    """Create a new player."""
    player, error = CRUDService(Player).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'player': serialize_player(player)}), 201


@api_bp.route('/players/<player_id>', methods=['GET'])
@tenant_required
def get_player(player_id: str):
    """Get a single player."""
    player = CRUDService(Player).get_by_id(player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    return jsonify({'player': serialize_player(player)})


@api_bp.route('/players/<player_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_player(player_id: str):
    """Update a player."""
    success, error = CRUDService(Player).update(player_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    player = CRUDService(Player).get_by_id(player_id)
    return jsonify({'player': serialize_player(player)})


@api_bp.route('/players/<player_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_player(player_id: str):
    """Delete a player."""
    success, error = CRUDService(Player).delete(player_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


@api_bp.route('/players/bulk', methods=['POST'])
@admin_required
@tenant_required
def bulk_create_players():
    """Bulk create players."""
    items = request.json.get('players', [])
    created, errors = CRUDService(Player).bulk_create(items, user=current_user)
    return jsonify({
        'created': [serialize_player(p) for p in created],
        'errors': errors
    }), 201 if not errors else 207


@api_bp.route('/players/bulk', methods=['PUT'])
@admin_required
@tenant_required
def bulk_update_players():
    """Bulk update players."""
    updates = request.json.get('updates', {})
    count, errors = CRUDService(Player).bulk_update(updates, user=current_user)
    return jsonify({'updated': count, 'errors': errors})


@api_bp.route('/players/bulk', methods=['DELETE'])
@admin_required
@tenant_required
def bulk_delete_players():
    """Bulk delete players."""
    ids = request.json.get('player_ids', [])
    count, errors = CRUDService(Player).bulk_delete(ids, user=current_user)
    return jsonify({'deleted': count, 'errors': errors})


# ============================================================================
# COACHES
# ============================================================================

@api_bp.route('/coaches', methods=['GET'])
@tenant_required
def list_coaches():
    """List all coaches."""
    coaches = CRUDService(Coach).list_all(order_by=Coach.last_name)
    return jsonify({'coaches': [serialize_coach(c) for c in coaches]})


@api_bp.route('/coaches', methods=['POST'])
@admin_required
@tenant_required
def create_coach():
    """Create a new coach."""
    coach, error = CRUDService(Coach).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'coach': serialize_coach(coach)}), 201


@api_bp.route('/coaches/<coach_id>', methods=['GET'])
@tenant_required
def get_coach(coach_id: str):
    """Get a single coach."""
    coach = CRUDService(Coach).get_by_id(coach_id)
    if not coach:
        return jsonify({'error': 'Coach not found'}), 404
    return jsonify({'coach': serialize_coach(coach)})


@api_bp.route('/coaches/<coach_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_coach(coach_id: str):
    """Update a coach."""
    success, error = CRUDService(Coach).update(coach_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    coach = CRUDService(Coach).get_by_id(coach_id)
    return jsonify({'coach': serialize_coach(coach)})


@api_bp.route('/coaches/<coach_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_coach(coach_id: str):
    """Delete a coach."""
    success, error = CRUDService(Coach).delete(coach_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


# ============================================================================
# REFEREES
# ============================================================================

@api_bp.route('/referees', methods=['GET'])
@tenant_required
def list_referees():
    """List all referees."""
    referees = CRUDService(Referee).list_all(order_by=Referee.last_name)
    return jsonify({'referees': [serialize_referee(r) for r in referees]})


@api_bp.route('/referees', methods=['POST'])
@admin_required
@tenant_required
def create_referee():
    """Create a new referee."""
    referee, error = CRUDService(Referee).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'referee': serialize_referee(referee)}), 201


@api_bp.route('/referees/<referee_id>', methods=['GET'])
@tenant_required
def get_referee(referee_id: str):
    """Get a single referee."""
    referee = CRUDService(Referee).get_by_id(referee_id)
    if not referee:
        return jsonify({'error': 'Referee not found'}), 404
    return jsonify({'referee': serialize_referee(referee)})


@api_bp.route('/referees/<referee_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_referee(referee_id: str):
    """Update a referee."""
    success, error = CRUDService(Referee).update(referee_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    referee = CRUDService(Referee).get_by_id(referee_id)
    return jsonify({'referee': serialize_referee(referee)})


@api_bp.route('/referees/<referee_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_referee(referee_id: str):
    """Delete a referee."""
    success, error = CRUDService(Referee).delete(referee_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


# ============================================================================
# VENUES
# ============================================================================

@api_bp.route('/venues', methods=['GET'])
@tenant_required
def list_venues():
    """List all venues."""
    venues = CRUDService(Venue).list_all(order_by=Venue.name)
    return jsonify({'venues': [serialize_venue(v) for v in venues]})


@api_bp.route('/venues', methods=['POST'])
@admin_required
@tenant_required
def create_venue():
    """Create a new venue."""
    venue, error = CRUDService(Venue).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'venue': serialize_venue(venue)}), 201


@api_bp.route('/venues/<venue_id>', methods=['GET'])
@tenant_required
def get_venue(venue_id: str):
    """Get a single venue."""
    venue = CRUDService(Venue).get_by_id(venue_id)
    if not venue:
        return jsonify({'error': 'Venue not found'}), 404
    return jsonify({'venue': serialize_venue(venue)})


@api_bp.route('/venues/<venue_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_venue(venue_id: str):
    """Update a venue."""
    success, error = CRUDService(Venue).update(venue_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    venue = CRUDService(Venue).get_by_id(venue_id)
    return jsonify({'venue': serialize_venue(venue)})


@api_bp.route('/venues/<venue_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_venue(venue_id: str):
    """Delete a venue."""
    success, error = CRUDService(Venue).delete(venue_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


# ============================================================================
# SPONSORS
# ============================================================================

@api_bp.route('/sponsors', methods=['GET'])
@tenant_required
def list_sponsors():
    """List all sponsors."""
    tier = request.args.get('tier')
    team_id = request.args.get('team_id')
    filters = {}
    if tier:
        filters['tier'] = tier
    if team_id:
        filters['team_id'] = team_id

    sponsors = CRUDService(Sponsor).list_all(filters=filters if filters else None, order_by=Sponsor.name)
    return jsonify({'sponsors': [serialize_sponsor(s) for s in sponsors]})


@api_bp.route('/sponsors', methods=['POST'])
@admin_required
@tenant_required
def create_sponsor():
    """Create a new sponsor."""
    sponsor, error = CRUDService(Sponsor).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'sponsor': serialize_sponsor(sponsor)}), 201


@api_bp.route('/sponsors/<sponsor_id>', methods=['GET'])
@tenant_required
def get_sponsor(sponsor_id: str):
    """Get a single sponsor."""
    sponsor = CRUDService(Sponsor).get_by_id(sponsor_id)
    if not sponsor:
        return jsonify({'error': 'Sponsor not found'}), 404
    return jsonify({'sponsor': serialize_sponsor(sponsor)})


@api_bp.route('/sponsors/<sponsor_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_sponsor(sponsor_id: str):
    """Update a sponsor."""
    success, error = CRUDService(Sponsor).update(sponsor_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    sponsor = CRUDService(Sponsor).get_by_id(sponsor_id)
    return jsonify({'sponsor': serialize_sponsor(sponsor)})


@api_bp.route('/sponsors/<sponsor_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_sponsor(sponsor_id: str):
    """Delete a sponsor."""
    success, error = CRUDService(Sponsor).delete(sponsor_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


# ============================================================================
# TRANSACTIONS (Finance)
# ============================================================================

@api_bp.route('/transactions', methods=['GET'])
@admin_required
@tenant_required
def list_transactions():
    """List all transactions."""
    category = request.args.get('category')
    filters = {'category': category} if category else None

    from slms.models import Transaction as TxnModel
    transactions = CRUDService(TxnModel).list_all(
        filters=filters,
        order_by=TxnModel.transaction_date.desc()
    )
    return jsonify({'transactions': [serialize_transaction(t) for t in transactions]})


@api_bp.route('/transactions', methods=['POST'])
@admin_required
@tenant_required
def create_transaction():
    """Create a new transaction."""
    from slms.models import Transaction as TxnModel
    transaction, error = CRUDService(TxnModel).create(request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'transaction': serialize_transaction(transaction)}), 201


@api_bp.route('/transactions/<transaction_id>', methods=['GET'])
@admin_required
@tenant_required
def get_transaction(transaction_id: str):
    """Get a single transaction."""
    from slms.models import Transaction as TxnModel
    transaction = CRUDService(TxnModel).get_by_id(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    return jsonify({'transaction': serialize_transaction(transaction)})


@api_bp.route('/transactions/<transaction_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_transaction(transaction_id: str):
    """Update a transaction."""
    from slms.models import Transaction as TxnModel
    success, error = CRUDService(TxnModel).update(transaction_id, request.json, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    transaction = CRUDService(TxnModel).get_by_id(transaction_id)
    return jsonify({'transaction': serialize_transaction(transaction)})


@api_bp.route('/transactions/<transaction_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_transaction(transaction_id: str):
    """Delete a transaction."""
    from slms.models import Transaction as TxnModel
    success, error = CRUDService(TxnModel).delete(transaction_id, user=current_user)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'success': True})


@api_bp.route('/transactions/summary', methods=['GET'])
@admin_required
@tenant_required
def transaction_summary():
    """Get financial summary."""
    from slms.models import Transaction as TxnModel
    from slms.blueprints.common.tenant import org_query
    from sqlalchemy import func

    # Get totals by category
    result = org_query(TxnModel).with_entities(
        TxnModel.category,
        func.sum(TxnModel.amount).label('total')
    ).group_by(TxnModel.category).all()

    summary = {category: total for category, total in result}

    # Calculate income vs expenses
    total_income = sum(total for total in summary.values() if total > 0)
    total_expenses = sum(total for total in summary.values() if total < 0)

    return jsonify({
        'summary': summary,
        'total_income': total_income,
        'total_expenses': abs(total_expenses),
        'net': total_income + total_expenses
    })


# ============================================================================
# CONTENT ASSETS (for Content Management System)
# ============================================================================

@api_bp.route('/upload-asset', methods=['POST'])
@login_required
@tenant_required
def upload_content_asset():
    """Upload asset for content management system."""
    from slms.services.content import AssetService
    from slms.services.storage import upload_file
    import os
    from datetime import datetime

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error': 'No file provided'}), 400

    # Get folder from form data
    folder = request.form.get('folder', '').strip()

    # Determine asset type based on mime type
    mime_type = file.content_type or 'application/octet-stream'
    if mime_type.startswith('image/'):
        asset_type = 'image'
    elif mime_type.startswith('video/'):
        asset_type = 'video'
    else:
        asset_type = 'document'

    try:
        # Upload file to storage
        upload_result = upload_file(file, folder='content_assets')

        # Get file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        # Create asset record
        asset = AssetService.create_asset(
            org_id=current_user.org_id,
            uploaded_by_id=current_user.id,
            filename=upload_result['filename'],
            original_filename=file.filename,
            storage_path=upload_result['path'],
            public_url=upload_result.get('public_url'),
            asset_type=asset_type,
            mime_type=mime_type,
            file_size=file_size,
            folder=folder if folder else None
        )

        return jsonify({
            'id': asset.id,
            'filename': asset.filename,
            'public_url': asset.public_url,
            'asset_type': asset.asset_type,
            'file_size': asset.file_size
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# EXPORT / IMPORT ENDPOINTS
# ============================================================================

from slms.services.export_import import ExportImportService
from flask import Response, make_response

@api_bp.route('/export/<model_name>', methods=['GET'])
@admin_required
@tenant_required
def export_data(model_name: str):
    """Export domain objects to CSV or XLSX."""
    format = request.args.get('format', 'csv').lower()

    if format not in ['csv', 'xlsx']:
        return jsonify({'error': 'Invalid format. Use csv or xlsx'}), 400

    try:
        # Get model class
        model_class = ExportImportService.MODEL_MAP.get(model_name)
        if not model_class:
            return jsonify({'error': f'Unknown model: {model_name}'}), 404

        # Build query with org filter
        query = org_query(model_class)

        # Export data
        if format == 'csv':
            content = ExportImportService.export_to_csv(query, model_name)
            response = make_response(content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={model_name}_export.csv'
        else:
            content = ExportImportService.export_to_xlsx(query, model_name)
            response = make_response(content)
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename={model_name}_export.xlsx'

        return response

    except Exception as e:
        current_app.logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/import/<model_name>', methods=['POST'])
@admin_required
@tenant_required
def import_data(model_name: str):
    """Import domain objects from CSV or XLSX."""
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    update_existing = request.form.get('update_existing', 'false').lower() == 'true'

    try:
        # Determine format from filename
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            content = file.read().decode('utf-8')
            created, updated, errors = ExportImportService.import_from_csv(
                content, model_name, current_user.org_id, update_existing
            )
        elif filename.endswith('.xlsx'):
            file.seek(0)
            created, updated, errors = ExportImportService.import_from_xlsx(
                file, model_name, current_user.org_id, update_existing
            )
        else:
            return jsonify({'error': 'Invalid file format. Use .csv or .xlsx'}), 400

        return jsonify({
            'created': created,
            'updated': updated,
            'errors': errors,
            'success': len(errors) == 0
        })

    except Exception as e:
        current_app.logger.error(f"Import error: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/export-template/<model_name>', methods=['GET'])
@admin_required
@tenant_required
def get_export_template(model_name: str):
    """Get empty template for import."""
    format = request.args.get('format', 'csv').lower()

    if format not in ['csv', 'xlsx']:
        return jsonify({'error': 'Invalid format. Use csv or xlsx'}), 400

    try:
        content = ExportImportService.get_export_template(model_name, format)

        if format == 'csv':
            response = make_response(content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={model_name}_template.csv'
        else:
            response = make_response(content)
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = f'attachment; filename={model_name}_template.xlsx'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WEBHOOK MANAGEMENT ENDPOINTS
# ============================================================================

from slms.services.webhooks import WebhookService, Webhook

@api_bp.route('/webhooks', methods=['GET'])
@admin_required
@tenant_required
def list_webhooks():
    """List all webhooks for the organization."""
    webhooks = org_query(Webhook).all()

    return jsonify({
        'webhooks': [{
            'id': w.id,
            'name': w.name,
            'url': w.url,
            'events': w.events,
            'is_active': w.is_active,
            'success_count': w.success_count,
            'failure_count': w.failure_count,
            'last_triggered_at': w.last_triggered_at.isoformat() if w.last_triggered_at else None,
            'created_at': w.created_at.isoformat()
        } for w in webhooks]
    })


@api_bp.route('/webhooks', methods=['POST'])
@admin_required
@tenant_required
def create_webhook():
    """Create a new webhook."""
    data = request.json
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    events = data.get('events', [])

    if not name or not url or not events:
        return jsonify({'error': 'name, url, and events are required'}), 400

    try:
        webhook = WebhookService.create_webhook(
            org_id=current_user.org_id,
            name=name,
            url=url,
            events=events,
            custom_headers=data.get('custom_headers')
        )

        return jsonify({
            'id': webhook.id,
            'name': webhook.name,
            'url': webhook.url,
            'secret': webhook.secret,
            'events': webhook.events,
            'is_active': webhook.is_active
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/webhooks/<webhook_id>', methods=['GET'])
@admin_required
@tenant_required
def get_webhook(webhook_id: str):
    """Get webhook details."""
    webhook = org_query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    stats = WebhookService.get_webhook_stats(webhook_id)

    return jsonify({
        'id': webhook.id,
        'name': webhook.name,
        'url': webhook.url,
        'secret': webhook.secret,
        'events': webhook.events,
        'is_active': webhook.is_active,
        'retry_count': webhook.retry_count,
        'timeout': webhook.timeout,
        'custom_headers': webhook.custom_headers,
        'stats': stats,
        'created_at': webhook.created_at.isoformat()
    })


@api_bp.route('/webhooks/<webhook_id>', methods=['PUT'])
@admin_required
@tenant_required
def update_webhook(webhook_id: str):
    """Update webhook settings."""
    webhook = org_query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    data = request.json
    allowed_updates = ['name', 'url', 'events', 'is_active', 'retry_count', 'timeout', 'custom_headers']

    updates = {k: v for k, v in data.items() if k in allowed_updates}

    webhook = WebhookService.update_webhook(webhook_id, **updates)

    return jsonify({
        'id': webhook.id,
        'name': webhook.name,
        'url': webhook.url,
        'events': webhook.events,
        'is_active': webhook.is_active
    })


@api_bp.route('/webhooks/<webhook_id>', methods=['DELETE'])
@admin_required
@tenant_required
def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    webhook = org_query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    WebhookService.delete_webhook(webhook_id)

    return jsonify({'success': True})


@api_bp.route('/webhooks/<webhook_id>/test', methods=['POST'])
@admin_required
@tenant_required
def test_webhook(webhook_id: str):
    """Send a test event to webhook."""
    webhook = org_query(Webhook).filter_by(id=webhook_id).first()
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    from slms.services.webhooks import WebhookEventType
    from datetime import datetime, timezone

    # Send test event
    test_payload = {
        'test': True,
        'message': 'This is a test webhook event',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    WebhookService._queue_delivery(webhook, 'test.event', test_payload)

    return jsonify({'message': 'Test event sent'})


@api_bp.route('/webhook-events', methods=['GET'])
@admin_required
@tenant_required
def list_webhook_events():
    """List available webhook event types."""
    from slms.services.webhooks import WebhookEventType

    events = [{
        'value': event.value,
        'name': event.name,
        'category': event.value.split('.')[0]
    } for event in WebhookEventType]

    return jsonify({'events': events})


# ============================================================================
# UNIVERSAL SEARCH ENDPOINTS
# ============================================================================

from slms.services.search import SearchService

@api_bp.route('/search', methods=['GET'])
@tenant_required
def universal_search():
    """Universal search across all entity types."""
    query = request.args.get('q', '').strip()
    types = request.args.getlist('types')  # e.g., ?types=teams&types=players
    limit = int(request.args.get('limit', 10))

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    results = SearchService.search(
        query=query,
        org_id=current_user.org_id,
        types=types if types else None,
        limit=limit
    )

    return jsonify({'results': results, 'query': query})


@api_bp.route('/search/typeahead', methods=['GET'])
@tenant_required
def search_typeahead():
    """Quick typeahead search for autocomplete."""
    query = request.args.get('q', '').strip()
    types = request.args.getlist('types')
    limit = int(request.args.get('limit', 5))

    if not query or len(query) < 2:
        return jsonify({'results': []})

    results = SearchService.typeahead(
        query=query,
        org_id=current_user.org_id,
        types=types if types else None,
        limit=limit
    )

    return jsonify({'results': results})


@api_bp.route('/search/<entity_type>', methods=['GET'])
@tenant_required
def advanced_search(entity_type: str):
    """Advanced search with filters and pagination."""
    # Get filters from query params
    filters = {}
    for key, value in request.args.items():
        if key not in ['page', 'per_page', 'sort_by', 'sort_order']:
            # Parse filter format: field_op (e.g., age_gt=18)
            if '_' in key:
                parts = key.rsplit('_', 1)
                if len(parts) == 2 and parts[1] in ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'contains', 'in']:
                    field, op = parts
                    if field not in filters:
                        filters[field] = {}
                    filters[field][op] = value
                else:
                    filters[key] = value
            else:
                filters[key] = value

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order', 'asc')

    try:
        result = SearchService.advanced_search(
            org_id=current_user.org_id,
            entity_type=entity_type,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/search/<entity_type>/filters', methods=['GET'])
@tenant_required
def get_search_filters(entity_type: str):
    """Get available filters for an entity type."""
    filters = SearchService.get_filters_for_type(entity_type)

    if not filters:
        return jsonify({'error': f'Unknown entity type: {entity_type}'}), 404

    return jsonify({'filters': filters})


@api_bp.route('/search/<entity_type>/<entity_id>/related', methods=['GET'])
@tenant_required
def get_related_content(entity_type: str, entity_id: str):
    """Get related content for an entity."""
    from slms.services.search import get_related_content as get_related

    related = get_related(entity_type, entity_id, current_user.org_id)

    # Serialize related content
    serialized = {}
    for key, items in related.items():
        if isinstance(items, list):
            serialized[key] = [
                {
                    'id': item.id,
                    'display': getattr(item, 'name', None) or f"{getattr(item, 'first_name', '')} {getattr(item, 'last_name', '')}".strip(),
                }
                for item in items
            ]
        elif items:  # Single object
            serialized[key] = {
                'id': items.id,
                'display': getattr(items, 'name', None) or f"{getattr(items, 'first_name', '')} {getattr(items, 'last_name', '')}".strip(),
            }

    return jsonify({'related': serialized})
