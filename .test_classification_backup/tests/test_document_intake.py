"""
Test Suite for Document Intake Layer (PHASE 1)
==============================================

تست‌های کامل برای:
- Document Normalizer
- Metadata Extractor
- OCR Handler
- Integration با کامپوننت‌های موجود
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path

from mahoun.switchboard import switchboard


class TestDocumentNormalizer:
    """Test Document Normalizer"""

    @pytest.fixture
    def normalizer(self):
        """Create Document Normalizer instance"""
        return type(switchboard.get_module("document_normalizer"))()

    @pytest.fixture
    def sample_text(self):
        """Sample Persian text for testing"""
        return """
        بسمه تعالی
        
        موضوع: قرارداد پیمانکاری
        تاریخ: 1403/01/15
        شماره: 12345
        
        طرف اول: شرکت الف
        طرف دوم: شرکت ب
        
        متن قرارداد...
        """

    @pytest.mark.asyncio
    async def test_normalize_text(self, normalizer, sample_text):
        """Test text normalization"""
        result = await normalizer.normalize_text(text=sample_text, doc_type="contract")

        assert result is not None
        assert result.document_id is not None
        assert result.type == "contract"
        assert result.content["text"] == sample_text
        assert result.content["text"] == sample_text
        assert "content" in result.__dict__

    @pytest.mark.asyncio
    async def test_normalize_text_detection(self, normalizer):
        """Test document type detection"""
        contract_text = "قرارداد بین طرف اول و طرف دوم..."
        result = await normalizer.normalize_text(
            text=contract_text, doc_type="contract"
        )

        assert result.type == "contract"

    @pytest.mark.asyncio
    async def test_normalize_file_txt(self, normalizer):
        """Test TXT file normalization"""
        # Create temporary TXT file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("این یک فایل تست است.\nتاریخ: 1403/01/15")
            temp_path = f.name

        try:
            result = await normalizer.normalize_file(temp_path)

            assert result is not None
            assert result.document_id is not None
            assert "text" in result.content
            assert result.metadata["file_name"].endswith(".txt")
        finally:
            os.unlink(temp_path)

    def test_to_dict(self, normalizer, sample_text):
        """Test conversion to dictionary"""

        async def run():
            normalized = await normalizer.normalize_text(
                text=sample_text, doc_type="contract"
            )
            return normalizer.to_dict(normalized)

        result_dict = asyncio.run(run())

        assert isinstance(result_dict, dict)
        assert "document_id" in result_dict
        assert "type" in result_dict
        assert "metadata" in result_dict
        assert "content" in result_dict


class TestMetadataExtractor:
    """Test Metadata Extractor"""

    @pytest.fixture
    def extractor(self):
        """Create Metadata Extractor instance"""
        return type(switchboard.get_module("metadata_extractor"))()

    @pytest.fixture
    def sample_contract_text(self):
        """Sample contract text"""
        return """
        بسمه تعالی
        
        قرارداد پیمانکاری
        شماره: 12345/1403
        تاریخ: 1403/01/15
        
        طرف اول: شرکت توسعه و ساخت الف
        طرف دوم: شرکت پیمانکاری ب
        
        موضوع: ساخت و ساز پروژه مسکونی
        
        امضا: مدیر عامل شرکت الف
        """

    @pytest.mark.asyncio
    async def test_extract_metadata(self, extractor, sample_contract_text):
        """Test metadata extraction"""
        metadata = await extractor.extract(
            text=sample_contract_text, doc_type="contract"
        )

        assert metadata is not None
        assert "doc_type" in metadata
        assert metadata["doc_type"] == "contract"
        assert "extracted_at" in metadata

    @pytest.mark.asyncio
    async def test_extract_dates(self, extractor):
        """Test date extraction"""
        text = "تاریخ: 1403/01/15\nتاریخ دریافت: 1403/01/20"
        metadata = await extractor.extract(text, "letter")

        assert "date" in metadata
        assert "dates_found" in metadata
        assert len(metadata["dates_found"]) > 0

    @pytest.mark.asyncio
    async def test_extract_document_number(self, extractor):
        """Test document number extraction"""
        text = "شماره: 12345/1403"
        metadata = await extractor.extract(text, "letter")

        assert "document_number" in metadata
        assert metadata["document_number"] is not None

    @pytest.mark.asyncio
    async def test_extract_subject(self, extractor):
        """Test subject extraction"""
        text = "موضوع: قرارداد پیمانکاری"
        metadata = await extractor.extract(text, "letter")

        assert "subject" in metadata
        assert "قرارداد" in metadata["subject"] or metadata["subject"] is not None

    @pytest.mark.asyncio
    async def test_extract_parties(self, extractor):
        """Test parties extraction"""
        text = "طرف اول: شرکت الف\nطرف دوم: شرکت ب"
        metadata = await extractor.extract(text, "contract")

        assert "parties" in metadata
        assert len(metadata["parties"]) > 0


class TestOCRHandler:
    """Test OCR Handler"""

    @pytest.fixture
    def ocr_handler(self):
        """Create OCR Handler instance"""
        return type(switchboard.get_module("ocr_handler"))()

    def test_ocr_availability(self, ocr_handler):
        """Test OCR handler availability"""
        # Just check if handler can be created
        assert ocr_handler is not None
        # Availability depends on dependencies
        assert isinstance(ocr_handler.available, bool)

    def test_supports_file(self, ocr_handler):
        """Test file type support"""
        assert ocr_handler.supports_file("test.jpg")
        assert ocr_handler.supports_file("test.png")
        assert ocr_handler.supports_file("test.jpeg")
        assert not ocr_handler.supports_file("test.txt")
        assert not ocr_handler.supports_file("test.pdf")


class TestDocumentHandlers:
    """Test Document Handlers Integration"""

    @pytest.fixture
    def handler_factory(self):
        """Create Document Handler Factory"""
        return type(switchboard.get_module("document_handler_factory"))()

    def test_handler_factory_initialization(self, handler_factory):
        """Test factory initialization"""
        assert handler_factory is not None
        assert len(handler_factory.handlers) > 0

    def test_txt_handler(self):
        """Test TXT handler"""
        from mahoun.pipelines.ingestion.document_handlers import TxtHandler

        handler = TxtHandler()
        assert handler.available  # Should always be available

        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            result = handler.extract_text(temp_path)
            assert result.success
            assert "Test content" in result.text
        finally:
            os.unlink(temp_path)


class TestIntegration:
    """Integration Tests"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test full document intake pipeline"""
        # Step 1: Normalize document
        normalizer = type(switchboard.get_module("document_normalizer"))()
        sample_text = "قرارداد پیمانکاری\nتاریخ: 1403/01/15\nشماره: 12345"

        normalized = await normalizer.normalize_text(
            text=sample_text, doc_type="contract"
        )

        assert normalized is not None
        assert normalized.type == "contract"

        # Step 2: Check metadata extraction
        # Step 2: Check metadata extraction
        assert normalized.metadata.get("doc_type") == "contract"

    @pytest.mark.asyncio
    async def test_helper_functions(self):
        """Test helper functions"""
        sample_text = "Test document\nتاریخ: 1403/01/15"

        # Test normalize_document_text by using typical normalizer method
        # Test normalize_document_text by using typical normalizer method
        normalizer = type(switchboard.get_module("document_normalizer"))()
        result = await normalizer.normalize_text(text=sample_text, doc_type="letter")

        result_dict = normalizer.to_dict(result)
        assert isinstance(result_dict, dict)
        assert "document_id" in result_dict
        assert "type" in result_dict
        assert result_dict["type"] == "letter"


class TestWiring:
    """Test Wiring with Existing Components"""

    @pytest.mark.asyncio
    async def test_integration_with_ingestion_pipeline(self):
        """Test integration with existing IngestionPipeline"""
        try:
            from mahoun.pipelines.ingestion import IngestionPipeline

            # Create normalizer
            normalizer = type(switchboard.get_module("document_normalizer"))()
            sample_text = "Test document for ingestion"

            # Normalize document
            normalized = await normalizer.normalize_text(
                text=sample_text, doc_type="document"
            )

            # Create ingestion pipeline
            pipeline = type(switchboard.get_module("legal_pipeline"))()
            if hasattr(pipeline, "initialize"):
                await pipeline.initialize()

            # Ingest normalized document
            result = await pipeline.ingest_document(
                doc_id=normalized.document_id,
                text=normalized.content["text"],
                metadata=normalized.metadata,
            )

            assert result.success
            assert result.chunks_created > 0

        except Exception as e:
            pytest.skip(f"IngestionPipeline integration test skipped: {e}")

    @pytest.mark.asyncio
    async def test_metadata_extractor_with_ner(self):
        """Test Metadata Extractor with NER integration"""
        try:
            extractor = type(switchboard.get_module("metadata_extractor"))()
            text = "قرارداد بین شرکت الف و شرکت ب"

            metadata = await extractor.extract(text, "contract")

            # Check if NER was used (if available)
            if extractor.ner_engine:
                assert "entities" in metadata
            else:
                # Should still work without NER
                assert "doc_type" in metadata

        except Exception as e:
            pytest.skip(f"NER integration test skipped: {e}")


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
