"""File upload service for handling user uploads."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
STATIC_UPLOAD_SUBDIR = 'uploads'


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _static_upload_root() -> Path:
    """Return (and ensure) the static uploads root."""
    static_root = Path(current_app.static_folder)
    upload_root = static_root / STATIC_UPLOAD_SUBDIR
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root


def _ensure_within_static_root(path: Path) -> None:
    static_root = Path(current_app.static_folder).resolve()
    resolved = path.resolve()
    if not str(resolved).startswith(str(static_root)):
        raise PermissionError('Attempted to write outside static directory')


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _determine_size(file: FileStorage) -> int:
    stream = file.stream
    current = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(current)
    return size


def save_upload(file: FileStorage, subfolder: str = 'general') -> str | None:
    """
    Save an uploaded file and return the relative URL path.

    Args:
        file: The uploaded file from the form
        subfolder: Subfolder within uploads directory (e.g., 'team_logos', 'player_photos')

    Returns:
        Relative URL path to the uploaded file, or None if upload failed
    """
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename):
        return None

    upload_root = _ensure_directory(_static_upload_root() / subfolder)

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = upload_root / filename
    _ensure_within_static_root(filepath)

    size = _determine_size(file)
    if size > MAX_FILE_SIZE:
        return None

    file.stream.seek(0)
    file.save(str(filepath))
    relative = filepath.relative_to(Path(current_app.static_folder))
    return f"/static/{relative.as_posix()}"


def delete_upload(file_url: str) -> bool:
    """
    Delete an uploaded file given its URL path.

    Args:
        file_url: The URL path of the file (e.g., '/static/uploads/team_logos/abc123.jpg')

    Returns:
        True if deletion was successful, False otherwise
    """
    if not file_url or not file_url.startswith('/static/'):
        return False

    relative = file_url[len('/static/'):]
    target = Path(current_app.static_folder) / relative
    _ensure_within_static_root(target)

    if target.exists() and target.is_file():
        target.unlink()
        _cleanup_empty_dirs(target.parent)
        return True

    return False


def store_media_file(file: FileStorage, org_slug: str | None, library_subdir: str = 'media') -> dict:
    """Persist a media library upload and return metadata for the saved file."""
    if not file or file.filename == '':
        raise ValueError('No file provided')

    if not allowed_file(file.filename):
        raise ValueError('Unsupported file type')

    size = _determine_size(file)
    if size > MAX_FILE_SIZE:
        raise ValueError('File exceeds maximum upload size of 5 MB')

    safe_org = secure_filename(org_slug or 'default') or 'default'
    upload_root = _ensure_directory(_static_upload_root() / library_subdir / safe_org)

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = upload_root / unique_name
    _ensure_within_static_root(filepath)

    file.stream.seek(0)
    file.save(str(filepath))

    relative = filepath.relative_to(Path(current_app.static_folder))
    return {
        'storage_path': relative.as_posix(),
        'public_url': f"/static/{relative.as_posix()}",
        'file_name': unique_name,
        'original_name': file.filename,
        'mime_type': file.mimetype,
        'file_size': size,
    }


def delete_media_file(storage_path: str) -> bool:
    """Remove a previously stored media asset file."""
    if not storage_path:
        return False

    static_root = Path(current_app.static_folder)
    target = static_root / storage_path
    _ensure_within_static_root(target)

    if target.exists() and target.is_file():
        target.unlink()
        _cleanup_empty_dirs(target.parent)
        return True
    return False


def _cleanup_empty_dirs(path: Path) -> None:
    """Remove empty directories up to the static uploads root."""
    static_root = _static_upload_root().resolve()
    current = path.resolve()
    while current != static_root and static_root in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


__all__ = ['save_upload', 'delete_upload', 'allowed_file', 'store_media_file', 'delete_media_file']
