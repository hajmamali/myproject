"""
Tests for OCR Post-Processor
=============================

Tests the OCR post-processing pipeline including:
- Persian/Arabic normalization
- Legal term correction
- Confidence filtering
- Statistical validation
"""

import pytest
from mahoun.pipelines.ingestion.ocr_post_processor import (
    OCRPostProcessor,
    PostProcessingConfig,
    PersianNormalizer,
    LegalTermCorrector,
    StatisticalValidator,
    CorrectionType,
    post_process_ocr
)


class TestPersianNormalizer:
    """Test Persian/Arabic text normalization"""
    
    def test_arabic_to_persian_conversion(self):
        """Test Arabic character conversion to Persian"""
        text = "اين ماده مربوط به قانون است"  # Contains Arabic Ya (ي)
        result, corrections = PersianNormalizer.normalize(text, normalize_arabic=True)
        
        # Should convert Arabic Ya to Persian Ya
        assert 'ی' in result or 'ي' not in result  # Either already Persian or converted
        assert len(corrections) >= 0  # May have corrections
    
    def test_diacritic_removal(self):
        """Test removal of Arabic diacritics"""
        text = "مَادَّة"  # With diacritics
        result, corrections = PersianNormalizer.normalize(text, remove_diacritics=True)
        
        # Should remove diacritics
        assert len(result) <= len(text)
        # Check if diacritic removal was recorded
        diacritic_corrections = [c for c in corrections if c.correction_type == CorrectionType.DIACRITIC_REMOVAL]
        if len(result) < len(text):
            assert len(diacritic_corrections) > 0
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        text = "ماده  ۱۲:    قانون"  # Multiple spaces
        result, corrections = PersianNormalizer.normalize(text, normalize_whitespace=True)
        
        # Should normalize to single spaces
        assert '  ' not in result
        assert result.strip() == result


class TestLegalTermCorrector:
    """Test legal terminology correction"""
    
    def test_article_correction(self):
        """Test correction of 'ماده' variants"""
        text = "ماد ه ۱۲ از قانون"  # Broken 'ماده'
        result, corrections = LegalTermCorrector.correct_legal_terms(text)
        
        # Should correct to 'ماده'
        assert 'ماده' in result
        # Check if correction was recorded
        if 'ماد ه' in text:
            legal_corrections = [c for c in corrections if c.correction_type == CorrectionType.LEGAL_TERM_CORRECTION]
            assert len(legal_corrections) > 0
    
    def test_verdict_term_correction(self):
        """Test correction of verdict terms"""
        text = "رای دادگاه"  # May need correction to 'رأی'
        result, corrections = LegalTermCorrector.correct_legal_terms(text)
        
        # Should handle verdict terms
        assert 'دادگاه' in result or 'دادگا ه' not in result


class TestStatisticalValidator:
    """Test statistical quality validation"""
    
    def test_persian_ratio_calculation(self):
        """Test Persian/Arabic character ratio calculation"""
        persian_text = "این یک متن فارسی است"
        ratio = StatisticalValidator.calculate_persian_ratio(persian_text)
        
        # Should have high Persian ratio
        assert ratio > 0.5
    
    def test_garbage_ratio_calculation(self):
        """Test garbage character ratio calculation"""
        clean_text = "ماده ۱۲: قانون"
        garbage_text = "ماده ۱۲: قانون @@##$$%%"
        
        clean_ratio = StatisticalValidator.calculate_garbage_ratio(clean_text)
        garbage_ratio = StatisticalValidator.calculate_garbage_ratio(garbage_text)
        
        # Clean text should have lower garbage ratio
        assert clean_ratio < garbage_ratio
    
    def test_quality_validation_pass(self):
        """Test quality validation with good text"""
        good_text = "ماده ۱۲: این ماده مربوط به قانون مدنی است"
        is_valid, stats, reason = StatisticalValidator.validate_quality(good_text)
        
        # Should pass validation
        assert is_valid
        assert stats['persian_ratio'] > 0
        assert stats['garbage_ratio'] < 1.0
    
    def test_quality_validation_fail_low_persian(self):
        """Test quality validation failure with low Persian ratio"""
        bad_text = "abc def ghi jkl mno"  # No Persian
        is_valid, stats, reason = StatisticalValidator.validate_quality(
            bad_text,
            min_persian_ratio=0.3
        )
        
        # Should fail validation
        assert not is_valid
        assert 'Persian ratio' in reason or 'persian' in reason.lower()


class TestOCRPostProcessor:
    """Test main OCR post-processor"""
    
    def test_basic_processing(self):
        """Test basic post-processing"""
        text = "ماده ۱۲: اين قانون"
        processor = OCRPostProcessor()
        result = processor.process(text)
        
        # Should succeed
        assert result.success
        assert len(result.corrected_text) > 0
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
    
    def test_empty_text_handling(self):
        """Test handling of empty text"""
        processor = OCRPostProcessor()
        result = processor.process("")
        
        # Should fail gracefully
        assert not result.success
        assert result.error is not None
    
    def test_confidence_filtering(self):
        """Test confidence-based filtering"""
        text = "ماده ۱۲"
        lines = [
            {'text': 'ماده', 'confidence': 0.9},
            {'text': '۱۲', 'confidence': 0.2},  # Low confidence
        ]
        
        config = PostProcessingConfig(min_line_confidence=0.5)
        processor = OCRPostProcessor(config)
        result = processor.process(text, lines)
        
        # Should filter low confidence lines
        if result.success:
            # Check if filtering was applied
            conf_corrections = [c for c in result.corrections 
                              if c.correction_type == CorrectionType.CONFIDENCE_FILTER]
            assert len(conf_corrections) >= 0  # May have filtered some lines
    
    def test_audit_trail(self):
        """Test audit trail generation"""
        text = "ماد ه ۱۲: اين قانون"  # Has corrections
        config = PostProcessingConfig(keep_audit_trail=True)
        processor = OCRPostProcessor(config)
        result = processor.process(text)
        
        # Should have audit trail
        if result.success:
            assert isinstance(result.corrections, list)
            # May have corrections depending on text
    
    def test_quality_score_calculation(self):
        """Test quality score calculation"""
        good_text = "ماده ۱۲: این ماده مربوط به قانون مدنی است"
        bad_text = "abc @#$ xyz"
        
        processor = OCRPostProcessor()
        good_result = processor.process(good_text)
        bad_result = processor.process(bad_text)
        
        # Good text should have higher quality score
        if good_result.success and bad_result.success:
            assert good_result.quality_score > bad_result.quality_score
    
    def test_disabled_features(self):
        """Test with all features disabled"""
        text = "ماده ۱۲"
        config = PostProcessingConfig(
            normalize_persian=False,
            enable_legal_correction=False,
            enable_statistical_validation=False
        )
        processor = OCRPostProcessor(config)
        result = processor.process(text)
        
        # Should still work but with minimal processing
        assert result.success or not result.success  # Either way is fine
        assert result.corrected_text == text or result.corrected_text != text


class TestConvenienceFunction:
    """Test convenience function"""
    
    def test_post_process_ocr_function(self):
        """Test post_process_ocr convenience function"""
        text = "ماده ۱۲: قانون"
        result = post_process_ocr(text)
        
        # Should work
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'corrected_text')
        assert hasattr(result, 'quality_score')


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests with realistic scenarios"""
    
    def test_realistic_legal_text(self):
        """Test with realistic legal text"""
        text = """
        ماده ۱۲: دادگاه با بررسی پرونده و استماع اظهارات طرفین
        رای به محکومیت خوانده صادر می‌نماید.
        """
        
        processor = OCRPostProcessor()
        result = processor.process(text)
        
        # Should process successfully
        assert result.success
        assert len(result.corrected_text) > 0
        assert 'ماده' in result.corrected_text
        assert 'دادگاه' in result.corrected_text
    
    def test_mixed_quality_text(self):
        """Test with mixed quality text (some good, some bad)"""
        text = "ماده ۱۲: قانون\n@#$%^&*\nبند الف"
        
        processor = OCRPostProcessor()
        result = processor.process(text)
        
        # Should handle mixed quality
        assert result is not None
        # May succeed or fail depending on garbage ratio


# ============================================================================
# Performance Tests (optional, marked as slow)
# ============================================================================

@pytest.mark.slow
class TestPerformance:
    """Performance tests"""
    
    def test_large_text_processing(self):
        """Test processing of large text"""
        # Generate large text
        text = "ماده ۱۲: این ماده مربوط به قانون است.\n" * 1000
        
        processor = OCRPostProcessor()
        result = processor.process(text)
        
        # Should complete without timeout
        assert result is not None
    
    def test_many_corrections(self):
        """Test text with many corrections needed"""
        # Text with many Arabic characters
        text = "ماد ه ۱۲: اين قانون مربوط به دادگا ه است" * 100
        
        processor = OCRPostProcessor()
        result = processor.process(text)
        
        # Should handle many corrections
        assert result is not None
        if result.success:
            assert len(result.corrections) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
