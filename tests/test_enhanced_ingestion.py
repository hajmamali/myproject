"""
Test Suite for Enhanced Ingestion Pipeline
==========================================
Comprehensive tests for enhanced ingestion accuracy improvements.

Tests:
1. Unit Tests - Imports, initialization, fallbacks
2. Integration Tests - End-to-end, API, backward compatibility
3. Performance Tests - Comparison with standard pipeline
"""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Test imports
# Test imports with strict importorskip (Contract Rule 1)
# These are optional modules, so we skip if missing
pytest.importorskip("mahoun.pipelines.ingestion.enhanced_pipeline")
pytest.importorskip("mahoun.pipelines.ingestion.llm_enhanced_parser")
pytest.importorskip("mahoun.pipelines.ingestion.enhanced_ner")
pytest.importorskip("mahoun.pipelines.ingestion.enhanced_chunker")
pytest.importorskip("mahoun.pipelines.ingestion.enhanced_embedding")
pytest.importorskip("mahoun.pipelines.ingestion.validation_quality")
pytest.importorskip("mahoun.pipelines.ingestion.llm_refiner")

from mahoun.pipelines.ingestion.enhanced_pipeline import EnhancedIngestionPipeline, EnhancedIngestionResult
from mahoun.pipelines.ingestion.llm_enhanced_parser import LLMEnhancedParser
from mahoun.pipelines.ingestion.enhanced_ner import EnhancedNEREngine
from mahoun.pipelines.ingestion.enhanced_chunker import EnhancedChunker, ChunkingConfig
from mahoun.pipelines.ingestion.enhanced_embedding import EnhancedEmbeddingService
from mahoun.pipelines.ingestion.validation_quality import DocumentValidator, QualityAssessor
from mahoun.pipelines.ingestion.llm_refiner import LLMRefinementService

HAS_ENHANCED = True # Still kept for backward compat in test logic down below if needed, though importorskip implies presence


# ============================================================================
# Unit Tests
# ============================================================================

class TestEnhancedImports:
    """Test that all enhanced components can be imported"""
    
    def test_import_enhanced_pipeline(self):
        """Test EnhancedIngestionPipeline import"""
        from mahoun.pipelines.ingestion import EnhancedIngestionPipeline
        assert EnhancedIngestionPipeline is not None
    
    def test_import_llm_enhanced_parser(self):
        """Test LLMEnhancedParser import"""
        from mahoun.pipelines.ingestion import LLMEnhancedParser
        assert LLMEnhancedParser is not None
    
    def test_import_enhanced_ner(self):
        """Test EnhancedNEREngine import"""
        from mahoun.pipelines.ingestion import EnhancedNEREngine
        assert EnhancedNEREngine is not None
    
    def test_import_enhanced_chunker(self):
        """Test EnhancedChunker import"""
        from mahoun.pipelines.ingestion import EnhancedChunker
        assert EnhancedChunker is not None
    
    def test_import_enhanced_embedding(self):
        """Test EnhancedEmbeddingService import"""
        from mahoun.pipelines.ingestion import EnhancedEmbeddingService
        assert EnhancedEmbeddingService is not None
    
    def test_import_validator(self):
        """Test DocumentValidator import"""
        from mahoun.pipelines.ingestion import DocumentValidator
        assert DocumentValidator is not None
    
    def test_import_quality_assessor(self):
        """Test QualityAssessor import"""
        from mahoun.pipelines.ingestion import QualityAssessor
        assert QualityAssessor is not None
    
    def test_import_llm_refiner(self):
        """Test LLMRefinementService import"""
        from mahoun.pipelines.ingestion import LLMRefinementService
        assert LLMRefinementService is not None


class TestEnhancedInitialization:
    """Test initialization of enhanced components"""
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_init_default(self):
        """Test EnhancedIngestionPipeline initialization with defaults"""
        pipeline = EnhancedIngestionPipeline()
        assert pipeline is not None
        assert pipeline.llm_parser is not None
        assert pipeline.ner_engine is not None
        assert pipeline.validator is not None
        assert pipeline.quality_assessor is not None
        assert pipeline.refiner is not None
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_init_custom(self):
        """Test EnhancedIngestionPipeline with custom settings"""
        pipeline = EnhancedIngestionPipeline(
            enable_llm_refinement=False,
            enable_cross_validation=False,
            enable_validation=False,
            strict_validation=False
        )
        assert pipeline is not None
        assert pipeline.validator is None  # Disabled
        assert pipeline.quality_assessor is None  # Disabled
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_initialize(self):
        """Test pipeline initialization"""
        pipeline = EnhancedIngestionPipeline()
        await pipeline.initialize()
        assert pipeline._initialized is True
        assert pipeline.chunker is not None
        assert pipeline.embedding_service is not None
        assert pipeline.vector_store is not None
    
    def test_llm_enhanced_parser_init(self):
        """Test LLMEnhancedParser initialization"""
        parser = LLMEnhancedParser(enable_refinement=False)
        assert parser is not None
        assert parser.enable_refinement is False
    
    def test_enhanced_ner_init(self):
        """Test EnhancedNEREngine initialization"""
        ner = EnhancedNEREngine(enable_cross_validation=False)
        assert ner is not None
        assert ner.enable_cross_validation is False
    
    def test_enhanced_chunker_init(self):
        """Test EnhancedChunker initialization"""
        config = ChunkingConfig(chunk_size=256, overlap=25)
        chunker = EnhancedChunker(config=config)
        assert chunker is not None
        assert chunker.config.chunk_size == 256


class TestFallbackMechanisms:
    """Test fallback mechanisms when components fail"""
    
    @pytest.mark.asyncio
    async def test_llm_parser_fallback_no_llm(self):
        """Test LLM parser falls back when LLM unavailable"""
        parser = LLMEnhancedParser(enable_refinement=True)
        
        # Mock LLM service to fail
        parser._llm_initialized = False
        parser.llm_service = None
        
        # Should still work, just without refinement
        result = await parser.parse_enhanced("test text")
        assert result is not None
        assert "_parsing_quality" in result
    
    @pytest.mark.asyncio
    async def test_enhanced_ner_fallback(self):
        """Test Enhanced NER falls back when cross-validation disabled"""
        ner = EnhancedNEREngine(enable_cross_validation=False)
        
        text = "آقای احمد احمدی فرزند محمد"
        result = ner.extract(text)
        
        assert result is not None
        assert "persons" in result
    
    @pytest.mark.asyncio
    async def test_chunker_fallback(self):
        """Test Enhanced Chunker fallback"""
        chunker = EnhancedChunker()
        
        text = "این یک متن تست است. " * 100
        chunks = chunker.chunk_document(
            text=text,
            doc_id="test_doc",
            metadata={}
        )
        
        assert chunks is not None
        assert len(chunks) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestEnhancedPipelineIntegration:
    """Test EnhancedIngestionPipeline end-to-end"""
    
    @pytest.fixture
    def sample_verdict_text(self):
        """Sample verdict text for testing"""
        return """
        رأی دادگاه تجدیدنظر استان تهران شعبه ۵
        
        در خصوص پرونده کلاسه ۱۴۰۲/۱۰/۱۲۳۴
        
        معترض ثالث: آقای احمد احمدی فرزند محمد
        خواندگان: شرکت توسعه فناوری به شماره ثبت ۱۲۳۴۵
        
        خواسته: اعتراض ثالث به عملیات اجرایی و رفع توقیف
        
        دادگاه به استناد ماده ۱۰ قانون مدنی و مواد ۳۴۸ و ۳۵۸ قانون آیین دادرسی مدنی
        رأی به وارد دانستن اعتراض صادر می‌کند.
        
        این رأی قطعی است.
        """
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_ingest_verdict(self, sample_verdict_text):
        """Test enhanced pipeline ingestion of verdict"""
        pipeline = EnhancedIngestionPipeline(
            enable_llm_refinement=False,  # Disable for faster testing
            enable_validation=True
        )
        await pipeline.initialize()
        
        result = await pipeline.ingest_document(
            doc_id="test_verdict_001",
            text=sample_verdict_text,
            metadata={"doc_type": "verdict"}
        )
        
        assert isinstance(result, EnhancedIngestionResult)
        assert result.success is True
        assert result.chunks_created > 0
        assert result.embeddings_created > 0
        assert result.indexed is True
        assert hasattr(result, 'quality_score')
        assert hasattr(result, 'validation_passed')
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_ingest_regular_document(self):
        """Test enhanced pipeline with regular document"""
        pipeline = EnhancedIngestionPipeline()
        await pipeline.initialize()
        
        text = "این یک سند عادی است. " * 50
        result = await pipeline.ingest_document(
            doc_id="test_doc_001",
            text=text,
            metadata={"doc_type": "document"}
        )
        
        assert result.success is True
        assert result.chunks_created > 0
    
    @pytest.mark.asyncio
    async def test_enhanced_pipeline_quality_metrics(self, sample_verdict_text):
        """Test that quality metrics are included"""
        pipeline = EnhancedIngestionPipeline(enable_validation=True)
        await pipeline.initialize()
        
        result = await pipeline.ingest_document(
            doc_id="test_verdict_002",
            text=sample_verdict_text,
            metadata={"doc_type": "verdict"}
        )
        
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
        assert isinstance(result.validation_passed, bool)


class TestBackwardCompatibility:
    """Test backward compatibility with standard pipeline"""
    
    @pytest.mark.asyncio
    async def test_result_compatibility(self):
        """Test EnhancedIngestionResult is compatible with IngestionResult"""
        from mahoun.pipelines.ingestion.pipeline import IngestionResult
        
        # Enhanced result should have all standard fields
        enhanced_result = EnhancedIngestionResult(
            success=True,
            doc_id="test",
            chunks_created=5,
            embeddings_created=5,
            indexed=True,
            processing_time_ms=100.0,
            quality_score=0.9,
            validation_passed=True
        )
        
        # Should be usable as IngestionResult
        assert isinstance(enhanced_result, IngestionResult)
        assert enhanced_result.success is True
        assert enhanced_result.chunks_created == 5
    
    @pytest.mark.asyncio
    async def test_api_compatibility(self):
        """Test API can use both pipelines"""
        from mahoun.pipelines.ingestion import IngestionPipeline, EnhancedIngestionPipeline
        
        # Both should have same interface
        standard = IngestionPipeline()
        enhanced = EnhancedIngestionPipeline()
        
        await standard.initialize()
        await enhanced.initialize()
        
        # Both should have ingest_document method
        assert hasattr(standard, 'ingest_document')
        assert hasattr(enhanced, 'ingest_document')
        
        # Both should return similar results
        text = "Test document"
        standard_result = await standard.ingest_document(
            doc_id="test_std",
            text=text
        )
        enhanced_result = await enhanced.ingest_document(
            doc_id="test_enh",
            text=text
        )
        
        # Both should succeed
        assert standard_result.success
        assert enhanced_result.success


class TestAPIIntegration:
    """Test API integration with enhanced pipeline"""
    
    @pytest.mark.asyncio
    async def test_api_endpoint_with_enhanced(self):
        """Test API endpoint can use enhanced pipeline"""
        # Mock environment variable
        with patch.dict(os.environ, {'USE_ENHANCED_INGESTION': 'true'}):
            # Reload the module to pick up env var
            import importlib
            from api.routers import ingest
            importlib.reload(ingest)
            
            # Get pipeline (should be enhanced if available)
            pipeline = await ingest.get_ingestion_pipeline()
            
            # Pipeline should exist
            assert pipeline is not None
            
            # If enhanced is available, it should be EnhancedIngestionPipeline
            if HAS_ENHANCED:
                # Check if it's enhanced (has quality_score in result)
                result = await pipeline.ingest_document(
                    doc_id="test_api",
                    text="Test text"
                )
                if hasattr(result, 'quality_score'):
                    assert isinstance(result, EnhancedIngestionResult)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformanceComparison:
    """Compare performance between standard and enhanced pipelines"""
    
    @pytest.fixture
    def performance_test_text(self):
        """Sample text for performance testing"""
        return """
        این یک متن تست برای مقایسه عملکرد است. """ * 100
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Performance test - run manually")
    async def test_performance_comparison(self, performance_test_text):
        """Compare processing time between pipelines"""
        from mahoun.pipelines.ingestion import IngestionPipeline, EnhancedIngestionPipeline
        
        # Standard pipeline
        standard = IngestionPipeline()
        await standard.initialize()
        
        start_time = time.time()
        standard_result = await standard.ingest_document(
            doc_id="perf_std",
            text=performance_test_text
        )
        standard_time = time.time() - start_time
        
        # Enhanced pipeline (without LLM for fair comparison)
        enhanced = EnhancedIngestionPipeline(enable_llm_refinement=False)
        await enhanced.initialize()
        
        start_time = time.time()
        enhanced_result = await enhanced.ingest_document(
            doc_id="perf_enh",
            text=performance_test_text
        )
        enhanced_time = time.time() - start_time
        
        # Log results
        print(f"\nPerformance Comparison:")
        print(f"Standard Pipeline: {standard_time:.2f}s")
        print(f"Enhanced Pipeline: {enhanced_time:.2f}s")
        print(f"Difference: {abs(enhanced_time - standard_time):.2f}s")
        
        # Both should succeed
        assert standard_result.success
        assert enhanced_result.success
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Performance test - run manually")
    async def test_llm_call_monitoring(self):
        """Monitor LLM calls in enhanced pipeline"""
        parser = LLMEnhancedParser(enable_refinement=True)
        
        # Mock LLM service to count calls
        call_count = 0
        
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return '{"test": "result"}'
        
        if parser.llm_service:
            parser.llm_service.generate = AsyncMock(side_effect=mock_generate)
        
        text = "Test text for LLM monitoring"
        result = await parser.parse_enhanced(text)
        
        print(f"\nLLM Calls: {call_count}")
        assert call_count >= 0  # Should be 0 if LLM unavailable


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidationAndQuality:
    """Test validation and quality assessment"""
    
    @pytest.fixture
    def sample_verdict_struct(self):
        """Sample verdict structure for validation"""
        return {
            "case_meta": {
                "court_level": "دادگاه تجدیدنظر استان تهران",
                "case_type": "اعتراض ثالث",
                "is_final": True
            },
            "parties": {
                "third_party_objector": {"name": "احمد احمدی"},
                "respondents": []
            },
            "claims": {
                "main": ["رفع توقیف"]
            },
            "legal_references": {
                "substantive_law": ["ماده ۱۰ قانون مدنی"],
                "procedural_law": ["ماده ۳۴۸ آیین دادرسی مدنی"]
            },
            "final_decision": {
                "is_final": True
            },
            "system_tags": ["اعتراض ثالث"]
        }
    
    def test_document_validator(self, sample_verdict_struct):
        """Test DocumentValidator"""
        validator = DocumentValidator(strict_mode=False)
        result = validator.validate_verdict(sample_verdict_struct)
        
        assert result is not None
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'quality_score')
        assert hasattr(result, 'missing_fields')
    
    def test_quality_assessor(self, sample_verdict_struct):
        """Test QualityAssessor"""
        assessor = QualityAssessor()
        metrics = assessor.assess_quality(sample_verdict_struct)
        
        assert metrics is not None
        assert metrics.completeness >= 0.0
        assert metrics.accuracy >= 0.0
        assert metrics.consistency >= 0.0
        assert metrics.overall_score >= 0.0


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in enhanced components"""
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling_empty_text(self):
        """Test pipeline handles empty text gracefully"""
        pipeline = EnhancedIngestionPipeline()
        await pipeline.initialize()
        
        result = await pipeline.ingest_document(
            doc_id="empty_test",
            text="",
            metadata={}
        )
        
        assert result.success is False
        assert result.chunks_created == 0
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling_invalid_metadata(self):
        """Test pipeline handles invalid metadata"""
        pipeline = EnhancedIngestionPipeline()
        await pipeline.initialize()
        
        result = await pipeline.ingest_document(
            doc_id="invalid_meta_test",
            text="Test text",
            metadata={"invalid": "data"}
        )
        
        # Should still process (metadata validation is lenient)
        assert result is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

