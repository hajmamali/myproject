"""
Claim Extractor - Step C
========================

Classification: MISSION-CRITICAL / VALIDATION STEP C
Purpose: Split generated prose text into atomic legal claims with traceability.

This is Step C of the 4-step validation pipeline.
Must execute AFTER Step B (Deterministic Validation).
Must execute BEFORE Step D (NLI Verification).

CRITICAL INVARIANTS:
- Every claim MUST reference the originating JSON field
- Every claim must be traceable back to Canonical Verdict JSON
- Claims must be atomic (single factual assertion)

Author: MAHOUN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple

from mahoun.core.logging import setup_logger

log = setup_logger("claim_extractor")


@dataclass(frozen=True)
class AtomicClaim:
    """
    Immutable record of a single atomic legal claim.
    
    An atomic claim is:
    - A single factual assertion
    - Extractable from the prose text
    - Traceable to Canonical Verdict JSON
    
    Attributes:
        claim_text: The actual text of the claim
        claim_type: Type of claim (e.g., "ownership", "liability", "validity")
        json_source: Reference to where this claim originates in JSON
        confidence: Confidence that this is a valid atomic claim (0-1)
        position: Character position in the source text
    """
    claim_text: str
    claim_type: str
    json_source: str  # Field path in Canonical JSON, e.g., "steps[0].statement"
    confidence: float = 1.0
    position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "json_source": self.json_source,
            "confidence": self.confidence,
            "position": self.position,
        }


@dataclass
class ClaimExtractionResult:
    """Result of claim extraction"""
    passed: bool
    claims: List[AtomicClaim] = field(default_factory=list)
    extraction_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "passed": self.passed,
            "claims": [c.to_dict() for c in self.claims],
            "num_claims": len(self.claims),
            "extraction_timestamp": self.extraction_timestamp,
        }


class ClaimExtractor:
    """
    Extract atomic legal claims from prose text.
    
    This extractor identifies atomic claims by:
    1. Splitting text at claim boundaries (periods, sentence boundaries)
    2. Classifying each claim by type
    3. Tracing each claim to its source in Canonical Verdict JSON
    
    CRITICAL: Every claim must be traceable to the JSON.
    If a claim cannot be traced, it must be flagged.
    
    Usage:
        extractor = ClaimExtractor()
        result = extractor.extract(prose_text=text, canonical_json=json_data)
        
        for claim in result.claims:
            print(f"Claim: {claim.claim_text}")
            print(f"  Source: {claim.json_source}")
            print(f"  Type: {claim.claim_type}")
    """
    
    def __init__(self):
        """Initialize claim extractor"""
        # Patterns for identifying claim boundaries
        self._claim_boundary_pattern = re.compile(
            r'(?:\.|!|؟|\n\n| based on| according to| therefore| thus| hence)',
            re.IGNORECASE
        )
        
        # Patterns for identifying claim types (Persian legal terms)
        self._claim_type_patterns = {
            "ownership": re.compile(
                r'(مالکیت|صاحب|مالک|تملک|دارایی)',
                re.IGNORECASE
            ),
            "validity": re.compile(
                r'(معتبر|نامعتبر|صحیح|باطل|ناovali)',
                re.IGNORECASE
            ),
            "liability": re.compile(
                r'(مسئولیت|متهم|مجرم|جرم|تقصیر)',
                re.IGNORECASE
            ),
            "obligation": re.compile(
                r'(تعهد|مکلف|موظف|باید|می‌بایست|ضروری)',
                re.IGNORECASE
            ),
            "right": re.compile(
                r'(حق|حقوق|اختیار|مجوز)',
                re.IGNORECASE
            ),
            "contradiction": re.compile(
                r'(تناقض|مغایرت|اختلاف|برخورد)',
                re.IGNORECASE
            ),
            "evidence": re.compile(
                r'(شاهد|مدرک|دلیل|سند|گواهی)',
                re.IGNORECASE
            ),
            "article": re.compile(
                r'(ماده|بند|تبصره|قانون)',
                re.IGNORECASE
            ),
        }
        
        log.info("ClaimExtractor initialized")
    
    def _classify_claim(self, claim_text: str) -> str:
        """
        Classify a claim by type based on its content.
        
        Args:
            claim_text: The text of the claim
            
        Returns:
            Claim type string
        """
        for claim_type, pattern in self._claim_type_patterns.items():
            if pattern.search(claim_text):
                return claim_type
        return "general"
    
    def _find_json_source(
        self,
        claim_text: str,
        canonical_json: Dict[str, Any]
    ) -> str:
        """
        Find the source of a claim in the Canonical Verdict JSON.
        
        This method searches for the claim text (or parts of it) in the JSON
        and returns a reference to where it was found.
        
        Args:
            claim_text: The text of the claim
            canonical_json: The Canonical Verdict JSON
            
        Returns:
            String reference to JSON source, e.g., "steps[0].statement"
        """
        # Normalize the claim text for comparison
        normalized_claim = claim_text.strip().lower()
        
        # Search in final_verdict
        if "final_verdict" in canonical_json:
            final_verdict = str(canonical_json["final_verdict"]).lower()
            if normalized_claim in final_verdict:
                return "final_verdict"
        
        # Search in steps
        if "steps" in canonical_json:
            for i, step in enumerate(canonical_json["steps"]):
                if isinstance(step, dict):
                    statement = step.get("statement", "").lower()
                    if normalized_claim in statement:
                        return f"steps[{i}].statement"
        
        # Search in rule_nodes
        if "rule_nodes" in canonical_json:
            for node_id, node in canonical_json["rule_nodes"].items():
                if isinstance(node, dict):
                    label = node.get("label", "").lower()
                    node_type = node.get("node_type", "").lower()
                    properties = str(node.get("properties", {})).lower()
                    
                    if (normalized_claim in label or 
                        normalized_claim in node_type or 
                        normalized_claim in properties):
                        return f"rule_nodes.{node_id}"
        
        # Search in precedent_nodes
        if "precedent_nodes" in canonical_json:
            for node_id, node in canonical_json["precedent_nodes"].items():
                if isinstance(node, dict):
                    label = node.get("label", "").lower()
                    node_type = node.get("node_type", "").lower()
                    properties = str(node.get("properties", {})).lower()
                    
                    if (normalized_claim in label or 
                        normalized_claim in node_type or 
                        normalized_claim in properties):
                        return f"precedent_nodes.{node_id}"
        
        # If not found, return "unknown"
        log.warning(f"Could not find JSON source for claim: {claim_text[:50]}...")
        return "unknown"
    
    def _split_into_claims(self, text: str) -> List[Tuple[str, int]]:
        """
        Split prose text into potential atomic claims.
        
        Args:
            text: The prose text to split
            
        Returns:
            List of (claim_text, position) tuples
        """
        claims: List[Tuple[str, int]] = []
        
        # Split by claim boundaries (sentences)
        # Simple approach: split by periods, exclamation marks, question marks
        sentences = re.split(r'(?<=[.!?؟])\s+', text)
        
        current_position = 0
        for sentence in sentences:
            if sentence.strip():
                claims.append((sentence.strip(), current_position))
                current_position += len(sentence) + 1  # +1 for the delimiter
        
        # If no sentences found, try splitting by double newlines
        if not claims and '\n\n' in text:
            parts = text.split('\n\n')
            current_position = 0
            for part in parts:
                if part.strip():
                    claims.append((part.strip(), current_position))
                    current_position += len(part) + 2
        
        # If still no claims, use the whole text
        if not claims and text.strip():
            claims.append((text.strip(), 0))
        
        return claims
    
    def extract(
        self,
        prose_text: str,
        canonical_json: Dict[str, Any],
    ) -> ClaimExtractionResult:
        """
        Extract atomic claims from prose text.
        
        Args:
            prose_text: The prose text to extract claims from
            canonical_json: The Canonical Verdict JSON for traceability
            
        Returns:
            ClaimExtractionResult with extracted claims
        """
        claims: List[AtomicClaim] = []
        
        # Split text into potential claims
        raw_claims = self._split_into_claims(prose_text)
        
        for claim_text, position in raw_claims:
            # Classify the claim
            claim_type = self._classify_claim(claim_text)
            
            # Find the JSON source
            json_source = self._find_json_source(claim_text, canonical_json)
            
            # Create atomic claim
            claim = AtomicClaim(
                claim_text=claim_text,
                claim_type=claim_type,
                json_source=json_source,
                confidence=1.0 if json_source != "unknown" else 0.5,
                position=position,
            )
            claims.append(claim)
        
        # Result is always "passed" for extraction
        # The actual validation happens in NLI step
        return ClaimExtractionResult(
            passed=True,
            claims=claims,
        )
