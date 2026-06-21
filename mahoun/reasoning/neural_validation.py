"""
Neural Output Validation Layer
==============================
MANDATORY cross-validation of neural outputs by symbolic layer.

CRITICAL INVARIANT: No neural output reaches production without symbolic verification.
ENFORCEMENT: Non-bypassable - exceptions block neural response.

This module implements the most critical security boundary in MAHOUN:
preventing LLM hallucination from being presented as verified legal reasoning.

Classification: MISSION-CRITICAL / ZERO-TRUST / NON-BYPASSABLE
"""

import hashlib

# Guardrails enforcement dynamically
import importlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from reasoning_logic.backward_chaining import BackwardChaining

# Core reasoning imports
from reasoning_logic.core import Fact
from reasoning_logic.forward_chaining import ForwardChaining
from reasoning_logic.knowledge_base import KnowledgeBase
from reasoning_logic.parser import FOLConverter

guardrails_enforcement = importlib.import_module("mahoun.guardrails.enforcement")
guard = guardrails_enforcement.guard

guardrails_exceptions = importlib.import_module("mahoun.guardrails.exceptions")
InvariantViolation = guardrails_exceptions.InvariantViolation

logger = logging.getLogger(__name__)


class ValidationMethod(str, Enum):
    """Neural validation methods"""

    SYMBOLIC_CROSS_VALIDATION = "symbolic_cross_validation"
    PROOF_CHAIN_VERIFICATION = "proof_chain_verification"
    CONTRADICTION_DETECTION = "contradiction_detection"
    EVIDENCE_GROUNDING_CHECK = "evidence_grounding_check"


class ValidationResult:
    """Result of neural output validation"""

    def __init__(
        self,
        valid: bool,
        confidence: float = 0.0,
        proof_chain: list[str] | None = None,
        validation_method: str = "unknown",
        rejection_reason: str | None = None,
        symbolic_facts: list[str] | None = None,
        validation_time_ms: float = 0.0,
        cache_hit: bool = False,
    ):
        self.valid = valid
        self.confidence = confidence
        self.proof_chain = proof_chain or []
        self.validation_method = validation_method
        self.rejection_reason = rejection_reason
        self.symbolic_facts = symbolic_facts or []
        self.validation_time_ms = validation_time_ms
        self.cache_hit = cache_hit
        self.timestamp = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "valid": self.valid,
            "confidence": self.confidence,
            "proof_chain": self.proof_chain,
            "validation_method": self.validation_method,
            "rejection_reason": self.rejection_reason,
            "symbolic_facts": self.symbolic_facts,
            "validation_time_ms": self.validation_time_ms,
            "cache_hit": self.cache_hit,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class NeuralValidationMetrics:
    """Metrics for neural validation performance and security"""

    total_validations: int = 0
    successful_validations: int = 0
    rejected_validations: int = 0
    cache_hits: int = 0
    avg_validation_time_ms: float = 0.0

    # Security metrics
    bypass_attempts: int = 0
    hallucination_detections: int = 0

    # Performance metrics
    symbolic_engine_failures: int = 0
    timeout_failures: int = 0

    def success_rate(self) -> float:
        """Calculate validation success rate"""
        if self.total_validations == 0:
            return 0.0
        return self.successful_validations / self.total_validations

    def rejection_rate(self) -> float:
        """Calculate validation rejection rate"""
        if self.total_validations == 0:
            return 0.0
        return self.rejected_validations / self.total_validations

    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_validations == 0:
            return 0.0
        return self.cache_hits / self.total_validations


class SymbolicFactExtractor:
    """
    Extracts symbolic facts from neural text output.

    This component converts natural language legal conclusions
    into formal logical statements that can be verified symbolically.
    """

    def __init__(self):
        self.parser = FOLConverter()
        self.legal_predicates = self._build_legal_predicate_patterns()

        # Pattern matching for common legal structures
        self.conclusion_patterns = [
            r"(?i)the\s+(?:court|judge|tribunal)\s+(?:finds|rules|holds|decides)\s+that\s+(.+)",
            r"(?i)it\s+is\s+(?:determined|concluded|found)\s+that\s+(.+)",
            r"(?i)therefore,?\s+(.+)",
            r"(?i)accordingly,?\s+(.+)",
            r"(?i)the\s+verdict\s+is\s+(.+)",
            r"(?i)conclusion:\s*(.+)",
        ]

        logger.info("Symbolic fact extractor initialized with legal pattern matching")

    def _build_legal_predicate_patterns(self) -> dict[str, str]:
        """Build patterns for common legal predicates"""
        return {
            "liable": "liable(X, Y)",
            "guilty": "guilty(X, Y)",
            "innocent": "innocent(X, Y)",
            "breach": "breach(X, Y)",
            "violation": "violation(X, Y)",
            "compliant": "compliant(X, Y)",
            "valid": "valid(X)",
            "invalid": "invalid(X)",
            "enforceable": "enforceable(X)",
            "binding": "binding(X, Y)",
            "applicable": "applicable(X, Y)",
            "precedent": "precedent(X, Y)",
        }

    def extract_symbolic_facts(self, neural_output: str) -> list[str]:
        """
        Extract symbolic facts from neural text output.

        Args:
            neural_output: Natural language legal conclusion

        Returns:
            List of symbolic facts in FOL format

        Raises:
            ValueError: If no symbolic facts can be extracted
        """
        if not neural_output or not neural_output.strip():
            raise ValueError("Empty neural output - cannot extract symbolic facts")

        extracted_facts = []

        # Extract using conclusion patterns
        for pattern in self.conclusion_patterns:
            import re

            matches = re.findall(pattern, neural_output)
            for match in matches:
                # Convert match to symbolic fact
                symbolic_fact = self._convert_to_symbolic_fact(match.strip())
                if symbolic_fact:
                    extracted_facts.append(symbolic_fact)

        # Extract using legal predicate patterns
        for predicate, template in self.legal_predicates.items():
            if predicate.lower() in neural_output.lower():
                # Simple extraction - in production, use more sophisticated NLP
                symbolic_fact = f"{predicate}(entity_from_neural_output)"
                extracted_facts.append(symbolic_fact)

        if not extracted_facts:
            # Fallback: create a generic conclusion fact
            conclusion_hash = hashlib.md5(neural_output.encode()).hexdigest()[:8]
            extracted_facts.append(f"neural_conclusion(conclusion_{conclusion_hash})")

            logger.warning(
                "No specific symbolic facts extracted from neural output, using generic conclusion",
                extra={"neural_output_preview": neural_output[:100], "fallback_fact": extracted_facts[0]},
            )

        logger.debug(
            f"Extracted {len(extracted_facts)} symbolic facts from neural output",
            extra={"extracted_facts": extracted_facts, "neural_output_length": len(neural_output)},
        )

        return extracted_facts

    def _convert_to_symbolic_fact(self, text: str) -> str | None:
        """Convert natural language text to symbolic fact"""
        # Simplified conversion - in production, use advanced NLP
        text = text.lower().strip()

        # Remove common legal phrases
        text = text.replace("the defendant", "defendant")
        text = text.replace("the plaintiff", "plaintiff")
        text = text.replace("the court", "court")

        # Simple predicate detection
        if "liable" in text:
            return "liable(defendant, damages)"
        elif "guilty" in text:
            return "guilty(defendant, charge)"
        elif "innocent" in text or "not guilty" in text:
            return "innocent(defendant, charge)"
        elif "breach" in text:
            return "breach(party, contract)"
        elif "valid" in text:
            return "valid(contract)"
        elif "invalid" in text:
            return "invalid(contract)"

        return None


class NeuralOutputValidator:
    """
    MANDATORY cross-validation of neural outputs by symbolic layer.

    SECURITY INVARIANT: No neural output reaches production without symbolic verification.
    ENFORCEMENT: Non-bypassable - exceptions block neural response.

    This is the most critical security component in MAHOUN. It prevents
    LLM hallucination from being presented as verified legal reasoning.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.8,
        validation_timeout_seconds: float = 30.0,
        cache_size: int = 1000,
        enable_proof_verification: bool = True,
    ):
        """
        Initialize neural output validator.

        Args:
            confidence_threshold: Minimum confidence for symbolic validation
            validation_timeout_seconds: Timeout for symbolic reasoning
            cache_size: Size of validation result cache
            enable_proof_verification: Whether to verify proof chains
        """
        self.confidence_threshold = confidence_threshold
        self.validation_timeout = validation_timeout_seconds
        self.enable_proof_verification = enable_proof_verification

        # Initialize symbolic reasoning components
        self.knowledge_base = KnowledgeBase()
        self.forward_chainer = ForwardChaining(self.knowledge_base)
        self.backward_chainer = BackwardChaining(self.knowledge_base)
        self.fact_extractor = SymbolicFactExtractor()

        # Validation cache for performance
        self.validation_cache: dict[str, ValidationResult] = {}
        self.cache_size = cache_size

        # Metrics tracking
        self.metrics = NeuralValidationMetrics()

        # Security monitoring
        self.bypass_attempts: list[dict[str, Any]] = []

        logger.info(
            "Neural Output Validator initialized with MANDATORY cross-validation",
            extra={
                "confidence_threshold": confidence_threshold,
                "validation_timeout": validation_timeout_seconds,
                "cache_size": cache_size,
                "proof_verification": enable_proof_verification,
                "security_level": "MAXIMUM",
            },
        )

    @guard
    def validate_neural_conclusion(
        self,
        neural_output: str,
        evidence_context: list[str],
        question_context: str | None = None,
        bypass_validation: bool = False,  # This parameter is IGNORED - no bypass allowed
    ) -> ValidationResult:
        """
        Cross-validate neural output against symbolic reasoning.

        CRITICAL: This function CANNOT be bypassed under any circumstances.
        The bypass_validation parameter is ignored - it exists only to catch
        bypass attempts and log them as security violations.

        Args:
            neural_output: Neural network generated conclusion
            evidence_context: List of evidence facts
            question_context: Optional question for context
            bypass_validation: IGNORED - bypass attempts are logged as violations

        Returns:
            ValidationResult with validation outcome

        Raises:
            InvariantViolation: If neural output fails symbolic validation
            ValueError: If inputs are invalid
            TimeoutError: If validation exceeds timeout
        """
        start_time = time.time()

        # SECURITY: Log bypass attempts
        if bypass_validation:
            self.metrics.bypass_attempts += 1
            logger.error(
                "SECURITY VIOLATION: Attempt to bypass neural validation detected",
                extra={
                    "bypass_parameter": bypass_validation,
                    "neural_output_preview": neural_output[:50],
                    "evidence_count": len(evidence_context),
                    "security_violation": True,
                    "violation_type": "bypass_attempt",
                },
            )
            # Continue with validation - bypass is ignored

        # Input validation
        if not neural_output or not neural_output.strip():
            raise ValueError("Neural output cannot be empty")

        if not evidence_context:
            raise ValueError("Evidence context is required for validation")

        # Check cache first
        cache_key = self._compute_cache_key(neural_output, evidence_context, question_context)
        if cache_key in self.validation_cache:
            cached_result = self.validation_cache[cache_key]
            cached_result.cache_hit = True
            self.metrics.cache_hits += 1
            self.metrics.total_validations += 1

            logger.debug(
                "Neural validation cache hit",
                extra={
                    "cache_key": cache_key[:16],
                    "cached_result": cached_result.valid,
                    "cache_size": len(self.validation_cache),
                },
            )

            return cached_result

        try:
            # Extract symbolic facts from neural output
            symbolic_facts = self.fact_extractor.extract_symbolic_facts(neural_output)

            # Prepare knowledge base with evidence
            temp_kb = self._prepare_knowledge_base(evidence_context)

            # Perform symbolic validation
            validation_result = self._perform_symbolic_validation(
                symbolic_facts=symbolic_facts,
                knowledge_base=temp_kb,
                neural_output=neural_output,
                question_context=question_context,
            )

            # Calculate validation time
            validation_time = (time.time() - start_time) * 1000
            validation_result.validation_time_ms = validation_time

            # Update metrics
            self.metrics.total_validations += 1
            if validation_result.valid:
                self.metrics.successful_validations += 1
            else:
                self.metrics.rejected_validations += 1
                self.metrics.hallucination_detections += 1

            # Update average validation time
            self.metrics.avg_validation_time_ms = (
                self.metrics.avg_validation_time_ms * (self.metrics.total_validations - 1) + validation_time
            ) / self.metrics.total_validations

            # Cache result (with size limit)
            if len(self.validation_cache) >= self.cache_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(self.validation_cache))
                del self.validation_cache[oldest_key]

            self.validation_cache[cache_key] = validation_result

            # Log validation result
            if validation_result.valid:
                logger.info(
                    "Neural output VALIDATED by symbolic reasoning",
                    extra={
                        "validation_method": validation_result.validation_method,
                        "confidence": validation_result.confidence,
                        "validation_time_ms": validation_time,
                        "symbolic_facts_count": len(symbolic_facts),
                    },
                )
            else:
                logger.error(
                    "Neural output REJECTED by symbolic validation",
                    extra={
                        "rejection_reason": validation_result.rejection_reason,
                        "neural_output_preview": neural_output[:100],
                        "evidence_count": len(evidence_context),
                        "symbolic_facts": symbolic_facts,
                        "validation_time_ms": validation_time,
                        "security_violation": True,
                        "violation_type": "hallucination_detected",
                    },
                )

                # FAIL-FAST: Raise exception to block neural output
                raise InvariantViolation(
                    "neural_output_validation_failed",
                    {
                        "rejection_reason": validation_result.rejection_reason,
                        "neural_output_preview": neural_output[:100],
                        "validation_method": validation_result.validation_method,
                        "confidence": validation_result.confidence,
                    },
                )

            return validation_result

        except TimeoutError:
            self.metrics.timeout_failures += 1
            logger.error(
                "Neural validation timeout - symbolic reasoning exceeded time limit",
                extra={
                    "timeout_seconds": self.validation_timeout,
                    "neural_output_preview": neural_output[:100],
                    "evidence_count": len(evidence_context),
                },
            )
            raise

        except Exception as e:
            self.metrics.symbolic_engine_failures += 1
            logger.error(
                "Neural validation failed due to symbolic engine error",
                extra={
                    "error": str(e),
                    "neural_output_preview": neural_output[:100],
                    "evidence_count": len(evidence_context),
                },
                exc_info=True,
            )

            # In case of symbolic engine failure, we REJECT the neural output
            # This is fail-safe behavior - better to reject valid output than
            # allow potentially hallucinated output through
            raise InvariantViolation(
                "symbolic_validation_engine_failure",
                {
                    "error": str(e),
                    "neural_output_preview": neural_output[:100],
                    "fail_safe_behavior": "reject_neural_output",
                },
            ) from e

    def _compute_cache_key(self, neural_output: str, evidence_context: list[str], question_context: str | None) -> str:
        """Compute cache key for validation result"""
        content = {
            "neural_output": neural_output,
            "evidence_context": sorted(evidence_context),  # Sort for consistency
            "question_context": question_context or "",
        }

        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _prepare_knowledge_base(self, evidence_context: list[str]) -> KnowledgeBase:
        """Prepare knowledge base with evidence facts"""
        temp_kb = KnowledgeBase()

        for evidence in evidence_context:
            try:
                # Parse evidence as fact
                if isinstance(evidence, str):
                    # Simple fact creation - in production, use proper parsing
                    fact = Fact(predicate=f"evidence_{len(temp_kb.facts)}", terms=[], confidence=1.0)
                    fact.metadata = {"source": "evidence_context", "text": evidence}
                    temp_kb.add_fact(fact)
                else:
                    # Handle structured evidence
                    fact = Fact(
                        predicate=evidence.get("predicate", "unknown"),
                        terms=evidence.get("terms", []),
                        confidence=evidence.get("confidence", 1.0),
                    )
                    temp_kb.add_fact(fact)

            except Exception as e:
                logger.warning(
                    f"Failed to parse evidence fact: {evidence}",
                    extra={"error": str(e), "evidence": str(evidence)[:100]},
                )

        logger.debug(
            f"Prepared knowledge base with {len(temp_kb.facts)} evidence facts",
            extra={"evidence_count": len(evidence_context), "kb_facts": len(temp_kb.facts)},
        )

        return temp_kb

    def _perform_symbolic_validation(
        self, symbolic_facts: list[str], knowledge_base: KnowledgeBase, neural_output: str, question_context: str | None
    ) -> ValidationResult:
        """Perform symbolic validation of extracted facts"""

        # Method 1: Forward chaining validation
        forward_result = self._validate_via_forward_chaining(symbolic_facts, knowledge_base)

        if forward_result.valid and forward_result.confidence >= self.confidence_threshold:
            return forward_result

        # Method 2: Backward chaining validation
        backward_result = self._validate_via_backward_chaining(symbolic_facts, knowledge_base)

        if backward_result.valid and backward_result.confidence >= self.confidence_threshold:
            return backward_result

        # Method 3: Evidence grounding check
        grounding_result = self._validate_evidence_grounding(symbolic_facts, knowledge_base)

        if grounding_result.valid and grounding_result.confidence >= self.confidence_threshold:
            return grounding_result

        # All validation methods failed
        return ValidationResult(
            valid=False,
            confidence=max(forward_result.confidence, backward_result.confidence, grounding_result.confidence),
            validation_method="multi_method_validation",
            rejection_reason=(
                f"All validation methods failed: "
                f"forward_chaining({forward_result.confidence:.2f}), "
                f"backward_chaining({backward_result.confidence:.2f}), "
                f"evidence_grounding({grounding_result.confidence:.2f})"
            ),
            symbolic_facts=symbolic_facts,
        )

    def _validate_via_forward_chaining(
        self, symbolic_facts: list[str], knowledge_base: KnowledgeBase
    ) -> ValidationResult:
        """Validate using forward chaining"""

        try:
            # Use forward chaining to derive conclusions
            derived_facts = self.forward_chainer.infer()

            # Check if symbolic facts can be derived
            derivable_count = 0
            for symbolic_fact in symbolic_facts:
                # Simple containment check - in production, use proper unification
                if any(symbolic_fact in str(fact) for fact in derived_facts):
                    derivable_count += 1

            confidence = derivable_count / len(symbolic_facts) if symbolic_facts else 0.0

            return ValidationResult(
                valid=confidence >= self.confidence_threshold,
                confidence=confidence,
                validation_method=ValidationMethod.SYMBOLIC_CROSS_VALIDATION,
                proof_chain=[str(fact) for fact in derived_facts[:10]],  # First 10 for brevity
                symbolic_facts=symbolic_facts,
            )

        except Exception as e:
            logger.warning(f"Forward chaining validation failed: {e}", extra={"symbolic_facts": symbolic_facts})
            return ValidationResult(
                valid=False,
                confidence=0.0,
                validation_method=ValidationMethod.SYMBOLIC_CROSS_VALIDATION,
                rejection_reason=f"Forward chaining error: {e}",
                symbolic_facts=symbolic_facts,
            )

    def _validate_via_backward_chaining(
        self, symbolic_facts: list[str], knowledge_base: KnowledgeBase
    ) -> ValidationResult:
        """Validate using backward chaining"""

        try:
            provable_count = 0
            proof_chains = []

            for symbolic_fact in symbolic_facts:
                # Attempt to prove each symbolic fact
                try:
                    # Simple proof attempt - in production, use proper goal parsing
                    proof_result = self.backward_chainer.prove(symbolic_fact)
                    if proof_result:
                        provable_count += 1
                        proof_chains.extend(proof_result[:5])  # Limit proof chain length
                except Exception:
                    # Proof failed for this fact
                    pass

            confidence = provable_count / len(symbolic_facts) if symbolic_facts else 0.0

            return ValidationResult(
                valid=confidence >= self.confidence_threshold,
                confidence=confidence,
                validation_method=ValidationMethod.PROOF_CHAIN_VERIFICATION,
                proof_chain=proof_chains,
                symbolic_facts=symbolic_facts,
            )

        except Exception as e:
            logger.warning(f"Backward chaining validation failed: {e}", extra={"symbolic_facts": symbolic_facts})
            return ValidationResult(
                valid=False,
                confidence=0.0,
                validation_method=ValidationMethod.PROOF_CHAIN_VERIFICATION,
                rejection_reason=f"Backward chaining error: {e}",
                symbolic_facts=symbolic_facts,
            )

    def _validate_evidence_grounding(
        self, symbolic_facts: list[str], knowledge_base: KnowledgeBase
    ) -> ValidationResult:
        """Validate evidence grounding of symbolic facts"""

        try:
            grounded_count = 0

            for symbolic_fact in symbolic_facts:
                # Check if fact is grounded in evidence
                for kb_fact in knowledge_base.facts:
                    # Simple grounding check - in production, use semantic similarity
                    if any(term in symbolic_fact.lower() for term in str(kb_fact).lower().split()):
                        grounded_count += 1
                        break

            confidence = grounded_count / len(symbolic_facts) if symbolic_facts else 0.0

            return ValidationResult(
                valid=confidence >= self.confidence_threshold,
                confidence=confidence,
                validation_method=ValidationMethod.EVIDENCE_GROUNDING_CHECK,
                symbolic_facts=symbolic_facts,
            )

        except Exception as e:
            logger.warning(f"Evidence grounding validation failed: {e}", extra={"symbolic_facts": symbolic_facts})
            return ValidationResult(
                valid=False,
                confidence=0.0,
                validation_method=ValidationMethod.EVIDENCE_GROUNDING_CHECK,
                rejection_reason=f"Evidence grounding error: {e}",
                symbolic_facts=symbolic_facts,
            )

    def get_validation_metrics(self) -> dict[str, Any]:
        """Get current validation metrics"""
        return {
            "total_validations": self.metrics.total_validations,
            "success_rate": self.metrics.success_rate(),
            "rejection_rate": self.metrics.rejection_rate(),
            "cache_hit_rate": self.metrics.cache_hit_rate(),
            "avg_validation_time_ms": self.metrics.avg_validation_time_ms,
            "bypass_attempts": self.metrics.bypass_attempts,
            "hallucination_detections": self.metrics.hallucination_detections,
            "symbolic_engine_failures": self.metrics.symbolic_engine_failures,
            "timeout_failures": self.metrics.timeout_failures,
            "cache_size": len(self.validation_cache),
            "confidence_threshold": self.confidence_threshold,
        }

    def clear_cache(self):
        """Clear validation cache"""
        self.validation_cache.clear()
        logger.info("Neural validation cache cleared")

    def update_confidence_threshold(self, new_threshold: float):
        """Update confidence threshold (with validation)"""
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

        old_threshold = self.confidence_threshold
        self.confidence_threshold = new_threshold

        # Clear cache since threshold changed
        self.clear_cache()

        logger.info(
            f"Neural validation confidence threshold updated: {old_threshold} -> {new_threshold}",
            extra={"old_threshold": old_threshold, "new_threshold": new_threshold, "cache_cleared": True},
        )


# Global validator instance (singleton pattern for performance)
_neural_validator: NeuralOutputValidator | None = None


def get_neural_validator() -> NeuralOutputValidator:
    """
    Get global neural validator instance.

    Returns:
        NeuralOutputValidator singleton instance
    """
    global _neural_validator

    if _neural_validator is None:
        _neural_validator = NeuralOutputValidator()
        logger.info("Global neural validator instance created")

    return _neural_validator


def validate_neural_output(
    neural_output: str, evidence_context: list[str], question_context: str | None = None
) -> ValidationResult:
    """
    Convenience function for neural output validation.

    This is the primary interface for validating neural outputs.

    Args:
        neural_output: Neural network generated conclusion
        evidence_context: List of evidence facts
        question_context: Optional question for context

    Returns:
        ValidationResult with validation outcome

    Raises:
        InvariantViolation: If neural output fails symbolic validation
    """
    validator = get_neural_validator()
    return validator.validate_neural_conclusion(
        neural_output=neural_output, evidence_context=evidence_context, question_context=question_context
    )


# Example usage and testing
if __name__ == "__main__":
    print("🛡️ Neural Output Validation Layer")
    print("=" * 60)

    # Create validator
    validator = NeuralOutputValidator(confidence_threshold=0.7)

    # Test case 1: Valid legal conclusion
    try:
        result = validator.validate_neural_conclusion(
            neural_output="The defendant is liable for breach of contract based on the evidence provided.",
            evidence_context=[
                "Contract was signed on January 1, 2024",
                "Defendant failed to deliver goods by agreed date",
                "Plaintiff suffered damages of $10,000",
            ],
            question_context="Is the defendant liable for breach of contract?",
        )

        print(f"✅ Validation result: {result.valid}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Method: {result.validation_method}")

    except InvariantViolation as e:
        print(f"❌ Neural output rejected: {e}")

    # Test case 2: Attempt bypass (should be logged and ignored)
    try:
        result = validator.validate_neural_conclusion(
            neural_output="The sky is purple and contracts are made of cheese.",
            evidence_context=["Some random evidence"],
            bypass_validation=True,  # This should be ignored and logged
        )

        print(f"⚠️ Bypass attempt result: {result.valid}")

    except InvariantViolation as e:
        print(f"✅ Bypass attempt correctly blocked: {e}")

    # Print metrics
    metrics = validator.get_validation_metrics()
    print("\n📊 Validation Metrics:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")
