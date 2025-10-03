"""Live scoring and game console blueprint."""
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from slms.blueprints.common.tenant import tenant_required
from slms.models.models import Game, GameStatus, StatType, PeriodType
from slms.services.live_game import LiveGameService
from slms.services.score_notifications import ScoreNotificationService
from slms.services.audit import log_admin_action

live_scoring_bp = Blueprint('live_scoring', __name__, url_prefix='/live-scoring')


# ============= Live Game Console Routes =============

@live_scoring_bp.route('/console/<game_id>')
@login_required
@tenant_required
def game_console(game_id):
    """Live game console UI."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.get_game_with_details(game_id, current_user.org_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    return render_template('live_game_console.html', game=game)


# ============= Game Control Endpoints =============

@live_scoring_bp.route('/api/games/<game_id>/start', methods=['POST'])
@login_required
@tenant_required
def start_game(game_id):
    """Start a game."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.start_game(game_id, current_user.org_id, current_user.id)
    if not game:
        return jsonify({'error': 'Game not found or already started'}), 400

    ScoreNotificationService.notify_game_start(game)

    log_admin_action(
        user=current_user,
        action='start_game',
        entity_type='game',
        entity_id=game.id
    )

    return jsonify({
        'status': game.status.value,
        'current_period': game.current_period,
        'message': 'Game started successfully'
    })


@live_scoring_bp.route('/api/games/<game_id>/score', methods=['POST'])
@login_required
@tenant_required
def update_score(game_id):
    """Update game score."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    home_score = data.get('home_score')
    away_score = data.get('away_score')

    if home_score is None or away_score is None:
        return jsonify({'error': 'Both home_score and away_score are required'}), 400

    game = LiveGameService.update_score(
        game_id=game_id,
        org_id=current_user.org_id,
        user_id=current_user.id,
        home_score=int(home_score),
        away_score=int(away_score),
        update_type='live_update',
        notes=data.get('notes')
    )

    if not game:
        return jsonify({'error': 'Game not found'}), 404

    ScoreNotificationService.notify_score_update(game)

    return jsonify({
        'home_score': game.home_score,
        'away_score': game.away_score,
        'last_update': game.last_score_update.isoformat() if game.last_score_update else None
    })


@live_scoring_bp.route('/api/games/<game_id>/halftime', methods=['POST'])
@login_required
@tenant_required
def set_halftime(game_id):
    """Set game to halftime."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.set_halftime(game_id, current_user.org_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    return jsonify({'status': game.status.value})


@live_scoring_bp.route('/api/games/<game_id>/resume', methods=['POST'])
@login_required
@tenant_required
def resume_game(game_id):
    """Resume game from halftime."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    period = data.get('period', 2)

    game = LiveGameService.resume_from_halftime(game_id, current_user.org_id, period)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    return jsonify({
        'status': game.status.value,
        'current_period': game.current_period
    })


@live_scoring_bp.route('/api/games/<game_id>/overtime', methods=['POST'])
@login_required
@tenant_required
def start_overtime(game_id):
    """Start overtime period."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.start_overtime(game_id, current_user.org_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    ScoreNotificationService.notify_overtime(game)

    return jsonify({
        'status': game.status.value,
        'overtime_periods': game.overtime_periods,
        'went_to_overtime': game.went_to_overtime
    })


@live_scoring_bp.route('/api/games/<game_id>/end', methods=['POST'])
@login_required
@tenant_required
def end_game(game_id):
    """End game and set to FINAL."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.end_game(game_id, current_user.org_id, current_user.id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    ScoreNotificationService.notify_game_end(game)

    log_admin_action(
        user=current_user,
        action='end_game',
        entity_type='game',
        entity_id=game.id,
        metadata={'final_score': f'{game.home_score}-{game.away_score}'}
    )

    return jsonify({
        'status': game.status.value,
        'final_score': {
            'home': game.home_score,
            'away': game.away_score
        }
    })


# ============= Events & Stats Endpoints =============

@live_scoring_bp.route('/api/games/<game_id>/events', methods=['POST'])
@login_required
@tenant_required
def add_event(game_id):
    """Add a game event."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    event_type = data.get('event_type')

    if not event_type:
        return jsonify({'error': 'event_type is required'}), 400

    period_type = None
    if data.get('period_type'):
        try:
            period_type = PeriodType(data['period_type'])
        except ValueError:
            pass

    event = LiveGameService.add_game_event(
        game_id=game_id,
        org_id=current_user.org_id,
        event_type=event_type,
        team_id=data.get('team_id'),
        player_id=data.get('player_id'),
        period=data.get('period'),
        period_type=period_type,
        game_clock=data.get('game_clock'),
        details=data.get('details', {}),
        description=data.get('description')
    )

    return jsonify({
        'id': event.id,
        'event_type': event.event_type,
        'created_at': event.created_at.isoformat()
    }), 201


@live_scoring_bp.route('/api/games/<game_id>/events', methods=['GET'])
@login_required
@tenant_required
def get_events(game_id):
    """Get all game events."""
    events = LiveGameService.get_game_events(game_id, current_user.org_id)

    return jsonify([{
        'id': e.id,
        'event_type': e.event_type,
        'team_id': e.team_id,
        'player_id': e.player_id,
        'period': e.period,
        'period_type': e.period_type.value if e.period_type else None,
        'game_clock': e.game_clock,
        'description': e.description,
        'details': e.details,
        'created_at': e.created_at.isoformat()
    } for e in events])


@live_scoring_bp.route('/api/games/<game_id>/penalties', methods=['POST'])
@login_required
@tenant_required
def add_penalty(game_id):
    """Record a penalty/foul."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    penalty = LiveGameService.record_penalty(
        game_id=game_id,
        org_id=current_user.org_id,
        team_id=data['team_id'],
        penalty_type=data['penalty_type'],
        player_id=data.get('player_id'),
        period=data.get('period'),
        game_clock=data.get('game_clock'),
        minutes=data.get('minutes'),
        severity=data.get('severity'),
        description=data.get('description'),
        resulted_in_ejection=data.get('resulted_in_ejection', False)
    )

    return jsonify({
        'id': penalty.id,
        'penalty_type': penalty.penalty_type,
        'player_id': penalty.player_id,
        'created_at': penalty.created_at.isoformat()
    }), 201


@live_scoring_bp.route('/api/games/<game_id>/penalties', methods=['GET'])
@login_required
@tenant_required
def get_penalties(game_id):
    """Get all penalties for a game."""
    penalties = LiveGameService.get_penalties(game_id, current_user.org_id)

    return jsonify([{
        'id': p.id,
        'penalty_type': p.penalty_type,
        'team_id': p.team_id,
        'player_id': p.player_id,
        'player_name': f"{p.player.first_name} {p.player.last_name}" if p.player else None,
        'period': p.period,
        'game_clock': p.game_clock,
        'minutes': p.minutes,
        'severity': p.severity,
        'description': p.description,
        'resulted_in_ejection': p.resulted_in_ejection,
        'created_at': p.created_at.isoformat()
    } for p in penalties])


@live_scoring_bp.route('/api/games/<game_id>/stats', methods=['POST'])
@login_required
@tenant_required
def update_stat(game_id):
    """Update player stat."""
    if not current_user.has_role('owner', 'admin', 'scorekeeper'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json

    try:
        stat_type = StatType(data['stat_type'])
    except (ValueError, KeyError):
        return jsonify({'error': 'Invalid stat_type'}), 400

    stat = LiveGameService.update_player_stat(
        game_id=game_id,
        org_id=current_user.org_id,
        player_id=data['player_id'],
        team_id=data['team_id'],
        stat_type=stat_type,
        value=int(data['value'])
    )

    return jsonify({
        'id': stat.id,
        'player_id': stat.player_id,
        'stat_type': stat.stat_type.value,
        'value': stat.value
    })


@live_scoring_bp.route('/api/games/<game_id>/stats', methods=['GET'])
@login_required
@tenant_required
def get_stats(game_id):
    """Get all player stats for a game."""
    stats = LiveGameService.get_player_stats(game_id, current_user.org_id)

    return jsonify([{
        'id': s.id,
        'player_id': s.player_id,
        'player_name': f"{s.player.first_name} {s.player.last_name}",
        'team_id': s.team_id,
        'stat_type': s.stat_type.value,
        'value': s.value
    } for s in stats])


# ============= Reconciliation Endpoints =============

@live_scoring_bp.route('/api/games/<game_id>/reconcile', methods=['POST'])
@login_required
@tenant_required
def reconcile_game(game_id):
    """Reconcile game (confirm final score)."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    game = LiveGameService.reconcile_game(game_id, current_user.org_id, current_user.id)
    if not game:
        return jsonify({'error': 'Game not found or not in FINAL status'}), 400

    ScoreNotificationService.notify_reconciliation(game)

    log_admin_action(
        user=current_user,
        action='reconcile_game',
        entity_type='game',
        entity_id=game.id
    )

    return jsonify({
        'is_reconciled': game.is_reconciled,
        'reconciled_at': game.reconciled_at.isoformat() if game.reconciled_at else None
    })


@live_scoring_bp.route('/api/games/<game_id>/validate', methods=['GET'])
@login_required
@tenant_required
def validate_score(game_id):
    """Validate game score."""
    game = LiveGameService.get_game_with_details(game_id, current_user.org_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    validation = LiveGameService.validate_score(game)
    return jsonify(validation)


@live_scoring_bp.route('/api/games/<game_id>/score-history', methods=['GET'])
@login_required
@tenant_required
def get_score_history(game_id):
    """Get score update history for audit."""
    history = LiveGameService.get_score_history(game_id, current_user.org_id)

    return jsonify([{
        'id': h.id,
        'previous_home_score': h.previous_home_score,
        'previous_away_score': h.previous_away_score,
        'new_home_score': h.new_home_score,
        'new_away_score': h.new_away_score,
        'update_type': h.update_type,
        'notes': h.notes,
        'created_at': h.created_at.isoformat()
    } for h in history])


# ============= Live Data Endpoint (for tickers/scoreboards) =============

@live_scoring_bp.route('/api/games/<game_id>/live', methods=['GET'])
@login_required
@tenant_required
def get_live_data(game_id):
    """Get live game data for ticker/scoreboard."""
    game = LiveGameService.get_game_with_details(game_id, current_user.org_id)
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    return jsonify({
        'game_id': game.id,
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
        'current_period': game.current_period,
        'game_clock': game.game_clock,
        'went_to_overtime': game.went_to_overtime,
        'overtime_periods': game.overtime_periods,
        'last_update': game.last_score_update.isoformat() if game.last_score_update else None
    })
