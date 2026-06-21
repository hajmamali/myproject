"""
Invariants Module Contracts
============================

Formal contracts for the invariants module's public interfaces.

These contracts define:
- Invariant specification structure
- Validation function contracts
- Version management contracts

All contracts use `extra="forbid"` to ensure clean data structures.

Validates Requirements: 2.1, 2.2, 2.3
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# Invariant Specification Contracts
# ============================================================================

class InvariantSpecContract(BaseModel):
    """
    Contract for system invariant specification.
    
    Validates: Requirement 2.2 - Invariant metadata structure
    
    An invariant is a non-negotiable guarantee that maintains system integrity.
    """
    id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="Invariant ID (e.g., 'EL-I1', 'G-I1')"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable invariant name"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Detailed invariant description"
    )
    enforced_at: List[str] = Field(
        ...,
        min_length=1,
        description="List of enforcement points (module::function paths)"
    )
    failure_consequence: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Consequence of invariant violation"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,  # Invariant specs are immutable
        json_schema_extra={
            "example": {
                "id": "EL-I1",
                "name": "Evidence Required",
                "description": "Every published verdict must have at least one evidence reference.",
                "enforced_at": ["mahoun/ledger/guards.py::validate_entry"],
                "failure_consequence": "Verdicts without evidence can be published, leading to hallucinated conclusions."
            }
        }
    )


class GetInvariantByIdInput(BaseModel):
    """
    Input contract for get_invariant_by_id()
    
    Validates: Requirement 2.1 - Query input
    """
    invariant_id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="Invariant ID to retrieve"
    )
    
    model_config = ConfigDict(extra="forbid")


class GetInvariantByIdOutput(BaseModel):
    """
    Output contract for get_invariant_by_id()
    
    Validates: Requirement 2.2 - Query output
    """
    invariant: InvariantSpecContract = Field(
        ...,
        description="Retrieved invariant specification"
    )
    
    model_config = ConfigDict(extra="forbid")


class GetInvariantByIdError(BaseModel):
    """
    Error contract for get_invariant_by_id() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - invariant_not_found: Requested invariant does not exist
    - invalid_id_format: ID format is invalid
    """
    error_type: str = Field(
        ...,
        pattern="^(invariant_not_found|invalid_id_format)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


class GetAllInvariantsOutput(BaseModel):
    """
    Output contract for get_all_invariants()
    
    Validates: Requirement 2.2 - List all invariants
    """
    invariants: List[InvariantSpecContract] = Field(
        ...,
        min_length=1,
        description="List of all registered invariants"
    )
    total_count: int = Field(
        ...,
        ge=1,
        description="Total number of invariants"
    )
    
    @field_validator('total_count')
    @classmethod
    def validate_count_matches_list(cls, v: int, info) -> int:
        """Ensure total_count matches invariants list length."""
        if 'invariants' in info.data:
            if v != len(info.data['invariants']):
                raise ValueError("total_count must match length of invariants list")
        return v
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Invariant Version Contracts
# ============================================================================

class InvariantVersionContract(BaseModel):
    """
    Contract for invariant version information.
    
    Validates: Requirement 2.2 - Version metadata
    """
    version: str = Field(
        ...,
        pattern="^[0-9]+\\.[0-9]+\\.[0-9]+$",
        description="Semantic version (e.g., '1.0.0')"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Version description/changelog entry"
    )
    
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "example": {
                "version": "1.0.0",
                "description": "Initial evidence ledger invariants"
            }
        }
    )


class GetCurrentVersionOutput(BaseModel):
    """
    Output contract for getting current invariant version.
    
    Validates: Requirement 2.2 - Current version output
    """
    current_version: str = Field(
        ...,
        pattern="^[0-9]+\\.[0-9]+\\.[0-9]+$",
        description="Current invariant version"
    )
    
    model_config = ConfigDict(extra="forbid")


class GetVersionHistoryOutput(BaseModel):
    """
    Output contract for getting version history.
    
    Validates: Requirement 2.2 - Version history output
    """
    versions: List[InvariantVersionContract] = Field(
        ...,
        min_length=1,
        description="List of all versions in chronological order"
    )
    current_version: str = Field(
        ...,
        pattern="^[0-9]+\\.[0-9]+\\.[0-9]+$",
        description="Current active version"
    )
    total_versions: int = Field(
        ...,
        ge=1,
        description="Total number of versions"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Validation Contracts
# ============================================================================

class ValidateInvariantInput(BaseModel):
    """
    Input contract for invariant validation functions.
    
    Validates: Requirement 2.1 - Validation input
    """
    invariant_id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="Invariant to validate"
    )
    context: Dict[str, Any] = Field(
        ...,
        description="Validation context (varies by invariant)"
    )
    
    model_config = ConfigDict(extra="forbid")


class ValidateInvariantOutput(BaseModel):
    """
    Output contract for invariant validation functions.
    
    Validates: Requirement 2.2 - Validation output
    """
    is_valid: bool = Field(
        ...,
        description="Whether invariant is satisfied"
    )
    invariant_id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="Invariant that was validated"
    )
    violation_message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Violation message if invalid"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional validation details"
    )
    
    @field_validator('violation_message')
    @classmethod
    def validate_message_when_invalid(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure violation_message is provided when invalid."""
        if 'is_valid' in info.data:
            if not info.data['is_valid'] and not v:
                raise ValueError("violation_message required when is_valid=False")
        return v
    
    model_config = ConfigDict(extra="forbid")


class ValidateInvariantError(BaseModel):
    """
    Error contract for validation failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - invariant_not_found: Invariant does not exist
    - invalid_context: Context missing required fields
    - validation_failed: Validation process failed
    """
    error_type: str = Field(
        ...,
        pattern="^(invariant_not_found|invalid_context|validation_failed)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Invariant Registry Contracts
# ============================================================================

class RegisterInvariantInput(BaseModel):
    """
    Input contract for registering new invariant.
    
    Validates: Requirement 2.1 - Registration input
    """
    invariant: InvariantSpecContract = Field(
        ...,
        description="Invariant specification to register"
    )
    
    model_config = ConfigDict(extra="forbid")


class RegisterInvariantOutput(BaseModel):
    """
    Output contract for registering new invariant.
    
    Validates: Requirement 2.2 - Registration output
    """
    invariant_id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="ID of registered invariant"
    )
    success: bool = Field(
        default=True,
        description="Registration success status"
    )
    
    model_config = ConfigDict(extra="forbid")


class RegisterInvariantError(BaseModel):
    """
    Error contract for registration failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - duplicate_id: Invariant ID already exists
    - invalid_spec: Invariant specification is invalid
    """
    error_type: str = Field(
        ...,
        pattern="^(duplicate_id|invalid_spec)$",
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Invariant Statistics Contracts
# ============================================================================

class InvariantStatisticsContract(BaseModel):
    """
    Contract for invariant enforcement statistics.
    
    Validates: Requirement 2.2 - Statistics structure
    """
    invariant_id: str = Field(
        ...,
        pattern="^[A-Z]+-I[0-9]+$",
        description="Invariant identifier"
    )
    total_checks: int = Field(
        default=0,
        ge=0,
        description="Total number of validation checks"
    )
    violations: int = Field(
        default=0,
        ge=0,
        description="Number of violations detected"
    )
    success_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Success rate (1.0 - violations/total_checks)"
    )
    last_checked: Optional[str] = Field(
        None,
        description="ISO timestamp of last check"
    )
    
    model_config = ConfigDict(extra="forbid")


class GetInvariantStatisticsOutput(BaseModel):
    """
    Output contract for getting invariant statistics.
    
    Validates: Requirement 2.2 - Statistics output
    """
    statistics: List[InvariantStatisticsContract] = Field(
        ...,
        description="Statistics for all invariants"
    )
    total_invariants: int = Field(
        ...,
        ge=0,
        description="Total number of invariants tracked"
    )
    overall_success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall success rate across all invariants"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Invariant Specification
    "InvariantSpecContract",
    "GetInvariantByIdInput",
    "GetInvariantByIdOutput",
    "GetInvariantByIdError",
    "GetAllInvariantsOutput",
    # Version Management
    "InvariantVersionContract",
    "GetCurrentVersionOutput",
    "GetVersionHistoryOutput",
    # Validation
    "ValidateInvariantInput",
    "ValidateInvariantOutput",
    "ValidateInvariantError",
    # Registry
    "RegisterInvariantInput",
    "RegisterInvariantOutput",
    "RegisterInvariantError",
    # Statistics
    "InvariantStatisticsContract",
    "GetInvariantStatisticsOutput",
]
