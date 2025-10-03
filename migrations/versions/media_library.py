"""add media asset table

Revision ID: media_library
Revises: enhance_registration
Create Date: 2025-10-02 15:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'media_library'
down_revision = 'enhance_registration'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'media_asset',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('media_type', sa.String(length=20), nullable=False, server_default='image'),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('storage_path', sa.String(length=512), nullable=True),
        sa.Column('public_url', sa.String(length=512), nullable=True),
        sa.Column('source_url', sa.String(length=1024), nullable=True),
        sa.Column('original_name', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('alt_text', sa.String(length=255), nullable=True),
        sa.Column('uploaded_by_user_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_media_asset_org_created', 'media_asset', ['org_id', 'created_at'], unique=False)
    op.create_index('ix_media_asset_org_type', 'media_asset', ['org_id', 'media_type'], unique=False)
    op.create_index('ix_media_asset_org_category', 'media_asset', ['org_id', 'category'], unique=False)


def downgrade():
    op.drop_index('ix_media_asset_org_category', table_name='media_asset')
    op.drop_index('ix_media_asset_org_type', table_name='media_asset')
    op.drop_index('ix_media_asset_org_created', table_name='media_asset')
    op.drop_table('media_asset')
