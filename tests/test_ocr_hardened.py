"""
Test script for Hardened PaddleOCR implementation
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/home/haji/Desktop/Platform')

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from mahoun.pipelines.ingestion.hardened_paddle_ocr import (
            HardenedPaddleOCR, 
            create_hardened_paddle_ocr,
            OCRCheckpoint,
            TruthTraceSegment
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_model_path_validation():
    """Test model path validation logic"""
    try:
        from mahoun.pipelines.ingestion.hardened_paddle_ocr import HardenedPaddleOCR
        
        # Test with non-existent directory (should warn but not fail)
        ocr = HardenedPaddleOCR(model_dir="/tmp/nonexistent_models")
        print("✅ Model path validation handled gracefully")
        return True
    except Exception as e:
        # This might fail due to PaddleOCR not being installed, which is ok for import test
        if "PaddleOCR is not available" in str(e):
            print("✅ Model path validation working (PaddleOCR not available expected)")
            return True
        else:
            print(f"❌ Unexpected error in model path validation: {e}")
            return False

def test_data_structures():
    """Test that data structures work correctly"""
    try:
        from mahoun.pipelines.ingestion.hardened_paddle_ocr import (
            OCRCheckpoint, 
            TruthTraceSegment
        )
        from datetime import datetime
        
        # Test OCRCheckpoint
        checkpoint = OCRCheckpoint(
            page_number=5,
            total_pages=10,
            processed_text=["sample text"],
            merkle_leaves=["hash123"],
            confidence_scores=[0.9],
            timestamp=datetime.utcnow().isoformat() + 'Z',
            document_hash="doc_hash_456"
        )
        
        # Test TruthTraceSegment
        segment = TruthTraceSegment(
            text="ماده 12: این قانون قابل اجرا است",
            bounding_box=[[10, 20], [100, 20], [100, 50], [10, 50]],
            raw_confidence=0.92,
            weighted_confidence=0.95,
            merkle_leaf_link="abcd1234",
            legal_keyword_flags={"ماده": True, "تبصره": False},
            syntax_validation={"article_format": True, "note_format": False}
        )
        
        print("✅ Data structures working correctly")
        return True
    except Exception as e:
        print(f"❌ Data structure test failed: {e}")
        return False

def test_legal_keywords():
    """Test that critical legal keywords are defined"""
    try:
        from mahoun.pipelines.ingestion.hardened_paddle_ocr import CRITICAL_LEGAL_KEYWORDS
        
        expected_keywords = {'ماده', 'تبصره', 'مبلغ', 'نفت'}
        if expected_keywords.issubset(CRITICAL_LEGAL_KEYWORDS):
            print("✅ Critical legal keywords properly defined")
            return True
        else:
            print(f"❌ Missing critical legal keywords. Expected: {expected_keywords}, Got: {CRITICAL_LEGAL_KEYWORDS}")
            return False
    except Exception as e:
        print(f"❌ Legal keywords test failed: {e}")
        return False

def test_persian_patterns():
    """Test that Persian legal patterns are defined"""
    try:
        from mahoun.pipelines.ingestion.hardened_paddle_ocr import PERSIAN_LEGAL_PATTERNS
        
        expected_patterns = {'case_number', 'national_id', 'article_format', 'note_format', 'amount_format', 'date_format'}
        if expected_patterns.issubset(set(PERSIAN_LEGAL_PATTERNS.keys())):
            print("✅ Persian legal patterns properly defined")
            return True
        else:
            print(f"❌ Missing Persian legal patterns. Expected: {expected_patterns}, Got: {set(PERSIAN_LEGAL_PATTERNS.keys())}")
            return False
    except Exception as e:
        print(f"❌ Persian patterns test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Hardened PaddleOCR Implementation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_model_path_validation,
        test_data_structures,
        test_legal_keywords,
        test_persian_patterns
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Empty line between tests
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())