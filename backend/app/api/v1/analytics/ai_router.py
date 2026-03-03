"""GAP-14: Natural Language Analytics Reports API router.

Single endpoint that accepts a natural language question and returns
structured analytics data with chart hints. Claude selects from
pre-validated query templates — no raw SQL, no PHI exposure.

Endpoint:
    POST /analytics/ai-query   — analytics:read (doctor, clinic_owner)
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_permission
from app.core.database import get_tenant_db
from app.schemas.ai_report import AIQueryRequest, AIQueryResponse
from app.services.ai_report_service import process_ai_query

logger = logging.getLogger("dentalos.analytics.ai")

router = APIRouter(prefix="/analytics", tags=["ai-reports"])


@router.post(
    "/ai-query",
    response_model=AIQueryResponse,
    status_code=200,
    summary="Consulta de analitica en lenguaje natural",
    description=(
        "Recibe una pregunta en espanol sobre la clinica y retorna "
        "datos analiticos estructurados con tipo de grafico recomendado."
    ),
)
async def ai_query(
    body: AIQueryRequest,
    current_user: AuthenticatedUser = Depends(require_permission("analytics:read")),
    db: AsyncSession = Depends(get_tenant_db),
) -> AIQueryResponse:
    """Process a natural language analytics question.

    The question is interpreted by Claude which selects a pre-validated
    query template. The server executes the corresponding SQLAlchemy
    ORM query and returns aggregated results. No raw SQL is generated
    and no PHI is included in the response.
    """
    result = await process_ai_query(db=db, question=body.question)

    return AIQueryResponse(
        answer=result["answer"],
        data=result["data"],
        chart_type=result["chart_type"],
        query_key=result["query_key"],
    )
