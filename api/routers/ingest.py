"""
Document Ingestion Router
==========================
Upload and process legal documents
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
import uuid
import logging

from api.models import (
    DocumentIngest,
    DocumentIngestResponse,
    User,
    JobSubmissionResponse,
    JobStatusResponse,
    JobListResponse,
    JobStatus,
    DLQItem,
    DLQListResponse,
    DLQRetryResponse,
    DLQErrorType,
)
from api.auth.dependencies import require_analyst, get_optional_user
from api.database import get_postgres
from typing import Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Lazy initialization of ingestion pipeline & unified loader
# ============================================================================

_ingestion_pipeline: Optional[Any] = None
_unified_loader: Optional[Any] = None




async def get_ingestion_pipeline():
    """
    Lazy init ingestion pipeline.

    This creates a single shared pipeline instance for the API router.
    The pipeline coordinates chunking, embedding, and vector storage.

    Can use EnhancedIngestionPipeline if USE_ENHANCED_INGESTION env var is set.
    """
    global _ingestion_pipeline
    import os

    if _ingestion_pipeline is None:
        try:
            # Check if enhanced pipeline should be used
            use_enhanced = (
                os.getenv("USE_ENHANCED_INGESTION", "false").lower() == "true"
            )

            if use_enhanced:
                try:
                    from mahoun.pipelines.ingestion.enhanced_pipeline import (
                        EnhancedIngestionPipeline,
                    )

                    _ingestion_pipeline = EnhancedIngestionPipeline(
                        enable_llm_refinement=True,
                        enable_cross_validation=True,
                        enable_validation=True,
                    )
                    await _ingestion_pipeline.initialize()

                    logger.info("Initialized EnhancedIngestionPipeline for ingest API")
                except ImportError as e:
                    logger.warning(
                        f"Enhanced pipeline not available: {e}. Falling back to standard pipeline."
                    )
                    use_enhanced = False

            if not use_enhanced:
                from mahoun.pipelines.ingestion.pipeline import IngestionPipeline

                _ingestion_pipeline = IngestionPipeline()
                await _ingestion_pipeline.initialize()

                logger.info("Initialized IngestionPipeline for ingest API")

        except ImportError as e:
            logger.error(f"Could not import IngestionPipeline: {e}")
            _ingestion_pipeline = None
        except Exception as e:
            logger.error(f"Could not initialize IngestionPipeline: {e}")
            _ingestion_pipeline = None
    return _ingestion_pipeline


def _build_upload_response(
    file_path: str,
    filename: str,
    mime: str,
    include_text: bool,
) -> dict:
    import hashlib
    from pathlib import Path
    from mahoun.pipelines.ingestion.document_handlers import extract_document_text

    extracted = extract_document_text(file_path)
    text = extracted.text or ""
    file_bytes = Path(file_path).read_bytes()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    response = {
        "doc_id": str(uuid.uuid4()),
        "filename": filename,
        "mime": mime,
        "sha256": file_sha256,
        "text_length": len(text),
        "text_preview": text[:2000],
        "extraction_method": extracted.metadata.get("extraction_method"),
    }

    if include_text:
        response["text"] = text

    if not extracted.success:
        response["extraction_error"] = (
            extracted.metadata.get("error") or extracted.error
        )

    return response


# ============================================================================
# Routes
# ============================================================================


@router.post("/", response_model=DocumentIngestResponse)
async def ingest_document(
    document: DocumentIngest,
    current_user: User = Depends(require_analyst),
    db=Depends(get_postgres),
):
    """
    Ingest legal document into MAHOUN system

    Requires: analyst or admin role

    Pipeline:
    1. Store metadata in PostgreSQL
    2. Chunk document text
    3. Generate embeddings
    4. (Future) Store in vector DB
    5. (Future) Build graph relationships
    """
    # Generate UUIDs consistently as strings for database compatibility
    record_id = str(uuid.uuid4())  # Primary key for the database record
    doc_id = str(uuid.uuid4())  # Document identifier
    chunks_created = 0
    embeddings_created = 0
    indexed = False
    graph_nodes_created = 0

    try:
        # Store metadata in PostgreSQL
        await db.execute(
            """
            INSERT INTO documents_metadata 
            (id, doc_id, title, law_type, law_id, case_id, date_published, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            record_id,
            doc_id,
            document.title,
            document.doc_type.value,
            document.law_id,
            document.case_id,
            document.date_published,
            document.source,
        )

        # Get ingestion pipeline
        pipeline = await get_ingestion_pipeline()

        if pipeline and document.content:
            # Run full ingestion: chunking + embedding + vector storage
            metadata = {
                "title": document.title,
                "doc_type": document.doc_type.value,
                "law_id": document.law_id,
                "case_id": document.case_id,
                "date_published": str(document.date_published)
                if document.date_published
                else None,
                "source": document.source,
            }

            result = await pipeline.ingest_document(
                doc_id=doc_id, text=document.content, metadata=metadata
            )

            chunks_created = result.chunks_created
            embeddings_created = result.embeddings_created
            indexed = result.indexed

            logger.info(
                f"Ingested document {doc_id}: "
                f"{chunks_created} chunks, {embeddings_created} embeddings, indexed={indexed}"
            )
        else:
            if not pipeline:
                logger.warning(
                    "Ingestion pipeline not available, document not fully processed"
                )
            if not document.content:
                logger.warning(f"No content provided for document {doc_id}")

        import os

        graph_build_enabled = (
            os.getenv("MAHOUN_GRAPH_BUILD_ENABLED", "false").lower() == "true"
        )

        if document.content and graph_build_enabled:
            try:
                from mahoun.pipelines.ingestion.minimal_verdict_parser import (
                    parse_verdict_text,
                    validate_verdict_struct,
                )
                from mahoun.pipelines.graph_build import GraphBuildPipeline

                verdict_struct = parse_verdict_text(document.content)
                is_valid, errors = validate_verdict_struct(verdict_struct)
                confidence = verdict_struct.get("_parsing_quality", {}).get(
                    "confidence_score", 0.0
                )

                if is_valid and confidence >= 0.6:
                    graph_pipeline = GraphBuildPipeline()
                    graph_result = graph_pipeline.build_from_verdict(
                        verdict_struct, source_id=doc_id
                    )
                    if graph_result.success:
                        graph_nodes_created = graph_result.nodes_created
                    else:
                        logger.warning(
                            f"Graph build failed for {doc_id}: {graph_result.error}"
                        )
                else:
                    if not is_valid:
                        logger.info(
                            f"Graph build skipped for {doc_id}: invalid verdict structure "
                            f"({len(errors)} errors)"
                        )
                    else:
                        logger.info(
                            f"Graph build skipped for {doc_id}: parsing confidence {confidence:.2f} below threshold"
                        )
            except Exception as e:
                logger.warning(
                    f"Graph build step failed for {doc_id}: {e}", exc_info=True
                )
        elif document.content:
            logger.info("Graph build skipped (MAHOUN_GRAPH_BUILD_ENABLED=false)")

        # Build status message
        # NOTE: Use `ingest_status` to avoid shadowing FastAPI's `status` module
        if indexed:
            message = f"Document ingested and indexed successfully ({chunks_created} chunks, {embeddings_created} embeddings)"
            ingest_status = "success"
        elif chunks_created > 0:
            message = f"Document processed but not fully indexed ({chunks_created} chunks created)"
            ingest_status = "partial"
        else:
            message = "Document metadata stored but content not processed"
            ingest_status = "metadata_only"

        return DocumentIngestResponse(
            doc_id=doc_id,
            status=ingest_status,
            message=message,
            chunks_created=chunks_created,
            embeddings_created=embeddings_created,
            graph_nodes_created=graph_nodes_created,
        )

    except Exception as e:
        logger.error(f"Ingestion failed for document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    include_text: bool = False,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Upload document file (PDF, DOCX, TXT)

    Supported formats:
    - PDF: Requires pdfplumber or pypdf
    - DOCX: Requires python-docx
    - TXT: Native support

    Note: Authentication is optional for file upload.
    If authenticated, user info will be logged for audit purposes.
    Use include_text=true to return full extracted text.
    """
    # Log upload with user info if available
    if current_user:
        logger.info(
            f"File upload by user: {current_user.username} (ID: {current_user.id})"
        )
    else:
        logger.info("File upload by anonymous user")
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided"
        )

    # Get file extension
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""

    supported_formats = {"pdf", "docx", "txt", "md"}
    if file_ext not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported format: {file_ext}. Supported: {sorted(supported_formats)}",
        )

    try:
        # Read file content
        content = await file.read()
        mime = file.content_type or "application/octet-stream"

        import tempfile
        from pathlib import Path

        suffix = f".{file_ext}" if file_ext else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            response = _build_upload_response(
                str(tmp_path),
                filename=file.filename,
                mime=mime,
                include_text=include_text,
            )
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                logger.debug("Temporary upload file cleanup failed", exc_info=True)

        return response

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


# ============================================================================
# ============================================================================








# ============================================================================
# ============================================================================






@router.post("/dlq/{job_id}/retry", response_model=DLQRetryResponse)
async def retry_dlq_job(
    job_id: str, current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Retry a failed job from DLQ

    Creates a new job with the same file and metadata.
    """
    loader = await get_unified_loader()

    if not loader:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unified loader not available",
        )

    try:
        import json
        from pathlib import Path

        dlq_dir = loader.dlq_dir

        # Find the failed file
        failed_file = None
        error_file = None

        for ef in dlq_dir.glob("*.error.json"):
            try:
                with open(ef, "r") as f:
                    error_data = json.load(f)

                if error_data.get("job_id") == job_id:
                    error_file = ef
                    # Find corresponding failed file
                    failed_file = ef.with_suffix("").with_suffix(".failed")
                    break
            except Exception:
                continue

        if not failed_file or not failed_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DLQ item {job_id} not found or file missing",
            )

        # Submit new job
        metadata = {"retried_from": job_id, "retry_attempt": 1}

        new_job_id = await loader.submit_file(str(failed_file), metadata)

        logger.info(f"Retrying DLQ job {job_id} as new job {new_job_id}")

        return DLQRetryResponse(
            success=True,
            new_job_id=new_job_id,
            message=f"Job resubmitted successfully. New job ID: {new_job_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry DLQ job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry DLQ job: {str(e)}",
        )


@router.delete("/dlq/{job_id}")
async def delete_dlq_item(
    job_id: str, current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Remove item from DLQ

    Deletes both the failed file and error log.
    """
    loader = await get_unified_loader()

    if not loader:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unified loader not available",
        )

    try:
        import json
        from pathlib import Path

        dlq_dir = loader.dlq_dir
        deleted = False

        # Find and delete files
        for error_file in dlq_dir.glob("*.error.json"):
            try:
                with open(error_file, "r") as f:
                    error_data = json.load(f)

                if error_data.get("job_id") == job_id:
                    # Delete error file
                    error_file.unlink()

                    # Delete corresponding failed file
                    failed_file = error_file.with_suffix("").with_suffix(".failed")
                    if failed_file.exists():
                        failed_file.unlink()

                    deleted = True
                    logger.info(f"Deleted DLQ item {job_id}")
                    break
            except Exception as e:
                logger.warning(f"Failed to process DLQ file {error_file}: {e}")
                continue

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DLQ item {job_id} not found",
            )

        return {"success": True, "message": f"DLQ item {job_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete DLQ item: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete DLQ item: {str(e)}",
        )


# ============================================================================
# Chunker Configuration Endpoints
# ============================================================================


@router.get("/config/chunker")
async def get_chunker_config(current_user: Optional[User] = Depends(get_optional_user)):
    """
    Get current chunker configuration

    Returns the active chunker type and its configuration parameters.
    This is useful for monitoring and debugging.
    """
    import os

    chunker_type = os.getenv("MAHOUN_CHUNKER_TYPE", "enhanced")

    config = {
        "chunker_type": chunker_type,
        "chunk_size": int(os.getenv("MAHOUN_CHUNK_SIZE", "512")),
        "overlap": int(os.getenv("MAHOUN_CHUNK_OVERLAP", "50")),
    }

    # Add legal-aware specific options if applicable
    if chunker_type in ["legal_aware", "auto"]:
        config["legal_aware_options"] = {
            "preserve_articles": os.getenv("MAHOUN_PRESERVE_ARTICLES", "true").lower()
            == "true",
            "preserve_reasoning": os.getenv("MAHOUN_PRESERVE_REASONING", "true").lower()
            == "true",
            "preserve_citations": os.getenv("MAHOUN_PRESERVE_CITATIONS", "true").lower()
            == "true",
            "min_chunk_size": int(os.getenv("MAHOUN_MIN_CHUNK_SIZE", "100")),
            "max_chunk_size": int(os.getenv("MAHOUN_MAX_CHUNK_SIZE", "1024")),
        }

    # Add graph storage status
    config["graph_storage_enabled"] = (
        os.getenv("MAHOUN_GRAPH_BUILD_ENABLED", "false").lower() == "true"
    )

    return config


@router.post("/config/chunker")
async def update_chunker_config(
    chunker_type: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    current_user: User = Depends(require_analyst),
):
    """
    Update chunker configuration

    Note: This updates the .env file. Server restart is required for changes to take effect.

    Requires: analyst or admin role

    Args:
        chunker_type: Type of chunker (enhanced, legal_aware, auto)
        chunk_size: Optional chunk size override
        overlap: Optional overlap override
    """
    from pathlib import Path

    # Validate chunker type
    valid_types = ["enhanced", "legal_aware", "auto"]
    if chunker_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chunker_type: {chunker_type}. Must be one of: {valid_types}",
        )

    # Validate chunk size if provided
    if chunk_size is not None:
        if chunk_size < 100 or chunk_size > 2048:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chunk_size must be between 100 and 2048",
            )

    # Validate overlap if provided
    if overlap is not None:
        if overlap < 0 or overlap > 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="overlap must be between 0 and 200",
            )

    try:
        env_file = Path(".env")

        if not env_file.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=".env file not found",
            )

        # Read current .env
        lines = env_file.read_text().splitlines()

        # Update or add configuration
        def update_or_add(key: str, value: str):
            nonlocal lines
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    updated = True
                    break
            if not updated:
                lines.append(f"{key}={value}")

        update_or_add("MAHOUN_CHUNKER_TYPE", chunker_type)

        if chunk_size is not None:
            update_or_add("MAHOUN_CHUNK_SIZE", str(chunk_size))

        if overlap is not None:
            update_or_add("MAHOUN_CHUNK_OVERLAP", str(overlap))

        # Write back to .env
        env_file.write_text("\n".join(lines) + "\n")

        logger.info(
            f"Chunker configuration updated by {current_user.username}: "
            f"type={chunker_type}, size={chunk_size}, overlap={overlap}"
        )

        return {
            "status": "updated",
            "chunker_type": chunker_type,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "message": "Configuration updated successfully. Restart the server to apply changes.",
            "restart_command": "make docker-restart",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chunker config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}",
        )


@router.get("/stats/chunking")
async def get_chunking_stats(current_user: Optional[User] = Depends(get_optional_user)):
    """
    Get chunking statistics from the pipeline

    Returns statistics about chunking performance and quality.
    """
    pipeline = await get_ingestion_pipeline()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion pipeline not available",
        )

    stats = pipeline.get_stats()

    # Extract chunking-specific stats
    chunking_stats = {
        "total_documents": stats.get("documents_ingested", 0),
        "total_chunks": stats.get("total_chunks", 0),
        "avg_chunks_per_document": (
            stats.get("total_chunks", 0) / stats.get("documents_ingested", 1)
            if stats.get("documents_ingested", 0) > 0
            else 0
        ),
        "avg_processing_time_ms": stats.get("avg_processing_time_ms", 0),
        "chunker_type": type(pipeline.chunker).__name__
        if pipeline.chunker
        else "Unknown",
    }

    return chunking_stats
