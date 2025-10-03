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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('organization')}

    # Add new organization fields for multi-tenant features (guarded)
    if 'description' not in cols:
        op.add_column('organization', sa.Column('description', sa.Text(), nullable=True))
    if 'contact_email' not in cols:
        op.add_column('organization', sa.Column('contact_email', sa.String(length=255), nullable=True))
    if 'contact_phone' not in cols:
        op.add_column('organization', sa.Column('contact_phone', sa.String(length=32), nullable=True))
    if 'website_url' not in cols:
        op.add_column('organization', sa.Column('website_url', sa.String(length=512), nullable=True))

    # Branding fields
    if 'secondary_color' not in cols:
        op.add_column('organization', sa.Column('secondary_color', sa.String(length=32), nullable=True))
    if 'favicon_url' not in cols:
        op.add_column('organization', sa.Column('favicon_url', sa.String(length=512), nullable=True))
    if 'banner_image_url' not in cols:
        op.add_column('organization', sa.Column('banner_image_url', sa.String(length=512), nullable=True))
    if 'custom_css' not in cols:
        op.add_column('organization', sa.Column('custom_css', sa.Text(), nullable=True))

    # Settings
    if 'timezone' not in cols:
        op.add_column('organization', sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'))
    if 'locale' not in cols:
        op.add_column('organization', sa.Column('locale', sa.String(length=10), nullable=False, server_default='en_US'))
    if 'is_active' not in cols:
        op.add_column('organization', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Custom domain
    if 'custom_domain' not in cols:
        op.add_column('organization', sa.Column('custom_domain', sa.String(length=255), nullable=True))

    # Storage management
    if 'storage_quota' not in cols:
        op.add_column('organization', sa.Column('storage_quota', sa.Integer(), nullable=True))
    if 'storage_used' not in cols:
        op.add_column('organization', sa.Column('storage_used', sa.Integer(), nullable=False, server_default='0'))

    # Plan/subscription
    if 'plan_type' not in cols:
        op.add_column('organization', sa.Column('plan_type', sa.String(length=32), nullable=False, server_default='free'))
    if 'plan_expires_at' not in cols:
        op.add_column('organization', sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Add indexes if missing
    idx = {i['name'] for i in inspector.get_indexes('organization')}
    if 'ix_organization_slug' not in idx:
        op.create_index('ix_organization_slug', 'organization', ['slug'], unique=False)
    if 'ix_organization_custom_domain' not in idx:
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
