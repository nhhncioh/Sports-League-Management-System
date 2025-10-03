"""add_user_security_fields

Revision ID: 51f90b7c9cf0
Revises: media_library
Create Date: 2025-10-03 14:10:27.720485

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '51f90b7c9cf0'
down_revision = 'media_library'
branch_labels = None
depends_on = None


def upgrade():
    # Add MFA and security fields to user table
    op.add_column('user', sa.Column('mfa_secret', sa.String(length=32), nullable=True))
    op.add_column('user', sa.Column('mfa_recovery_codes', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('password_reset_token', sa.String(length=64), nullable=True))
    op.add_column('user', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user', sa.Column('last_login_ip', sa.String(length=45), nullable=True))

    # Add index for password reset token lookups
    op.create_index('ix_user_password_reset_token', 'user', ['password_reset_token'], unique=False)


def downgrade():
    op.drop_index('ix_user_password_reset_token', table_name='user')
    op.drop_column('user', 'last_login_ip')
    op.drop_column('user', 'last_login_at')
    op.drop_column('user', 'locked_until')
    op.drop_column('user', 'failed_login_attempts')
    op.drop_column('user', 'password_reset_expires')
    op.drop_column('user', 'password_reset_token')
    op.drop_column('user', 'mfa_recovery_codes')
    op.drop_column('user', 'mfa_secret')
