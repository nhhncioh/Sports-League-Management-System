import json
import csv
import io
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from slms.services.db import get_db
from slms.auth import admin_required
from . import schedule_mgmt_bp
import random

def _round_robin_schedule(team_ids, double_round=False):
    """
    Generate round-robin schedule pairings
    """
    if len(team_ids) < 2:
        return []

    # Make even number of teams
    if len(team_ids) % 2 != 0:
        team_ids = team_ids + [None]  # Bye

    n = len(team_ids)
    schedule = []

    for round_num in range(n - 1):
        round_pairings = []
        for i in range(n // 2):
            home = team_ids[i]
            away = team_ids[n - 1 - i]
            if home is not None and away is not None:
                round_pairings.append((home, away))
        schedule.append(round_pairings)

        # Rotate teams (keep first team fixed)
        team_ids = [team_ids[0]] + [team_ids[-1]] + team_ids[1:-1]

    # Double round robin (reverse fixtures for second half)
    if double_round:
        second_half = []
        for round_pairings in schedule:
            reversed_round = [(away, home) for home, away in round_pairings]
            second_half.append(reversed_round)
        schedule.extend(second_half)

    return schedule


def _detect_conflicts(draft_id, db):
    """
    Detect scheduling conflicts in a draft
    """
    cur = db.cursor()
    conflicts = []

    # Get all draft matches
    cur.execute("""
        SELECT dm.draft_match_id, dm.home_team_id, dm.away_team_id, dm.proposed_date,
               dm.venue_id, dm.matchday,
               ht.name as home_team, at.name as away_team,
               sd.league_id, sd.season_id
        FROM draft_matches dm
        JOIN teams ht ON dm.home_team_id = ht.team_id
        JOIN teams at ON dm.away_team_id = at.team_id
        JOIN schedule_drafts sd ON dm.draft_id = sd.draft_id
        WHERE dm.draft_id = %s
        ORDER BY dm.proposed_date
    """, (draft_id,))
    matches = cur.fetchall()

    for match in matches:
        draft_match_id, home_id, away_id, proposed_date, venue_id, matchday, home_name, away_name, league_id, season_id = match

        # Check blackout dates
        cur.execute("""
            SELECT blackout_id, reason
            FROM blackout_dates
            WHERE (league_id = %s OR league_id IS NULL)
            AND %s::date BETWEEN start_date AND end_date
        """, (league_id, proposed_date))

        blackout = cur.fetchone()
        if blackout:
            conflicts.append({
                'draft_match_id': draft_match_id,
                'type': 'blackout_date',
                'severity': 'error',
                'description': f"Match on {proposed_date.strftime('%Y-%m-%d')} falls on blackout period: {blackout[1] or 'Blackout period'}",
                'auto_resolvable': True,
                'suggestion': 'Move match to next available date'
            })

        # Check team double booking (team playing twice on same day)
        cur.execute("""
            SELECT COUNT(*)
            FROM draft_matches
            WHERE draft_id = %s
            AND draft_match_id != %s
            AND DATE(proposed_date) = DATE(%s)
            AND (home_team_id = %s OR away_team_id = %s OR home_team_id = %s OR away_team_id = %s)
        """, (draft_id, draft_match_id, proposed_date, home_id, home_id, away_id, away_id))

        double_booking = cur.fetchone()[0]
        if double_booking > 0:
            conflicts.append({
                'draft_match_id': draft_match_id,
                'type': 'double_booking',
                'severity': 'error',
                'description': f"Team has multiple matches scheduled on {proposed_date.strftime('%Y-%m-%d')}",
                'auto_resolvable': False,
                'suggestion': 'Reschedule one of the matches'
            })

        # Check minimum rest period (less than 2 days between matches for same team)
        cur.execute("""
            SELECT dm2.proposed_date, ht.name as opponent
            FROM draft_matches dm2
            LEFT JOIN teams ht ON (
                CASE
                    WHEN dm2.home_team_id IN (%s, %s) THEN dm2.away_team_id
                    ELSE dm2.home_team_id
                END = ht.team_id
            )
            WHERE dm2.draft_id = %s
            AND dm2.draft_match_id != %s
            AND (dm2.home_team_id IN (%s, %s) OR dm2.away_team_id IN (%s, %s))
            AND ABS(EXTRACT(epoch FROM (dm2.proposed_date - %s)) / 86400) < 2
        """, (home_id, away_id, draft_id, draft_match_id, home_id, away_id, home_id, away_id, proposed_date))

        rest_violations = cur.fetchall()
        for violation in rest_violations:
            conflicts.append({
                'draft_match_id': draft_match_id,
                'type': 'rest_period',
                'severity': 'warning',
                'description': f"Less than 2 days between matches (next match: {violation[0].strftime('%Y-%m-%d')} vs {violation[1]})",
                'auto_resolvable': True,
                'suggestion': 'Adjust match dates to allow minimum 2-day rest'
            })

        # Check venue conflicts if venue is specified
        if venue_id:
            cur.execute("""
                SELECT COUNT(*)
                FROM draft_matches
                WHERE draft_id = %s
                AND draft_match_id != %s
                AND venue_id = %s
                AND ABS(EXTRACT(epoch FROM (proposed_date - %s)) / 3600) < 4
            """, (draft_id, draft_match_id, venue_id, proposed_date))

            venue_conflict = cur.fetchone()[0]
            if venue_conflict > 0:
                conflicts.append({
                    'draft_match_id': draft_match_id,
                    'type': 'venue_conflict',
                    'severity': 'error',
                    'description': f"Venue is already booked within 4 hours of this match",
                    'auto_resolvable': False,
                    'suggestion': 'Use different venue or adjust timing'
                })

    cur.close()
    return conflicts


def _save_conflicts(draft_id, conflicts, db):
    """
    Save detected conflicts to database
    """
    cur = db.cursor()

    # Clear existing conflicts for this draft
    cur.execute("""
        DELETE FROM schedule_conflicts
        WHERE draft_match_id IN (SELECT draft_match_id FROM draft_matches WHERE draft_id = %s)
    """, (draft_id,))

    # Insert new conflicts
    for conflict in conflicts:
        cur.execute("""
            INSERT INTO schedule_conflicts
            (draft_match_id, conflict_type, severity, description, auto_resolvable, resolution_suggestion)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            conflict['draft_match_id'],
            conflict['type'],
            conflict['severity'],
            conflict['description'],
            conflict['auto_resolvable'],
            conflict.get('suggestion')
        ))

    # Update draft conflict count
    cur.execute("""
        UPDATE schedule_drafts
        SET conflict_count = %s
        WHERE draft_id = %s
    """, (len(conflicts), draft_id))

    db.commit()
    cur.close()


@schedule_mgmt_bp.route('/', methods=['GET', 'POST'])
@admin_required
def index():
    """Main schedule management page."""
    db = get_db()
    drafts: list[dict] = []
    blackout_dates: list[dict] = []
    conflicts: list[dict] = []
    leagues: list[dict] = []
    seasons = []
    stats = {
        'total_drafts': 0,
        'pending_approval': 0,
        'total_conflicts': 0,
        'blackout_dates': 0,
    }
    schema_errors: list[str] = []

    cur = None
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT sd.draft_id, sd.draft_name, sd.status, sd.created_at, sd.submitted_at,
                   sd.reviewed_at, sd.conflict_count, sd.rejection_reason,
                   l.name as league_name, s.year as season_year, sd.league_id, sd.season_id
            FROM schedule_drafts sd
            JOIN leagues l ON sd.league_id = l.league_id
            JOIN seasons s ON sd.season_id = s.season_id
            ORDER BY sd.created_at DESC
            """
        )
        for row in cur.fetchall():
            drafts.append(
                {
                    'draft_id': row[0],
                    'draft_name': row[1],
                    'status': row[2],
                    'created_at': row[3],
                    'submitted_at': row[4],
                    'reviewed_at': row[5],
                    'conflict_count': row[6],
                    'rejection_reason': row[7],
                    'league_name': row[8],
                    'season_year': row[9],
                    'league_id': row[10],
                    'season_id': row[11],
                }
            )

        cur.execute(
            """
            SELECT bd.blackout_id, bd.start_date, bd.end_date, bd.reason, l.name as league_name
            FROM blackout_dates bd
            LEFT JOIN leagues l ON bd.league_id = l.league_id
            ORDER BY bd.start_date DESC
            """
        )
        for row in cur.fetchall():
            blackout_dates.append(
                {
                    'blackout_id': row[0],
                    'start_date': row[1],
                    'end_date': row[2],
                    'reason': row[3],
                    'league_name': row[4],
                }
            )

        cur.execute(
            """
            SELECT sc.conflict_id, sc.conflict_type, sc.severity, sc.description,
                   sc.auto_resolvable, sc.resolution_suggestion,
                   dm.proposed_date, ht.name as home_team, at.name as away_team
            FROM schedule_conflicts sc
            JOIN draft_matches dm ON sc.draft_match_id = dm.draft_match_id
            JOIN teams ht ON dm.home_team_id = ht.team_id
            JOIN teams at ON dm.away_team_id = at.team_id
            ORDER BY sc.severity DESC, dm.proposed_date
            """
        )
        for row in cur.fetchall():
            conflicts.append(
                {
                    'conflict_id': row[0],
                    'conflict_type': row[1],
                    'severity': row[2],
                    'description': row[3],
                    'auto_resolvable': row[4],
                    'resolution_suggestion': row[5],
                    'match_date': row[6],
                    'home_team': row[7],
                    'away_team': row[8],
                }
            )

        cur.execute('SELECT league_id AS id, name FROM leagues ORDER BY name')
        leagues = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]

        cur.execute('SELECT season_id, year, league_id FROM seasons ORDER BY year DESC')
        seasons = cur.fetchall()

        stats = {
            'total_drafts': len(drafts),
            'pending_approval': len([d for d in drafts if d['status'] == 'pending_approval']),
            'total_conflicts': sum(d['conflict_count'] for d in drafts),
            'blackout_dates': len(blackout_dates),
        }

    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        current_app.logger.exception('Failed to load schedule management dashboard')
        schema_errors.append(str(exc))
        drafts.clear()
        blackout_dates.clear()
        conflicts.clear()
        leagues.clear()
        seasons = []
        stats = {
            'total_drafts': 0,
            'pending_approval': 0,
            'total_conflicts': 0,
            'blackout_dates': 0,
        }
    finally:
        if cur is not None:
            cur.close()

    if schema_errors:
        flash(
            'Schedule management tables are missing or not migrated yet. '
            'Run migrations/add_schedule_management_tables.sql or see '
            'SCHEDULE_MANAGEMENT_README.md for setup details.',
            'error',
        )

    if request.method == 'POST' and request.form.get('action') == 'create_draft':
        return _create_draft()

    return render_template(
        'schedule_management.html',
        drafts=drafts,
        blackout_dates=blackout_dates,
        conflicts=conflicts,
        leagues=leagues,
        seasons=seasons,
        stats=stats,
        schema_errors=schema_errors,
    )


def _create_draft():
    """Create a new schedule plan"""
    db = get_db()
    cur = db.cursor()

    try:
        draft_name = request.form.get('draft_name')
        league_id = int(request.form.get('league_id'))
        season_id = int(request.form.get('season_id'))
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        interval_days = int(request.form.get('interval_days', 7))
        double_round = 'double_round' in request.form
        shuffle_teams = 'shuffle_teams' in request.form
        respect_blackouts = 'respect_blackouts' in request.form

        # Create draft
        generation_params = {
            'start_date': str(start_date),
            'interval_days': interval_days,
            'double_round': double_round,
            'shuffle_teams': shuffle_teams,
            'respect_blackouts': respect_blackouts
        }

        cur.execute("""
            INSERT INTO schedule_drafts (league_id, season_id, draft_name, status, generation_params)
            VALUES (%s, %s, %s, 'draft', %s)
            RETURNING draft_id
        """, (league_id, season_id, draft_name, json.dumps(generation_params)))

        draft_id = cur.fetchone()[0]

        # Get teams
        cur.execute('SELECT team_id FROM teams WHERE league_id = %s ORDER BY name', (league_id,))
        team_ids = [row[0] for row in cur.fetchall()]

        if len(team_ids) < 2:
            flash('At least 2 teams required to generate fixtures', 'error')
            return redirect(url_for('schedule_mgmt.index'))

        if shuffle_teams:
            random.shuffle(team_ids)

        # Generate schedule
        schedule = _round_robin_schedule(team_ids, double_round)

        # Get blackout dates if respecting them
        blackout_dates = []
        if respect_blackouts:
            cur.execute("""
                SELECT start_date, end_date
                FROM blackout_dates
                WHERE (league_id = %s OR league_id IS NULL)
                AND (season_id = %s OR season_id IS NULL)
            """, (league_id, season_id))
            blackout_dates = cur.fetchall()

        # Insert matches
        current_date = start_date
        for matchday, pairings in enumerate(schedule, 1):
            # Skip blackout dates
            while respect_blackouts and any(bd[0] <= current_date <= bd[1] for bd in blackout_dates):
                current_date += timedelta(days=1)

            for home_id, away_id in pairings:
                cur.execute("""
                    INSERT INTO draft_matches (draft_id, home_team_id, away_team_id, proposed_date, matchday)
                    VALUES (%s, %s, %s, %s, %s)
                """, (draft_id, home_id, away_id, datetime.combine(current_date, datetime.min.time()), matchday))

            current_date += timedelta(days=interval_days)

        # Detect conflicts
        conflicts = _detect_conflicts(draft_id, db)
        _save_conflicts(draft_id, conflicts, db)

        # Log creation
        cur.execute("""
            INSERT INTO schedule_approval_log (draft_id, action, notes)
            VALUES (%s, 'created', %s)
        """, (draft_id, f"Plan created with {len(schedule)} matchdays"))

        db.commit()
        flash(f"Schedule plan '{draft_name}' created successfully with {sum(len(p) for p in schedule)} matches!", 'success')

    except Exception as e:
        db.rollback()
        flash(f'Error creating plan: {str(e)}', 'error')
    finally:
        cur.close()

    return redirect(url_for('schedule_mgmt.index'))


@schedule_mgmt_bp.route('/draft/<int:draft_id>/matches')
@admin_required
def get_draft_matches(draft_id):
    """Get all matches for a plan (for reordering)"""
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT dm.draft_match_id, dm.matchday, dm.proposed_date, dm.display_order, dm.has_conflict,
               ht.name as home_team, at.name as away_team
        FROM draft_matches dm
        JOIN teams ht ON dm.home_team_id = ht.team_id
        JOIN teams at ON dm.away_team_id = at.team_id
        WHERE dm.draft_id = %s
        ORDER BY dm.matchday, dm.display_order, dm.proposed_date
    """, (draft_id,))

    matches = []
    for row in cur.fetchall():
        matches.append({
            'draft_match_id': row[0],
            'matchday': row[1],
            'proposed_date': row[2].strftime('%Y-%m-%d %H:%M'),
            'display_order': row[3],
            'has_conflict': row[4],
            'home_team': row[5],
            'away_team': row[6]
        })

    cur.close()
    return jsonify({'matches': matches})


@schedule_mgmt_bp.route('/draft/<int:draft_id>/reorder', methods=['POST'])
@admin_required
def reorder_matches(draft_id):
    """Save new order for matches"""
    db = get_db()
    cur = db.cursor()

    try:
        order = request.json.get('order', [])

        for item in order:
            cur.execute("""
                UPDATE draft_matches
                SET display_order = %s
                WHERE draft_match_id = %s
            """, (item['display_order'], item['draft_match_id']))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>/submit', methods=['POST'])
@admin_required
def submit_draft(draft_id):
    """Submit plan for approval"""
    db = get_db()
    cur = db.cursor()

    try:
        cur.execute("""
            UPDATE schedule_drafts
            SET status = 'pending_approval', submitted_at = CURRENT_TIMESTAMP
            WHERE draft_id = %s
        """, (draft_id,))

        cur.execute("""
            INSERT INTO schedule_approval_log (draft_id, action, notes)
            VALUES (%s, 'submitted', 'Plan submitted for approval')
        """, (draft_id,))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>/approve', methods=['POST'])
@admin_required
def approve_draft(draft_id):
    """Approve a plan"""
    db = get_db()
    cur = db.cursor()

    try:
        notes = request.json.get('notes', '')

        cur.execute("""
            UPDATE schedule_drafts
            SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, approval_notes = %s
            WHERE draft_id = %s
        """, (notes, draft_id))

        cur.execute("""
            INSERT INTO schedule_approval_log (draft_id, action, notes)
            VALUES (%s, 'approved', %s)
        """, (draft_id, notes or 'Plan approved'))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>/reject', methods=['POST'])
@admin_required
def reject_draft(draft_id):
    """Reject a plan"""
    db = get_db()
    cur = db.cursor()

    try:
        reason = request.json.get('reason', '')

        cur.execute("""
            UPDATE schedule_drafts
            SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, rejection_reason = %s
            WHERE draft_id = %s
        """, (reason, draft_id))

        cur.execute("""
            INSERT INTO schedule_approval_log (draft_id, action, notes)
            VALUES (%s, 'rejected', %s)
        """, (draft_id, reason))

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>/publish', methods=['POST'])
@admin_required
def publish_draft(draft_id):
    """Publish approved plan to actual matches"""
    db = get_db()
    cur = db.cursor()

    try:
        # Get draft info
        cur.execute("""
            SELECT league_id, season_id, status
            FROM schedule_drafts
            WHERE draft_id = %s
        """, (draft_id,))

        draft = cur.fetchone()
        if not draft or draft[2] != 'approved':
            return jsonify({'success': False, 'error': 'Plan must be approved before publishing'}), 400

        league_id, season_id, _ = draft

        # Get all draft matches
        cur.execute("""
            SELECT home_team_id, away_team_id, proposed_date, venue_id, matchday, display_order
            FROM draft_matches
            WHERE draft_id = %s
            ORDER BY matchday, display_order
        """, (draft_id,))

        matches = cur.fetchall()

        # Insert into actual matches table
        for match in matches:
            home_id, away_id, proposed_date, venue_id, matchday, display_order = match
            cur.execute("""
                INSERT INTO matches (home_team_id, away_team_id, utc_date, league_id, season_id, venue_id, matchday, display_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (home_id, away_id, proposed_date, league_id, season_id, venue_id, matchday, display_order))

        # Update draft status
        cur.execute("""
            UPDATE schedule_drafts
            SET status = 'published'
            WHERE draft_id = %s
        """, (draft_id,))

        cur.execute("""
            INSERT INTO schedule_approval_log (draft_id, action, notes)
            VALUES (%s, 'published', %s)
        """, (draft_id, f"Published {len(matches)} matches to schedule"))

        db.commit()
        return jsonify({'success': True, 'matches_created': len(matches)})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>', methods=['DELETE'])
@admin_required
def delete_draft(draft_id):
    """Delete a plan"""
    db = get_db()
    cur = db.cursor()

    try:
        cur.execute('DELETE FROM schedule_drafts WHERE draft_id = %s', (draft_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/blackout', methods=['POST'])
@admin_required
def add_blackout():
    """Add blackout date"""
    db = get_db()
    cur = db.cursor()

    try:
        league_id = request.form.get('league_id') or None
        season_id = request.form.get('season_id') or None
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')

        cur.execute("""
            INSERT INTO blackout_dates (league_id, season_id, start_date, end_date, reason)
            VALUES (%s, %s, %s, %s, %s)
        """, (league_id, season_id, start_date, end_date, reason))

        db.commit()
        flash('Blackout date added successfully', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error adding blackout date: {str(e)}', 'error')
    finally:
        cur.close()

    return redirect(url_for('schedule_mgmt.index'))


@schedule_mgmt_bp.route('/blackout/<int:blackout_id>', methods=['DELETE'])
@admin_required
def delete_blackout(blackout_id):
    """Delete blackout date"""
    db = get_db()
    cur = db.cursor()

    try:
        cur.execute('DELETE FROM blackout_dates WHERE blackout_id = %s', (blackout_id,))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()


@schedule_mgmt_bp.route('/draft/<int:draft_id>/export')
@admin_required
def export_draft(draft_id):
    """Export plan in various formats"""
    export_format = request.args.get('format', 'csv')
    db = get_db()
    cur = db.cursor()

    # Get draft matches
    cur.execute("""
        SELECT dm.matchday, dm.proposed_date, ht.name as home_team, at.name as away_team,
               l.name as league, s.year as season
        FROM draft_matches dm
        JOIN teams ht ON dm.home_team_id = ht.team_id
        JOIN teams at ON dm.away_team_id = at.team_id
        JOIN schedule_drafts sd ON dm.draft_id = sd.draft_id
        JOIN leagues l ON sd.league_id = l.league_id
        JOIN seasons s ON sd.season_id = s.season_id
        WHERE dm.draft_id = %s
        ORDER BY dm.matchday, dm.display_order, dm.proposed_date
    """, (draft_id,))

    matches = cur.fetchall()
    cur.close()

    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Matchday', 'Date', 'Time', 'Home Team', 'Away Team', 'League', 'Season'])

        for match in matches:
            matchday, proposed_date, home, away, league, season = match
            writer.writerow([
                matchday,
                proposed_date.strftime('%Y-%m-%d'),
                proposed_date.strftime('%H:%M'),
                home,
                away,
                league,
                season
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'schedule_plan_{draft_id}.csv'
        )

    elif export_format == 'json':
        data = []
        for match in matches:
            matchday, proposed_date, home, away, league, season = match
            data.append({
                'matchday': matchday,
                'date': proposed_date.strftime('%Y-%m-%d'),
                'time': proposed_date.strftime('%H:%M'),
                'home_team': home,
                'away_team': away,
                'league': league,
                'season': season
            })

        return jsonify(data)

    return jsonify({'error': 'Unsupported format'}), 400





