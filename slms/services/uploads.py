"""File upload service for handling user uploads."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'slms/static/uploads'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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

    # Create upload directory if it doesn't exist
    upload_path = Path(UPLOAD_FOLDER) / subfolder
    upload_path.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = upload_path / filename

    # Save the file
    try:
        file.save(str(filepath))
        # Return URL path (relative to static folder)
        return f"/static/uploads/{subfolder}/{filename}"
    except Exception as e:
        print(f"Error saving file: {e}")
        return None


def delete_upload(file_url: str) -> bool:
    """
    Delete an uploaded file given its URL path.

    Args:
        file_url: The URL path of the file (e.g., '/static/uploads/team_logos/abc123.jpg')

    Returns:
        True if deletion was successful, False otherwise
    """
    if not file_url:
        return False

    try:
        # Convert URL to filesystem path
        if file_url.startswith('/static/'):
            file_path = Path('slms') / file_url[1:]  # Remove leading '/'
        else:
            return False

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
    except Exception as e:
        print(f"Error deleting file: {e}")

    return False


__all__ = ['save_upload', 'delete_upload', 'allowed_file']
