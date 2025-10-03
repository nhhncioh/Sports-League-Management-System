"""add_coach_referee_sponsor_transaction_models

Revision ID: a62667f0bcf4
Revises: 99a12646cb8d
Create Date: 2025-10-03 14:59:13.999856

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a62667f0bcf4'
down_revision = '99a12646cb8d'
branch_labels = None
depends_on = None


def upgrade():
    # Coach table
    op.create_table(
        'coach',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('certification_level', sa.String(length=100), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_coach_org', 'coach', ['org_id'], unique=False)

    # Referee table
    op.create_table(
        'referee',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('certification_level', sa.String(length=100), nullable=True),
        sa.Column('license_number', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_referee_org', 'referee', ['org_id'], unique=False)

    # Sponsor table
    op.create_table(
        'sponsor',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_name', sa.String(length=255), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=32), nullable=True),
        sa.Column('website_url', sa.String(length=512), nullable=True),
        sa.Column('logo_url', sa.String(length=512), nullable=True),
        sa.Column('tier', sa.String(length=50), nullable=False, server_default='bronze'),
        sa.Column('contract_start', sa.Date(), nullable=True),
        sa.Column('contract_end', sa.Date(), nullable=True),
        sa.Column('sponsorship_amount', sa.Integer(), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('team_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sponsor_org', 'sponsor', ['org_id'], unique=False)
    op.create_index('ix_sponsor_org_tier', 'sponsor', ['org_id', 'tier'], unique=False)

    # Coach assignment
    op.create_table(
        'coach_assignment',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('coach_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('season_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='head_coach'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['coach_id'], ['coach.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['season_id'], ['season.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('coach_id', 'team_id', 'season_id', name='uq_coach_team_season')
    )
    op.create_index('ix_coach_assignment_team', 'coach_assignment', ['team_id'], unique=False)

    # Game officials (referee assignments)
    op.create_table(
        'game_officials',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('game_id', sa.String(length=36), nullable=False),
        sa.Column('referee_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='referee'),
        sa.Column('payment_amount', sa.Integer(), nullable=True),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['game_id'], ['game.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['referee_id'], ['referee.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', 'referee_id', name='uq_game_referee')
    )
    op.create_index('ix_game_officials_game', 'game_officials', ['game_id'], unique=False)

    # Transaction table
    op.create_table(
        'transaction',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('team_id', sa.String(length=36), nullable=True),
        sa.Column('registration_id', sa.String(length=36), nullable=True),
        sa.Column('sponsor_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['team.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['registration_id'], ['registration.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sponsor_id'], ['sponsor.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transaction_org_date', 'transaction', ['org_id', 'transaction_date'], unique=False)
    op.create_index('ix_transaction_org_category', 'transaction', ['org_id', 'category'], unique=False)


def downgrade():
    op.drop_index('ix_transaction_org_category', table_name='transaction')
    op.drop_index('ix_transaction_org_date', table_name='transaction')
    op.drop_table('transaction')

    op.drop_index('ix_game_officials_game', table_name='game_officials')
    op.drop_table('game_officials')

    op.drop_index('ix_coach_assignment_team', table_name='coach_assignment')
    op.drop_table('coach_assignment')

    op.drop_index('ix_sponsor_org_tier', table_name='sponsor')
    op.drop_index('ix_sponsor_org', table_name='sponsor')
    op.drop_table('sponsor')

    op.drop_index('ix_referee_org', table_name='referee')
    op.drop_table('referee')

    op.drop_index('ix_coach_org', table_name='coach')
    op.drop_table('coach')
