"""
Legal Search API Router
=======================

FastAPI router for searching legal verdicts in MAHOUN.

Endpoints:
- POST /v1/search/verdicts - Search for relevant verdicts

Usage:
    POST /v1/search/verdicts
    {
        "query": "اعتراض ثالث اجرایی نسبت به توقیف عملیات",
        "filters": {
            "court_level": "دادگاه تجدیدنظر استان",
            "is_final": true
        },
        "limit": 10
    }
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============================================================================
# Request/Response Models
# ============================================================================


class SearchFilters(BaseModel):
    """
    Filters for verdict search.

    All fields are optional and can be combined.
    """

    court_level: Optional[str] = Field(
        default=None,
        description="Court level, e.g., 'دادگاه تجدیدنظر استان'",
        json_schema_extra={"example": "دادگاه تجدیدنظر استان"},
    )
    case_type: Optional[str] = Field(
        default=None,
        description="Type of case, e.g., 'اعتراض ثالث اجرایی / رفع توقیف'",
        json_schema_extra={"example": "اعتراض ثالث اجرایی / رفع توقیف"},
    )
    is_final: Optional[bool] = Field(
        default=None, description="Whether the verdict is final (قطعی)"
    )
    article_no: Optional[str] = Field(
        default=None,
        description="Law article number to filter by",
        json_schema_extra={"example": "348"},
    )
    law_name: Optional[str] = Field(
        default=None,
        description="Name of law to filter by",
        json_schema_extra={"example": "قانون آیین دادرسی مدنی"},
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags to filter by",
        json_schema_extra={"example": ["اعتراض ثالث اجرایی", "رفع توقیف"]},
    )


class VerdictSearchRequest(BaseModel):
    """Request body for verdict search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language search query (Persian or English)",
        json_schema_extra={
            "example": "اعتراض ثالث اجرایی نسبت به توقیف عملیات اجرای احکام"
        },
    )
    filters: Optional[SearchFilters] = Field(
        default=None, description="Optional filters to narrow results"
    )
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results to return"
    )
    enrich_with_graph: bool = Field(
        default=True,
        description="Whether to enrich results with graph data (law articles, tags)",
    )


class VerdictHit(BaseModel):
    """A single verdict search result."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "verdict_id": "verdict_001",
                "score": 0.85,
                "section": "appeal_reasoning",
                "chunk_text": "دادگاه تجدیدنظر با توجه به مستندات ارائه شده و اعتراض ثالث...",
                "case_type": "اعتراض ثالث اجرایی / رفع توقیف",
                "court_level": "دادگاه تجدیدنظر استان",
                "procedure_stage": "تجدیدنظر",
                "is_final": True,
                "tags": ["اعتراض ثالث اجرایی", "رفع توقیف", "تأیید رأی بدوی"],
                "law_articles": [
                    "ماده 146 قانون اجرای احکام مدنی",
                    "ماده 348 قانون آیین دادرسی مدنی",
                ],
            }
        }
    }

    verdict_id: str = Field(..., description="Unique identifier of the verdict")
    score: float = Field(..., description="Relevance score (0-1, higher is better)")
    section: str = Field(..., description="Section of the verdict")
    chunk_text: str = Field(..., description="Relevant text snippet")

    case_type: Optional[str] = Field(default=None, description="Type of case")
    court_level: Optional[str] = Field(default=None, description="Court level")
    procedure_stage: Optional[str] = Field(default=None, description="Procedure stage")
    is_final: Optional[bool] = Field(default=None, description="Whether final verdict")

    tags: List[str] = Field(default_factory=list, description="Associated tags")
    law_articles: List[str] = Field(
        default_factory=list, description="Referenced law articles"
    )

    extra_metadata: dict = Field(
        default_factory=dict, description="Additional metadata"
    )


class VerdictSearchResponse(BaseModel):
    """Response for verdict search."""

    results: List[VerdictHit] = Field(
        default_factory=list, description="List of search results"
    )
    total: int = Field(default=0, description="Total number of results returned")
    query: str = Field(..., description="Original search query")
    filters_applied: Optional[dict] = Field(
        default=None, description="Filters that were applied"
    )


# ============================================================================
# Router
# ============================================================================

router = APIRouter(
    prefix="/v1/search",
    tags=["search"],
    responses={500: {"description": "Internal server error"}},
)


# Singleton service instance
_search_service = None


def get_search_service():
    """
    Dependency injection for LegalSearchService.

    Uses a singleton pattern for efficiency.
    """
    global _search_service

    if _search_service is None:
        try:
            from services.search.legal_search_service import LegalSearchService

            _search_service = LegalSearchService()
            logger.info("LegalSearchService initialized")
        except ImportError as e:
            logger.error(f"Failed to import LegalSearchService: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search service unavailable",
            )

    return _search_service


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/verdicts",
    response_model=VerdictSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search legal verdicts",
    description="""
    Search for legal verdicts using natural language queries.
    
    This endpoint performs semantic search over indexed verdict chunks,
    with optional filtering and graph-based enrichment.
    
    **Features:**
    - Semantic search in Persian and English
    - Filtering by court level, case type, finality status
    - Filtering by law article or tags
    - Automatic enrichment with graph data (law articles, tags)
    
    **Example query:** "اعتراض ثالث اجرایی نسبت به توقیف عملیات اجرای احکام"
    """,
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "verdict_id": "verdict_001",
                                "score": 0.85,
                                "section": "appeal_reasoning",
                                "chunk_text": "دادگاه تجدیدنظر...",
                                "case_type": "اعتراض ثالث اجرایی / رفع توقیف",
                                "court_level": "دادگاه تجدیدنظر استان",
                                "is_final": True,
                                "tags": ["اعتراض ثالث اجرایی"],
                                "law_articles": ["ماده 348 قانون آیین دادرسی مدنی"],
                            }
                        ],
                        "total": 1,
                        "query": "اعتراض ثالث اجرایی",
                    }
                }
            },
        }
    },
)
async def search_verdicts(
    payload: VerdictSearchRequest, service=Depends(get_search_service)
):
    """
    Search for legal verdicts matching a natural language query.

    Args:
        payload: Search request with query, filters, and limit
        service: Injected LegalSearchService instance

    Returns:
        VerdictSearchResponse with matching verdicts
    """
    logger.info(
        f"Search request: query='{payload.query[:50]}...', limit={payload.limit}"
    )

    try:
        # Convert request filters to service filters
        from services.search.legal_search_service import LegalSearchFilters

        service_filters: Optional[Any] = None
        if payload.filters:
            service_filters = LegalSearchFilters(
                court_level=payload.filters.court_level,
                case_type=payload.filters.case_type,
                is_final=payload.filters.is_final,
                article_no=payload.filters.article_no,
                law_name=payload.filters.law_name,
                tags=payload.filters.tags,
            )

        # Execute search
        results = await service.search_verdicts(
            query=payload.query,
            filters=service_filters,
            limit=payload.limit,
            enrich_with_graph=payload.enrich_with_graph,
        )

        # Convert results to response model
        hits = [
            VerdictHit(
                verdict_id=r.verdict_id,
                score=r.score,
                section=r.section,
                chunk_text=r.chunk_text,
                case_type=r.case_type,
                court_level=r.court_level,
                procedure_stage=r.procedure_stage,
                is_final=r.is_final,
                tags=r.tags,
                law_articles=r.law_articles,
                extra_metadata=r.extra_metadata,
            )
            for r in results
        ]

        # Build filters_applied dict for response
        filters_applied: Optional[Any] = None
        if payload.filters:
            filters_applied = payload.filters.model_dump(exclude_none=True)

        return VerdictSearchResponse(
            results=hits,
            total=len(hits),
            query=payload.query,
            filters_applied=filters_applied,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)

        # Safely extract query text - guard against corrupted payload
        try:
            query_text = payload.query if payload else ""
        except Exception:
            query_text = ""

        # Safely extract filters - guard against Pydantic serialization errors
        try:
            filters_applied = (
                payload.filters.model_dump(exclude_none=True)
                if payload and payload.filters is not None
                else None
            )
        except Exception:
            # If filters are corrupted or Pydantic raises an error,
            # fall back to None to ensure error handler never crashes
            filters_applied: Optional[Any] = None
        # Return empty results instead of raising to ensure graceful degradation
        return VerdictSearchResponse(
            results=[], total=0, query=query_text, filters_applied=filters_applied
        )


@router.get(
    "/health",
    summary="Search service health check",
    description="Check if the search service is operational",
)
async def search_health():
    """
    Health check for the search service.

    Returns status of VectorStore and Graph backends.
    """
    health_status = {
        "status": "healthy",
        "service": "legal_search",
        "backends": {"vector_store": "unknown", "graph": "unknown"},
    }

    try:
        service = get_search_service()

        # Check VectorStore
        try:
            vs_manager = await service._get_vector_manager()
            health_status["backends"]["vector_store"] = (
                "available" if vs_manager else "unavailable"
            )
        except Exception as e:
            logger.debug(f"VectorStore health check failed: {e}")
            health_status["backends"]["vector_store"] = "unavailable"

        # Check Graph
        try:
            graph_ops = service._get_graph_ops()
            health_status["backends"]["graph"] = (
                "available" if graph_ops else "unavailable"
            )
        except Exception as e:
            logger.debug(f"Graph health check failed: {e}")
            health_status["backends"]["graph"] = "unavailable"

        # Determine overall status
        if health_status["backends"]["vector_store"] == "unavailable":
            health_status["status"] = "degraded"
            health_status["message"] = (
                "VectorStore not available; search will return empty results"
            )

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

    return health_status
