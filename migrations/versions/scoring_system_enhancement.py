"""Scoring system enhancement

Revision ID: scoring_system_001
Revises: league_lifecycle_001
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'scoring_system_001'
down_revision = 'league_lifecycle_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to game table
    op.add_column('game', sa.Column('went_to_overtime', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('game', sa.Column('overtime_periods', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('game', sa.Column('home_score_regulation', sa.Integer(), nullable=True))
    op.add_column('game', sa.Column('away_score_regulation', sa.Integer(), nullable=True))
    op.add_column('game', sa.Column('period_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('game', sa.Column('is_reconciled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('game', sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('game', sa.Column('reconciled_by_user_id', sa.String(length=36), nullable=True))
    op.add_column('game', sa.Column('current_period', sa.Integer(), nullable=True))
    op.add_column('game', sa.Column('game_clock', sa.String(length=10), nullable=True))
    op.add_column('game', sa.Column('last_score_update', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_game_reconciled_by_user', 'game', 'user', ['reconciled_by_user_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_game_reconciled', 'game', ['is_reconciled'])

    # Create game_event table
    op.create_table(
        'game_event',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('game_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=True),
        sa.Column('player_id', sa.String(length=36), nullable=True),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('period_type', sa.String(length=20), nullable=True),
        sa.Column('game_clock', sa.String(length=10), nullable=True),
        sa.Column('event_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['game.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_id'], ['player.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_game_event_game', 'game_event', ['game_id'])
    op.create_index('ix_game_event_game_time', 'game_event', ['game_id', 'event_time'])
    op.create_index('ix_game_event_org_id', 'game_event', ['org_id'])

    # Create player_game_stat table
    op.create_table(
        'player_game_stat',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('game_id', sa.String(length=36), nullable=False),
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('stat_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'player_id', 'stat_type', name='uq_player_game_stat'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['game.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['player.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_player_game_stat_game', 'player_game_stat', ['game_id'])
    op.create_index('ix_player_game_stat_player', 'player_game_stat', ['player_id'])
    op.create_index('ix_player_game_stat_org_id', 'player_game_stat', ['org_id'])

    # Create penalty table
    op.create_table(
        'penalty',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('game_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('player_id', sa.String(length=36), nullable=True),
        sa.Column('penalty_type', sa.String(length=100), nullable=False),
        sa.Column('period', sa.Integer(), nullable=True),
        sa.Column('game_clock', sa.String(length=10), nullable=True),
        sa.Column('minutes', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resulted_in_ejection', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['game.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['player.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_penalty_game', 'penalty', ['game_id'])
    op.create_index('ix_penalty_player', 'penalty', ['player_id'])
    op.create_index('ix_penalty_org_id', 'penalty', ['org_id'])

    # Create score_update table (audit trail)
    op.create_table(
        'score_update',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('game_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('previous_home_score', sa.Integer(), nullable=False),
        sa.Column('previous_away_score', sa.Integer(), nullable=False),
        sa.Column('new_home_score', sa.Integer(), nullable=False),
        sa.Column('new_away_score', sa.Integer(), nullable=False),
        sa.Column('update_type', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['game.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_score_update_game', 'score_update', ['game_id'])
    op.create_index('ix_score_update_org_id', 'score_update', ['org_id'])


def downgrade():
    # Drop tables
    op.drop_index('ix_score_update_org_id', table_name='score_update')
    op.drop_index('ix_score_update_game', table_name='score_update')
    op.drop_table('score_update')

    op.drop_index('ix_penalty_org_id', table_name='penalty')
    op.drop_index('ix_penalty_player', table_name='penalty')
    op.drop_index('ix_penalty_game', table_name='penalty')
    op.drop_table('penalty')

    op.drop_index('ix_player_game_stat_org_id', table_name='player_game_stat')
    op.drop_index('ix_player_game_stat_player', table_name='player_game_stat')
    op.drop_index('ix_player_game_stat_game', table_name='player_game_stat')
    op.drop_table('player_game_stat')

    op.drop_index('ix_game_event_org_id', table_name='game_event')
    op.drop_index('ix_game_event_game_time', table_name='game_event')
    op.drop_index('ix_game_event_game', table_name='game_event')
    op.drop_table('game_event')

    # Drop game columns
    op.drop_constraint('fk_game_reconciled_by_user', 'game', type_='foreignkey')
    op.drop_index('ix_game_reconciled', table_name='game')
    op.drop_column('game', 'last_score_update')
    op.drop_column('game', 'game_clock')
    op.drop_column('game', 'current_period')
    op.drop_column('game', 'reconciled_by_user_id')
    op.drop_column('game', 'reconciled_at')
    op.drop_column('game', 'is_reconciled')
    op.drop_column('game', 'period_scores')
    op.drop_column('game', 'away_score_regulation')
    op.drop_column('game', 'home_score_regulation')
    op.drop_column('game', 'overtime_periods')
    op.drop_column('game', 'went_to_overtime')
