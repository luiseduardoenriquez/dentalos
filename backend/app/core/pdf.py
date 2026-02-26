"""PDF generation utility using Playwright + Jinja2 for DentalOS.

Renders HTML templates with context data and converts to PDF bytes.
All PDF templates live in backend/templates/ directory.

A headless Chromium browser is lazily initialized on the first call to
``render_pdf`` and reused for all subsequent renders.  Call
``shutdown_pdf_engine`` during application shutdown to close the browser
and Playwright context cleanly.

Security invariants:
  - Template context is sanitized -- no raw HTML injection.
  - Generated PDFs are not cached (contain PHI).
  - The browser runs headless with no network access needed.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import Browser, Playwright, async_playwright

logger = logging.getLogger("dentalos.pdf")

# Template directory
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# Module-level browser state (lazy-initialized)
_playwright: Playwright | None = None
_browser: Browser | None = None

# PDF page settings
_PDF_FORMAT = "A4"
_PDF_MARGIN = {
    "top": "15mm",
    "right": "15mm",
    "bottom": "15mm",
    "left": "15mm",
}


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment with autoescaping enabled."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


async def _get_browser() -> Browser:
    """Return the shared Chromium browser, launching it on first call."""
    global _playwright, _browser  # noqa: PLW0603

    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        logger.info("Playwright Chromium browser launched")

    return _browser


async def render_pdf(
    *,
    template_name: str,
    context: dict,
    watermark: str | None = None,
) -> bytes:
    """Render an HTML template to PDF bytes.

    A new browser page is created for each render call and closed
    immediately after the PDF is generated.

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

    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes: bytes = await page.pdf(
            format=_PDF_FORMAT,
            margin=_PDF_MARGIN,
            print_background=True,
        )
    finally:
        await page.close()

    logger.info("PDF rendered: template=%s size=%d bytes", template_name, len(pdf_bytes))

    return pdf_bytes


async def shutdown_pdf_engine() -> None:
    """Close the shared browser and Playwright context.

    Call this during application shutdown to release resources cleanly.
    Safe to call multiple times or when the engine was never initialized.
    """
    global _playwright, _browser  # noqa: PLW0603

    if _browser is not None:
        await _browser.close()
        _browser = None
        logger.info("Playwright browser closed")

    if _playwright is not None:
        await _playwright.stop()
        _playwright = None
        logger.info("Playwright stopped")
