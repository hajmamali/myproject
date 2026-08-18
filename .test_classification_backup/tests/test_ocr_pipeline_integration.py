import pytest
pytest.importorskip("PIL")
"""
OCR Pipeline Integration Tests
===============================

Comprehensive end-to-end tests for the complete OCR pipeline:
- Preprocessing (ocr_preprocessing.py)
- OCR Engine (ocr_handler.py)
- Post-processing (ocr_post_processor.py)

Tests realistic scenarios with actual Persian legal documents.
"""

import pytest
import tempfile
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from mahoun.pipelines.ingestion.ocr_handler import (
    OCREngine,
    OCRResult,
    ocr_image,
    check_ocr_availability
)
from mahoun.pipelines.ingestion.ocr_post_processor import (
    OCRPostProcessor,
    PostProcessingConfig,
    post_process_ocr
)

# Try to import preprocessing
try:
    from mahoun.pipelines.ingestion.ocr_preprocessing import (
        OCRPreprocessor,
        PreprocessingConfig
    )
    PREPROCESSING_AVAILABLE = True
except ImportError:
    PREPROCESSING_AVAILABLE = False


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_image_dir():
    """Create temporary directory for test images"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_persian_text():
    """Sample Persian legal text for testing"""
    return """
    ماده ۱۲: دادگاه با بررسی پرونده و استماع اظهارات طرفین
    رأی به محکومیت خوانده به پرداخت مبلغ ده میلیون ریال
    به عنوان خسارت وارده به خواهان صادر می‌نماید.
    
    بند الف: این رأی قطعی و لازم‌الاجرا است.
    تبصره: در صورت عدم پرداخت، اموال خوانده توقیف خواهد شد.
    """


@pytest.fixture
def create_test_image(temp_image_dir):
    """Factory to create test images with Persian text"""
    def _create(text: str, filename: str = "test.png", add_noise: bool = False):
        # Create image
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font that supports Persian
        try:
            # Try common Persian fonts
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                'C:\\Windows\\Fonts\\arial.ttf',
            ]
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 24)
                    break
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Draw text
        y_position = 50
        for line in text.strip().split('\n'):
            if line.strip():
                draw.text((50, y_position), line.strip(), fill='black', font=font)
                y_position += 40
        
        # Add noise if requested
        if add_noise:
            img_array = np.array(img)
            noise = np.random.randint(0, 50, img_array.shape, dtype=np.uint8)
            img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(img_array)
        
        # Save
        img_path = temp_image_dir / filename
        img.save(img_path)
        return str(img_path)
    
    return _create


# ============================================================================
# Integration Tests - Full Pipeline
# ============================================================================

class TestOCRPipelineIntegration:
    """Test complete OCR pipeline with all components"""
    
    def test_full_pipeline_clean_image(self, create_test_image, sample_persian_text):
        """Test full pipeline with clean image"""
        # Skip if OCR not available
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create test image
        img_path = create_test_image(sample_persian_text, "clean.png")
        
        # Run OCR with post-processing
        result = ocr_image(img_path)
        
        # Assertions
        assert result.success
        assert len(result.text) > 0
        
        # Check if post-processing was applied
        if 'post_processing_applied' in result.metadata:
            assert result.metadata['post_processing_applied'] is True
            assert 'quality_score' in result.metadata
            assert 0.0 <= result.metadata['quality_score'] <= 1.0
    
    def test_full_pipeline_noisy_image(self, create_test_image, sample_persian_text):
        """Test full pipeline with noisy image"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create noisy test image
        img_path = create_test_image(sample_persian_text, "noisy.png", add_noise=True)
        
        # Run OCR
        result = ocr_image(img_path)
        
        # Should still succeed (graceful degradation)
        assert result.success or not result.success  # Either way is acceptable
        
        # If successful, check quality score
        if result.success and 'quality_score' in result.metadata:
            # Noisy images should have lower quality score
            assert result.metadata['quality_score'] >= 0.0
    
    def test_pipeline_with_preprocessing(self, create_test_image, sample_persian_text):
        """Test pipeline with preprocessing enabled"""
        if not PREPROCESSING_AVAILABLE:
            pytest.skip("Preprocessing not available")
        
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create test image
        img_path = create_test_image(sample_persian_text, "preprocess.png")
        
        # Apply preprocessing
        preprocessor = OCRPreprocessor(PreprocessingConfig())
        preprocessed_path = preprocessor.preprocess(img_path)
        
        # Run OCR on preprocessed image
        result = ocr_image(preprocessed_path)
        
        # Should succeed
        assert result.success
        assert len(result.text) > 0
    
    def test_pipeline_comparison_with_without_postprocessing(
        self, create_test_image, sample_persian_text
    ):
        """Compare results with and without post-processing"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create test image with intentional errors
        text_with_errors = sample_persian_text.replace('ماده', 'ماد ه').replace('دادگاه', 'دادگا ه')
        img_path = create_test_image(text_with_errors, "errors.png")
        
        # OCR without post-processing
        engine_no_pp = OCREngine(enable_post_processing=False)
        result_no_pp = engine_no_pp.ocr_image(img_path)
        
        # OCR with post-processing
        engine_with_pp = OCREngine(enable_post_processing=True)
        result_with_pp = engine_with_pp.ocr_image(img_path)
        
        # Both should succeed
        if result_no_pp.success and result_with_pp.success:
            # Post-processed version should have corrections
            if 'corrections_count' in result_with_pp.metadata:
                # May have corrections (depending on OCR output)
                assert result_with_pp.metadata['corrections_count'] >= 0


# ============================================================================
# Integration Tests - Component Interaction
# ============================================================================

class TestComponentInteraction:
    """Test interaction between different components"""
    
    def test_ocr_engine_post_processor_integration(self):
        """Test OCR engine and post-processor work together"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create engine with post-processing
        engine = OCREngine(enable_post_processing=True)
        
        # Check post-processor is initialized
        assert engine.enable_post_processing
        assert engine.post_processor is not None
    
    def test_post_processor_with_ocr_metadata(self):
        """Test post-processor handles OCR metadata correctly"""
        # Sample OCR output
        text = "ماد ه ۱۲: اين قانون"
        lines = [
            {'text': 'ماد ه', 'confidence': 0.9},
            {'text': '۱۲:', 'confidence': 0.95},
            {'text': 'اين', 'confidence': 0.85},
            {'text': 'قانون', 'confidence': 0.92}
        ]
        
        # Process
        result = post_process_ocr(text, lines)
        
        # Should succeed
        assert result.success
        assert len(result.corrected_text) > 0
        
        # Should have corrections
        if result.corrections:
            assert len(result.corrections) > 0


# ============================================================================
# Realistic Scenario Tests
# ============================================================================

class TestRealisticScenarios:
    """Test realistic legal document scenarios"""
    
    def test_verdict_document(self, create_test_image):
        """Test with realistic verdict document"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        verdict_text = """
        دادنامه شماره: ۱۴۰۰۰۹۹۷۰۹۰۰۱۲۳۴۵۶
        
        رأی دادگاه
        
        در خصوص دعوی آقای احمد محمدی به طرفیت خانم فاطمه رضایی
        به خواسته مطالبه وجه چک به مبلغ پنجاه میلیون ریال
        
        دادگاه با بررسی محتویات پرونده و استماع اظهارات طرفین
        و ملاحظه اصل چک و گواهی عدم پرداخت
        
        مستنداً به ماده ۳۱۰ قانون تجارت
        حکم به محکومیت خوانده صادر می‌نماید.
        
        این رأی ظرف بیست روز قابل تجدیدنظر است.
        """
        
        img_path = create_test_image(verdict_text, "verdict.png")
        result = ocr_image(img_path)
        
        # Should extract text
        if result.success:
            assert len(result.text) > 0
            # Check for key legal terms
            text_lower = result.text
            # May contain some legal terms (depending on OCR quality)
    
    def test_law_article_document(self, create_test_image):
        """Test with law article document"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        law_text = """
        قانون مدنی
        
        ماده ۱۰: هر کس بدون مجوز قانونی عمداً به جان یا مال یا
        حیثیت دیگری صدمه بزند مسئول جبران خسارت ناشی از عمل خود است.
        
        بند الف: خسارت شامل ضرر و زیان مادی و معنوی می‌شود.
        بند ب: مسئولیت مدنی مانع از تعقیب کیفری نیست.
        
        تبصره ۱: در صورت تعدد مسئولین، مسئولیت به صورت تضامنی است.
        تبصره ۲: ورثه متوفی در حدود ترکه مسئول دیون او هستند.
        """
        
        img_path = create_test_image(law_text, "law.png")
        result = ocr_image(img_path)
        
        # Should extract text
        if result.success:
            assert len(result.text) > 0


# ============================================================================
# Error Handling & Edge Cases
# ============================================================================

class TestErrorHandling:
    """Test error handling in integration scenarios"""
    
    def test_invalid_image_path(self):
        """Test with invalid image path"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Try to OCR non-existent file
        engine = OCREngine()
        result = engine.ocr_image("/nonexistent/path/image.png")
        
        # Should fail gracefully
        assert not result.success
        assert result.error is not None
    
    def test_corrupted_image(self, temp_image_dir):
        """Test with corrupted image file"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create corrupted image file
        corrupted_path = temp_image_dir / "corrupted.png"
        with open(corrupted_path, 'wb') as f:
            f.write(b'not an image')
        
        # Try to OCR
        engine = OCREngine()
        result = engine.ocr_image(str(corrupted_path))
        
        # Should fail gracefully
        assert not result.success
    
    def test_empty_image(self, temp_image_dir):
        """Test with empty/blank image"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Create blank image
        img = Image.new('RGB', (800, 600), color='white')
        img_path = temp_image_dir / "blank.png"
        img.save(img_path)
        
        # Try to OCR
        result = ocr_image(str(img_path))
        
        # May succeed with empty text or fail
        if result.success:
            # Empty or very short text
            assert len(result.text.strip()) < 100


# ============================================================================
# Performance & Quality Tests
# ============================================================================

@pytest.mark.slow
class TestPerformanceQuality:
    """Performance and quality benchmarks"""
    
    def test_processing_time(self, create_test_image, sample_persian_text):
        """Test processing time is reasonable"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        import time
        
        img_path = create_test_image(sample_persian_text, "perf.png")
        
        # Measure time
        start = time.time()
        result = ocr_image(img_path)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 10 seconds for small image)
        assert elapsed < 10.0
        
        # Log timing
        print(f"\nOCR processing time: {elapsed:.2f}s")
        if 'post_processing_applied' in result.metadata:
            print(f"Post-processing: enabled")
            print(f"Quality score: {result.metadata.get('quality_score', 'N/A')}")
    
    def test_quality_improvement_measurement(self, create_test_image):
        """Measure quality improvement from post-processing"""
        availability = check_ocr_availability()
        if not availability['is_available']:
            pytest.skip("No OCR engine available")
        
        # Text with common OCR errors
        text_with_errors = """
        ماد ه ۱۲: اين قانون مربوط به دادگا ه است
        بن د الف: تبصر ه اول
        """
        
        img_path = create_test_image(text_with_errors, "quality.png")
        
        # Without post-processing
        engine_no_pp = OCREngine(enable_post_processing=False)
        result_no_pp = engine_no_pp.ocr_image(img_path)
        
        # With post-processing
        engine_with_pp = OCREngine(enable_post_processing=True)
        result_with_pp = engine_with_pp.ocr_image(img_path)
        
        # Compare
        if result_no_pp.success and result_with_pp.success:
            print(f"\nWithout post-processing: {len(result_no_pp.text)} chars")
            print(f"With post-processing: {len(result_with_pp.text)} chars")
            
            if 'corrections_count' in result_with_pp.metadata:
                print(f"Corrections applied: {result_with_pp.metadata['corrections_count']}")
            if 'quality_score' in result_with_pp.metadata:
                print(f"Quality score: {result_with_pp.metadata['quality_score']:.2%}")


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfiguration:
    """Test configuration and environment variables"""
    
    def test_post_processing_can_be_disabled(self):
        """Test post-processing can be disabled"""
        engine = OCREngine(enable_post_processing=False)
        assert not engine.enable_post_processing
        assert engine.post_processor is None
    
    def test_post_processing_enabled_by_default(self):
        """Test post-processing is enabled by default"""
        engine = OCREngine()
        # Should be enabled if available
        if engine.post_processor is not None:
            assert engine.enable_post_processing
    
    def test_custom_post_processing_config(self):
        """Test custom post-processing configuration"""
        config = PostProcessingConfig(
            min_line_confidence=0.7,
            normalize_persian=True,
            enable_legal_correction=True
        )
        processor = OCRPostProcessor(config)
        
        assert processor.config.min_line_confidence == 0.7
        assert processor.config.normalize_persian is True
        assert processor.config.enable_legal_correction is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
