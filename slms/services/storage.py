"""Per-tenant file storage service."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from flask import current_app
from werkzeug.utils import secure_filename

if TYPE_CHECKING:
    from slms.models import Organization


class TenantStorage:
    """Manages file storage for multi-tenant organizations."""

    def __init__(self, org: Organization):
        """
        Initialize tenant storage.

        Args:
            org: Organization instance
        """
        self.org = org
        self.base_path = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
        self.org_path = self.base_path / str(org.slug)

    def get_org_path(self, subdir: str | None = None) -> Path:
        """
        Get organization-specific storage path.

        Args:
            subdir: Optional subdirectory (e.g., 'logos', 'media', 'documents')

        Returns:
            Path object
        """
        if subdir:
            return self.org_path / subdir
        return self.org_path

    def ensure_path_exists(self, path: Path) -> None:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        file: BinaryIO,
        filename: str,
        subdir: str | None = None,
        allowed_extensions: set[str] | None = None
    ) -> tuple[str | None, str | None]:
        """
        Save a file to tenant storage.

        Args:
            file: File object to save
            filename: Original filename
            subdir: Subdirectory to save in
            allowed_extensions: Set of allowed file extensions

        Returns:
            (file_path, error_message)
        """
        try:
            # Validate file extension
            if allowed_extensions:
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext not in allowed_extensions:
                    return None, f"File type .{ext} is not allowed"

            # Check storage quota
            if self.org.storage_quota:
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Seek back to start

                if self.org.storage_used + file_size > self.org.storage_quota:
                    return None, "Storage quota exceeded"

            # Generate safe filename
            safe_name = secure_filename(filename)
            # Add unique prefix to avoid collisions
            unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"

            # Get storage path
            storage_path = self.get_org_path(subdir)
            self.ensure_path_exists(storage_path)

            # Save file
            file_path = storage_path / unique_name
            with open(file_path, 'wb') as f:
                file.seek(0)
                f.write(file.read())

            # Update storage usage
            from slms.extensions import db
            self.org.storage_used += file_path.stat().st_size
            db.session.commit()

            # Return relative path
            relative_path = str(file_path.relative_to(self.base_path))
            return relative_path, None

        except Exception as e:
            current_app.logger.error(f"Failed to save file: {e}")
            return None, "Failed to save file"

    def delete_file(self, file_path: str) -> tuple[bool, str | None]:
        """
        Delete a file from tenant storage.

        Args:
            file_path: Relative file path

        Returns:
            (success, error_message)
        """
        try:
            full_path = self.base_path / file_path

            # Security check: ensure path is within org directory
            if not str(full_path.resolve()).startswith(str(self.org_path.resolve())):
                return False, "Invalid file path"

            if not full_path.exists():
                return False, "File not found"

            # Get file size before deletion
            file_size = full_path.stat().st_size

            # Delete file
            full_path.unlink()

            # Update storage usage
            from slms.extensions import db
            self.org.storage_used = max(0, self.org.storage_used - file_size)
            db.session.commit()

            return True, None

        except Exception as e:
            current_app.logger.error(f"Failed to delete file: {e}")
            return False, "Failed to delete file"

    def get_file_url(self, file_path: str) -> str:
        """
        Get public URL for a file.

        Args:
            file_path: Relative file path

        Returns:
            Public URL
        """
        from flask import url_for
        return url_for('static', filename=f'uploads/{file_path}', _external=True)

    def list_files(self, subdir: str | None = None, pattern: str = '*') -> list[dict]:
        """
        List files in tenant storage.

        Args:
            subdir: Subdirectory to list
            pattern: Glob pattern (e.g., '*.jpg')

        Returns:
            List of file info dictionaries
        """
        try:
            storage_path = self.get_org_path(subdir)
            if not storage_path.exists():
                return []

            files = []
            for file_path in storage_path.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    relative_path = str(file_path.relative_to(self.base_path))
                    files.append({
                        'path': relative_path,
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'url': self.get_file_url(relative_path)
                    })

            return sorted(files, key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            current_app.logger.error(f"Failed to list files: {e}")
            return []

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics for the organization.

        Returns:
            Dictionary with storage stats
        """
        return {
            'used': self.org.storage_used,
            'quota': self.org.storage_quota,
            'percent': (self.org.storage_used / self.org.storage_quota * 100) if self.org.storage_quota else 0,
            'remaining': (self.org.storage_quota - self.org.storage_used) if self.org.storage_quota else None,
        }


def get_tenant_storage(org: Organization) -> TenantStorage:
    """
    Get tenant storage instance for an organization.

    Args:
        org: Organization instance

    Returns:
        TenantStorage instance
    """
    return TenantStorage(org)


# Common allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}
ALLOWED_MEDIA_EXTENSIONS = {'mp4', 'mov', 'avi', 'wmv', 'flv', 'mp3', 'wav'}


def upload_file(file, folder: str | None = None) -> dict:
    """
    Simple upload helper for file uploads.

    Args:
        file: File object from request.files
        folder: Optional subfolder

    Returns:
        Dictionary with filename, path, and public_url
    """
    from flask_login import current_user
    from slms.extensions import db

    # Get current user's organization
    org = current_user.organization if hasattr(current_user, 'organization') else None
    if not org:
        raise ValueError("No organization found for current user")

    storage = get_tenant_storage(org)

    # Save file
    file_path, error = storage.save_file(file, file.filename, subdir=folder)
    if error:
        raise ValueError(error)

    # Generate public URL
    public_url = storage.get_file_url(file_path)

    return {
        'filename': Path(file_path).name,
        'path': file_path,
        'public_url': public_url
    }


__all__ = [
    'TenantStorage',
    'get_tenant_storage',
    'upload_file',
    'ALLOWED_IMAGE_EXTENSIONS',
    'ALLOWED_DOCUMENT_EXTENSIONS',
    'ALLOWED_MEDIA_EXTENSIONS',
]
