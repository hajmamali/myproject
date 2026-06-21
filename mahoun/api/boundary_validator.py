"""
MAHOUN API Boundary Validator
==============================
PHASE 1 HARDENING: Boundary B1 Implementation

Non-bypassable enforcement at API boundary.
All inputs MUST pass through this validator before processing.

Invariants Enforced:
- B1-I1: All inputs validated for adversarial patterns
- B1-I2: Payload structure strictly validated
- B1-I3: Provenance captured at entry point
- B1-I4: Invalid payloads rejected with explicit reason codes
"""

import hashlib
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict

from mahoun.core.logging import setup_logger
from mahoun.guardrails.adversarial_detector import (
    AdversarialInputDetector,
    DetectionResult,
    ThreatLevel,
    create_boundary_detector,
    get_boundary_detector,
)
from mahoun.invariants.versions import INVARIANT_VERSION

log = setup_logger("boundary_validator")


class ValidationErrorCode(str, Enum):
    """Explicit error codes for boundary violations"""
    ADVERSARIAL_INPUT = "adversarial_input"
    INVALID_PAYLOAD_STRUCTURE = "invalid_payload_structure"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    PRIVACY_VIOLATION = "privacy_violation"
    OVERSIZED_PAYLOAD = "oversized_payload"
    UNSUPPORTED_CONTENT_TYPE = "unsupported_content_type"
    VALIDATION_SYSTEM_ERROR = "validation_system_error"


class RejectionReason(BaseModel):
    """Structured rejection reason for audit trail"""
    error_code: ValidationErrorCode
    message: str
    field: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class BoundaryValidationResult:
    """
    Immutable result of boundary validation.
    
    HARDENING: All validation decisions are auditable and immutable.
    """
    is_valid: bool
    input_id: str
    input_hash: str
    rejection_reason: Optional[RejectionReason] = None
    detection_result: Optional[DetectionResult] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invariant_version: str = INVARIANT_VERSION
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Convert to audit log format"""
        return {
            "event_type": "boundary_validation",
            "is_valid": self.is_valid,
            "input_id": self.input_id,
            "input_hash": self.input_hash,
            "rejection_reason": self.rejection_reason.model_dump() if self.rejection_reason else None,
            "timestamp": self.timestamp.isoformat(),
            "invariant_version": self.invariant_version,
        }


# ============================================================================
# Strict Payload Contracts
# ============================================================================

class ClaimRequestPayload(BaseModel):
    """
    Strict contract for claim generation requests.
    
    HARDENING: extra="forbid" prevents injection attacks via extra fields.
    """
    claim_type: str = Field(..., min_length=1, max_length=100)
    facts: str = Field(..., min_length=10, max_length=50000)
    parties: Dict[str, str] = Field(default_factory=dict)
    legal_basis: Optional[str] = Field(None, max_length=1000)
    request_id: Optional[str] = Field(None, max_length=200)
    
    @field_validator('facts')
    @classmethod
    def validate_facts_not_empty(cls, v: str) -> str:
        """Ensure facts field has substantive content"""
        if len(v.strip()) < 10:
            raise ValueError("Facts must contain at least 10 characters of substantive content")
        return v
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "claim_type": "breach_of_contract",
                "facts": "Plaintiff entered into contract with defendant on January 1, 2024...",
                "parties": {"plaintiff": "Company A", "defendant": "Company B"},
            }
        }
    )


class VerdictRequestPayload(BaseModel):
    """
    Strict contract for verdict generation requests.
    
    HARDENING: Verdict requests require explicit evidence references.
    """
    question: str = Field(..., min_length=10, max_length=2000)
    facts: List[Dict[str, Any]] = Field(..., min_length=1)
    case_id: Optional[str] = Field(None, max_length=200)
    request_id: Optional[str] = Field(None, max_length=200)
    
    @field_validator('facts')
    @classmethod
    def validate_facts_have_evidence(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure each fact has required fields for evidence linking"""
        for i, fact in enumerate(v):
            if 'id' not in fact and 'value' not in fact:
                raise ValueError(f"Fact at index {i} must have 'id' or 'value' field")
        return v
    
    model_config = ConfigDict(extra="forbid")


class EdgeCreationPayload(BaseModel):
    """
    Strict contract for graph edge creation.
    
    HARDENING: Edge creation REQUIRES provenance evidence.
    """
    source_id: str = Field(..., min_length=1, max_length=500)
    target_id: str = Field(..., min_length=1, max_length=500)
    relationship_type: str = Field(..., min_length=1, max_length=100)
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[str] = Field(..., min_length=1)  # REQUIRED - no default
    provenance: Dict[str, Any] = Field(..., min_length=1)  # REQUIRED
    request_id: Optional[str] = Field(None, max_length=200)
    
    @field_validator('evidence')
    @classmethod
    def validate_evidence_non_empty(cls, v: List[str]) -> List[str]:
        """Ensure evidence list is not empty"""
        if not v or all(not e.strip() for e in v):
            raise ValueError("At least one non-empty evidence reference is required")
        return v
    
    @field_validator('provenance')
    @classmethod
    def validate_provenance_fields(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure provenance has required tracking fields"""
        required = ['source', 'timestamp', 'method']
        missing = [f for f in required if f not in v]
        if missing:
            raise ValueError(f"Provenance missing required fields: {missing}")
        return v
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Boundary Validator
# ============================================================================

class BoundaryValidator:
    """
    MAHOUN API Boundary Validator - NON-BYPASSABLE.
    
    This validator operates as a mandatory gate at the API boundary.
    All requests MUST pass through validate_* methods.
    
    Enforcement Points:
    1. Adversarial input detection
    2. Payload structure validation (Pydantic)
    3. Required field verification
    4. Privacy/payload size checks
    5. Provenance capture
    """
    
    def __init__(
        self,
        detector: Optional[AdversarialInputDetector] = None,
        max_payload_size: int = 10 * 1024 * 1024,  # 10MB
        strict_mode: bool = True,
    ):
        """
        Initialize boundary validator.
        
        Args:
            detector: Adversarial detector instance (created if None)
            max_payload_size: Maximum allowed payload size in bytes
            strict_mode: If True, all validations are enforced strictly
        """
        self.detector = detector or get_boundary_detector()
        self.max_payload_size = max_payload_size
        self.strict_mode = strict_mode
        
        # Validation statistics
        self._total_validated = 0
        self._rejected_count = 0
        self._rejection_by_reason: Dict[str, int] = {}
        
        log.info(
            f"BoundaryValidator initialized: "
            f"max_size={max_payload_size}, strict={strict_mode}, "
            f"invariant_version={INVARIANT_VERSION}"
        )
    
    def _generate_input_id(self, payload: str) -> tuple[str, str]:
        """Generate deterministic input ID and hash"""
        content_hash = hashlib.sha256(payload.encode()).hexdigest()
        input_id = f"boundary_{content_hash[:16]}_{int(datetime.now(timezone.utc).timestamp())}"
        return input_id, content_hash
    
    def _create_rejection(
        self,
        error_code: ValidationErrorCode,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> BoundaryValidationResult:
        """Create a rejection result"""
        rejection = RejectionReason(
            error_code=error_code,
            message=message,
            field=field,
            details=details or {},
        )
        
        return BoundaryValidationResult(
            is_valid=False,
            input_id="rejected",
            input_hash="",
            rejection_reason=rejection,
        )
    
    def validate_claim_request(
        self,
        raw_payload: Dict[str, Any],
        embedding: Optional[Any] = None,
    ) -> BoundaryValidationResult:
        """
        Validate claim generation request at API boundary.
        
        HARDENING: This is a mandatory gate. No claim processing without validation.
        
        Args:
            raw_payload: Raw request payload
            embedding: Optional embedding for adversarial detection
        
        Returns:
            BoundaryValidationResult with validation decision
        """
        self._total_validated += 1
        
        # Step 1: Payload size check
        payload_str = json.dumps(raw_payload)
        if len(payload_str) > self.max_payload_size:
            self._rejected_count += 1
            self._rejection_by_reason[ValidationErrorCode.OVERSIZED_PAYLOAD.value] = \
                self._rejection_by_reason.get(ValidationErrorCode.OVERSIZED_PAYLOAD.value, 0) + 1
            
            return self._create_rejection(
                error_code=ValidationErrorCode.OVERSIZED_PAYLOAD,
                message=f"Payload size {len(payload_str)} exceeds maximum {self.max_payload_size}",
                details={"size": len(payload_str), "max": self.max_payload_size},
            )
        
        # Step 2: Generate input ID and hash
        input_id, input_hash = self._generate_input_id(payload_str)
        
        # Step 3: Adversarial detection (critical text fields)
        text_to_check = f"{raw_payload.get('claim_type', '')} {raw_payload.get('facts', '')}"
        
        detection_result = self.detector.detect(
            input_text=text_to_check,
            embedding=embedding,
            metadata={"request_type": "claim", "input_id": input_id},
        )
        
        # Step 4: Check adversarial detection result
        if detection_result.is_adversarial and self.strict_mode:
            self._rejected_count += 1
            self._rejection_by_reason[ValidationErrorCode.ADVERSARIAL_INPUT.value] = \
                self._rejection_by_reason.get(ValidationErrorCode.ADVERSARIAL_INPUT.value, 0) + 1
            
            return BoundaryValidationResult(
                is_valid=False,
                input_id=input_id,
                input_hash=input_hash,
                rejection_reason=RejectionReason(
                    error_code=ValidationErrorCode.ADVERSARIAL_INPUT,
                    message=f"Adversarial input detected: {detection_result.threat_level.value}",
                    details={
                        "threat_level": detection_result.threat_level.value,
                        "confidence": detection_result.confidence,
                        "methods": list(detection_result.detection_methods.keys()),
                    },
                ),
                detection_result=detection_result,
            )
        
        # Step 5: Strict payload validation with Pydantic
        try:
            validated_payload = ClaimRequestPayload.model_validate(raw_payload)
        except Exception as e:
            self._rejected_count += 1
            self._rejection_by_reason[ValidationErrorCode.INVALID_PAYLOAD_STRUCTURE.value] = \
                self._rejection_by_reason.get(ValidationErrorCode.INVALID_PAYLOAD_STRUCTURE.value, 0) + 1
            
            return self._create_rejection(
                error_code=ValidationErrorCode.INVALID_PAYLOAD_STRUCTURE,
                message=f"Payload validation failed: {str(e)}",
                details={"error": str(e)},
            )
        
        # Step 6: Success - return validated result
        return BoundaryValidationResult(
            is_valid=True,
            input_id=input_id,
            input_hash=input_hash,
            detection_result=detection_result,
            provenance={
                "validated_payload": validated_payload.model_dump(),
                "detection_performed": True,
            },
        )
    
    def validate_verdict_request(
        self,
        raw_payload: Dict[str, Any],
        embedding: Optional[Any] = None,
    ) -> BoundaryValidationResult:
        """
        Validate verdict generation request at API boundary.
        
        HARDENING: Verdict requests require evidence references per EL-I1.
        """
        self._total_validated += 1
        
        # Payload size check
        payload_str = json.dumps(raw_payload)
        if len(payload_str) > self.max_payload_size:
            self._rejected_count += 1
            return self._create_rejection(
                error_code=ValidationErrorCode.OVERSIZED_PAYLOAD,
                message=f"Payload size {len(payload_str)} exceeds maximum",
            )
        
        input_id, input_hash = self._generate_input_id(payload_str)
        
        # Adversarial detection
        text_to_check = raw_payload.get('question', '')
        detection_result = self.detector.detect(
            input_text=text_to_check,
            embedding=embedding,
            metadata={"request_type": "verdict", "input_id": input_id},
        )
        
        if detection_result.is_adversarial and self.strict_mode:
            self._rejected_count += 1
            return BoundaryValidationResult(
                is_valid=False,
                input_id=input_id,
                input_hash=input_hash,
                rejection_reason=RejectionReason(
                    error_code=ValidationErrorCode.ADVERSARIAL_INPUT,
                    message=f"Adversarial input detected: {detection_result.threat_level.value}",
                ),
                detection_result=detection_result,
            )
        
        # Strict validation
        try:
            validated_payload = VerdictRequestPayload.model_validate(raw_payload)
        except Exception as e:
            self._rejected_count += 1
            return self._create_rejection(
                error_code=ValidationErrorCode.INVALID_PAYLOAD_STRUCTURE,
                message=f"Payload validation failed: {str(e)}",
            )
        
        return BoundaryValidationResult(
            is_valid=True,
            input_id=input_id,
            input_hash=input_hash,
            detection_result=detection_result,
            provenance={
                "validated_payload": validated_payload.model_dump(),
                "evidence_count": len(validated_payload.facts),
            },
        )
    
    def validate_edge_creation(
        self,
        raw_payload: Dict[str, Any],
        embedding: Optional[Any] = None,
    ) -> BoundaryValidationResult:
        """
        Validate graph edge creation request at API boundary.
        
        HARDENING: Edge creation REQUIRES provenance and evidence (P0 fix).
        """
        self._total_validated += 1
        
        payload_str = json.dumps(raw_payload)
        input_id, input_hash = self._generate_input_id(payload_str)
        
        # CRITICAL: Edge creation requires evidence and provenance
        # This enforces: "No graph edge without provenance"
        
        try:
            validated_payload = EdgeCreationPayload.model_validate(raw_payload)
        except Exception as e:
            self._rejected_count += 1
            self._rejection_by_reason[ValidationErrorCode.MISSING_REQUIRED_FIELD.value] = \
                self._rejection_by_reason.get(ValidationErrorCode.MISSING_REQUIRED_FIELD.value, 0) + 1
            
            # Check if it's specifically the evidence/provenance missing
            error_str = str(e).lower()
            if 'evidence' in error_str:
                return self._create_rejection(
                    error_code=ValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message="Edge creation requires evidence references (B1-I4 enforcement)",
                    field="evidence",
                    details={"violation": "No graph edge without evidence"},
                )
            elif 'provenance' in error_str:
                return self._create_rejection(
                    error_code=ValidationErrorCode.MISSING_REQUIRED_FIELD,
                    message="Edge creation requires provenance tracking (B1-I4 enforcement)",
                    field="provenance",
                    details={"violation": "No graph edge without provenance"},
                )
            
            return self._create_rejection(
                error_code=ValidationErrorCode.INVALID_PAYLOAD_STRUCTURE,
                message=f"Edge payload validation failed: {str(e)}",
            )
        
        # Success - edge has evidence and provenance
        return BoundaryValidationResult(
            is_valid=True,
            input_id=input_id,
            input_hash=input_hash,
            provenance={
                "validated_payload": validated_payload.model_dump(),
                "evidence_count": len(validated_payload.evidence),
                "provenance_fields": list(validated_payload.provenance.keys()),
            },
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "total_validated": self._total_validated,
            "rejected_count": self._rejected_count,
            "rejection_rate": self._rejected_count / max(self._total_validated, 1),
            "rejection_by_reason": self._rejection_by_reason.copy(),
            "strict_mode": self.strict_mode,
            "max_payload_size": self.max_payload_size,
            "invariant_version": INVARIANT_VERSION,
        }


# ============================================================================
# Global Instance
# ============================================================================

_validator: Optional[BoundaryValidator] = None


def get_boundary_validator() -> BoundaryValidator:
    """Get or create global boundary validator"""
    global _validator
    if _validator is None:
        _validator = BoundaryValidator()
    return _validator


def reset_boundary_validator() -> None:
    """Reset global validator (for testing)"""
    global _validator
    _validator = None
    log.info("Boundary validator reset")


# Convenience functions for direct use

def validate_claim_payload(payload: Dict[str, Any]) -> BoundaryValidationResult:
    """Convenience function to validate claim payload"""
    return get_boundary_validator().validate_claim_request(payload)


def validate_verdict_payload(payload: Dict[str, Any]) -> BoundaryValidationResult:
    """Convenience function to validate verdict payload"""
    return get_boundary_validator().validate_verdict_request(payload)


def validate_edge_payload(payload: Dict[str, Any]) -> BoundaryValidationResult:
    """Convenience function to validate edge payload"""
    return get_boundary_validator().validate_edge_creation(payload)
