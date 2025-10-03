"""Content management and moderation service."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from slms.extensions import db
from slms.models.models import (
    Article, ArticleStatus, ArticleRevision, ContentAsset,
    EditorPermission, User, UserRole
)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


class ContentPermissionService:
    """Service for managing editor permissions."""

    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Owners and admins have all permissions
        if user.has_role(UserRole.OWNER, UserRole.ADMIN):
            return True

        # Check specific permission
        stmt = (
            select(EditorPermission)
            .where(EditorPermission.user_id == user.id)
            .where(EditorPermission.permission_type == permission)
        )
        return db.session.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def grant_permission(
        user_id: str,
        org_id: str,
        permission: str,
        granted_by_id: str
    ) -> EditorPermission:
        """Grant a permission to a user."""
        # Check if permission already exists
        stmt = (
            select(EditorPermission)
            .where(EditorPermission.user_id == user_id)
            .where(EditorPermission.permission_type == permission)
        )
        existing = db.session.execute(stmt).scalar_one_or_none()

        if existing:
            return existing

        perm = EditorPermission(
            org_id=org_id,
            user_id=user_id,
            permission_type=permission,
            granted_by_id=granted_by_id
        )
        db.session.add(perm)
        db.session.commit()
        return perm

    @staticmethod
    def revoke_permission(user_id: str, permission: str) -> bool:
        """Revoke a permission from a user."""
        stmt = (
            select(EditorPermission)
            .where(EditorPermission.user_id == user_id)
            .where(EditorPermission.permission_type == permission)
        )
        perm = db.session.execute(stmt).scalar_one_or_none()

        if perm:
            db.session.delete(perm)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_user_permissions(user_id: str) -> list[str]:
        """Get all permissions for a user."""
        stmt = (
            select(EditorPermission.permission_type)
            .where(EditorPermission.user_id == user_id)
        )
        return [p[0] for p in db.session.execute(stmt).all()]


class ArticleService:
    """Service for article management."""

    @staticmethod
    def create_article(
        org_id: str,
        author_id: str,
        title: str,
        content: str,
        excerpt: str | None = None,
        **kwargs
    ) -> Article:
        """Create a new article in draft status."""
        slug = slugify(title)

        # Ensure unique slug
        base_slug = slug
        counter = 1
        while True:
            stmt = select(Article).where(and_(
                Article.org_id == org_id,
                Article.slug == slug
            ))
            if not db.session.execute(stmt).scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        article = Article(
            org_id=org_id,
            author_id=author_id,
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            status=ArticleStatus.DRAFT,
            **kwargs
        )

        db.session.add(article)
        db.session.commit()

        # Create initial revision
        ArticleService._create_revision(
            article=article,
            edited_by_id=author_id,
            change_summary="Initial version"
        )

        return article

    @staticmethod
    def update_article(
        article_id: str,
        org_id: str,
        user_id: str,
        change_summary: str | None = None,
        **updates
    ) -> Article | None:
        """Update article and create revision."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        # Track if content changed
        content_changed = 'content' in updates or 'title' in updates

        for key, value in updates.items():
            if hasattr(article, key) and key not in ['id', 'org_id', 'author_id', 'created_at']:
                setattr(article, key, value)

        article.last_edited_by_id = user_id

        # Create revision if content changed
        if content_changed:
            ArticleService._create_revision(
                article=article,
                edited_by_id=user_id,
                change_summary=change_summary
            )

        db.session.commit()
        return article

    @staticmethod
    def _create_revision(article: Article, edited_by_id: str, change_summary: str | None = None):
        """Create a revision snapshot."""
        # Get latest revision number
        stmt = (
            select(ArticleRevision.revision_number)
            .where(ArticleRevision.article_id == article.id)
            .order_by(ArticleRevision.revision_number.desc())
        )
        latest = db.session.execute(stmt).scalar_one_or_none()
        revision_number = (latest or 0) + 1

        revision = ArticleRevision(
            org_id=article.org_id,
            article_id=article.id,
            revision_number=revision_number,
            title=article.title,
            content=article.content,
            excerpt=article.excerpt,
            edited_by_id=edited_by_id,
            change_summary=change_summary,
            metadata_snapshot={
                'categories': article.categories,
                'tags': article.tags,
                'featured_image_url': article.featured_image_url
            }
        )
        db.session.add(revision)

    @staticmethod
    def submit_for_review(article_id: str, org_id: str, user_id: str) -> Article | None:
        """Submit article for review."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        if article.status != ArticleStatus.DRAFT:
            return None

        article.status = ArticleStatus.PENDING_REVIEW
        article.last_edited_by_id = user_id
        db.session.commit()
        return article

    @staticmethod
    def approve_article(article_id: str, org_id: str, reviewer_id: str, notes: str | None = None) -> Article | None:
        """Approve article for publishing."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        article.status = ArticleStatus.APPROVED
        article.reviewed_by_id = reviewer_id
        article.reviewed_at = datetime.now(timezone.utc)
        article.review_notes = notes
        db.session.commit()
        return article

    @staticmethod
    def reject_article(article_id: str, org_id: str, reviewer_id: str, notes: str) -> Article | None:
        """Reject article and send back to draft."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        article.status = ArticleStatus.DRAFT
        article.reviewed_by_id = reviewer_id
        article.reviewed_at = datetime.now(timezone.utc)
        article.review_notes = notes
        db.session.commit()
        return article

    @staticmethod
    def publish_article(article_id: str, org_id: str, user_id: str, scheduled_at: datetime | None = None) -> Article | None:
        """Publish article (immediately or scheduled)."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        if scheduled_at:
            article.scheduled_publish_at = scheduled_at
            article.status = ArticleStatus.APPROVED
        else:
            article.status = ArticleStatus.PUBLISHED
            article.published_at = datetime.now(timezone.utc)

        article.last_edited_by_id = user_id
        db.session.commit()
        return article

    @staticmethod
    def unpublish_article(article_id: str, org_id: str) -> Article | None:
        """Unpublish article (move back to draft)."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        article.status = ArticleStatus.DRAFT
        article.published_at = None
        db.session.commit()
        return article

    @staticmethod
    def trash_article(article_id: str, org_id: str, user_id: str) -> Article | None:
        """Move article to trash."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        article.status = ArticleStatus.TRASHED
        article.trashed_at = datetime.now(timezone.utc)
        article.trashed_by_id = user_id
        db.session.commit()
        return article

    @staticmethod
    def restore_article(article_id: str, org_id: str) -> Article | None:
        """Restore article from trash."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return None

        article.status = ArticleStatus.DRAFT
        article.trashed_at = None
        article.trashed_by_id = None
        db.session.commit()
        return article

    @staticmethod
    def delete_article_permanently(article_id: str, org_id: str) -> bool:
        """Permanently delete article (only from trash)."""
        article = db.session.get(Article, article_id)
        if not article or article.org_id != org_id:
            return False

        if article.status != ArticleStatus.TRASHED:
            return False

        db.session.delete(article)
        db.session.commit()
        return True

    @staticmethod
    def get_article(article_id: str, org_id: str) -> Article | None:
        """Get article with all relationships loaded."""
        stmt = (
            select(Article)
            .where(Article.id == article_id)
            .where(Article.org_id == org_id)
            .options(
                joinedload(Article.author),
                joinedload(Article.last_edited_by),
                joinedload(Article.reviewed_by),
                joinedload(Article.revisions)
            )
        )
        return db.session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_articles(
        org_id: str,
        status: ArticleStatus | None = None,
        author_id: str | None = None,
        include_trashed: bool = False
    ) -> list[Article]:
        """List articles with filters."""
        conditions = [Article.org_id == org_id]

        if status:
            conditions.append(Article.status == status)
        elif not include_trashed:
            conditions.append(Article.status != ArticleStatus.TRASHED)

        if author_id:
            conditions.append(Article.author_id == author_id)

        stmt = (
            select(Article)
            .where(and_(*conditions))
            .options(joinedload(Article.author))
            .order_by(Article.created_at.desc())
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def get_revisions(article_id: str, org_id: str) -> list[ArticleRevision]:
        """Get all revisions for an article."""
        stmt = (
            select(ArticleRevision)
            .where(ArticleRevision.article_id == article_id)
            .where(ArticleRevision.org_id == org_id)
            .options(joinedload(ArticleRevision.edited_by))
            .order_by(ArticleRevision.revision_number.desc())
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def restore_revision(article_id: str, org_id: str, revision_id: str, user_id: str) -> Article | None:
        """Restore article to a previous revision."""
        article = db.session.get(Article, article_id)
        revision = db.session.get(ArticleRevision, revision_id)

        if not article or not revision or article.org_id != org_id:
            return None

        article.title = revision.title
        article.content = revision.content
        article.excerpt = revision.excerpt
        article.last_edited_by_id = user_id

        # Create new revision noting restoration
        ArticleService._create_revision(
            article=article,
            edited_by_id=user_id,
            change_summary=f"Restored from revision #{revision.revision_number}"
        )

        db.session.commit()
        return article

    @staticmethod
    def increment_view_count(article_id: str):
        """Increment article view count."""
        article = db.session.get(Article, article_id)
        if article:
            article.view_count += 1
            db.session.commit()


class AssetService:
    """Service for content asset management."""

    @staticmethod
    def create_asset(
        org_id: str,
        uploaded_by_id: str,
        filename: str,
        storage_path: str,
        **kwargs
    ) -> ContentAsset:
        """Register a new content asset."""
        asset = ContentAsset(
            org_id=org_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            original_filename=kwargs.get('original_filename', filename),
            storage_path=storage_path,
            **{k: v for k, v in kwargs.items() if k != 'original_filename'}
        )
        db.session.add(asset)
        db.session.commit()
        return asset

    @staticmethod
    def list_assets(
        org_id: str,
        asset_type: str | None = None,
        folder: str | None = None
    ) -> list[ContentAsset]:
        """List content assets with filters."""
        conditions = [ContentAsset.org_id == org_id]

        if asset_type:
            conditions.append(ContentAsset.asset_type == asset_type)
        if folder:
            conditions.append(ContentAsset.folder == folder)

        stmt = (
            select(ContentAsset)
            .where(and_(*conditions))
            .options(joinedload(ContentAsset.uploaded_by))
            .order_by(ContentAsset.created_at.desc())
        )
        return list(db.session.execute(stmt).scalars())

    @staticmethod
    def get_asset(asset_id: str, org_id: str) -> ContentAsset | None:
        """Get content asset."""
        asset = db.session.get(ContentAsset, asset_id)
        if asset and asset.org_id == org_id:
            return asset
        return None

    @staticmethod
    def delete_asset(asset_id: str, org_id: str) -> bool:
        """Delete content asset."""
        asset = db.session.get(ContentAsset, asset_id)
        if not asset or asset.org_id != org_id:
            return False

        db.session.delete(asset)
        db.session.commit()
        return True

    @staticmethod
    def update_asset_usage(asset_id: str):
        """Update asset usage tracking."""
        asset = db.session.get(ContentAsset, asset_id)
        if asset:
            asset.usage_count += 1
            asset.last_used_at = datetime.now(timezone.utc)
            db.session.commit()
