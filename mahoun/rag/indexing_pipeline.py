"""
Indexing Pipeline for MAHOUN
=============================

Indexing Pipeline برای انواع مدارک:
- قراردادها (Contracts)
- مکاتبات (Correspondence)
- گزارش‌ها (Reports)
- شرایط عمومی پیمان (General Conditions)

از کامپوننت‌های موجود استفاده می‌کند:
- IngestionPipeline برای پردازش
- Document Normalizer برای normalization
- VectorStoreManager برای ذخیره‌سازی
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from mahoun.pipelines.ingestion import IngestionPipeline
from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer, normalize_document_text

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """انواع مدارک"""
    CONTRACT = "contract"
    CORRESPONDENCE = "correspondence"
    REPORT = "report"
    GENERAL_CONDITIONS = "general_conditions"
    OTHER = "other"


@dataclass
class IndexingResult:
    """نتیجه indexing"""
    success: bool
    doc_id: str
    doc_type: str
    chunks_created: int
    embeddings_created: int
    indexed: bool
    processing_time_ms: float
    error: Optional[str] = None


class IndexingPipeline:
    """
    Indexing Pipeline برای انواع مدارک پیمانکاری
    
    این کلاس از کامپوننت‌های موجود استفاده می‌کند:
    - Document Normalizer برای normalization
    - IngestionPipeline برای processing و indexing
    
    Usage:
        pipeline = IndexingPipeline()
        await pipeline.initialize()
        
        result = await pipeline.index_document(
            text="متن قرارداد...",
            doc_type="contract",
            metadata={"title": "قرارداد اصلی"}
        )
    """
    
    def __init__(
        self,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
        normalizer: Optional[DocumentNormalizer] = None
    ):
        """
        Initialize Indexing Pipeline
        
        Args:
            ingestion_pipeline: IngestionPipeline instance (created if None)
            normalizer: DocumentNormalizer instance (created if None)
        """
        self.ingestion_pipeline = ingestion_pipeline
        self.normalizer = normalizer or DocumentNormalizer()
        self._initialized = False
        
        # Statistics
        self.stats = {
            "total_indexed": 0,
            "by_type": {dt.value: 0 for dt in DocumentType},
            "total_chunks": 0,
            "total_embeddings": 0,
            "failed_indexings": 0
        }
        
        logger.info("IndexingPipeline initialized")
    
    async def initialize(self):
        """Initialize pipeline components"""
        if self._initialized:
            return
        
        # Initialize ingestion pipeline if needed
        if self.ingestion_pipeline is None:
            self.ingestion_pipeline = IngestionPipeline()
            await self.ingestion_pipeline.initialize()
        
        self._initialized = True
        logger.info("IndexingPipeline fully initialized")
    
    async def index_document(
        self,
        text: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> IndexingResult:
        """
        Index a document
        
        Args:
            text: متن سند
            doc_type: نوع سند (contract, correspondence, report, etc.)
            metadata: metadata اضافی
            doc_id: شناسه سند (اگر None باشد، generate می‌شود)
        
        Returns:
            IndexingResult
        """
        import time
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Step 1: Normalize document
            normalized = await self.normalizer.normalize_text(
                text=text,
                doc_type=doc_type,
                metadata=metadata
            )
            
            # Use provided doc_id or use normalized document_id
            final_doc_id = doc_id or normalized.document_id
            
            # Step 2: Index using IngestionPipeline
            ingestion_result = await self.ingestion_pipeline.ingest_document(
                doc_id=final_doc_id,
                text=normalized.content["text"],
                metadata={
                    **normalized.metadata,
                    "doc_type": doc_type,
                    "normalized": True
                }
            )
            
            # Step 3: Update statistics
            self._update_stats(doc_type, ingestion_result)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            return IndexingResult(
                success=ingestion_result.success,
                doc_id=final_doc_id,
                doc_type=doc_type,
                chunks_created=ingestion_result.chunks_created,
                embeddings_created=ingestion_result.embeddings_created,
                indexed=ingestion_result.indexed,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            self.stats["failed_indexings"] += 1
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            return IndexingResult(
                success=False,
                doc_id=doc_id or "unknown",
                doc_type=doc_type,
                chunks_created=0,
                embeddings_created=0,
                indexed=False,
                processing_time_ms=processing_time_ms,
                error=str(e)
            )
    
    async def index_contract(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> IndexingResult:
        """Index a contract document"""
        return await self.index_document(
            text=text,
            doc_type=DocumentType.CONTRACT.value,
            metadata=metadata,
            doc_id=doc_id
        )
    
    async def index_correspondence(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> IndexingResult:
        """Index a correspondence document"""
        return await self.index_document(
            text=text,
            doc_type=DocumentType.CORRESPONDENCE.value,
            metadata=metadata,
            doc_id=doc_id
        )
    
    async def index_report(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> IndexingResult:
        """Index a report document"""
        return await self.index_document(
            text=text,
            doc_type=DocumentType.REPORT.value,
            metadata=metadata,
            doc_id=doc_id
        )
    
    async def index_general_conditions(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> IndexingResult:
        """Index general conditions document"""
        return await self.index_document(
            text=text,
            doc_type=DocumentType.GENERAL_CONDITIONS.value,
            metadata=metadata,
            doc_id=doc_id
        )
    
    async def batch_index(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[IndexingResult]:
        """
        Index multiple documents in batch
        
        Args:
            documents: List of dicts with keys: text, doc_type, metadata, doc_id
        
        Returns:
            List of IndexingResult
        """
        results: List[Any] = []
        for doc in documents:
            result = await self.index_document(
                text=doc.get("text", ""),
                doc_type=doc.get("doc_type", "other"),
                metadata=doc.get("metadata"),
                doc_id=doc.get("doc_id")
            )
            results.append(result)
        
        return results
    
    def _update_stats(self, doc_type: str, ingestion_result: Any):
        """Update statistics"""
        self.stats["total_indexed"] += 1
        
        # Update by type
        if doc_type in [dt.value for dt in DocumentType]:
            self.stats["by_type"][doc_type] += 1
        else:
            self.stats["by_type"][DocumentType.OTHER.value] += 1
        
        # Update chunks and embeddings
        if ingestion_result.success:
            self.stats["total_chunks"] += ingestion_result.chunks_created
            self.stats["total_embeddings"] += ingestion_result.embeddings_created
        else:
            self.stats["failed_indexings"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return self.stats.copy()


# ============================================================================
# Helper Functions
# ============================================================================

async def index_document(
    text: str,
    doc_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> IndexingResult:
    """
    Helper function to index a document
    
    Args:
        text: متن سند
        doc_type: نوع سند
        metadata: metadata اضافی
    
    Returns:
        IndexingResult
    """
    pipeline = IndexingPipeline()
    await pipeline.initialize()
    return await pipeline.index_document(text, doc_type, metadata)

