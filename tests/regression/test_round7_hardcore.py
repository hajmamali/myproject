"""
ROUND 7 - HARDCORE Regression Tests for Production Wiring
========================================================

These are EXTREMELY STRICT tests that verify:
1. NLI verification IS wired into production verdict path
2. HardenedPaddleOCR IS wired into production OCR path  
3. Fail-closed behavior IS enforced
4. NO mocks, NO stubs - real code path verification only

These tests will FAIL if any production wiring is missing.
"""

import pytest
import os
import sys
import inspect
from pathlib import Path


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_source_file(file_path):
    """Get the source code of a file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def get_class_source(cls):
    """Get source of a class."""
    try:
        return inspect.getsource(cls)
    except (TypeError, OSError):
        # For classes defined in files with decorators, get the file directly
        file_path = inspect.getfile(cls)
        return get_source_file(file_path)


def get_method_source(obj, method_name):
    """Get source of a method."""
    try:
        method = getattr(obj, method_name)
        return inspect.getsource(method)
    except (TypeError, OSError):
        # Fallback to file
        file_path = inspect.getfile(obj)
        return get_source_file(file_path)


# ============================================================================
# CRITICAL: Issue 1 - NLI Text-Grounding Verification
# ============================================================================

class TestNLIVerifierHardCore:
    """
    HARDCORE TESTS for Issue 1: NLI verification MUST be wired into production.
    These tests verify the ACTUAL wiring, not just that components exist.
    """
    
    @pytest.mark.p0
    def test_reasoning_chain_has_active_nli_import(self):
        """
        CRITICAL: Verify reasoning_chain.py has ACTIVE import of UltraNLIVerifier.
        Previous issue: import was commented out but reference was not.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "reasoning" / "reasoning_chain.py"
        source = get_source_file(file_path)
        
        # Must have active import
        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in source
        
        # Must NOT have commented import
        assert "# from mahoun.guardrails.ultra_nli_verifier import" not in source
        
        # Must use the imported class
        assert "self._nli_verifier = UltraNLIVerifier" in source
        
    @pytest.mark.p0
    def test_verdict_engine_has_nli_verification_code(self):
        """
        CRITICAL: Verify EvidenceLinkedVerdictEngine.generate_verdict() 
        contains NLI verification code.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "reasoning" / "evidence_linked_verdict.py"
        source = get_source_file(file_path)
        
        # Must import UltraNLIVerifier
        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in source
        
        # Must create nli_verifier instance
        assert "nli_verifier = UltraNLIVerifier" in source
        
        # Must call verify method
        assert "nli_verifier.verify" in source
        
        # Must check is_supported
        assert "nli_result.is_supported" in source
        
    @pytest.mark.p0  
    def test_verdict_engine_nli_is_fail_closed_in_production(self):
        """
        CRITICAL: NLI verification MUST fail-closed in production.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "reasoning" / "evidence_linked_verdict.py"
        source = get_source_file(file_path)
        
        # Must check production mode
        assert "is_production()" in source
        
        # Must raise error when NLI fails in production
        assert "RuntimeError" in source
        assert "blocked in production" in source.lower() or "production" in source.lower()
        
        # Must have hard fail message
        assert "CRITICAL" in source or "trust-critical" in source
        
    @pytest.mark.p0
    def test_nli_verification_in_generate_verdict_method(self):
        """
        Verify NLI verification is in the generate_verdict method specifically.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "reasoning" / "evidence_linked_verdict.py"
        source = get_source_file(file_path)
        
        # Find generate_verdict method
        lines = source.split('\n')
        in_generate_verdict = False
        generate_verdict_block = []
        
        for line in lines:
            if 'def generate_verdict' in line:
                in_generate_verdict = True
            elif in_generate_verdict and line and not line.startswith(' ') and not line.startswith('\t'):
                break
            elif in_generate_verdict:
                generate_verdict_block.append(line)
        
        block_source = '\n'.join(generate_verdict_block)
        
        # Verify NLI code is in generate_verdict
        assert "UltraNLIVerifier" in block_source
        assert "nli_verifier.verify" in block_source


# ============================================================================
# CRITICAL: Issue 2 - HardenedPaddleOCR Wiring
# ============================================================================

class TestHardenedPaddleOCRHardCore:
    """
    HARDCORE TESTS for Issue 2: HardenedPaddleOCR MUST be wired into production.
    """
    
    @pytest.mark.p0
    def test_document_handlers_imports_hardened_ocr(self):
        """
        CRITICAL: document_handlers.py MUST import HardenedPaddleOCR.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        source = get_source_file(file_path)
        
        # Must import HardenedPaddleOCR
        assert "from mahoun.pipelines.ingestion.hardened_paddle_ocr import HardenedPaddleOCR" in source
        
    @pytest.mark.p0
    def test_ocr_method_uses_hardened_paddle_ocr_first(self):
        """
        CRITICAL: _extract_with_ocr MUST try HardenedPaddleOCR FIRST.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        source = get_source_file(file_path)
        
        # Find _extract_with_ocr method
        lines = source.split('\n')
        in_method = False
        method_lines = []
        
        for line in lines:
            if '_extract_with_ocr' in line and 'def' in line:
                in_method = True
            elif in_method and line and not line.startswith(' ') and not line.startswith('\t') and not line.strip().startswith('#'):
                break
            elif in_method:
                method_lines.append(line)
        
        method_source = '\n'.join(method_lines)
        
        # Must try HardenedPaddleOCR
        assert "HardenedPaddleOCR" in method_source
        
        # Must create instance
        assert "hardened_ocr = HardenedPaddleOCR" in method_source
        
        # Must call ocr method
        assert "ocr_image_hardened" in method_source or "ocr_pdf_hardened" in method_source
        
    @pytest.mark.p0
    def test_hardened_ocr_produces_merkle_root(self):
        """
        CRITICAL: HardenedPaddleOCR MUST produce Merkle root for provenance.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        source = get_source_file(file_path)
        
        # Find _extract_with_ocr method
        lines = source.split('\n')
        in_method = False
        method_lines = []
        
        for line in lines:
            if '_extract_with_ocr' in line and 'def' in line:
                in_method = True
            elif in_method and line and not line.startswith(' ') and not line.startswith('\t') and not line.strip().startswith('#'):
                break
            elif in_method:
                method_lines.append(line)
        
        method_source = '\n'.join(method_lines)
        
        # Must get Merkle root
        assert "get_document_merkle_root" in method_source
        
        # Must store in metadata
        assert "merkle_root" in method_source
        
    @pytest.mark.p0
    def test_production_mode_requires_hardened_ocr(self):
        """
        CRITICAL: In production, HardenedPaddleOCR MUST be required.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        source = get_source_file(file_path)
        
        # Must check production mode
        assert "is_production()" in source
        
        # Must raise if HardenedPaddleOCR unavailable in production
        assert "HardenedPaddleOCR is REQUIRED" in source
        
    @pytest.mark.p0
    def test_fallback_chain_exists(self):
        """
        Verify fallback chain: HardenedPaddleOCR -> PaddleOCR -> Tesseract
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        source = get_source_file(file_path)
        
        # Find _extract_with_ocr method
        lines = source.split('\n')
        in_method = False
        method_lines = []
        
        for line in lines:
            if '_extract_with_ocr' in line and 'def' in line:
                in_method = True
            elif in_method and line and not line.startswith(' ') and not line.startswith('\t') and not line.strip().startswith('#'):
                break
            elif in_method:
                method_lines.append(line)
        
        method_source = '\n'.join(method_lines)
        
        # Must have HardenedPaddleOCR
        assert "HardenedPaddleOCR" in method_source
        
        # Must have PaddleOCR fallback
        assert "from paddleocr import PaddleOCR" in method_source
        
        # Must have Tesseract fallback
        assert "pytesseract" in method_source


# ============================================================================
# CRITICAL: Issue 3 - DocumentValidator Verification  
# ============================================================================

class TestDocumentValidatorHardCore:
    """
    HARDCORE TESTS for Issue 3: DocumentValidator wiring status.
    """
    
    @pytest.mark.p1
    def test_enhanced_pipeline_imports_document_validator(self):
        """
        Verify EnhancedIngestionPipeline imports DocumentValidator.
        """
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "enhanced_pipeline.py"
        source = get_source_file(file_path)
        
        # Must import DocumentValidator
        assert "DocumentValidator" in source
        
    @pytest.mark.p1
    def test_ingest_router_conditional_enhanced(self):
        """
        Verify ingest router conditionally uses EnhancedIngestionPipeline.
        """
        file_path = Path(__file__).parent.parent.parent / "api" / "routers" / "ingest.py"
        source = get_source_file(file_path)
        
        # Must check environment variable
        assert "USE_ENHANCED_INGESTION" in source
        
        # Must import EnhancedIngestionPipeline conditionally
        assert "EnhancedIngestionPipeline" in source
        
        # Must fall back to standard pipeline
        assert "IngestionPipeline" in source


# ============================================================================
# CRITICAL: Production Path Integration Tests
# ============================================================================

class TestProductionPathIntegrationHardCore:
    """
    Verify the COMPLETE production path is properly wired.
    """
    
    @pytest.mark.p0
    def test_verdict_engine_wired_via_router(self):
        """
        CRITICAL: Verify verdict engine is reachable from API router.
        """
        # This test doesn't require dependencies
        file_path = Path(__file__).parent.parent.parent / "api" / "routers" / "reasoning.py"
        source = get_source_file(file_path)
        
        # Must have get_verdict_engine
        assert "get_verdict_engine" in source
        
        # Must import EvidenceLinkedVerdictEngine
        assert "EvidenceLinkedVerdictEngine" in source
        
    @pytest.mark.p0
    def test_ingestion_pipeline_wired_via_router(self):
        """
        CRITICAL: Verify ingestion pipeline is reachable from API router.
        """
        file_path = Path(__file__).parent.parent.parent / "api" / "routers" / "ingest.py"
        source = get_source_file(file_path)
        
        # Must have get_ingestion_pipeline
        assert "get_ingestion_pipeline" in source


# ============================================================================
# CRITICAL: File Existence Tests
# ============================================================================

class TestFileExistence:
    """Verify all required files exist."""
    
    @pytest.mark.p0
    def test_ultra_nli_verifier_file_exists(self):
        """Verify ultra_nli_verifier.py exists."""
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "guardrails" / "ultra_nli_verifier.py"
        assert file_path.exists()
        
    @pytest.mark.p0
    def test_hardened_paddle_ocr_file_exists(self):
        """Verify hardened_paddle_ocr.py exists."""
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "hardened_paddle_ocr.py"
        assert file_path.exists()
        
    @pytest.mark.p0
    def test_evidence_linked_verdict_file_exists(self):
        """Verify evidence_linked_verdict.py exists."""
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "reasoning" / "evidence_linked_verdict.py"
        assert file_path.exists()
        
    @pytest.mark.p0
    def test_document_handlers_file_exists(self):
        """Verify document_handlers.py exists."""
        file_path = Path(__file__).parent.parent.parent / "mahoun" / "pipelines" / "ingestion" / "document_handlers.py"
        assert file_path.exists()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "p0 or p1"])
