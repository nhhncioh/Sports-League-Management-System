"""Utilities for managing persisted media assets."""

from __future__ import annotations

import mimetypes
from typing import Iterable

from flask import g
from werkzeug.datastructures import FileStorage

from slms.extensions import db
from slms.models import MediaAsset
from slms.services.uploads import store_media_file, delete_media_file


def create_media_asset(
    *,
    title: str,
    description: str | None = None,
    category: str | None = None,
    media_type: str | None = None,
    file: FileStorage | None = None,
    source_url: str | None = None,
    alt_text: str | None = None,
    uploaded_by_user_id: str | None = None,
) -> MediaAsset:
    """Persist a new media asset and return it."""
    org = getattr(g, 'org', None)
    if org is None:
        raise ValueError('Organization context is required to create media assets')

    cleaned_title = (title or '').strip() or (file.filename if file and file.filename else 'Untitled asset')
    asset = MediaAsset(
        org_id=org.id,
        title=cleaned_title,
        description=(description or '').strip() or None,
        category=(category or '').strip() or None,
        alt_text=(alt_text or '').strip() or None,
    )

    if uploaded_by_user_id:
        asset.uploaded_by_user_id = uploaded_by_user_id

    if file and file.filename:
        stored = store_media_file(file, getattr(g, 'org_slug', None))
        asset.storage_path = stored['storage_path']
        asset.public_url = stored['public_url']
        asset.mime_type = stored['mime_type']
        asset.file_size = stored['file_size']
        asset.original_name = stored['original_name']
        asset.media_type = media_type or ('video' if (asset.mime_type or '').startswith('video/') else 'image')
    elif source_url:
        cleaned_source = source_url.strip()
        if not cleaned_source:
            raise ValueError('Source URL must not be empty')
        asset.source_url = cleaned_source
        asset.public_url = cleaned_source
        guess = mimetypes.guess_type(cleaned_source)[0]
        asset.mime_type = guess
        asset.media_type = media_type or ('video' if (guess or '').startswith('video/') else 'image')
    else:
        raise ValueError('Either a file upload or source URL must be provided')

    db.session.add(asset)
    db.session.commit()
    return asset


def delete_media_asset(asset: MediaAsset) -> None:
    """Remove the asset record and any stored file."""
    if asset.storage_path:
        delete_media_file(asset.storage_path)
    db.session.delete(asset)
    db.session.commit()


def serialize_media_asset(asset: MediaAsset) -> dict:
    """Serialize an asset for JSON responses."""
    return {
        'id': asset.id,
        'title': asset.title,
        'description': asset.description,
        'category': asset.category,
        'media_type': asset.media_type,
        'url': asset.url,
        'public_url': asset.public_url,
        'source_url': asset.source_url,
        'alt_text': asset.alt_text,
        'file_size': asset.file_size,
        'mime_type': asset.mime_type,
        'original_name': asset.original_name,
        'created_at': asset.created_at.isoformat() if asset.created_at else None,
    }


def serialize_media_collection(assets: Iterable[MediaAsset]) -> list[dict]:
    """Helper for serializing multiple assets."""
    return [serialize_media_asset(asset) for asset in assets]


def update_media_asset(
    asset: MediaAsset,
    *,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    media_type: str | None = None,
    file: FileStorage | None = None,
    source_url: str | None = None,
    alt_text: str | None = None,
) -> MediaAsset:
    """Update an existing media asset in-place."""
    if title is not None:
        asset.title = title.strip() or asset.title
    if description is not None:
        asset.description = description.strip() or None
    if category is not None:
        asset.category = category.strip() or None
    if alt_text is not None:
        asset.alt_text = alt_text.strip() or None

    if file and file.filename:
        if asset.storage_path:
            delete_media_file(asset.storage_path)
        stored = store_media_file(file, getattr(g, 'org_slug', None))
        asset.storage_path = stored['storage_path']
        asset.public_url = stored['public_url']
        asset.source_url = None
        asset.mime_type = stored['mime_type']
        asset.file_size = stored['file_size']
        asset.original_name = stored['original_name']
        asset.media_type = media_type or ('video' if (asset.mime_type or '').startswith('video/') else 'image')
    elif source_url is not None:
        cleaned = source_url.strip()
        if cleaned:
            if asset.storage_path:
                delete_media_file(asset.storage_path)
            asset.storage_path = None
            asset.source_url = cleaned
            asset.public_url = cleaned
            asset.original_name = None
            asset.file_size = None
            asset.mime_type = mimetypes.guess_type(cleaned)[0]
            asset.media_type = media_type or ('video' if (asset.mime_type or '').startswith('video/') else 'image')
        else:
            asset.source_url = None
            asset.public_url = None
            asset.mime_type = None
            asset.file_size = None
            asset.original_name = None

    if media_type and not (file and file.filename) and source_url is None:
        asset.media_type = media_type

    db.session.commit()
    return asset

__all__ = [
    'create_media_asset',
    'update_media_asset',
    'delete_media_asset',
    'serialize_media_asset',
    'serialize_media_collection',
]

