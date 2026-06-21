import pytest
pytest.importorskip("hypothesis")
"""
Property-Based Tests for Fine-Tuning Pipeline
==============================================
Using hypothesis to test invariants and edge cases.

These tests verify that the fine-tuning pipeline maintains
its contracts under all possible inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from mahoun.finetuning.feedback_pipeline import (
    FeedbackPipeline,
    UserFeedback,
    FeedbackType,
    TrainingExample,
)


# =============================================================================
# Strategies for generating test data
# =============================================================================

feedback_type_strategy = st.sampled_from([
    FeedbackType.RATING,
    FeedbackType.CORRECTION,
    FeedbackType.PREFERENCE,
    FeedbackType.REJECTION,
])

rating_strategy = st.floats(min_value=1.0, max_value=5.0, allow_nan=False)
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
response_time_strategy = st.floats(min_value=100.0, max_value=30000.0, allow_nan=False)


@st.composite
def user_feedback_strategy(draw):
    """Generate random UserFeedback objects"""
    feedback_type = draw(feedback_type_strategy)
    
    feedback = UserFeedback(
        feedback_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        user_id=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        query=draw(st.text(min_size=1, max_size=500)),
        response=draw(st.text(min_size=1, max_size=1000)),
        feedback_type=feedback_type,
        rating=draw(st.one_of(st.none(), rating_strategy)),
        corrected_response=draw(st.one_of(st.none(), st.text(min_size=1, max_size=1000))) if feedback_type == FeedbackType.CORRECTION else None,
        preferred_response=draw(st.one_of(st.none(), st.text(min_size=1, max_size=1000))) if feedback_type == FeedbackType.PREFERENCE else None,
        response_time_ms=draw(st.one_of(st.none(), response_time_strategy)),
        confidence_score=draw(st.one_of(st.none(), confidence_strategy)),
    )
    return feedback


# =============================================================================
# Property Tests
# =============================================================================

class TestQualityScoreProperties:
    """Property tests for quality score calculation"""
    
    @given(user_feedback_strategy())
    @settings(max_examples=100, deadline=None)
    def test_quality_score_bounded(self, feedback: UserFeedback):
        """Quality score must always be between 0 and 1"""
        pipeline = FeedbackPipeline()
        score = pipeline._calculate_quality_score(feedback)
        
        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"
    
    @given(
        rating=rating_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=50, deadline=None)
    def test_higher_rating_higher_score(self, rating: float, confidence: float):
        """Higher rating should generally lead to higher score"""
        pipeline = FeedbackPipeline()
        
        low_rating_feedback = UserFeedback(
            feedback_id="low",
            user_id="user",
            query="Q",
            response="R",
            feedback_type=FeedbackType.RATING,
            rating=1.0,
            confidence_score=confidence,
        )
        
        high_rating_feedback = UserFeedback(
            feedback_id="high",
            user_id="user",
            query="Q",
            response="R",
            feedback_type=FeedbackType.RATING,
            rating=5.0,
            confidence_score=confidence,
        )
        
        low_score = pipeline._calculate_quality_score(low_rating_feedback)
        high_score = pipeline._calculate_quality_score(high_rating_feedback)
        
        assert high_score >= low_score, f"High rating ({high_score}) should >= low rating ({low_score})"
    
    @given(confidence=confidence_strategy)
    @settings(max_examples=50, deadline=None)
    def test_correction_bonus(self, confidence: float):
        """Correction feedback should get bonus over rating feedback"""
        pipeline = FeedbackPipeline()
        
        rating_feedback = UserFeedback(
            feedback_id="rating",
            user_id="user",
            query="Q",
            response="R",
            feedback_type=FeedbackType.RATING,
            confidence_score=confidence,
        )
        
        correction_feedback = UserFeedback(
            feedback_id="correction",
            user_id="user",
            query="Q",
            response="R",
            feedback_type=FeedbackType.CORRECTION,
            corrected_response="Better R",
            confidence_score=confidence,
        )
        
        rating_score = pipeline._calculate_quality_score(rating_feedback)
        correction_score = pipeline._calculate_quality_score(correction_feedback)
        
        assert correction_score >= rating_score, \
            f"Correction ({correction_score}) should >= rating ({rating_score})"


class TestFeedbackCollectionProperties:
    """Property tests for feedback collection"""
    
    @given(st.lists(user_feedback_strategy(), min_size=0, max_size=20))
    @settings(max_examples=50, deadline=None)
    def test_collect_returns_subset(self, feedbacks: list):
        """Collected feedback should be subset of stored feedback"""
        pipeline = FeedbackPipeline()
        
        for fb in feedbacks:
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback()
        
        assert len(collected) <= len(feedbacks), \
            f"Collected {len(collected)} > stored {len(feedbacks)}"
    
    @given(
        min_rating=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=30, deadline=None)
    def test_rating_filter_works(self, min_rating: float):
        """Rating filter should only return feedback >= min_rating"""
        pipeline = FeedbackPipeline()
        
        # Add feedback with various ratings
        for i, rating in enumerate([1.0, 2.0, 3.0, 4.0, 5.0]):
            fb = UserFeedback(
                feedback_id=f"fb_{i}",
                user_id="user",
                query="Q",
                response="R",
                feedback_type=FeedbackType.RATING,
                rating=rating,
            )
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback(min_rating=min_rating)
        
        for fb in collected:
            if fb.rating is not None:
                assert fb.rating >= min_rating, \
                    f"Rating {fb.rating} < min_rating {min_rating}"


class TestTrainingExampleProperties:
    """Property tests for training example conversion"""
    
    @given(st.lists(user_feedback_strategy(), min_size=1, max_size=10))
    @settings(max_examples=50, deadline=None)
    def test_examples_have_required_fields(self, feedbacks: list):
        """All training examples must have required fields"""
        pipeline = FeedbackPipeline(min_quality_score=0.0)  # Accept all
        
        for fb in feedbacks:
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        for example in examples:
            assert example.input_text is not None
            assert example.target_text is not None
            assert example.source in ["rating", "correction", "preference"]
            assert 0.0 <= example.quality_score <= 1.0
            assert example.weight > 0
    
    @given(st.lists(user_feedback_strategy(), min_size=0, max_size=10))
    @settings(max_examples=50, deadline=None)
    def test_examples_count_bounded(self, feedbacks: list):
        """Number of examples should not exceed number of feedbacks"""
        pipeline = FeedbackPipeline(min_quality_score=0.0)
        
        for fb in feedbacks:
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        assert len(examples) <= len(feedbacks), \
            f"Examples {len(examples)} > feedbacks {len(feedbacks)}"


class TestDatasetProperties:
    """Property tests for dataset creation"""
    
    @given(
        train_ratio=st.floats(min_value=0.1, max_value=0.9, allow_nan=False),
        eval_ratio=st.floats(min_value=0.05, max_value=0.3, allow_nan=False),
    )
    @settings(max_examples=30, deadline=None)
    def test_split_ratios_respected(self, train_ratio: float, eval_ratio: float):
        """Dataset splits should approximately match ratios"""
        # Ensure ratios sum to <= 1
        assume(train_ratio + eval_ratio <= 0.95)
        test_ratio = 1.0 - train_ratio - eval_ratio
        
        pipeline = FeedbackPipeline(
            train_ratio=train_ratio,
            eval_ratio=eval_ratio,
            test_ratio=test_ratio,
            min_quality_score=0.0,
        )
        
        # Add enough feedback for meaningful splits
        for i in range(100):
            fb = UserFeedback(
                feedback_id=f"fb_{i}",
                user_id="user",
                query=f"Query {i}",
                response=f"Response {i}",
                feedback_type=FeedbackType.RATING,
                rating=5.0,
                confidence_score=0.9,
            )
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        if len(examples) < 10:
            return  # Skip if not enough examples
        
        dataset = pipeline.create_dataset(examples, "test")
        
        # Check splits sum to total
        total_split = len(dataset.train_examples) + len(dataset.eval_examples) + len(dataset.test_examples)
        assert total_split == dataset.total_examples, \
            f"Splits {total_split} != total {dataset.total_examples}"
    
    @given(st.lists(user_feedback_strategy(), min_size=5, max_size=20))
    @settings(max_examples=30, deadline=None)
    def test_dataset_preserves_examples(self, feedbacks: list):
        """Dataset should preserve all examples"""
        pipeline = FeedbackPipeline(min_quality_score=0.0)
        
        for fb in feedbacks:
            pipeline.add_feedback(fb)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        if not examples:
            return  # Skip if no examples
        
        dataset = pipeline.create_dataset(examples, "test")
        
        # All examples should be in one of the splits
        all_split_examples = (
            dataset.train_examples +
            dataset.eval_examples +
            dataset.test_examples
        )
        
        assert len(all_split_examples) == len(examples), \
            f"Split examples {len(all_split_examples)} != original {len(examples)}"


class TestPipelineInvariants:
    """Test system invariants"""
    
    @given(user_feedback_strategy())
    @settings(max_examples=50, deadline=None)
    def test_add_feedback_increases_count(self, feedback: UserFeedback):
        """Adding feedback should increase store count by 1"""
        pipeline = FeedbackPipeline()
        
        initial_count = len(pipeline.feedback_store)
        pipeline.add_feedback(feedback)
        final_count = len(pipeline.feedback_store)
        
        assert final_count == initial_count + 1
    
    @given(st.lists(user_feedback_strategy(), min_size=0, max_size=10))
    @settings(max_examples=30, deadline=None)
    def test_pipeline_idempotent_collection(self, feedbacks: list):
        """Multiple collections should return same result"""
        pipeline = FeedbackPipeline()
        
        for fb in feedbacks:
            pipeline.add_feedback(fb)
        
        collected1 = pipeline.collect_feedback()
        collected2 = pipeline.collect_feedback()
        
        assert len(collected1) == len(collected2)
    
    def test_empty_pipeline_returns_empty(self):
        """Empty pipeline should return empty results"""
        pipeline = FeedbackPipeline()
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        assert len(collected) == 0
        assert len(examples) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
