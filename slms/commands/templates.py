"""CSV template generation commands."""

import click
import csv
from pathlib import Path
from flask.cli import with_appcontext


@click.group('templates')
def template_commands():
    """CSV template generation commands."""
    pass


def ensure_export_dir():
    """Ensure the export directory exists."""
    export_dir = Path('/tmp/exports')
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


@template_commands.command('teams')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def generate_teams_template(output_dir):
    """Generate a CSV template for team imports.

    Example:
        flask templates:teams
        flask templates:teams --output-dir ./downloads
    """
    if output_dir:
        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
    else:
        export_dir = ensure_export_dir()

    filename = 'teams_import_template.csv'
    file_path = export_dir / filename

    # Sample team data
    sample_data = [
        {
            'name': 'Thunder Bolts',
            'city': 'Downtown',
            'code': 'TB',
            'coach_name': 'John Smith',
            'coach_email': 'john.smith@email.com'
        },
        {
            'name': 'Fire Hawks',
            'city': 'Westside',
            'code': 'FH',
            'coach_name': 'Sarah Johnson',
            'coach_email': 'sarah.johnson@email.com'
        },
        {
            'name': 'Ice Wolves',
            'city': 'Northside',
            'code': 'IW',
            'coach_name': 'Mike Davis',
            'coach_email': 'mike.davis@email.com'
        }
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'city', 'code', 'coach_name', 'coach_email']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)

    click.echo(click.style('✓ Teams import template generated!', fg='green'))
    click.echo(f'File: {file_path}')
    click.echo()
    click.echo('Template columns:')
    click.echo('  • name: Team name (required)')
    click.echo('  • city: Team city (optional)')
    click.echo('  • code: Team abbreviation, max 5 chars (optional)')
    click.echo('  • coach_name: Coach full name (optional)')
    click.echo('  • coach_email: Coach email address (optional)')


@template_commands.command('players')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def generate_players_template(output_dir):
    """Generate a CSV template for player imports.

    Example:
        flask templates:players
    """
    if output_dir:
        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
    else:
        export_dir = ensure_export_dir()

    filename = 'players_import_template.csv'
    file_path = export_dir / filename

    # Sample player data
    sample_data = [
        {
            'first_name': 'Alex',
            'last_name': 'Johnson',
            'email': 'alex.johnson@email.com',
            'jersey_number': '23',
            'birthdate': '1995-06-15',
            'team_name': 'Thunder Bolts'
        },
        {
            'first_name': 'Jordan',
            'last_name': 'Smith',
            'email': 'jordan.smith@email.com',
            'jersey_number': '10',
            'birthdate': '1998-03-22',
            'team_name': 'Fire Hawks'
        },
        {
            'first_name': 'Taylor',
            'last_name': 'Williams',
            'email': 'taylor.williams@email.com',
            'jersey_number': '7',
            'birthdate': '1996-11-08',
            'team_name': 'Ice Wolves'
        }
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['first_name', 'last_name', 'email', 'jersey_number', 'birthdate', 'team_name']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)

    click.echo(click.style('✓ Players import template generated!', fg='green'))
    click.echo(f'File: {file_path}')
    click.echo()
    click.echo('Template columns:')
    click.echo('  • first_name: Player first name (required)')
    click.echo('  • last_name: Player last name (required)')
    click.echo('  • email: Player email address (optional)')
    click.echo('  • jersey_number: Jersey number (optional, must be unique per team)')
    click.echo('  • birthdate: Birth date in YYYY-MM-DD format (optional)')
    click.echo('  • team_name: Team name to assign player to (optional)')


@template_commands.command('venues')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def generate_venues_template(output_dir):
    """Generate a CSV template for venue imports.

    Example:
        flask templates:venues
    """
    if output_dir:
        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
    else:
        export_dir = ensure_export_dir()

    filename = 'venues_import_template.csv'
    file_path = export_dir / filename

    # Sample venue data
    sample_data = [
        {
            'name': 'Central Sports Complex',
            'address': '123 Main Street',
            'city': 'Downtown',
            'timezone': 'America/New_York',
            'court_label': 'Court 1',
            'open_time': '08:00',
            'close_time': '22:00'
        },
        {
            'name': 'Eastside Community Center',
            'address': '456 Oak Avenue',
            'city': 'Eastside',
            'timezone': 'America/New_York',
            'court_label': 'Gymnasium',
            'open_time': '09:00',
            'close_time': '21:00'
        }
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'address', 'city', 'timezone', 'court_label', 'open_time', 'close_time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)

    click.echo(click.style('✓ Venues import template generated!', fg='green'))
    click.echo(f'File: {file_path}')
    click.echo()
    click.echo('Template columns:')
    click.echo('  • name: Venue name (required)')
    click.echo('  • address: Street address (optional)')
    click.echo('  • city: City name (optional)')
    click.echo('  • timezone: Timezone (optional, e.g., America/New_York)')
    click.echo('  • court_label: Court/field identifier (optional)')
    click.echo('  • open_time: Opening time in HH:MM format (optional)')
    click.echo('  • close_time: Closing time in HH:MM format (optional)')


@template_commands.command('all')
@click.option('--output-dir', help='Custom output directory (default: /tmp/exports)')
@with_appcontext
def generate_all_templates(output_dir):
    """Generate all CSV import templates.

    Example:
        flask templates:all
    """
    click.echo('Generating all CSV import templates...')
    click.echo()

    # Generate each template
    ctx = click.get_current_context()
    ctx.invoke(generate_teams_template, output_dir=output_dir)
    click.echo()
    ctx.invoke(generate_players_template, output_dir=output_dir)
    click.echo()
    ctx.invoke(generate_venues_template, output_dir=output_dir)

    click.echo()
    click.echo(click.style('✓ All templates generated successfully!', fg='green'))