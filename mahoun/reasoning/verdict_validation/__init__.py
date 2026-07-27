"""
MAHOUN Verdict Validation Pipeline
====================================

Classification: MISSION-CRITICAL / VALIDATION PIPELINE / PRODUCTION
Purpose: Guarantee that generated legal text never deviates from Canonical Verdict JSON.

This pipeline enforces:
- Step A: Schema Validation (required fields, version, completeness)
- Step B: Deterministic Consistency Validation (text vs JSON comparison)
- Step C: Atomic Claim Extraction (split text into traceable claims)
- Step D: Semantic Verification (NLI-based entailment checking)

The Canonical Verdict JSON is the ONLY source of truth.
LLM-generated prose is NEVER authoritative.

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from mahoun.reasoning.verdict_validation.pipeline import (
    VerdictValidationPipeline,
    ValidationResult,
    IntegrityViolation,
)
from mahoun.reasoning.verdict_validation.schema_validator import (
    SchemaValidator,
    SchemaValidationResult,
)
from mahoun.reasoning.verdict_validation.deterministic_validator import (
    DeterministicValidator,
    DeterministicValidationResult,
)
from mahoun.reasoning.verdict_validation.claim_extractor import (
    ClaimExtractor,
    AtomicClaim,
    ClaimExtractionResult,
)
from mahoun.reasoning.verdict_validation.nli_validator import (
    NLIValidator,
    NLIValidationResult,
)

__all__ = [
    # Pipeline
    "VerdictValidationPipeline",
    "ValidationResult",
    "IntegrityViolation",
    # Step A: Schema
    "SchemaValidator",
    "SchemaValidationResult",
    # Step B: Deterministic
    "DeterministicValidator",
    "DeterministicValidationResult",
    # Step C: Claims
    "ClaimExtractor",
    "AtomicClaim",
    "ClaimExtractionResult",
    # Step D: NLI
    "NLIValidator",
    "NLIValidationResult",
]
