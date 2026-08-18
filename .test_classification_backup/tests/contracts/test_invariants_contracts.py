"""
Invariants Module Contract Tests
=================================

Tests for invariants module Pydantic contracts.

These tests validate:
- Invariant specification structure
- Validation function contracts
- Version management contracts
- Registry operations

IMPORTANT: These are CONTRACT tests, not BEHAVIOR tests.
They test data structure integrity, not invariant enforcement logic.

Validates Requirements: 2.1, 2.2, 2.3
"""

import pytest
from pydantic import ValidationError

from mahoun.schemas.contracts.invariants_contracts import (
    # Invariant Specification
    InvariantSpecContract,
    GetInvariantByIdInput,
    GetInvariantByIdOutput,
    GetInvariantByIdError,
    GetAllInvariantsOutput,
    # Version Management
    InvariantVersionContract,
    GetCurrentVersionOutput,
    GetVersionHistoryOutput,
    # Validation
    ValidateInvariantInput,
    ValidateInvariantOutput,
    ValidateInvariantError,
    # Registry
    RegisterInvariantInput,
    RegisterInvariantOutput,
    RegisterInvariantError,
    # Statistics
    InvariantStatisticsContract,
    GetInvariantStatisticsOutput,
)


# ============================================================================
# InvariantSpecContract Tests
# ============================================================================

class TestInvariantSpecContract:
    """Test InvariantSpecContract validation."""
    
    def test_valid_invariant_spec(self):
        """Valid invariant spec should pass."""
        spec = InvariantSpecContract(
            id="EL-I1",
            name="Evidence Required",
            description="Every published verdict must have at least one evidence reference.",
            enforced_at=["mahoun/ledger/guards.py::validate_entry"],
            failure_consequence="Verdicts without evidence can be published."
        )
        assert spec.id == "EL-I1"
        assert len(spec.enforced_at) == 1
    
    def test_different_prefix_valid(self):
        """Invariant with different prefix should pass."""
        spec = InvariantSpecContract(
            id="G-I1",
            name="Graph Invariant",
            description="Test",
            enforced_at=["test.py"],
            failure_consequence="Test"
        )
        assert spec.id == "G-I1"
    
    def test_invalid_id_format_fails(self):
        """Invalid ID format should fail."""
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="INVALID",  # Must match [A-Z]+-I[0-9]+
                name="Test",
                description="Test",
                enforced_at=["test.py"],
                failure_consequence="Test"
            )
    
    def test_empty_enforced_at_fails(self):
        """Empty enforced_at should fail."""
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="EL-I1",
                name="Test",
                description="Test",
                enforced_at=[],  # Must have at least one
                failure_consequence="Test"
            )
    
    def test_spec_is_frozen(self):
        """Invariant spec should be immutable."""
        spec = InvariantSpecContract(
            id="EL-I1",
            name="Test",
            description="Test",
            enforced_at=["test.py"],
            failure_consequence="Test"
        )
        with pytest.raises((ValidationError, AttributeError)):
            spec.id = "modified"
    
    def test_extra_fields_forbidden(self):
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="EL-I1",
                name="Test",
                description="Test",
                enforced_at=["test.py"],
                failure_consequence="Test",
                extra_field="not_allowed"
            )


# ============================================================================
# GetInvariantByIdInput Tests
# ============================================================================

class TestGetInvariantByIdInput:
    """Test GetInvariantByIdInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = GetInvariantByIdInput(invariant_id="EL-I1")
        assert inp.invariant_id == "EL-I1"
    
    def test_invalid_id_format_fails(self):
        """Invalid ID format should fail."""
        with pytest.raises(ValidationError):
            GetInvariantByIdInput(invariant_id="INVALID")


# ============================================================================
# GetInvariantByIdOutput Tests
# ============================================================================

class TestGetInvariantByIdOutput:
    """Test GetInvariantByIdOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetInvariantByIdOutput(
            invariant=InvariantSpecContract(
                id="EL-I1",
                name="Test",
                description="Test",
                enforced_at=["test.py"],
                failure_consequence="Test"
            )
        )
        assert output.invariant.id == "EL-I1"


# ============================================================================
# GetInvariantByIdError Tests
# ============================================================================

class TestGetInvariantByIdError:
    """Test GetInvariantByIdError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = GetInvariantByIdError(
            error_type="invariant_not_found",
            message="Invariant EL-I99 not found"
        )
        assert error.error_type == "invariant_not_found"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = ["invariant_not_found", "invalid_id_format"]
        for error_type in valid_types:
            error = GetInvariantByIdError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type


# ============================================================================
# GetAllInvariantsOutput Tests
# ============================================================================

class TestGetAllInvariantsOutput:
    """Test GetAllInvariantsOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetAllInvariantsOutput(
            invariants=[
                InvariantSpecContract(
                    id="EL-I1",
                    name="Test1",
                    description="Test",
                    enforced_at=["test.py"],
                    failure_consequence="Test"
                ),
                InvariantSpecContract(
                    id="EL-I2",
                    name="Test2",
                    description="Test",
                    enforced_at=["test.py"],
                    failure_consequence="Test"
                )
            ],
            total_count=2
        )
        assert output.total_count == 2
        assert len(output.invariants) == 2
    
    def test_mismatched_count_fails(self):
        """Mismatched total_count should fail."""
        with pytest.raises(ValidationError):
            GetAllInvariantsOutput(
                invariants=[
                    InvariantSpecContract(
                        id="EL-I1",
                        name="Test",
                        description="Test",
                        enforced_at=["test.py"],
                        failure_consequence="Test"
                    )
                ],
                total_count=5  # Doesn't match list length
            )
    
    def test_empty_invariants_fails(self):
        """Empty invariants list should fail."""
        with pytest.raises(ValidationError):
            GetAllInvariantsOutput(
                invariants=[],
                total_count=0
            )


# ============================================================================
# InvariantVersionContract Tests
# ============================================================================

class TestInvariantVersionContract:
    """Test InvariantVersionContract validation."""
    
    def test_valid_version(self):
        """Valid version should pass."""
        version = InvariantVersionContract(
            version="1.0.0",
            description="Initial release"
        )
        assert version.version == "1.0.0"
    
    def test_invalid_version_format_fails(self):
        """Invalid version format should fail."""
        with pytest.raises(ValidationError):
            InvariantVersionContract(
                version="1.0",  # Must be X.Y.Z
                description="Test"
            )
    
    def test_version_is_frozen(self):
        """Version should be immutable."""
        version = InvariantVersionContract(
            version="1.0.0",
            description="Test"
        )
        with pytest.raises((ValidationError, AttributeError)):
            version.version = "2.0.0"


# ============================================================================
# GetCurrentVersionOutput Tests
# ============================================================================

class TestGetCurrentVersionOutput:
    """Test GetCurrentVersionOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetCurrentVersionOutput(current_version="1.1.0")
        assert output.current_version == "1.1.0"
    
    def test_invalid_version_format_fails(self):
        """Invalid version format should fail."""
        with pytest.raises(ValidationError):
            GetCurrentVersionOutput(current_version="invalid")


# ============================================================================
# GetVersionHistoryOutput Tests
# ============================================================================

class TestGetVersionHistoryOutput:
    """Test GetVersionHistoryOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetVersionHistoryOutput(
            versions=[
                InvariantVersionContract(
                    version="1.0.0",
                    description="Initial"
                ),
                InvariantVersionContract(
                    version="1.1.0",
                    description="Update"
                )
            ],
            current_version="1.1.0",
            total_versions=2
        )
        assert output.total_versions == 2
        assert output.current_version == "1.1.0"


# ============================================================================
# ValidateInvariantInput Tests
# ============================================================================

class TestValidateInvariantInput:
    """Test ValidateInvariantInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = ValidateInvariantInput(
            invariant_id="EL-I1",
            context={"verdict_id": "v123", "evidence_count": 5}
        )
        assert inp.invariant_id == "EL-I1"
        assert "verdict_id" in inp.context


# ============================================================================
# ValidateInvariantOutput Tests
# ============================================================================

class TestValidateInvariantOutput:
    """Test ValidateInvariantOutput validation."""
    
    def test_valid_output_success(self):
        """Valid output with success should pass."""
        output = ValidateInvariantOutput(
            is_valid=True,
            invariant_id="EL-I1",
            violation_message=None
        )
        assert output.is_valid is True
        assert output.violation_message is None
    
    def test_valid_output_failure(self):
        """Valid output with failure should pass."""
        output = ValidateInvariantOutput(
            is_valid=False,
            invariant_id="EL-I1",
            violation_message="Evidence count is zero"
        )
        assert output.is_valid is False
        assert output.violation_message is not None
    
    def test_invalid_without_message_fails(self):
        """Invalid without violation_message should fail."""
        with pytest.raises(ValidationError):
            ValidateInvariantOutput(
                is_valid=False,
                invariant_id="EL-I1",
                violation_message=None  # Required when invalid
            )


# ============================================================================
# ValidateInvariantError Tests
# ============================================================================

class TestValidateInvariantError:
    """Test ValidateInvariantError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = ValidateInvariantError(
            error_type="invariant_not_found",
            message="Invariant not found"
        )
        assert error.error_type == "invariant_not_found"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = [
            "invariant_not_found",
            "invalid_context",
            "validation_failed"
        ]
        for error_type in valid_types:
            error = ValidateInvariantError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type


# ============================================================================
# RegisterInvariantInput Tests
# ============================================================================

class TestRegisterInvariantInput:
    """Test RegisterInvariantInput validation."""
    
    def test_valid_input(self):
        """Valid input should pass."""
        inp = RegisterInvariantInput(
            invariant=InvariantSpecContract(
                id="NEW-I1",
                name="New Invariant",
                description="Test",
                enforced_at=["test.py"],
                failure_consequence="Test"
            )
        )
        assert inp.invariant.id == "NEW-I1"


# ============================================================================
# RegisterInvariantOutput Tests
# ============================================================================

class TestRegisterInvariantOutput:
    """Test RegisterInvariantOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = RegisterInvariantOutput(
            invariant_id="NEW-I1",
            success=True
        )
        assert output.invariant_id == "NEW-I1"
        assert output.success is True


# ============================================================================
# RegisterInvariantError Tests
# ============================================================================

class TestRegisterInvariantError:
    """Test RegisterInvariantError validation."""
    
    def test_valid_error(self):
        """Valid error should pass."""
        error = RegisterInvariantError(
            error_type="duplicate_id",
            message="Invariant ID already exists"
        )
        assert error.error_type == "duplicate_id"
    
    def test_all_valid_error_types(self):
        """All documented error types should be valid."""
        valid_types = ["duplicate_id", "invalid_spec"]
        for error_type in valid_types:
            error = RegisterInvariantError(
                error_type=error_type,
                message=f"Test {error_type}"
            )
            assert error.error_type == error_type


# ============================================================================
# InvariantStatisticsContract Tests
# ============================================================================

class TestInvariantStatisticsContract:
    """Test InvariantStatisticsContract validation."""
    
    def test_valid_statistics(self):
        """Valid statistics should pass."""
        stats = InvariantStatisticsContract(
            invariant_id="EL-I1",
            total_checks=1000,
            violations=5,
            success_rate=0.995,
            last_checked="2024-01-15T10:30:00Z"
        )
        assert stats.total_checks == 1000
        assert stats.violations == 5
        assert stats.success_rate == 0.995
    
    def test_default_statistics(self):
        """Default statistics should pass."""
        stats = InvariantStatisticsContract(invariant_id="EL-I1")
        assert stats.total_checks == 0
        assert stats.violations == 0
        assert stats.success_rate == 1.0
    
    def test_negative_checks_fails(self):
        """Negative checks should fail."""
        with pytest.raises(ValidationError):
            InvariantStatisticsContract(
                invariant_id="EL-I1",
                total_checks=-1
            )
    
    def test_success_rate_out_of_range_fails(self):
        """Success rate outside [0, 1] should fail."""
        with pytest.raises(ValidationError):
            InvariantStatisticsContract(
                invariant_id="EL-I1",
                success_rate=1.5
            )


# ============================================================================
# GetInvariantStatisticsOutput Tests
# ============================================================================

class TestGetInvariantStatisticsOutput:
    """Test GetInvariantStatisticsOutput validation."""
    
    def test_valid_output(self):
        """Valid output should pass."""
        output = GetInvariantStatisticsOutput(
            statistics=[
                InvariantStatisticsContract(
                    invariant_id="EL-I1",
                    total_checks=1000,
                    violations=5,
                    success_rate=0.995
                ),
                InvariantStatisticsContract(
                    invariant_id="EL-I2",
                    total_checks=500,
                    violations=0,
                    success_rate=1.0
                )
            ],
            total_invariants=2,
            overall_success_rate=0.997
        )
        assert output.total_invariants == 2
        assert output.overall_success_rate == 0.997


# ============================================================================
# Integration Tests
# ============================================================================

class TestInvariantsContractIntegration:
    """Test contract integration and workflows."""
    
    def test_complete_invariant_workflow(self):
        """Complete invariant workflow should validate."""
        # Register
        register_input = RegisterInvariantInput(
            invariant=InvariantSpecContract(
                id="TEST-I1",
                name="Test Invariant",
                description="Test description",
                enforced_at=["test.py::test_func"],
                failure_consequence="Test consequence"
            )
        )
        
        register_output = RegisterInvariantOutput(
            invariant_id="TEST-I1",
            success=True
        )
        
        # Validate
        validate_input = ValidateInvariantInput(
            invariant_id="TEST-I1",
            context={"test_field": "value"}
        )
        
        validate_output = ValidateInvariantOutput(
            is_valid=True,
            invariant_id="TEST-I1"
        )
        
        # Get by ID
        get_output = GetInvariantByIdOutput(
            invariant=register_input.invariant
        )
        
        assert register_output.invariant_id == "TEST-I1"
        assert validate_output.is_valid is True
        assert get_output.invariant.id == "TEST-I1"
    
    def test_version_management_workflow(self):
        """Version management workflow should validate."""
        # Current version
        current = GetCurrentVersionOutput(current_version="1.1.0")
        
        # History
        history = GetVersionHistoryOutput(
            versions=[
                InvariantVersionContract(
                    version="1.0.0",
                    description="Initial"
                ),
                InvariantVersionContract(
                    version="1.1.0",
                    description="Added privacy"
                )
            ],
            current_version="1.1.0",
            total_versions=2
        )
        
        assert current.current_version == history.current_version
        assert len(history.versions) == history.total_versions
    
    def test_extra_forbid_at_all_levels(self):
        """extra='forbid' should be enforced at all nesting levels."""
        # Extra field at spec level
        with pytest.raises(ValidationError):
            InvariantSpecContract(
                id="EL-I1",
                name="Test",
                description="Test",
                enforced_at=["test.py"],
                failure_consequence="Test",
                extra_field="not_allowed"
            )
        
        # Extra field at output level
        with pytest.raises(ValidationError):
            GetAllInvariantsOutput(
                invariants=[
                    InvariantSpecContract(
                        id="EL-I1",
                        name="Test",
                        description="Test",
                        enforced_at=["test.py"],
                        failure_consequence="Test"
                    )
                ],
                total_count=1,
                extra_field="not_allowed"
            )
