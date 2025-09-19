"""Add color scheme fields to team model

Revision ID: add_team_color_scheme_fields
Revises: 55d8933bd3cb
Create Date: 2025-09-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_team_color_scheme_fields'
down_revision = '55d8933bd3cb'
branch_labels = None
depends_on = None


def upgrade():
    # Add color scheme fields to team table
    with op.batch_alter_table('team', schema=None) as batch_op:
        batch_op.add_column(sa.Column('primary_color', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('secondary_color', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('accent_color', sa.String(length=7), nullable=True))

    # Add color scheme fields to registration table (for team preferences)
    with op.batch_alter_table('registration', schema=None) as batch_op:
        batch_op.add_column(sa.Column('primary_color', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('secondary_color', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('accent_color', sa.String(length=7), nullable=True))


def downgrade():
    # Remove color scheme fields from registration table
    with op.batch_alter_table('registration', schema=None) as batch_op:
        batch_op.drop_column('accent_color')
        batch_op.drop_column('secondary_color')
        batch_op.drop_column('primary_color')

    # Remove color scheme fields from team table
    with op.batch_alter_table('team', schema=None) as batch_op:
        batch_op.drop_column('accent_color')
        batch_op.drop_column('secondary_color')
        batch_op.drop_column('primary_color')