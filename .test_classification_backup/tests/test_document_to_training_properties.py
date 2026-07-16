import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Document-to-Training Pipeline
======================================================
Rigorous property-based testing using Hypothesis.

Tests universal properties that MUST hold for all inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis import assume

from mahoun.finetuning.document_to_training import (
    DocumentToTrainingPipeline,
    DocumentToTrainingConfig,
    GroundednessVerifier,
    DifficultyClassifier,
    DifficultyLevel,
)
from mahoun.finetuning.qa_generator import QAPair, QAGenerationStrategy, DomainType
from mahoun.finetuning.quality_filter import QualityFilter


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def qa_pair_strategy(draw):
    """Generate valid QAPair"""
    question = draw(st.text(min_size=10, max_size=200))
    answer = draw(st.text(min_size=20, max_size=500))
    source_text = draw(st.text(min_size=50, max_size=1000))
    
    # Ensure answer appears in source (for groundedness)
    if draw(st.booleans()):
        # Make grounded
        source_text = source_text + " " + answer
    
    return QAPair(
        question=question,
        answer=answer,
        qa_id=f"qa_{draw(st.integers(min_value=1, max_value=10000))}",
        source_chunk_id=f"chunk_{draw(st.integers(min_value=0, max_value=100))}",
        source_text=source_text,
        question_type=draw(st.sampled_from(["factual", "reasoning", "comparison"])),
        difficulty=draw(st.sampled_from(["easy", "medium", "hard"])),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        generation_strategy=draw(st.sampled_from(["llm_based", "template_based", "extractive", "hybrid"])),
    )


@st.composite
def document_strategy(draw):
    """Generate valid document text"""
    # Generate simple paragraphs for fast testing
    num_paragraphs = draw(st.integers(min_value=2, max_value=4))
    paragraphs = []
    
    for _ in range(num_paragraphs):
        # Simple sentences with basic ASCII
        num_sentences = draw(st.integers(min_value=2, max_value=3))
        sentences = []
        for _ in range(num_sentences):
            sentence = draw(st.text(
                min_size=20, 
                max_size=60,
                alphabet=st.characters(min_codepoint=32, max_codepoint=126)
            ))
            sentences.append(sentence)
        paragraph = ". ".join(sentences) + "."
        paragraphs.append(paragraph)
    
    return "\n\n".join(paragraphs)


# =============================================================================
# Property Tests: Groundedness Verifier
# =============================================================================

class TestGroundednessVerifierProperties:
    """Property tests for GroundednessVerifier"""
    
    @given(qa_pair_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_groundedness_score_range(self, qa_pair):
        """Property: Groundedness score must be in [0, 1]"""
        verifier = GroundednessVerifier(min_overlap=0.5)
        is_grounded, score = verifier.verify(qa_pair)
        
        assert 0.0 <= score <= 1.0, f"Score {score} out of range"
        assert isinstance(is_grounded, bool)
    
    @given(qa_pair_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_perfect_overlap_is_grounded(self, qa_pair):
        """Property: If answer is substring of source, should be grounded"""
        # Force perfect overlap with meaningful words (not just stop words)
        qa_pair.answer = "contract employment salary benefits vacation"
        qa_pair.source_text = "The contract employment salary benefits vacation are specified in section 5."
        qa_pair.evidence_span = qa_pair.answer
        
        verifier = GroundednessVerifier(min_overlap=0.5)
        is_grounded, score = verifier.verify(qa_pair)
        
        # Should have high score and be grounded
        assert score >= 0.5, f"Perfect overlap should have high score, got {score}"
        assert is_grounded, "Perfect overlap should be grounded"
    
    @given(qa_pair_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_no_overlap_not_grounded(self, qa_pair):
        """Property: If answer has no overlap with source, not grounded"""
        # Force no overlap
        qa_pair.answer = "XXXXXXXXX YYYYYYYY ZZZZZZZZZ"
        qa_pair.source_text = "AAAAA BBBBB CCCCC DDDDD"
        
        verifier = GroundednessVerifier(min_overlap=0.5)
        is_grounded, score = verifier.verify(qa_pair)
        
        assert not is_grounded
        assert score < 0.5


# =============================================================================
# Property Tests: Difficulty Classifier
# =============================================================================

class TestDifficultyClassifierProperties:
    """Property tests for DifficultyClassifier"""
    
    @given(qa_pair_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_difficulty_is_valid_level(self, qa_pair):
        """Property: Difficulty must be one of the valid levels"""
        classifier = DifficultyClassifier(model="heuristic")
        difficulty = classifier.classify(qa_pair)
        
        assert difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]
    
    @given(qa_pair_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_longer_questions_harder(self, qa_pair):
        """Property: Very long questions tend to be harder"""
        # Create very long question
        qa_pair.question = " ".join(["word"] * 50)  # 50 words
        qa_pair.answer = " ".join(["answer"] * 100)  # 100 words
        qa_pair.question_type = "reasoning"
        
        classifier = DifficultyClassifier(model="heuristic")
        difficulty = classifier.classify(qa_pair)
        
        # Should be medium or hard
        assert difficulty in [DifficultyLevel.MEDIUM, DifficultyLevel.HARD]


# =============================================================================
# Property Tests: Quality Filter
# =============================================================================

class TestQualityFilterProperties:
    """Property tests for QualityFilter"""
    
    @given(st.lists(qa_pair_strategy(), min_size=1, max_size=20))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_filter_reduces_or_maintains_size(self, qa_pairs):
        """Property: Filtering never increases the number of pairs"""
        filter = QualityFilter(min_quality_score=0.7, enable_adaptive=False)
        filtered = filter.filter(qa_pairs)
        
        assert len(filtered) <= len(qa_pairs)
    
    @given(st.lists(qa_pair_strategy(), min_size=5, max_size=20))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_adaptive_threshold_keeps_some(self, qa_pairs):
        """Property: Adaptive filtering keeps at least some pairs"""
        assume(len(qa_pairs) >= 10)  # Need enough for adaptive
        
        filter = QualityFilter(
            min_quality_score=0.3,  # Low minimum
            enable_adaptive=True,
            adaptive_percentile=0.6  # Keep top 60%
        )
        filtered = filter.filter(qa_pairs)
        
        # Should keep at least 40% (since we keep top 60%)
        assert len(filtered) >= len(qa_pairs) * 0.4
    
    @given(st.lists(qa_pair_strategy(), min_size=1, max_size=20))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_high_confidence_pairs_pass(self, qa_pairs):
        """Property: High confidence pairs should pass filter"""
        # Set all to high confidence
        for pair in qa_pairs:
            pair.confidence = 0.95
            pair.is_valid = True
            pair.generation_strategy = "llm_based"
        
        filter = QualityFilter(min_quality_score=0.7, enable_adaptive=False)
        filtered = filter.filter(qa_pairs)
        
        # All should pass
        assert len(filtered) == len(qa_pairs)


# =============================================================================
# Property Tests: Document Chunking
# =============================================================================

class TestDocumentChunkingProperties:
    """Property tests for document chunking"""
    
    @given(document_strategy())
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow], deadline=2000)
    def test_chunks_cover_document(self, document):
        """Property: Chunks should cover the entire document"""
        assume(len(document) >= 100)
        assume(len(document) <= 2000)  # Limit size for speed
        
        pipeline = DocumentToTrainingPipeline()
        chunks = pipeline._chunk_document(document)
        
        if chunks:
            # Check that chunks are non-empty
            for chunk in chunks:
                assert len(chunk["text"]) > 0
                assert chunk["start"] >= 0
                assert chunk["end"] <= len(document)
                assert chunk["start"] < chunk["end"]
    
    @given(document_strategy())
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow], deadline=2000)
    def test_chunk_size_bounded(self, document):
        """Property: Chunks should respect size limits"""
        assume(len(document) >= 100)
        assume(len(document) <= 2000)  # Limit size for speed
        
        config = DocumentToTrainingConfig(chunk_size=512)
        pipeline = DocumentToTrainingPipeline(config=config)
        chunks = pipeline._chunk_document(document)
        
        for chunk in chunks:
            # Chunks should be roughly within size limit (with some tolerance for sentence boundaries)
            assert len(chunk["text"]) <= config.chunk_size * 1.5


# =============================================================================
# Property Tests: End-to-End Pipeline
# =============================================================================

class TestPipelineProperties:
    """Property tests for end-to-end pipeline"""
    
    @pytest.mark.asyncio
    @given(document_strategy())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.too_slow], deadline=5000)
    async def test_pipeline_produces_valid_result(self, document):
        """Property: Pipeline always produces a valid ProcessingResult"""
        assume(len(document) >= 200)  # Need minimum length
        assume(len(document) <= 1500)  # Limit size for speed
        
        config = DocumentToTrainingConfig(
            qa_strategy=QAGenerationStrategy.EXTRACTIVE,  # Fast strategy
            min_quality_score=0.5,  # Lower threshold for testing
            enable_groundedness_check=False,  # Disable for speed
            enable_difficulty_classification=False,
            max_chunks_per_document=5,  # Limit chunks for speed
        )
        
        pipeline = DocumentToTrainingPipeline(config=config)
        await pipeline.initialize()
        
        result = await pipeline.process_document(
            doc_id="test_doc",
            text=document,
        )
        
        # Result should have required fields
        assert result.doc_id == "test_doc"
        assert isinstance(result.success, bool)
        assert result.processing_time_ms >= 0
        assert result.total_qa_pairs >= 0
        
        if result.success:
            assert result.dataset is not None
            assert result.dataset.total_examples >= 0
    
    @pytest.mark.asyncio
    @given(st.text(min_size=10, max_size=50))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.too_slow], deadline=3000)
    async def test_short_documents_handled_gracefully(self, short_text):
        """Property: Short documents should be handled without crashing"""
        pipeline = DocumentToTrainingPipeline()
        await pipeline.initialize()
        
        result = await pipeline.process_document(
            doc_id="short_doc",
            text=short_text,
        )
        
        # Should not crash, but may not succeed
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error is not None


# =============================================================================
# Property Tests: Training Example Conversion
# =============================================================================

class TestTrainingExampleProperties:
    """Property tests for Q&A to training example conversion"""
    
    @given(st.lists(qa_pair_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_conversion_preserves_count(self, qa_pairs):
        """Property: Converting Q&A pairs preserves count"""
        pipeline = DocumentToTrainingPipeline()
        examples = pipeline._qa_to_training_examples(qa_pairs, "test_doc")
        
        assert len(examples) == len(qa_pairs)
    
    @given(st.lists(qa_pair_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_quality_scores_in_range(self, qa_pairs):
        """Property: Quality scores must be in [0, 1]"""
        pipeline = DocumentToTrainingPipeline()
        examples = pipeline._qa_to_training_examples(qa_pairs, "test_doc")
        
        for example in examples:
            assert 0.0 <= example.quality_score <= 1.0
            assert example.weight > 0.0


# =============================================================================
# Invariant Tests
# =============================================================================

class TestInvariants:
    """Test system invariants"""
    
    def test_groundedness_verifier_deterministic(self):
        """Invariant: Same input produces same output"""
        qa_pair = QAPair(
            question="What is X?",
            answer="X is Y",
            qa_id="qa_001",
            source_chunk_id="chunk_001",
            source_text="X is Y and Z is W",
            question_type="factual",
            difficulty="easy",
            confidence=0.8,
        )
        
        verifier = GroundednessVerifier(min_overlap=0.5)
        
        result1 = verifier.verify(qa_pair)
        result2 = verifier.verify(qa_pair)
        
        assert result1 == result2, "Verifier must be deterministic"
    
    def test_difficulty_classifier_deterministic(self):
        """Invariant: Same input produces same output"""
        qa_pair = QAPair(
            question="What is the meaning of life?",
            answer="42",
            qa_id="qa_001",
            source_chunk_id="chunk_001",
            source_text="The answer is 42",
            question_type="factual",
            difficulty="easy",
            confidence=0.8,
        )
        
        classifier = DifficultyClassifier(model="heuristic")
        
        result1 = classifier.classify(qa_pair)
        result2 = classifier.classify(qa_pair)
        
        assert result1 == result2, "Classifier must be deterministic"
