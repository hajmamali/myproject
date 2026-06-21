#!/usr/bin/env python3
"""Quick test for quality score fix"""

from mahoun.finetuning.feedback_pipeline import FeedbackPipeline, UserFeedback, FeedbackType

pipeline = FeedbackPipeline()

# Low quality feedback
lq = UserFeedback(
    feedback_id='lq',
    user_id='u',
    query='Q',
    response='R',
    feedback_type=FeedbackType.RATING,
    rating=2.0,
    response_time_ms=10000,
    confidence_score=0.3
)
score_lq = pipeline._calculate_quality_score(lq)

# High quality feedback
hq = UserFeedback(
    feedback_id='hq',
    user_id='u',
    query='Q',
    response='R',
    feedback_type=FeedbackType.CORRECTION,
    rating=5.0,
    response_time_ms=1000,
    confidence_score=0.95
)
score_hq = pipeline._calculate_quality_score(hq)

print(f"Low quality score: {score_lq:.4f}")
print(f"  Expected: < 0.7")
print(f"  Result: {'PASS' if score_lq < 0.7 else 'FAIL'}")
print()
print(f"High quality score: {score_hq:.4f}")
print(f"  Expected: >= 0.8")
print(f"  Result: {'PASS' if score_hq >= 0.8 else 'FAIL'}")
print()

# Calculate breakdown for low quality
print("Low quality breakdown:")
print(f"  rating=2.0 → {(2.0/5.0)*0.4:.4f}")
print(f"  response_time=10000ms → 0.02")
print(f"  confidence=0.3 → {0.3*0.2:.4f}")
print(f"  type=RATING → 0.1")
print(f"  Total: {(2.0/5.0)*0.4 + 0.02 + 0.3*0.2 + 0.1:.4f}")

if score_lq < 0.7 and score_hq >= 0.8:
    print("\n✅ ALL TESTS PASSED!")
else:
    print("\n❌ TESTS FAILED!")
    exit(1)
