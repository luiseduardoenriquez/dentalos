"""Service catalog model — lives in each tenant schema.

One table:
  - ServiceCatalog: clinic's own CUPS-based service price list.

cups_code is immutable after creation (enforced in the service layer,
not at the DB level, to avoid costly column constraints on UPDATE).
All monetary values are stored in cents (COP).
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ServiceCatalog(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Per-tenant CUPS service entry with a custom price.

    Each clinic maintains its own price list, keyed by CUPS code.
    Prices are stored in COP cents (integer) — never floats.
    Inactive entries (is_active=False) are hidden from clinical workflows
    but retained for historical billing references.
    """

    __tablename__ = "service_catalog"
    __table_args__ = (
        UniqueConstraint("cups_code", name="uq_service_catalog_cups_code"),
        CheckConstraint(
            "category IN ("
            "'diagnostic','preventive','restorative','endodontic',"
            "'periodontic','surgical','orthodontic','prosthodontic','other'"
            ")",
            name="chk_service_catalog_category",
        ),
        Index("idx_service_catalog_category", "category"),
        Index("idx_service_catalog_cups_code", "cups_code"),
    )

    # CUPS code — immutable after creation (enforced in service layer)
    cups_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # Description
    name: Mapped[str] = mapped_column(String(300), nullable=False)

    # Pricing — always cents (COP)
    default_price: Mapped[int] = mapped_column(Integer, nullable=False)

    # Classification
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<ServiceCatalog cups={self.cups_code} "
            f"name={self.name!r} price={self.default_price}>"
        )
