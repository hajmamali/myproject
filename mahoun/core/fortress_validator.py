"""
MAHOUN Fortress Validator
==========================

Classification: MISSION-CRITICAL / SECURITY-ENFORCEMENT / NON-BYPASSABLE
Purpose: Final forensic validation layer for all reasoning outputs

This module implements the Fortress Validator, a standalone wrapper that intercepts
ALL outputs from unified_reasoning_service.py and performs mandatory forensic checks
before allowing responses to proceed.

Core Responsibilities:
- Enforce RedLines.yaml governance thresholds
- Validate proof_tree existence and integrity
- Verify agreement_score >= 0.85
- Block responses that violate zero-hallucination guarantees
- Generate forensic audit trails
- Raise SecurityBreachException on violations

Author: MahouN AEO Governance Council
Version: 1.0.0
Last Updated: 2026-05-13
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar, TYPE_CHECKING, Dict, Union

# Make yaml optional for kernel isolation
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

# TYPE_CHECKING for type hints only - no runtime import
if TYPE_CHECKING:
    # Type hints only - not imported at runtime
    ReasoningResponse = Any
else:
    # Runtime placeholder
    ReasoningResponse = Any

# These remain with fallback due to optional dependency
try:
    from reasoning_logic.parser import FOLConverter, ParseError
except ImportError:
    FOLConverter = Any  # type: ignore
    ParseError = Exception  # type: ignore

try:
    from mahoun.core.logging_config import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

try:
    from mahoun.infrastructure.observability.metrics_migration import get_metrics_collector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


log = get_logger(__name__)

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

T = TypeVar("T")


class ViolationSeverity(str, Enum):
    """Severity classification for RedLine violations"""

    CRITICAL = "CRITICAL"  # Immediate block, security breach
    HIGH = "HIGH"  # Block response, log incident
    MEDIUM = "MEDIUM"  # Warn, allow with audit
    LOW = "LOW"  # Log only


class ViolationType(str, Enum):
    """Types of RedLine violations"""

    MISSING_PROOF_TREE = "MISSING_PROOF_TREE"
    LOW_AGREEMENT_SCORE = "LOW_AGREEMENT_SCORE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"
    AUDIT_TRAIL_INCOMPLETE = "AUDIT_TRAIL_INCOMPLETE"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    RESOURCE_VIOLATION = "RESOURCE_VIOLATION"
    SILENT_FAILURE = "SILENT_FAILURE"


class ExecutionMode(str, Enum):
    """System execution modes"""

    DESKTOP_MINIMAL = "DESKTOP_MINIMAL"
    ENTERPRISE_FULL = "ENTERPRISE_FULL"


# ============================================================================
# EXCEPTIONS
# ============================================================================


from mahoun.core.exceptions import BaseMahounError, SecurityBreachException as CanonicalSecurityBreach


class SecurityBreachException(CanonicalSecurityBreach, Exception):  # type: ignore[misc]
    """Legacy alias that now inherits the canonical deterministic error contract (403)."""
    pass
    """
    Raised when a RedLine violation is detected.

    This exception is NON-BYPASSABLE and indicates a critical
    governance failure that must be addressed immediately.
    """

    def __init__(
        self,
        message: str,
        violation_type: ViolationType,
        severity: ViolationSeverity,
        forensic_context: dict[str, Any],
        correlation_id: str | None = None,
    ):
        self.message = message
        self.violation_type = violation_type
        self.severity = severity
        self.forensic_context = forensic_context
        self.correlation_id = correlation_id
        self.timestamp = datetime.now(UTC).isoformat()

        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format exception message with forensic context"""
        return (
            f"[SECURITY BREACH] {self.severity.value}\n"
            f"Violation: {self.violation_type.value}\n"
            f"Message: {self.message}\n"
            f"Correlation ID: {self.correlation_id}\n"
            f"Timestamp: {self.timestamp}\n"
            f"Forensic Context: {self.forensic_context}"
        )


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


@dataclass
class RedLinesConfig:
    """Pure dataclass model for RedLines.yaml configuration (no pydantic)"""

    @dataclass
    class ThresholdsConfig:
        min_agreement_score: float
        min_confidence_score: float
        max_reasoning_time_ms: int
        max_recursion_depth: int
        
        def __post_init__(self):
            """Validate constraints after initialization"""
            if not (0.0 <= self.min_agreement_score <= 1.0):
                raise ValueError("min_agreement_score must be between 0.0 and 1.0")
            if not (0.0 <= self.min_confidence_score <= 1.0):
                raise ValueError("min_confidence_score must be between 0.0 and 1.0")
            if self.max_reasoning_time_ms <= 0:
                raise ValueError("max_reasoning_time_ms must be > 0")
            if self.max_recursion_depth <= 0:
                raise ValueError("max_recursion_depth must be > 0")

    @dataclass
    class ProofRequirementsConfig:
        proof_tree_required: bool
        min_proof_depth: int
        evidence_linkage_required: bool
        audit_trail_required: bool
        
        def __post_init__(self):
            if self.min_proof_depth < 0:
                raise ValueError("min_proof_depth must be >= 0")

    @dataclass
    class HallucinationPreventionConfig:
        require_graph_evidence: bool
        require_source_attribution: bool
        reject_contradictions: bool
        require_determinism: bool

    @dataclass
    class DualModeConfig:
        enforce_semantic_equivalence: bool
        allow_resource_scaling_only: bool
        fail_on_semantic_drift: bool

    @dataclass
    class ExceptionsConfig:
        violation_exception: str
        allow_silent_failures: bool
        require_exception_logging: bool
        require_forensic_context: bool

    thresholds: ThresholdsConfig
    proof_requirements: ProofRequirementsConfig
    hallucination_prevention: HallucinationPreventionConfig
    dual_mode: DualModeConfig
    exceptions: ExceptionsConfig


@dataclass
class ValidationResult:
    """Result of fortress validation (pure dataclass, no pydantic)"""

    passed: bool
    correlation_id: str
    timestamp: str
    execution_time_ms: float
    violations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    forensic_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> dict[str, Any]:
        """Pydantic compatibility method"""
        return {
            "passed": self.passed,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
            "violations": self.violations,
            "warnings": self.warnings,
            "forensic_hash": self.forensic_hash,
            "metadata": self.metadata,
        }


# Removed redundant ReasoningResponse BaseModel definition to avoid shadowing the dataclass


# ============================================================================
# FORTRESS VALIDATOR CORE
# ============================================================================


@dataclass
class ForensicContext:
    """Forensic context for audit trail"""

    correlation_id: str
    timestamp: str
    execution_mode: ExecutionMode
    response_hash: str
    validation_checks: list[str] = field(default_factory=list)
    violations_detected: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FortressValidator:
    """
    The Fortress Validator: Final governance enforcement layer.

    This class intercepts ALL outputs from unified_reasoning_service.py
    and performs mandatory forensic validation before allowing responses
    to proceed.

    Responsibilities:
    - Load and enforce RedLines.yaml configuration
    - Validate proof_tree existence and integrity
    - Verify agreement_score >= threshold
    - Check evidence linkage and audit trails
    - Generate forensic audit records
    - Raise SecurityBreachException on violations

    Usage:
        validator = FortressValidator()
        validated_response = await validator.validate(
            response=reasoning_response,
            correlation_id="req-12345"
        )
    """

    def __init__(
        self,
        config_path: Path | None = None,
        execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL,
        strict_mode: bool = True,
    ):
        """
        Initialize Fortress Validator.

        Args:
            config_path: Path to RedLines.yaml (defaults to constitution/RedLines.yaml)
            execution_mode: Current execution mode (DESKTOP_MINIMAL or ENTERPRISE_FULL)
            strict_mode: If True, raise exceptions on violations; if False, log only
        """
        self.execution_mode = execution_mode
        self.strict_mode = strict_mode
        self.config_path = config_path or Path(__file__).parent.parent.parent / "constitution" / "RedLines.yaml"

        # Load configuration
        self.config = self._load_config()

        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "passed": 0,
            "failed": 0,
            "violations_by_type": {},
            "average_validation_time_ms": 0.0,
        }

        # Forensic audit trail
        self.audit_trail: list[ForensicContext] = []

        log.info(
            f"FortressValidator initialized: mode={execution_mode.value}, "
            f"strict={strict_mode}, config={self.config_path}"
        )

    def _load_config(self) -> RedLinesConfig:
        """Load and validate RedLines.yaml configuration"""
        try:
            if not self.config_path.exists():
                log.error(f"RedLines.yaml not found at {self.config_path}")
                raise FileNotFoundError(f"RedLines configuration missing: {self.config_path}")

            if not YAML_AVAILABLE:
                log.error("PyYAML not available - using fallback default config")
                return self._get_default_config()

            with open(self.config_path) as f:
                raw_config = yaml.safe_load(f)

            # Convert nested dicts to dataclasses
            config = RedLinesConfig(
                thresholds=RedLinesConfig.ThresholdsConfig(**raw_config['thresholds']),
                proof_requirements=RedLinesConfig.ProofRequirementsConfig(**raw_config['proof_requirements']),
                hallucination_prevention=RedLinesConfig.HallucinationPreventionConfig(**raw_config['hallucination_prevention']),
                dual_mode=RedLinesConfig.DualModeConfig(**raw_config['dual_mode']),
                exceptions=RedLinesConfig.ExceptionsConfig(**raw_config['exceptions']),
            )
            
            log.info(f"RedLines.yaml loaded successfully: min_agreement={config.thresholds.min_agreement_score}")
            return config

        except Exception as e:
            log.critical(f"Failed to load RedLines.yaml: {e}")
            raise
    
    def _get_default_config(self) -> RedLinesConfig:
        """Get fallback default configuration when YAML unavailable"""
        return RedLinesConfig(
            thresholds=RedLinesConfig.ThresholdsConfig(
                min_agreement_score=0.85,
                min_confidence_score=0.70,
                max_reasoning_time_ms=30000,
                max_recursion_depth=10,
            ),
            proof_requirements=RedLinesConfig.ProofRequirementsConfig(
                proof_tree_required=True,
                min_proof_depth=1,
                evidence_linkage_required=True,
                audit_trail_required=True,
            ),
            hallucination_prevention=RedLinesConfig.HallucinationPreventionConfig(
                require_graph_evidence=True,
                require_source_attribution=True,
                reject_contradictions=True,
                require_determinism=True,
            ),
            dual_mode=RedLinesConfig.DualModeConfig(
                enforce_semantic_equivalence=True,
                allow_resource_scaling_only=True,
                fail_on_semantic_drift=True,
            ),
            exceptions=RedLinesConfig.ExceptionsConfig(
                violation_exception="SecurityBreachException",
                allow_silent_failures=False,
                require_exception_logging=True,
                require_forensic_context=True,
            ),
        )

    async def validate(
        self, response: Any, correlation_id: str | None = None
    ) -> ValidationResult:
        """
        Perform comprehensive fortress validation on reasoning response.

        This is the main entry point for validation. It performs all
        mandatory checks defined in RedLines.yaml and raises
        SecurityBreachException if critical violations are detected.

        Args:
            response: Reasoning service response to validate
            correlation_id: Optional correlation ID for tracing

        Returns:
            ValidationResult with pass/fail status and forensic context

        Raises:
            SecurityBreachException: On critical RedLine violations
        """
        start_time = time.perf_counter()
        correlation_id = correlation_id or self._generate_correlation_id()

        violations: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Convert dict to expected type if needed
        if isinstance(response, dict):
            # Use duck-typing and dynamic validation instead of direct import
            try:
                required_fields = ["success", "result", "confidence", "reasoning_mode", "execution_time_ms"]
                for f in required_fields:
                    if f not in response:
                        raise ValueError(f"Missing required field: {f}")
                        
                # Convert to object-like structure for processing
                class DynamicResponse:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                
                response = DynamicResponse(
                    success=response.get("success"),
                    result=response.get("result"),
                    confidence=response.get("confidence"),
                    reasoning_mode=response.get("reasoning_mode"),
                    execution_time_ms=response.get("execution_time_ms"),
                    proof_tree=response.get("proof_tree"),
                    explanation=response.get("explanation"),
                    derived_facts=response.get("derived_facts", []),
                    error=response.get("error"),
                    metadata=response.get("metadata", {}),
                    fortress_validated=response.get("fortress_validated", False),
                    audit_hash=response.get("audit_hash"),
                    validation_timestamp=response.get("validation_timestamp"),
                    correlation_id=response.get("correlation_id"),
                )
            except Exception as e:
                violations.append(
                    {
                        "type": ViolationType.AUDIT_TRAIL_INCOMPLETE.value,
                        "severity": ViolationSeverity.CRITICAL.value,
                        "message": f"Invalid response structure: {e}",
                        "details": {"exception": str(e)},
                    }
                )

        # Initialize forensic context
        forensic_ctx = ForensicContext(
            correlation_id=correlation_id,
            timestamp=datetime.now(UTC).isoformat(),
            execution_mode=self.execution_mode,
            response_hash=self._compute_response_hash(response),
        )

        # Execute validation checks
        try:
            # CHECK 1: Proof tree validation
            proof_violation = await self._validate_proof_tree(response, forensic_ctx)
            if proof_violation:
                violations.append(proof_violation)

            # CHECK 2: Agreement score validation
            agreement_violation = await self._validate_agreement_score(response, forensic_ctx)
            if agreement_violation:
                violations.append(agreement_violation)

            # CHECK 3: Evidence linkage validation
            evidence_violation = await self._validate_evidence_linkage(response, forensic_ctx)
            if evidence_violation:
                violations.append(evidence_violation)

            # CHECK 4: Audit trail validation
            audit_violation = await self._validate_audit_trail(response, forensic_ctx)
            if audit_violation:
                violations.append(audit_violation)

            # CHECK 5: Determinism validation
            determinism_violation = await self._validate_determinism(response, forensic_ctx)
            if determinism_violation:
                violations.append(determinism_violation)

            # CHECK 6: Contradiction detection
            contradiction_violation = await self._validate_contradictions(response, forensic_ctx)
            if contradiction_violation:
                violations.append(contradiction_violation)

        except Exception as e:
            log.error(f"[{correlation_id}] Validation check failed: {e}")
            violations.append(
                {
                    "type": ViolationType.SILENT_FAILURE.value,
                    "severity": ViolationSeverity.CRITICAL.value,
                    "message": f"Validation exception: {e}",
                    "details": {"exception": str(e)},
                }
            )

        # Compute execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Determine overall pass/fail
        blocking_violations = [v for v in violations if v["severity"] in [ViolationSeverity.CRITICAL.value, ViolationSeverity.HIGH.value]]
        passed = len(blocking_violations) == 0

        # Update statistics
        self._update_stats(passed, violations, execution_time_ms)

        # Store forensic context
        forensic_ctx.violations_detected = violations
        self.audit_trail.append(forensic_ctx)

        # ========================================================================
        # PROOF-CARRYING CONTRACT INJECTION
        # ========================================================================
        # If validation passed, inject proof-carrying metadata into response
        if passed and hasattr(response, 'fortress_validated'):
            response.fortress_validated = True
            response.audit_hash = forensic_ctx.response_hash
            response.validation_timestamp = forensic_ctx.timestamp
            response.correlation_id = correlation_id

            log.debug(
                f"[{correlation_id}] Proof-carrying metadata injected: "
                f"hash={response.audit_hash}, timestamp={response.validation_timestamp}"
            )

            # Enforce the proof-carrying contract AFTER metadata is injected
            if hasattr(response, "verify_proof_carrying_contract"):
                response.verify_proof_carrying_contract()

        # Create validation result
        result = ValidationResult(
            passed=passed,
            correlation_id=correlation_id,
            timestamp=forensic_ctx.timestamp,
            execution_time_ms=execution_time_ms,
            violations=violations,
            warnings=warnings,
            forensic_hash=forensic_ctx.response_hash,
            metadata={
                "execution_mode": self.execution_mode.value,
                "strict_mode": self.strict_mode,
                "checks_performed": len(forensic_ctx.validation_checks),
                "proof_carrying_injected": passed,  # Track if metadata was injected
            },
        )

        # Raise exception if critical violations detected and strict mode enabled
        if not passed and self.strict_mode:
            self._raise_security_breach(violations, forensic_ctx)

        # Log result
        if passed:
            log.info(f"[{correlation_id}] ✓ Fortress validation PASSED ({execution_time_ms:.2f}ms)")
        else:
            log.error(f"[{correlation_id}] ✗ Fortress validation FAILED: {len(violations)} violations")

        return result

    async def _validate_proof_tree(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate proof_tree existence and integrity"""
        forensic_ctx.validation_checks.append("proof_tree")

        if not self.config.proof_requirements.proof_tree_required:
            return None

        if getattr(response, 'proof_tree', None) is None:
            return {
                "type": ViolationType.MISSING_PROOF_TREE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": "Response missing required proof_tree",
                "details": {"requirement": "proof_tree_required=true", "actual": "proof_tree=None"},
            }

        # Validate proof depth if proof_tree exists
        proof_tree = getattr(response, 'proof_tree', None)
        if proof_tree and hasattr(proof_tree, "get_proof_depth"):
            try:
                depth = proof_tree.get_proof_depth()
                min_depth = self.config.proof_requirements.min_proof_depth

                if depth < min_depth:
                    return {
                        "type": ViolationType.MISSING_PROOF_TREE.value,
                        "severity": ViolationSeverity.HIGH.value,
                        "message": f"Proof tree depth {depth} below minimum {min_depth}",
                        "details": {"depth": depth, "min_depth": min_depth},
                    }
            except Exception as e:
                log.warning(f"Could not validate proof depth: {e}")

        # Validate Proof Tree Reconstruction (Document -> Evidence -> Rule -> Verdict)
        if proof_tree and hasattr(proof_tree, "steps"):
            has_facts = False
            has_rules = False
            
            for step in proof_tree.steps:
                evidence_list = step.get("evidence", [])
                for ev in evidence_list:
                    node_type = ev.get("node_type", "") if isinstance(ev, dict) else getattr(ev, "node_type", "")
                    if node_type == "Fact":
                        has_facts = True
                    elif node_type in ["LegalRule", "LegalPrecedent", "rule", "precedent", "statute"]:
                        has_rules = True
            
            # Diagnostic Fallbacks have 0 steps, which is valid if no proof path was found
            if len(proof_tree.steps) > 0 and not (has_facts and has_rules):
                return {
                    "type": ViolationType.MISSING_PROOF_TREE.value,
                    "severity": ViolationSeverity.CRITICAL.value,
                    "message": "Proof Tree Reconstruction Failed: Lineage must include Fact -> Rule/Precedent -> Conclusion",
                    "details": {"has_facts": has_facts, "has_rules": has_rules},
                }

        return None

    async def _validate_agreement_score(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate agreement_score meets threshold"""
        forensic_ctx.validation_checks.append("agreement_score")

        # Extract agreement_score from metadata
        agreement_score = getattr(response, 'metadata', {}).get("agreement_score")

        if agreement_score is None:
            # If no agreement_score, check if this is a single-mode response
            if getattr(response, 'reasoning_mode', None) in ["SYMBOLIC", "NEURAL"]:
                # Single-mode responses don't have agreement scores
                return None

            return {
                "type": ViolationType.AUDIT_TRAIL_INCOMPLETE.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": "Missing agreement_score in hybrid reasoning response",
                "details": {"reasoning_mode": response.reasoning_mode},
            }

        min_score = self.config.thresholds.min_agreement_score

        if agreement_score < min_score:
            return {
                "type": ViolationType.LOW_AGREEMENT_SCORE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": f"Agreement score {agreement_score} ({agreement_score:.2%}) below threshold {min_score:.2%}",
                "details": {
                    "agreement_score": agreement_score,
                    "threshold": min_score,
                    "gap": min_score - agreement_score,
                },
            }

        return None

    async def _validate_evidence_linkage(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate evidence linkage requirements"""
        forensic_ctx.validation_checks.append("evidence_linkage")

        if not self.config.hallucination_prevention.require_graph_evidence:
            return None

        # Check if derived_facts exist (evidence of graph reasoning)
        derived_facts = getattr(response, 'derived_facts', [])
        if not derived_facts or len(derived_facts) == 0:
            return {
                "type": ViolationType.MISSING_EVIDENCE.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": "No derived facts found (missing graph evidence)",
                "details": {"derived_facts_count": 0},
            }

        # R-07 Citation Traceability Enforcement
        proof_tree = getattr(response, 'proof_tree', None)
        if proof_tree and hasattr(proof_tree, "steps"):
            for step in proof_tree.steps:
                evidence_list = step.get("evidence", [])
                for ev in evidence_list:
                    node_type = ev.get("node_type", "") if isinstance(ev, dict) else getattr(ev, "node_type", "")
                    if node_type in ["LegalRule", "LegalPrecedent", "rule", "precedent", "statute"]:
                        justification = ev.get("justification", "") if isinstance(ev, dict) else getattr(ev, "justification", "")
                        # The justification MUST contain a verifiable source citation
                        if "[Source:" not in justification and "[Court:" not in justification:
                            return {
                                "type": ViolationType.MISSING_EVIDENCE.value,
                                "severity": ViolationSeverity.CRITICAL.value,
                                "message": f"R-07 Citation Traceability Violation: {node_type} lacks explicit source citation.",
                                "details": {"justification": justification},
                            }

        # HARDENING: Formal validation of derived facts
        converter = FOLConverter()
        invalid_facts = []
        for fact_str in derived_facts:
            try:
                converter.parse(fact_str)
            except ParseError as e:
                invalid_facts.append({"fact": fact_str, "error": str(e)})

        if invalid_facts:
            return {
                "type": ViolationType.DETERMINISM_FAILURE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": f"Formal Evidence Validation Failed: {len(invalid_facts)} invalid facts",
                "details": {"invalid_facts": invalid_facts[:5]},
            }

        return None

    async def _validate_audit_trail(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate audit trail completeness"""
        forensic_ctx.validation_checks.append("audit_trail")

        if not self.config.proof_requirements.audit_trail_required:
            return None

        # Check for required metadata fields
        required_fields = ["reasoning_mode", "execution_time_ms"]
        missing_fields = []
        
        for f in required_fields:
            if not hasattr(response, f) or getattr(response, f) is None:
                missing_fields.append(f)

        if missing_fields:
            return {
                "type": ViolationType.AUDIT_TRAIL_INCOMPLETE.value,
                "severity": ViolationSeverity.MEDIUM.value,
                "message": f"Audit trail missing required fields: {missing_fields}",
                "details": {"missing_fields": missing_fields},
            }

        return None

    async def _validate_determinism(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate determinism requirements"""
        forensic_ctx.validation_checks.append("determinism")

        if not self.config.hallucination_prevention.require_determinism:
            return None

        # Check if response contains non-deterministic indicators
        reasoning_mode = getattr(response, 'reasoning_mode', '')
        proof_tree = getattr(response, 'proof_tree', None)
        
        if reasoning_mode == "NEURAL" and not proof_tree:
            return {
                "type": ViolationType.DETERMINISM_FAILURE.value,
                "severity": ViolationSeverity.MEDIUM.value,
                "message": "Neural-only response without proof tree (non-deterministic)",
                "details": {"reasoning_mode": reasoning_mode},
            }

        return None

    async def _validate_contradictions(
        self, response: Any, forensic_ctx: ForensicContext
    ) -> dict[str, Any] | None:
        """Validate contradiction detection"""
        forensic_ctx.validation_checks.append("contradictions")

        if not self.config.hallucination_prevention.reject_contradictions:
            return None

        # Check metadata for contradiction markers
        metadata = getattr(response, 'metadata', {})
        contradictions = metadata.get("contradictions", [])

        if contradictions and len(contradictions) > 0:
            return {
                "type": ViolationType.CONTRADICTION_DETECTED.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": f"Contradictions detected: {len(contradictions)}",
                "details": {"contradictions": contradictions[:5]},  # Limit to first 5
            }

        return None

    def _compute_response_hash(self, response: Any) -> str:
        """Compute forensic hash of response for audit trail using deterministic serialization"""
        import json

        # Build deterministic dict from response
        if isinstance(response, dict):
            resp_dict = {
                "result": str(response.get("result", "")),
                "confidence": float(response.get("confidence", 0.0) or 0.0),
                "reasoning_mode": str(response.get("reasoning_mode", "")),
                "proof_tree": str(response.get("proof_tree", "")),
                "derived_facts": [str(f) for f in response.get("derived_facts", []) or []],
            }
        else:
            resp_dict = {
                "result": str(getattr(response, "result", "")),
                "confidence": float(getattr(response, "confidence", 0.0) or 0.0),
                "reasoning_mode": str(getattr(response, "reasoning_mode", "")),
                "proof_tree": str(getattr(response, "proof_tree", "")),
                "derived_facts": [str(f) for f in getattr(response, "derived_facts", []) or []],
            }

        hash_input = json.dumps(resp_dict, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        return f"fortress-{uuid.uuid4().hex[:12]}"

    def _update_stats(self, passed: bool, violations: list[dict[str, Any]], execution_time_ms: float) -> None:
        """Update validation statistics"""
        self.stats["total_validations"] += 1

        if passed:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1

        # Update violation counts by type
        for violation in violations:
            vtype = violation["type"]
            self.stats["violations_by_type"][vtype] = self.stats["violations_by_type"].get(vtype, 0) + 1

        if METRICS_AVAILABLE:
            collector = get_metrics_collector()
            collector.register_counter("mahoun_fortress_validation_total").inc()
            if not passed:
                collector.register_counter("mahoun_fortress_validation_failed_total").inc()
            for violation in violations:
                collector.register_counter("mahoun_security_breaches_total", labels={"type": violation["type"]}).inc()

        # Update average validation time
        total = self.stats["total_validations"]
        current_avg = self.stats["average_validation_time_ms"]
        self.stats["average_validation_time_ms"] = ((current_avg * (total - 1)) + execution_time_ms) / total

    def _raise_security_breach(self, violations: list[dict[str, Any]], forensic_ctx: ForensicContext) -> None:
        """Raise SecurityBreachException for critical violations"""
        critical_violations = [v for v in violations if v["severity"] == ViolationSeverity.CRITICAL.value]

        if not critical_violations:
            return

        primary_violation = critical_violations[0]

        raise SecurityBreachException(
            message=primary_violation["message"],
            violation_type=ViolationType(primary_violation["type"]),
            severity=ViolationSeverity.CRITICAL,
            forensic_context={
                "correlation_id": forensic_ctx.correlation_id,
                "timestamp": forensic_ctx.timestamp,
                "response_hash": forensic_ctx.response_hash,
                "total_violations": len(violations),
                "critical_violations": len(critical_violations),
                "violations": violations,
            },
            correlation_id=forensic_ctx.correlation_id,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics"""
        return self.stats.copy()

    def get_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit trail entries"""
        recent = self.audit_trail[-limit:]
        return [
            {
                "correlation_id": ctx.correlation_id,
                "timestamp": ctx.timestamp,
                "execution_mode": ctx.execution_mode.value,
                "response_hash": ctx.response_hash,
                "checks_performed": len(ctx.validation_checks),
                "violations_count": len(ctx.violations_detected),
            }
            for ctx in recent
        ]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


async def validate_reasoning_response(
    response: Any, correlation_id: str | None = None, strict_mode: bool = True
) -> ValidationResult:
    """
    Convenience function for one-off validation.

    Args:
        response: Reasoning response to validate
        correlation_id: Optional correlation ID
        strict_mode: If True, raise exceptions on violations

    Returns:
        ValidationResult

    Raises:
        SecurityBreachException: On critical violations (if strict_mode=True)
    """
    validator = FortressValidator(strict_mode=strict_mode)
    return await validator.validate(response, correlation_id)


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

log.info("FortressValidator module loaded: GOVERNANCE ENFORCEMENT ACTIVE")
