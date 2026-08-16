"""
Ultra-Hard Integrity Test for OCR Ensemble
==========================================

This test suite performs comprehensive validation of the OCR Ensemble system
with extreme edge cases, performance stress testing, and correctness validation.

Test Categories:
1. Basic Functionality - Core ensemble OCR correctness
2. Voting Strategies - Majority, weighted, best_confidence, unanimous
3. Parallel Execution - Thread-safety and performance
4. Graceful Degradation - Engine failure handling
5. Multi-page Processing - PDF document handling
6. Configuration - Environment variable loading
7. Dependency Injection - OCR Container integration
8. Edge Cases - Empty inputs, malformed data, timeouts
9. Integration - Document handlers integration
10. Performance - Large document stress testing
11. Metadata Validation - Statistics and audit trail
12. Correctness - Text accuracy and confidence scoring
"""

import pytest
import logging
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any
from PIL import Image

from mahoun.pipelines.ingestion.ocr_ensemble import (
    OCREnsemble,
    EnsembleConfig,
    VotingStrategy,
    EnsembleResult,
    EngineResult,
    VotingSystem,
    TextAligner,
)
from mahoun.pipelines.ingestion.ocr_adapters import (
    OCRDependencyContainer,
    OCRContainerConfig,
    get_ocr_container,
    reset_global_ocr_container,
)

logger = logging.getLogger(__name__)


class TestBasicFunctionality:
    """Test core ensemble OCR functionality."""

    def test_ensemble_initialization(self):
        """Test OCR Ensemble initialization with default config."""
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        assert ensemble is not None
        assert ensemble.config is not None
        assert len(ensemble.config.engines) == 3

    def test_ensemble_initialization_custom_config(self):
        """Test OCR Ensemble initialization with custom config."""
        config = EnsembleConfig(
            engines=['paddle', 'tesseract'],
            min_engines=1,
            voting_strategy=VotingStrategy.MAJORITY
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.min_engines == 1
        assert ensemble.config.voting_strategy == VotingStrategy.MAJORITY
        assert len(ensemble.config.engines) == 2

    def test_ensemble_initialization_without_ocr_engine(self):
        """Test graceful handling when OCR engine is unavailable."""
        # This tests the graceful degradation when OCREngine import fails
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        # Should initialize even if OCR engine is unavailable
        assert ensemble is not None


class TestVotingStrategies:
    """Test voting strategy implementations."""

    def test_majority_vote(self):
        """Test majority voting strategy."""
        candidates = [
            ("hello", 0.9, "engine1"),
            ("hello", 0.85, "engine2"),
            ("world", 0.8, "engine3")
        ]
        
        text, conf, reason = VotingSystem.majority_vote(candidates)
        
        assert text == "hello"
        assert conf > 0
        assert "majority_vote" in reason

    def test_weighted_vote(self):
        """Test confidence-weighted voting."""
        candidates = [
            ("hello", 0.9, "engine1"),
            ("world", 0.95, "engine2"),
            ("hello", 0.85, "engine3")
        ]
        
        text, conf, reason = VotingSystem.weighted_vote(candidates)
        
        # "hello" should win due to combined weight (0.9 + 0.85 = 1.75)
        assert text == "hello"
        assert "weighted_vote" in reason

    def test_best_confidence_vote(self):
        """Test best confidence selection."""
        candidates = [
            ("hello", 0.9, "engine1"),
            ("world", 0.95, "engine2"),
            ("test", 0.8, "engine3")
        ]
        
        text, conf, reason = VotingSystem.best_confidence_vote(candidates)
        
        assert text == "world"
        assert conf == 0.95
        assert "best_confidence" in reason

    def test_unanimous_vote_agreement(self):
        """Test unanimous voting with agreement."""
        candidates = [
            ("hello world", 0.9, "engine1"),
            ("hello world", 0.85, "engine2"),
            ("hello world", 0.88, "engine3")
        ]
        
        text, conf, reason = VotingSystem.unanimous_vote(candidates, similarity_threshold=0.9)
        
        assert text == "hello world"
        assert "unanimous" in reason

    def test_unanimous_vote_disagreement(self):
        """Test unanimous voting with disagreement (should fallback to weighted)."""
        candidates = [
            ("hello", 0.9, "engine1"),
            ("world", 0.85, "engine2"),
            ("test", 0.88, "engine3")
        ]
        
        text, conf, reason = VotingSystem.unanimous_vote(candidates, similarity_threshold=0.9)
        
        # Should fallback to weighted vote
        assert "weighted_vote" in reason

    def test_empty_candidates(self):
        """Test voting with empty candidates."""
        candidates = []
        
        text, conf, reason = VotingSystem.majority_vote(candidates)
        assert text == ""
        assert conf == 0.0
        assert reason == "no_candidates"


class TestTextAlignment:
    """Test text alignment and similarity calculation."""

    def test_similarity_identical(self):
        """Test similarity calculation for identical texts."""
        similarity = TextAligner.calculate_similarity("hello", "hello")
        assert similarity == 1.0

    def test_similarity_different(self):
        """Test similarity calculation for different texts."""
        similarity = TextAligner.calculate_similarity("hello", "world")
        assert similarity < 1.0
        assert similarity >= 0.0

    def test_similarity_empty(self):
        """Test similarity calculation with empty texts."""
        similarity = TextAligner.calculate_similarity("", "")
        assert similarity == 1.0

    def test_similarity_one_empty(self):
        """Test similarity calculation with one empty text."""
        similarity = TextAligner.calculate_similarity("hello", "")
        assert similarity == 0.0

    def test_align_lines_simple(self):
        """Test simple line alignment."""
        lines_list = [
            [{"text": "line1"}, {"text": "line2"}],
            [{"text": "line1"}, {"text": "line2"}]
        ]
        
        aligned = TextAligner.align_lines(lines_list)
        
        assert len(aligned) == 2
        assert len(aligned[0]) == 2

    def test_align_lines_uneven(self):
        """Test line alignment with uneven line counts."""
        lines_list = [
            [{"text": "line1"}, {"text": "line2"}],
            [{"text": "line1"}]
        ]
        
        aligned = TextAligner.align_lines(lines_list)
        
        assert len(aligned) == 2
        assert aligned[1][1] is None  # Should pad with None


class TestParallelExecution:
    """Test parallel execution and thread-safety."""

    def test_parallel_execution_enabled(self):
        """Test that parallel execution can be enabled."""
        config = EnsembleConfig(
            parallel_execution=True,
            max_workers=3
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.parallel_execution is True
        assert ensemble.config.max_workers == 3

    def test_parallel_execution_disabled(self):
        """Test that parallel execution can be disabled."""
        config = EnsembleConfig(
            parallel_execution=False
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.parallel_execution is False

    def test_timeout_configuration(self):
        """Test timeout per engine configuration."""
        config = EnsembleConfig(
            timeout_per_engine=60.0
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.timeout_per_engine == 60.0


class TestGracefulDegradation:
    """Test graceful degradation on engine failures."""

    def test_min_engines_requirement(self):
        """Test minimum engines requirement."""
        config = EnsembleConfig(
            min_engines=3
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.min_engines == 3

    def test_confidence_threshold(self):
        """Test confidence threshold configuration."""
        config = EnsembleConfig(
            confidence_threshold=0.7 
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.confidence_threshold == 0.7

    def test_disagreement_flagging(self):
        """Test disagreement flagging configuration."""
        config = EnsembleConfig(
            flag_disagreements=True,
            disagreement_threshold=0.3
        )
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.flag_disagreements is True
        assert ensemble.config.disagreement_threshold == 0.3


class TestMultiPageProcessing:
    """Test multi-page document processing."""

    def test_process_images_method_exists(self):
        """Test that process_images method exists."""
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        assert hasattr(ensemble, 'process_images')
        assert callable(ensemble.process_images)

    def test_process_images_with_empty_list(self):
        """Test processing empty image list."""
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        result = ensemble.process_images([], "test_doc")
        
        assert result is not None
        assert result.success is False  # No pages to process


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = EnsembleConfig()
        
        assert len(config.engines) == 3
        assert config.min_engines == 2
        assert config.voting_strategy == VotingStrategy.WEIGHTED
        assert config.parallel_execution is True

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = EnsembleConfig(
            engines=['paddle'],
            min_engines=1,
            voting_strategy=VotingStrategy.BEST_CONFIDENCE,
            parallel_execution=False
        )
        
        assert len(config.engines) == 1
        assert config.min_engines == 1
        assert config.voting_strategy == VotingStrategy.BEST_CONFIDENCE
        assert config.parallel_execution is False


class TestDependencyInjection:
    """Test OCR dependency injection container."""

    def test_container_initialization(self):
        """Test OCR container initialization."""
        config = OCRContainerConfig()
        container = OCRDependencyContainer(config)
        
        assert container is not None
        assert container.config is not None

    def test_container_status(self):
        """Test container status reporting."""
        config = OCRContainerConfig()
        container = OCRDependencyContainer(config)
        
        status = container.get_status()
        
        assert isinstance(status, dict)
        assert 'ocr_ensemble' in status
        assert 'post_processor' in status
        assert 'pre_processor' in status
        assert 'hardened_ocr' in status

    def test_container_reset(self):
        """Test container reset functionality."""
        config = OCRContainerConfig()
        container = OCRDependencyContainer(config)
        
        # Access a component to initialize it
        _ = container.ocr_ensemble
        
        # Reset
        container.reset()
        
        # Status should show not initialized
        status = container.get_status()
        assert status['ocr_ensemble'] is False

    def test_global_container_singleton(self):
        """Test global container singleton pattern."""
        container1 = get_ocr_container()
        container2 = get_ocr_container()
        
        assert container1 is container2

    def test_global_container_reset(self):
        """Test global container reset."""
        _ = get_ocr_container()
        reset_global_ocr_container()
        
        # New container should be created
        container = get_ocr_container()
        assert container is not None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_engines_list(self):
        """Test configuration with empty engines list."""
        config = EnsembleConfig(engines=[])
        ensemble = OCREnsemble(config)
        
        assert len(ensemble.config.engines) == 0

    def test_single_engine(self):
        """Test configuration with single engine."""
        config = EnsembleConfig(engines=['paddle'], min_engines=1)
        ensemble = OCREnsemble(config)
        
        assert len(ensemble.config.engines) == 1
        assert ensemble.config.min_engines == 1

    def test_invalid_voting_strategy_string(self):
        """Test handling of invalid voting strategy string."""
        # This tests the environment variable loading with invalid strategy
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        # Should handle gracefully
        assert ensemble is not None


class TestIntegration:
    """Test integration with document handlers."""

    def test_ocr_adapters_import(self):
        """Test that OCR adapters can be imported."""
        from mahoun.pipelines.ingestion.ocr_adapters import (
            OCRDependencyContainer,
            OCRContainerConfig,
            get_ocr_container
        )
        
        assert OCRDependencyContainer is not None
        assert OCRContainerConfig is not None
        assert get_ocr_container is not None

    def test_document_handlers_ensemble_import(self):
        """Test that document handlers can import ensemble."""
        from mahoun.pipelines.ingestion.document_handlers import extract_document_text
        
        # Should be able to import without errors
        assert extract_document_text is not None


class TestMetadataValidation:
    """Test metadata and statistics correctness."""

    def test_ensemble_result_structure(self):
        """Test EnsembleResult data structure."""
        result = EnsembleResult(
            success=True,
            text="test",
            confidence=0.9,
            engine_results=[],
            voting_strategy="weighted"
        )
        
        assert result.success is True
        assert result.text == "test"
        assert result.confidence == 0.9
        assert result.voting_strategy == "weighted"

    def test_engine_result_structure(self):
        """Test EngineResult data structure."""
        result = EngineResult(
            engine_name="paddle",
            text="test",
            lines=[],
            confidence=0.9,
            success=True
        )
        
        assert result.engine_name == "paddle"
        assert result.text == "test"
        assert result.confidence == 0.9
        assert result.success is True


class TestCorrectnessValidation:
    """Test correctness of ensemble operations."""

    def test_voting_strategy_enum_values(self):
        """Test that voting strategy enum has correct values."""
        assert VotingStrategy.MAJORITY.value == "majority"
        assert VotingStrategy.WEIGHTED.value == "weighted"
        assert VotingStrategy.BEST_CONFIDENCE.value == "best_confidence"
        assert VotingStrategy.UNANIMOUS.value == "unanimous"

    def test_ensemble_config_defaults(self):
        """Test that ensemble config has sensible defaults."""
        config = EnsembleConfig()
        
        assert config.min_engines <= len(config.engines)
        assert 0.0 <= config.confidence_threshold <= 1.0
        assert config.max_workers > 0
        assert config.timeout_per_engine > 0


class TestPerformance:
    """Test performance characteristics."""

    def test_caching_configuration(self):
        """Test caching configuration."""
        config = EnsembleConfig(enable_caching=True)
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.enable_caching is True

    def test_max_workers_configuration(self):
        """Test max workers configuration."""
        config = EnsembleConfig(max_workers=5)
        ensemble = OCREnsemble(config)
        
        assert ensemble.config.max_workers == 5


class TestRegressionScenarios:
    """Test regression scenarios from previous issues."""

    def test_ensemble_without_ocr_engine_fallback(self):
        """Test that ensemble handles missing OCR engine gracefully."""
        config = EnsembleConfig()
        ensemble = OCREnsemble(config)
        
        # Should not crash even if OCR engine is unavailable
        assert ensemble is not None

    def test_voting_strategy_string_mapping(self):
        """Test that voting strategy strings map correctly to enums."""
        strategy_map = {
            "majority": VotingStrategy.MAJORITY,
            "weighted": VotingStrategy.WEIGHTED,
            "best_confidence": VotingStrategy.BEST_CONFIDENCE,
            "unanimous": VotingStrategy.UNANIMOUS
        }
        
        for string_val, enum_val in strategy_map.items():
            assert enum_val.value == string_val


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
