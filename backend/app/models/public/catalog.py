"""Public catalog models — shared across all tenants (public schema).

Two tables:
  - CIE10Catalog:  ICD-10 diagnosis codes (Spanish edition)
  - CUPSCatalog:   Colombian CUPS procedure codes

Both catalogs are read-only for tenants and are populated via seeder scripts.
Full-text search is supported through PostgreSQL GIN indexes on tsvector columns.
"""

from sqlalchemy import Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import PublicBase, TimestampMixin, UUIDPrimaryKeyMixin


class CIE10Catalog(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    """ICD-10 (CIE-10 in Spanish) diagnosis code catalog.

    Shared platform-wide — one row per ICD-10 leaf code.
    GIN index on tsvector enables fast Spanish full-text search
    without loading all rows for substring matching.
    """

    __tablename__ = "cie10_catalog"
    __table_args__ = (
        Index(
            "idx_cie10_catalog_description_fts",
            func.to_tsvector("spanish", Text("description")),
            postgresql_using="gin",
        ),
        Index("idx_cie10_catalog_code", "code"),
        Index("idx_cie10_catalog_category", "category"),
    )

    # Code — e.g. "K02.1" (unique, immutable)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    # Spanish description
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Grouping category (e.g. "K00-K14 Enfermedades de la cavidad bucal")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<CIE10Catalog {self.code}: {self.description[:40]}>"


class CUPSCatalog(UUIDPrimaryKeyMixin, TimestampMixin, PublicBase):
    """Colombian CUPS (health procedure) code catalog.

    Shared platform-wide — one row per CUPS code.
    GIN index on tsvector enables fast Spanish full-text search.
    """

    __tablename__ = "cups_catalog"
    __table_args__ = (
        Index(
            "idx_cups_catalog_description_fts",
            func.to_tsvector("spanish", Text("description")),
            postgresql_using="gin",
        ),
        Index("idx_cups_catalog_code", "code"),
        Index("idx_cups_catalog_category", "category"),
    )

    # Code — e.g. "890202" (6-digit numeric string, unique, immutable)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    # Spanish description
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Grouping category (e.g. "Odontología general")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<CUPSCatalog {self.code}: {self.description[:40]}>"
