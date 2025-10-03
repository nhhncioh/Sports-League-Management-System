"""Normalize organization constraints (custom_domain unique)

Revision ID: org_normalization_001
Revises: ticker_system_001
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'org_normalization_001'
down_revision = ('ticker_system_001', 'webhook_system_001')
branch_labels = None
depends_on = None


def upgrade():
    # Ensure unique constraint on custom_domain to match model (allows multiple NULLs)
    try:
        op.create_unique_constraint('uq_organization_custom_domain', 'organization', ['custom_domain'])
    except Exception:
        # If already exists or dialect limitations, ignore
        pass


def downgrade():
    try:
        op.drop_constraint('uq_organization_custom_domain', 'organization', type_='unique')
    except Exception:
        pass
