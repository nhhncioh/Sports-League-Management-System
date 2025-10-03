"""Multi-Factor Authentication service."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slms.models import User


def generate_qr_code(user: User, org_name: str | None = None) -> bytes:
    """Generate QR code for MFA setup."""
    import qrcode
    from qrcode.image.pure import PyPNGImage

    uri = user.get_mfa_uri(org_name)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white", image_factory=PyPNGImage)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf.getvalue()


__all__ = ["generate_qr_code"]
