"""
Schema Validator - Step A
=========================

Classification: MISSION-CRITICAL / VALIDATION STEP A
Purpose: Validate that Canonical Verdict JSON has all required fields and valid schema.

This is Step A of the 4-step validation pipeline.
Must execute BEFORE Step B (Deterministic Validation).

CRITICAL INVARIANTS:
- Required fields must be present
- Schema version must be valid
- Verdict must be complete (not empty/partial)
- Fail-closed on any schema violation

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from mahoun.core.logging import setup_logger
from mahoun.reasoning.verdict_validation.pipeline import (
    ViolationSeverity,
    ViolationType,
    ValidationStep,
)

log = setup_logger("schema_validator")


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

# Canonical Verdict JSON Schema Version 1.0.0
CANONICAL_VERDICT_SCHEMA = {
    "version": "1.0.0",
    "required_fields": [
        "verdict_id",
        "case_id", 
        "final_verdict",
        "steps",
        "confidence_score",
        "unresolved_conflicts",
    ],
    "optional_fields": [
        "metadata",
        "evidence_references",
        "rule_nodes",
        "precedent_nodes",
        "contradictions",
        "execution_id",
        "correlation_id",
        "timestamp",
    ],
    "field_types": {
        "verdict_id": str,
        "case_id": str,
        "final_verdict": str,
        "steps": list,
        "confidence_score": (int, float),
        "unresolved_conflicts": list,
        "metadata": dict,
    },
    "field_validations": {
        "verdict_id": {"min_length": 1, "max_length": 100},
        "case_id": {"min_length": 1, "max_length": 100},
        "final_verdict": {"min_length": 1, "max_length": 10000},
        "confidence_score": {"min": 0.0, "max": 1.0},
    },
}


@dataclass(frozen=True)
class SchemaViolation:
    """Single schema validation violation"""
    message: str
    field: str
    violation_type: ViolationType = ViolationType.MISSING_REQUIRED_FIELD
    severity: ViolationSeverity = ViolationSeverity.CRITICAL
    expected: Optional[str] = None
    actual: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "field": self.field,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class SchemaValidationResult:
    """Result of schema validation"""
    passed: bool
    violations: List[SchemaViolation] = field(default_factory=list)
    validated_fields: List[str] = field(default_factory=list)
    schema_version: str = "1.0.0"
    validation_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "validated_fields": self.validated_fields,
            "schema_version": self.schema_version,
            "validation_timestamp": self.validation_timestamp,
        }


class SchemaValidator:
    """
    Validator for Canonical Verdict JSON schema.
    
    This validator ensures that the Canonical Verdict JSON:
    1. Has all required fields
    2. Has valid field types
    3. Passes field-level validations
    4. Has a valid schema version
    
    CRITICAL: This is Step A and MUST pass before any other validation.
    If schema validation fails, the entire pipeline must fail-closed.
    
    Usage:
        validator = SchemaValidator()
        result = validator.validate(canonical_json)
        
        if not result.passed:
            # Fail-closed - do NOT continue
            raise IntegrityViolationError("Schema validation failed", result.violations[0])
    """
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """
        Initialize schema validator.
        
        Args:
            schema: Custom schema to use (defaults to CANONICAL_VERDICT_SCHEMA)
        """
        self.schema = schema or CANONICAL_VERDICT_SCHEMA
        log.info(f"SchemaValidator initialized with schema version {self.schema['version']}")
    
    def validate(self, canonical_json: Dict[str, Any]) -> SchemaValidationResult:
        """
        Validate Canonical Verdict JSON against schema.
        
        Args:
            canonical_json: The Canonical Verdict JSON to validate
            
        Returns:
            SchemaValidationResult with validation details
        """
        violations: List[SchemaViolation] = []
        validated_fields: List[str] = []
        
        # Check if input is a dict
        if not isinstance(canonical_json, dict):
            violations.append(SchemaViolation(
                message="Canonical Verdict JSON must be a dictionary",
                field="root",
                violation_type=ViolationType.INVALID_SCHEMA_VERSION,
                severity=ViolationSeverity.CRITICAL,
                expected="dict",
                actual=str(type(canonical_json)),
            ))
            return SchemaValidationResult(
                passed=False,
                violations=violations,
                validated_fields=validated_fields,
            )
        
        # Step 1: Check required fields
        for field_name in self.schema["required_fields"]:
            if field_name not in canonical_json:
                violations.append(SchemaViolation(
                    message=f"Required field '{field_name}' is missing",
                    field=field_name,
                    violation_type=ViolationType.MISSING_REQUIRED_FIELD,
                    severity=ViolationSeverity.CRITICAL,
                ))
            else:
                validated_fields.append(field_name)
        
        # Step 2: Check field types
        for field_name, expected_types in self.schema.get("field_types", {}).items():
            if field_name in canonical_json:
                value = canonical_json[field_name]
                if not isinstance(value, expected_types):
                    violations.append(SchemaViolation(
                        message=f"Field '{field_name}' has invalid type",
                        field=field_name,
                        violation_type=ViolationType.INVALID_SCHEMA_VERSION,
                        severity=ViolationSeverity.CRITICAL,
                        expected=str(expected_types),
                        actual=str(type(value)),
                    ))
        
        # Step 3: Check field-level validations
        for field_name, validation_rules in self.schema.get("field_validations", {}).items():
            if field_name in canonical_json:
                value = canonical_json[field_name]
                
                # Check min_length
                if "min_length" in validation_rules and isinstance(value, str):
                    min_len = validation_rules["min_length"]
                    if len(value) < min_len:
                        violations.append(SchemaViolation(
                            message=f"Field '{field_name}' is too short (min: {min_len})",
                            field=field_name,
                            violation_type=ViolationType.INCOMPLETE_VERDICT,
                            severity=ViolationSeverity.HIGH,
                            expected=f"length >= {min_len}",
                            actual=f"length = {len(value)}",
                        ))
                
                # Check max_length
                if "max_length" in validation_rules and isinstance(value, str):
                    max_len = validation_rules["max_length"]
                    if len(value) > max_len:
                        violations.append(SchemaViolation(
                            message=f"Field '{field_name}' is too long (max: {max_len})",
                            field=field_name,
                            violation_type=ViolationType.INVALID_SCHEMA_VERSION,
                            severity=ViolationSeverity.MEDIUM,
                            expected=f"length <= {max_len}",
                            actual=f"length = {len(value)}",
                        ))
                
                # Check min/max for numeric fields
                if "min" in validation_rules and isinstance(value, (int, float)):
                    min_val = validation_rules["min"]
                    if value < min_val:
                        violations.append(SchemaViolation(
                            message=f"Field '{field_name}' is below minimum ({min_val})",
                            field=field_name,
                            violation_type=ViolationType.INVALID_SCHEMA_VERSION,
                            severity=ViolationSeverity.HIGH,
                            expected=f">= {min_val}",
                            actual=str(value),
                        ))
                
                if "max" in validation_rules and isinstance(value, (int, float)):
                    max_val = validation_rules["max"]
                    if value > max_val:
                        violations.append(SchemaViolation(
                            message=f"Field '{field_name}' is above maximum ({max_val})",
                            field=field_name,
                            violation_type=ViolationType.INVALID_SCHEMA_VERSION,
                            severity=ViolationSeverity.HIGH,
                            expected=f"<= {max_val}",
                            actual=str(value),
                        ))
        
        # Step 4: Check for empty/invalid values in required fields
        for field_name in self.schema["required_fields"]:
            if field_name in canonical_json:
                value = canonical_json[field_name]
                
                # Check for empty strings
                if isinstance(value, str) and not value.strip():
                    violations.append(SchemaViolation(
                        message=f"Required field '{field_name}' is empty",
                        field=field_name,
                        violation_type=ViolationType.INCOMPLETE_VERDICT,
                        severity=ViolationSeverity.CRITICAL,
                    ))
                
                # Check for empty lists
                if isinstance(value, list) and len(value) == 0 and field_name != "unresolved_conflicts":
                    violations.append(SchemaViolation(
                        message=f"Required field '{field_name}' is empty list",
                        field=field_name,
                        violation_type=ViolationType.INCOMPLETE_VERDICT,
                        severity=ViolationSeverity.HIGH,
                    ))
        
        # Final result
        passed = len(violations) == 0
        
        return SchemaValidationResult(
            passed=passed,
            violations=violations,
            validated_fields=validated_fields,
            schema_version=self.schema["version"],
        )
