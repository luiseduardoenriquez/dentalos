"""Medical code catalog request/response schemas (CIE-10, CUPS)."""
from pydantic import BaseModel


# ─── CIE-10 Schemas ───────────────────────────────────────────────────────────


class CIE10SearchResult(BaseModel):
    """Single CIE-10 diagnostic code result."""

    code: str
    description: str
    category: str | None = None


class CIE10SearchResponse(BaseModel):
    """Response envelope for CIE-10 search results."""

    items: list[CIE10SearchResult]
    count: int


# ─── CUPS Schemas ─────────────────────────────────────────────────────────────


class CUPSSearchResult(BaseModel):
    """Single CUPS procedure code result."""

    code: str
    description: str
    category: str | None = None


class CUPSSearchResponse(BaseModel):
    """Response envelope for CUPS search results."""

    items: list[CUPSSearchResult]
    count: int
