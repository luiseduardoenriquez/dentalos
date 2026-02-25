"""PDF generation utility using WeasyPrint + Jinja2 for DentalOS.

Renders HTML templates with context data and converts to PDF bytes.
All PDF templates live in backend/templates/ directory.

Security invariants:
  - Template context is sanitized — no raw HTML injection.
  - Generated PDFs are not cached (contain PHI).
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

logger = logging.getLogger("dentalos.pdf")

# Template directory
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment with autoescaping enabled."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def render_pdf(
    *,
    template_name: str,
    context: dict,
    watermark: str | None = None,
) -> bytes:
    """Render an HTML template to PDF bytes.

    Args:
        template_name: Filename of the Jinja2 template (e.g., "treatment_plan_es.html").
        context: Template context dict.
        watermark: Optional watermark text overlay (e.g., "BORRADOR", "ANULADO").

    Returns:
        PDF content as bytes.
    """
    env = _get_jinja_env()
    template = env.get_template(template_name)

    # Inject watermark into context if provided
    if watermark:
        context = {**context, "_watermark": watermark}

    html_content = template.render(**context)

    pdf_bytes = HTML(string=html_content).write_pdf()

    logger.info("PDF rendered: template=%s size=%d bytes", template_name, len(pdf_bytes))

    return pdf_bytes
