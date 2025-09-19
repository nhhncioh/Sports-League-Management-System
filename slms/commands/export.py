"""CSV export CLI commands."""

import click
import csv
import os
from pathlib import Path
from flask.cli import with_appcontext
from datetime import datetime

from slms.extensions import db
from slms.models import (
    Organization, Season, Team, Game, Player, Registration, Venue
)


@click.group('export')
def export_commands():
    """CSV export commands."""
    pass


def ensure_export_dir():
    """Ensure the export directory exists."""
    export_dir = Path('/tmp/exports')
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def generate_filename(org_slug, season_name, data_type, extension='csv'):
    """Generate a filename for the export."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_season = season_name.replace(' ', '_').replace('/', '_')
    return f"{org_slug}_{safe_season}_{data_type}_{timestamp}.{extension}"


@export_commands.command('season')
@click.option('--season', 'season_id', required=True, help='Season ID to export data for')
@click.option('--what', type=click.Choice(['standings', 'schedule', 'registrations', 'all']),
              required=True, help='What data to export')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def export_season(season_id, what, output_dir):
    """Export season data to CSV files.

    Available export types:
    - standings: Team standings with wins/losses/points
    - schedule: Complete game schedule with results
    - registrations: Player registrations for the season
    - all: Export all data types

    Example:
        flask export:season --season <id> --what standings
        flask export:season --season <id> --what all
    """
    try:
        # Find season
        season = db.session.query(Season).filter_by(id=season_id).first()
        if not season:
            click.echo(click.style(f'Error: Season with ID "{season_id}" not found', fg='red'))
            return

        # Get organization
        org = db.session.query(Organization).filter_by(id=season.org_id).first()

        # Set up export directory
        if output_dir:
            export_dir = Path(output_dir)
            export_dir.mkdir(parents=True, exist_ok=True)
        else:
            export_dir = ensure_export_dir()

        click.echo(f'Exporting data for season: {season.name}')
        click.echo(f'Organization: {org.name}')
        click.echo(f'Export directory: {export_dir}')
        click.echo()

        exported_files = []

        if what in ['standings', 'all']:
            exported_files.append(export_standings(season, org, export_dir))

        if what in ['schedule', 'all']:
            exported_files.append(export_schedule(season, org, export_dir))

        if what in ['registrations', 'all']:
            exported_files.append(export_registrations(season, org, export_dir))

        click.echo(click.style('✓ Export completed successfully!', fg='green'))
        click.echo('\nGenerated files:')
        for file_path in exported_files:
            if file_path:
                click.echo(f'  • {file_path}')

    except Exception as e:
        click.echo(click.style(f'Error during export: {str(e)}', fg='red'))
        import traceback
        traceback.print_exc()


def export_standings(season, org, export_dir):
    """Export team standings to CSV."""
    click.echo('Exporting standings...')

    # Calculate standings
    teams = db.session.query(Team).filter_by(season_id=season.id).all()
    standings_data = []

    for team in teams:
        # Get games for this team
        home_games = db.session.query(Game).filter_by(
            season_id=season.id,
            home_team_id=team.id
        ).all()

        away_games = db.session.query(Game).filter_by(
            season_id=season.id,
            away_team_id=team.id
        ).all()

        wins = 0
        losses = 0
        ties = 0
        points_for = 0
        points_against = 0
        games_played = 0

        # Count home games
        for game in home_games:
            if game.status.value == 'final':
                games_played += 1
                points_for += game.home_score
                points_against += game.away_score

                if game.home_score > game.away_score:
                    wins += 1
                elif game.home_score < game.away_score:
                    losses += 1
                else:
                    ties += 1

        # Count away games
        for game in away_games:
            if game.status.value == 'final':
                games_played += 1
                points_for += game.away_score
                points_against += game.home_score

                if game.away_score > game.home_score:
                    wins += 1
                elif game.away_score < game.home_score:
                    losses += 1
                else:
                    ties += 1

        # Calculate additional stats
        win_percentage = (wins / games_played) if games_played > 0 else 0
        points_per_game = (points_for / games_played) if games_played > 0 else 0
        points_allowed_per_game = (points_against / games_played) if games_played > 0 else 0

        standings_data.append({
            'team_name': team.name,
            'games_played': games_played,
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'win_percentage': round(win_percentage, 3),
            'points_for': points_for,
            'points_against': points_against,
            'points_differential': points_for - points_against,
            'points_per_game': round(points_per_game, 1),
            'points_allowed_per_game': round(points_allowed_per_game, 1),
            'coach_name': team.coach_name or '',
            'coach_email': team.coach_email or ''
        })

    # Sort by wins descending, then by points differential
    standings_data.sort(key=lambda x: (-x['wins'], -x['points_differential']))

    # Add rank
    for i, team_data in enumerate(standings_data):
        team_data['rank'] = i + 1

    # Write to CSV
    filename = generate_filename(org.slug, season.name, 'standings')
    file_path = export_dir / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'rank', 'team_name', 'games_played', 'wins', 'losses', 'ties',
            'win_percentage', 'points_for', 'points_against', 'points_differential',
            'points_per_game', 'points_allowed_per_game', 'coach_name', 'coach_email'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(standings_data)

    click.echo(f'  ✓ Standings exported to {filename}')
    return file_path


def export_schedule(season, org, export_dir):
    """Export game schedule to CSV."""
    click.echo('Exporting schedule...')

    # Get all games for the season
    games = db.session.query(Game).filter_by(season_id=season.id).order_by(Game.start_time).all()

    schedule_data = []
    for game in games:
        # Get team and venue names
        home_team_name = game.home_team.name if game.home_team else 'TBD'
        away_team_name = game.away_team.name if game.away_team else 'TBD'
        venue_name = game.venue.name if game.venue else 'TBD'
        venue_address = game.venue.address if game.venue else ''

        schedule_data.append({
            'game_id': game.id,
            'date': game.start_time.strftime('%Y-%m-%d') if game.start_time else '',
            'time': game.start_time.strftime('%H:%M') if game.start_time else '',
            'home_team': home_team_name,
            'away_team': away_team_name,
            'venue': venue_name,
            'venue_address': venue_address,
            'status': game.status.value,
            'home_score': game.home_score if game.status.value == 'final' else '',
            'away_score': game.away_score if game.status.value == 'final' else '',
            'winner': _determine_winner(game),
            'notes': game.notes or ''
        })

    # Write to CSV
    filename = generate_filename(org.slug, season.name, 'schedule')
    file_path = export_dir / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'game_id', 'date', 'time', 'home_team', 'away_team', 'venue',
            'venue_address', 'status', 'home_score', 'away_score', 'winner', 'notes'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(schedule_data)

    click.echo(f'  ✓ Schedule exported to {filename}')
    return file_path


def export_registrations(season, org, export_dir):
    """Export registrations to CSV."""
    click.echo('Exporting registrations...')

    # Get all registrations for the season
    registrations = db.session.query(Registration).filter_by(season_id=season.id).all()

    registration_data = []
    for reg in registrations:
        # Split name if it contains first and last name
        name_parts = reg.name.split(' ', 1) if reg.name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        registration_data.append({
            'registration_id': reg.id,
            'name': reg.name,
            'first_name': first_name,
            'last_name': last_name,
            'email': reg.email,
            'team_name': reg.team_name or '',
            'preferred_division': reg.preferred_division or '',
            'registration_date': reg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'waiver_signed': 'Yes' if reg.waiver_signed else 'No',
            'waiver_signed_date': reg.waiver_signed_at.strftime('%Y-%m-%d %H:%M:%S') if reg.waiver_signed_at else '',
            'payment_status': reg.payment_status.value,
            'payment_notes': reg.payment_notes or '',
            'notes': reg.notes or ''
        })

    # Write to CSV
    filename = generate_filename(org.slug, season.name, 'registrations')
    file_path = export_dir / filename

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'registration_id', 'name', 'first_name', 'last_name', 'email', 'team_name',
            'preferred_division', 'registration_date', 'waiver_signed', 'waiver_signed_date',
            'payment_status', 'payment_notes', 'notes'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(registration_data)

    click.echo(f'  ✓ Registrations exported to {filename}')
    return file_path


def _determine_winner(game):
    """Determine the winner of a game."""
    if game.status.value != 'final':
        return ''

    if game.home_score > game.away_score:
        return game.home_team.name if game.home_team else 'Home Team'
    elif game.away_score > game.home_score:
        return game.away_team.name if game.away_team else 'Away Team'
    else:
        return 'Tie'


def _calculate_age(birthdate):
    """Calculate age from birthdate."""
    if not birthdate:
        return ''

    today = datetime.now().date()
    age = today.year - birthdate.year

    # Adjust if birthday hasn't occurred this year
    if today.month < birthdate.month or (today.month == birthdate.month and today.day < birthdate.day):
        age -= 1

    return age


@export_commands.command('list-seasons')
@click.option('--org', help='Filter by organization slug')
@with_appcontext
def list_seasons(org):
    """List all seasons for export reference."""
    query = db.session.query(Season)

    if org:
        organization = db.session.query(Organization).filter_by(slug=org).first()
        if not organization:
            click.echo(click.style(f'Error: Organization with slug "{org}" not found', fg='red'))
            return
        query = query.filter_by(org_id=organization.id)

    seasons = query.order_by(Season.created_at.desc()).all()

    if not seasons:
        click.echo('No seasons found.')
        return

    click.echo(f'Found {len(seasons)} season(s):\n')

    for season in seasons:
        org_info = db.session.query(Organization).filter_by(id=season.org_id).first()
        league_info = db.session.query(Organization).filter_by(id=season.league_id).first()

        click.echo(f'• {season.name}')
        click.echo(f'  ID: {season.id}')
        click.echo(f'  Organization: {org_info.name} ({org_info.slug})')
        if season.start_date and season.end_date:
            click.echo(f'  Dates: {season.start_date} to {season.end_date}')
        click.echo(f'  Active: {"Yes" if season.is_active else "No"}')
        click.echo(f'  Created: {season.created_at.strftime("%Y-%m-%d")}')
        click.echo()


@export_commands.command('teams')
@click.option('--season', 'season_id', required=True, help='Season ID to export teams for')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def export_teams(season_id, output_dir):
    """Export teams and players to CSV."""
    try:
        season = db.session.query(Season).filter_by(id=season_id).first()
        if not season:
            click.echo(click.style(f'Error: Season with ID "{season_id}" not found', fg='red'))
            return

        org = db.session.query(Organization).filter_by(id=season.org_id).first()

        # Set up export directory
        if output_dir:
            export_dir = Path(output_dir)
            export_dir.mkdir(parents=True, exist_ok=True)
        else:
            export_dir = ensure_export_dir()

        click.echo(f'Exporting teams for season: {season.name}')

        # Get teams and players
        teams = db.session.query(Team).filter_by(season_id=season.id).all()

        teams_data = []
        players_data = []

        for team in teams:
            # Team data
            player_count = db.session.query(Player).filter_by(team_id=team.id).count()

            teams_data.append({
                'team_id': team.id,
                'team_name': team.name,
                'coach_name': team.coach_name or '',
                'coach_email': team.coach_email or '',
                'player_count': player_count,
                'created_date': team.created_at.strftime('%Y-%m-%d')
            })

            # Players data
            players = db.session.query(Player).filter_by(team_id=team.id).all()
            for player in players:
                players_data.append({
                    'player_id': player.id,
                    'team_name': team.name,
                    'first_name': player.first_name,
                    'last_name': player.last_name,
                    'email': player.email or '',
                    'jersey_number': player.jersey_number or '',
                    'birthdate': player.birthdate.strftime('%Y-%m-%d') if player.birthdate else '',
                    'age': _calculate_age(player.birthdate) if player.birthdate else ''
                })

        # Export teams
        teams_filename = generate_filename(org.slug, season.name, 'teams')
        teams_file_path = export_dir / teams_filename

        with open(teams_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['team_id', 'team_name', 'coach_name', 'coach_email', 'player_count', 'created_date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(teams_data)

        # Export players
        players_filename = generate_filename(org.slug, season.name, 'players')
        players_file_path = export_dir / players_filename

        with open(players_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['player_id', 'team_name', 'first_name', 'last_name', 'email', 'jersey_number', 'birthdate', 'age']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(players_data)

        click.echo(click.style('✓ Teams and players exported successfully!', fg='green'))
        click.echo(f'  • Teams: {teams_filename}')
        click.echo(f'  • Players: {players_filename}')

    except Exception as e:
        click.echo(click.style(f'Error during export: {str(e)}', fg='red'))