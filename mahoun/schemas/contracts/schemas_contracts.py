"""
Contract Schemas for Schemas Module

This module defines formal input/output contracts for the schemas module's public interfaces.
All contracts are Pydantic models with validation rules.

Module: mahoun.schemas
Responsibility: Pydantic models and validation schemas for legal document structures
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Dict, Any, Optional, List


# ============================================================================
# Schema Validation Contracts
# ============================================================================

class SchemaValidationInput(BaseModel):
    """
    Contract for schema validation input.
    
    Validates: Schema validation request parameters
    """
    schema_name: str = Field(..., min_length=1, max_length=255, description="Name of schema to validate against")
    data: Dict[str, Any] = Field(..., description="Data to validate")
    strict: bool = Field(default=False, description="Whether to use strict validation")
    
    @field_validator('schema_name')
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        """Validate schema name format."""
        if not v.strip():
            raise ValueError("schema_name cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class SchemaValidationOutput(BaseModel):
    """
    Contract for schema validation output.
    
    Validates: Schema validation result structure
    """
    is_valid: bool = Field(..., description="Whether data is valid")
    errors: List[str] = Field(..., description="List of validation errors")
    warnings: List[str] = Field(..., description="List of validation warnings")
    validated_data: Optional[Dict[str, Any]] = Field(default=None, description="Validated data if successful")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Field Validation Contracts
# ============================================================================

class FieldValidationRule(BaseModel):
    """
    Contract for field validation rule.
    
    Validates: Individual field validation rule structure
    """
    field_name: str = Field(..., min_length=1, description="Name of field")
    rule_type: str = Field(..., min_length=1, description="Type of validation rule")
    rule_value: Any = Field(..., description="Value for the rule")
    error_message: Optional[str] = Field(default=None, description="Custom error message")
    
    @field_validator('field_name')
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field name format."""
        if not v.strip():
            raise ValueError("field_name cannot be empty or whitespace")
        return v.strip()
    
    @field_validator('rule_type')
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        """Validate rule type format."""
        if not v.strip():
            raise ValueError("rule_type cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class FieldConstraints(BaseModel):
    """
    Contract for field constraints.
    
    Validates: Field constraint specification
    """
    field_name: str = Field(..., min_length=1, description="Name of field")
    required: bool = Field(default=False, description="Whether field is required")
    min_value: Optional[float] = Field(default=None, description="Minimum value")
    max_value: Optional[float] = Field(default=None, description="Maximum value")
    pattern: Optional[str] = Field(default=None, description="Regex pattern")
    allowed_values: Optional[List[Any]] = Field(default=None, description="List of allowed values")
    
    @field_validator('field_name')
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field name format."""
        if not v.strip():
            raise ValueError("field_name cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Schema Metadata Contracts
# ============================================================================

class SchemaMetadata(BaseModel):
    """
    Contract for schema metadata.
    
    Validates: Schema metadata structure
    """
    schema_name: str = Field(..., min_length=1, description="Schema name")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Schema version (semver)")
    description: str = Field(..., description="Schema description")
    fields: List[str] = Field(..., description="List of field names")
    required_fields: List[str] = Field(..., description="List of required field names")
    optional_fields: List[str] = Field(..., description="List of optional field names")
    
    @field_validator('schema_name')
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        """Validate schema name format."""
        if not v.strip():
            raise ValueError("schema_name cannot be empty or whitespace")
        return v.strip()
    
    model_config = ConfigDict(frozen=True)


class SchemaVersion(BaseModel):
    """
    Contract for schema version.
    
    Validates: Schema version information
    """
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="Version number (semver)")
    released_at: str = Field(..., description="Release timestamp (ISO 8601)")
    changes: List[str] = Field(..., description="List of changes in this version")
    breaking_changes: bool = Field(default=False, description="Whether version has breaking changes")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Error Contracts
# ============================================================================

class SchemaValidationError(BaseModel):
    """
    Contract for schema validation errors.
    
    Error Types:
    - ValidationError: Data does not match schema
    - SchemaNotFound: Requested schema does not exist
    - IncompatibleVersion: Schema version mismatch
    """
    error_type: str = Field(..., pattern="^(ValidationError|SchemaNotFound|IncompatibleVersion)$")
    message: str = Field(..., min_length=1, description="Error message")
    field_name: Optional[str] = Field(default=None, description="Field that caused error")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Contract Registry
# ============================================================================

__all__ = [
    # Schema Validation
    "SchemaValidationInput",
    "SchemaValidationOutput",
    
    # Field Validation
    "FieldValidationRule",
    "FieldConstraints",
    
    # Schema Metadata
    "SchemaMetadata",
    "SchemaVersion",
    
    # Errors
    "SchemaValidationError",
]
