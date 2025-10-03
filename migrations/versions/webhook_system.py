"""Webhook system for automation

Revision ID: webhook_system_001
Revises: content_moderation_001
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'webhook_system_001'
down_revision = 'content_moderation_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create webhook table
    op.create_table(
        'webhook',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=False),
        sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('timeout', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('custom_headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_webhook_org_id', 'webhook', ['org_id'])

    # Create webhook_delivery table
    op.create_table(
        'webhook_delivery',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('webhook_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhook.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_webhook_delivery_webhook_id', 'webhook_delivery', ['webhook_id'])
    op.create_index('ix_webhook_delivery_status', 'webhook_delivery', ['status'])
    op.create_index('ix_webhook_delivery_next_retry', 'webhook_delivery', ['next_retry_at'])


def downgrade():
    # Drop tables
    op.drop_index('ix_webhook_delivery_next_retry', table_name='webhook_delivery')
    op.drop_index('ix_webhook_delivery_status', table_name='webhook_delivery')
    op.drop_index('ix_webhook_delivery_webhook_id', table_name='webhook_delivery')
    op.drop_table('webhook_delivery')

    op.drop_index('ix_webhook_org_id', table_name='webhook')
    op.drop_table('webhook')
