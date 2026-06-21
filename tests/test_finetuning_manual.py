#!/usr/bin/env python3
"""
Manual Test for Fine-Tuning Pipeline
=====================================
Run without pytest to verify functionality.
"""

from mahoun.finetuning.feedback_pipeline import (
    FeedbackPipeline,
    UserFeedback,
    FeedbackType,
)


def test_basic_pipeline():
    """Test basic pipeline functionality"""
    print("🧪 Testing FeedbackPipeline...")
    
    # Create pipeline
    pipeline = FeedbackPipeline(
        min_rating=4.0,
        min_quality_score=0.7
    )
    print("✓ Pipeline created")
    
    # Add feedback
    feedback = UserFeedback(
        feedback_id="test_001",
        user_id="user_001",
        query="What is force majeure?",
        response="Force majeure is an unforeseeable circumstance...",
        feedback_type=FeedbackType.RATING,
        rating=5.0,
        response_time_ms=1200,
        confidence_score=0.95
    )
    pipeline.add_feedback(feedback)
    print(f"✓ Added feedback: {len(pipeline.feedback_store)} items")
    
    # Collect feedback
    collected = pipeline.collect_feedback()
    print(f"✓ Collected feedback: {len(collected)} items")
    
    # Convert to examples
    examples = pipeline.convert_to_training_examples(collected)
    print(f"✓ Converted to examples: {len(examples)} items")
    
    if examples:
        print(f"  - Input: {examples[0].input_text[:50]}...")
        print(f"  - Target: {examples[0].target_text[:50]}...")
        print(f"  - Quality: {examples[0].quality_score:.3f}")
    
    # Create dataset
    if examples:
        dataset = pipeline.create_dataset(
            examples=examples,
            dataset_name="test_dataset",
            description="Test dataset"
        )
        print(f"✓ Created dataset: {dataset.total_examples} examples")
        print(f"  - Train: {len(dataset.train_examples)}")
        print(f"  - Eval: {len(dataset.eval_examples)}")
        print(f"  - Test: {len(dataset.test_examples)}")
        print(f"  - Avg quality: {dataset.avg_quality_score:.3f}")
    
    print("\n✅ All tests passed!")
    return True


def test_quality_scoring():
    """Test quality score calculation"""
    print("\n🧪 Testing quality scoring...")
    
    pipeline = FeedbackPipeline()
    
    # High quality
    high_quality = UserFeedback(
        feedback_id="hq",
        user_id="user_hq",
        query="Test",
        response="Test",
        feedback_type=FeedbackType.CORRECTION,
        rating=5.0,
        response_time_ms=1000,
        confidence_score=0.95
    )
    score_hq = pipeline._calculate_quality_score(high_quality)
    print(f"✓ High quality score: {score_hq:.3f}")
    assert score_hq >= 0.8, f"Expected >= 0.8, got {score_hq}"
    
    # Low quality
    low_quality = UserFeedback(
        feedback_id="lq",
        user_id="user_lq",
        query="Test",
        response="Test",
        feedback_type=FeedbackType.RATING,
        rating=2.0,
        response_time_ms=10000,
        confidence_score=0.3
    )
    score_lq = pipeline._calculate_quality_score(low_quality)
    print(f"✓ Low quality score: {score_lq:.3f}")
    assert score_lq <= 0.7, f"Expected <= 0.7, got {score_lq}"
    
    print("✅ Quality scoring works!")
    return True


def test_feedback_types():
    """Test different feedback types"""
    print("\n🧪 Testing feedback types...")
    
    pipeline = FeedbackPipeline()
    
    # Rating feedback
    rating_fb = UserFeedback(
        feedback_id="rating",
        user_id="user",
        query="Q1",
        response="R1",
        feedback_type=FeedbackType.RATING,
        rating=5.0,
        confidence_score=0.9
    )
    
    # Correction feedback
    correction_fb = UserFeedback(
        feedback_id="correction",
        user_id="user",
        query="Q2",
        response="R2",
        feedback_type=FeedbackType.CORRECTION,
        corrected_response="Better R2",
        confidence_score=0.9
    )
    
    # Preference feedback
    preference_fb = UserFeedback(
        feedback_id="preference",
        user_id="user",
        query="Q3",
        response="R3",
        feedback_type=FeedbackType.PREFERENCE,
        preferred_response="Preferred R3",
        confidence_score=0.9
    )
    
    examples = pipeline.convert_to_training_examples([
        rating_fb,
        correction_fb,
        preference_fb
    ])
    
    print(f"✓ Converted {len(examples)} examples")
    
    sources = [e.source for e in examples]
    print(f"  - Sources: {sources}")
    
    assert "rating" in sources
    assert "correction" in sources
    assert "preference" in sources
    
    print("✅ All feedback types work!")
    return True


if __name__ == "__main__":
    try:
        test_basic_pipeline()
        test_quality_scoring()
        test_feedback_types()
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
