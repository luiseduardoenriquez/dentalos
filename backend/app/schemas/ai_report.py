"""Pydantic schemas for GAP-14 Natural Language Analytics Reports.

Request and response models for the AI-powered analytics query endpoint.
The endpoint translates natural language questions into pre-validated
SQLAlchemy ORM queries and returns structured data with chart hints.
"""

from pydantic import BaseModel, Field


class AIQueryRequest(BaseModel):
    """Natural language analytics question from a clinic user."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Pregunta en lenguaje natural sobre la clinica.",
        examples=["Cuantos pacientes vinieron este mes?"],
    )


class AIQueryResponse(BaseModel):
    """Structured analytics response with data and chart recommendation."""

    answer: str = Field(
        ...,
        description="Explicacion en espanol de los resultados.",
    )
    data: list[dict] = Field(
        default_factory=list,
        description="Resultado de la consulta como lista de diccionarios.",
    )
    chart_type: str = Field(
        ...,
        description="Tipo de grafico recomendado: bar, line, pie, table, number.",
    )
    query_key: str = Field(
        ...,
        description="Clave de la consulta ejecutada del registro de plantillas.",
    )
