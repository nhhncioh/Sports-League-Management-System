from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from functools import wraps
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
import json
import random

from flask_login import current_user

from slms.services.db import get_db
from slms.extensions import db
from slms.services.site import _load_site_settings, invalidate_site_settings_cache
from slms.models import UserRole, User


def _default_homepage_config():
    return {
        'title': '',
        'subtitle': '',
        'background_url': '',
        'cta_text': '',
        'cta_url': '',
        'highlights': [],
    }


AVERAGE_MATCH_REVENUE_USD = 7500  # fallback estimate when transaction data is unavailable

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if current_user.is_authenticated:
            has_role = getattr(current_user, 'has_role', None)
            if callable(has_role) and current_user.has_role(UserRole.OWNER, UserRole.ADMIN):
                return f(*args, **kwargs)
        if session.get('is_admin'):
            return f(*args, **kwargs)
        flash('You need to be an admin to access this page', 'error')
        return redirect(url_for('auth.login', next=request.url))
    return wrap

def get_existing_data(table_name):
    db = get_db()
    cur = db.cursor()
    cur.execute(f'SELECT * FROM {table_name}')
    data = cur.fetchall()
    cur.close()
    return data


def _calc_metric(current_value, previous_value):
    current = current_value or 0
    previous = previous_value or 0
    delta = current - previous
    delta_pct = (delta / previous * 100) if previous else None
    return {
        'current': current,
        'previous': previous,
        'delta': delta,
        'delta_pct': delta_pct,
    }


def _execute_scalar(cur, query, params=None):
    cur.execute(query, params or ())
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else 0



def _parse_amount_to_cents(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int((Decimal(str(value)) * 100).quantize(Decimal('1')))
    value = value.strip()
    if not value:
        return None
    try:
        quant = Decimal(value.replace(',', ''))
    except InvalidOperation:
        raise ValueError('Invalid currency amount')
    cents = int((quant * 100).quantize(Decimal('1')))
    return cents


def _format_cents_to_decimal(cents):
    if cents is None:
        return None
    return (Decimal(cents) / Decimal('100')).quantize(Decimal('0.01'))


def _ensure_finance_hub_tables(db_wrapper):
    """Create tables for comprehensive finance hub"""
    cur = db_wrapper.cursor()
    try:
        # Revenue tracking table for consolidated financial data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS league_revenue (
                revenue_id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL REFERENCES leagues(league_id) ON DELETE CASCADE,
                revenue_type VARCHAR(50) NOT NULL, -- 'fees', 'sponsorship', 'in_person', 'square', 'other'
                amount_cents INTEGER NOT NULL DEFAULT 0,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
                description TEXT,
                reference_id INTEGER, -- References to related records (fee_id, sponsor_id, etc)
                reference_type VARCHAR(50), -- 'installment', 'sponsorship_deal', 'manual_entry'
                payment_method VARCHAR(50), -- 'cash', 'check', 'card', 'bank_transfer', 'square', 'online'
                status VARCHAR(20) NOT NULL DEFAULT 'confirmed', -- 'pending', 'confirmed', 'cancelled'
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB -- For storing additional payment gateway data
            )
        """)

        # In-person payment transactions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS in_person_payments (
                payment_id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL REFERENCES leagues(league_id) ON DELETE CASCADE,
                amount_cents INTEGER NOT NULL,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                payment_method VARCHAR(50) NOT NULL, -- 'cash', 'check', 'card'
                payment_date DATE NOT NULL DEFAULT CURRENT_DATE,
                payer_name VARCHAR(255),
                payer_contact VARCHAR(255), -- Phone or email
                description TEXT NOT NULL,
                check_number VARCHAR(50), -- For check payments
                card_last_four VARCHAR(4), -- For card payments (security)
                receipt_number VARCHAR(100),
                notes TEXT,
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Enhanced financial reports/budget tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS league_budgets (
                budget_id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL REFERENCES leagues(league_id) ON DELETE CASCADE,
                budget_year INTEGER NOT NULL,
                category VARCHAR(100) NOT NULL, -- 'registration_fees', 'sponsorships', 'concessions', etc
                budgeted_amount_cents INTEGER NOT NULL DEFAULT 0,
                actual_amount_cents INTEGER NOT NULL DEFAULT 0,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league_id, budget_year, category)
            )
        """)

        # Square payment integration tracking (ready for future)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS square_payments (
                square_payment_id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL REFERENCES leagues(league_id) ON DELETE CASCADE,
                square_payment_id_external VARCHAR(255) UNIQUE NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                status VARCHAR(50) NOT NULL, -- 'completed', 'pending', 'failed', 'cancelled'
                payment_date TIMESTAMP,
                description TEXT,
                customer_email VARCHAR(255),
                customer_name VARCHAR(255),
                receipt_url TEXT,
                reference_id INTEGER, -- Link to league fees, etc
                reference_type VARCHAR(50),
                square_order_id VARCHAR(255),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_league_revenue_league_id ON league_revenue(league_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_league_revenue_date ON league_revenue(transaction_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_league_revenue_type ON league_revenue(revenue_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_in_person_payments_league_id ON in_person_payments(league_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_in_person_payments_date ON in_person_payments(payment_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_league_budgets_league_year ON league_budgets(league_id, budget_year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_square_payments_league_id ON square_payments(league_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_square_payments_status ON square_payments(status)")

        db_wrapper.commit()
    except Exception:
        db_wrapper.rollback()
        raise
    finally:
        cur.close()


def _get_comprehensive_finance_data(db, league_id_int):
    """Get all financial data for the finance hub"""
    if not league_id_int:
        return {
            'total_revenue': {'amount': 0, 'display': '$0.00'},
            'revenue_breakdown': {},
            'recent_transactions': [],
            'budget_vs_actual': [],
            'sponsor_revenue': {'amount': 0, 'display': '$0.00'},
            'fee_revenue': {'amount': 0, 'display': '$0.00'},
            'in_person_revenue': {'amount': 0, 'display': '$0.00'},
            'fee_plan': None,
            'installments': [],
            'teams': []
        }

    cur = db.cursor()
    try:
        # Get total revenue by type
        cur.execute("""
            SELECT revenue_type,
                   COALESCE(SUM(amount_cents), 0) as total_cents,
                   COUNT(*) as transaction_count
            FROM league_revenue
            WHERE league_id = %s AND status = 'confirmed'
            GROUP BY revenue_type
            ORDER BY total_cents DESC
        """, (league_id_int,))

        revenue_breakdown = {}
        total_revenue_cents = 0

        for row in cur.fetchall():
            revenue_type, amount_cents, count = row
            revenue_breakdown[revenue_type] = {
                'amount_cents': amount_cents,
                'amount_display': _format_cents_to_decimal(amount_cents),
                'transaction_count': count
            }
            total_revenue_cents += amount_cents

        # Get recent transactions
        cur.execute("""
            SELECT revenue_type, amount_cents, transaction_date, description, payment_method
            FROM league_revenue
            WHERE league_id = %s
            ORDER BY transaction_date DESC, created_at DESC
            LIMIT 10
        """, (league_id_int,))

        recent_transactions = []
        for row in cur.fetchall():
            revenue_type, amount_cents, trans_date, description, payment_method = row
            recent_transactions.append({
                'type': revenue_type,
                'amount_display': _format_cents_to_decimal(amount_cents),
                'date': trans_date.strftime('%Y-%m-%d') if trans_date else '',
                'description': description or '',
                'payment_method': payment_method or ''
            })

        # Get sponsor revenue data (all active deals since sponsors aren't league-specific in current schema)
        cur.execute("""
            SELECT COALESCE(SUM(sd.deal_value_cents), 0) as sponsor_revenue
            FROM sponsorship_deals sd
            WHERE sd.deal_status = 'active'
        """)

        sponsor_revenue_cents = cur.fetchone()[0] or 0

        # Get fee plan and installments (existing logic)
        plan = _get_league_fee_plan(cur, league_id_int)
        installments = []
        fee_revenue_cents = 0

        if plan:
            cur.execute("""
                SELECT installment_id, label, due_date, amount_cents, status, notes
                FROM league_fee_installments
                WHERE plan_id = %s
                ORDER BY due_date IS NULL, due_date
            """, (plan['plan_id'],))

            for row in cur.fetchall():
                installment_id, label, due_date, amount_cents, status, notes = row
                installments.append({
                    'installment_id': installment_id,
                    'label': label,
                    'due_date': due_date.strftime('%Y-%m-%d') if due_date else '',
                    'amount_cents': amount_cents or 0,
                    'amount_display': _format_cents_to_decimal(amount_cents or 0),
                    'status': status or 'pending',
                    'notes': notes
                })
                if status == 'paid':
                    fee_revenue_cents += amount_cents or 0

        # Get in-person payments
        cur.execute("""
            SELECT COALESCE(SUM(amount_cents), 0)
            FROM in_person_payments
            WHERE league_id = %s
        """, (league_id_int,))

        in_person_revenue_cents = cur.fetchone()[0] or 0

        # Get teams for the league
        cur.execute('SELECT team_id, name FROM teams WHERE league_id = %s ORDER BY name', (league_id_int,))
        teams = [{'team_id': row[0], 'name': row[1]} for row in cur.fetchall()]

        return {
            'total_revenue': {
                'amount': total_revenue_cents,
                'display': f'${_format_cents_to_decimal(total_revenue_cents)}'
            },
            'revenue_breakdown': revenue_breakdown,
            'recent_transactions': recent_transactions,
            'sponsor_revenue': {
                'amount': sponsor_revenue_cents,
                'display': f'${_format_cents_to_decimal(sponsor_revenue_cents)}'
            },
            'fee_revenue': {
                'amount': fee_revenue_cents,
                'display': f'${_format_cents_to_decimal(fee_revenue_cents)}'
            },
            'in_person_revenue': {
                'amount': in_person_revenue_cents,
                'display': f'${_format_cents_to_decimal(in_person_revenue_cents)}'
            },
            'fee_plan': plan,
            'installments': installments,
            'teams': teams
        }

    finally:
        cur.close()


def _handle_add_in_person_payment(db):
    """Handle adding in-person payment"""
    try:
        league_id = int(request.form.get('league_id'))
        amount_cents = _parse_amount_to_cents(request.form.get('amount'))
        payment_method = request.form.get('payment_method')
        payer_name = request.form.get('payer_name', '').strip()
        description = request.form.get('description', '').strip()
        payment_date = request.form.get('payment_date') or datetime.now().date()

        if not amount_cents or amount_cents <= 0:
            flash('Valid payment amount is required.', 'error')
            return redirect(url_for('admin.league_finance_hub', league_id=league_id))

        cur = db.cursor()
        try:
            # Insert in-person payment
            cur.execute("""
                INSERT INTO in_person_payments
                (league_id, amount_cents, payment_method, payer_name, description,
                 payment_date, check_number, card_last_four, receipt_number, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING payment_id
            """, (
                league_id, amount_cents, payment_method, payer_name, description,
                payment_date,
                request.form.get('check_number', '').strip() or None,
                request.form.get('card_last_four', '').strip() or None,
                request.form.get('receipt_number', '').strip() or None,
                request.form.get('notes', '').strip() or None,
                1  # TODO: Replace with current_user.id when auth is implemented
            ))

            payment_id = cur.fetchone()[0]

            # Also add to league_revenue for consolidated tracking
            cur.execute("""
                INSERT INTO league_revenue
                (league_id, revenue_type, amount_cents, transaction_date, description,
                 reference_id, reference_type, payment_method, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                league_id, 'in_person', amount_cents, payment_date,
                f'{description} - {payer_name}', payment_id, 'in_person_payment',
                payment_method, 'confirmed', 1
            ))

            db.commit()
            flash('In-person payment recorded successfully.', 'success')

        except Exception as e:
            db.rollback()
            flash(f'Failed to record payment: {str(e)}', 'error')
        finally:
            cur.close()

    except (ValueError, TypeError):
        flash('Invalid payment data provided.', 'error')

    return redirect(url_for('admin.league_finance_hub',
                           league_id=request.form.get('league_id')))


def _handle_update_budget(db):
    """Handle budget update"""
    # Implementation for budget management
    flash('Budget feature coming soon.', 'info')
    return redirect(url_for('admin.league_finance_hub',
                           league_id=request.form.get('league_id')))


def _handle_generate_revenue_entry(db):
    """Handle manual revenue entry"""
    # Implementation for manual revenue entries
    flash('Manual revenue entry feature coming soon.', 'info')
    return redirect(url_for('admin.league_finance_hub',
                           league_id=request.form.get('league_id')))


def _handle_legacy_fee_actions(db):
    """Handle existing fee management actions"""
    # This will contain the existing fee management logic
    # For now, redirect to the old system
    flash('Fee management integration in progress.', 'info')
    return redirect(url_for('admin.manage_league_fees',
                           league_id=request.form.get('league_id')))


def _ensure_league_rules_table(db_wrapper):
    cur = db_wrapper.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS league_rules (
                league_id INTEGER PRIMARY KEY REFERENCES leagues(league_id) ON DELETE CASCADE,
                points_win INTEGER NOT NULL DEFAULT 3,
                points_draw INTEGER NOT NULL DEFAULT 1,
                points_loss INTEGER NOT NULL DEFAULT 0,
                tiebreakers TEXT,
                substitution_limit INTEGER,
                foreign_player_limit INTEGER,
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create custom fields table for league rules
        cur.execute("""
            CREATE TABLE IF NOT EXISTS league_rules_custom_fields (
                field_id SERIAL PRIMARY KEY,
                league_id INTEGER NOT NULL REFERENCES leagues(league_id) ON DELETE CASCADE,
                field_name VARCHAR(100) NOT NULL,
                field_type VARCHAR(20) NOT NULL DEFAULT 'text',
                field_value TEXT,
                display_order INTEGER DEFAULT 0,
                is_required BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league_id, field_name)
            )
        """)

        # Create index for better performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_league_rules_custom_fields_league_id
            ON league_rules_custom_fields(league_id)
        """)

        db_wrapper.commit()
    except Exception:
        db_wrapper.rollback()
        raise
    finally:
        cur.close()


def _round_robin_schedule(team_ids, double_round=False):
    teams = list(team_ids)
    if len(teams) < 2:
        return []

    if len(teams) % 2:
        teams.append(None)

    rounds = len(teams) - 1
    schedule = []

    for round_index in range(rounds):
        pairings = []
        for idx in range(len(teams) // 2):
            home = teams[idx]
            away = teams[-(idx + 1)]
            if home is None or away is None:
                continue
            if idx == 0 and round_index % 2 == 1:
                home, away = away, home
            pairings.append((home, away))
        schedule.append(pairings)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    if double_round:
        schedule.extend([[(away, home) for home, away in pairings] for pairings in schedule])

    return schedule


def _parse_tiebreakers(raw_value):
    if not raw_value:
        return ['GD', 'GF']
    tokens = []
    for token in str(raw_value).split(','):
        token = token.strip().upper()
        if token:
            tokens.append(token)
    return tokens or ['GD', 'GF']


def _standing_sort_key(record, tiebreakers):
    key = [-record['points']]
    for tb in tiebreakers:
        if tb == 'GD':
            key.append(-record['goal_difference'])
        elif tb == 'GF':
            key.append(-record['goals_for'])
        elif tb == 'GA':
            key.append(record['goals_against'])
        elif tb == 'W':
            key.append(-record['won'])
    key.append(record['team_name'].lower())
    return tuple(key)


def _init_standing_record(team_id, team_name):
    return {
        'team_id': team_id,
        'team_name': team_name,
        'played_games': 0,
        'won': 0,
        'draw': 0,
        'lost': 0,
        'goals_for': 0,
        'goals_against': 0,
        'form': [],
    }


def _get_league_fee_plan(cur, league_id):
    cur.execute(
        "SELECT plan_id, total_fee_cents, deposit_cents, currency, notes, installments_enabled, installment_count FROM league_fee_plans WHERE league_id = %s",
        (league_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    plan_id, total_fee, deposit, currency, notes, enabled, count = row
    return {
        'plan_id': plan_id,
        'league_id': league_id,
        'total_fee_cents': total_fee or 0,
        'deposit_cents': deposit,
        'currency': (currency or 'USD').upper(),
        'notes': notes,
        'installments_enabled': bool(enabled),
        'installment_count': count or 0,
        'total_fee_display': _format_cents_to_decimal(total_fee or 0),
        'deposit_display': _format_cents_to_decimal(deposit) if deposit is not None else None,
    }


def _ensure_league_fee_plan(cur, league_id, currency='USD'):
    plan = _get_league_fee_plan(cur, league_id)
    if plan:
        return plan
    now = datetime.utcnow()
    cur.execute(
        "INSERT INTO league_fee_plans (league_id, total_fee_cents, deposit_cents, currency, notes, installments_enabled, installment_count, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (league_id, 0, None, currency.upper(), None, False, 0, now, now)
    )
    return _get_league_fee_plan(cur, league_id)




def _load_homepage_config(cur, league_id):
    try:
        cur.execute(
            "SELECT homepage_title, homepage_subtitle, homepage_background_url, homepage_cta_text, homepage_cta_url, homepage_highlights_json FROM leagues WHERE league_id = %s",
            (league_id,)
        )
        row = cur.fetchone()
    except Exception:
        return _default_homepage_config()
    if not row:
        return _default_homepage_config()
    highlights_json = row[5] or '[]'
    try:
        highlights = json.loads(highlights_json)
    except (TypeError, json.JSONDecodeError):
        highlights = []
    return {
        'title': row[0] or '',
        'subtitle': row[1] or '',
        'background_url': row[2] or '',
        'cta_text': row[3] or '',
        'cta_url': row[4] or '',
        'highlights': highlights,
    }



def _save_homepage_config(cur, league_id, config):
    try:
        highlights_json = json.dumps(config.get('highlights', []))
    except (TypeError, ValueError):
        highlights_json = '[]'
    cur.execute(
        "UPDATE leagues SET homepage_title = %s, homepage_subtitle = %s, homepage_background_url = %s, homepage_cta_text = %s, homepage_cta_url = %s, homepage_highlights_json = %s WHERE league_id = %s",
        (
            config.get('title') or None,
            config.get('subtitle') or None,
            config.get('background_url') or None,
            config.get('cta_text') or None,
            config.get('cta_url') or None,
            highlights_json,
            league_id,
        )
    )




NAV_AUDIENCE_CHOICES = ('everyone', 'auth', 'guest', 'admin')
NAV_LAYOUT_CHOICES = ('top', 'sidebar')


def _load_navigation_settings():
    settings = _load_site_settings()
    raw_links = settings.get('navigation_links_raw', []) or []
    layout = settings.get('nav_layout', 'top') or 'top'
    return {
        'layout': layout if layout in NAV_LAYOUT_CHOICES else 'top',
        'links': raw_links,
    }


def _persist_navigation_settings(layout: str, links: list[dict]):
    layout_normalized = layout if layout in NAV_LAYOUT_CHOICES else 'top'
    db = get_db()
    cur = db.cursor()
    try:
        payload = json.dumps(links)
        cur.execute('SELECT id FROM site_settings ORDER BY id ASC LIMIT 1')
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE site_settings SET nav_layout = %s, navigation_json = %s, updated_at = NOW() WHERE id = %s",
                (layout_normalized, payload, row[0])
            )
        else:
            cur.execute(
                "INSERT INTO site_settings (nav_layout, navigation_json) VALUES (%s, %s)",
                (layout_normalized, payload)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
    invalidate_site_settings_cache()
def _build_league_insights():
    db = get_db()
    cur = db.cursor()
    try:
        current_year = datetime.utcnow().year
        previous_year = current_year - 1

        teams_current = _execute_scalar(
            cur,
            """
            SELECT COUNT(DISTINCT team_id)
            FROM (
                SELECT home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                UNION
                SELECT away_team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
            ) AS teams_year
            """,
            (current_year, current_year),
        )
        teams_previous = _execute_scalar(
            cur,
            """
            SELECT COUNT(DISTINCT team_id)
            FROM (
                SELECT home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                UNION
                SELECT away_team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
            ) AS teams_year
            """,
            (previous_year, previous_year),
        )

        players_current = _execute_scalar(
            cur,
            """
            SELECT COUNT(DISTINCT p.player_id)
            FROM players p
            WHERE p.team_id IN (
                SELECT team_id FROM (
                    SELECT home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                    UNION
                    SELECT away_team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                ) AS teams_year
            )
            """,
            (current_year, current_year),
        )
        players_previous = _execute_scalar(
            cur,
            """
            SELECT COUNT(DISTINCT p.player_id)
            FROM players p
            WHERE p.team_id IN (
                SELECT team_id FROM (
                    SELECT home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                    UNION
                    SELECT away_team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                ) AS teams_year
            )
            """,
            (previous_year, previous_year),
        )

        matches_current = _execute_scalar(
            cur,
            "SELECT COUNT(*) FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s",
            (current_year,),
        )
        matches_previous = _execute_scalar(
            cur,
            "SELECT COUNT(*) FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s",
            (previous_year,),
        )
        matches_completed_current = _execute_scalar(
            cur,
            "SELECT COUNT(*) FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s AND winner IS NOT NULL",
            (current_year,),
        )
        matches_completed_previous = _execute_scalar(
            cur,
            "SELECT COUNT(*) FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s AND winner IS NOT NULL",
            (previous_year,),
        )

        revenue_current_cents = int(matches_current * AVERAGE_MATCH_REVENUE_USD * 100)
        revenue_previous_cents = int(matches_previous * AVERAGE_MATCH_REVENUE_USD * 100)

        average_team_size = (players_current / teams_current) if teams_current else None

        conversion_rate = (
            (matches_completed_current / matches_current) * 100
            if matches_current
            else None
        )

        league_data = {}

        cur.execute(
            """
            SELECT sub.league_id, l.name, COUNT(DISTINCT sub.team_id) AS team_count
            FROM (
                SELECT league_id, home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                UNION
                SELECT league_id, away_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
            ) AS sub
            JOIN leagues l ON l.league_id = sub.league_id
            GROUP BY sub.league_id, l.name
            """,
            (current_year, current_year),
        )
        for league_id, name, team_count in cur.fetchall():
            league_data[league_id] = {
                'name': name,
                'teams_current': int(team_count or 0),
                'teams_previous': 0,
                'registrations_current': 0,
                'revenue_cents': 0,
            }

        cur.execute(
            """
            SELECT sub.league_id, l.name, COUNT(DISTINCT sub.team_id) AS team_count
            FROM (
                SELECT league_id, home_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
                UNION
                SELECT league_id, away_team_id AS team_id FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s
            ) AS sub
            JOIN leagues l ON l.league_id = sub.league_id
            GROUP BY sub.league_id, l.name
            """,
            (previous_year, previous_year),
        )
        for league_id, name, team_count in cur.fetchall():
            entry = league_data.setdefault(
                league_id,
                {
                    'name': name,
                    'teams_current': 0,
                    'teams_previous': 0,
                    'registrations_current': 0,
                    'revenue_cents': 0,
                },
            )
            entry['teams_previous'] = int(team_count or 0)

        cur.execute(
            "SELECT league_id, COUNT(*) FROM matches WHERE EXTRACT(YEAR FROM utc_date) = %s GROUP BY league_id",
            (current_year,),
        )
        for league_id, match_count in cur.fetchall():
            entry = league_data.setdefault(
                league_id,
                {
                    'name': '',
                    'teams_current': 0,
                    'teams_previous': 0,
                    'registrations_current': 0,
                    'revenue_cents': 0,
                },
            )
            entry['registrations_current'] = int(match_count or 0)
            entry['revenue_cents'] = int((match_count or 0) * AVERAGE_MATCH_REVENUE_USD * 100)

        league_breakdown = []
        for entry in league_data.values():
            metric = _calc_metric(entry['teams_current'], entry['teams_previous'])
            league_breakdown.append(
                {
                    'name': entry['name'],
                    'teams_current': entry['teams_current'],
                    'teams_previous': entry['teams_previous'],
                    'team_delta': metric['delta'],
                    'team_delta_pct': metric['delta_pct'],
                    'registrations_current': entry['registrations_current'],
                    'revenue_cents': entry['revenue_cents'],
                }
            )

        league_breakdown.sort(key=lambda item: item['teams_current'], reverse=True)
        league_breakdown = league_breakdown[:6]

        return {
            'current_year': current_year,
            'previous_year': previous_year,
            'totals': {
                'teams': _calc_metric(teams_current, teams_previous),
                'players': _calc_metric(players_current, players_previous),
                'registrations': _calc_metric(matches_current, matches_previous),
                'paid_registrations': _calc_metric(matches_completed_current, matches_completed_previous),
                'revenue': _calc_metric(revenue_current_cents, revenue_previous_cents),
            },
            'conversion_rate': conversion_rate,
            'average_team_size': average_team_size,
            'league_breakdown': league_breakdown,
            'updated_at': datetime.utcnow(),
        }
    finally:
        cur.close()


@admin_bp.route('/')
@admin_required
def admin_dashboard():
    insights = _build_league_insights()
    return render_template('admin.html', insights=insights)

@admin_bp.route('/manage_stadiums', methods=['GET', 'POST'])
@admin_required
def manage_stadiums():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            stadium_id = request.form.get('stadium_id')
            name = request.form['name']
            location = request.form['location']
            capacity = request.form['capacity']

            if 'add' in request.form:
                cur.execute('INSERT INTO stadiums (name, location, capacity) VALUES (%s, %s, %s)', 
                            (name, location, capacity))
                flash('Stadium added successfully', 'success')
            elif 'edit' in request.form and stadium_id:
                cur.execute('UPDATE stadiums SET name = %s, location = %s, capacity = %s WHERE stadium_id = %s', 
                            (name, location, capacity, stadium_id))
                flash('Stadium updated successfully', 'success')
            elif 'delete' in request.form and stadium_id:
                cur.execute('DELETE FROM stadiums WHERE stadium_id = %s', (stadium_id,))
                flash('Stadium deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_stadiums'))

    cur.execute('SELECT stadium_id, name, location, capacity FROM stadiums')
    stadiums = cur.fetchall()
    cur.close()
    return render_template('manage_stadiums.html', stadiums=stadiums)

@admin_bp.route('/manage_leagues', methods=['GET', 'POST'])
@admin_required
def manage_leagues():
    db = get_db()
    cur = db.cursor()

    def _clean(value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    if request.method == 'POST':
        try:
            league_id = request.form.get('league_id')
            name = _clean(request.form.get('name'))
            country = _clean(request.form.get('country'))
            primary_color = _clean(request.form.get('primary_color'))
            secondary_color = _clean(request.form.get('secondary_color'))
            accent_color = _clean(request.form.get('accent_color'))
            text_color = _clean(request.form.get('text_color'))
            logo_url = _clean(request.form.get('logo_url'))
            hero_image_url = _clean(request.form.get('hero_image_url'))

            if not name or not country:
                flash('Name and country are required', 'error')
                return redirect(url_for('admin.manage_leagues'))

            if 'add' in request.form:
                cur.execute(
                    "INSERT INTO leagues (name, country, primary_color, secondary_color, accent_color, text_color, logo_url, hero_image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (name, country, primary_color, secondary_color, accent_color, text_color, logo_url, hero_image_url)
                )
                flash('League added successfully', 'success')
            elif 'edit' in request.form and league_id:
                cur.execute(
                    "UPDATE leagues SET name = %s, country = %s, primary_color = %s, secondary_color = %s, accent_color = %s, text_color = %s, logo_url = %s, hero_image_url = %s WHERE league_id = %s",
                    (name, country, primary_color, secondary_color, accent_color, text_color, logo_url, hero_image_url, league_id)
                )
                flash('League updated successfully', 'success')
            elif 'delete' in request.form:
                delete_id = request.form.get('deleteItemId') or league_id
                if delete_id:
                    cur.execute('DELETE FROM leagues WHERE league_id = %s', (delete_id,))
                    flash('League deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_leagues'))

    rows = []
    try:
        cur.execute(
            "SELECT league_id, name, country, primary_color, secondary_color, accent_color, text_color, logo_url, hero_image_url FROM leagues ORDER BY name"
        )
        rows = cur.fetchall()
    except Exception as e:
        db.rollback()
        flash('Failed to load leagues: ' + str(e), 'error')
    finally:
        cur.close()

    columns = ['id', 'name', 'country', 'primary_color', 'secondary_color', 'accent_color', 'text_color', 'logo_url', 'hero_image_url']
    leagues = [dict(zip(columns, row)) for row in rows]
    return render_template('manage_leagues.html', leagues=leagues)




@admin_bp.route('/league_homepage', methods=['GET', 'POST'])
@admin_required
def manage_league_homepage():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
    leagues = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    cur.close()

    selected_league_id = request.form.get('league_id') or request.args.get('league_id')
    if not selected_league_id and leagues:
        selected_league_id = str(leagues[0]['id'])
    league_id_int = int(selected_league_id) if selected_league_id else None

    config = _default_homepage_config()
    if league_id_int:
        cur = get_db().cursor()
        config = _load_homepage_config(cur, league_id_int)
        cur.close()

    if request.method == 'POST':
        action = request.form.get('action') or 'save'
        cur = get_db().cursor()
        try:
            if not league_id_int:
                flash('Please choose a league first.', 'error')
                return redirect(url_for('admin.manage_league_homepage'))

            if action == 'reset':
                _save_homepage_config(cur, league_id_int, _default_homepage_config())
                db.commit()
                flash('Homepage settings reset to defaults.', 'success')
            else:
                highlights = []
                for index in range(1, 4):
                    title = (request.form.get(f'highlight_title_{index}') or '').strip()
                    body = (request.form.get(f'highlight_body_{index}') or '').strip()
                    icon = (request.form.get(f'highlight_icon_{index}') or '').strip()
                    if title or body:
                        highlights.append({
                            'title': title,
                            'body': body,
                            'icon': icon or 'ph ph-star',
                        })

                config_payload = {
                    'title': (request.form.get('homepage_title') or '').strip() or None,
                    'subtitle': (request.form.get('homepage_subtitle') or '').strip() or None,
                    'background_url': (request.form.get('homepage_background_url') or '').strip() or None,
                    'cta_text': (request.form.get('homepage_cta_text') or '').strip() or None,
                    'cta_url': (request.form.get('homepage_cta_url') or '').strip() or None,
                    'highlights': highlights,
                }
                _save_homepage_config(cur, league_id_int, config_payload)
                db.commit()
                flash('Homepage content saved.', 'success')
        except Exception as exc:
            db.rollback()
            flash('Failed to update homepage: ' + str(exc), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_league_homepage', league_id=selected_league_id))

    if league_id_int:
        cur = get_db().cursor()
        config = _load_homepage_config(cur, league_id_int)
        cur.close()
    else:
        config = _default_homepage_config()

    highlights = list(config.get('highlights', []))
    while len(highlights) < 3:
        highlights.append({'title': '', 'body': '', 'icon': 'ph ph-star'})

    return render_template(
        'manage_league_homepage.html',
        leagues=leagues,
        selected_league_id=selected_league_id,
        config=config,
        highlights=highlights,
    )

@admin_bp.route('/manage_navigation', methods=['GET', 'POST'])
@admin_required
def manage_navigation():
    nav_config = _load_navigation_settings()
    current_links = nav_config.get('links', [])
    current_layout = nav_config.get('layout', 'top')

    if request.method == 'POST':
        submitted_layout = (request.form.get('nav_layout') or 'top').strip().lower()
        labels = request.form.getlist('nav_label[]')
        types = request.form.getlist('nav_type[]')
        values = request.form.getlist('nav_value[]')
        icons = request.form.getlist('nav_icon[]')
        audiences = request.form.getlist('nav_audience[]')

        nav_items: list[dict] = []
        for idx, label in enumerate(labels):
            label_text = (label or '').strip()
            value_text = (values[idx] if idx < len(values) else '').strip()
            if not label_text or not value_text:
                continue
            item_type = (types[idx] if idx < len(types) else 'url').strip().lower()
            if item_type not in {'url', 'endpoint'}:
                item_type = 'url'
            icon_value = (icons[idx] if idx < len(icons) else '').strip() or None
            audience_value = (audiences[idx] if idx < len(audiences) else 'everyone').strip().lower()
            if audience_value not in NAV_AUDIENCE_CHOICES:
                audience_value = 'everyone'
            open_in_new = bool(request.form.get(f'nav_newtab_{idx}'))
            nav_items.append({
                'label': label_text,
                'type': item_type,
                'value': value_text,
                'icon': icon_value,
                'audience': audience_value,
                'open_in_new': open_in_new,
            })

        if not nav_items:
            nav_items = [dict(item) for item in current_links]

        try:
            _persist_navigation_settings(submitted_layout, nav_items)
            flash('Navigation settings updated.', 'success')
        except Exception as exc:
            flash('Failed to update navigation: ' + str(exc), 'error')
        return redirect(url_for('admin.manage_navigation'))

    links_for_form = current_links if current_links else [
        {
            'label': '',
            'type': 'url',
            'value': '',
            'icon': '',
            'audience': 'everyone',
            'open_in_new': False,
        }
    ]

    return render_template(
        'manage_navigation.html',
        nav_links=links_for_form,
        nav_layout=current_layout,
        layout_choices=NAV_LAYOUT_CHOICES,
        audience_choices=NAV_AUDIENCE_CHOICES,
    )


@admin_bp.route('/league_finance_hub', methods=['GET', 'POST'])
@admin_required
def league_finance_hub():
    """Comprehensive league finance management hub"""
    db = get_db()
    try:
        _ensure_finance_hub_tables(db)
    except Exception as exc:
        flash('Failed to prepare finance hub storage: ' + str(exc), 'error')
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_in_person_payment':
            return _handle_add_in_person_payment(db)
        elif action == 'update_budget':
            return _handle_update_budget(db)
        elif action == 'generate_revenue_entry':
            return _handle_generate_revenue_entry(db)
        # Continue handling existing fee management actions
        else:
            return _handle_legacy_fee_actions(db)

    # Get league selection
    base_cur = db.cursor()
    base_cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
    leagues = [{'id': row[0], 'name': row[1]} for row in base_cur.fetchall()]
    base_cur.close()

    selected_league_id = request.form.get('league_id') or request.args.get('league_id')
    if not selected_league_id and leagues:
        selected_league_id = str(leagues[0]['id'])

    league_id_int = int(selected_league_id) if selected_league_id else None

    # Gather comprehensive financial data
    finance_data = _get_comprehensive_finance_data(db, league_id_int)

    return render_template('league_finance_hub.html',
                         leagues=leagues,
                         selected_league_id=selected_league_id,
                         current_datetime=datetime.now().strftime('%Y-%m-%d %H:%M'),
                         current_date=datetime.now().strftime('%Y-%m-%d'),
                         **finance_data)


@admin_bp.route('/manage_league_fees', methods=['GET', 'POST'])
@admin_required
def manage_league_fees():
    db = get_db()
    base_cur = db.cursor()
    base_cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
    leagues = [{'id': row[0], 'name': row[1]} for row in base_cur.fetchall()]
    base_cur.close()

    selected_league_id = request.form.get('league_id') or request.args.get('league_id')
    if not selected_league_id and leagues:
        selected_league_id = str(leagues[0]['id'])

    league_id_int = int(selected_league_id) if selected_league_id else None

    if request.method == 'POST':
        action = request.form.get('action')
        cur = db.cursor()
        try:
            if not league_id_int:
                flash('Please select a league to manage fees.', 'error')
                return redirect(url_for('admin.manage_league_fees'))

            if action == 'update_plan':
                total_fee_cents = _parse_amount_to_cents(request.form.get('total_fee')) or 0
                deposit_cents = _parse_amount_to_cents(request.form.get('deposit'))
                currency = (request.form.get('currency') or 'USD').upper()[:3]
                installments_enabled = True if request.form.get('installments_enabled') else False
                notes = (request.form.get('notes') or '').strip() or None
                now = datetime.utcnow().isoformat()

                plan = _get_league_fee_plan(cur, league_id_int)
                installment_count = request.form.get('installment_count')
                try:
                    installment_count_int = int(installment_count) if installment_count else 0
                except ValueError:
                    installment_count_int = 0

                if plan:
                    cur.execute(
                        "UPDATE league_fee_plans SET total_fee_cents = %s, deposit_cents = %s, currency = %s, notes = %s, installments_enabled = %s, installment_count = %s, updated_at = %s WHERE league_id = %s",
                        (total_fee_cents, deposit_cents, currency, notes, installments_enabled, installment_count_int, now, league_id_int)
                    )
                else:
                    cur.execute(
                        "INSERT INTO league_fee_plans (league_id, total_fee_cents, deposit_cents, currency, notes, installments_enabled, installment_count, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (league_id_int, total_fee_cents, deposit_cents, currency, notes, installments_enabled, installment_count_int, now, now)
                    )
                db.commit()
                flash('League fee plan saved.', 'success')

            elif action == 'add_installment':
                label = (request.form.get('label') or 'Installment').strip()
                amount_cents = _parse_amount_to_cents(request.form.get('amount'))
                if amount_cents is None:
                    raise ValueError('Installment amount is required.')
                due_date = request.form.get('due_date')
                notes = (request.form.get('installment_notes') or '').strip() or None

                plan = _ensure_league_fee_plan(cur, league_id_int)

                cur.execute(
                    "INSERT INTO league_fee_installments (plan_id, label, due_date, amount_cents, status, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                    (plan['plan_id'], label, due_date or None, amount_cents, request.form.get('status') or 'pending', notes)
                )
                db.commit()
                flash('Installment added.', 'success')

            elif action == 'delete_installment':
                installment_id = request.form.get('installment_id')
                if installment_id:
                    cur.execute('DELETE FROM league_installment_status WHERE installment_id = %s', (installment_id,))
                    cur.execute('DELETE FROM league_fee_installments WHERE installment_id = %s', (installment_id,))
                    db.commit()
                    flash('Installment removed.', 'success')

            elif action == 'update_status':
                installment_id = request.form.get('installment_id')
                team_id = request.form.get('team_id')
                status = (request.form.get('status') or 'pending').strip()
                if not installment_id or not team_id:
                    raise ValueError('Installment and team are required for status updates.')
                amount_paid_cents = _parse_amount_to_cents(request.form.get('amount_paid'))
                paid_at_value = request.form.get('paid_at')
                paid_at = None
                if paid_at_value:
                    try:
                        paid_at = datetime.strptime(paid_at_value, '%Y-%m-%d').date().isoformat()
                    except ValueError:
                        raise ValueError('Invalid paid date format.')
                notes = (request.form.get('status_notes') or '').strip() or None

                cur.execute(
                    'SELECT status_id FROM league_installment_status WHERE installment_id = %s AND team_id = %s',
                    (installment_id, team_id)
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        'UPDATE league_installment_status SET status = %s, amount_paid_cents = %s, paid_at = %s, notes = %s WHERE status_id = %s',
                        (status, amount_paid_cents, paid_at, notes, existing[0])
                    )
                else:
                    cur.execute(
                        'INSERT INTO league_installment_status (installment_id, team_id, status, amount_paid_cents, paid_at, notes) VALUES (%s, %s, %s, %s, %s, %s)',
                        (installment_id, team_id, status, amount_paid_cents, paid_at, notes)
                    )
                db.commit()
                flash('Installment status updated.', 'success')
        except ValueError as exc:
            db.rollback()
            flash(str(exc), 'error')
        except Exception as exc:
            db.rollback()
            flash('Operation failed: ' + str(exc), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_league_fees', league_id=selected_league_id))

    plan = None
    installments = []
    teams = []
    status_by_team = {}
    totals = {
        'installment_total_cents': 0,
        'deposit_display': None,
        'total_fee_display': None,
    }

    if league_id_int:
        cur = db.cursor()
        try:
            plan = _get_league_fee_plan(cur, league_id_int)
            if plan:
                totals['total_fee_display'] = plan['total_fee_display']
                totals['deposit_display'] = plan['deposit_display']

                cur.execute(
                    "SELECT installment_id, label, due_date, amount_cents, status, notes FROM league_fee_installments WHERE plan_id = %s ORDER BY due_date IS NULL, due_date",
                    (plan['plan_id'],)
                )
                rows = cur.fetchall()
                for row in rows:
                    installment_id, label, due_date, amount_cents, status, notes = row
                    if isinstance(due_date, datetime):
                        due_str = due_date.date().isoformat()
                    elif isinstance(due_date, date):
                        due_str = due_date.isoformat()
                    elif due_date:
                        due_str = str(due_date)
                    else:
                        due_str = ''
                    installments.append({
                        'installment_id': installment_id,
                        'label': label,
                        'due_date': due_str,
                        'amount_cents': amount_cents or 0,
                        'amount_display': _format_cents_to_decimal(amount_cents or 0),
                        'status': status or 'pending',
                        'notes': notes,
                    })
                    totals['installment_total_cents'] += amount_cents or 0

                cur.execute('SELECT team_id, name FROM teams WHERE league_id = %s ORDER BY name', (league_id_int,))
                teams = [{'team_id': row[0], 'name': row[1]} for row in cur.fetchall()]

                if installments and teams:
                    inst_ids = [inst['installment_id'] for inst in installments]
                    placeholders = ','.join(['%s'] * len(inst_ids))
                    cur.execute(
                        f'SELECT status_id, installment_id, team_id, status, amount_paid_cents, paid_at, notes FROM league_installment_status WHERE installment_id IN ({placeholders})',
                        tuple(inst_ids)
                    )
                    for status_row in cur.fetchall():
                        status_id, installment_id, team_id, status, amount_paid_cents, paid_at, notes = status_row
                        if isinstance(paid_at, datetime):
                            paid_date = paid_at.date().isoformat()
                        elif isinstance(paid_at, date):
                            paid_date = paid_at.isoformat()
                        elif paid_at:
                            paid_date = str(paid_at)
                        else:
                            paid_date = ''
                        status_by_team.setdefault(team_id, {})[installment_id] = {
                            'status_id': status_id,
                            'status': status or 'pending',
                            'amount_paid_cents': amount_paid_cents,
                            'amount_paid_display': _format_cents_to_decimal(amount_paid_cents) if amount_paid_cents is not None else None,
                            'paid_at': paid_date,
                            'notes': notes,
                        }
        finally:
            cur.close()

    totals['installment_total_display'] = _format_cents_to_decimal(totals['installment_total_cents']) if totals['installment_total_cents'] else None

    return render_template(
        'manage_league_fees.html',
        leagues=leagues,
        selected_league_id=selected_league_id,
        plan=plan,
        installments=installments,
        teams=teams,
        status_by_team=status_by_team,
        totals=totals,
    )




@admin_bp.route('/manage_league_rules', methods=['GET', 'POST'])
@admin_required
def manage_league_rules():
    db = get_db()
    try:
        _ensure_league_rules_table(db)
    except Exception as exc:
        flash('Failed to prepare league rules storage: ' + str(exc), 'error')
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action', 'save_rules')

        if action == 'add_custom_field':
            return _handle_add_custom_field(db)
        elif action == 'delete_custom_field':
            return _handle_delete_custom_field(db)
        elif action == 'save_rules':
            return _handle_save_rules(db)
        elif action == 'load_rules':
            return _handle_load_rules(db)

    # GET request - load all data
    cur = db.cursor()
    leagues = []
    rules = []
    custom_fields_by_league = {}

    try:
        cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
        leagues = cur.fetchall()

        # Get all league rules with custom fields
        cur.execute("""
            SELECT lr.league_id, l.name, lr.points_win, lr.points_draw, lr.points_loss,
                   lr.tiebreakers, lr.substitution_limit, lr.foreign_player_limit, lr.notes
            FROM league_rules lr
            JOIN leagues l ON lr.league_id = l.league_id
            ORDER BY l.name
        """)
        rules = cur.fetchall()

        # Get custom fields for each league
        cur.execute("""
            SELECT league_id, field_id, field_name, field_type, field_value, display_order, is_required
            FROM league_rules_custom_fields
            ORDER BY league_id, display_order, field_name
        """)
        for row in cur.fetchall():
            league_id = row[0]
            if league_id not in custom_fields_by_league:
                custom_fields_by_league[league_id] = []
            custom_fields_by_league[league_id].append({
                'field_id': row[1],
                'field_name': row[2],
                'field_type': row[3],
                'field_value': row[4],
                'display_order': row[5],
                'is_required': row[6]
            })

    except Exception as e:
        flash(f'Error loading league rules data: {str(e)}', 'error')
    finally:
        cur.close()

    return render_template('manage_league_rules.html',
                         leagues=leagues,
                         rules=rules,
                         custom_fields_by_league=custom_fields_by_league)


def _handle_add_custom_field(db):
    """Handle adding a new custom field"""
    try:
        league_id = int(request.form.get('league_id'))
        field_name = request.form.get('field_name', '').strip()
        field_type = request.form.get('field_type', 'text')
        field_value = request.form.get('field_value', '').strip()
        is_required = bool(request.form.get('is_required'))

        if not field_name:
            flash('Field name is required.', 'error')
            return redirect(url_for('admin.manage_league_rules'))

        cur = db.cursor()
        try:
            # Get next display order
            cur.execute(
                "SELECT COALESCE(MAX(display_order), 0) + 1 FROM league_rules_custom_fields WHERE league_id = %s",
                (league_id,)
            )
            display_order = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO league_rules_custom_fields
                (league_id, field_name, field_type, field_value, display_order, is_required)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (league_id, field_name, field_type, field_value or None, display_order, is_required))

            db.commit()
            flash(f'Custom field "{field_name}" added successfully.', 'success')
        except Exception as exc:
            db.rollback()
            if 'unique' in str(exc).lower():
                flash(f'Field "{field_name}" already exists for this league.', 'error')
            else:
                flash(f'Failed to add custom field: {str(exc)}', 'error')
        finally:
            cur.close()

    except (ValueError, TypeError):
        flash('Invalid league selection.', 'error')

    return redirect(url_for('admin.manage_league_rules'))


def _handle_delete_custom_field(db):
    """Handle deleting a custom field"""
    try:
        field_id = int(request.form.get('field_id'))

        cur = db.cursor()
        try:
            cur.execute("DELETE FROM league_rules_custom_fields WHERE field_id = %s", (field_id,))

            if cur.rowcount > 0:
                db.commit()
                flash('Custom field deleted successfully.', 'success')
            else:
                flash('Custom field not found.', 'error')
        except Exception as exc:
            db.rollback()
            flash(f'Failed to delete custom field: {str(exc)}', 'error')
        finally:
            cur.close()

    except (ValueError, TypeError):
        flash('Invalid field selection.', 'error')

    return redirect(url_for('admin.manage_league_rules'))


def _handle_save_rules(db):
    """Handle saving league rules and custom fields"""
    cur = db.cursor()
    try:
        league_id_value = request.form.get('league_id')
        if not league_id_value:
            flash('Please select a league before saving rules.', 'error')
            return redirect(url_for('admin.manage_league_rules'))

        try:
            league_id = int(league_id_value)
        except (TypeError, ValueError):
            flash('Invalid league selection.', 'error')
            return redirect(url_for('admin.manage_league_rules'))

        def _optional_int(value):
            if value is None or value == '':
                return None
            return int(value)

        # Save basic league rules
        points_win = int(request.form.get('points_win', 3) or 3)
        points_draw = int(request.form.get('points_draw', 1) or 1)
        points_loss = int(request.form.get('points_loss', 0) or 0)
        tiebreakers = (request.form.get('tiebreakers') or '').strip() or None
        substitution_limit = _optional_int(request.form.get('substitution_limit'))
        foreign_player_limit = _optional_int(request.form.get('foreign_player_limit'))
        notes = (request.form.get('notes') or '').strip() or None

        cur.execute("""
            INSERT INTO league_rules (league_id, points_win, points_draw, points_loss,
                                    tiebreakers, substitution_limit, foreign_player_limit, notes, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (league_id) DO UPDATE SET
                points_win = EXCLUDED.points_win,
                points_draw = EXCLUDED.points_draw,
                points_loss = EXCLUDED.points_loss,
                tiebreakers = EXCLUDED.tiebreakers,
                substitution_limit = EXCLUDED.substitution_limit,
                foreign_player_limit = EXCLUDED.foreign_player_limit,
                notes = EXCLUDED.notes,
                updated_at = CURRENT_TIMESTAMP
        """, (league_id, points_win, points_draw, points_loss, tiebreakers, substitution_limit, foreign_player_limit, notes))

        # Save custom field values
        for key, value in request.form.items():
            if key.startswith('custom_field_'):
                field_id = key.replace('custom_field_', '')
                try:
                    field_id_int = int(field_id)
                    cur.execute(
                        "UPDATE league_rules_custom_fields SET field_value = %s WHERE field_id = %s",
                        (value.strip() or None, field_id_int)
                    )
                except (ValueError, TypeError):
                    continue

        db.commit()
        flash('League rules saved successfully.', 'success')

    except Exception as exc:
        db.rollback()
        flash('Failed to save league rules: ' + str(exc), 'error')
    finally:
        cur.close()

    return redirect(url_for('admin.manage_league_rules'))


def _handle_load_rules(db):
    """Handle loading rules for a specific league (AJAX endpoint)"""
    try:
        league_id = int(request.form.get('league_id'))

        cur = db.cursor()
        try:
            # Get basic rules
            cur.execute("""
                SELECT points_win, points_draw, points_loss, tiebreakers,
                       substitution_limit, foreign_player_limit, notes
                FROM league_rules WHERE league_id = %s
            """, (league_id,))

            rules_data = cur.fetchone()

            # Get custom fields
            cur.execute("""
                SELECT field_id, field_name, field_type, field_value, is_required
                FROM league_rules_custom_fields
                WHERE league_id = %s
                ORDER BY display_order, field_name
            """, (league_id,))

            custom_fields = cur.fetchall()

            return {
                'success': True,
                'rules': rules_data,
                'custom_fields': custom_fields
            }

        finally:
            cur.close()

    except (ValueError, TypeError):
        return {'success': False, 'error': 'Invalid league selection'}
    except Exception as exc:
        return {'success': False, 'error': str(exc)}


@admin_bp.route('/manage_seasons', methods=['GET', 'POST'])
@admin_required
def manage_seasons():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            season_id = request.form.get('season_id')
            league_id = request.form['league_id']
            year = request.form['year']

            if 'add' in request.form:
                cur.execute('INSERT INTO seasons (league_id, year) VALUES (%s, %s)', (league_id, year))
                flash('Season added successfully', 'success')
            elif 'edit' in request.form and season_id:
                cur.execute('UPDATE seasons SET league_id = %s, year = %s WHERE season_id = %s', (league_id, year, season_id))
                flash('Season updated successfully', 'success')
            elif 'delete' in request.form:
                season_id = request.form['deleteItemId']
                cur.execute('DELETE FROM seasons WHERE season_id = %s', (season_id,))
                flash('Season deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_seasons'))

    cur.execute('''
        SELECT s.season_id, s.league_id, s.year, l.name
        FROM seasons s
        JOIN leagues l ON s.league_id = l.league_id
    ''')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_seasons.html', seasons=seasons, leagues=leagues)

@admin_bp.route('/manage_teams', methods=['GET', 'POST'])
@admin_required
def manage_teams():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            team_id = request.form.get('team_id')
            name = request.form['name']
            founded_year = request.form['founded_year']
            stadium_id = request.form['stadium_id']
            league_id = request.form['league_id']
            coach_id = request.form['coach_id']

            if 'add' in request.form:
                cur.execute('INSERT INTO teams (name, founded_year, stadium_id, league_id, coach_id) VALUES (%s, %s, %s, %s, %s)', 
                            (name, founded_year, stadium_id, league_id, coach_id))
                flash('Team added successfully', 'success')
            elif 'edit' in request.form and team_id:
                cur.execute('UPDATE teams SET name = %s, founded_year = %s, stadium_id = %s, league_id = %s, coach_id = %s WHERE team_id = %s', 
                            (name, founded_year, stadium_id, league_id, coach_id, team_id))
                flash('Team updated successfully', 'success')
            elif 'delete' in request.form and team_id:
                cur.execute('DELETE FROM teams WHERE team_id = %s', (team_id,))
                flash('Team deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_teams'))

    cur.execute('SELECT team_id, name, founded_year, stadium_id, league_id, coach_id FROM teams')
    teams = cur.fetchall()
    cur.execute('SELECT stadium_id, name FROM stadiums')
    stadiums = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.execute('SELECT coach_id, name FROM coaches')
    coaches = cur.fetchall()
    cur.close()
    return render_template('manage_teams.html', teams=teams, stadiums=stadiums, leagues=leagues, coaches=coaches)


@admin_bp.route('/manage_coaches', methods=['GET', 'POST'])
@admin_required
def manage_coaches():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            coach_id = request.form.get('coach_id')
            name = request.form['name']
            nationality = request.form['nationality']
            team_id = request.form['team_id']

            if 'add' in request.form:
                cur.execute('INSERT INTO coaches (name, nationality, team_id) VALUES (%s, %s, %s)', 
                            (name, nationality, team_id))
                flash('Coach added successfully', 'success')
            elif 'submit' in request.form and coach_id:
                cur.execute('UPDATE coaches SET name = %s, nationality = %s, team_id = %s WHERE coach_id = %s', 
                            (name, nationality, team_id, coach_id))
                flash('Coach updated successfully', 'success')
            elif 'delete' in request.form:
                coach_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM coaches WHERE coach_id = %s', (coach_id,))
                flash('Coach deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_coaches'))

    cur.execute('''
        SELECT c.coach_id, c.name, c.team_id, c.nationality, t.name AS team_name
        FROM coaches c
        JOIN teams t ON c.team_id = t.team_id
    ''')
    coaches = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.close()
    return render_template('manage_coaches.html', coaches=coaches, teams=teams)



@admin_bp.route('/manage_players', methods=['GET', 'POST'])
@admin_required
def manage_players():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            player_id = request.form.get('player_id')
            team_id = request.form['team_id']
            name = request.form['name']
            position = request.form['position']
            date_of_birth = request.form['date_of_birth']
            nationality = request.form['nationality']
            email = request.form.get('email', '')
            weight_kg = request.form.get('weight_kg') or None
            height_cm = request.form.get('height_cm') or None
            sport = request.form.get('sport', 'Football')

            if 'submit' in request.form:
                if player_id:
                    cur.execute('''UPDATE players SET team_id = %s, name = %s, position = %s, date_of_birth = %s,
                                   nationality = %s, email = %s, weight_kg = %s, height_cm = %s, sport = %s
                                   WHERE player_id = %s''',
                                (team_id, name, position, date_of_birth, nationality, email, weight_kg, height_cm, sport, player_id))
                    flash('Player updated successfully', 'success')
                else:
                    cur.execute('''INSERT INTO players (team_id, name, position, date_of_birth, nationality, email, weight_kg, height_cm, sport)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (team_id, name, position, date_of_birth, nationality, email, weight_kg, height_cm, sport))
                    flash('Player added successfully', 'success')
            elif 'delete' in request.form:
                player_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM players WHERE player_id = %s', (player_id,))
                flash('Player deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_players'))

    cur.execute('''SELECT p.player_id, t.name AS team, p.name, p.position, p.date_of_birth, p.nationality, p.team_id,
                          p.email, p.weight_kg, p.height_cm, p.sport
                   FROM players p JOIN teams t ON p.team_id = t.team_id''')
    players = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.execute('SELECT name, positions FROM sports ORDER BY name')
    sports = cur.fetchall()
    cur.close()
    return render_template('manage_players.html', players=players, teams=teams, sports=sports)


@admin_bp.route('/manage_news', methods=['GET', 'POST'])
@admin_required
def manage_news():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            news_id = request.form.get('news_id')
            title = request.form['title']
            content = request.form['content']
            summary = request.form.get('summary', '')
            category = request.form.get('category', 'General')
            status = request.form.get('status', 'draft')
            is_featured = request.form.get('is_featured') == 'on'
            show_on_homepage = request.form.get('show_on_homepage') == 'on'
            image_url = request.form.get('image_url', '')

            if 'submit' in request.form:
                if news_id:
                    # Update existing news
                    cur.execute('''UPDATE news SET title = %s, content = %s, summary = %s, category = %s,
                                   status = %s, is_featured = %s, show_on_homepage = %s, image_url = %s,
                                   updated_at = CURRENT_TIMESTAMP,
                                   published_at = CASE WHEN status = 'published' AND published_at IS NULL
                                                      THEN CURRENT_TIMESTAMP ELSE published_at END
                                   WHERE news_id = %s''',
                                (title, content, summary, category, status, is_featured, show_on_homepage, image_url, news_id))
                    flash('News article updated successfully', 'success')
                else:
                    # Create new news
                    published_at = 'CURRENT_TIMESTAMP' if status == 'published' else 'NULL'
                    cur.execute('''INSERT INTO news (title, content, summary, category, status, is_featured,
                                   show_on_homepage, image_url, published_at)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (title, content, summary, category, status, is_featured, show_on_homepage, image_url,
                                 'now()' if status == 'published' else None))
                    flash('News article created successfully', 'success')
            elif 'delete' in request.form:
                news_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM news WHERE news_id = %s', (news_id,))
                flash('News article deleted successfully', 'success')

            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_news'))

    # Get all news articles
    cur.execute('''SELECT news_id, title, summary, content, category, status, is_featured, show_on_homepage,
                   created_at, published_at, author_id FROM news ORDER BY created_at DESC''')
    news_articles = cur.fetchall()

    cur.close()
    return render_template('manage_news.html', news_articles=news_articles)


@admin_bp.route('/manage_sponsors', methods=['GET', 'POST'])
@admin_required
def manage_sponsors():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            if 'submit_sponsor' in request.form:
                sponsor_id = request.form.get('sponsor_id')
                company_name = request.form['company_name']
                contact_person = request.form.get('contact_person', '')
                email = request.form.get('email', '')
                phone = request.form.get('phone', '')
                website = request.form.get('website', '')
                address = request.form.get('address', '')
                industry = request.form.get('industry', '')
                company_size = request.form.get('company_size', '')
                annual_revenue_range = request.form.get('annual_revenue_range', '')
                status = request.form.get('status', 'prospect')
                priority = request.form.get('priority', 'medium')
                notes = request.form.get('notes', '')
                first_contact_date = request.form.get('first_contact_date') or None
                last_contact_date = request.form.get('last_contact_date') or None

                if sponsor_id:
                    # Update existing sponsor
                    cur.execute('''UPDATE sponsors SET company_name = %s, contact_person = %s, email = %s,
                                   phone = %s, website = %s, address = %s, industry = %s, company_size = %s,
                                   annual_revenue_range = %s, status = %s, priority = %s, notes = %s,
                                   first_contact_date = %s, last_contact_date = %s, updated_at = CURRENT_TIMESTAMP
                                   WHERE sponsor_id = %s''',
                                (company_name, contact_person, email, phone, website, address, industry,
                                 company_size, annual_revenue_range, status, priority, notes,
                                 first_contact_date, last_contact_date, sponsor_id))
                    flash('Sponsor updated successfully', 'success')
                else:
                    # Create new sponsor
                    cur.execute('''INSERT INTO sponsors (company_name, contact_person, email, phone, website,
                                   address, industry, company_size, annual_revenue_range, status, priority,
                                   notes, first_contact_date, last_contact_date, created_by)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (company_name, contact_person, email, phone, website, address, industry,
                                 company_size, annual_revenue_range, status, priority, notes,
                                 first_contact_date, last_contact_date, current_user.user_id if current_user.is_authenticated else None))
                    flash('Sponsor added successfully', 'success')

            elif 'submit_deal' in request.form:
                deal_id = request.form.get('deal_id')
                sponsor_id = request.form['deal_sponsor_id']
                deal_name = request.form['deal_name']
                deal_type = request.form.get('deal_type', 'other')
                sponsorship_level = request.form.get('sponsorship_level', 'bronze')
                deal_value = request.form.get('deal_value', '0')
                deal_value_cents = int(float(deal_value) * 100) if deal_value else 0
                currency = request.form.get('currency', 'USD')
                deal_status = request.form.get('deal_status', 'prospect')
                start_date = request.form.get('start_date') or None
                end_date = request.form.get('end_date') or None
                benefits_provided = request.form.get('benefits_provided', '')
                deliverables = request.form.get('deliverables', '')
                payment_terms = request.form.get('payment_terms', '')
                notes = request.form.get('deal_notes', '')

                if deal_id:
                    # Update existing deal
                    cur.execute('''UPDATE sponsorship_deals SET sponsor_id = %s, deal_name = %s, deal_type = %s,
                                   sponsorship_level = %s, deal_value_cents = %s, currency = %s, deal_status = %s,
                                   start_date = %s, end_date = %s, benefits_provided = %s, deliverables = %s,
                                   payment_terms = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                                   WHERE deal_id = %s''',
                                (sponsor_id, deal_name, deal_type, sponsorship_level, deal_value_cents, currency,
                                 deal_status, start_date, end_date, benefits_provided, deliverables,
                                 payment_terms, notes, deal_id))
                    flash('Deal updated successfully', 'success')
                else:
                    # Create new deal
                    cur.execute('''INSERT INTO sponsorship_deals (sponsor_id, deal_name, deal_type, sponsorship_level,
                                   deal_value_cents, currency, deal_status, start_date, end_date, benefits_provided,
                                   deliverables, payment_terms, notes, created_by)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (sponsor_id, deal_name, deal_type, sponsorship_level, deal_value_cents, currency,
                                 deal_status, start_date, end_date, benefits_provided, deliverables,
                                 payment_terms, notes, current_user.user_id if current_user.is_authenticated else None))
                    flash('Deal added successfully', 'success')

            elif 'delete_sponsor' in request.form:
                sponsor_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM sponsors WHERE sponsor_id = %s', (sponsor_id,))
                flash('Sponsor deleted successfully', 'success')

            elif 'delete_deal' in request.form:
                deal_id = request.form['deleteDealId']
                cur.execute('DELETE FROM sponsorship_deals WHERE deal_id = %s', (deal_id,))
                flash('Deal deleted successfully', 'success')

            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_sponsors'))

    # Get all sponsors with deal counts
    cur.execute('''SELECT s.sponsor_id, s.company_name, s.contact_person, s.email, s.phone, s.website,
                   s.address, s.industry, s.company_size, s.annual_revenue_range, s.status, s.priority,
                   s.notes, s.first_contact_date, s.last_contact_date, s.created_at,
                   COUNT(d.deal_id) as deal_count,
                   COALESCE(SUM(CASE WHEN d.deal_status = 'active' THEN d.deal_value_cents ELSE 0 END), 0) as active_value
                   FROM sponsors s
                   LEFT JOIN sponsorship_deals d ON s.sponsor_id = d.sponsor_id
                   GROUP BY s.sponsor_id
                   ORDER BY s.priority DESC, s.last_contact_date DESC''')
    sponsors = cur.fetchall()

    # Get all deals with sponsor info
    cur.execute('''SELECT d.deal_id, d.sponsor_id, s.company_name, d.deal_name, d.deal_type,
                   d.sponsorship_level, d.deal_value_cents, d.currency, d.deal_status,
                   d.start_date, d.end_date, d.benefits_provided, d.deliverables,
                   d.payment_terms, d.notes, d.created_at
                   FROM sponsorship_deals d
                   JOIN sponsors s ON d.sponsor_id = s.sponsor_id
                   ORDER BY d.deal_status, d.start_date DESC''')
    deals = cur.fetchall()

    cur.close()
    return render_template('manage_sponsors.html', sponsors=sponsors, deals=deals)


@admin_bp.route('/export_sponsors')
@admin_required
def export_sponsors():
    """Export sponsors data to Excel"""
    try:
        import pandas as pd
        from flask import send_file
        import tempfile
        import os
        from datetime import datetime

        db = get_db()
        cur = db.cursor()

        # Export sponsors
        cur.execute('''SELECT s.sponsor_id, s.company_name, s.contact_person, s.email, s.phone, s.website,
                       s.address, s.industry, s.company_size, s.annual_revenue_range, s.status, s.priority,
                       s.notes, s.first_contact_date, s.last_contact_date, s.created_at,
                       COUNT(d.deal_id) as deal_count,
                       COALESCE(SUM(CASE WHEN d.deal_status = 'active' THEN d.deal_value_cents ELSE 0 END), 0) as active_value
                       FROM sponsors s
                       LEFT JOIN sponsorship_deals d ON s.sponsor_id = d.sponsor_id
                       GROUP BY s.sponsor_id
                       ORDER BY s.company_name''')
        sponsors_data = cur.fetchall()

        # Export deals
        cur.execute('''SELECT d.deal_id, s.company_name as sponsor, d.deal_name, d.deal_type,
                       d.sponsorship_level, d.deal_value_cents, d.currency, d.deal_status,
                       d.start_date, d.end_date, d.benefits_provided, d.deliverables,
                       d.payment_terms, d.notes, d.created_at
                       FROM sponsorship_deals d
                       JOIN sponsors s ON d.sponsor_id = s.sponsor_id
                       ORDER BY s.company_name, d.deal_name''')
        deals_data = cur.fetchall()

        cur.close()

        # Create DataFrames
        sponsors_columns = ['ID', 'Company Name', 'Contact Person', 'Email', 'Phone', 'Website',
                           'Address', 'Industry', 'Company Size', 'Revenue Range', 'Status', 'Priority',
                           'Notes', 'First Contact Date', 'Last Contact Date', 'Created At',
                           'Deal Count', 'Active Value (cents)']

        deals_columns = ['Deal ID', 'Sponsor', 'Deal Name', 'Deal Type', 'Level', 'Value (cents)',
                        'Currency', 'Status', 'Start Date', 'End Date', 'Benefits', 'Deliverables',
                        'Payment Terms', 'Notes', 'Created At']

        sponsors_df = pd.DataFrame(sponsors_data, columns=sponsors_columns)
        deals_df = pd.DataFrame(deals_data, columns=deals_columns)

        # Format dates
        for date_col in ['First Contact Date', 'Last Contact Date', 'Created At']:
            if date_col in sponsors_df.columns:
                sponsors_df[date_col] = pd.to_datetime(sponsors_df[date_col]).dt.strftime('%Y-%m-%d')

        for date_col in ['Start Date', 'End Date', 'Created At']:
            if date_col in deals_df.columns:
                deals_df[date_col] = pd.to_datetime(deals_df[date_col]).dt.strftime('%Y-%m-%d')

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                sponsors_df.to_excel(writer, sheet_name='Sponsors', index=False)
                deals_df.to_excel(writer, sheet_name='Deals', index=False)

            filename = f"sponsorship_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            return send_file(tmp.name, as_attachment=True, download_name=filename,
                           mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('admin.manage_sponsors'))


@admin_bp.route('/import_sponsors', methods=['POST'])
@admin_required
def import_sponsors():
    """Import sponsors data from Excel"""
    try:
        import pandas as pd
        from werkzeug.utils import secure_filename

        if 'excel_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin.manage_sponsors'))

        file = request.files['excel_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin.manage_sponsors'))

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('Please upload an Excel file (.xlsx or .xls)', 'error')
            return redirect(url_for('admin.manage_sponsors'))

        # Read Excel file
        try:
            # Try to read sponsors sheet
            sponsors_df = pd.read_excel(file, sheet_name='Sponsors')
        except:
            # Fallback to first sheet
            sponsors_df = pd.read_excel(file)

        db = get_db()
        cur = db.cursor()

        imported_count = 0
        skipped_count = 0

        for _, row in sponsors_df.iterrows():
            try:
                company_name = str(row.get('Company Name', '')).strip()
                if not company_name:
                    skipped_count += 1
                    continue

                # Check if sponsor already exists
                cur.execute('SELECT sponsor_id FROM sponsors WHERE company_name = %s', (company_name,))
                existing = cur.fetchone()

                contact_person = str(row.get('Contact Person', '')) if pd.notna(row.get('Contact Person')) else None
                email = str(row.get('Email', '')) if pd.notna(row.get('Email')) else None
                phone = str(row.get('Phone', '')) if pd.notna(row.get('Phone')) else None
                website = str(row.get('Website', '')) if pd.notna(row.get('Website')) else None
                address = str(row.get('Address', '')) if pd.notna(row.get('Address')) else None
                industry = str(row.get('Industry', '')) if pd.notna(row.get('Industry')) else None
                company_size = str(row.get('Company Size', '')) if pd.notna(row.get('Company Size')) else None
                revenue_range = str(row.get('Revenue Range', '')) if pd.notna(row.get('Revenue Range')) else None
                status = str(row.get('Status', 'prospect')).lower() if pd.notna(row.get('Status')) else 'prospect'
                priority = str(row.get('Priority', 'medium')).lower() if pd.notna(row.get('Priority')) else 'medium'
                notes = str(row.get('Notes', '')) if pd.notna(row.get('Notes')) else None

                # Handle dates
                first_contact_date = None
                if pd.notna(row.get('First Contact Date')):
                    try:
                        first_contact_date = pd.to_datetime(row.get('First Contact Date')).strftime('%Y-%m-%d')
                    except:
                        pass

                last_contact_date = None
                if pd.notna(row.get('Last Contact Date')):
                    try:
                        last_contact_date = pd.to_datetime(row.get('Last Contact Date')).strftime('%Y-%m-%d')
                    except:
                        pass

                if existing:
                    # Update existing sponsor
                    cur.execute('''UPDATE sponsors SET contact_person = %s, email = %s, phone = %s,
                                   website = %s, address = %s, industry = %s, company_size = %s,
                                   annual_revenue_range = %s, status = %s, priority = %s, notes = %s,
                                   first_contact_date = %s, last_contact_date = %s, updated_at = CURRENT_TIMESTAMP
                                   WHERE company_name = %s''',
                                (contact_person, email, phone, website, address, industry,
                                 company_size, revenue_range, status, priority, notes,
                                 first_contact_date, last_contact_date, company_name))
                else:
                    # Create new sponsor
                    cur.execute('''INSERT INTO sponsors (company_name, contact_person, email, phone, website,
                                   address, industry, company_size, annual_revenue_range, status, priority,
                                   notes, first_contact_date, last_contact_date, created_by)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (company_name, contact_person, email, phone, website, address, industry,
                                 company_size, revenue_range, status, priority, notes,
                                 first_contact_date, last_contact_date, current_user.user_id if current_user.is_authenticated else None))

                imported_count += 1

            except Exception as e:
                print(f"Error processing row: {str(e)}")
                skipped_count += 1
                continue

        db.commit()
        cur.close()

        flash(f'Import completed: {imported_count} sponsors imported/updated, {skipped_count} skipped', 'success')

    except Exception as e:
        flash(f'Import failed: {str(e)}', 'error')

    return redirect(url_for('admin.manage_sponsors'))


@admin_bp.route('/export_players')
@admin_required
def export_players():
    """Export players data to Excel"""
    try:
        import pandas as pd
        from flask import send_file
        import tempfile
        from datetime import datetime

        db = get_db()
        cur = db.cursor()

        # Export players with team info
        cur.execute('''SELECT p.player_id, p.name, p.email, p.date_of_birth, p.position,
                       p.nationality, p.weight_kg, p.height_cm, p.sport,
                       t.name as team_name, s.year as season_year, l.name as league_name
                       FROM players p
                       LEFT JOIN teams t ON p.team_id = t.team_id
                       LEFT JOIN seasons s ON t.league_id = s.league_id
                       LEFT JOIN leagues l ON t.league_id = l.league_id
                       ORDER BY p.name''')
        players_data = cur.fetchall()

        cur.close()

        # Create DataFrame
        columns = ['Player ID', 'Name', 'Email', 'Date of Birth', 'Position',
                  'Nationality', 'Weight (kg)', 'Height (cm)', 'Sport',
                  'Team', 'Season Year', 'League']

        players_df = pd.DataFrame(players_data, columns=columns)

        # Format dates
        if 'Date of Birth' in players_df.columns:
            players_df['Date of Birth'] = pd.to_datetime(players_df['Date of Birth']).dt.strftime('%Y-%m-%d')

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                players_df.to_excel(writer, sheet_name='Players', index=False)

            filename = f"players_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            return send_file(tmp.name, as_attachment=True, download_name=filename,
                           mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('admin.manage_players'))


@admin_bp.route('/import_players', methods=['POST'])
@admin_required
def import_players():
    """Import players data from Excel"""
    try:
        import pandas as pd

        if 'excel_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin.manage_players'))

        file = request.files['excel_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin.manage_players'))

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            flash('Please upload an Excel file (.xlsx or .xls)', 'error')
            return redirect(url_for('admin.manage_players'))

        # Read Excel file
        try:
            # Try to read players sheet
            players_df = pd.read_excel(file, sheet_name='Players')
        except:
            # Fallback to first sheet
            players_df = pd.read_excel(file)

        db = get_db()
        cur = db.cursor()

        imported_count = 0
        skipped_count = 0

        for _, row in players_df.iterrows():
            try:
                name = str(row.get('Name', '')).strip()
                if not name:
                    skipped_count += 1
                    continue

                email = str(row.get('Email', '')) if pd.notna(row.get('Email')) else None
                phone = str(row.get('Phone', '')) if pd.notna(row.get('Phone')) else None
                position = str(row.get('Position', '')) if pd.notna(row.get('Position')) else None
                jersey_number = None
                if pd.notna(row.get('Jersey Number')):
                    try:
                        jersey_number = int(row.get('Jersey Number'))
                    except:
                        pass

                emergency_contact_name = str(row.get('Emergency Contact Name', '')) if pd.notna(row.get('Emergency Contact Name')) else None
                emergency_contact_phone = str(row.get('Emergency Contact Phone', '')) if pd.notna(row.get('Emergency Contact Phone')) else None

                # Handle date of birth
                date_of_birth = None
                if pd.notna(row.get('Date of Birth')):
                    try:
                        date_of_birth = pd.to_datetime(row.get('Date of Birth')).strftime('%Y-%m-%d')
                    except:
                        pass

                # Find team by name if provided
                team_id = None
                team_name = str(row.get('Team', '')) if pd.notna(row.get('Team')) else None
                if team_name:
                    cur.execute('SELECT team_id FROM teams WHERE team_name = %s LIMIT 1', (team_name,))
                    team_result = cur.fetchone()
                    if team_result:
                        team_id = team_result[0]

                # Check if player already exists
                cur.execute('SELECT player_id FROM players WHERE name = %s AND email = %s', (name, email))
                existing = cur.fetchone()

                if existing:
                    # Update existing player
                    cur.execute('''UPDATE players SET phone = %s, date_of_birth = %s, position = %s,
                                   jersey_number = %s, emergency_contact_name = %s, emergency_contact_phone = %s,
                                   team_id = %s WHERE player_id = %s''',
                                (phone, date_of_birth, position, jersey_number, emergency_contact_name,
                                 emergency_contact_phone, team_id, existing[0]))
                else:
                    # Create new player
                    cur.execute('''INSERT INTO players (name, email, phone, date_of_birth, position,
                                   jersey_number, emergency_contact_name, emergency_contact_phone, team_id)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                                (name, email, phone, date_of_birth, position, jersey_number,
                                 emergency_contact_name, emergency_contact_phone, team_id))

                imported_count += 1

            except Exception as e:
                print(f"Error processing row: {str(e)}")
                skipped_count += 1
                continue

        db.commit()
        cur.close()

        flash(f'Import completed: {imported_count} players imported/updated, {skipped_count} skipped', 'success')

    except Exception as e:
        flash(f'Import failed: {str(e)}', 'error')

    return redirect(url_for('admin.manage_players'))


@admin_bp.route('/generate_fixtures', methods=['GET', 'POST'])
@admin_required
def generate_fixtures():
    db = get_db()

    if request.method == 'POST':
        cur = db.cursor()
        try:
            league_id_value = request.form.get('league_id')
            season_id_value = request.form.get('season_id')
            start_date_value = request.form.get('start_date')
            interval_value = request.form.get('interval_days') or '7'
            double_round = 'double_round' in request.form
            shuffle_teams = 'shuffle' in request.form

            try:
                league_id = int(league_id_value)
                season_id = int(season_id_value)
            except (TypeError, ValueError):
                flash('Please choose a league and season before generating fixtures.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            try:
                interval_days = int(interval_value)
                if interval_days < 1:
                    raise ValueError
            except (TypeError, ValueError):
                flash('Interval between rounds must be at least one day.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            try:
                start_date = datetime.strptime(start_date_value, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                flash('Please provide a valid start date.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            cur.execute('SELECT league_id FROM seasons WHERE season_id = %s', (season_id,))
            season_row = cur.fetchone()
            if not season_row:
                flash('Selected season could not be found.', 'error')
                return redirect(url_for('admin.generate_fixtures'))
            if season_row[0] != league_id:
                flash('Selected season does not belong to that league.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            cur.execute('SELECT team_id FROM teams WHERE league_id = %s ORDER BY name', (league_id,))
            team_rows = cur.fetchall()
            team_ids = [row[0] for row in team_rows]
            if len(team_ids) < 2:
                flash('At least two teams are required to generate fixtures.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            if shuffle_teams:
                random.shuffle(team_ids)

            schedule = _round_robin_schedule(team_ids, double_round=double_round)
            if not schedule:
                flash('No fixtures generated because there were not enough teams.', 'error')
                return redirect(url_for('admin.generate_fixtures'))

            cur.execute('SELECT home_team_id, away_team_id FROM matches WHERE league_id = %s AND season_id = %s', (league_id, season_id))
            existing_pairs = {(row[0], row[1]) for row in cur.fetchall()}

            created = 0
            skipped = 0
            for round_index, pairings in enumerate(schedule):
                round_datetime = datetime.combine(start_date + timedelta(days=interval_days * round_index), datetime.min.time())
                for home_team_id, away_team_id in pairings:
                    if (home_team_id, away_team_id) in existing_pairs:
                        skipped += 1
                        continue
                    cur.execute(
                        'INSERT INTO matches (utc_date, home_team_id, away_team_id, season_id, league_id) VALUES (%s, %s, %s, %s, %s)',
                        (round_datetime, home_team_id, away_team_id, season_id, league_id)
                    )
                    existing_pairs.add((home_team_id, away_team_id))
                    created += 1

            if created:
                db.commit()
            else:
                db.rollback()

            if created:
                message = f"Generated {created} fixture{'s' if created != 1 else ''}."
                if skipped:
                    message += f" Skipped {skipped} existing pairing{'s' if skipped != 1 else ''}."
                flash(message, 'success')
            else:
                info_message = 'No new fixtures were generated; an identical schedule already exists.' if skipped else 'No fixtures were generated.'
                flash(info_message, 'info')
        except Exception as exc:
            db.rollback()
            flash('Failed to generate fixtures: ' + str(exc), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.generate_fixtures'))

    cur = db.cursor()
    try:
        cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
        leagues = cur.fetchall()
        cur.execute('SELECT season_id, year, league_id FROM seasons ORDER BY year DESC, season_id DESC')
        seasons = cur.fetchall()
    finally:
        cur.close()
    return render_template('generate_fixtures.html', leagues=leagues, seasons=seasons)


@admin_bp.route('/manage_matches', methods=['GET', 'POST'])
@admin_required
def manage_matches():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            match_id = request.form.get('match_id')
            date = request.form['date']
            team1_id = request.form['team1_id']
            team2_id = request.form['team2_id']
            season_id = request.form['season_id']
            league_id = request.form['league_id']

            if 'submit' in request.form:
                if match_id:
                    cur.execute('UPDATE matches SET utc_date = %s, home_team_id = %s, away_team_id = %s, season_id = %s, league_id = %s WHERE match_id = %s', 
                                (date, team1_id, team2_id, season_id, league_id, match_id))
                    flash('Match updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO matches (utc_date, home_team_id, away_team_id, season_id, league_id) VALUES (%s, %s, %s, %s, %s)', 
                                (date, team1_id, team2_id, season_id, league_id))
                    flash('Match added successfully', 'success')
            elif 'delete' in request.form:
                match_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM matches WHERE match_id = %s', (match_id,))
                flash('Match deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_matches'))

    cur.execute('''
        SELECT m.match_id, m.utc_date, t1.name AS team1, t2.name AS team2, s.year AS season, l.name AS league,
               m.home_team_id, m.away_team_id
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        JOIN seasons s ON m.season_id = s.season_id
        JOIN leagues l ON m.league_id = l.league_id
    ''')
    matches = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.execute('SELECT season_id, year FROM seasons')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_matches.html', matches=matches, teams=teams, seasons=seasons, leagues=leagues)



@admin_bp.route('/manage_countries', methods=['GET', 'POST'])
@admin_required
def manage_countries():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            country_id = request.form.get('country_id')
            name = request.form['name']
            flag_url = request.form['flag_url']

            if 'submit' in request.form:
                if country_id:
                    cur.execute('UPDATE countries SET name = %s, flag_url = %s WHERE country_id = %s', 
                                (name, flag_url, country_id))
                    flash('Country updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO countries (name, flag_url) VALUES (%s, %s)', 
                                (name, flag_url))
                    flash('Country added successfully', 'success')
            elif 'delete' in request.form:
                country_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM countries WHERE country_id = %s', (country_id,))
                flash('Country deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_countries'))

    cur.execute('SELECT country_id, name, flag_url FROM countries')
    countries = cur.fetchall()
    cur.close()
    return render_template('manage_countries.html', countries=countries)



@admin_bp.route('/manage_referees', methods=['GET', 'POST'])
@admin_required
def manage_referees():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            referee_id = request.form.get('referee_id')
            name = request.form['name']
            nationality = request.form['nationality']

            if 'submit' in request.form:
                if referee_id:
                    cur.execute('UPDATE referees SET name = %s, nationality = %s WHERE referee_id = %s', 
                                (name, nationality, referee_id))
                    flash('Referee updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO referees (name, nationality) VALUES (%s, %s)', 
                                (name, nationality))
                    flash('Referee added successfully', 'success')
            elif 'delete' in request.form:
                referee_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM referees WHERE referee_id = %s', (referee_id,))
                flash('Referee deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_referees'))

    cur.execute('SELECT referee_id, name, nationality FROM referees')
    referees = cur.fetchall()
    cur.close()
    return render_template('manage_referees.html', referees=referees)



@admin_bp.route('/manage_scorers', methods=['GET', 'POST'])
@admin_required
def manage_scorers():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            scorer_id = request.form.get('scorer_id')
            player_id = request.form['player_id']
            season_id = request.form['season_id']
            league_id = request.form['league_id']
            goals = request.form['goals']
            assists = request.form['assists']
            penalties = request.form['penalties']

            if 'submit' in request.form:
                if scorer_id:
                    cur.execute('UPDATE scorers SET player_id = %s, season_id = %s, league_id = %s, goals = %s, assists = %s, penalties = %s WHERE scorer_id = %s',
                                (player_id, season_id, league_id, goals, assists, penalties, scorer_id))
                    flash('Scorer updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO scorers (player_id, season_id, league_id, goals, assists, penalties) VALUES (%s, %s, %s, %s, %s, %s)',
                                (player_id, season_id, league_id, goals, assists, penalties))
                    flash('Scorer added successfully', 'success')
            elif 'delete' in request.form:
                scorer_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM scorers WHERE scorer_id = %s', (scorer_id,))
                flash('Scorer deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_scorers'))

    cur.execute('''
        SELECT s.scorer_id, p.name, se.year, l.name, s.goals, s.assists, s.penalties 
        FROM scorers s 
        JOIN players p ON s.player_id = p.player_id 
        JOIN seasons se ON s.season_id = se.season_id 
        JOIN leagues l ON s.league_id = l.league_id
    ''')
    scorers = cur.fetchall()
    cur.execute('SELECT player_id, name FROM players')
    players = cur.fetchall()
    cur.execute('SELECT season_id, year FROM seasons')
    seasons = cur.fetchall()
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()
    cur.close()
    return render_template('manage_scorers.html', scorers=scorers, players=players, seasons=seasons, leagues=leagues)



@admin_bp.route('/recalculate_standings', methods=['GET', 'POST'])
@admin_required
def recalculate_standings():
    db = get_db()
    results = []
    selected_league_id = None
    selected_season_id = None

    try:
        _ensure_league_rules_table(db)
    except Exception as exc:
        flash('Failed to prepare league rules storage: ' + str(exc), 'error')
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        cur = db.cursor()
        try:
            league_id_value = request.form.get('league_id')
            season_id_value = request.form.get('season_id')
            save_flag = bool(request.form.get('save'))

            try:
                league_id = int(league_id_value)
                season_id = int(season_id_value)
            except (TypeError, ValueError):
                flash('Please choose both a league and season.', 'error')
                return redirect(url_for('admin.recalculate_standings'))

            selected_league_id = league_id
            selected_season_id = season_id

            cur.execute('SELECT league_id FROM seasons WHERE season_id = %s', (season_id,))
            season_row = cur.fetchone()
            if not season_row:
                flash('Selected season could not be found.', 'error')
                return redirect(url_for('admin.recalculate_standings'))
            if season_row[0] != league_id:
                flash('Season does not belong to the selected league.', 'error')
                return redirect(url_for('admin.recalculate_standings'))

            cur.execute('SELECT points_win, points_draw, points_loss, tiebreakers FROM league_rules WHERE league_id = %s', (league_id,))
            rules_row = cur.fetchone()
            points_win = int(rules_row[0]) if rules_row and rules_row[0] is not None else 3
            points_draw = int(rules_row[1]) if rules_row and rules_row[1] is not None else 1
            points_loss = int(rules_row[2]) if rules_row and rules_row[2] is not None else 0
            tiebreakers = _parse_tiebreakers(rules_row[3] if rules_row else None)

            cur.execute('SELECT team_id, name FROM teams WHERE league_id = %s', (league_id,))
            team_rows = cur.fetchall()
            team_names = {row[0]: row[1] for row in team_rows}
            stats = {team_id: _init_standing_record(team_id, name) for team_id, name in team_names.items()}

            cur.execute(
                """
                SELECT m.match_id, m.utc_date, m.home_team_id, m.away_team_id,
                       sc.full_time_home, sc.full_time_away
                FROM matches m
                LEFT JOIN scores sc ON sc.match_id = m.match_id
                WHERE m.league_id = %s AND m.season_id = %s
                ORDER BY m.utc_date ASC, m.match_id ASC
                """,
                (league_id, season_id)
            )
            match_rows = cur.fetchall()

            for row in match_rows:
                home_team_id = row[2]
                away_team_id = row[3]
                home_score = row[4]
                away_score = row[5]

                if home_team_id is None or away_team_id is None:
                    continue

                if home_team_id not in stats:
                    stats[home_team_id] = _init_standing_record(home_team_id, team_names.get(home_team_id, f'Team {home_team_id}'))
                if away_team_id not in stats:
                    stats[away_team_id] = _init_standing_record(away_team_id, team_names.get(away_team_id, f'Team {away_team_id}'))

                if home_score is None or away_score is None:
                    continue

                home_stat = stats[home_team_id]
                away_stat = stats[away_team_id]

                home_stat['played_games'] += 1
                away_stat['played_games'] += 1
                home_stat['goals_for'] += home_score
                home_stat['goals_against'] += away_score
                away_stat['goals_for'] += away_score
                away_stat['goals_against'] += home_score

                if home_score > away_score:
                    home_stat['won'] += 1
                    away_stat['lost'] += 1
                    home_stat['form'].append('W')
                    away_stat['form'].append('L')
                elif home_score < away_score:
                    home_stat['lost'] += 1
                    away_stat['won'] += 1
                    home_stat['form'].append('L')
                    away_stat['form'].append('W')
                else:
                    home_stat['draw'] += 1
                    away_stat['draw'] += 1
                    home_stat['form'].append('D')
                    away_stat['form'].append('D')

            if not stats:
                flash('No teams found for the selected league.', 'info')
            else:
                for team_id, record in stats.items():
                    goal_difference = record['goals_for'] - record['goals_against']
                    points = record['won'] * points_win + record['draw'] * points_draw + record['lost'] * points_loss
                    recent_form = record['form'][-5:]
                    results.append({
                        'team_id': team_id,
                        'team_name': record['team_name'],
                        'played_games': record['played_games'],
                        'won': record['won'],
                        'draw': record['draw'],
                        'lost': record['lost'],
                        'goals_for': record['goals_for'],
                        'goals_against': record['goals_against'],
                        'goal_difference': goal_difference,
                        'points': points,
                        'form': ' '.join(recent_form),
                    })

                results.sort(key=lambda r, tb=tiebreakers: _standing_sort_key(r, tb))
                for position, entry in enumerate(results, start=1):
                    entry['position'] = position

                if save_flag and results:
                    try:
                        for entry in results:
                            cur.execute('DELETE FROM standings WHERE team_id = %s', (entry['team_id'],))
                        for entry in results:
                            cur.execute(
                                'INSERT INTO standings (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                                (
                                    entry['position'], entry['team_id'], entry['played_games'], entry['won'],
                                    entry['draw'], entry['lost'], entry['points'], entry['goals_for'],
                                    entry['goals_against'], entry['goal_difference'], entry['form']
                                )
                            )
                        db.commit()
                        flash('Standings recalculated and saved.', 'success')
                    except Exception as exc:
                        db.rollback()
                        results = []
                        flash('Failed to save standings: ' + str(exc), 'error')
                elif results:
                    flash('Standings recalculated.', 'success')
                else:
                    flash('No completed matches found to calculate standings.', 'info')
        except Exception as exc:
            db.rollback()
            results = []
            flash('Failed to recalculate standings: ' + str(exc), 'error')
        finally:
            cur.close()

    cur = db.cursor()
    try:
        cur.execute('SELECT league_id, name FROM leagues ORDER BY name')
        leagues = cur.fetchall()
        cur.execute('SELECT season_id, year, league_id FROM seasons ORDER BY year DESC, season_id DESC')
        seasons = cur.fetchall()
    finally:
        cur.close()
    return render_template('recalculate_standings.html', leagues=leagues, seasons=seasons, results=results, league_id=selected_league_id, season_id=selected_season_id)


@admin_bp.route('/manage_scores', methods=['GET', 'POST'])
@admin_required
def manage_scores():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            score_id = request.form.get('score_id')
            match_id = request.form['match_id']
            full_time_home = request.form['full_time_home']
            full_time_away = request.form['full_time_away']
            half_time_home = request.form['half_time_home']
            half_time_away = request.form['half_time_away']

            if 'submit' in request.form:
                if score_id:
                    cur.execute('UPDATE scores SET match_id = %s, full_time_home = %s, full_time_away = %s, half_time_home = %s, half_time_away = %s WHERE score_id = %s',
                                (match_id, full_time_home, full_time_away, half_time_home, half_time_away, score_id))
                    flash('Score updated successfully', 'success')
                else:
                    cur.execute('INSERT INTO scores (match_id, full_time_home, full_time_away, half_time_home, half_time_away) VALUES (%s, %s, %s, %s, %s)',
                                (match_id, full_time_home, full_time_away, half_time_home, half_time_away))
                    flash('Score added successfully', 'success')
            elif 'delete' in request.form:
                score_id = request.form['deleteEntityId']
                cur.execute('DELETE FROM scores WHERE score_id = %s', (score_id,))
                flash('Score deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_scores'))

    cur.execute('SELECT s.score_id, m.utc_date, s.full_time_home, s.full_time_away, s.half_time_home, s.half_time_away FROM scores s JOIN matches m ON s.match_id = m.match_id')
    scores = cur.fetchall()
    cur.execute('SELECT match_id, utc_date FROM matches')
    matches = cur.fetchall()
    cur.close()
    return render_template('manage_scores.html', scores=scores, matches=matches)



@admin_bp.route('/manage_standings', methods=['GET', 'POST'])
@admin_required
def manage_standings():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        try:
            standing_id = request.form.get('standing_id')
            position = request.form['position']
            team_id = request.form['team_id']
            played_games = request.form['played_games']
            won = request.form['won']
            draw = request.form['draw']
            lost = request.form['lost']
            points = request.form['points']
            goals_for = request.form['goals_for']
            goals_against = request.form['goals_against']
            goal_difference = request.form['goal_difference']
            form = request.form['form']

            if 'add' in request.form:
                cur.execute('''
                    INSERT INTO standings (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form))
                flash('Standing added successfully', 'success')
            elif 'edit' in request.form and standing_id:
                cur.execute('''
                    UPDATE standings
                    SET position = %s, team_id = %s, played_games = %s, won = %s, draw = %s, lost = %s, points = %s, goals_for = %s, goals_against = %s, goal_difference = %s, form = %s
                    WHERE standing_id = %s
                ''', (position, team_id, played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form, standing_id))
                flash('Standing updated successfully', 'success')
            elif 'delete' in request.form:
                standing_id = request.form['deleteItemId']
                cur.execute('DELETE FROM standings WHERE standing_id = %s', (standing_id,))
                flash('Standing deleted successfully', 'success')
            db.commit()
        except Exception as e:
            db.rollback()
            flash('An error occurred: ' + str(e), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.manage_standings'))

    cur.execute('''
        SELECT s.standing_id, s.position, t.name, s.played_games, s.won, s.draw, s.lost, s.points, s.goals_for, s.goals_against, s.goal_difference, s.form, s.team_id
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
    ''')
    standings = cur.fetchall()
    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()
    cur.close()
    return render_template('manage_standings.html', standings=standings, teams=teams)

@admin_bp.route('/manage_users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    org = getattr(g, 'org', None)

    user_id_raw = (request.form.get('user_id') or '').strip() if request.method == 'POST' else ''
    is_admin = request.form.get('is_admin') == 'true' if request.method == 'POST' else False

    def _update_orm_user(orm_id: str) -> bool:
        query = db.session.query(User)
        if org is not None:
            query = query.filter_by(org_id=org.id)
        target = query.filter(User.id == orm_id).first()
        if not target:
            return False
        if target.role == UserRole.OWNER:
            flash('Owners already have full privileges.', 'info')
            return True
        target.role = UserRole.ADMIN if is_admin else UserRole.VIEWER
        db.session.commit()
        flash('User privilege updated successfully.', 'success')
        return True

    def _update_legacy_user(legacy_id: int) -> bool:
        sql_db = get_db()
        cur = sql_db.cursor()
        try:
            cur.execute('UPDATE users SET is_admin = %s WHERE user_id = %s', (is_admin, legacy_id))
            if cur.rowcount:
                sql_db.commit()
                flash('User privilege updated successfully.', 'success')
                return True
            sql_db.rollback()
            return False
        except Exception as exc:
            sql_db.rollback()
            flash('Failed to update legacy user: ' + str(exc), 'error')
            return True
        finally:
            cur.close()

    if request.method == 'POST':
        if not user_id_raw:
            flash('Please select a user before updating privileges.', 'error')
            return redirect(url_for('admin.manage_users'))

        updated = False
        if user_id_raw.startswith('legacy:'):
            try:
                legacy_id = int(user_id_raw.split(':', 1)[1])
            except ValueError:
                flash('Invalid user selection.', 'error')
                return redirect(url_for('admin.manage_users'))
            updated = _update_legacy_user(legacy_id)
        else:
            updated = _update_orm_user(user_id_raw)

        if not updated:
            flash('User not found for this organization.', 'error')
            db.session.rollback()
        db.session.expire_all()
        return redirect(url_for('admin.manage_users'))

    query = db.session.query(User)
    if org is not None:
        query = query.filter_by(org_id=org.id)
    orm_users = query.order_by(User.email.asc()).all()

    legacy_rows = []
    try:
        sql_db = get_db()
        cur = sql_db.cursor()
        cur.execute('SELECT user_id, username, is_admin FROM users ORDER BY username ASC')
        legacy_rows = cur.fetchall()
    except Exception:
        legacy_rows = []
    finally:
        try:
            cur.close()
        except Exception:
            pass

    user_rows = [
        {
            'id': orm_user.id,
            'email': orm_user.email,
            'is_admin': orm_user.role in (UserRole.ADMIN, UserRole.OWNER),
        }
        for orm_user in orm_users
    ]

    for legacy_id, username, is_admin_flag in legacy_rows:
        user_rows.append(
            {
                'id': f'legacy:{legacy_id}',
                'email': username,
                'is_admin': bool(is_admin_flag),
            }
        )

    if current_user.is_authenticated:
        current_id = getattr(current_user, 'id', None)
        current_email = getattr(current_user, 'email', None)
        if current_id and current_email:
            if current_id not in {row['id'] for row in user_rows}:
                user_rows.append(
                    {
                        'id': current_id,
                        'email': current_email,
                        'is_admin': current_user.has_role(UserRole.OWNER, UserRole.ADMIN) if hasattr(current_user, 'has_role') else False,
                    }
                )

    user_rows.sort(key=lambda row: row['email'].lower())

    flash(f'Loaded {len(user_rows)} users', 'info')
    return render_template('manage_users.html', users=user_rows)









@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def site_settings():
    db = get_db()
    settings = _load_site_settings()
    if request.method == 'POST':
        site_title = (request.form.get('site_title') or '').strip() or 'Sports League Management System'
        brand_image_url = (request.form.get('brand_image_url') or '').strip() or None
        primary_color = (request.form.get('primary_color') or '#343a40').strip() or '#343a40'
        try:
            cur = db.cursor()
            cur.execute('SELECT id FROM site_settings ORDER BY id ASC LIMIT 1')
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE site_settings SET site_title = %s, brand_image_url = %s, primary_color = %s, updated_at = NOW() WHERE id = %s",
                    (site_title, brand_image_url, primary_color, row[0])
                )
            else:
                cur.execute(
                    "INSERT INTO site_settings (site_title, brand_image_url, primary_color) VALUES (%s, %s, %s)",
                    (site_title, brand_image_url, primary_color)
                )
            db.commit()
            invalidate_site_settings_cache()
            flash('Site settings updated.', 'success')
        except Exception as exc:
            db.rollback()
            flash('Failed to update site settings: ' + str(exc), 'error')
        finally:
            cur.close()
        return redirect(url_for('admin.site_settings'))
    return render_template('manage_settings.html', settings=settings)

