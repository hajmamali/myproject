"""
Simple Fine-Tuning Tests
=========================
Basic unit tests for fine-tuning components without complex integration.
"""

import pytest
from datetime import datetime

from mahoun.finetuning.feedback_pipeline import (
    FeedbackPipeline,
    UserFeedback,
    FeedbackType,
)


def test_feedback_pipeline_creation():
    """Test creating a feedback pipeline"""
    pipeline = FeedbackPipeline(
        min_rating=4.0,
        min_quality_score=0.7
    )
    
    assert pipeline.min_rating == 4.0
    assert pipeline.min_quality_score == 0.7
    assert len(pipeline.feedback_store) == 0


def test_add_feedback():
    """Test adding feedback to pipeline"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="test_001",
        user_id="user_001",
        query="Test query",
        response="Test response",
        feedback_type=FeedbackType.RATING,
        rating=5.0
    )
    
    pipeline.add_feedback(feedback)
    
    assert len(pipeline.feedback_store) == 1
    assert pipeline.feedback_store[0].feedback_id == "test_001"


def test_quality_score_high():
    """Test quality score calculation for high-quality feedback"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="hq_001",
        user_id="user_hq",
        query="High quality",
        response="High quality response",
        feedback_type=FeedbackType.CORRECTION,
        rating=5.0,
        response_time_ms=1000,
        confidence_score=0.95
    )
    
    score = pipeline._calculate_quality_score(feedback)
    assert score >= 0.8


def test_quality_score_low():
    """Test quality score calculation for low-quality feedback"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="lq_001",
        user_id="user_lq",
        query="Low quality",
        response="Low quality response",
        feedback_type=FeedbackType.RATING,
        rating=2.0,
        response_time_ms=10000,
        confidence_score=0.3
    )
    
    score = pipeline._calculate_quality_score(feedback)
    assert score <= 0.7  # Should be at or below threshold


def test_collect_empty_feedback():
    """Test collecting from empty pipeline"""
    pipeline = FeedbackPipeline()
    
    collected = pipeline.collect_feedback()
    assert len(collected) == 0


def test_collect_with_rating_filter():
    """Test collecting feedback with rating filter"""
    pipeline = FeedbackPipeline()
    
    # Add high-rated feedback
    feedback1 = UserFeedback(
        feedback_id="fb_high",
        user_id="user_1",
        query="Query 1",
        response="Response 1",
        feedback_type=FeedbackType.RATING,
        rating=5.0
    )
    pipeline.add_feedback(feedback1)
    
    # Add low-rated feedback
    feedback2 = UserFeedback(
        feedback_id="fb_low",
        user_id="user_2",
        query="Query 2",
        response="Response 2",
        feedback_type=FeedbackType.RATING,
        rating=2.0
    )
    pipeline.add_feedback(feedback2)
    
    # Collect with min_rating=4.0
    collected = pipeline.collect_feedback(min_rating=4.0)
    
    assert len(collected) == 1
    assert collected[0].feedback_id == "fb_high"


def test_convert_rating_feedback():
    """Test converting rating feedback to training example"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="fb_rating",
        user_id="user_rating",
        query="What is AI?",
        response="AI is artificial intelligence",
        feedback_type=FeedbackType.RATING,
        rating=5.0,
        confidence_score=0.9
    )
    
    examples = pipeline.convert_to_training_examples([feedback])
    
    assert len(examples) == 1
    assert examples[0].input_text == "What is AI?"
    assert examples[0].target_text == "AI is artificial intelligence"
    assert examples[0].source == "rating"


def test_convert_correction_feedback():
    """Test converting correction feedback to training example"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="fb_correction",
        user_id="user_correction",
        query="What is ML?",
        response="ML is something",
        feedback_type=FeedbackType.CORRECTION,
        corrected_response="ML is machine learning, a subset of AI",
        confidence_score=0.9
    )
    
    examples = pipeline.convert_to_training_examples([feedback])
    
    assert len(examples) == 1
    assert examples[0].input_text == "What is ML?"
    assert examples[0].target_text == "ML is machine learning, a subset of AI"
    assert examples[0].source == "correction"
    assert examples[0].weight == 1.5  # Corrections have higher weight


def test_convert_preference_feedback():
    """Test converting preference feedback to training example"""
    pipeline = FeedbackPipeline()
    
    feedback = UserFeedback(
        feedback_id="fb_pref",
        user_id="user_pref",
        query="Explain NLP",
        response="Response A",
        feedback_type=FeedbackType.PREFERENCE,
        preferred_response="NLP is natural language processing",
        rejected_response="Response A",
        confidence_score=0.9
    )
    
    examples = pipeline.convert_to_training_examples([feedback])
    
    assert len(examples) == 1
    assert examples[0].target_text == "NLP is natural language processing"
    assert examples[0].source == "preference"


def test_filter_low_quality():
    """Test that low-quality feedback is filtered out"""
    pipeline = FeedbackPipeline(min_quality_score=0.7)
    
    # Low quality feedback
    feedback = UserFeedback(
        feedback_id="fb_low_quality",
        user_id="user_lq",
        query="Test",
        response="Test",
        feedback_type=FeedbackType.RATING,
        rating=2.0,
        response_time_ms=10000,
        confidence_score=0.2
    )
    
    examples = pipeline.convert_to_training_examples([feedback])
    
    # Should be filtered out
    assert len(examples) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
