"""User management CLI commands."""

import click
from flask.cli import with_appcontext

from slms.extensions import db
from slms.models import Organization, User, UserRole


def _get_org_by_slug(slug: str) -> Organization | None:
    return db.session.query(Organization).filter_by(slug=slug).first()


@click.group('user')
def user_commands():
    """User management commands."""
    pass


@user_commands.command('create')
@click.option('--org', 'org_slug', required=True, help='Organization slug')
@click.option('--email', required=True, help='User email')
@click.option('--password', required=True, help='User password')
@click.option('--role', type=click.Choice([r.value for r in UserRole]), default=UserRole.ADMIN.value, show_default=True)
@with_appcontext
def create_user(org_slug, email, password, role):
    """Create a user in an organization."""
    org = _get_org_by_slug(org_slug)
    if not org:
        click.echo(click.style(f'Error: Organization with slug "{org_slug}" not found', fg='red'))
        return

    existing = db.session.query(User).filter_by(org_id=org.id, email=email).first()
    if existing:
        click.echo(click.style(f'Error: User with email "{email}" already exists in org "{org_slug}"', fg='red'))
        return

    user = User(org_id=org.id, email=email, role=UserRole(role))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    click.echo(click.style('User created successfully!', fg='green'))
    click.echo(f'  Org: {org.slug} ({org.name})')
    click.echo(f'  Email: {email}')
    click.echo(f'  Role: {role}')


@user_commands.command('set-password')
@click.option('--org', 'org_slug', required=True, help='Organization slug')
@click.option('--email', required=True, help='User email')
@click.option('--password', required=True, help='New password')
@with_appcontext
def set_password(org_slug, email, password):
    """Set or reset a user's password."""
    org = _get_org_by_slug(org_slug)
    if not org:
        click.echo(click.style(f'Error: Organization with slug "{org_slug}" not found', fg='red'))
        return

    user = db.session.query(User).filter_by(org_id=org.id, email=email).first()
    if not user:
        click.echo(click.style(f'Error: No user {email} found in org {org_slug}', fg='red'))
        return

    user.set_password(password)
    db.session.commit()
    click.echo(click.style('Password updated.', fg='green'))

