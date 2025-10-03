"""League lifecycle management blueprint."""
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from slms.blueprints.common.tenant import tenant_required
from slms.models.models import League, Season, LeagueStatus, SeasonStatus, SportType
from slms.services.league import LeagueService, SeasonService
from slms.services.audit import log_admin_action

league_mgmt_bp = Blueprint('league_mgmt', __name__, url_prefix='/league-management')


# ============= League Management Routes =============

@league_mgmt_bp.route('/')
@login_required
@tenant_required
def index():
    """League management dashboard."""
    return render_template('league_management.html')


@league_mgmt_bp.route('/api/leagues', methods=['GET'])
@login_required
@tenant_required
def list_leagues():
    """List all leagues for the organization."""
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    status_filter = request.args.get('status')

    status = None
    if status_filter:
        try:
            status = LeagueStatus(status_filter)
        except ValueError:
            pass

    leagues = LeagueService.list_leagues(
        org_id=current_user.org_id,
        status=status,
        include_archived=include_archived,
    )

    return jsonify([{
        'id': league.id,
        'name': league.name,
        'sport': league.sport.value,
        'description': league.description,
        'status': league.status.value,
        'timezone': league.timezone,
        'archived_at': league.archived_at.isoformat() if league.archived_at else None,
        'created_at': league.created_at.isoformat(),
        'settings': league.settings or {},
    } for league in leagues])


@league_mgmt_bp.route('/api/leagues', methods=['POST'])
@login_required
@tenant_required
def create_league():
    """Create a new league."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    name = data.get('name', '').strip()
    sport = data.get('sport', '').strip()

    if not name or not sport:
        return jsonify({'error': 'Name and sport are required'}), 400

    try:
        sport_enum = SportType(sport)
    except ValueError:
        return jsonify({'error': f'Invalid sport type: {sport}'}), 400

    league = LeagueService.create_league(
        org_id=current_user.org_id,
        name=name,
        sport=sport_enum,
        description=data.get('description'),
        league_timezone=data.get('timezone', 'UTC'),
        settings=data.get('settings', {}),
    )

    log_admin_action(
        user=current_user,
        action='create',
        entity_type='league',
        entity_id=league.id,
        metadata={'name': league.name, 'sport': league.sport.value},
    )

    return jsonify({
        'id': league.id,
        'name': league.name,
        'sport': league.sport.value,
        'description': league.description,
        'status': league.status.value,
        'timezone': league.timezone,
        'created_at': league.created_at.isoformat(),
    }), 201


@league_mgmt_bp.route('/api/leagues/<league_id>', methods=['GET'])
@login_required
@tenant_required
def get_league(league_id):
    """Get league details."""
    league = LeagueService.get_league(league_id, current_user.org_id)
    if not league:
        return jsonify({'error': 'League not found'}), 404

    return jsonify({
        'id': league.id,
        'name': league.name,
        'sport': league.sport.value,
        'description': league.description,
        'status': league.status.value,
        'timezone': league.timezone,
        'archived_at': league.archived_at.isoformat() if league.archived_at else None,
        'created_at': league.created_at.isoformat(),
        'settings': league.settings or {},
    })


@league_mgmt_bp.route('/api/leagues/<league_id>', methods=['PUT'])
@login_required
@tenant_required
def update_league(league_id):
    """Update league details."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    updates = {}

    if 'name' in data:
        updates['name'] = data['name'].strip()
    if 'description' in data:
        updates['description'] = data['description']
    if 'sport' in data:
        try:
            updates['sport'] = SportType(data['sport'])
        except ValueError:
            return jsonify({'error': f'Invalid sport type: {data["sport"]}'}), 400
    if 'timezone' in data:
        updates['timezone'] = data['timezone']
    if 'settings' in data:
        updates['settings'] = data['settings']

    league = LeagueService.update_league(league_id, current_user.org_id, **updates)
    if not league:
        return jsonify({'error': 'League not found'}), 404

    log_admin_action(
        user=current_user,
        action='update',
        entity_type='league',
        entity_id=league.id,
        metadata={'updates': list(updates.keys())},
    )

    return jsonify({
        'id': league.id,
        'name': league.name,
        'sport': league.sport.value,
        'description': league.description,
        'status': league.status.value,
        'timezone': league.timezone,
    })


@league_mgmt_bp.route('/api/leagues/<league_id>/activate', methods=['POST'])
@login_required
@tenant_required
def activate_league(league_id):
    """Activate a league."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    league = LeagueService.activate_league(league_id, current_user.org_id)
    if not league:
        return jsonify({'error': 'League not found'}), 404

    log_admin_action(
        user=current_user,
        action='activate',
        entity_type='league',
        entity_id=league.id,
    )

    return jsonify({'status': league.status.value})


@league_mgmt_bp.route('/api/leagues/<league_id>/archive', methods=['POST'])
@login_required
@tenant_required
def archive_league(league_id):
    """Archive a league and all its seasons."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    league = LeagueService.archive_league(league_id, current_user.org_id)
    if not league:
        return jsonify({'error': 'League not found'}), 404

    log_admin_action(
        user=current_user,
        action='archive',
        entity_type='league',
        entity_id=league.id,
    )

    return jsonify({'status': league.status.value, 'archived_at': league.archived_at.isoformat()})


@league_mgmt_bp.route('/api/leagues/<league_id>/restore', methods=['POST'])
@login_required
@tenant_required
def restore_league(league_id):
    """Restore an archived league."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    league = LeagueService.restore_league(league_id, current_user.org_id)
    if not league:
        return jsonify({'error': 'League not found'}), 404

    log_admin_action(
        user=current_user,
        action='restore',
        entity_type='league',
        entity_id=league.id,
    )

    return jsonify({'status': league.status.value})


@league_mgmt_bp.route('/api/leagues/<league_id>', methods=['DELETE'])
@login_required
@tenant_required
def delete_league(league_id):
    """Delete a league (draft only)."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    if not LeagueService.delete_league(league_id, current_user.org_id):
        return jsonify({'error': 'League not found or cannot be deleted'}), 400

    log_admin_action(
        user=current_user,
        action='delete',
        entity_type='league',
        entity_id=league_id,
    )

    return '', 204


# ============= Season Management Routes =============

@league_mgmt_bp.route('/api/leagues/<league_id>/seasons', methods=['GET'])
@login_required
@tenant_required
def list_seasons(league_id):
    """List all seasons for a league."""
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    status_filter = request.args.get('status')

    status = None
    if status_filter:
        try:
            status = SeasonStatus(status_filter)
        except ValueError:
            pass

    seasons = SeasonService.list_seasons(
        org_id=current_user.org_id,
        league_id=league_id,
        status=status,
        include_archived=include_archived,
    )

    return jsonify([{
        'id': season.id,
        'name': season.name,
        'league_id': season.league_id,
        'start_date': season.start_date.isoformat() if season.start_date else None,
        'end_date': season.end_date.isoformat() if season.end_date else None,
        'status': season.status.value,
        'is_active': season.is_active,
        'timezone': season.timezone,
        'rules': season.rules or {},
        'registration_open': season.registration_open,
        'registration_deadline': season.registration_deadline.isoformat() if season.registration_deadline else None,
        'off_season_start': season.off_season_start.isoformat() if season.off_season_start else None,
        'off_season_end': season.off_season_end.isoformat() if season.off_season_end else None,
        'off_season_message': season.off_season_message,
        'created_at': season.created_at.isoformat(),
    } for season in seasons])


@league_mgmt_bp.route('/api/leagues/<league_id>/seasons', methods=['POST'])
@login_required
@tenant_required
def create_season(league_id):
    """Create a new season."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    season = SeasonService.create_season(
        org_id=current_user.org_id,
        league_id=league_id,
        name=name,
        start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
        rules=data.get('rules', {}),
        season_timezone=data.get('timezone'),
        registration_open=data.get('registration_open', False),
        registration_mode=data.get('registration_mode'),
        registration_deadline=datetime.fromisoformat(data['registration_deadline']) if data.get('registration_deadline') else None,
        fee_cents=data.get('fee_cents'),
        currency=data.get('currency', 'CAD'),
        default_game_length_minutes=data.get('default_game_length_minutes'),
    )

    if not season:
        return jsonify({'error': 'League not found'}), 404

    log_admin_action(
        user=current_user,
        action='create',
        entity_type='season',
        entity_id=season.id,
        metadata={'name': season.name, 'league_id': league_id},
    )

    return jsonify({
        'id': season.id,
        'name': season.name,
        'status': season.status.value,
        'created_at': season.created_at.isoformat(),
    }), 201


@league_mgmt_bp.route('/api/seasons/<season_id>', methods=['GET'])
@login_required
@tenant_required
def get_season(season_id):
    """Get season details."""
    season = SeasonService.get_season(season_id, current_user.org_id)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    return jsonify({
        'id': season.id,
        'name': season.name,
        'league_id': season.league_id,
        'start_date': season.start_date.isoformat() if season.start_date else None,
        'end_date': season.end_date.isoformat() if season.end_date else None,
        'status': season.status.value,
        'is_active': season.is_active,
        'timezone': season.timezone,
        'rules': season.rules or {},
        'registration_open': season.registration_open,
        'registration_mode': season.registration_mode.value if season.registration_mode else None,
        'registration_deadline': season.registration_deadline.isoformat() if season.registration_deadline else None,
        'fee_cents': season.fee_cents,
        'currency': season.currency,
        'default_game_length_minutes': season.default_game_length_minutes,
        'off_season_start': season.off_season_start.isoformat() if season.off_season_start else None,
        'off_season_end': season.off_season_end.isoformat() if season.off_season_end else None,
        'off_season_message': season.off_season_message,
        'created_at': season.created_at.isoformat(),
    })


@league_mgmt_bp.route('/api/seasons/<season_id>', methods=['PUT'])
@login_required
@tenant_required
def update_season(season_id):
    """Update season details."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    updates = {}

    # Map fields from request
    field_mapping = {
        'name': 'name',
        'start_date': 'start_date',
        'end_date': 'end_date',
        'timezone': 'timezone',
        'rules': 'rules',
        'registration_open': 'registration_open',
        'registration_mode': 'registration_mode',
        'registration_deadline': 'registration_deadline',
        'fee_cents': 'fee_cents',
        'currency': 'currency',
        'default_game_length_minutes': 'default_game_length_minutes',
        'off_season_start': 'off_season_start',
        'off_season_end': 'off_season_end',
        'off_season_message': 'off_season_message',
    }

    for api_field, model_field in field_mapping.items():
        if api_field in data:
            value = data[api_field]
            # Handle date/datetime conversions
            if api_field in ['start_date', 'end_date', 'off_season_start', 'off_season_end'] and value:
                value = datetime.fromisoformat(value).date() if api_field in ['off_season_start', 'off_season_end'] else datetime.fromisoformat(value)
            elif api_field == 'registration_deadline' and value:
                value = datetime.fromisoformat(value)
            updates[model_field] = value

    season = SeasonService.update_season(season_id, current_user.org_id, **updates)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='update',
        entity_type='season',
        entity_id=season.id,
        metadata={'updates': list(updates.keys())},
    )

    return jsonify({'id': season.id, 'status': season.status.value})


@league_mgmt_bp.route('/api/seasons/<season_id>/activate', methods=['POST'])
@login_required
@tenant_required
def activate_season(season_id):
    """Activate a season."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    season = SeasonService.activate_season(season_id, current_user.org_id)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='activate',
        entity_type='season',
        entity_id=season.id,
    )

    return jsonify({'status': season.status.value, 'is_active': season.is_active})


@league_mgmt_bp.route('/api/seasons/<season_id>/off-season', methods=['POST'])
@login_required
@tenant_required
def set_off_season(season_id):
    """Set season to off-season state."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    message = data.get('message')

    season = SeasonService.set_off_season(season_id, current_user.org_id, message)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='set_off_season',
        entity_type='season',
        entity_id=season.id,
    )

    return jsonify({'status': season.status.value})


@league_mgmt_bp.route('/api/seasons/<season_id>/complete', methods=['POST'])
@login_required
@tenant_required
def complete_season(season_id):
    """Mark season as completed."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    season = SeasonService.complete_season(season_id, current_user.org_id)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='complete',
        entity_type='season',
        entity_id=season.id,
    )

    return jsonify({'status': season.status.value})


@league_mgmt_bp.route('/api/seasons/<season_id>/archive', methods=['POST'])
@login_required
@tenant_required
def archive_season(season_id):
    """Archive a season."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    season = SeasonService.archive_season(season_id, current_user.org_id)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='archive',
        entity_type='season',
        entity_id=season.id,
    )

    return jsonify({'status': season.status.value, 'archived_at': season.archived_at.isoformat()})


@league_mgmt_bp.route('/api/seasons/<season_id>/restore', methods=['POST'])
@login_required
@tenant_required
def restore_season(season_id):
    """Restore an archived season."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    season = SeasonService.restore_season(season_id, current_user.org_id)
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    log_admin_action(
        user=current_user,
        action='restore',
        entity_type='season',
        entity_id=season.id,
    )

    return jsonify({'status': season.status.value})


@league_mgmt_bp.route('/api/seasons/<season_id>', methods=['DELETE'])
@login_required
@tenant_required
def delete_season(season_id):
    """Delete a season (draft only)."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    if not SeasonService.delete_season(season_id, current_user.org_id):
        return jsonify({'error': 'Season not found or cannot be deleted'}), 400

    log_admin_action(
        user=current_user,
        action='delete',
        entity_type='season',
        entity_id=season_id,
    )

    return '', 204
