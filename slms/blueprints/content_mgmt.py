"""Content management and moderation blueprint."""
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user

from slms.blueprints.common.tenant import tenant_required
from slms.models.models import ArticleStatus
from slms.services.content import ArticleService, AssetService, ContentPermissionService
from slms.services.audit import log_admin_action

content_mgmt_bp = Blueprint('content_mgmt', __name__, url_prefix='/content')


# ============= Content Dashboard =============

@content_mgmt_bp.route('/')
@login_required
@tenant_required
def dashboard():
    """Content management dashboard."""
    if not current_user.has_role('owner', 'admin', 'editor'):
        return jsonify({'error': 'Unauthorized'}), 403

    return render_template('content_dashboard.html')


@content_mgmt_bp.route('/articles')
@login_required
@tenant_required
def articles_list():
    """Articles list view."""
    if not current_user.has_role('owner', 'admin', 'editor'):
        return jsonify({'error': 'Unauthorized'}), 403

    return render_template('articles_list.html')


@content_mgmt_bp.route('/articles/new')
@login_required
@tenant_required
def article_new():
    """Create new article view."""
    if not ContentPermissionService.has_permission(current_user, 'create_article'):
        return jsonify({'error': 'Unauthorized'}), 403

    return render_template('article_editor.html', article=None)


@content_mgmt_bp.route('/articles/<article_id>/edit')
@login_required
@tenant_required
def article_edit(article_id):
    """Edit article view."""
    article = ArticleService.get_article(article_id, current_user.org_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    # Check permissions
    can_edit = (
        article.author_id == current_user.id and ContentPermissionService.has_permission(current_user, 'edit_own')
    ) or ContentPermissionService.has_permission(current_user, 'edit_all')

    if not can_edit:
        return jsonify({'error': 'Unauthorized'}), 403

    return render_template('article_editor.html', article=article)


@content_mgmt_bp.route('/assets')
@login_required
@tenant_required
def assets_manager():
    """Asset management view."""
    if not ContentPermissionService.has_permission(current_user, 'manage_assets'):
        return jsonify({'error': 'Unauthorized'}), 403

    return render_template('assets_manager.html')


# ============= Article API Endpoints =============

@content_mgmt_bp.route('/api/articles', methods=['GET'])
@login_required
@tenant_required
def list_articles():
    """List articles with filters."""
    status_filter = request.args.get('status')
    author_filter = request.args.get('author_id')
    include_trashed = request.args.get('include_trashed', 'false').lower() == 'true'

    status = None
    if status_filter:
        try:
            status = ArticleStatus(status_filter)
        except ValueError:
            pass

    # Editors can only see their own articles unless they have edit_all permission
    author_id = None
    if not ContentPermissionService.has_permission(current_user, 'edit_all'):
        author_id = current_user.id
    elif author_filter:
        author_id = author_filter

    articles = ArticleService.list_articles(
        org_id=current_user.org_id,
        status=status,
        author_id=author_id,
        include_trashed=include_trashed
    )

    return jsonify([{
        'id': a.id,
        'title': a.title,
        'slug': a.slug,
        'excerpt': a.excerpt,
        'status': a.status.value,
        'author': {'id': a.author.id, 'email': a.author.email} if a.author else None,
        'published_at': a.published_at.isoformat() if a.published_at else None,
        'view_count': a.view_count,
        'is_featured': a.is_featured,
        'is_pinned': a.is_pinned,
        'created_at': a.created_at.isoformat(),
        'updated_at': a.updated_at.isoformat()
    } for a in articles])


@content_mgmt_bp.route('/api/articles', methods=['POST'])
@login_required
@tenant_required
def create_article():
    """Create a new article."""
    if not ContentPermissionService.has_permission(current_user, 'create_article'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    article = ArticleService.create_article(
        org_id=current_user.org_id,
        author_id=current_user.id,
        title=title,
        content=content,
        excerpt=data.get('excerpt'),
        meta_description=data.get('meta_description'),
        meta_keywords=data.get('meta_keywords'),
        featured_image_url=data.get('featured_image_url'),
        categories=data.get('categories', []),
        tags=data.get('tags', [])
    )

    log_admin_action(
        user=current_user,
        action='create_article',
        entity_type='article',
        entity_id=article.id,
        metadata={'title': article.title}
    )

    return jsonify({
        'id': article.id,
        'title': article.title,
        'slug': article.slug,
        'status': article.status.value
    }), 201


@content_mgmt_bp.route('/api/articles/<article_id>', methods=['GET'])
@login_required
@tenant_required
def get_article(article_id):
    """Get article details."""
    article = ArticleService.get_article(article_id, current_user.org_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    return jsonify({
        'id': article.id,
        'title': article.title,
        'slug': article.slug,
        'excerpt': article.excerpt,
        'content': article.content,
        'meta_description': article.meta_description,
        'meta_keywords': article.meta_keywords,
        'featured_image_url': article.featured_image_url,
        'status': article.status.value,
        'published_at': article.published_at.isoformat() if article.published_at else None,
        'scheduled_publish_at': article.scheduled_publish_at.isoformat() if article.scheduled_publish_at else None,
        'author': {'id': article.author.id, 'email': article.author.email} if article.author else None,
        'last_edited_by': {'id': article.last_edited_by.id, 'email': article.last_edited_by.email} if article.last_edited_by else None,
        'reviewed_by': {'id': article.reviewed_by.id, 'email': article.reviewed_by.email} if article.reviewed_by else None,
        'reviewed_at': article.reviewed_at.isoformat() if article.reviewed_at else None,
        'review_notes': article.review_notes,
        'view_count': article.view_count,
        'is_featured': article.is_featured,
        'is_pinned': article.is_pinned,
        'categories': article.categories or [],
        'tags': article.tags or [],
        'created_at': article.created_at.isoformat(),
        'updated_at': article.updated_at.isoformat()
    })


@content_mgmt_bp.route('/api/articles/<article_id>', methods=['PUT'])
@login_required
@tenant_required
def update_article(article_id):
    """Update article."""
    article = ArticleService.get_article(article_id, current_user.org_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    # Check permissions
    can_edit = (
        article.author_id == current_user.id and ContentPermissionService.has_permission(current_user, 'edit_own')
    ) or ContentPermissionService.has_permission(current_user, 'edit_all')

    if not can_edit:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    updates = {}

    for field in ['title', 'content', 'excerpt', 'meta_description', 'meta_keywords',
                  'featured_image_url', 'categories', 'tags', 'is_featured', 'is_pinned']:
        if field in data:
            updates[field] = data[field]

    article = ArticleService.update_article(
        article_id=article_id,
        org_id=current_user.org_id,
        user_id=current_user.id,
        change_summary=data.get('change_summary'),
        **updates
    )

    log_admin_action(
        user=current_user,
        action='update_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'id': article.id, 'updated_at': article.updated_at.isoformat()})


@content_mgmt_bp.route('/api/articles/<article_id>/submit-review', methods=['POST'])
@login_required
@tenant_required
def submit_for_review(article_id):
    """Submit article for review."""
    article = ArticleService.submit_for_review(article_id, current_user.org_id, current_user.id)
    if not article:
        return jsonify({'error': 'Article not found or cannot be submitted'}), 400

    log_admin_action(
        user=current_user,
        action='submit_review',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>/approve', methods=['POST'])
@login_required
@tenant_required
def approve_article(article_id):
    """Approve article."""
    if not ContentPermissionService.has_permission(current_user, 'approve'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    article = ArticleService.approve_article(
        article_id=article_id,
        org_id=current_user.org_id,
        reviewer_id=current_user.id,
        notes=data.get('notes')
    )

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='approve_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>/reject', methods=['POST'])
@login_required
@tenant_required
def reject_article(article_id):
    """Reject article."""
    if not ContentPermissionService.has_permission(current_user, 'approve'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    notes = data.get('notes', '').strip()

    if not notes:
        return jsonify({'error': 'Review notes are required for rejection'}), 400

    article = ArticleService.reject_article(
        article_id=article_id,
        org_id=current_user.org_id,
        reviewer_id=current_user.id,
        notes=notes
    )

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='reject_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>/publish', methods=['POST'])
@login_required
@tenant_required
def publish_article(article_id):
    """Publish article."""
    if not ContentPermissionService.has_permission(current_user, 'publish'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json or {}
    scheduled_at = None
    if data.get('scheduled_at'):
        scheduled_at = datetime.fromisoformat(data['scheduled_at'])

    article = ArticleService.publish_article(
        article_id=article_id,
        org_id=current_user.org_id,
        user_id=current_user.id,
        scheduled_at=scheduled_at
    )

    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='publish_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({
        'status': article.status.value,
        'published_at': article.published_at.isoformat() if article.published_at else None
    })


@content_mgmt_bp.route('/api/articles/<article_id>/unpublish', methods=['POST'])
@login_required
@tenant_required
def unpublish_article(article_id):
    """Unpublish article."""
    if not ContentPermissionService.has_permission(current_user, 'publish'):
        return jsonify({'error': 'Unauthorized'}), 403

    article = ArticleService.unpublish_article(article_id, current_user.org_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='unpublish_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>/trash', methods=['POST'])
@login_required
@tenant_required
def trash_article(article_id):
    """Move article to trash."""
    if not ContentPermissionService.has_permission(current_user, 'delete'):
        return jsonify({'error': 'Unauthorized'}), 403

    article = ArticleService.trash_article(article_id, current_user.org_id, current_user.id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='trash_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>/restore', methods=['POST'])
@login_required
@tenant_required
def restore_article(article_id):
    """Restore article from trash."""
    if not ContentPermissionService.has_permission(current_user, 'delete'):
        return jsonify({'error': 'Unauthorized'}), 403

    article = ArticleService.restore_article(article_id, current_user.org_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    log_admin_action(
        user=current_user,
        action='restore_article',
        entity_type='article',
        entity_id=article.id
    )

    return jsonify({'status': article.status.value})


@content_mgmt_bp.route('/api/articles/<article_id>', methods=['DELETE'])
@login_required
@tenant_required
def delete_article_permanently(article_id):
    """Permanently delete article."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    if not ArticleService.delete_article_permanently(article_id, current_user.org_id):
        return jsonify({'error': 'Article not found or not in trash'}), 400

    log_admin_action(
        user=current_user,
        action='delete_article_permanent',
        entity_type='article',
        entity_id=article_id
    )

    return '', 204


# ============= Revision API Endpoints =============

@content_mgmt_bp.route('/api/articles/<article_id>/revisions', methods=['GET'])
@login_required
@tenant_required
def get_revisions(article_id):
    """Get article revision history."""
    revisions = ArticleService.get_revisions(article_id, current_user.org_id)

    return jsonify([{
        'id': r.id,
        'revision_number': r.revision_number,
        'title': r.title,
        'excerpt': r.excerpt,
        'change_summary': r.change_summary,
        'edited_by': {'id': r.edited_by.id, 'email': r.edited_by.email} if r.edited_by else None,
        'created_at': r.created_at.isoformat()
    } for r in revisions])


@content_mgmt_bp.route('/api/articles/<article_id>/revisions/<revision_id>/restore', methods=['POST'])
@login_required
@tenant_required
def restore_revision(article_id, revision_id):
    """Restore article to a previous revision."""
    article = ArticleService.restore_revision(article_id, current_user.org_id, revision_id, current_user.id)
    if not article:
        return jsonify({'error': 'Article or revision not found'}), 404

    log_admin_action(
        user=current_user,
        action='restore_revision',
        entity_type='article',
        entity_id=article.id,
        metadata={'revision_id': revision_id}
    )

    return jsonify({'message': 'Revision restored successfully'})


# ============= Asset API Endpoints =============

@content_mgmt_bp.route('/api/assets', methods=['GET'])
@login_required
@tenant_required
def list_assets():
    """List content assets."""
    if not ContentPermissionService.has_permission(current_user, 'manage_assets'):
        return jsonify({'error': 'Unauthorized'}), 403

    asset_type = request.args.get('type')
    folder = request.args.get('folder')

    assets = AssetService.list_assets(
        org_id=current_user.org_id,
        asset_type=asset_type,
        folder=folder
    )

    return jsonify([{
        'id': a.id,
        'filename': a.filename,
        'original_filename': a.original_filename,
        'public_url': a.public_url,
        'asset_type': a.asset_type,
        'mime_type': a.mime_type,
        'file_size': a.file_size,
        'folder': a.folder,
        'description': a.description,
        'alt_text': a.alt_text,
        'width': a.width,
        'height': a.height,
        'uploaded_by': {'id': a.uploaded_by.id, 'email': a.uploaded_by.email} if a.uploaded_by else None,
        'usage_count': a.usage_count,
        'created_at': a.created_at.isoformat()
    } for a in assets])


@content_mgmt_bp.route('/api/assets/<asset_id>', methods=['DELETE'])
@login_required
@tenant_required
def delete_asset(asset_id):
    """Delete content asset."""
    if not ContentPermissionService.has_permission(current_user, 'manage_assets'):
        return jsonify({'error': 'Unauthorized'}), 403

    if not AssetService.delete_asset(asset_id, current_user.org_id):
        return jsonify({'error': 'Asset not found'}), 404

    log_admin_action(
        user=current_user,
        action='delete_asset',
        entity_type='content_asset',
        entity_id=asset_id
    )

    return '', 204


# ============= Permission API Endpoints =============

@content_mgmt_bp.route('/api/permissions/check', methods=['POST'])
@login_required
@tenant_required
def check_permission():
    """Check if user has a permission."""
    data = request.json
    permission = data.get('permission')

    if not permission:
        return jsonify({'error': 'Permission type required'}), 400

    has_perm = ContentPermissionService.has_permission(current_user, permission)
    return jsonify({'has_permission': has_perm})


@content_mgmt_bp.route('/api/permissions/user/<user_id>', methods=['GET'])
@login_required
@tenant_required
def get_user_permissions(user_id):
    """Get all permissions for a user."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    permissions = ContentPermissionService.get_user_permissions(user_id)
    return jsonify({'permissions': permissions})


@content_mgmt_bp.route('/api/permissions/grant', methods=['POST'])
@login_required
@tenant_required
def grant_permission():
    """Grant permission to user."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    user_id = data.get('user_id')
    permission = data.get('permission')

    if not user_id or not permission:
        return jsonify({'error': 'user_id and permission are required'}), 400

    ContentPermissionService.grant_permission(
        user_id=user_id,
        org_id=current_user.org_id,
        permission=permission,
        granted_by_id=current_user.id
    )

    return jsonify({'message': 'Permission granted successfully'})


@content_mgmt_bp.route('/api/permissions/revoke', methods=['POST'])
@login_required
@tenant_required
def revoke_permission():
    """Revoke permission from user."""
    if not current_user.has_role('owner', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    user_id = data.get('user_id')
    permission = data.get('permission')

    if not user_id or not permission:
        return jsonify({'error': 'user_id and permission are required'}), 400

    ContentPermissionService.revoke_permission(user_id, permission)
    return jsonify({'message': 'Permission revoked successfully'})
