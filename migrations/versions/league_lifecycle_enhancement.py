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
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = postgresql.JSONB(astext_type=sa.Text()) if dialect == 'postgresql' else sa.JSON()

    # Helper to list existing columns
    def _columns(table: str) -> set[str]:
        if dialect == 'sqlite':
            rows = bind.exec_driver_sql(f"PRAGMA table_info('{table}')").fetchall()
            return {row[1] for row in rows}
        else:
            # Safe here as 'table' is a fixed internal identifier
            res = bind.exec_driver_sql(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
            )
            return {row[0] for row in res}

    league_cols = _columns('league')
    if 'description' not in league_cols:
        op.add_column('league', sa.Column('description', sa.Text(), nullable=True))
    if 'status' not in league_cols:
        op.add_column('league', sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
    if 'timezone' not in league_cols:
        op.add_column('league', sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'))
    if 'archived_at' not in league_cols:
        op.add_column('league', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    if 'settings' not in league_cols:
        op.add_column('league', sa.Column('settings', json_type, nullable=True))

    season_cols = _columns('season')
    if 'status' not in season_cols:
        op.add_column('season', sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
    if 'archived_at' not in season_cols:
        op.add_column('season', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    if 'registration_deadline' not in season_cols:
        op.add_column('season', sa.Column('registration_deadline', sa.DateTime(timezone=True), nullable=True))
    if 'rules' not in season_cols:
        op.add_column('season', sa.Column('rules', json_type, nullable=True))
    if 'timezone' not in season_cols:
        op.add_column('season', sa.Column('timezone', sa.String(length=64), nullable=True))
    if 'off_season_start' not in season_cols:
        op.add_column('season', sa.Column('off_season_start', sa.Date(), nullable=True))
    if 'off_season_end' not in season_cols:
        op.add_column('season', sa.Column('off_season_end', sa.Date(), nullable=True))
    if 'off_season_message' not in season_cols:
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
