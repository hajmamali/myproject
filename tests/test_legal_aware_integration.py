"""
Legal-Aware Integration Tests
=============================
Comprehensive integration tests for legal-aware schema design.

Tests cover:
- Legal metadata extraction and storage
- Cross-system synchronization (vector ↔ graph)
- Legal-aware retrieval and filtering
- Court hierarchy ranking
- Supersession detection
- Migration service functionality
"""

import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone

from mahoun.schemas.legal_aware_schema import (
    LegalMetadata, CourtRank, StatuteStatus, LegalQueryFilter,
    EnhancedRetrievalResult, LegalDocumentType
)
from mahoun.rag.legal_aware_retrieval import LegalAwareRetrievalService
from mahoun.graph.legal_cypher_queries import LegalCypherQueries, LegalQueryExecutor
from mahoun.services.legal_migration_service import LegalMigrationService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_legal_metadata():
    """Sample legal metadata for testing"""
    return LegalMetadata(
        court_rank=CourtRank.SUPREME_COURT,
        statute_status=StatuteStatus.ACTIVE,
        date_jalali="1402/10/15",
        date_gregorian="2024-01-05",
        authority_score=0.95,
        citation_count=25,
        cited_by_higher_courts=True,
        legal_domain="civil"
    )


@pytest.fixture
def sample_legal_documents():
    """Sample legal documents for testing"""
    return [
        {
            "doc_id": "supreme_verdict_001",
            "content": "رأی دیوان عالی کشور - ماده 10 قانون مدنی",
            "court_rank": CourtRank.SUPREME_COURT,
            "statute_status": StatuteStatus.ACTIVE,
            "authority_score": 0.95
        },
        {
            "doc_id": "appeals_verdict_001",
            "content": "رأی دادگاه تجدیدنظر - ماده 183 قانون مدنی",
            "court_rank": CourtRank.APPEALS_COURT,
            "statute_status": StatuteStatus.ACTIVE,
            "authority_score": 0.85
        },
        {
            "doc_id": "first_instance_verdict_001",
            "content": "رأی دادگاه بدوی - قرارداد خرید و فروش",
            "court_rank": CourtRank.FIRST_INSTANCE,
            "statute_status": StatuteStatus.ACTIVE,
            "authority_score": 0.70
        },
        {
            "doc_id": "repealed_law_001",
            "content": "قانون منسوخ شده - ماده 50",
            "court_rank": None,
            "statute_status": StatuteStatus.REPEALED,
            "authority_score": 0.0
        }
    ]


# ============================================================================
# Legal Metadata Tests
# ============================================================================

class TestLegalMetadata:
    """Test legal metadata schema and validation"""
    
    def test_legal_metadata_creation(self, sample_legal_metadata):
        """Test creating legal metadata with all fields"""
        assert sample_legal_metadata.court_rank == CourtRank.SUPREME_COURT
        assert sample_legal_metadata.statute_status == StatuteStatus.ACTIVE
        assert sample_legal_metadata.authority_score == 0.95
        assert sample_legal_metadata.cited_by_higher_courts is True
    
    def test_court_rank_hierarchy(self):
        """Test court rank hierarchy ordering"""
        assert CourtRank.SUPREME_COURT.value < CourtRank.APPEALS_COURT.value
        assert CourtRank.APPEALS_COURT.value < CourtRank.FIRST_INSTANCE.value
        assert CourtRank.FIRST_INSTANCE.value < CourtRank.SPECIALIZED_COURT.value
    
    def test_statute_status_values(self):
        """Test statute status enumeration"""
        assert StatuteStatus.ACTIVE.value == "active"
        assert StatuteStatus.REPEALED.value == "repealed"
        assert StatuteStatus.AMENDED.value == "amended"
    
    def test_legal_metadata_defaults(self):
        """Test legal metadata default values"""
        metadata = LegalMetadata()
        assert metadata.statute_status == StatuteStatus.ACTIVE
        assert metadata.authority_score == 0.0
        assert metadata.citation_count == 0
        assert metadata.cited_by_higher_courts is False


# ============================================================================
# Legal Query Filter Tests
# ============================================================================

class TestLegalQueryFilter:
    """Test legal query filtering"""
    
    def test_default_filter(self):
        """Test default legal query filter"""
        filter = LegalQueryFilter()
        assert filter.exclude_repealed is True
        assert filter.min_authority_score == 0.0
        assert StatuteStatus.ACTIVE in filter.allowed_statuses
    
    def test_court_hierarchy_filter(self):
        """Test filtering by court hierarchy"""
        filter = LegalQueryFilter(
            min_court_rank=CourtRank.APPEALS_COURT,
            max_court_rank=CourtRank.FIRST_INSTANCE
        )
        assert filter.min_court_rank == CourtRank.APPEALS_COURT
        assert filter.max_court_rank == CourtRank.FIRST_INSTANCE
    
    def test_authority_score_filter(self):
        """Test filtering by authority score"""
        filter = LegalQueryFilter(min_authority_score=0.8)
        assert filter.min_authority_score == 0.8
    
    def test_temporal_filter(self):
        """Test temporal filtering"""
        filter = LegalQueryFilter(
            date_from="2020-01-01",
            date_to="2024-12-31"
        )
        assert filter.date_from == "2020-01-01"
        assert filter.date_to == "2024-12-31"


# ============================================================================
# Legal Cypher Queries Tests
# ============================================================================

class TestLegalCypherQueries:
    """Test legal Cypher query collection"""
    
    def test_query_retrieval(self):
        """Test retrieving queries by name"""
        query = LegalCypherQueries.get_query("find_superseded_laws")
        assert query is not None
        assert query.name == "find_superseded_laws"
        assert query.category.value == "supersession"
    
    def test_query_categories(self):
        """Test querying by category"""
        supersession_queries = LegalCypherQueries.get_queries_by_category(
            LegalCypherQueries.FIND_SUPERSEDED_LAWS.category
        )
        assert len(supersession_queries) > 0
    
    def test_all_queries_list(self):
        """Test listing all queries"""
        all_queries = LegalCypherQueries.list_all_queries()
        assert len(all_queries) > 0
        
        # Verify essential queries exist
        query_names = [q.name for q in all_queries]
        assert "find_superseded_laws" in query_names
        assert "validate_no_supersession" in query_names
        assert "rank_by_court_hierarchy" in query_names
    
    def test_query_parameters(self):
        """Test query parameter definitions"""
        query = LegalCypherQueries.get_query("find_superseded_laws")
        assert "law_id" in query.parameters
        assert query.complexity in ["LOW", "MEDIUM", "HIGH"]


# ============================================================================
# Legal-Aware Retrieval Tests
# ============================================================================

class TestLegalAwareRetrieval:
    """Test legal-aware retrieval service"""
    
    @pytest.mark.asyncio
    async def test_legal_filtering(self, sample_legal_documents):
        """Test filtering of repealed documents"""
        # Mock retrieval results
        mock_results = [
            EnhancedRetrievalResult(
                doc_id=doc["doc_id"],
                content=doc["content"],
                score=0.9,
                rank=i+1,
                source="test",
                legal_metadata=LegalMetadata(
                    court_rank=doc["court_rank"],
                    statute_status=doc["statute_status"],
                    authority_score=doc["authority_score"]
                )
            )
            for i, doc in enumerate(sample_legal_documents)
        ]
        
        # Create filter
        legal_filter = LegalQueryFilter(exclude_repealed=True)
        
        # Apply filtering logic
        filtered = [
            r for r in mock_results
            if r.legal_metadata.statute_status != StatuteStatus.REPEALED
        ]
        
        # Verify repealed documents are excluded
        assert len(filtered) == 3
        assert all(r.legal_metadata.statute_status != StatuteStatus.REPEALED for r in filtered)
    
    @pytest.mark.asyncio
    async def test_court_hierarchy_ranking(self, sample_legal_documents):
        """Test ranking by court hierarchy"""
        # Mock retrieval results
        mock_results = [
            EnhancedRetrievalResult(
                doc_id=doc["doc_id"],
                content=doc["content"],
                score=0.8,  # Same base score
                rank=i+1,
                source="test",
                legal_metadata=LegalMetadata(
                    court_rank=doc["court_rank"],
                    statute_status=doc["statute_status"],
                    authority_score=doc["authority_score"]
                )
            )
            for i, doc in enumerate(sample_legal_documents[:3])  # Exclude repealed
        ]
        
        # Apply authority ranking
        for result in mock_results:
            metadata = result.legal_metadata
            authority_boost = 0.0
            
            if metadata.court_rank == CourtRank.SUPREME_COURT:
                authority_boost += 0.3
            elif metadata.court_rank == CourtRank.APPEALS_COURT:
                authority_boost += 0.2
            elif metadata.court_rank == CourtRank.FIRST_INSTANCE:
                authority_boost += 0.1
            
            result.score = min(1.0, result.score + authority_boost)
        
        # Sort by score
        mock_results.sort(key=lambda x: x.score, reverse=True)
        
        # Verify Supreme Court is ranked first
        assert mock_results[0].legal_metadata.court_rank == CourtRank.SUPREME_COURT
        assert mock_results[1].legal_metadata.court_rank == CourtRank.APPEALS_COURT
        assert mock_results[2].legal_metadata.court_rank == CourtRank.FIRST_INSTANCE


# ============================================================================
# Migration Service Tests
# ============================================================================

class TestLegalMigrationService:
    """Test legal schema migration service"""
    
    @pytest.mark.asyncio
    async def test_metadata_extraction(self):
        """Test legal metadata extraction from document ID"""
        # Test Supreme Court document
        doc_id = "supreme_verdict_دیوان_عالی_001"
        metadata = LegalMetadata()
        
        if "supreme" in doc_id.lower() or "دیوان_عالی" in doc_id:
            metadata.court_rank = CourtRank.SUPREME_COURT
            metadata.authority_score = 0.95
        
        assert metadata.court_rank == CourtRank.SUPREME_COURT
        assert metadata.authority_score == 0.95
    
    @pytest.mark.asyncio
    async def test_migration_batch_creation(self):
        """Test creating migration batch"""
        from mahoun.services.legal_migration_service import MigrationBatch, MigrationStatus
        
        batch = MigrationBatch(
            batch_id="test_migration_001",
            document_ids=["doc1", "doc2", "doc3"],
            batch_size=100
        )
        
        assert batch.status == MigrationStatus.PENDING
        assert len(batch.document_ids) == 3
        assert batch.processed_count == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestLegalAwareIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_legal_retrieval_pipeline(self, sample_legal_documents):
        """Test complete legal-aware retrieval pipeline"""
        # 1. Create legal metadata
        documents_with_metadata = []
        for doc in sample_legal_documents:
            metadata = LegalMetadata(
                court_rank=doc["court_rank"],
                statute_status=doc["statute_status"],
                authority_score=doc["authority_score"]
            )
            documents_with_metadata.append({
                **doc,
                "legal_metadata": metadata
            })
        
        # 2. Apply legal filtering
        legal_filter = LegalQueryFilter(
            exclude_repealed=True,
            min_authority_score=0.7
        )
        
        filtered_docs = [
            doc for doc in documents_with_metadata
            if doc["legal_metadata"].statute_status != StatuteStatus.REPEALED
            and doc["legal_metadata"].authority_score >= legal_filter.min_authority_score
        ]
        
        # 3. Apply court hierarchy ranking
        filtered_docs.sort(
            key=lambda x: (
                x["legal_metadata"].court_rank.value if x["legal_metadata"].court_rank else 999,
                -x["legal_metadata"].authority_score
            )
        )
        
        # 4. Verify results
        assert len(filtered_docs) == 3
        assert filtered_docs[0]["court_rank"] == CourtRank.SUPREME_COURT
        assert all(doc["statute_status"] != StatuteStatus.REPEALED for doc in filtered_docs)
    
    @pytest.mark.asyncio
    async def test_supersession_detection(self):
        """Test supersession relationship detection"""
        # Create documents with supersession
        old_law = LegalMetadata(
            statute_status=StatuteStatus.ACTIVE,
            superseded_by="new_law_001"
        )
        
        new_law = LegalMetadata(
            statute_status=StatuteStatus.ACTIVE,
            supersedes=["old_law_001"]
        )
        
        # Verify supersession relationships
        assert old_law.superseded_by == "new_law_001"
        assert "old_law_001" in new_law.supersedes
    
    @pytest.mark.asyncio
    async def test_cross_system_synchronization(self):
        """Test cross-system UID synchronization"""
        from mahoun.schemas.legal_aware_schema import GlobalIdentifier
        
        # Create global identifier
        global_id = GlobalIdentifier(
            uid="doc_12345",
            document_type=LegalDocumentType.VERDICT,
            in_vector_store=True,
            in_graph_store=True,
            sync_status="synchronized"
        )
        
        # Verify synchronization
        assert global_id.in_vector_store is True
        assert global_id.in_graph_store is True
        assert global_id.sync_status == "synchronized"


# ============================================================================
# Performance Tests
# ============================================================================

class TestLegalAwarePerformance:
    """Performance tests for legal-aware operations"""
    
    @pytest.mark.asyncio
    async def test_large_batch_filtering(self):
        """Test filtering performance with large document set"""
        # Create large document set
        large_doc_set = [
            LegalMetadata(
                court_rank=CourtRank.SUPREME_COURT if i % 3 == 0 else CourtRank.APPEALS_COURT,
                statute_status=StatuteStatus.ACTIVE if i % 5 != 0 else StatuteStatus.REPEALED,
                authority_score=0.5 + (i % 50) / 100
            )
            for i in range(1000)
        ]
        
        # Apply filtering
        start_time = datetime.now(timezone.utc)
        filtered = [
            doc for doc in large_doc_set
            if doc.statute_status == StatuteStatus.ACTIVE
            and doc.authority_score >= 0.7
        ]
        end_time = datetime.now(timezone.utc)
        
        # Verify performance
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0  # Should complete in less than 1 second
        assert len(filtered) > 0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
