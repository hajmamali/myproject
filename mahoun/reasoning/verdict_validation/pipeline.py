"""
Verdict Validation Pipeline - Main Orchestrator
==================================================

Classification: MISSION-CRITICAL / VALIDATION ORCHESTRATOR
Purpose: Orchestrate the 4-step validation pipeline for Canonical Verdict JSON integrity.

Pipeline Steps:
1. Step A: Schema Validation - Validate structure and required fields
2. Step B: Deterministic Consistency Validation - Compare text vs JSON
3. Step C: Atomic Claim Extraction - Split text into traceable claims
4. Step D: Semantic Verification (NLI) - Verify claims using NLI

CRITICAL RULE:
- Step B MUST execute BEFORE Step D (NLI)
- If Step B fails, pipeline MUST stop (fail-closed)
- No LLM is allowed in Step B (deterministic only)
- Every claim in Step C MUST reference the originating JSON field

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from mahoun.core.logging import setup_logger

log = setup_logger("verdict_validation_pipeline")


# ============================================================================
# EXCEPTIONS
# ============================================================================

class IntegrityViolationError(Exception):
    """
    Exception raised when verdict integrity validation fails.
    
    This is a CRITICAL error - the verdict cannot be trusted.
    The pipeline MUST fail-closed on this exception.
    """
    def __init__(self, message: str, violation: "IntegrityViolation"):
        self.violation = violation
        super().__init__(f"[INTEGRITY VIOLATION] {message}")


# ============================================================================
# ENUMS
# ============================================================================

class ValidationStep(str, Enum):
    """Validation pipeline steps"""
    SCHEMA = "schema"
    DETERMINISTIC = "deterministic"
    CLAIM_EXTRACTION = "claim_extraction"
    NLI = "nli"


class ViolationType(str, Enum):
    """Types of integrity violations"""
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_SCHEMA_VERSION = "INVALID_SCHEMA_VERSION"
    INCOMPLETE_VERDICT = "INCOMPLETE_VERDICT"
    TEXT_JSON_MISMATCH = "TEXT_JSON_MISMATCH"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CONTRADICTED_CLAIM = "CONTRADICTED_CLAIM"
    DETERMINISTIC_MISMATCH = "DETERMINISTIC_MISMATCH"


class ViolationSeverity(str, Enum):
    """Severity levels for violations"""
    CRITICAL = "CRITICAL"      # Must fail-closed
    HIGH = "HIGH"              # Strongly recommended to fail
    MEDIUM = "MEDIUM"          # Should be flagged
    LOW = "LOW"                # Informational


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass(frozen=True)
class IntegrityViolation:
    """
    Immutable record of a single integrity violation.
    
    Attributes:
        violation_type: Type of violation
        severity: Severity level
        message: Human-readable description
        field: Which field/element had the issue
        expected: Expected value (if applicable)
        actual: Actual value (if applicable)
        step: Which validation step detected this
        timestamp: When the violation was detected
    """
    violation_type: ViolationType
    severity: ViolationSeverity
    message: str
    field: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    step: ValidationStep = ValidationStep.SCHEMA
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
            "step": self.step.value,
            "timestamp": self.timestamp,
        }


@dataclass
class ValidationResult:
    """
    Complete result of the validation pipeline.
    
    Attributes:
        passed: Whether all validations passed
        verdict_id: The verdict being validated
        case_id: The case being validated
        violations: List of all integrity violations found
        schema_result: Result of Step A
        deterministic_result: Result of Step B
        claim_result: Result of Step C
        nli_result: Result of Step D
        execution_trace: Complete trace of execution
        timestamp: When validation was performed
    """
    passed: bool
    verdict_id: str
    case_id: str
    violations: List[IntegrityViolation] = field(default_factory=list)
    schema_result: Optional[Any] = None
    deterministic_result: Optional[Any] = None
    claim_result: Optional[Any] = None
    nli_result: Optional[Any] = None
    execution_trace: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if there are any CRITICAL violations"""
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)
    
    @property
    def has_blocking_violations(self) -> bool:
        """Check if there are any CRITICAL or HIGH violations"""
        return any(
            v.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]
            for v in self.violations
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "passed": self.passed,
            "verdict_id": self.verdict_id,
            "case_id": self.case_id,
            "violations": [v.to_dict() for v in self.violations],
            "has_critical_violations": self.has_critical_violations,
            "has_blocking_violations": self.has_blocking_violations,
            "schema_result": self.schema_result.to_dict() if self.schema_result else None,
            "deterministic_result": (
                self.deterministic_result.to_dict() if self.deterministic_result else None
            ),
            "claim_result": self.claim_result.to_dict() if self.claim_result else None,
            "nli_result": self.nli_result.to_dict() if self.nli_result else None,
            "execution_trace": self.execution_trace,
            "timestamp": self.timestamp,
        }


# ============================================================================
# CANONICAL VERDICT JSON SCHEMA
# ============================================================================

# Minimum required fields for a Canonical Verdict JSON
CANONICAL_VERDICT_SCHEMA_V1 = {
    "required": [
        "verdict_id",
        "case_id",
        "final_verdict",
        "steps",
        "confidence_score",
        "unresolved_conflicts",
    ],
    "optional": [
        "metadata",
        "evidence_references",
        "rule_nodes",
        "precedent_nodes",
        "contradictions",
    ],
    "version": "1.0.0",
}


# ============================================================================
# MAIN PIPELINE CLASS
# ============================================================================

class VerdictValidationPipeline:
    """
    Main orchestrator for the Canonical Verdict JSON validation pipeline.
    
    This pipeline guarantees that the generated legal text (prose) never
    deviates from the Canonical Verdict JSON. It enforces:
    
    1. Step A: Schema Validation - The JSON has all required fields
    2. Step B: Deterministic Consistency - The text matches the JSON
    3. Step C: Atomic Claim Extraction - Text split into traceable claims
    4. Step D: Semantic Verification - NLI checks for entailment/contradiction
    
    CRITICAL INVARIANTS:
    - The Canonical Verdict JSON is the ONLY source of truth
    - LLM-generated prose is NEVER authoritative
    - Step B MUST execute BEFORE Step D
    - If Step B fails, the pipeline MUST fail-closed
    - No LLM is allowed in Step B (deterministic parsing only)
    
    Usage:
        pipeline = VerdictValidationPipeline()
        
        # Create Canonical Verdict JSON
        canonical_json = {
            "verdict_id": "...",
            "case_id": "...",
            "final_verdict": "...",  # This is the structured data, NOT prose
            "steps": [...],
            ...
        }
        
        # Generate prose from JSON (LLM or template)
        prose_text = "..."  # The human-readable text
        
        # Validate
        result = pipeline.validate(
            canonical_json=canonical_json,
            prose_text=prose_text,
            verdict_id="...",
            case_id="..."
        )
        
        if not result.passed:
            raise IntegrityViolationError("Verdict validation failed", result.violations[0])
    """
    
    def __init__(
        self,
        enable_nli: bool = True,
        nli_threshold: float = 0.7,
        strict_mode: bool = True,
    ):
        """
        Initialize the validation pipeline.
        
        Args:
            enable_nli: Whether to enable NLI verification (Step D)
            nli_threshold: Minimum entailment score to pass NLI
            strict_mode: If True, fail-closed on any violation
        """
        self.enable_nli = enable_nli
        self.nli_threshold = nli_threshold
        self.strict_mode = strict_mode
        
        # Initialize validators (lazy-loaded to avoid dependency issues)
        self._schema_validator: Optional[Any] = None
        self._deterministic_validator: Optional[Any] = None
        self._claim_extractor: Optional[Any] = None
        self._nli_validator: Optional[Any] = None
        
        log.info(
            f"VerdictValidationPipeline initialized: "
            f"nli_enabled={enable_nli}, threshold={nli_threshold}, strict={strict_mode}"
        )
    
    def _get_schema_validator(self) -> "SchemaValidator":
        """Lazy-load schema validator"""
        if self._schema_validator is None:
            from mahoun.reasoning.verdict_validation.schema_validator import SchemaValidator
            self._schema_validator = SchemaValidator()
        return self._schema_validator
    
    def _get_deterministic_validator(self) -> "DeterministicValidator":
        """Lazy-load deterministic validator"""
        if self._deterministic_validator is None:
            from mahoun.reasoning.verdict_validation.deterministic_validator import (
                DeterministicValidator,
            )
            self._deterministic_validator = DeterministicValidator()
        return self._deterministic_validator
    
    def _get_claim_extractor(self) -> "ClaimExtractor":
        """Lazy-load claim extractor"""
        if self._claim_extractor is None:
            from mahoun.reasoning.verdict_validation.claim_extractor import ClaimExtractor
            self._claim_extractor = ClaimExtractor()
        return self._claim_extractor
    
    def _get_nli_validator(self) -> "NLIValidator":
        """Lazy-load NLI validator"""
        if self._nli_validator is None:
            from mahoun.reasoning.verdict_validation.nli_validator import NLIValidator
            self._nli_validator = NLIValidator(threshold=self.nli_threshold)
        return self._nli_validator
    
    def validate(
        self,
        canonical_json: Dict[str, Any],
        prose_text: str,
        verdict_id: str,
        case_id: str,
    ) -> ValidationResult:
        """
        Execute the complete validation pipeline.
        
        This method enforces that the generated prose text is fully
        faithful to the Canonical Verdict JSON.
        
        CRITICAL: This method MUST fail-closed on any integrity violation
        when strict_mode is True.
        
        Args:
            canonical_json: The Canonical Verdict JSON (source of truth)
            prose_text: The generated human-readable text to validate
            verdict_id: Unique identifier for this verdict
            case_id: Case identifier
            
        Returns:
            ValidationResult with complete validation details
            
        Raises:
            IntegrityViolationError: If strict_mode is True and violations are found
        """
        import time
        start_time = time.time()
        
        violations: List[IntegrityViolation] = []
        execution_trace: Dict[str, Any] = {
            "steps_executed": [],
            "step_timings": {},
            "start_timestamp": datetime.now(UTC).isoformat(),
        }
        
        result = ValidationResult(
            passed=False,  # Will be set to True only if all steps pass
            verdict_id=verdict_id,
            case_id=case_id,
            violations=violations,
            execution_trace=execution_trace,
            timestamp=datetime.now(UTC).isoformat(),
        )
        
        try:
            # ========================================================================
            # STEP A: Schema Validation
            # ========================================================================
            step_start = time.time()
            log.debug(f"[{verdict_id}] Executing Step A: Schema Validation")
            
            schema_validator = self._get_schema_validator()
            result.schema_result = schema_validator.validate(canonical_json)
            
            if not result.schema_result.passed:
                for violation in result.schema_result.violations:
                    violations.append(IntegrityViolation(
                        violation_type=ViolationType.MISSING_REQUIRED_FIELD,
                        severity=ViolationSeverity.CRITICAL,
                        message=violation.message,
                        field=violation.field,
                        step=ValidationStep.SCHEMA,
                    ))
            
            execution_trace["steps_executed"].append(ValidationStep.SCHEMA.value)
            execution_trace["step_timings"][ValidationStep.SCHEMA.value] = time.time() - step_start
            
            if self.strict_mode and violations:
                log.error(f"[{verdict_id}] CRITICAL: Schema validation failed")
                result.violations = violations
                result.execution_trace = execution_trace
                raise IntegrityViolationError(
                    f"Schema validation failed with {len(violations)} violations",
                    violations[0]
                )
            
            # ========================================================================
            # STEP B: Deterministic Consistency Validation
            # ========================================================================
            step_start = time.time()
            log.debug(f"[{verdict_id}] Executing Step B: Deterministic Consistency Validation")
            
            deterministic_validator = self._get_deterministic_validator()
            result.deterministic_result = deterministic_validator.validate(
                canonical_json=canonical_json,
                prose_text=prose_text,
            )
            
            if not result.deterministic_result.passed:
                for violation in result.deterministic_result.violations:
                    violations.append(IntegrityViolation(
                        violation_type=ViolationType.TEXT_JSON_MISMATCH,
                        severity=ViolationSeverity.CRITICAL,
                        message=violation.message,
                        field=violation.field,
                        expected=violation.expected,
                        actual=violation.actual,
                        step=ValidationStep.DETERMINISTIC,
                    ))
            
            execution_trace["steps_executed"].append(ValidationStep.DETERMINISTIC.value)
            execution_trace["step_timings"][ValidationStep.DETERMINISTIC.value] = time.time() - step_start
            
            # CRITICAL: If deterministic validation fails, STOP the pipeline
            # No LLM-based validation can fix a deterministic mismatch
            if self.strict_mode and not result.deterministic_result.passed:
                log.error(f"[{verdict_id}] CRITICAL: Deterministic validation failed - stopping pipeline")
                result.violations = violations
                result.execution_trace = execution_trace
                raise IntegrityViolationError(
                    f"Deterministic validation failed with {len(result.deterministic_result.violations)} violations",
                    result.deterministic_result.violations[0]
                )
            
            # ========================================================================
            # STEP C: Atomic Claim Extraction
            # ========================================================================
            step_start = time.time()
            log.debug(f"[{verdict_id}] Executing Step C: Atomic Claim Extraction")
            
            claim_extractor = self._get_claim_extractor()
            result.claim_result = claim_extractor.extract(
                prose_text=prose_text,
                canonical_json=canonical_json,
            )
            
            execution_trace["steps_executed"].append(ValidationStep.CLAIM_EXTRACTION.value)
            execution_trace["step_timings"][ValidationStep.CLAIM_EXTRACTION.value] = time.time() - step_start
            
            # ========================================================================
            # STEP D: Semantic Verification (NLI)
            # ========================================================================
            if self.enable_nli:
                step_start = time.time()
                log.debug(f"[{verdict_id}] Executing Step D: Semantic Verification (NLI)")
                
                nli_validator = self._get_nli_validator()
                result.nli_result = nli_validator.validate(
                    canonical_json=canonical_json,
                    prose_text=prose_text,
                    claims=result.claim_result.claims if result.claim_result else [],
                )
                
                if not result.nli_result.passed:
                    for violation in result.nli_result.violations:
                        violations.append(IntegrityViolation(
                            violation_type=ViolationType.UNSUPPORTED_CLAIM,
                            severity=ViolationSeverity.HIGH,
                            message=violation.message,
                            field=violation.field,
                            step=ValidationStep.NLI,
                        ))
                
                execution_trace["steps_executed"].append(ValidationStep.NLI.value)
                execution_trace["step_timings"][ValidationStep.NLI.value] = time.time() - step_start
            else:
                log.debug(f"[{verdict_id}] NLI verification disabled")
            
            # ========================================================================
            # FINAL RESULT
            # ========================================================================
            result.passed = len(violations) == 0
            result.violations = violations
            
            total_time = time.time() - start_time
            execution_trace["total_time_ms"] = total_time * 1000
            execution_trace["end_timestamp"] = datetime.now(UTC).isoformat()
            
            log.info(
                f"[{verdict_id}] Validation pipeline completed: "
                f"passed={result.passed}, violations={len(violations)}, "
                f"time={total_time:.3f}s"
            )
            
            return result
            
        except IntegrityViolationError:
            # Re-raise integrity violations
            raise
        except Exception as e:
            # Log unexpected errors
            log.error(f"[{verdict_id}] Unexpected error in validation pipeline: {e}", exc_info=True)
            violations.append(IntegrityViolation(
                violation_type=ViolationType.DETERMINISTIC_MISMATCH,
                severity=ViolationSeverity.CRITICAL,
                message=f"Unexpected validation error: {str(e)}",
                field="pipeline",
                step=ValidationStep.DETERMINISTIC,
            ))
            result.violations = violations
            result.execution_trace = execution_trace
            result.passed = False
            return result
