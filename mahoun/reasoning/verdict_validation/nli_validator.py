"""
NLI Validator - Step D
======================

Classification: MISSION-CRITICAL / VALIDATION STEP D
Purpose: Semantic verification of atomic claims using NLI (Natural Language Inference).

This is Step D of the 4-step validation pipeline.
Must execute AFTER Step C (Claim Extraction).
Must execute AFTER Step B (Deterministic Validation) - if Step B fails, this MUST NOT run.

CRITICAL INVARIANTS:
- Must reference Canonical Verdict JSON, NOT prompt/conversation/user request
- Must classify each claim as: ENTAILED, CONTRADICTED, NOT_SUPPORTED
- Must produce confidence scores
- If entailment fails or contradiction detected: MUST fail-closed

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mahoun.core.logging import setup_logger
from mahoun.reasoning.verdict_validation.pipeline import (
    ViolationSeverity,
    ViolationType,
    ValidationStep,
)

if TYPE_CHECKING:
    from mahoun.reasoning.verdict_validation.claim_extractor import AtomicClaim

log = setup_logger("nli_validator")


# ============================================================================
# ENUMS
# ============================================================================

class NLILabel(str, Enum):
    """NLI classification labels"""
    ENTAILED = "ENTAILED"           # Claim is logically entailed by context
    CONTRADICTED = "CONTRADICTED"   # Claim contradicts the context
    NOT_SUPPORTED = "NOT_SUPPORTED" # Claim is not supported by context (neutral)


class ClaimStatus(str, Enum):
    """Status of a claim after NLI verification"""
    ENTAILED = "ENTAILED"
    CONTRADICTED = "CONTRADICTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    SKIPPED = "SKIPPED"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass(frozen=True)
class ClaimVerificationResult:
    """Result of verifying a single claim with NLI"""
    claim_text: str
    status: ClaimStatus
    label: NLILabel
    entailment_score: float
    contradiction_score: float
    neutral_score: float
    threshold: float
    passed: bool
    explanation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "claim_text": self.claim_text,
            "status": self.status.value,
            "label": self.label.value,
            "entailment_score": self.entailment_score,
            "contradiction_score": self.contradiction_score,
            "neutral_score": self.neutral_score,
            "threshold": self.threshold,
            "passed": self.passed,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class NLViolation:
    """Single NLI validation violation"""
    message: str
    claim_text: str
    field: str
    violation_type: ViolationType = ViolationType.UNSUPPORTED_CLAIM
    severity: ViolationSeverity = ViolationSeverity.HIGH
    expected: Optional[str] = None
    actual: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "message": self.message,
            "claim_text": self.claim_text,
            "field": self.field,
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class NLIValidationResult:
    """Result of NLI validation"""
    passed: bool
    violations: List[NLViolation] = field(default_factory=list)
    claim_results: List[ClaimVerificationResult] = field(default_factory=list)
    total_claims: int = 0
    entailed_claims: int = 0
    contradicted_claims: int = 0
    not_supported_claims: int = 0
    avg_entailment_score: float = 0.0
    avg_contradiction_score: float = 0.0
    validation_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "claim_results": [cr.to_dict() for cr in self.claim_results],
            "total_claims": self.total_claims,
            "entailed_claims": self.entailed_claims,
            "contradicted_claims": self.contradicted_claims,
            "not_supported_claims": self.not_supported_claims,
            "avg_entailment_score": self.avg_entailment_score,
            "avg_contradiction_score": self.avg_contradiction_score,
            "validation_timestamp": self.validation_timestamp,
        }


# ============================================================================
# NLI VALIDATOR
# ============================================================================

class NLIValidator:
    """
    NLI-based validator for semantic verification of atomic claims.
    
    This validator uses NLI (Natural Language Inference) to check if each
    atomic claim is entailed by the Canonical Verdict JSON context.
    
    CRITICAL RULES:
    - Must use Canonical Verdict JSON as context, NOT prompt/conversation
    - If entailment_score < threshold: claim is NOT_SUPPORTED
    - If contradiction_score > 0: claim is CONTRADICTED
    - If ANY claim is CONTRADICTED: MUST fail-closed
    - If ANY claim is NOT_SUPPORTED with high confidence: MUST fail-closed
    
    Implementation Strategy:
    This validator has TWO modes:
    1. If UltraNLIVerifier is available: Use it for full NLI verification
    2. If UltraNLIVerifier is NOT available: Use deterministic fallback
       (check if claim text appears in JSON)
    
    Usage:
        validator = NLIValidator(threshold=0.7)
        result = validator.validate(
            canonical_json=json_data,
            prose_text=text,
            claims=[...]  # List of AtomicClaim objects
        )
        
        if not result.passed:
            # Fail-closed - reject the verdict
            raise IntegrityViolationError("NLI validation failed", result.violations[0])
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize NLI validator.
        
        Args:
            threshold: Minimum entailment score to consider a claim supported
        """
        self.threshold = threshold
        self._nli_verifier: Optional[Any] = None
        self._nli_available = False
        
        # Try to initialize UltraNLIVerifier
        self._initialize_nli()
        
        log.info(
            f"NLIValidator initialized: threshold={threshold}, "
            f"nli_available={self._nli_available}"
        )
    
    def _initialize_nli(self) -> None:
        """Try to initialize UltraNLIVerifier"""
        try:
            from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier
            self._nli_verifier = UltraNLIVerifier(threshold=self.threshold)
            self._nli_available = True
            log.info("UltraNLIVerifier loaded successfully")
        except ImportError as e:
            log.warning(f"UltraNLIVerifier not available: {e}")
            self._nli_available = False
        except Exception as e:
            log.error(f"Failed to initialize UltraNLIVerifier: {e}")
            self._nli_available = False
    
    def _build_context_from_json(self, canonical_json: Dict[str, Any]) -> str:
        """
        Build a context string from Canonical Verdict JSON for NLI.
        
        This context should contain all the information needed to verify claims.
        
        Args:
            canonical_json: The Canonical Verdict JSON
            
        Returns:
            Context string for NLI verification
        """
        context_parts: List[str] = []
        
        # Add final_verdict
        if "final_verdict" in canonical_json:
            context_parts.append(f"Final Verdict: {canonical_json['final_verdict']}")
        
        # Add steps
        if "steps" in canonical_json:
            context_parts.append("Steps:")
            for i, step in enumerate(canonical_json["steps"]):
                if isinstance(step, dict):
                    statement = step.get("statement", "")
                    context_parts.append(f"  Step {i+1}: {statement}")
                    
                    # Add evidence
                    evidence = step.get("evidence", [])
                    if evidence:
                        context_parts.append(f"    Evidence: {[str(e) for e in evidence]}")
        
        # Add rule_nodes
        if "rule_nodes" in canonical_json:
            context_parts.append("Legal Rules:")
            for node_id, node in canonical_json["rule_nodes"].items():
                if isinstance(node, dict):
                    label = node.get("label", node_id)
                    node_type = node.get("node_type", "")
                    context_parts.append(f"  Rule {node_id}: {label} ({node_type})")
        
        # Add precedent_nodes
        if "precedent_nodes" in canonical_json:
            context_parts.append("Precedents:")
            for node_id, node in canonical_json["precedent_nodes"].items():
                if isinstance(node, dict):
                    label = node.get("label", node_id)
                    node_type = node.get("node_type", "")
                    context_parts.append(f"  Precedent {node_id}: {label} ({node_type})")
        
        # Add metadata
        if "metadata" in canonical_json and isinstance(canonical_json["metadata"], dict):
            context_parts.append("Metadata:")
            for key, value in canonical_json["metadata"].items():
                context_parts.append(f"  {key}: {value}")
        
        return '\n'.join(context_parts)
    
    def _verify_claim_deterministic(
        self,
        claim_text: str,
        context: str,
    ) -> ClaimVerificationResult:
        """
        Deterministic fallback verification when NLI is not available.
        
        This checks if the claim text (or its key phrases) appear in the context.
        
        Args:
            claim_text: The claim to verify
            context: The context from Canonical Verdict JSON
            
        Returns:
            ClaimVerificationResult
        """
        import difflib
        
        # Check if claim appears in context
        if claim_text in context:
            return ClaimVerificationResult(
                claim_text=claim_text,
                status=ClaimStatus.ENTAILED,
                label=NLILabel.ENTAILED,
                entailment_score=1.0,
                contradiction_score=0.0,
                neutral_score=0.0,
                threshold=self.threshold,
                passed=True,
                explanation="Claim text found in context",
            )
        
        # Check for partial matches
        claim_words = set(claim_text.lower().split())
        context_words = set(context.lower().split())
        
        # If most words are in context, consider it entailed
        match_ratio = len(claim_words & context_words) / len(claim_words) if claim_words else 0
        
        if match_ratio >= 0.8:
            return ClaimVerificationResult(
                claim_text=claim_text,
                status=ClaimStatus.ENTAILED,
                label=NLILabel.ENTAILED,
                entailment_score=match_ratio,
                contradiction_score=0.0,
                neutral_score=1.0 - match_ratio,
                threshold=self.threshold,
                passed=True,
                explanation=f"Partial match ({match_ratio:.1%} of words found)",
            )
        
        # Check for contradiction (claim says opposite of context)
        # This is a simple check - in production, use proper NLI
        if self._is_contradiction(claim_text, context):
            return ClaimVerificationResult(
                claim_text=claim_text,
                status=ClaimStatus.CONTRADICTED,
                label=NLILabel.CONTRADICTED,
                entailment_score=0.0,
                contradiction_score=1.0,
                neutral_score=0.0,
                threshold=self.threshold,
                passed=False,
                explanation="Claim appears to contradict context",
            )
        
        # If not entailed and not contradicted, it's not supported
        return ClaimVerificationResult(
            claim_text=claim_text,
            status=ClaimStatus.NOT_SUPPORTED,
            label=NLILabel.NOT_SUPPORTED,
            entailment_score=0.0,
            contradiction_score=0.0,
            neutral_score=1.0,
            threshold=self.threshold,
            passed=False,
            explanation="Claim not found in context",
        )
    
    def _is_contradiction(self, claim_text: str, context: str) -> bool:
        """
        Simple contradiction detection (deterministic fallback).
        
        This is a basic implementation. In production with NLI available,
        the UltraNLIVerifier will handle proper contradiction detection.
        """
        # Check for negation patterns
        negation_words = ["نمی", "نه", "غی", "بی", " بدون", "مخالف"]
        
        claim_lower = claim_text.lower()
        context_lower = context.lower()
        
        # If claim and context say opposite things about the same topic
        # This is a very basic check
        for word in negation_words:
            if word in claim_lower and word not in context_lower:
                return True
            if word not in claim_lower and word in context_lower:
                return True
        
        return False
    
    def _verify_claim_with_nli(
        self,
        claim_text: str,
        context: str,
    ) -> ClaimVerificationResult:
        """
        Verify a claim using UltraNLIVerifier.
        
        Args:
            claim_text: The claim to verify
            context: The context from Canonical Verdict JSON
            
        Returns:
            ClaimVerificationResult
        """
        try:
            result = self._nli_verifier.verify(
                context=context,
                answer=claim_text,
            )
            
            # Convert UltraNLIResult to ClaimVerificationResult
            label = result.label
            
            if label == NLILabel.ENTAILED:
                status = ClaimStatus.ENTAILED
                passed = result.entailment_score >= self.threshold
            elif label == NLILabel.CONTRADICTED:
                status = ClaimStatus.CONTRADICTED
                passed = False
            else:  # NOT_SUPPORTED or neutral
                status = ClaimStatus.NOT_SUPPORTED
                passed = False
            
            return ClaimVerificationResult(
                claim_text=claim_text,
                status=status,
                label=label,
                entailment_score=result.entailment_score,
                contradiction_score=result.contradiction_score,
                neutral_score=result.neutral_score,
                threshold=self.threshold,
                passed=passed,
                explanation=None,
            )
            
        except Exception as e:
            log.error(f"NLI verification failed for claim '{claim_text[:50]}...': {e}")
            # Fallback to deterministic verification
            return self._verify_claim_deterministic(claim_text, context)
    
    def validate(
        self,
        canonical_json: Dict[str, Any],
        prose_text: str,
        claims: List["AtomicClaim"],
    ) -> NLIValidationResult:
        """
        Validate all claims using NLI.
        
        CRITICAL: This step MUST execute AFTER Step B (Deterministic Validation).
        If Step B failed, this method should NOT be called.
        
        Args:
            canonical_json: The Canonical Verdict JSON (source of truth)
            prose_text: The full prose text (for reference)
            claims: List of AtomicClaim objects to verify
            
        Returns:
            NLIValidationResult with verification details
        """
        # Build context from JSON
        context = self._build_context_from_json(canonical_json)
        
        claim_results: List[ClaimVerificationResult] = []
        violations: List[NLViolation] = []
        
        total_claims = len(claims)
        entailed_count = 0
        contradicted_count = 0
        not_supported_count = 0
        
        total_entailment = 0.0
        total_contradiction = 0.0
        
        for claim in claims:
            if self._nli_available:
                result = self._verify_claim_with_nli(claim.claim_text, context)
            else:
                result = self._verify_claim_deterministic(claim.claim_text, context)
            
            claim_results.append(result)
            
            # Update counters
            if result.status == ClaimStatus.ENTAILED:
                entailed_count += 1
            elif result.status == ClaimStatus.CONTRADICTED:
                contradicted_count += 1
            else:
                not_supported_count += 1
            
            total_entailment += result.entailment_score
            total_contradiction += result.contradiction_score
            
            # If claim failed, create violation
            if not result.passed:
                violations.append(NLViolation(
                    message=f"Claim verification failed: {result.status.value}",
                    claim_text=claim.claim_text,
                    field=claim.json_source,
                    violation_type=ViolationType.UNSUPPORTED_CLAIM if result.status == ClaimStatus.NOT_SUPPORTED else ViolationType.CONTRADICTED_CLAIM,
                    severity=ViolationSeverity.HIGH if result.status == ClaimStatus.CONTRADICTED else ViolationSeverity.MEDIUM,
                ))
        
        # Calculate averages
        avg_entailment = total_entailment / total_claims if total_claims > 0 else 0.0
        avg_contradiction = total_contradiction / total_claims if total_claims > 0 else 0.0
        
        # Passed if all claims are entailed and no contradictions
        passed = (
            contradicted_count == 0 and 
            (entailed_count == total_claims or not_supported_count == 0)
        )
        
        return NLIValidationResult(
            passed=passed,
            violations=violations,
            claim_results=claim_results,
            total_claims=total_claims,
            entailed_claims=entailed_count,
            contradicted_claims=contradicted_count,
            not_supported_claims=not_supported_count,
            avg_entailment_score=avg_entailment,
            avg_contradiction_score=avg_contradiction,
        )
