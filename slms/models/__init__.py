"""Application data models for SLMS."""

from slms.models.models import *  # noqa: F401,F403

__all__ = [name for name in globals() if name[0].isupper()]
