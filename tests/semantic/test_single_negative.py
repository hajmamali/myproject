"""Single negative test to debug issues."""

import pytest
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VerificationStatus(Enum):
    """Verification lifecycle states."""
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"


class GovernanceViolation(Exception):
    """Raised when governance rules are violated."""
    pass


@dataclass
class SemanticFact:
    """Proof-carrying semantic fact."""
    fact_id: str
    source_text_span: Optional[str]
    source_sha256: Optional[str]
    source_article_id: str
    status: VerificationStatus
    verification_method: str
    verification_date: datetime
    extracted_by: str
    extraction_version: str
    ingestion_run: str


def materialize_semantic_fact(fact: SemanticFact):
    """Mock: Materialize semantic fact to graph."""
    if not fact.source_text_span:
        raise GovernanceViolation("Missing source text span")
    if not fact.source_sha256:
        raise GovernanceViolation("Missing SHA-256 proof")
    if not fact.source_article_id:
        raise GovernanceViolation("Missing source article")
    
    # Success
    return True


class TestSingleNegative:
    """Single negative test for debugging."""
    
    def test_concept_without_text_span_rejected(self):
        """
        NEGATIVE TEST: Cannot create concept without source_text_span.
        """
        concept = SemanticFact(
            fact_id="test_001",
            source_text_span=None,  # ← MISSING!
            source_sha256="abc123",
            source_article_id="article_10",
            status=VerificationStatus.CANDIDATE,
            verification_method="test",
            verification_date=datetime.now(),
            extracted_by="test",
            extraction_version="1.0.0",
            ingestion_run="test_run"
        )
        
        # This should raise GovernanceViolation
        with pytest.raises(GovernanceViolation, match="Missing source text span"):
            materialize_semantic_fact(concept)
    
    def test_concept_with_valid_data_accepted(self):
        """
        POSITIVE TEST: Valid concept should be accepted.
        """
        concept = SemanticFact(
            fact_id="test_002",
            source_text_span="مالکیت",  # ← Present
            source_sha256="abc123",     # ← Present
            source_article_id="article_10",  # ← Present
            status=VerificationStatus.VERIFIED,
            verification_method="test",
            verification_date=datetime.now(),
            extracted_by="test",
            extraction_version="1.0.0",
            ingestion_run="test_run"
        )
        
        # This should succeed
        result = materialize_semantic_fact(concept)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])