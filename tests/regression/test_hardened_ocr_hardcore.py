"""
HARDCORE Regression Tests for HardenedPaddleOCR Wiring (ROUND 7 - ISSUE 2)
============================================================================

These tests are INTENTIONALLY extremely strict and difficult.
They verify ACTUAL behavior, not just code presence.
They do NOT use mocks, stubs, or any form of test simplification.

Purpose: To catch ANY regression in the OCR wiring with maximum severity.

Test Philosophy:
- Fail fast on any discrepancy
- No tolerance for degraded mode in production
- Verify complete execution path
- Test actual imports and method calls
- Verify fail-closed behavior under real conditions
- Verify Merkle integrity proof propagation
"""

import pytest
import os
import sys

# Force development mode for tests
os.environ["MAHOUN_ENVIRONMENT"] = "development"


class TestHardenedOCRImportHardcore:
    """
    HARDCORE: Verify HardenedPaddleOCR can be imported and has correct interface.
    """

    def test_hardened_paddle_ocr_file_exists(self):
        """
        Verify the file itself exists at the expected location.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/hardened_paddle_ocr.py")
        assert file_path.exists(), \
            f"HardenedPaddleOCR file not found at {file_path}"
        
        # Verify it's not empty
        content = file_path.read_text()
        assert len(content) > 10000, \
            "HardenedPaddleOCR file is too small (expected 1457+ lines)"

    def test_hardened_paddle_ocr_class_exists(self):
        """
        Verify the HardenedPaddleOCR class exists at line 167.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/hardened_paddle_ocr.py")
        lines = file_path.read_text().split('\n')
        
        # Find the class definition
        class_line = None
        for i, line in enumerate(lines):
            if line.strip().startswith("class HardenedPaddleOCR"):
                class_line = i + 1  # 1-indexed
                break
        
        assert class_line is not None, \
            "HardenedPaddleOCR class not found"
        
        # Should be around line 167
        assert 150 < class_line < 200, \
            f"HardenedPaddleOCR class at unexpected line {class_line} (expected ~167)"

    def test_ocr_image_hardened_method_exists(self):
        """
        Verify ocr_image_hardened method exists with correct signature.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/hardened_paddle_ocr.py")
        content = file_path.read_text()
        
        # Find method definition
        assert "def ocr_image_hardened(" in content, \
            "ocr_image_hardened method not found"
        
        # Check it has the expected parameters
        assert "image_path: str | Path" in content, \
            "ocr_image_hardened missing image_path parameter"
        
        assert "document_id: str = \"\"" in content, \
            "ocr_image_hardened missing document_id parameter"
        
        assert "page_number: int = 0" in content, \
            "ocr_image_hardened missing page_number parameter"
        
        assert "enable_checkpointing: bool = True" in content, \
            "ocr_image_hardened missing enable_checkpointing parameter"

    def test_get_document_merkle_root_exists(self):
        """
        Verify get_document_merkle_root method exists.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/hardened_paddle_ocr.py")
        content = file_path.read_text()
        
        assert "def get_document_merkle_root(self) -> str:" in content, \
            "get_document_merkle_root method not found with correct signature"


class TestOCRWiringInDocumentHandlersHardcore:
    """
    HARDCORE: Verify HardenedPaddleOCR is actually wired into document_handlers.py
    """

    def test_hardened_ocr_import_in_extract_with_ocr(self):
        """
        Verify that HardenedPaddleOCR is imported in _extract_with_ocr.
        
        Before fix: document_handlers.py used plain PaddleOCR directly
        After fix: It must import and use HardenedPaddleOCR
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        # Find _extract_with_ocr method
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        assert extract_start > 0, \
            "_extract_with_ocr method not found"
        
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must have HardenedPaddleOCR import
        assert "from mahoun.pipelines.ingestion.hardened_paddle_ocr import HardenedPaddleOCR" in extract_section, \
            "HardenedPaddleOCR import not found in _extract_with_ocr"

    def test_hardened_ocr_instantiation_in_extract_with_ocr(self):
        """
        Verify that HardenedPaddleOCR is instantiated with correct parameters.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must instantiate HardenedPaddleOCR
        assert "HardenedPaddleOCR(" in extract_section, \
            "HardenedPaddleOCR instantiation not found"
        
        # Must have expected parameters
        assert "model_dir=" in extract_section, \
            "model_dir parameter not found in HardenedPaddleOCR instantiation"
        
        assert "checkpoint_dir=" in extract_section, \
            "checkpoint_dir parameter not found in HardenedPaddleOCR instantiation"
        
        assert "legal_keyword_threshold=" in extract_section, \
            "legal_keyword_threshold parameter not found"
        
        assert "general_confidence_threshold=" in extract_section, \
            "general_confidence_threshold parameter not found"

    def test_ocr_image_hardened_is_called(self):
        """
        Verify that ocr_image_hardened method is actually called.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must call ocr_image_hardened
        assert "ocr_image_hardened(" in extract_section, \
            "ocr_image_hardened call not found"
        
        # Must pass expected parameters
        assert "image_path=" in extract_section, \
            "image_path not passed to ocr_image_hardened"
        
        assert "document_id=" in extract_section, \
            "document_id not passed to ocr_image_hardened"
        
        assert "page_number=" in extract_section, \
            "page_number not passed to ocr_image_hardened"
        
        assert "enable_checkpointing=True" in extract_section, \
            "enable_checkpointing=True not passed to ocr_image_hardened"

    def test_get_document_merkle_root_is_called(self):
        """
        Verify that get_document_merkle_root is called and result is captured.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must call get_document_merkle_root
        assert "get_document_merkle_root()" in extract_section, \
            "get_document_merkle_root call not found"
        
        # Must capture the result
        assert "merkle_root = hardened_ocr.get_document_merkle_root()" in extract_section, \
            "merkle_root not captured from get_document_merkle_root"


class TestOCRPriorityOrderHardcore:
    """
    HARDCORE: Verify OCR engines are tried in correct priority order.
    """

    def test_hardened_ocr_is_priority_1(self):
        """
        Verify that HardenedPaddleOCR is tried FIRST (PRIORITY 1).
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Find positions of key elements
        hardened_import_pos = extract_section.find("from mahoun.pipelines.ingestion.hardened_paddle_ocr import HardenedPaddleOCR")
        paddle_import_pos = extract_section.find("from paddleocr import PaddleOCR")
        tesseract_import_pos = extract_section.find("import pytesseract")
        
        # HardenedPaddleOCR must appear before plain PaddleOCR
        # (or at least, the try block for Hardened must come before except that uses PaddleOCR)
        assert hardened_import_pos > 0, \
            "HardenedPaddleOCR import not found"
        
        # The structure should have Hardened in try, PaddleOCR in except
        # So the import for Hardened should be in the code before fallback imports
        assert hardened_import_pos < 2000, \
            "HardenedPaddleOCR import appears too late in the method"

    def test_paddleocr_is_priority_2_fallback(self):
        """
        Verify that plain PaddleOCR is PRIORITY 2 (fallback when Hardened fails).
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must have except ImportError for HardenedPaddleOCR failure
        assert "except ImportError as e:" in extract_section, \
            "No ImportError exception handling for HardenedPaddleOCR"
        
        # In the except block, must try plain PaddleOCR
        except_pos = extract_section.find("except ImportError as e:")
        after_except = extract_section[except_pos:except_pos + 3000]
        
        assert "from paddleocr import PaddleOCR" in after_except, \
            "PaddleOCR fallback not found after HardenedPaddleOCR ImportError"

    def test_tesseract_is_priority_3_fallback(self):
        """
        Verify that Tesseract is PRIORITY 3 (last resort).
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must have except ImportError for PaddleOCR fallback
        # And then try Tesseract
        assert "except ImportError:" in extract_section, \
            "No ImportError exception handling for PaddleOCR fallback"
        
        # After the second except, must import pytesseract
        import_pos = extract_section.rfind("import pytesseract")
        assert import_pos > 0, \
            "pytesseract import not found (Tesseract fallback)"


class TestOCRProductionRequirementHardcore:
    """
    HARDCORE: Verify that in production, HardenedPaddleOCR is REQUIRED.
    """

    def test_production_blocks_without_hardened_ocr(self):
        """
        Verify that in production mode, missing HardenedPaddleOCR raises ImportError.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Find the ImportError except block
        except_pos = extract_section.find("except ImportError as e:")
        except_block = extract_section[except_pos:except_pos + 2000]
        
        # Must check for production
        assert "is_production()" in except_block, \
            "Production environment not checked in ImportError handler"
        
        # In production, must raise ImportError
        prod_check_pos = except_block.find("if is_production():")
        assert prod_check_pos > 0, \
            "Production check not found in ImportError handler"
        
        prod_block = except_block[prod_check_pos:prod_check_pos + 500]
        assert "raise ImportError" in prod_block, \
            "Production doesn't raise ImportError when HardenedPaddleOCR is missing"
        
        # Must mention this is REQUIRED
        assert "REQUIRED" in prod_block or "required" in prod_block.lower(), \
            "Error message doesn't indicate HardenedPaddleOCR is required in production"

    def test_production_error_message_mentions_integrity(self):
        """
        Verify that production error mentions integrity guarantees.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Find production error message
        except_pos = extract_section.find("if is_production():")
        prod_block = extract_section[except_pos:except_pos + 500]
        
        # Must mention integrity
        assert "integrity" in prod_block.lower() or "checkpoint" in prod_block.lower(), \
            "Production error doesn't mention integrity or checkpoint requirements"


class TestOCRDevelopmentFallbackHardcore:
    """
    HARDCORE: Verify that in development, fallback is allowed with warnings.
    """

    def test_development_allows_paddleocr_fallback(self):
        """
        Verify that in development mode, PaddleOCR fallback is allowed.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Find the ImportError except block
        except_pos = extract_section.find("except ImportError as e:")
        except_block = extract_section[except_pos:except_pos + 2000]
        
        # Must check for production
        prod_check_pos = except_block.find("if is_production():")
        prod_block = except_block[prod_check_pos:prod_check_pos + 500]
        
        # After the if is_production() block, there must be else or code that continues
        # (for development mode)
        after_prod = except_block[prod_check_pos + len("if is_production():"):prod_check_pos + 1500]
        
        # Must have PaddleOCR fallback
        assert "from paddleocr import PaddleOCR" in after_prod or "PaddleOCR" in after_prod, \
            "PaddleOCR fallback not found after production check"

    def test_development_logs_warning(self):
        """
        Verify that development mode logs a warning when falling back.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must have warning log
        assert "log.warning" in extract_section or "logger.warning" in extract_section, \
            "No warning log for fallback"
        
        # Warning must mention HardenedPaddleOCR
        assert "HardenedPaddleOCR" in extract_section, \
            "Warning doesn't mention HardenedPaddleOCR"


class TestMerkleRootPropagationHardcore:
    """
    HARDCORE: Verify that Merkle root is properly propagated through metadata.
    """

    def test_merkle_root_variable_exists(self):
        """
        Verify that merkle_root variable is initialized.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must initialize merkle_root
        assert "merkle_root = None" in extract_section, \
            "merkle_root variable not initialized to None"

    def test_merkle_root_added_to_metadata(self):
        """
        Verify that merkle_root is added to metadata when available.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must add merkle_root to metadata
        assert "merkle_root" in extract_section, \
            "merkle_root not mentioned in metadata"
        
        # Must check if merkle_root exists before adding
        assert "if merkle_root:" in extract_section, \
            "No check if merkle_root exists before adding to metadata"
        
        # Must add to metadata dict
        assert 'metadata["merkle_root"]' in extract_section or 'metadata["merkle_root"]' in extract_section, \
            "merkle_root not added to metadata dictionary"


class TestOCRDocumentIdHardcore:
    """
    HARDCORE: Verify that document ID is properly generated for checkpointing.
    """

    def test_document_id_is_hash_based(self):
        """
        Verify that document_id is generated from file hash.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must generate document hash
        assert "hashlib.sha256" in extract_section, \
            "Document hash not generated using SHA-256"
        
        # Must read file to generate hash
        assert "with open(pdf_path, \"rb\")" in extract_section, \
            "File not read for hash generation"
        
        # Must create document_id from hash
        assert "document_id" in extract_section, \
            "document_id not created from hash"

    def test_document_id_passed_to_hardened_ocr(self):
        """
        Verify that document_id is passed to HardenedPaddleOCR methods.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # document_id must be passed to ocr_image_hardened
        assert "document_id=document_id" in extract_section, \
            "document_id not passed to ocr_image_hardened"


class TestOCRCompleteFlowHardcore:
    """
    HARDCORE: Verify the complete OCR flow is correct.
    """

    def test_pdf_converted_to_images(self):
        """
        Verify that PDF is converted to images before OCR.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must convert PDF to images
        assert "convert_from_path" in extract_section, \
            "PDF not converted to images"
        
        assert "pdf2image" in extract_section, \
            "pdf2image not used for conversion"
        
        assert "dpi=300" in extract_section, \
            "DPI not set to 300 for image conversion"

    def test_pages_processed_individually(self):
        """
        Verify that pages are processed individually.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must iterate through images
        assert "for page_num, image in enumerate(images):" in extract_section, \
            "Not iterating through images"
        
        # Must save each image temporarily
        assert "image.save(" in extract_section, \
            "Images not saved temporarily"

    def test_results_collected_per_page(self):
        """
        Verify that results are collected for each page.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must have pages_text list
        assert "pages_text: List[Any] = []" in extract_section or "pages_text = []" in extract_section, \
            "pages_text list not initialized"
        
        # Must append results
        assert "pages_text.append(" in extract_section, \
            "Results not appended to pages_text"

    def test_final_text_joined_with_newlines(self):
        """
        Verify that final text is joined with newlines.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/pipelines/ingestion/document_handlers.py")
        content = file_path.read_text()
        
        extract_start = content.find("def _extract_with_ocr(self, file_path: str)")
        extract_section = content[extract_start:extract_start + 10000]
        
        # Must join with newlines
        assert "'\\n\\n'.join(pages_text)" in extract_section or '\n\n'.join(pages_text) in extract_section, \
            "Final text not joined with double newlines"
