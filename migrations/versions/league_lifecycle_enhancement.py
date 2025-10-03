"""League lifecycle enhancement

Revision ID: league_lifecycle_001
Revises:
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'league_lifecycle_001'
down_revision = None  # Update this to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to league table
    op.add_column('league', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('league', sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
    op.add_column('league', sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'))
    op.add_column('league', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('league', sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add new columns to season table
    op.add_column('season', sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
    op.add_column('season', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('season', sa.Column('registration_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('season', sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('season', sa.Column('timezone', sa.String(length=64), nullable=True))
    op.add_column('season', sa.Column('off_season_start', sa.Date(), nullable=True))
    op.add_column('season', sa.Column('off_season_end', sa.Date(), nullable=True))
    op.add_column('season', sa.Column('off_season_message', sa.Text(), nullable=True))

    # Create indexes for better query performance
    op.create_index('ix_league_status', 'league', ['status'])
    op.create_index('ix_league_org_status', 'league', ['org_id', 'status'])
    op.create_index('ix_season_status', 'season', ['status'])
    op.create_index('ix_season_org_status', 'season', ['org_id', 'status'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_season_org_status', table_name='season')
    op.drop_index('ix_season_status', table_name='season')
    op.drop_index('ix_league_org_status', table_name='league')
    op.drop_index('ix_league_status', table_name='league')

    # Remove columns from season table
    op.drop_column('season', 'off_season_message')
    op.drop_column('season', 'off_season_end')
    op.drop_column('season', 'off_season_start')
    op.drop_column('season', 'timezone')
    op.drop_column('season', 'rules')
    op.drop_column('season', 'registration_deadline')
    op.drop_column('season', 'archived_at')
    op.drop_column('season', 'status')

    # Remove columns from league table
    op.drop_column('league', 'settings')
    op.drop_column('league', 'archived_at')
    op.drop_column('league', 'timezone')
    op.drop_column('league', 'status')
    op.drop_column('league', 'description')
