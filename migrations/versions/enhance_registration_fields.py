"""enhance registration fields

Revision ID: enhance_registration
Revises:
Create Date: 2025-10-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'enhance_registration'
down_revision = ('add_season_registration_fields', 'add_team_color_scheme_fields')  # Merge both branches
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns exist before adding (some may exist from previous migrations)
    conn = op.get_bind()
    dialect = conn.dialect.name
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('registration')]

    # Add new fields to registration table (skip if already exist)
    if 'phone' not in existing_columns:
        op.add_column('registration', sa.Column('phone', sa.String(20), nullable=True))
    if 'date_of_birth' not in existing_columns:
        op.add_column('registration', sa.Column('date_of_birth', sa.Date(), nullable=True))
    if 'gender' not in existing_columns:
        op.add_column('registration', sa.Column('gender', sa.String(20), nullable=True))
    if 'skill_level' not in existing_columns:
        op.add_column('registration', sa.Column('skill_level', sa.String(50), nullable=True))
    if 'jersey_size' not in existing_columns:
        op.add_column('registration', sa.Column('jersey_size', sa.String(10), nullable=True))
    if 'jersey_number_preference' not in existing_columns:
        op.add_column('registration', sa.Column('jersey_number_preference', sa.String(10), nullable=True))

    # Emergency contact info
    if 'emergency_contact_name' not in existing_columns:
        op.add_column('registration', sa.Column('emergency_contact_name', sa.String(255), nullable=True))
    if 'emergency_contact_phone' not in existing_columns:
        op.add_column('registration', sa.Column('emergency_contact_phone', sa.String(20), nullable=True))
    if 'emergency_contact_relationship' not in existing_columns:
        op.add_column('registration', sa.Column('emergency_contact_relationship', sa.String(100), nullable=True))

    # Team info for team registrations
    if 'team_size' not in existing_columns:
        op.add_column('registration', sa.Column('team_size', sa.Integer(), nullable=True))
    if 'team_logo_url' not in existing_columns:
        op.add_column('registration', sa.Column('team_logo_url', sa.String(512), nullable=True))
    if 'player_photo_url' not in existing_columns:
        op.add_column('registration', sa.Column('player_photo_url', sa.String(512), nullable=True))

    # Color scheme fields (skip if already exist from previous migration)
    if 'primary_color' not in existing_columns:
        op.add_column('registration', sa.Column('primary_color', sa.String(7), nullable=True))
    if 'secondary_color' not in existing_columns:
        op.add_column('registration', sa.Column('secondary_color', sa.String(7), nullable=True))
    if 'accent_color' not in existing_columns:
        op.add_column('registration', sa.Column('accent_color', sa.String(7), nullable=True))

    # Status and approval workflow
    if 'status' not in existing_columns:
        op.add_column('registration', sa.Column('status', sa.String(20), nullable=False, server_default='pending'))
    if 'reviewed_by_user_id' not in existing_columns:
        op.add_column('registration', sa.Column('reviewed_by_user_id', sa.String(36), nullable=True))
    if 'reviewed_at' not in existing_columns:
        op.add_column('registration', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    if 'rejection_reason' not in existing_columns:
        op.add_column('registration', sa.Column('rejection_reason', sa.Text(), nullable=True))
    if 'admin_notes' not in existing_columns:
        op.add_column('registration', sa.Column('admin_notes', sa.Text(), nullable=True))

    # Payment details
    if 'payment_method' not in existing_columns:
        op.add_column('registration', sa.Column('payment_method', sa.String(50), nullable=True))
    if 'payment_transaction_id' not in existing_columns:
        op.add_column('registration', sa.Column('payment_transaction_id', sa.String(255), nullable=True))
    if 'paid_at' not in existing_columns:
        op.add_column('registration', sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True))

    # Medical and special requirements
    if 'medical_conditions' not in existing_columns:
        op.add_column('registration', sa.Column('medical_conditions', sa.Text(), nullable=True))
    if 'allergies' not in existing_columns:
        op.add_column('registration', sa.Column('allergies', sa.Text(), nullable=True))
    if 'special_requirements' not in existing_columns:
        op.add_column('registration', sa.Column('special_requirements', sa.Text(), nullable=True))

    # Add foreign key for reviewed_by (check if it exists first)
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('registration')]
    if dialect != 'sqlite' and 'fk_registration_reviewed_by_user' not in existing_fks:
        op.create_foreign_key(
            'fk_registration_reviewed_by_user',
            'registration',
            'user',
            ['reviewed_by_user_id'],
            ['id'],
            ondelete='SET NULL'
        )

    # Create indexes on status for faster queries (check if they exist first)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('registration')]
    if 'ix_registration_status' not in existing_indexes:
        op.create_index('ix_registration_status', 'registration', ['status'])
    if 'ix_registration_org_status' not in existing_indexes:
        op.create_index('ix_registration_org_status', 'registration', ['org_id', 'status'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_registration_org_status', table_name='registration')
    op.drop_index('ix_registration_status', table_name='registration')

    # Drop foreign key
    op.drop_constraint('fk_registration_reviewed_by_user', 'registration', type_='foreignkey')

    # Drop all added columns
    op.drop_column('registration', 'special_requirements')
    op.drop_column('registration', 'allergies')
    op.drop_column('registration', 'medical_conditions')
    op.drop_column('registration', 'paid_at')
    op.drop_column('registration', 'payment_transaction_id')
    op.drop_column('registration', 'payment_method')
    op.drop_column('registration', 'admin_notes')
    op.drop_column('registration', 'rejection_reason')
    op.drop_column('registration', 'reviewed_at')
    op.drop_column('registration', 'reviewed_by_user_id')
    op.drop_column('registration', 'status')
    op.drop_column('registration', 'accent_color')
    op.drop_column('registration', 'secondary_color')
    op.drop_column('registration', 'primary_color')
    op.drop_column('registration', 'player_photo_url')
    op.drop_column('registration', 'team_logo_url')
    op.drop_column('registration', 'team_size')
    op.drop_column('registration', 'emergency_contact_relationship')
    op.drop_column('registration', 'emergency_contact_phone')
    op.drop_column('registration', 'emergency_contact_name')
    op.drop_column('registration', 'jersey_number_preference')
    op.drop_column('registration', 'jersey_size')
    op.drop_column('registration', 'skill_level')
    op.drop_column('registration', 'gender')
    op.drop_column('registration', 'date_of_birth')
    op.drop_column('registration', 'phone')
