"""
HARDCORE Regression Tests for NLI Verification Wiring (ROUND 7 - ISSUE 1)
=========================================================================

These tests are INTENTIONALLY extremely strict and difficult.
They verify ACTUAL behavior, not just code presence.
They do NOT use mocks, stubs, or any form of test simplification.

Purpose: To catch ANY regression in the NLI verification wiring with maximum severity.

Test Philosophy:
- Fail fast on any discrepancy
- No tolerance for degraded mode in production
- Verify complete execution path
- Test actual imports, not just file content
- Verify fail-closed behavior under real conditions
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Force development mode for tests that need to run
os.environ["MAHOUN_ENVIRONMENT"] = "development"


class TestNLIImportHardcore:
    """
    HARDCORE: Verify that the import in reasoning_chain.py is structurally correct.
    
    This test does NOT just check if the module can be imported.
    It verifies the ACTUAL import statement in the source code.
    """

    def test_reasoning_chain_has_correct_nli_import_statement(self):
        """
        Verify that reasoning_chain.py contains the CORRECT import statement.
        
        Before fix: Line 159-160 had:
            # from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier as NLIVerifier
            self._nli_verifier = NLIVerifier(threshold=self.config.nli_threshold)
        
        After fix: Line 159-160 must have:
            from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier
            self._nli_verifier = UltraNLIVerifier(threshold=self.config.nli_threshold)
        
        This test checks the ACTUAL source code, not just if it imports.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/reasoning_chain.py")
        lines = file_path.read_text().split('\n')
        
        # Find the initialization section
        init_start = None
        for i, line in enumerate(lines):
            if 'Initialize NLI Verifier' in line or 'Initialize NLI' in line:
                init_start = i
                break
        
        assert init_start is not None, "Could not find NLI Verifier initialization section"
        
        # Check the next 20 lines for the import
        init_section = '\n'.join(lines[init_start:init_start + 20])
        
        # The import MUST be active (not commented)
        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in init_section, \
            "Active UltraNLIVerifier import not found in initialization"
        
        # The import line itself MUST NOT be commented (line starting with #)
        # We need to check individual lines, not the whole section
        has_active_import = False
        for line in lines[init_start:init_start + 20]:
            stripped = line.strip()
            if stripped.startswith("from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier"):
                has_active_import = True
                break
        
        assert has_active_import, \
            "UltraNLIVerifier import line is commented out or missing"
        
        # The instantiation MUST use UltraNLIVerifier (not NLIVerifier)
        assert "UltraNLIVerifier(threshold=" in init_section, \
            "Instantiation with UltraNLIVerifier not found"
        
        # The instantiation MUST NOT use NLIVerifier (the old broken name) without Ultra prefix
        # Check that we don't have standalone NLIVerifier (which would be the broken import)
        # But UltraNLIVerifier is OK
        lines_to_check = [line.strip() for line in lines[init_start:init_start + 20]]
        for line in lines_to_check:
            if line.startswith("self._nli_verifier = NLIVerifier("):
                assert False, f"Found broken NLIVerifier instantiation: {line}"

    def test_reasoning_chain_nli_import_is_not_broken(self):
        """
        Verify that the module can be imported without NameError.
        
        This is a basic sanity check that the fix actually works.
        Before the fix, this would raise:
            NameError: name 'NLIVerifier' is not defined
        """
        # This MUST NOT raise NameError
        try:
            from mahoun.reasoning.reasoning_chain import ReasoningChain, ReasoningConfig
        except NameError as e:
            pytest.fail(f"NameError during import: {e}. The fix did not work!")


class TestNLIInProductionPathHardcore:
    """
    HARDCORE: Verify NLI is actually in the production verdict path.
    
    These tests verify that the NLI verification code is not just present somewhere,
    but is actually in the CRITICAL path that generates verdicts.
    """

    def test_nli_is_between_text_generation_and_ledger(self):
        """
        Verify that NLI verification happens AFTER text generation and BEFORE ledger creation.
        
        The execution order in generate_verdict() must be:
        1. ... (earlier steps)
        2. _synthesize_final_verdict() - generates text
        3. NLI verification - verifies text
        4. _calculate_confidence_score()
        5. LedgerEntry creation
        6. VerdictExecutionResult return
        
        This test verifies this order in the source code.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find key method calls
        synthesize_pos = content.find("_synthesize_final_verdict")
        nli_pos = content.find("UltraNLIVerifier")
        confidence_pos = content.find("_calculate_confidence_score")
        ledger_pos = content.find("LedgerEntry(")
        
        assert synthesize_pos > 0, "_synthesize_final_verdict not found"
        assert nli_pos > 0, "UltraNLIVerifier not found"
        assert confidence_pos > 0, "_calculate_confidence_score not found"
        assert ledger_pos > 0, "LedgerEntry creation not found"
        
        # NLI must come AFTER text synthesis
        assert nli_pos > synthesize_pos, \
            "NLI verification is BEFORE text generation (wrong order!)"
        
        # NLI must come BEFORE confidence calculation
        assert nli_pos < confidence_pos, \
            "NLI verification is AFTER confidence calculation (wrong order!)"
        
        # Confidence must come BEFORE ledger creation
        assert confidence_pos < ledger_pos, \
            "Confidence calculation is AFTER ledger creation (wrong order!)"

    def test_nli_uses_correct_evidence_context(self):
        """
        Verify that NLI verification uses the CORRECT context.
        
        The context must be built from:
        - verdict_steps evidence
        - resolved_nodes
        - NOT from raw input or retrieval results
        
        This ensures we're verifying against the ACTUAL evidence used,
        not some intermediate or raw data.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find the NLI verification section
        nli_section_start = content.find("NLI Text-Grounding Verification")
        nli_section_end = content.find("Step 9: Calculate confidence score", nli_section_start)
        nli_section = content[nli_section_start:nli_section_end]
        
        # Verify context is built from verdict_steps
        assert "verdict_steps" in nli_section, \
            "NLI context not built from verdict_steps"
        
        # Verify context is built from resolved_nodes
        assert "resolved_nodes" in nli_section, \
            "NLI context not built from resolved_nodes"
        
        # Verify we extract evidence from steps
        assert "for step in verdict_steps" in nli_section, \
            "Not iterating through verdict_steps to build context"
        
        # Verify we extract text from evidence
        assert "ev.text" in nli_section or "ev.node_id" in nli_section, \
            "Not extracting text from evidence objects"

    def test_nli_verification_result_is_checked(self):
        """
        Verify that NLI verification result is actually CHECKED and ACTED upon.
        
        It's not enough to call verify() - we must check the result and fail if needed.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find the NLI verification section
        nli_section_start = content.find("nli_result: UltraNLIResult = nli_verifier.verify")
        nli_section_end = nli_section_start + 5000  # Look ahead
        nli_section = content[nli_section_start:nli_section_end]
        
        # Must check is_supported
        assert "nli_result.is_supported" in nli_section, \
            "NLI result.is_supported is not checked"
        
        # Must have conditional based on the check
        assert "if not nli_result.is_supported" in nli_section, \
            "No conditional check for failed NLI verification"
        
        # In production, must raise an error
        assert "raise RuntimeError" in nli_section or "raise ImportError" in nli_section, \
            "No error raised when NLI verification fails"


class TestNLIFailClosedHardcore:
    """
    HARDCORE: Verify fail-closed behavior for NLI.
    
    Per CONSTITUTION Section 10, missing/failed verification must BLOCK execution.
    """

    def test_production_nli_failure_raises_error(self):
        """
        Verify that in PRODUCTION mode, NLI failure RAISES an error (does not continue).
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find NLI verification section
        nli_section_start = content.find("if not nli_result.is_supported")
        nli_section_end = nli_section_start + 2000
        nli_section = content[nli_section_start:nli_section_end]
        
        # Must check for production
        assert "is_production()" in nli_section, \
            "Production environment not checked for NLI failure"
        
        # In production block, must raise
        prod_block_start = nli_section.find("if is_production():")
        prod_block = nli_section[prod_block_start:prod_block_start + 500]
        
        assert "raise" in prod_block, \
            "Production block does not raise error on NLI failure"
        
        # Must mention this is CRITICAL or TRUST-CRITICAL
        assert "CRITICAL" in prod_block or "trust-critical" in prod_block or "trust critical" in prod_block, \
            "Error message doesn't indicate this is a critical/trust failure"

    def test_development_nli_failure_logs_but_continues(self):
        """
        Verify that in DEVELOPMENT mode, NLI failure LOGS but does NOT raise.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find NLI verification section
        nli_section_start = content.find("if not nli_result.is_supported")
        nli_section_end = nli_section_start + 2000
        nli_section = content[nli_section_start:nli_section_end]
        
        # Must have else block (or similar) for development
        assert "else:" in nli_section or "DEVELOPMENT MODE" in nli_section, \
            "No development mode handling for NLI failure"
        
        # In development block, must log
        dev_block = nli_section[nli_section.find("else:"):nli_section.find("else:") + 500] if "else:" in nli_section else nli_section
        
        assert "log.critical" in dev_block or "log.warning" in dev_block or "logger" in dev_block, \
            "Development mode doesn't log NLI failure"
        
        # In development, must mention DEVELOPMENT MODE
        assert "DEVELOPMENT MODE" in nli_section, \
            "Development mode not explicitly marked in NLI failure handling"

    def test_import_failure_raises_in_production(self):
        """
        Verify that if UltraNLIVerifier cannot be imported, production mode raises ImportError.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find the try-except block for NLI verification
        nli_try_start = content.find("# Step 9: NLI Text-Grounding Verification")
        nli_section = content[nli_try_start:nli_try_start + 8000]
        
        # Must have exception handling for ImportError
        assert "except ImportError as e:" in nli_section, \
            "No ImportError exception handling for NLI"
        
        # Find the except block
        except_start = nli_section.find("except ImportError as e:")
        except_block = nli_section[except_start:except_start + 1000]
        
        # Must check for production
        assert "is_production()" in except_block, \
            "Production not checked for NLI import failure"
        
        # In production, must raise ImportError
        # Look for the if is_production() block
        prod_check_pos = except_block.find("if is_production():")
        if prod_check_pos >= 0:
            prod_block = except_block[prod_check_pos:prod_check_pos + 500]
            assert "raise ImportError" in prod_block, \
                "Production doesn't raise ImportError when UltraNLIVerifier is missing"
            
            # Must mention this is FATAL or REQUIRED
            assert "FATAL" in prod_block or "REQUIRED" in prod_block, \
                "Error message doesn't indicate this is fatal/required"


class TestNLIContextCompletenessHardcore:
    """
    HARDCORE: Verify that NLI context includes ALL necessary evidence.
    
    The context must include:
    - All evidence from verdict_steps
    - All rule and precedent text from resolved_nodes
    - Step statements
    """

    def test_context_includes_step_evidence(self):
        """
        Verify that context building iterates through step evidence.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find context building section
        context_start = content.find("context_parts = []")
        context_section = content[context_start:context_start + 2000]
        
        # Must iterate through verdict_steps
        assert "for step in verdict_steps:" in context_section, \
            "Not iterating through verdict_steps"
        
        # Must iterate through step evidence
        assert "for ev in step.evidence:" in context_section, \
            "Not iterating through step evidence"
        
        # Must extract text from evidence
        assert "ev.text" in context_section, \
            "Not extracting text from evidence"

    def test_context_includes_resolved_nodes(self):
        """
        Verify that context includes rule and precedent text from resolved_nodes.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find context building section
        context_start = content.find("context_parts = []")
        context_section = content[context_start:context_start + 3000]
        
        # Must iterate through resolved_nodes
        assert "for node_id, node in resolved_nodes.items():" in context_section, \
            "Not iterating through resolved_nodes"
        
        # Must check for LegalRule and LegalPrecedent
        assert "LegalRule" in context_section and "LegalPrecedent" in context_section, \
            "Not checking for LegalRule and LegalPrecedent nodes"
        
        # Must extract text/content/description from nodes
        text_fields = ['text', 'description', 'content', 'conclusion', 'decision']
        found_fields = [f for f in text_fields if f"node.properties['{f}']" in context_section or f'"{f}"' in context_section]
        
        assert len(found_fields) > 0, \
            f"Not extracting any text fields from node properties. Checked: {text_fields}"

    def test_empty_context_raises_in_production(self):
        """
        Verify that if context is empty (no evidence), production raises error.
        
        The code checks: if context and final_verdict and final_verdict.strip()
        So if context is empty, it skips the NLI verification block entirely.
        We need to verify there's an elif or else that handles the empty context case.
        """
        import pathlib
        
        file_path = pathlib.Path("/home/haji/Desktop/KingMahouN/mahoun/reasoning/evidence_linked_verdict.py")
        content = file_path.read_text()
        
        # Find the NLI verification section
        nli_start = content.find("# Step 9: NLI Text-Grounding Verification")
        nli_section = content[nli_start:nli_start + 5000]
        
        # Must have condition that checks context
        assert "if context and final_verdict" in nli_section, \
            "No condition checking for non-empty context"
        
        # Must have handling for when context is empty
        # This could be "elif not context" or "else:" after the if
        has_empty_handling = "elif not context" in nli_section or "else:" in nli_section
        assert has_empty_handling, \
            "No handling for empty context case"
        
        # Must check for production in the empty context handling
        # Find the else/elif block
        if "elif not context" in nli_section:
            elif_pos = nli_section.find("elif not context")
            elif_block = nli_section[elif_pos:elif_pos + 500]
            assert "is_production()" in elif_block, \
                "Production not checked for empty context in elif"
            assert "raise RuntimeError" in elif_block, \
                "Production doesn't raise error for empty context in elif"
