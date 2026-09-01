"""
Demo of Phase 2A Contract Tests.

Shows key negative tests working.
"""

import pytest
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from unittest.mock import Mock


class VerificationStatus(Enum):
    """Verification lifecycle states."""
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    MATERIALIZED = "MATERIALIZED"


class GovernanceViolation(Exception):
    """Raised when governance rules are violated."""
    pass


class IntegrityError(Exception):
    """Raised when data integrity constraints are violated."""
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


@dataclass
class SemanticIdentity:
    """Canonical identity for semantic entities."""
    canonical_id: str
    canonical_label_fa: str
    jurisdiction: str
    domain: str
    ontology_version: str


def materialize_semantic_fact(fact: SemanticFact):
    """Mock: Materialize semantic fact to graph."""
    if not fact.source_text_span:
        raise GovernanceViolation("Missing source text span")
    if not fact.source_sha256:
        raise GovernanceViolation("Missing SHA-256 proof")
    if not fact.source_article_id:
        raise GovernanceViolation("Missing source article")
    return True


def materialize_entity_mock(entity: SemanticIdentity):
    """Mock: Materialize entity with duplicate checking."""
    # Simulate duplicate check
    if hasattr(materialize_entity_mock, 'entities'):
        for e in materialize_entity_mock.entities:
            if (e.canonical_id == entity.canonical_id and
                e.jurisdiction == entity.jurisdiction and
                e.ontology_version == entity.ontology_version):
                raise IntegrityError("duplicate_canonical_id")
        materialize_entity_mock.entities.append(entity)
    else:
        materialize_entity_mock.entities = [entity]
    return True


def can_create_semantic_edge(source, target, edge_type: str) -> tuple[bool, str]:
    """Mock: Check if semantic edge can be created."""
    if source.status not in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]:
        return False, "source_not_verified"
    if target.status not in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]:
        return False, "target_not_verified"
    return True, "verified"


def query_reasoning_graph_mock(assertions):
    """Mock: Query reasoning graph (verified only)."""
    return [a for a in assertions if a.status == VerificationStatus.VERIFIED]


class TestPhase2AContractDemo:
    """
    Demo of Phase 2A contract enforcement.
    
    Shows key tests from the full suite.
    """
    
    # ========================================================================
    # Category 1: Missing Evidence (PRIORITY 1)
    # ========================================================================
    
    def test_missing_evidence_rejected(self):
        """
        🔴 NEGATIVE: Facts without evidence → REJECTED
        
        This is the CORE zero-hallucination test.
        """
        # Missing text span
        concept_no_span = SemanticFact(
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
        
        with pytest.raises(GovernanceViolation, match="Missing source text span"):
            materialize_semantic_fact(concept_no_span)
        
        # Missing SHA-256
        concept_no_hash = SemanticFact(
            fact_id="test_002",
            source_text_span="مالکیت",
            source_sha256=None,  # ← MISSING!
            source_article_id="article_10",
            status=VerificationStatus.CANDIDATE,
            verification_method="test",
            verification_date=datetime.now(),
            extracted_by="test",
            extraction_version="1.0.0",
            ingestion_run="test_run"
        )
        
        with pytest.raises(GovernanceViolation, match="Missing SHA-256 proof"):
            materialize_semantic_fact(concept_no_hash)
    
    # ========================================================================
    # Category 2: Unverified Endpoints (PRIORITY 1)
    # ========================================================================
    
    def test_unverified_endpoints_rejected(self):
        """
        🔴 NEGATIVE: Edges from/to unverified nodes → REJECTED
        
        This enforces fail-closed principle.
        """
        candidate_node = Mock(status=VerificationStatus.CANDIDATE)
        verified_node = Mock(status=VerificationStatus.VERIFIED)
        unresolved_node = Mock(status=VerificationStatus.UNRESOLVED)
        
        # CANDIDATE → VERIFIED: Should fail
        result, reason = can_create_semantic_edge(candidate_node, verified_node, "REGULATES")
        assert result is False
        assert reason == "source_not_verified"
        
        # VERIFIED → UNRESOLVED: Should fail
        result, reason = can_create_semantic_edge(verified_node, unresolved_node, "REGULATES")
        assert result is False
        assert reason == "target_not_verified"
        
        # VERIFIED → VERIFIED: Should succeed
        result, reason = can_create_semantic_edge(verified_node, verified_node, "REGULATES")
        assert result is True
        assert reason == "verified"
    
    def test_reasoning_excludes_unverified(self):
        """
        🔴 NEGATIVE: Reasoning engine excludes unverified facts
        
        This is the zero-hallucination guarantee.
        """
        verified_assertion = Mock(
            assertion_id="verified",
            status=VerificationStatus.VERIFIED
        )
        candidate_assertion = Mock(
            assertion_id="candidate",
            status=VerificationStatus.CANDIDATE
        )
        
        # Query reasoning graph
        results = query_reasoning_graph_mock([verified_assertion, candidate_assertion])
        
        # Only verified should appear
        assert len(results) == 1
        assert results[0].assertion_id == "verified"
    
    # ========================================================================
    # Category 3: Duplicate Identity (PRIORITY 1)
    # ========================================================================
    
    def test_duplicate_identity_rejected(self):
        """
        🔴 NEGATIVE: Duplicate canonical_id → REJECTED
        
        Prevents same problem as duplicate components in codebase.
        """
        # Clear previous entities
        if hasattr(materialize_entity_mock, 'entities'):
            materialize_entity_mock.entities = []
        
        # First entity
        entity1 = SemanticIdentity(
            canonical_id="concept_ownership",
            canonical_label_fa="مالکیت",
            jurisdiction="IR",
            domain="property_law",
            ontology_version="1.0"
        )
        
        # Should succeed
        result = materialize_entity_mock(entity1)
        assert result is True
        
        # Try to create duplicate
        entity2 = SemanticIdentity(
            canonical_id="concept_ownership",  # ← DUPLICATE!
            canonical_label_fa="حق مالکیت",
            jurisdiction="IR",
            domain="property_law",
            ontology_version="1.0"
        )
        
        # Should fail
        with pytest.raises(IntegrityError, match="duplicate_canonical_id"):
            materialize_entity_mock(entity2)
    
    # ========================================================================
    # Category 4: Valid Cases (PRIORITY 2)
    # ========================================================================
    
    def test_valid_fact_accepted(self):
        """
        🟢 POSITIVE: Valid fact with complete evidence → ACCEPTED
        
        This verifies the happy path works.
        """
        valid_concept = SemanticFact(
            fact_id="valid_001",
            source_text_span="مالکیت",      # ← Present
            source_sha256="abc123",         # ← Present
            source_article_id="article_10", # ← Present
            status=VerificationStatus.VERIFIED,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        # Should succeed
        result = materialize_semantic_fact(valid_concept)
        assert result is True
    
    def test_valid_identity_accepted(self):
        """
        🟢 POSITIVE: Valid identity → ACCEPTED
        
        This verifies entity creation works.
        """
        # Clear previous entities
        if hasattr(materialize_entity_mock, 'entities'):
            materialize_entity_mock.entities = []
        
        valid_entity = SemanticIdentity(
            canonical_id="concept_freedom_of_contract",
            canonical_label_fa="آزادی قراردادها",
            jurisdiction="IR",
            domain="contract_law",
            ontology_version="1.0"
        )
        
        result = materialize_entity_mock(valid_entity)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])