"""
Contract Tests for Schemas Module

These tests validate that schemas module contracts are correctly defined and enforceable.
Tests are independent of behavior - they only validate schema compliance.

Test Categories:
1. Meta-Schema Tests: Validate schema validation contracts
2. Output Contract Tests: Validate output schemas are complete
3. Error Contract Tests: Validate error schemas cover all failure modes
"""

import pytest
from pydantic import ValidationError

from mahoun.schemas.contracts.schemas_contracts import (
    # Schema validation contracts
    SchemaValidationInput,
    SchemaValidationOutput,
    SchemaValidationError,
    
    # Field validation contracts
    FieldValidationRule,
    FieldConstraints,
    
    # Schema metadata contracts
    SchemaMetadata,
    SchemaVersion,
)


# ============================================================================
# Schema Validation Contract Tests
# ============================================================================

class TestSchemaValidationInput:
    """Test SchemaValidationInput contract."""
    
    def test_valid_schema_validation_input(self):
        """Test valid schema validation input accepted."""
        input_data = SchemaValidationInput(
            schema_name="VerdictStruct",
            data={"case_number": "123", "court_name": "Supreme Court"},
            strict=True
        )
        assert input_data.schema_name == "VerdictStruct"
        assert input_data.strict is True
    
    def test_empty_schema_name_rejected(self):
        """Test empty schema name rejected."""
        with pytest.raises(ValidationError):
            SchemaValidationInput(
                schema_name="",
                data={}
            )
    
    def test_missing_data_rejected(self):
        """Test missing data rejected."""
        with pytest.raises(ValidationError):
            SchemaValidationInput(
                schema_name="TestSchema"
            )
    
    def test_strict_defaults_to_false(self):
        """Test strict defaults to False."""
        input_data = SchemaValidationInput(
            schema_name="TestSchema",
            data={}
        )
        assert input_data.strict is False


class TestSchemaValidationOutput:
    """Test SchemaValidationOutput contract."""
    
    def test_valid_schema_validation_output(self):
        """Test valid schema validation output accepted."""
        output = SchemaValidationOutput(
            is_valid=True,
            errors=[],
            warnings=["Field X is deprecated"],
            validated_data={"field": "value"}
        )
        assert output.is_valid is True
        assert len(output.warnings) == 1
    
    def test_invalid_with_errors(self):
        """Test invalid output with errors."""
        output = SchemaValidationOutput(
            is_valid=False,
            errors=["Missing required field: case_number"],
            warnings=[],
            validated_data=None
        )
        assert output.is_valid is False
        assert len(output.errors) == 1
    
    def test_validated_data_optional(self):
        """Test validated_data is optional."""
        output = SchemaValidationOutput(
            is_valid=False,
            errors=["Error"],
            warnings=[]
        )
        assert output.validated_data is None
    
    def test_immutability(self):
        """Test output is immutable."""
        output = SchemaValidationOutput(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        with pytest.raises(ValidationError):
            output.is_valid = False


# ============================================================================
# Field Validation Contract Tests
# ============================================================================

class TestFieldValidationRule:
    """Test FieldValidationRule contract."""
    
    def test_valid_field_validation_rule(self):
        """Test valid field validation rule accepted."""
        rule = FieldValidationRule(
            field_name="case_number",
            rule_type="required",
            rule_value=True,
            error_message="Case number is required"
        )
        assert rule.field_name == "case_number"
        assert rule.rule_type == "required"
    
    def test_empty_field_name_rejected(self):
        """Test empty field name rejected."""
        with pytest.raises(ValidationError):
            FieldValidationRule(
                field_name="",
                rule_type="required",
                rule_value=True
            )
    
    def test_empty_rule_type_rejected(self):
        """Test empty rule type rejected."""
        with pytest.raises(ValidationError):
            FieldValidationRule(
                field_name="test_field",
                rule_type="",
                rule_value=True
            )
    
    def test_error_message_optional(self):
        """Test error message is optional."""
        rule = FieldValidationRule(
            field_name="test_field",
            rule_type="min_length",
            rule_value=5
        )
        assert rule.error_message is None


class TestFieldConstraints:
    """Test FieldConstraints contract."""
    
    def test_valid_field_constraints(self):
        """Test valid field constraints accepted."""
        constraints = FieldConstraints(
            field_name="confidence",
            required=True,
            min_value=0.0,
            max_value=1.0,
            pattern=None,
            allowed_values=None
        )
        assert constraints.required is True
        assert constraints.min_value == 0.0
        assert constraints.max_value == 1.0
    
    def test_empty_field_name_rejected(self):
        """Test empty field name rejected."""
        with pytest.raises(ValidationError):
            FieldConstraints(
                field_name="",
                required=True
            )
    
    def test_all_constraints_optional_except_field_name(self):
        """Test all constraints optional except field_name."""
        constraints = FieldConstraints(
            field_name="test_field"
        )
        assert constraints.required is False
        assert constraints.min_value is None
        assert constraints.max_value is None
    
    def test_pattern_validation(self):
        """Test pattern constraint."""
        constraints = FieldConstraints(
            field_name="case_number",
            pattern=r"^\d{4}-\d{4}$"
        )
        assert constraints.pattern == r"^\d{4}-\d{4}$"
    
    def test_allowed_values_validation(self):
        """Test allowed values constraint."""
        constraints = FieldConstraints(
            field_name="status",
            allowed_values=["pending", "approved", "rejected"]
        )
        assert len(constraints.allowed_values) == 3


# ============================================================================
# Schema Metadata Contract Tests
# ============================================================================

class TestSchemaMetadata:
    """Test SchemaMetadata contract."""
    
    def test_valid_schema_metadata(self):
        """Test valid schema metadata accepted."""
        metadata = SchemaMetadata(
            schema_name="VerdictStruct",
            version="1.0.0",
            description="Complete verdict structure",
            fields=["case_meta", "parties", "claims"],
            required_fields=["case_meta"],
            optional_fields=["parties", "claims"]
        )
        assert metadata.schema_name == "VerdictStruct"
        assert metadata.version == "1.0.0"
        assert len(metadata.fields) == 3
    
    def test_empty_schema_name_rejected(self):
        """Test empty schema name rejected."""
        with pytest.raises(ValidationError):
            SchemaMetadata(
                schema_name="",
                version="1.0.0",
                description="Test",
                fields=[],
                required_fields=[],
                optional_fields=[]
            )
    
    def test_invalid_version_format_rejected(self):
        """Test invalid version format rejected."""
        with pytest.raises(ValidationError):
            SchemaMetadata(
                schema_name="TestSchema",
                version="invalid",
                description="Test",
                fields=[],
                required_fields=[],
                optional_fields=[]
            )
    
    def test_valid_version_formats(self):
        """Test valid version formats accepted."""
        valid_versions = ["1.0.0", "2.1.3", "0.0.1", "10.20.30"]
        for version in valid_versions:
            metadata = SchemaMetadata(
                schema_name="TestSchema",
                version=version,
                description="Test",
                fields=[],
                required_fields=[],
                optional_fields=[]
            )
            assert metadata.version == version
    
    def test_empty_fields_allowed(self):
        """Test empty fields list allowed."""
        metadata = SchemaMetadata(
            schema_name="EmptySchema",
            version="1.0.0",
            description="Empty schema",
            fields=[],
            required_fields=[],
            optional_fields=[]
        )
        assert len(metadata.fields) == 0


class TestSchemaVersion:
    """Test SchemaVersion contract."""
    
    def test_valid_schema_version(self):
        """Test valid schema version accepted."""
        version = SchemaVersion(
            version="2.0.0",
            released_at="2026-02-09T10:00:00Z",
            changes=["Added new field: verdict_sections", "Deprecated field: old_field"],
            breaking_changes=False
        )
        assert version.version == "2.0.0"
        assert version.breaking_changes is False
    
    def test_invalid_version_format_rejected(self):
        """Test invalid version format rejected."""
        with pytest.raises(ValidationError):
            SchemaVersion(
                version="v1.0",
                released_at="2026-02-09T10:00:00Z",
                changes=[]
            )
    
    def test_empty_changes_allowed(self):
        """Test empty changes list allowed."""
        version = SchemaVersion(
            version="1.0.0",
            released_at="2026-02-09T10:00:00Z",
            changes=[]
        )
        assert len(version.changes) == 0
    
    def test_breaking_changes_defaults_to_false(self):
        """Test breaking_changes defaults to False."""
        version = SchemaVersion(
            version="1.0.0",
            released_at="2026-02-09T10:00:00Z",
            changes=[]
        )
        assert version.breaking_changes is False


# ============================================================================
# Error Contract Tests
# ============================================================================

class TestSchemaValidationError:
    """Test SchemaValidationError contract."""
    
    def test_valid_validation_error(self):
        """Test valid validation error accepted."""
        error = SchemaValidationError(
            error_type="ValidationError",
            message="Field validation failed",
            field_name="case_number",
            details={"expected": "string", "got": "int"}
        )
        assert error.error_type == "ValidationError"
        assert error.field_name == "case_number"
    
    def test_valid_schema_not_found_error(self):
        """Test valid SchemaNotFound error accepted."""
        error = SchemaValidationError(
            error_type="SchemaNotFound",
            message="Schema 'UnknownSchema' not found"
        )
        assert error.error_type == "SchemaNotFound"
    
    def test_valid_incompatible_version_error(self):
        """Test valid IncompatibleVersion error accepted."""
        error = SchemaValidationError(
            error_type="IncompatibleVersion",
            message="Schema version mismatch"
        )
        assert error.error_type == "IncompatibleVersion"
    
    def test_invalid_error_type_rejected(self):
        """Test invalid error type rejected."""
        with pytest.raises(ValidationError):
            SchemaValidationError(
                error_type="UnknownError",
                message="Test"
            )
    
    def test_empty_message_rejected(self):
        """Test empty message rejected."""
        with pytest.raises(ValidationError):
            SchemaValidationError(
                error_type="ValidationError",
                message=""
            )
    
    def test_field_name_optional(self):
        """Test field_name is optional."""
        error = SchemaValidationError(
            error_type="SchemaNotFound",
            message="Schema not found"
        )
        assert error.field_name is None
    
    def test_details_optional(self):
        """Test details is optional."""
        error = SchemaValidationError(
            error_type="ValidationError",
            message="Validation failed"
        )
        assert error.details is None


# ============================================================================
# Contract Completeness Tests
# ============================================================================

class TestContractCompleteness:
    """Test that all contracts are complete and consistent."""
    
    def test_all_validation_contracts_defined(self):
        """Test all validation contracts defined."""
        assert SchemaValidationInput is not None
        assert SchemaValidationOutput is not None
        assert SchemaValidationError is not None
    
    def test_all_field_contracts_defined(self):
        """Test all field contracts defined."""
        assert FieldValidationRule is not None
        assert FieldConstraints is not None
    
    def test_all_metadata_contracts_defined(self):
        """Test all metadata contracts defined."""
        assert SchemaMetadata is not None
        assert SchemaVersion is not None
    
    def test_all_error_types_covered(self):
        """Test all error types are covered."""
        error_types = ["ValidationError", "SchemaNotFound", "IncompatibleVersion"]
        for error_type in error_types:
            error = SchemaValidationError(
                error_type=error_type,
                message="Test"
            )
            assert error.error_type == error_type
    
    def test_version_format_consistency(self):
        """Test version format is consistent across contracts."""
        # SchemaMetadata version
        metadata = SchemaMetadata(
            schema_name="Test",
            version="1.2.3",
            description="Test",
            fields=[],
            required_fields=[],
            optional_fields=[]
        )
        
        # SchemaVersion version
        version = SchemaVersion(
            version="1.2.3",
            released_at="2026-02-09T10:00:00Z",
            changes=[]
        )
        
        assert metadata.version == version.version
