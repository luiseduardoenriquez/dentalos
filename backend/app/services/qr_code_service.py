"""QR code generation utility.

Generates QR code images as base64-encoded PNGs for payment collection flows.
Falls back to a 1x1 transparent PNG placeholder if the qrcode library is not
installed (CI environments, minimal containers, etc.).
"""

import base64
import io
import logging

logger = logging.getLogger("dentalos.qr_code")


class QRCodeService:
    """Generates QR code images as base64-encoded PNGs."""

    def generate_base64(self, *, data: str, size: int = 256) -> str:
        """Generate a QR code image and return as base64 string.

        Uses the ``qrcode`` library with Pillow backend. Falls back to a
        1x1 transparent PNG placeholder if the library is not installed.

        Args:
            data: The string content to encode in the QR code.
            size: Ignored in current implementation (box_size controls output).

        Returns:
            Base64-encoded PNG string (no data URI prefix).
        """
        try:
            import qrcode  # type: ignore[import-untyped]

            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except ImportError:
            logger.warning("qrcode library not installed, returning placeholder")
            # 1x1 transparent PNG as placeholder
            return base64.b64encode(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            ).decode("utf-8")


# Module-level singleton
qr_code_service = QRCodeService()
