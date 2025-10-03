"""enhance_organization_multi_tenant

Revision ID: 99a12646cb8d
Revises: 51f90b7c9cf0
Create Date: 2025-10-03 14:27:32.853844

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99a12646cb8d'
down_revision = '51f90b7c9cf0'
branch_labels = None
depends_on = None


def upgrade():
    # Add new organization fields for multi-tenant features
    op.add_column('organization', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('organization', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('organization', sa.Column('contact_phone', sa.String(length=32), nullable=True))
    op.add_column('organization', sa.Column('website_url', sa.String(length=512), nullable=True))

    # Branding fields
    op.add_column('organization', sa.Column('secondary_color', sa.String(length=32), nullable=True))
    op.add_column('organization', sa.Column('favicon_url', sa.String(length=512), nullable=True))
    op.add_column('organization', sa.Column('banner_image_url', sa.String(length=512), nullable=True))
    op.add_column('organization', sa.Column('custom_css', sa.Text(), nullable=True))

    # Settings
    op.add_column('organization', sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'))
    op.add_column('organization', sa.Column('locale', sa.String(length=10), nullable=False, server_default='en_US'))
    op.add_column('organization', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Custom domain
    op.add_column('organization', sa.Column('custom_domain', sa.String(length=255), nullable=True))

    # Storage management
    op.add_column('organization', sa.Column('storage_quota', sa.Integer(), nullable=True))
    op.add_column('organization', sa.Column('storage_used', sa.Integer(), nullable=False, server_default='0'))

    # Plan/subscription
    op.add_column('organization', sa.Column('plan_type', sa.String(length=32), nullable=False, server_default='free'))
    op.add_column('organization', sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Add indexes
    op.create_index('ix_organization_slug', 'organization', ['slug'], unique=False)
    op.create_index('ix_organization_custom_domain', 'organization', ['custom_domain'], unique=False)


def downgrade():
    op.drop_index('ix_organization_custom_domain', table_name='organization')
    op.drop_index('ix_organization_slug', table_name='organization')

    op.drop_column('organization', 'plan_expires_at')
    op.drop_column('organization', 'plan_type')
    op.drop_column('organization', 'storage_used')
    op.drop_column('organization', 'storage_quota')
    op.drop_column('organization', 'custom_domain')
    op.drop_column('organization', 'is_active')
    op.drop_column('organization', 'locale')
    op.drop_column('organization', 'timezone')
    op.drop_column('organization', 'custom_css')
    op.drop_column('organization', 'banner_image_url')
    op.drop_column('organization', 'favicon_url')
    op.drop_column('organization', 'secondary_color')
    op.drop_column('organization', 'website_url')
    op.drop_column('organization', 'contact_phone')
    op.drop_column('organization', 'contact_email')
    op.drop_column('organization', 'description')
