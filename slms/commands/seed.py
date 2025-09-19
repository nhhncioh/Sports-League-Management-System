"""Data seeding CLI commands."""

import click
from flask.cli import with_appcontext
from datetime import datetime, date, timedelta
import random

from slms.extensions import db
from slms.models import (
    Organization, User, UserRole, League, SportType, Season,
    Team, Player, Venue, Game, GameStatus, Registration
)


@click.group('seed')
def seed_commands():
    """Data seeding commands."""
    pass


@seed_commands.command('demo')
@click.option('--org', required=True, help='Organization slug to seed data for')
@click.option('--teams', default=6, help='Number of teams to create (default: 6)')
@click.option('--players-per-team', default=12, help='Players per team (default: 12)')
@click.option('--venues', default=1, help='Number of venues to create (default: 1)')
@click.option('--games', default=15, help='Number of games to create (default: 15)')
@with_appcontext
def seed_demo(org, teams, players_per_team, venues, games):
    """Seed demo data for an organization.

    Creates:
    - Demo league and season
    - Specified number of teams with players
    - Venues
    - Sample games with some completed scores
    - Sample registrations

    Example:
        flask seed:demo --org demo
        flask seed:demo --org demo --teams 8 --venues 2 --games 20
    """
    try:
        # Find organization
        organization = db.session.query(Organization).filter_by(slug=org).first()
        if not organization:
            click.echo(click.style(f'Error: Organization with slug "{org}" not found', fg='red'))
            return

        click.echo(f'Seeding demo data for organization: {organization.name}')
        click.echo(f'Teams: {teams}, Players per team: {players_per_team}, Venues: {venues}, Games: {games}')
        click.echo()

        # Create demo league
        click.echo('Creating demo league...')
        league = League(
            org_id=organization.id,
            name='Demo Basketball League',
            sport=SportType.BASKETBALL
        )
        db.session.add(league)
        db.session.flush()

        # Create demo season
        click.echo('Creating demo season...')
        start_date = date.today() - timedelta(days=30)
        end_date = date.today() + timedelta(days=60)

        season = Season(
            org_id=organization.id,
            league_id=league.id,
            name='Spring 2024 Demo Season',
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            default_game_length_minutes=48
        )
        db.session.add(season)
        db.session.flush()

        # Create venues
        click.echo(f'Creating {venues} venue(s)...')
        venue_names = [
            'Central Sports Complex',
            'Eastside Community Center',
            'Westfield Athletic Club',
            'Downtown Recreation Center',
            'Northside Gymnasium'
        ]

        created_venues = []
        for i in range(venues):
            venue = Venue(
                org_id=organization.id,
                name=venue_names[i % len(venue_names)],
                address=f'{100 + i*50} Demo Street',
                city='Demo City',
                timezone='America/New_York',
                court_label=f'Court {i+1}' if venues > 1 else 'Main Court'
            )
            db.session.add(venue)
            created_venues.append(venue)

        db.session.flush()

        # Create teams
        click.echo(f'Creating {teams} teams...')
        team_names = [
            'Thunder Bolts', 'Fire Hawks', 'Ice Wolves', 'Storm Eagles',
            'Lightning Sharks', 'Blazing Tigers', 'Frost Bears', 'Wind Runners',
            'Solar Falcons', 'Ocean Warriors', 'Mountain Lions', 'Desert Vipers'
        ]

        created_teams = []
        for i in range(teams):
            team = Team(
                org_id=organization.id,
                season_id=season.id,
                name=team_names[i % len(team_names)],
                coach_name=f'Coach {chr(65 + i)}. Smith',
                coach_email=f'coach{i+1}@demo.com'
            )
            db.session.add(team)
            created_teams.append(team)

        db.session.flush()

        # Create players
        click.echo(f'Creating players ({players_per_team} per team)...')
        first_names = [
            'Alex', 'Jordan', 'Taylor', 'Casey', 'Morgan', 'Riley', 'Avery', 'Quinn',
            'Sam', 'Reese', 'Dakota', 'Cameron', 'Blake', 'Drew', 'Sage', 'Parker'
        ]
        last_names = [
            'Johnson', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore',
            'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin'
        ]

        total_players = 0
        for team in created_teams:
            for j in range(players_per_team):
                # Generate random birthdate (18-35 years old)
                birth_year = datetime.now().year - random.randint(18, 35)
                birthdate = date(birth_year, random.randint(1, 12), random.randint(1, 28))

                player = Player(
                    org_id=organization.id,
                    team_id=team.id,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    email=f'player{total_players + j + 1}@demo.com',
                    jersey_number=j + 1,
                    birthdate=birthdate
                )
                db.session.add(player)
            total_players += players_per_team

        # Create games
        click.echo(f'Creating {games} games...')
        game_times = [
            '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'
        ]

        for i in range(games):
            # Select random teams
            home_team = random.choice(created_teams)
            away_team = random.choice([t for t in created_teams if t.id != home_team.id])

            # Random game date within season
            days_offset = random.randint(0, 90)
            game_date = start_date + timedelta(days=days_offset)
            game_time = random.choice(game_times)
            game_datetime = datetime.combine(game_date, datetime.strptime(game_time, '%H:%M').time())

            # Random venue
            venue = random.choice(created_venues)

            # Determine game status and scores
            if game_datetime < datetime.now() - timedelta(days=1):
                # Past games are completed with scores
                status = GameStatus.FINAL
                home_score = random.randint(45, 95)
                away_score = random.randint(45, 95)
                # Ensure not a tie
                if home_score == away_score:
                    home_score += random.randint(1, 5)
            elif game_datetime < datetime.now() + timedelta(hours=1):
                # Current/recent games might be in progress
                status = random.choice([GameStatus.IN_PROGRESS, GameStatus.FINAL])
                if status == GameStatus.FINAL:
                    home_score = random.randint(45, 95)
                    away_score = random.randint(45, 95)
                    if home_score == away_score:
                        home_score += random.randint(1, 5)
                else:
                    home_score = random.randint(20, 60)
                    away_score = random.randint(20, 60)
            else:
                # Future games are scheduled
                status = GameStatus.SCHEDULED
                home_score = 0
                away_score = 0

            game = Game(
                org_id=organization.id,
                season_id=season.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                venue_id=venue.id,
                start_time=game_datetime,
                status=status,
                home_score=home_score,
                away_score=away_score,
                notes=f'Game {i+1}' if random.random() > 0.7 else None
            )
            db.session.add(game)

        # Commit the core data first (leagues, seasons, teams, venues, games, players)
        db.session.commit()
        click.echo('✓ Core data committed successfully!')

        # Skip registration creation for now due to schema issues
        click.echo('Skipping registrations due to database schema mismatch...')
        registration_count = 0

        click.echo(click.style('✓ Demo data seeded successfully!', fg='green'))
        click.echo()
        click.echo('Created:')
        click.echo(f'  • 1 League: {league.name}')
        click.echo(f'  • 1 Season: {season.name}')
        click.echo(f'  • {len(created_teams)} Teams with {total_players} players total')
        click.echo(f'  • {len(created_venues)} Venue(s)')
        click.echo(f'  • {games} Games')
        click.echo(f'  • {registration_count} Registrations')
        click.echo()
        click.echo(f'Visit: http://localhost:5000/{org} to see the public site')
        click.echo(f'Admin: http://localhost:5000/{org}/admin')

    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'Error seeding demo data: {str(e)}', fg='red'))
        import traceback
        traceback.print_exc()


@seed_commands.command('clear')
@click.option('--org', required=True, help='Organization slug to clear data for')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@with_appcontext
def clear_data(org, force):
    """Clear all seeded data for an organization.

    WARNING: This will delete all leagues, seasons, teams, players, games, and registrations.
    """
    organization = db.session.query(Organization).filter_by(slug=org).first()
    if not organization:
        click.echo(click.style(f'Error: Organization with slug "{org}" not found', fg='red'))
        return

    if not force:
        click.echo(f'This will permanently delete ALL data for organization "{organization.name}":')
        click.echo('- Leagues and seasons')
        click.echo('- Teams and players')
        click.echo('- Games and scores')
        click.echo('- Registrations')
        click.echo('- Venues')
        click.echo()

        if not click.confirm('Are you sure you want to continue?'):
            click.echo('Operation cancelled.')
            return

    try:
        from slms.models import League, Season, Team, Player, Game, Venue, Registration

        # Delete in proper order to respect foreign key constraints
        db.session.query(Registration).filter_by(org_id=organization.id).delete()
        db.session.query(Game).filter_by(org_id=organization.id).delete()
        db.session.query(Player).filter_by(org_id=organization.id).delete()
        db.session.query(Team).filter_by(org_id=organization.id).delete()
        db.session.query(Season).filter_by(org_id=organization.id).delete()
        db.session.query(League).filter_by(org_id=organization.id).delete()
        db.session.query(Venue).filter_by(org_id=organization.id).delete()

        db.session.commit()

        click.echo(click.style(f'✓ All data cleared for organization "{organization.name}"', fg='green'))

    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'Error clearing data: {str(e)}', fg='red'))