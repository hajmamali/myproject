"""
MAHOUN API Router
==================

Endpoints اصلی برای MAHOUN:
- Document Management
- Analysis (Delay, Dispute, Timeline)
- Report Generation
- Contract Q&A
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/mahoun",
    tags=["mahoun"],
    responses={500: {"description": "Internal server error"}},
)


# ============================================================================
# Request/Response Models
# ============================================================================


class DocumentUploadRequest(BaseModel):
    """Request for document upload"""

    doc_type: str = Field(
        ..., description="Document type: contract, letter, report, general_conditions"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    index: bool = Field(True, description="Index document after upload")


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""

    success: bool
    document_id: str
    doc_type: str
    normalized: Dict[str, Any]
    indexed: bool
    processing_time_ms: float


class DelayAnalysisRequest(BaseModel):
    """Request for delay analysis"""

    project_id: str = Field(..., description="Project identifier")
    query: Optional[str] = Field(None, description="Analysis query")
    baseline_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Baseline schedule"
    )
    actual_schedule: Optional[Dict[str, Any]] = Field(
        None, description="Actual schedule"
    )


class DelayAnalysisResponse(BaseModel):
    """Response for delay analysis"""

    success: bool
    project_id: str
    delays: List[Dict[str, Any]]
    delay_analysis: Dict[str, Any]
    critical_path: List[Dict[str, Any]]
    attribution: Dict[str, Any]
    processing_time_ms: float


class ClaimGenerationRequest(BaseModel):
    """Request for claim generation"""

    claim_type: str = Field(..., description="Type of claim")
    facts: str = Field(..., description="Facts and information")
    legal_basis: Optional[str] = Field(None, description="Legal basis")
    parties: Optional[Dict[str, str]] = Field(None, description="Parties information")


class ClaimGenerationResponse(BaseModel):
    """Response for claim generation"""

    success: bool
    claim_id: str
    claim_content: str
    markdown: str
    citations: List[Dict[str, Any]]
    processing_time_ms: float


class ContractQueryRequest(BaseModel):
    """Request for contract query"""

    query: str = Field(..., description="Question about contract")
    clause_number: Optional[str] = Field(None, description="Specific clause number")
    contract_id: Optional[str] = Field(None, description="Contract identifier")
    top_k: int = Field(10, description="Number of results", ge=1, le=20)


class ContractQueryResponse(BaseModel):
    """Response for contract query"""

    success: bool
    answer: str
    confidence: float
    verified: bool
    citations: List[Dict[str, Any]]
    clauses: List[Dict[str, Any]]
    processing_time_ms: float


class ReportResponse(BaseModel):
    """Response for report"""

    success: bool
    report_id: str
    report_type: str
    content: str
    markdown: str
    download_url: Optional[str] = None
    processing_time_ms: float


# ============================================================================
# Dependencies
# ============================================================================

_orchestrator: Optional[Any] = None
_report_storage = {}


def get_orchestrator():
    """Get UltraOrchestrator instance"""
    global _orchestrator

    if _orchestrator is None:
        from mahoun.agents.orchestrator import UltraOrchestrator
        from mahoun.agents import (
            UltraDocParserAgent,
            DisputeAgent,
            UltraClaimAgent,
            TimelineAgent,
            DelayAgent,
            NarrativeAgent,
            UltraContractAgent,
        )

        _orchestrator = UltraOrchestrator()

        # Register all agents
        # We must provide names to register_agent(name, agent)
        _orchestrator.register_agent("doc_parser_agent", UltraDocParserAgent())
        _orchestrator.register_agent("dispute_agent", DisputeAgent())
        _orchestrator.register_agent("claim_agent", UltraClaimAgent())
        _orchestrator.register_agent("timeline_agent", TimelineAgent())
        _orchestrator.register_agent("delay_agent", DelayAgent())
        _orchestrator.register_agent("narrative_agent", NarrativeAgent())
        _orchestrator.register_agent("contract_agent", UltraContractAgent())

        logger.info("UltraOrchestrator initialized with all agents")

    return _orchestrator


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/upload-documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and process documents",
    description="Upload documents (PDF, DOCX, TXT, Images) and normalize them",
)
async def upload_documents(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    index: bool = True,
):
    """
    Upload and process documents

    Supports: PDF, DOCX, TXT, Images (with OCR)
    """
    import time

    start_time = time.time()

    try:
        # Save uploaded file
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Use DocParserAgent
        orchestrator = get_orchestrator()
        doc_parser = orchestrator.agents.get("doc_parser_agent")

        if not doc_parser:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DocParserAgent not available",
            )

        # Initialize if needed
        if not doc_parser._initialized:
            await doc_parser.initialize()

        # Process document
        result = await doc_parser.process(
            {
                "file_path": str(file_path),
                "doc_type": doc_type or "document",
                "metadata": metadata or {},
                "index": index,
            }
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Document processing failed"),
            )

        processing_time_ms = (time.time() - start_time) * 1000

        return DocumentUploadResponse(
            success=True,
            document_id=result.get("document_id"),
            doc_type=result.get("normalized", {}).get("type", "document"),
            normalized=result.get("normalized", {}),
            indexed=result.get("indexed", False),
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}",
        )


@router.post(
    "/analyze-delay",
    response_model=DelayAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze project delays",
    description="Analyze delays in a project with baseline vs actual comparison",
)
async def analyze_delay(request: DelayAnalysisRequest):
    """Analyze project delays"""
    import time

    start_time = time.time()

    try:
        from mahoun.domain.delay_analyzer import DelayAnalysisEngine

        engine = DelayAnalysisEngine()
        await engine.initialize()

        result = await engine.analyze(
            {
                "project_id": request.project_id,
                "query": request.query,
                "baseline_schedule": request.baseline_schedule,
                "actual_schedule": request.actual_schedule,
            }
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Delay analysis failed"),
            )

        processing_time_ms = (time.time() - start_time) * 1000

        return DelayAnalysisResponse(
            success=True,
            project_id=request.project_id,
            delays=result.get("delays", []),
            delay_analysis=result.get("delay_analysis", {}),
            critical_path=result.get("critical_path", []),
            attribution=result.get("attribution", {}),
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Delay analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delay analysis failed: {str(e)}",
        )


@router.post(
    "/generate-claim",
    response_model=ClaimGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate claim draft",
    description="Generate formal claim document",
)
async def generate_claim(request: ClaimGenerationRequest):
    """Generate claim draft"""
    import time

    start_time = time.time()

    try:
        from output.claim_generator import ClaimDraftGenerator

        generator = ClaimDraftGenerator()
        await generator.initialize()

        result = await generator.generate(
            {
                "claim_type": request.claim_type,
                "facts": request.facts,
                "legal_basis": request.legal_basis,
                "parties": request.parties,
            }
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Claim generation failed"),
            )

        claim_id = str(uuid.uuid4())
        processing_time_ms = (time.time() - start_time) * 1000

        return ClaimGenerationResponse(
            success=True,
            claim_id=claim_id,
            claim_content=result.get("content", ""),
            markdown=result.get("markdown", ""),
            citations=result.get("citations", []),
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Claim generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claim generation failed: {str(e)}",
        )


@router.post(
    "/ask-contract",
    response_model=ContractQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask contract question",
    description="Ask questions about contracts and get answers with citations",
)
async def ask_contract(request: ContractQueryRequest):
    """Ask contract question"""
    import time

    start_time = time.time()

    try:
        orchestrator = get_orchestrator()
        contract_agent = orchestrator.agents.get("contract_agent")

        if not contract_agent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ContractAgent not available",
            )

        # Initialize if needed
        if not contract_agent._initialized:
            await contract_agent.initialize()

        # Process query
        result = await contract_agent.process(
            {"query": request.query, "top_k": request.top_k}
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Contract query failed"),
            )

        processing_time_ms = (time.time() - start_time) * 1000

        return ContractQueryResponse(
            success=True,
            answer=result.get("answer", ""),
            confidence=result.get("confidence", 0.0),
            verified=result.get("verified", False),
            citations=result.get("citations", []),
            clauses=[c for c in result.get("citations", []) if c.get("clause")],
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Contract query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contract query failed: {str(e)}",
        )


@router.post(
    "/generate-delay-report",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate delay report",
    description="Generate comprehensive delay analysis report",
)
async def generate_delay_report(request: DelayAnalysisRequest):
    """Generate delay report"""
    import time

    start_time = time.time()

    try:
        from output.delay_report import DelayReportGenerator

        generator = DelayReportGenerator()
        await generator.initialize()

        result = await generator.generate(
            {
                "project_id": request.project_id,
                "query": request.query,
                "baseline_schedule": request.baseline_schedule,
                "actual_schedule": request.actual_schedule,
            }
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Report generation failed"),
            )

        report_id = str(uuid.uuid4())
        processing_time_ms = (time.time() - start_time) * 1000

        # Store report
        _report_storage[report_id] = result

        return ReportResponse(
            success=True,
            report_id=report_id,
            report_type="delay",
            content=result.get("content", ""),
            markdown=result.get("markdown", ""),
            download_url=f"/api/v1/mahoun/reports/{report_id}",
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Delay report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.post(
    "/generate-timeline-report",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate timeline report",
    description="Generate timeline analysis report",
)
async def generate_timeline_report(
    query: Optional[str] = None,
    documents: Optional[List[str]] = None,
    date_range: Optional[Dict[str, Any]] = None,
):
    """Generate timeline report"""
    import time

    start_time = time.time()

    try:
        from output.timeline_report import TimelineReportGenerator

        generator = TimelineReportGenerator()
        await generator.initialize()

        result = await generator.generate(
            {
                "query": query or "timeline",
                "documents": documents or [],
                "date_range": date_range,
            }
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Report generation failed"),
            )

        report_id = str(uuid.uuid4())
        processing_time_ms = (time.time() - start_time) * 1000

        # Store report
        _report_storage[report_id] = result

        return ReportResponse(
            success=True,
            report_id=report_id,
            report_type="timeline",
            content=result.get("content", ""),
            markdown=result.get("markdown", ""),
            download_url=f"/api/v1/mahoun/reports/{report_id}",
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Timeline report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get(
    "/reports/{report_id}",
    summary="Get report",
    description="Get generated report by ID",
)
async def get_report(report_id: str, format: str = "json"):
    """Get report by ID"""
    if report_id not in _report_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    report = _report_storage[report_id]

    if format == "json":
        return report
    elif format == "markdown":
        return {"markdown": report.get("markdown", "")}
    elif format == "text":
        return {"content": report.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}",
        )


@router.get(
    "/reports", summary="List reports", description="List all generated reports"
)
async def list_reports():
    """List all reports"""
    return {
        "reports": [
            {
                "report_id": report_id,
                "report_type": report.get("metadata", {}).get("report_type", "unknown"),
                "generated_at": report.get("metadata", {}).get("generated_at"),
            }
            for report_id, report in _report_storage.items()
        ],
        "total": len(_report_storage),
    }
