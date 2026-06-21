"""
Training Datasets API Router
============================
REST API endpoints for document-to-training dataset conversion.

This router provides the MISSING LINK between document upload and training:
    POST /api/v1/training-datasets/from-document → Upload document → Generate dataset
    GET  /api/v1/training-datasets/{dataset_id} → Get dataset info
    GET  /api/v1/training-datasets → List all datasets
    POST /api/v1/training-datasets/batch → Batch process multiple documents

Endpoints:
- Document upload with automatic Q&A generation
- Quality filtering and groundedness verification
- Dataset creation with train/eval/test splits
- Batch processing support
- Progress tracking and metrics
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks, Query, Path as PathParam
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from mahoun.finetuning.document_to_training import (
    DocumentToTrainingPipeline,
    DocumentToTrainingConfig,
    ProcessingResult,
    QAGenerationStrategy,
    DomainType,
)
from mahoun.core.validation import SafeString, StringSanitizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/training-datasets", tags=["training-datasets"])

# Global pipeline instance (initialized on first use)
_pipeline: Optional[DocumentToTrainingPipeline] = None
_pipeline_lock = asyncio.Lock()

# Job tracking
_jobs: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class DatasetCreationRequest(BaseModel):
    """Request to create dataset from document"""
    doc_id: Optional[str] = Field(None, description="Document ID (auto-generated if not provided)")
    domain: DomainType = Field(DomainType.GENERAL, description="Document domain")
    qa_strategy: QAGenerationStrategy = Field(
        QAGenerationStrategy.HYBRID,
        description="Q&A generation strategy"
    )
    min_quality_score: float = Field(0.7, ge=0.0, le=1.0, description="Minimum quality threshold")
    enable_groundedness_check: bool = Field(True, description="Enable groundedness verification")
    output_format: str = Field("jsonl", pattern="^(jsonl|json|csv)$", description="Output format")


class DatasetInfo(BaseModel):
    """Dataset information"""
    dataset_id: str
    doc_id: str
    name: str
    description: str
    
    # Statistics
    total_examples: int
    train_examples: int
    eval_examples: int
    test_examples: int
    avg_quality_score: float
    
    # Processing metrics
    total_qa_pairs: int
    filtered_qa_pairs: int
    grounded_qa_pairs: int
    avg_groundedness_score: float
    
    # Difficulty distribution
    easy_count: int
    medium_count: int
    hard_count: int
    
    # Paths
    dataset_path: str
    
    # Metadata
    created_at: str
    processing_time_ms: float
    success: bool
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class JobStatus(BaseModel):
    """Background job status"""
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 to 1.0
    message: str
    result: Optional[DatasetInfo] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class BatchRequest(BaseModel):
    """Batch processing request"""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to process")
    config: Optional[DatasetCreationRequest] = None


# =============================================================================
# Helper Functions
# =============================================================================

async def get_pipeline() -> DocumentToTrainingPipeline:
    """Get or create pipeline instance (singleton)"""
    global _pipeline
    
    async with _pipeline_lock:
        if _pipeline is None:
            _pipeline = DocumentToTrainingPipeline()
            await _pipeline.initialize()
            logger.info("DocumentToTrainingPipeline initialized")
    
    return _pipeline


def processing_result_to_dataset_info(result: ProcessingResult) -> DatasetInfo:
    """Convert ProcessingResult to DatasetInfo"""
    return DatasetInfo(
        dataset_id=result.dataset.dataset_id if result.dataset else "unknown",
        doc_id=result.doc_id,
        name=result.dataset.name if result.dataset else "",
        description=result.dataset.description if result.dataset else "",
        total_examples=result.dataset.total_examples if result.dataset else 0,
        train_examples=len(result.dataset.train_examples) if result.dataset else 0,
        eval_examples=len(result.dataset.eval_examples) if result.dataset else 0,
        test_examples=len(result.dataset.test_examples) if result.dataset else 0,
        avg_quality_score=result.avg_quality_score,
        total_qa_pairs=result.total_qa_pairs,
        filtered_qa_pairs=result.filtered_qa_pairs,
        grounded_qa_pairs=result.grounded_qa_pairs,
        avg_groundedness_score=result.avg_groundedness_score,
        easy_count=result.easy_count,
        medium_count=result.medium_count,
        hard_count=result.hard_count,
        dataset_path=str(result.dataset_path) if result.dataset_path else "",
        created_at=result.dataset.created_at.isoformat() if result.dataset else datetime.now().isoformat(),
        processing_time_ms=result.processing_time_ms,
        success=result.success,
        error=result.error,
        warnings=result.warnings,
    )


async def process_document_background(
    job_id: str,
    doc_id: str,
    text: str,
    config: DatasetCreationRequest,
):
    """Background task for document processing"""
    try:
        _jobs[job_id]["status"] = "processing"
        _jobs[job_id]["progress"] = 0.1
        _jobs[job_id]["message"] = "Initializing pipeline..."
        _jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Get pipeline
        pipeline = await get_pipeline()
        
        # Configure pipeline
        pipeline_config = DocumentToTrainingConfig(
            qa_strategy=config.qa_strategy,
            domain=config.domain,
            min_quality_score=config.min_quality_score,
            enable_groundedness_check=config.enable_groundedness_check,
            output_format=config.output_format,
        )
        pipeline.config = pipeline_config
        
        _jobs[job_id]["progress"] = 0.3
        _jobs[job_id]["message"] = "Processing document..."
        _jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Process document
        result = await pipeline.process_document(
            doc_id=doc_id,
            text=text,
            metadata={"domain": config.domain.value},
        )
        
        _jobs[job_id]["progress"] = 1.0
        _jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        if result.success:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["message"] = "Dataset created successfully"
            _jobs[job_id]["result"] = processing_result_to_dataset_info(result)
        else:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["message"] = f"Processing failed: {result.error}"
            _jobs[job_id]["error"] = result.error
        
    except Exception as e:
        logger.error(f"Background processing failed for job {job_id}: {e}", exc_info=True)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["message"] = f"Error: {str(e)}"
        _jobs[job_id]["error"] = str(e)
        _jobs[job_id]["updated_at"] = datetime.now().isoformat()


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/from-document", response_model=DatasetInfo, status_code=201)
async def create_dataset_from_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    doc_id: Optional[str] = Form(None, description="Document ID"),
    domain: DomainType = Form(DomainType.GENERAL, description="Document domain"),
    qa_strategy: QAGenerationStrategy = Form(
        QAGenerationStrategy.HYBRID,
        description="Q&A generation strategy"
    ),
    min_quality_score: float = Form(0.7, ge=0.0, le=1.0, description="Minimum quality threshold"),
    enable_groundedness_check: bool = Form(True, description="Enable groundedness verification"),
    output_format: str = Form("jsonl", description="Output format (jsonl, json, csv)"),
):
    """
    Create training dataset from uploaded document.
    
    This endpoint:
    1. Accepts document upload (PDF, DOCX, TXT)
    2. Extracts text content
    3. Generates Q&A pairs using multiple strategies
    4. Filters by quality and groundedness
    5. Creates training dataset with splits
    6. Returns dataset information
    
    **Processing Steps:**
    - Document chunking
    - Q&A generation (LLM, Template, Extractive, or Hybrid)
    - Quality filtering
    - Groundedness verification
    - Difficulty classification
    - Dataset creation (train/eval/test splits)
    
    **Returns:**
    - Dataset information with metrics
    - File paths for train/eval/test splits
    - Quality and groundedness scores
    """
    try:
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = f"doc_{uuid4().hex[:8]}"
        
        # Validate file type
        allowed_types = ["text/plain", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Allowed: TXT, PDF, DOCX"
            )
        
        # Read file content
        content = await file.read()
        
        # Extract text (basic implementation - can be enhanced)
        if file.content_type == "text/plain":
            text = content.decode("utf-8")
        else:
            # For PDF/DOCX, use document handlers
            from mahoun.pipelines.ingestion.document_handlers import DocumentHandlerFactory
            
            handler = DocumentHandlerFactory.get_handler(file.filename)
            text = handler.extract_text(content)
        
        # Sanitize text
        sanitizer = StringSanitizer()
        text = sanitizer.sanitize(text)
        
        if len(text) < 100:
            raise HTTPException(
                status_code=400,
                detail="Document too short (minimum 100 characters)"
            )
        
        # Get pipeline
        pipeline = await get_pipeline()
        
        # Configure pipeline
        config = DocumentToTrainingConfig(
            qa_strategy=qa_strategy,
            domain=domain,
            min_quality_score=min_quality_score,
            enable_groundedness_check=enable_groundedness_check,
            output_format=output_format,
        )
        pipeline.config = config
        
        # Process document
        logger.info(f"Processing document {doc_id} ({len(text)} chars)")
        result = await pipeline.process_document(
            doc_id=doc_id,
            text=text,
            metadata={"domain": domain.value, "filename": file.filename},
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {result.error}"
            )
        
        # Convert to response
        dataset_info = processing_result_to_dataset_info(result)
        
        logger.info(f"Dataset created: {dataset_info.dataset_id}")
        return dataset_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating dataset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-document/async", response_model=JobStatus, status_code=202)
async def create_dataset_from_document_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_id: Optional[str] = Form(None),
    domain: DomainType = Form(DomainType.GENERAL),
    qa_strategy: QAGenerationStrategy = Form(QAGenerationStrategy.HYBRID),
    min_quality_score: float = Form(0.7),
    enable_groundedness_check: bool = Form(True),
    output_format: str = Form("jsonl"),
):
    """
    Create training dataset from document (async/background processing).
    
    For large documents, use this endpoint to process in the background.
    Returns a job ID that can be used to check status.
    """
    try:
        # Generate IDs
        if not doc_id:
            doc_id = f"doc_{uuid4().hex[:8]}"
        job_id = f"job_{uuid4().hex[:12]}"
        
        # Read file
        content = await file.read()
        
        if file.content_type == "text/plain":
            text = content.decode("utf-8")
        else:
            from mahoun.pipelines.ingestion.document_handlers import DocumentHandlerFactory
            handler = DocumentHandlerFactory.get_handler(file.filename)
            text = handler.extract_text(content)
        
        # Create job
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0.0,
            "message": "Job queued",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # Create config
        config = DatasetCreationRequest(
            doc_id=doc_id,
            domain=domain,
            qa_strategy=qa_strategy,
            min_quality_score=min_quality_score,
            enable_groundedness_check=enable_groundedness_check,
            output_format=output_format,
        )
        
        # Schedule background task
        background_tasks.add_task(
            process_document_background,
            job_id, doc_id, text, config
        )
        
        return JobStatus(**_jobs[job_id])
        
    except Exception as e:
        logger.error(f"Error creating async job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of background job"""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**_jobs[job_id])


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of jobs to return"),
):
    """List all background jobs"""
    jobs = list(_jobs.values())
    
    # Filter by status
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    
    # Sort by created_at (newest first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Limit
    jobs = jobs[:limit]
    
    return [JobStatus(**j) for j in jobs]


@router.get("/{dataset_id}", response_model=DatasetInfo)
async def get_dataset(dataset_id: str):
    """Get dataset information by ID"""
    # Search in jobs
    for job in _jobs.values():
        if job.get("result") and job["result"].get("dataset_id") == dataset_id:
            return DatasetInfo(**job["result"])
    
    raise HTTPException(status_code=404, detail="Dataset not found")


@router.get("/{dataset_id}/download/{split}")
async def download_dataset_split(
    dataset_id: str,
    split: str = PathParam(..., pattern="^(train|eval|test)$", description="Dataset split"),
):
    """Download dataset split file"""
    # Find dataset
    dataset_info = None
    for job in _jobs.values():
        if job.get("result") and job["result"].get("dataset_id") == dataset_id:
            dataset_info = job["result"]
            break
    
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get file path
    dataset_path = Path(dataset_info["dataset_path"])
    file_path = dataset_path / f"{split}.jsonl"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Split file not found: {split}")
    
    return FileResponse(
        path=file_path,
        filename=f"{dataset_id}_{split}.jsonl",
        media_type="application/x-ndjson",
    )


@router.post("/batch", response_model=List[DatasetInfo])
async def batch_process_documents(request: BatchRequest):
    """
    Batch process multiple documents.
    
    Processes multiple documents in parallel and returns results.
    """
    try:
        pipeline = await get_pipeline()
        
        # Configure if provided
        if request.config:
            config = DocumentToTrainingConfig(
                qa_strategy=request.config.qa_strategy,
                domain=request.config.domain,
                min_quality_score=request.config.min_quality_score,
                enable_groundedness_check=request.config.enable_groundedness_check,
                output_format=request.config.output_format,
            )
            pipeline.config = config
        
        # Process batch
        results = await pipeline.process_batch(request.documents)
        
        # Convert to response
        dataset_infos = [
            processing_result_to_dataset_info(result)
            for result in results
        ]
        
        return dataset_infos
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
async def get_pipeline_stats():
    """Get pipeline statistics"""
    try:
        pipeline = await get_pipeline()
        stats = pipeline.get_stats()
        
        # Add job stats
        stats["jobs"] = {
            "total": len(_jobs),
            "pending": sum(1 for j in _jobs.values() if j["status"] == "pending"),
            "processing": sum(1 for j in _jobs.values() if j["status"] == "processing"),
            "completed": sum(1 for j in _jobs.values() if j["status"] == "completed"),
            "failed": sum(1 for j in _jobs.values() if j["status"] == "failed"),
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Delete a job from tracking"""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del _jobs[job_id]
    return None
