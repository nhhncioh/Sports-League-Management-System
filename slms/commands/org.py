"""Organization management CLI commands."""

import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from slms.extensions import db
from slms.models import Organization, User, UserRole


@click.group('org')
def org_commands():
    """Organization management commands."""
    pass


@org_commands.command('create')
@click.option('--name', required=True, help='Organization name')
@click.option('--slug', required=True, help='Organization slug (URL-friendly identifier)')
@click.option('--admin-email', help='Admin user email (optional)')
@click.option('--admin-password', help='Admin user password (optional)')
@click.option('--primary-color', help='Primary brand color (hex code)')
@with_appcontext
def create_org(name, slug, admin_email, admin_password, primary_color):
    """Create a new organization.

    Example:
        flask org:create --name "Demo League" --slug demo
        flask org:create --name "Demo League" --slug demo --admin-email admin@demo.com --admin-password password123
    """
    try:
        # Validate slug format
        if not slug.replace('-', '').replace('_', '').isalnum():
            click.echo(click.style('Error: Slug must contain only letters, numbers, hyphens, and underscores', fg='red'))
            return

        # Check if slug already exists
        existing_org = db.session.query(Organization).filter_by(slug=slug).first()
        if existing_org:
            click.echo(click.style(f'Error: Organization with slug "{slug}" already exists', fg='red'))
            return

        # Create organization
        org = Organization(
            name=name,
            slug=slug,
            primary_color=primary_color
        )

        db.session.add(org)
        db.session.flush()  # Get the org ID

        # Create admin user if credentials provided
        if admin_email and admin_password:
            # Check if user already exists
            existing_user = db.session.query(User).filter_by(
                org_id=org.id,
                email=admin_email
            ).first()

            if existing_user:
                click.echo(click.style(f'Warning: User with email "{admin_email}" already exists in this organization', fg='yellow'))
            else:
                admin_user = User(
                    org_id=org.id,
                    email=admin_email,
                    role=UserRole.OWNER
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)

        db.session.commit()

        click.echo(click.style('✓ Organization created successfully!', fg='green'))
        click.echo(f'  Name: {name}')
        click.echo(f'  Slug: {slug}')
        click.echo(f'  ID: {org.id}')

        if admin_email:
            click.echo(f'  Admin Email: {admin_email}')

        click.echo(f'\nPublic URL: http://localhost:5000/{slug}')
        click.echo(f'Admin URL: http://localhost:5000/{slug}/admin')

    except IntegrityError as e:
        db.session.rollback()
        click.echo(click.style(f'Error: Database constraint violation - {str(e)}', fg='red'))
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'Error creating organization: {str(e)}', fg='red'))


@org_commands.command('list')
@with_appcontext
def list_orgs():
    """List all organizations."""
    orgs = db.session.query(Organization).all()

    if not orgs:
        click.echo('No organizations found.')
        return

    click.echo(f'Found {len(orgs)} organization(s):\n')

    for org in orgs:
        user_count = db.session.query(User).filter_by(org_id=org.id).count()

        click.echo(f'• {org.name}')
        click.echo(f'  Slug: {org.slug}')
        click.echo(f'  ID: {org.id}')
        click.echo(f'  Users: {user_count}')
        click.echo(f'  Created: {org.created_at.strftime("%Y-%m-%d %H:%M")}')
        click.echo(f'  URL: http://localhost:5000/{org.slug}')
        click.echo()


@org_commands.command('delete')
@click.argument('slug')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@with_appcontext
def delete_org(slug, force):
    """Delete an organization and all its data.

    WARNING: This will permanently delete all data associated with the organization.
    """
    org = db.session.query(Organization).filter_by(slug=slug).first()

    if not org:
        click.echo(click.style(f'Error: Organization with slug "{slug}" not found', fg='red'))
        return

    if not force:
        click.echo(f'This will permanently delete organization "{org.name}" and ALL associated data:')
        click.echo('- Users and authentication data')
        click.echo('- Leagues and seasons')
        click.echo('- Teams and players')
        click.echo('- Games and scores')
        click.echo('- Registrations and payments')
        click.echo('- Venues and schedules')
        click.echo()

        if not click.confirm('Are you sure you want to continue?'):
            click.echo('Operation cancelled.')
            return

    try:
        db.session.delete(org)
        db.session.commit()

        click.echo(click.style(f'✓ Organization "{org.name}" deleted successfully', fg='green'))

    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'Error deleting organization: {str(e)}', fg='red'))


@org_commands.command('info')
@click.argument('slug')
@with_appcontext
def org_info(slug):
    """Show detailed information about an organization."""
    org = db.session.query(Organization).filter_by(slug=slug).first()

    if not org:
        click.echo(click.style(f'Error: Organization with slug "{slug}" not found', fg='red'))
        return

    # Get counts
    user_count = db.session.query(User).filter_by(org_id=org.id).count()

    # Import here to avoid circular imports
    from slms.models import League, Season, Team, Player, Game, Venue, Registration

    league_count = db.session.query(League).filter_by(org_id=org.id).count()
    season_count = db.session.query(Season).filter_by(org_id=org.id).count()
    team_count = db.session.query(Team).filter_by(org_id=org.id).count()
    player_count = db.session.query(Player).filter_by(org_id=org.id).count()
    game_count = db.session.query(Game).filter_by(org_id=org.id).count()
    venue_count = db.session.query(Venue).filter_by(org_id=org.id).count()
    registration_count = db.session.query(Registration).filter_by(org_id=org.id).count()

    click.echo(f'Organization: {org.name}')
    click.echo(f'Slug: {org.slug}')
    click.echo(f'ID: {org.id}')
    if org.primary_color:
        click.echo(f'Primary Color: {org.primary_color}')
    click.echo(f'Created: {org.created_at.strftime("%Y-%m-%d %H:%M:%S")}')
    click.echo(f'Last Updated: {org.updated_at.strftime("%Y-%m-%d %H:%M:%S")}')
    click.echo()

    click.echo('Statistics:')
    click.echo(f'  Users: {user_count}')
    click.echo(f'  Leagues: {league_count}')
    click.echo(f'  Seasons: {season_count}')
    click.echo(f'  Teams: {team_count}')
    click.echo(f'  Players: {player_count}')
    click.echo(f'  Games: {game_count}')
    click.echo(f'  Venues: {venue_count}')
    click.echo(f'  Registrations: {registration_count}')
    click.echo()

    click.echo('URLs:')
    click.echo(f'  Public: http://localhost:5000/{org.slug}')
    click.echo(f'  Admin: http://localhost:5000/{org.slug}/admin')