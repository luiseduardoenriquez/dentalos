"""Email delivery service — INT-03.

Loads HTML templates from backend/templates/, renders {{variable}} placeholders,
and sends via SendGrid SDK. In dev mode (no API key), logs the email and returns True.
"""
import html
import logging
from pathlib import Path

logger = logging.getLogger("dentalos.email")

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _mask_email(email: str) -> str:
    """Mask an email address for safe logging — e.g. j***@example.com.

    Returns the original value unchanged if it does not contain '@',
    and an empty string if the input is empty.
    """
    if not email:
        return ""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


class EmailService:
    """Stateless email service with template rendering and SendGrid dispatch."""

    def __init__(self) -> None:
        self._template_cache: dict[str, str] = {}

    def _load_template(self, template_name: str) -> str:
        """Load and cache an HTML template from disk."""
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        path = _TEMPLATE_DIR / template_name
        if not path.exists():
            raise FileNotFoundError(f"Email template not found: {template_name}")

        content = path.read_text(encoding="utf-8")
        self._template_cache[template_name] = content
        return content

    def _render(self, template: str, context: dict[str, str]) -> str:
        """Render {{key}} placeholders in template with context values.

        All values are HTML-escaped before substitution to prevent XSS.
        """
        rendered = template
        for key, value in context.items():
            safe_value = html.escape(str(value))
            rendered = rendered.replace("{{ " + key + " }}", safe_value)
            rendered = rendered.replace("{{" + key + "}}", safe_value)
        return rendered

    async def send_email(
        self,
        *,
        to_email: str,
        to_name: str,
        subject: str,
        template_name: str,
        context: dict[str, str],
    ) -> bool:
        """Send an email using a template.

        In dev mode (no SendGrid API key), logs the email and returns True.
        """
        from app.core.config import settings

        # Load and render template
        template = self._load_template(template_name)
        html_content = self._render(template, context)

        # Dev mode — no SendGrid key
        if not settings.sendgrid_api_key:
            logger.info(
                "Email (dev mode): to=%s subject='%s' template=%s",
                _mask_email(to_email),
                subject,
                template_name,
            )
            return True

        # Production — send via SendGrid
        try:
            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
            from_email = Email(settings.email_from_address, settings.email_from_name)
            to_email_obj = To(to_email, to_name)
            content = Content("text/html", html_content)
            mail = Mail(from_email, to_email_obj, subject, content)

            response = sg.client.mail.send.post(request_body=mail.get())

            if response.status_code in (200, 201, 202):
                logger.info("Email sent: to=%s subject='%s'", _mask_email(to_email), subject)
                return True
            else:
                logger.error(
                    "Email send failed: status=%d to=%s",
                    response.status_code,
                    _mask_email(to_email),
                )
                return False
        except Exception:
            logger.exception("Email send error: to=%s subject='%s'", _mask_email(to_email), subject)
            return False


# Module-level singleton
email_service = EmailService()
