"""
Ledger Module Contract Tests
=============================

Tests for ledger module Pydantic contracts.

These tests validate:
- LedgerEntry structure compliance
- Write operation contracts
- Verification contracts
- Invariant enforcement (EL-I1, EL-I4, EL-I6, EL-I7)

IMPORTANT: These are CONTRACT tests, not BEHAVIOR tests.
They test data structure integrity and invariant enforcement.

Validates Requirements: 2.1, 2.2, 2.3
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from mahoun.schemas.contracts.ledger_contracts import (
    # Ledger Entry
    LedgerEntryContract,
    # Write Operations
    WriteLedgerInput,
    WriteLedgerOutput,
    WriteLedgerError,
    # Verification
    VerifyIntegrityInput,
    VerifyIntegrityOutput,
    VerifyIntegrityError,
    # Invariants
    InvariantSpecContract,
    GetInvariantsOutput,
    # Configuration
    LedgerBackendConfig,
)


# ============================================================================
# LedgerEntryContract Tests
# ============================================================================

class TestLedgerEntryContract:
    """Test LedgerEntryContract validation (enforces EL-I1, EL-I4, EL-I7)."""
    
    def test_valid_entry(self):
        """Valid ledger entry should pass."""
        entry = LedgerEntryContract(
            verdict_id="verdict_12345",
            case_id="case_67890",
            referenced_ltm_nodes=["rule_1", "statute_220"],
            referenced_facts=["fact_0", "fact_1"],
            confidence=0.92,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now()
        )
        assert entry.verdict_id == "verdict_12345"
        assert len(entry.referenced_ltm_nodes) == 2
    
    def test_entry_with_optional_fields(self):
        """Entry with optional fields should pass."""
        entry = LedgerEntryContract(
            verdict_id="verdict_12345",
            case_id="case_67890",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_0"],
            confidence=0.85,
            invariant_version="1.0.0",
            guard_mode="WARN",
            created_at=datetime.now(),
            event_type="verdict_published",
            request_id="req_abc123"
        )
        assert entry.event_type == "verdict_published"
        assert entry.request_id == "req_abc123"
    
    def test_empty_ltm_nodes_fails_el_i1(self):
        """Empty LTM nodes should fail (EL-I1: Evidence Required)."""
        with pytest.raises(ValidationError) as exc_info:
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=[],  # EL-I1 violation
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
        # Pydantic min_length=1 catches this before custom validator
        assert "referenced_ltm_nodes" in str(exc_info.value)
    
    def test_long_fact_reference_fails_el_i7(self):
        """Long fact reference should fail (EL-I7: Privacy violation)."""
        with pytest.raises(ValidationError) as exc_info:
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["a" * 501],  # Too long - possible value leak
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
        assert "EL-I7" in str(exc_info.value) or "privacy" in str(exc_info.value).lower()
    
    def test_sensitive_pattern_in_fact_fails_el_i7(self):
        """Sensitive pattern in fact reference should fail (EL-I7)."""
        with pytest.raises(ValidationError) as exc_info:
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["ssn_123456789"],  # Sensitive pattern
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
        assert "EL-I7" in str(exc_info.value) or "sensitive" in str(exc_info.value).lower()
    
    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_0"],
                confidence=1.5,  # Invalid
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
    
    def test_invalid_guard_mode_fails(self):
        """Invalid guard_mode should fail."""
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="INVALID",  # Must be OFF|WARN|STRICT|AUDIT
                created_at=datetime.now()
            )
    
    def test_entry_is_frozen_el_i4(self):
        """Entry should be immutable (EL-I4: Immutability)."""
        entry = LedgerEntryContract(
            verdict_id="verdict_12345",
            case_id="case_67890",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_0"],
            confidence=0.85,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now()
        )
        # Pydantic frozen=True prevents modification
        with pytest.raises((ValidationError, AttributeError)):
            entry.verdict_id = "modified"  # Should fail
    
    def test_extra_fields_forbidden(self):
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(),
                extra_field="not_allowed"
            )


# ============================================================================
# WriteLedgerInput Tests
# ============================================================================

class TestWriteLedgerInput:
    """Test WriteLedgerInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = WriteLedgerInput(
            entry=LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
        )
        assert inp.entry.verdict_id == "verdict_12345"


# ============================================================================
# WriteLedgerOutput Tests
# ============================================================================

class TestWriteLedgerOutput:
    """Test WriteLedgerOutput validation (enforces EL-I6)."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = WriteLedgerOutput(
            entry_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
            prev_hash="genesis",
            written_at=datetime.now(),
            success=True
        )
        assert output.entry_hash == "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"
        assert output.prev_hash == "genesis"
    
    def test_output_with_prev_hash(self):
        """Output with previous hash should pass."""
        output = WriteLedgerOutput(
            entry_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
            prev_hash="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            written_at=datetime.now()
        )
        assert len(output.prev_hash) == 64
    
    def test_invalid_hash_length_fails(self):
        """Hash with wrong length should fail."""
        with pytest.raises(ValidationError):
            WriteLedgerOutput(
                entry_hash="short_hash",  # Too short
                prev_hash="genesis",
                written_at=datetime.now()
            )
    
    def test_invalid_hash_chars_fails(self):
        """Hash with invalid characters should fail."""
        with pytest.raises(ValidationError):
            WriteLedgerOutput(
                entry_hash="g1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",  # 'g' invalid
                prev_hash="genesis",
                written_at=datetime.now()
            )
    
    def test_invalid_prev_hash_fails(self):
        """Invalid prev_hash should fail."""
        with pytest.raises(ValidationError):
            WriteLedgerOutput(
                entry_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
                prev_hash="invalid",  # Not 'genesis' or 64-char hex
                written_at=datetime.now()
            )


# ============================================================================
# WriteLedgerError Tests
# ============================================================================

class TestWriteLedgerError:
    """Test WriteLedgerError validation (enforces EL-I3)."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = WriteLedgerError(
            error_type="storage_failure",
            message="Failed to write to ledger backend",
            blocks_verdict=True
        )
        assert error.error_type == "storage_failure"
        assert error.blocks_verdict is True  # EL-I3: Verdict blocking
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "evidence_required",
            "privacy_violation",
            "storage_failure",
            "hash_computation_failed"
        ]
        for error_type in valid_types:
            error = WriteLedgerError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type
    
    def test_invalid_error_type_fails(self):
        """Invalid error_type should fail."""
        with pytest.raises(ValidationError):
            WriteLedgerError(
                error_type="invalid_type",
                message="message"
            )


# ============================================================================
# VerifyIntegrityOutput Tests
# ============================================================================

class TestVerifyIntegrityOutput:
    """Test VerifyIntegrityOutput validation (enforces EL-I6)."""
    
    def test_valid_output_chain_valid(self):
        """Valid output with valid chain should pass."""
        output = VerifyIntegrityOutput(
            is_valid=True,
            total_entries=1523,
            first_invalid_entry=None,
            verification_timestamp=datetime.now()
        )
        assert output.is_valid is True
        assert output.total_entries == 1523
    
    def test_valid_output_chain_invalid(self):
        """Valid output with invalid chain should pass."""
        output = VerifyIntegrityOutput(
            is_valid=False,
            total_entries=1523,
            first_invalid_entry="verdict_500",
            verification_timestamp=datetime.now()
        )
        assert output.is_valid is False
        assert output.first_invalid_entry == "verdict_500"
    
    def test_negative_total_entries_fails(self):
        """Negative total_entries should fail."""
        with pytest.raises(ValidationError):
            VerifyIntegrityOutput(
                is_valid=True,
                total_entries=-1,
                verification_timestamp=datetime.now()
            )


# ============================================================================
# VerifyIntegrityError Tests
# ============================================================================

class TestVerifyIntegrityError:
    """Test VerifyIntegrityError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = VerifyIntegrityError(
            error_type="backend_unavailable",
            message="Storage backend not accessible"
        )
        assert error.error_type == "backend_unavailable"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "backend_unavailable",
            "corrupted_data",
            "verification_timeout"
        ]
        for error_type in valid_types:
            error = VerifyIntegrityError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type


# ============================================================================
# InvariantSpecContract Tests
# ============================================================================

class TestInvariantSpecContract:
    """Test InvariantSpecContract validation."""
    
    def test_valid_invariant(self):
        """Valid invariant spec should pass."""
        inv = InvariantSpecContract(
            id="EL-I1",
            name="Evidence Required",
            description="Every published verdict must have at least one evidence reference.",
            enforced_at=["mahoun/ledger/guards.py::validate_entry"],
            failure_consequence="Verdicts without evidence can be published."
        )
        assert inv.id == "EL-I1"
        assert len(inv.enforced_at) == 1
    
    def test_invalid_id_format_fails(self):
        """Invalid ID format should fail."""
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="INVALID",  # Must match EL-I[0-9]+
                name="Test",
                description="Test description",
                enforced_at=["test.py"],
                failure_consequence="Test consequence"
            )
    
    def test_empty_enforced_at_fails(self):
        """Empty enforced_at should fail."""
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="EL-I1",
                name="Test",
                description="Test description",
                enforced_at=[],  # Must have at least one
                failure_consequence="Test consequence"
            )


# ============================================================================
# GetInvariantsOutput Tests
# ============================================================================

class TestGetInvariantsOutput:
    """Test GetInvariantsOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetInvariantsOutput(
            invariants=[
                InvariantSpecContract(
                    id="EL-I1",
                    name="Evidence Required",
                    description="Test",
                    enforced_at=["test.py"],
                    failure_consequence="Test"
                ),
                InvariantSpecContract(
                    id="EL-I2",
                    name="No Reasoning Persistence",
                    description="Test",
                    enforced_at=["test.py"],
                    failure_consequence="Test"
                )
            ],
            invariant_version="1.0.0",
            total_invariants=2
        )
        assert output.total_invariants == 2
        assert len(output.invariants) == 2
    
    def test_empty_invariants_fails(self):
        """Empty invariants list should fail."""
        with pytest.raises(ValidationError):
            GetInvariantsOutput(
                invariants=[],
                invariant_version="1.0.0",
                total_invariants=0
            )


# ============================================================================
# LedgerBackendConfig Tests
# ============================================================================

class TestLedgerBackendConfig:
    """Test LedgerBackendConfig validation."""
    
    def test_valid_jsonl_config(self):
        """Valid JSONL config should pass."""
        config = LedgerBackendConfig(
            backend_type="jsonl",
            path="data/ledger/evidence.jsonl"
        )
        assert config.backend_type == "jsonl"
        assert config.path == "data/ledger/evidence.jsonl"
    
    def test_valid_sqlite_config(self):
        """Valid SQLite config should pass."""
        config = LedgerBackendConfig(
            backend_type="sqlite",
            path="data/ledger/evidence.db"
        )
        assert config.backend_type == "sqlite"
    
    def test_valid_noop_config(self):
        """Valid noop config (no path) should pass."""
        config = LedgerBackendConfig(
            backend_type="noop"
        )
        assert config.backend_type == "noop"
        assert config.path is None
    
    def test_jsonl_without_path_fails(self):
        """JSONL config without path should fail."""
        with pytest.raises(ValidationError):
            LedgerBackendConfig(
                backend_type="jsonl"
                # Missing path
            )
    
    def test_sqlite_without_path_fails(self):
        """SQLite config without path should fail."""
        with pytest.raises(ValidationError):
            LedgerBackendConfig(
                backend_type="sqlite"
                # Missing path
            )
    
    def test_invalid_backend_type_fails(self):
        """Invalid backend_type should fail."""
        with pytest.raises(ValidationError):
            LedgerBackendConfig(
                backend_type="invalid",
                path="test.db"
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestLedgerContractIntegration:
    """Test contract integration and invariant enforcement."""
    
    def test_complete_write_workflow(self):
        """Complete write workflow should validate."""
        # Input
        inp = WriteLedgerInput(
            entry=LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1", "statute_220"],
                referenced_facts=["fact_0", "fact_1"],
                confidence=0.92,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(),
                event_type="verdict_published"
            )
        )
        
        # Output
        output = WriteLedgerOutput(
            entry_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
            prev_hash="genesis",
            written_at=datetime.now(),
            success=True
        )
        
        assert inp.entry.verdict_id == "verdict_12345"
        assert output.success is True
        assert len(output.entry_hash) == 64
    
    def test_invariant_enforcement_chain(self):
        """Invariant enforcement should work across contracts."""
        # EL-I1: Evidence required
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=[],  # EL-I1 violation
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
        
        # EL-I7: Privacy preservation
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["email_user@example.com"],  # Sensitive pattern
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now()
            )
    
    def test_extra_forbid_at_all_levels(self):
        """extra='forbid' should be enforced at all nesting levels."""
        # Extra field at entry level
        with pytest.raises(ValidationError):
            LedgerEntryContract(
                verdict_id="verdict_12345",
                case_id="case_67890",
                referenced_ltm_nodes=["rule_1"],
                referenced_facts=["fact_0"],
                confidence=0.85,
                invariant_version="1.0.0",
                guard_mode="STRICT",
                created_at=datetime.now(),
                extra_field="not_allowed"
            )
        
        # Extra field at output level
        with pytest.raises(ValidationError):
            WriteLedgerOutput(
                entry_hash="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
                prev_hash="genesis",
                written_at=datetime.now(),
                extra_field="not_allowed"
            )
