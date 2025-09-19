"""CLI commands for SLMS."""

from .org import org_commands
from .seed import seed_commands
from .export import export_commands
from .templates import template_commands
from .user import user_commands


def register_commands(app):
    """Register all CLI command groups with the Flask app."""
    app.cli.add_command(org_commands)
    app.cli.add_command(seed_commands)
    app.cli.add_command(export_commands)
    app.cli.add_command(template_commands)
    app.cli.add_command(user_commands)
