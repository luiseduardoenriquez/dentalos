"""Reminder config model — lives in each tenant schema.

One table:
  - ReminderConfig: one row per tenant that controls how and when appointment
    reminders are dispatched. Not clinical data — no soft delete required.

The reminders field is a JSONB array of rule objects:
    [
        {"hours_before": 48, "channels": ["email"]},
        {"hours_before": 24, "channels": ["sms", "whatsapp"]},
        {"hours_before": 2,  "channels": ["sms"]}
    ]

default_channels is a JSONB array of channel strings applied when a patient
has no explicit channel preference: e.g. ["sms"].

max_reminders_allowed caps how many rule entries are accepted (plan-dependent).
"""

from sqlalchemy import Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ReminderConfig(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Tenant-level configuration for appointment reminder dispatch.

    One row is created per tenant during onboarding. The notification worker
    reads this row to build its dispatch schedule before each reminder job.

    Not clinical data — no soft delete, no is_active flag.
    """

    __tablename__ = "reminder_configs"

    # Reminder rules — ordered array of {hours_before, channels}
    reminders: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        default=list,
    )

    # Fallback channels when patient has no preference
    default_channels: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text('\'["sms"]\'::jsonb'),
        default=lambda: ["sms"],
    )

    # Plan-enforced cap on the number of reminder rules
    max_reminders_allowed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    def __repr__(self) -> str:
        return (
            f"<ReminderConfig max_reminders={self.max_reminders_allowed} "
            f"channels={self.default_channels}>"
        )
