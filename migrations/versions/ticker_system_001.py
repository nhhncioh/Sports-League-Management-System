"""Ticker system tables (settings and items)

Revision ID: ticker_system_001
Revises: webhook_system_001
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ticker_system_001'
down_revision = 'a62667f0bcf4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Choose JSON type per dialect (use JSONB for Postgres)
    json_type = postgresql.JSONB(astext_type=sa.Text()) if dialect == 'postgresql' else sa.JSON()

    op.create_table(
        'ticker_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('league_id', sa.String(length=36), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('theme', json_type, nullable=False),
        sa.Column('source', json_type, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['league.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('league_id', name='uq_ticker_settings_league')
    )

    op.create_table(
        'ticker_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('league_id', sa.String(length=36), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=True, server_default='FINAL'),
        sa.Column('home_name', sa.String(length=80), nullable=True),
        sa.Column('away_name', sa.String(length=80), nullable=True),
        sa.Column('home_logo', sa.Text(), nullable=True),
        sa.Column('away_logo', sa.Text(), nullable=True),
        sa.Column('home_score', sa.Integer(), nullable=True),
        sa.Column('away_score', sa.Integer(), nullable=True),
        sa.Column('venue', sa.String(length=120), nullable=True),
        sa.Column('link_url', sa.Text(), nullable=True),
        sa.Column('sort_key', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['league_id'], ['league.id'], ondelete='CASCADE')
    )
    # A simple index on league_id + sort_key provides acceptable performance across dialects
    op.create_index('ix_ticker_items_league_sort', 'ticker_items', ['league_id', 'sort_key'], unique=False)

    # Set default JSON values using direct SQL to handle JSONB/TEXT appropriately
    # Only apply defaults if columns are NULL on insert in future, but here we ensure table exists.


def downgrade():
    op.drop_index('ix_ticker_items_league_sort', table_name='ticker_items')
    op.drop_table('ticker_items')
    op.drop_table('ticker_settings')
