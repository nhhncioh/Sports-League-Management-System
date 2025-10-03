"""Content moderation system

Revision ID: content_moderation_001
Revises: scoring_system_001
Create Date: 2025-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'content_moderation_001'
down_revision = 'scoring_system_001'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    json_type = postgresql.JSONB(astext_type=sa.Text()) if dialect == 'postgresql' else sa.JSON()
    # Create article table
    op.create_table(
        'article',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('slug', sa.String(length=600), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('meta_description', sa.String(length=500), nullable=True),
        sa.Column('meta_keywords', sa.String(length=500), nullable=True),
        sa.Column('featured_image_url', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('author_id', sa.String(length=36), nullable=False),
        sa.Column('last_edited_by_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_by_id', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('trashed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trashed_by_id', sa.String(length=36), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('categories', json_type, nullable=True),
        sa.Column('tags', json_type, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_edited_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trashed_by_id'], ['user.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_article_org_id', 'article', ['org_id'])
    op.create_index('ix_article_author_id', 'article', ['author_id'])
    op.create_index('ix_article_org_status', 'article', ['org_id', 'status'])
    op.create_index('ix_article_org_published', 'article', ['org_id', 'published_at'])
    op.create_index('ix_article_slug', 'article', ['slug'])

    # Create article_revision table
    op.create_table(
        'article_revision',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('article_id', sa.String(length=36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('edited_by_id', sa.String(length=36), nullable=False),
        sa.Column('change_summary', sa.String(length=500), nullable=True),
        sa.Column('metadata_snapshot', json_type, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['article_id'], ['article.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['edited_by_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_article_revision_org_id', 'article_revision', ['org_id'])
    op.create_index('ix_article_revision_article', 'article_revision', ['article_id'])
    op.create_index('ix_article_revision_edited_by', 'article_revision', ['edited_by_id'])

    # Create content_asset table
    op.create_table(
        'content_asset',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('storage_path', sa.String(length=1000), nullable=False),
        sa.Column('public_url', sa.String(length=1000), nullable=True),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('mime_type', sa.String(length=200), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('folder', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('alt_text', sa.String(length=500), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_id', sa.String(length=36), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_content_asset_org_id', 'content_asset', ['org_id'])
    op.create_index('ix_content_asset_org_type', 'content_asset', ['org_id', 'asset_type'])
    op.create_index('ix_content_asset_org_folder', 'content_asset', ['org_id', 'folder'])
    op.create_index('ix_content_asset_uploaded_by', 'content_asset', ['uploaded_by_id'])

    # Create editor_permission table
    op.create_table(
        'editor_permission',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('permission_type', sa.String(length=100), nullable=False),
        sa.Column('granted_by_id', sa.String(length=36), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'permission_type', name='uq_user_permission'),
        sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by_id'], ['user.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_editor_permission_org_id', 'editor_permission', ['org_id'])
    op.create_index('ix_editor_permission_user_id', 'editor_permission', ['user_id'])


def downgrade():
    # Drop tables
    op.drop_index('ix_editor_permission_user_id', table_name='editor_permission')
    op.drop_index('ix_editor_permission_org_id', table_name='editor_permission')
    op.drop_table('editor_permission')

    op.drop_index('ix_content_asset_uploaded_by', table_name='content_asset')
    op.drop_index('ix_content_asset_org_folder', table_name='content_asset')
    op.drop_index('ix_content_asset_org_type', table_name='content_asset')
    op.drop_index('ix_content_asset_org_id', table_name='content_asset')
    op.drop_table('content_asset')

    op.drop_index('ix_article_revision_edited_by', table_name='article_revision')
    op.drop_index('ix_article_revision_article', table_name='article_revision')
    op.drop_index('ix_article_revision_org_id', table_name='article_revision')
    op.drop_table('article_revision')

    op.drop_index('ix_article_slug', table_name='article')
    op.drop_index('ix_article_org_published', table_name='article')
    op.drop_index('ix_article_org_status', table_name='article')
    op.drop_index('ix_article_author_id', table_name='article')
    op.drop_index('ix_article_org_id', table_name='article')
    op.drop_table('article')
