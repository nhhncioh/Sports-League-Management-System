"""add season registration fields

Revision ID: add_season_registration_fields
Revises: 55d8933bd3cb
Create Date: 2025-09-17 20:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_season_registration_fields'
down_revision = '55d8933bd3cb'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    season_cols = {c['name'] for c in inspector.get_columns('season')}
    if 'registration_open' not in season_cols:
        with op.batch_alter_table('season', schema=None) as batch_op:
            batch_op.add_column(sa.Column('registration_open', sa.Boolean(), nullable=False, server_default='false'))
    if 'registration_mode' not in season_cols:
        with op.batch_alter_table('season', schema=None) as batch_op:
            batch_op.add_column(sa.Column('registration_mode', sa.Enum('OPEN', 'APPROVAL', 'CLOSED', name='registration_mode', native_enum=False), nullable=True))
    if 'fee_cents' not in season_cols:
        with op.batch_alter_table('season', schema=None) as batch_op:
            batch_op.add_column(sa.Column('fee_cents', sa.Integer(), nullable=True))
    if 'currency' not in season_cols:
        with op.batch_alter_table('season', schema=None) as batch_op:
            batch_op.add_column(sa.Column('currency', sa.String(length=3), nullable=False, server_default='CAD'))

    venue_cols = {c['name'] for c in inspector.get_columns('venue')}
    if 'open_time' not in venue_cols:
        with op.batch_alter_table('venue', schema=None) as batch_op:
            batch_op.add_column(sa.Column('open_time', sa.String(length=5), nullable=True))
    if 'close_time' not in venue_cols:
        with op.batch_alter_table('venue', schema=None) as batch_op:
            batch_op.add_column(sa.Column('close_time', sa.String(length=5), nullable=True))


def downgrade():
    # Remove registration fields from season table
    with op.batch_alter_table('season', schema=None) as batch_op:
        batch_op.drop_column('currency')
        batch_op.drop_column('fee_cents')
        batch_op.drop_column('registration_mode')
        batch_op.drop_column('registration_open')
