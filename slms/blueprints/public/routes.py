from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, g
from flask_login import current_user

from slms.security import roles_required
from slms.services.db import get_db
from slms.models import MediaAsset, UserRole
import json
from slms.extensions import bcrypt

public_bp = Blueprint('public', __name__)


def public_required(f):
    return roles_required(
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.COACH,
        UserRole.SCOREKEEPER,
        UserRole.PLAYER,
        UserRole.VIEWER,
    )(f)


def _default_league_homepage(name, country):
    return {
        'title': name,
        'subtitle': f'{country} - Official League Home',
        'background_url': '',
        'cta_text': 'See Schedule',
        'cta_url': url_for('portal.index'),
        'highlights': [],
    }


@public_bp.route('/user')
@public_required
def user_dashboard():
    return render_template('user_dashboard.html')

@public_bp.route('/user/teams')
@public_required
def user_teams():
    db = get_db()
    cur = db.cursor()

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')

    # Fetch available leagues and countries for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    # Build the base query
    query = """
        SELECT team_id, name, crestURL 
        FROM teams
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND nationality = (SELECT name FROM countries WHERE country_id = %s)"
        filters.append(country_id)

    query += " LIMIT %s OFFSET %s"
    filters.append(20)
    filters.append((request.args.get('page', 1, type=int) - 1) * 20)

    cur.execute(query, filters)
    teams = cur.fetchall()

    cur.execute('SELECT COUNT(*) FROM teams WHERE 1=1 ' + (' AND league_id = %s' if league_id else '') + (' AND nationality = (SELECT name FROM countries WHERE country_id = %s)' if country_id else ''), filters[:-2])
    total_teams = cur.fetchone()[0]
    cur.close()

    total_pages = (total_teams + 19) // 20

    return render_template('user_teams.html', teams=teams, page=request.args.get('page', 1, type=int), total_pages=total_pages, leagues=leagues, countries=countries, max=max, min=min, str=str)

@public_bp.route('/user/players')
@public_required
def user_players():
    db = get_db()
    cur = db.cursor()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')
    team_id = request.args.get('team_id')
    position = request.args.get('position')

    # Fetch available leagues, countries, teams, and positions for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()

    positions = ['Goalkeeper', 'Defence', 'Midfield', 'Offence']

    # Build the base query
    query = """
        SELECT p.player_id, p.name, p.position, t.crestURL, t.name, c.flag_url
        FROM players p
        JOIN teams t ON p.team_id = t.team_id
        JOIN countries c ON p.nationality = c.name
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND t.league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND c.country_id = %s"
        filters.append(country_id)
    if team_id:
        query += " AND p.team_id = %s"
        filters.append(team_id)
    if position:
        query += " AND p.position = %s"
        filters.append(position)

    query += " LIMIT %s OFFSET %s"
    filters.append(per_page)
    filters.append(offset)

    cur.execute(query, filters)
    players = cur.fetchall()

    cur.execute('SELECT COUNT(*) FROM players p JOIN teams t ON p.team_id = t.team_id JOIN countries c ON p.nationality = c.name WHERE 1=1' + (' AND t.league_id = %s' if league_id else '') + (' AND c.country_id = %s' if country_id else '') + (' AND p.team_id = %s' if team_id else '') + (' AND p.position = %s' if position else ''), filters[:-2])
    total_players = cur.fetchone()[0]
    cur.close()

    total_pages = (total_players + per_page - 1) // per_page

    return render_template('user_players.html', players=players, page=page, total_pages=total_pages, leagues=leagues, countries=countries, teams=teams, positions=positions, max=max, min=min, str=str)




@public_bp.route('/user/leagues')
@public_required
def user_leagues():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT l.league_id, l.name, c.flag_url, l.icon_url
        FROM leagues l
        JOIN countries c ON l.country_id = c.country_id
    ''')
    leagues = cur.fetchall()
    cur.close()

    return render_template('user_leagues.html', leagues=leagues)
    
@public_bp.route('/user/matches')
@public_required
def user_matches():
    db = get_db()
    cur = db.cursor()

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')
    team_id = request.args.get('team_id')
    matchday = request.args.get('matchday')

    # Fetch available leagues, countries, and teams for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries')
    countries = cur.fetchall()

    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()

    matchdays = [i for i in range(1, 39)]  # Assuming matchdays from 1 to 38

    # Build the base query
    query = """
        SELECT m.match_id, 
               t1.name AS home_team_name, 
               t2.name AS away_team_name, 
               s.full_time_home AS home_score, 
               s.full_time_away AS away_score,
               TO_CHAR(m.utc_date, 'Month DD, YYYY') AS formatted_date,
               t1.crestURL AS home_team_logo,
               t2.crestURL AS away_team_logo,
               m.matchday
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        LEFT JOIN scores s ON m.match_id = s.match_id
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND m.league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND (t1.country_id = %s OR t2.country_id = %s)"
        filters.append(country_id)
        filters.append(country_id)
    if team_id:
        query += " AND (m.home_team_id = %s OR m.away_team_id = %s)"
        filters.append(team_id)
        filters.append(team_id)
    if matchday:
        query += " AND m.matchday = %s"
        filters.append(matchday)

    query += " ORDER BY m.utc_date DESC"

    cur.execute(query, filters)
    matches = cur.fetchall()
    cur.close()

    return render_template('user_matches.html', matches=matches, leagues=leagues, countries=countries, teams=teams, matchdays=matchdays, str=str)



@public_bp.route('/team/<int:team_id>')
@public_required
def profile_team(team_id):
    db = get_db()
    cur = db.cursor()

    # Get team details along with stadium, coach, league, and crestURL
    cur.execute("""
        SELECT t.name, t.founded_year, s.name AS stadium_name, c.name AS coach_name, l.name AS league_name, t.crestURL, co.flag_url
        FROM teams t 
        JOIN stadiums s ON t.stadium_id = s.stadium_id 
        JOIN coaches c ON t.coach_id = c.coach_id 
        JOIN countries co ON c.nationality = co.name
        JOIN leagues l ON t.league_id = l.league_id
        WHERE t.team_id = %s
    """, (team_id,))
    team = cur.fetchone()

    # Get players
    cur.execute("""
        SELECT p.player_id, p.name, p.date_of_birth, p.position, p.nationality, c.flag_url
        FROM players p 
        JOIN countries c ON p.nationality = c.name
        WHERE p.team_id = %s
    """, (team_id,))
    players = cur.fetchall()

    # Get match scores
    cur.execute("""
        SELECT 
            m.match_id,
            TO_CHAR(m.utc_date, 'Mon, DD YYYY') AS utc_date, 
            t1.name AS home_team_name, 
            t2.name AS away_team_name, 
            s.full_time_home, 
            s.full_time_away,
            t1.crestURL AS home_team_logo,
            t2.crestURL AS away_team_logo,
            m.matchday
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        LEFT JOIN scores s ON m.match_id = s.match_id
        WHERE m.home_team_id = %s OR m.away_team_id = %s
        ORDER BY m.utc_date DESC
    """, (team_id, team_id))
    scores = cur.fetchall()

    cur.close()

    if team:
        return render_template('profile_team.html',
                               team=team,
                               players=players,
                               scores=scores,
                               logo_url=team[5])
    else:
        flash('Team not found', 'error')
        return redirect(url_for('public.user_dashboard'))




@public_bp.route('/player/<int:player_id>')
@public_required
def profile_player(player_id):
    db = get_db()
    cur = db.cursor()

    # Fetch player details
    cur.execute("""
        SELECT p.name, p.date_of_birth, p.position, t.team_id, t.name AS team_name, c.flag_url, c.name AS nationality
        FROM players p 
        JOIN teams t ON p.team_id = t.team_id 
        JOIN countries c ON p.nationality = c.name
        WHERE p.player_id = %s
    """, (player_id,))
    player = cur.fetchone()

    # Fetch player statistics if they are in the top scorers list
    cur.execute("""
        SELECT sc.goals, sc.assists, sc.penalties
        FROM scorers sc
        WHERE sc.player_id = %s
    """, (player_id,))
    statistics = cur.fetchone()

    cur.close()

    if player:
        return render_template('profile_player.html', player=player, statistics=statistics)
    else:
        flash('Player not found', 'error')
        return redirect(url_for('public.user_dashboard'))





@public_bp.route('/match/<int:match_id>')
@public_required
def profile_match(match_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT m.match_id, 
               t1.name AS home_team_name, 
               t2.name AS away_team_name, 
               s.full_time_home AS home_score, 
               s.full_time_away AS away_score,
               TO_CHAR(m.utc_date, 'Month DD, YYYY') AS formatted_date,
               m.matchday,
               t1.crestURL AS home_team_logo,
               t2.crestURL AS away_team_logo,
               st.name AS stadium_name,
               st.location AS stadium_location,
               r.name AS referee_name,
               c.flag_url AS referee_flag_url,
               t1.team_id AS home_team_id,
               t2.team_id AS away_team_id
        FROM matches m
        JOIN teams t1 ON m.home_team_id = t1.team_id
        JOIN teams t2 ON m.away_team_id = t2.team_id
        LEFT JOIN scores s ON m.match_id = s.match_id
        JOIN stadiums st ON t1.stadium_id = st.stadium_id
        JOIN match_referees mr ON m.match_id = mr.match_id
        JOIN referees r ON mr.referee_id = r.referee_id
        JOIN countries c ON r.nationality = c.name
        WHERE m.match_id = %s
    """, (match_id,))
    match = cur.fetchone()

    cur.execute("""
        SELECT s.full_time_home, s.full_time_away, s.half_time_home, s.half_time_away
        FROM scores s
        WHERE s.match_id = %s
    """, (match_id,))
    scores = cur.fetchall()

    cur.close()

    if match:
        return render_template('profile_match.html', match=match, scores=scores)
    else:
        flash('Match not found', 'error')
        return redirect(url_for('public.user_dashboard'))





@public_bp.route('/league/<int:league_id>')
@public_required
def profile_league(league_id):
    db = get_db()
    cur = db.cursor()

    league_info = None
    homepage_config = None

    try:
        cur.execute(
            """
            SELECT
                l.league_id,
                l.name,
                c.name AS country,
                l.icon_url,
                c.flag_url,
                l.cl_spot,
                l.uel_spot,
                l.relegation_spot,
                l.homepage_title,
                l.homepage_subtitle,
                l.homepage_background_url,
                l.homepage_cta_text,
                l.homepage_cta_url,
                l.homepage_highlights_json
            FROM leagues l
            JOIN countries c ON l.country_id = c.country_id
            WHERE l.league_id = %s
            """,
            (league_id,)
        )
        row = cur.fetchone()
    except Exception:
        db.rollback()
        cur = db.cursor()
        cur.execute(
            """
            SELECT l.league_id, l.name, c.name AS country, l.icon_url, c.flag_url, l.cl_spot, l.uel_spot, l.relegation_spot
            FROM leagues l
            JOIN countries c ON l.country_id = c.country_id
            WHERE l.league_id = %s
            """,
            (league_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            abort(404)
        (
            league_id,
            name,
            country,
            icon_url,
            flag_url,
            cl_spot,
            uel_spot,
            relegation_spot,
        ) = row
        homepage_config = _default_league_homepage(name, country)
    else:
        if not row:
            cur.close()
            abort(404)
        (
            league_id,
            name,
            country,
            icon_url,
            flag_url,
            cl_spot,
            uel_spot,
            relegation_spot,
            homepage_title,
            homepage_subtitle,
            homepage_background_url,
            homepage_cta_text,
            homepage_cta_url,
            homepage_highlights_json,
        ) = row
        try:
            highlights = json.loads(homepage_highlights_json or '[]')
        except (TypeError, json.JSONDecodeError):
            highlights = []
        homepage_config = {
            'title': homepage_title or name,
            'subtitle': homepage_subtitle or f'{country} - Official League Home',
            'background_url': homepage_background_url or '',
            'cta_text': homepage_cta_text or 'See Schedule',
            'cta_url': homepage_cta_url or url_for('portal.index'),
            'highlights': highlights,
        }

    league_info = {
        'id': league_id,
        'name': name,
        'country': country,
        'icon_url': icon_url,
        'flag_url': flag_url,
        'cl_spot': cl_spot,
        'uel_spot': uel_spot,
        'relegation_spot': relegation_spot,
    }

    cur.execute('SELECT team_id, name, cresturl FROM teams WHERE league_id = %s ORDER BY name', (league_id,))
    teams = [
        {'team_id': t[0], 'name': t[1], 'crest': t[2]}
        for t in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT s.position, s.team_id, t.name AS team_name, s.played_games, s.won, s.draw, s.lost,
               s.points, s.goals_for, s.goals_against, s.goal_difference, s.form, t.crestURL,
               CASE WHEN s.position <= l.cl_spot THEN TRUE ELSE FALSE END AS champions_spot,
               CASE WHEN s.position > l.cl_spot AND s.position <= l.cl_spot + l.uel_spot THEN TRUE ELSE FALSE END AS europa_spot,
               CASE WHEN s.position > (SELECT COUNT(*) FROM standings WHERE league_id = %s) - l.relegation_spot THEN TRUE ELSE FALSE END AS relegation_spot
        FROM standings s
        JOIN teams t ON s.team_id = t.team_id
        JOIN leagues l ON s.league_id = l.league_id
        WHERE s.league_id = %s
        ORDER BY s.position
        """,
        (league_id, league_id)
    )
    standings_rows = cur.fetchall()
    cur.close()

    standings = []
    for row in standings_rows:
        (
            position,
            team_id,
            team_name,
            played_games,
            won,
            draw,
            lost,
            points,
            gf,
            ga,
            gd,
            form,
            crest,
            champions_spot,
            europa_spot,
            relegation_spot,
        ) = row
        form_list = list(form or '')
        standings.append({
            'position': position,
            'team_id': team_id,
            'team_name': team_name,
            'played_games': played_games,
            'won': won,
            'draw': draw,
            'lost': lost,
            'points': points,
            'goals_for': gf,
            'goals_against': ga,
            'goal_difference': gd,
            'form': form_list,
            'crest': crest,
            'champions_spot': bool(champions_spot),
            'europa_spot': bool(europa_spot),
            'relegation_spot': bool(relegation_spot),
        })

    return render_template(
        'profile_league.html',
        league=league_info,
        homepage=homepage_config,
        teams=teams,
        standings=standings,
    )


@public_bp.route('/user/scorers')
@public_required
def user_scorers():
    db = get_db()
    cur = db.cursor()

    # Get filter parameters from the request
    league_id = request.args.get('league_id')
    country_id = request.args.get('country_id')
    team_id = request.args.get('team_id')

    # Fetch available leagues, countries, and teams for filtering
    cur.execute('SELECT league_id, name FROM leagues')
    leagues = cur.fetchall()

    cur.execute('SELECT country_id, name FROM countries ORDER BY country_id ASC')
    countries = cur.fetchall()

    cur.execute('SELECT team_id, name FROM teams')
    teams = cur.fetchall()

    # Build the base query
    query = """
        SELECT sc.player_id, p.name, sc.goals, sc.assists, sc.penalties, t.crestURL, p.nationality
        FROM scorers sc
        JOIN players p ON sc.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE 1=1
    """
    filters = []

    # Add filters based on the selected values
    if league_id:
        query += " AND sc.league_id = %s"
        filters.append(league_id)
    if country_id:
        query += " AND p.nationality = (SELECT name FROM countries WHERE country_id = %s)"
        filters.append(country_id)
    if team_id:
        query += " AND p.team_id = %s"
        filters.append(team_id)

    query += " ORDER BY sc.goals DESC"

    cur.execute(query, filters)
    scorers = cur.fetchall()
    cur.close()

    return render_template('user_scorers.html', scorers=scorers, leagues=leagues, countries=countries, teams=teams, str=str)


# Main application routes

@public_bp.route('/')
def landing():
    if current_user.is_authenticated:
        org_slug = None
        try:
            org = getattr(current_user, 'organization', None)
            if org and getattr(org, 'slug', None):
                org_slug = org.slug
        except Exception:
            pass
        if not org_slug:
            org_slug = session.get('org_slug')
        return redirect(url_for('public.home', org=org_slug) if org_slug else url_for('public.home'))
    return render_template('landing.html')


@public_bp.route('/home')
def home():
    org_slug = None
    try:
        if current_user.is_authenticated:
            org = getattr(current_user, 'organization', None)
            if org and getattr(org, 'slug', None):
                org_slug = org.slug
    except Exception:
        pass
    if not org_slug:
        org_slug = session.get('org_slug')

    if current_user.is_authenticated:
        if current_user.has_role(UserRole.OWNER, UserRole.ADMIN):
            return redirect(url_for('admin.manage_league_homepage'))
        return redirect(url_for('public.user_dashboard'))
    if session.get('user_id'):
        if session.get('is_admin'):
            return redirect(url_for('admin.manage_league_homepage'))
        return redirect(url_for('public.user_dashboard'))
    return redirect(url_for('auth.login'))


@public_bp.route('/login', methods=['GET', 'POST'])
def login_redirect():
    next_url = request.args.get('next')
    return redirect(url_for('auth.login', next=next_url))


@public_bp.route('/logout')
def logout_redirect():
    return redirect(url_for('auth.logout'))


@public_bp.route('/about')
def about():
    return render_template('about.html')


@public_bp.route('/search', methods=['GET', 'POST'])
@public_required
def search():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form['query']
        db = get_db()
        cur = db.cursor()

        # Search in teams
        cur.execute(
            "SELECT team_id, name, 'team' AS source FROM teams WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in coaches
        cur.execute(
            "SELECT coach_id, name, 'coach' AS source FROM coaches WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in players
        cur.execute(
            "SELECT player_id, name, 'player' AS source FROM players WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in stadiums
        cur.execute(
            "SELECT stadium_id, name, 'stadium' AS source FROM stadiums WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        # Search in leagues
        cur.execute(
            "SELECT league_id, name, 'league' AS source FROM leagues WHERE name ILIKE %s",
            ('%' + query + '%', ))
        results.extend(cur.fetchall())

        cur.close()

    return render_template('search.html', results=results, query=query)


@public_bp.route('/add_user', methods=['GET', 'POST'])
@public_required
def add_user():
    if request.method == 'POST':
        try:
            db = get_db()
            cur = db.cursor()
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            cur.execute(
                'INSERT INTO users (username, password, email) VALUES (%s, %s, %s)',
                (username, hashed_password, email))
            db.commit()
            cur.close()
            flash('User added successfully', 'success')
            return redirect(url_for('public.user_dashboard'))
        except Exception as e:
            db.rollback()
            print("Error: ", str(e))
            flash('Failed to add user', 'error')
            return redirect(url_for('public.add_user'))
    return render_template('add_user.html')


@public_bp.route('/profile', methods=['GET', 'POST'])
@public_required
def profile():
    db = get_db()
    cur = db.cursor()
    user_id = session['user_id']

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if the username already exists
        cur.execute(
            'SELECT * FROM users WHERE username = %s AND user_id != %s',
            (username, user_id))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Username already taken', 'error')
            return redirect(url_for('public.profile'))

        # Check if the email already exists
        cur.execute('SELECT * FROM users WHERE email = %s AND user_id != %s',
                    (email, user_id))
        existing_email = cur.fetchone()
        if existing_email:
            flash('Email already registered', 'error')
            return redirect(url_for('public.profile'))

        # Hash the password if it is updated
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cur.execute(
            'UPDATE users SET username = %s, email = %s, password = %s WHERE user_id = %s',
            (username, email, hashed_password, user_id))
        db.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('public.profile'))

    cur.execute('SELECT username, email FROM users WHERE user_id = %s',
                (user_id, ))
    user = cur.fetchone()
    cur.close()

    return render_template('profile.html', user=user)


@public_bp.route('/gallery')
def media_gallery():
    """Public media gallery - photos and videos"""
    category = (request.args.get('category') or '').strip()
    media_type = (request.args.get('type') or '').strip()

    query = MediaAsset.query.order_by(MediaAsset.created_at.desc())
    org = getattr(g, 'org', None)
    if org is not None:
        query = query.filter(MediaAsset.org_id == org.id)

    if category:
        query = query.filter(MediaAsset.category == category)

    if media_type:
        query = query.filter(MediaAsset.media_type == media_type)

    assets = query.all()
    media_items = [
        {
            'id': asset.id,
            'media_id': asset.id,
            'title': asset.title,
            'description': asset.description,
            'url': asset.url,
            'media_type': asset.media_type,
            'category': asset.category,
            'created_at': asset.created_at.isoformat() if asset.created_at else None,
        }
        for asset in assets
    ]

    category_query = MediaAsset.query
    if org is not None:
        category_query = category_query.filter(MediaAsset.org_id == org.id)
    raw_categories = category_query.with_entities(MediaAsset.category).distinct().all()
    category_values = sorted({value for (value,) in raw_categories if value})

    return render_template('public_gallery.html',
                         media_items=media_items,
                         categories=category_values,
                         selected_category=category,
                         selected_type=media_type)


@public_bp.route('/search')
def search():
    """Universal search page."""
    return render_template('universal_search.html')


@public_bp.route('/teams/<team_id>')
def team_profile(team_id):
    """Team profile page."""
    from slms.models.models import Team
    from slms.services.search import search_players_by_team, search_games_by_team
    from slms.extensions import db

    team = db.session.get(Team, team_id)
    if not team:
        abort(404)

    # Get related data
    players = search_players_by_team(team_id, team.org_id)
    games = search_games_by_team(team_id, team.org_id, limit=10)

    return render_template('team_profile.html', team=team, players=players, games=games)


@public_bp.route('/players/<player_id>')
def player_profile(player_id):
    """Player profile page."""
    from slms.models.models import Player, Team
    from slms.extensions import db

    player = db.session.get(Player, player_id)
    if not player:
        abort(404)

    # Get team if assigned
    team = db.session.get(Team, player.team_id) if player.team_id else None

    return render_template('player_profile.html', player=player, team=team)


@public_bp.route('/venues/<venue_id>')
def venue_profile(venue_id):
    """Venue profile page."""
    from slms.models.models import Venue
    from slms.services.search import search_games_by_venue
    from slms.extensions import db

    venue = db.session.get(Venue, venue_id)
    if not venue:
        abort(404)

    # Get upcoming games
    games = search_games_by_venue(venue_id, venue.org_id, limit=10)

    return render_template('venue_profile.html', venue=venue, games=games)



