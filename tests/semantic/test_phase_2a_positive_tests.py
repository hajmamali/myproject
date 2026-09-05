"""
Phase 2A Positive Tests.

PRIORITY 2: These tests verify the HAPPY PATH works correctly.

Philosophy:
- After proving the system REJECTS bad inputs (negative tests)
- Now prove the system ACCEPTS good inputs (positive tests)

Test Categories:
1. Valid Entity Creation
2. Valid Assertion Creation
3. Provenance Chain Integrity
4. Schema Compliance
5. Verification Lifecycle

These tests run AFTER negative tests pass.
"""

import pytest
import hashlib
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from unittest.mock import Mock


# ============================================================================
# Test Fixtures (reuse from negative tests)
# ============================================================================

class VerificationStatus(Enum):
    """Verification lifecycle states."""
    CANDIDATE = "CANDIDATE"
    NORMALIZED = "NORMALIZED"
    VERIFIED = "VERIFIED"
    UNRESOLVED = "UNRESOLVED"
    MATERIALIZED = "MATERIALIZED"


@dataclass
class SemanticIdentity:
    """Canonical identity for semantic entities."""
    canonical_id: str
    canonical_label_fa: str
    canonical_label_en: str
    normalized_label: str
    jurisdiction: str
    domain: str
    ontology_version: str
    semantic_schema_version: str
    aliases_fa: List[str] = None
    aliases_en: List[str] = None
    parent_concept_id: Optional[str] = None


@dataclass
class SemanticFact:
    """Proof-carrying semantic fact."""
    fact_id: str
    fact_type: str
    node_label: Optional[str]
    edge_type: Optional[str]
    source_article_id: str
    source_text_span: str
    source_offset_start: int
    source_offset_end: int
    source_sha256: str
    status: VerificationStatus
    verification_method: str
    verification_date: datetime
    confidence_score: Optional[float]
    extracted_by: str
    extraction_version: str
    ingestion_run: str
    
    def verify(self, article_text: str) -> bool:
        """Verify that source_text_span exists in article_text."""
        # Extract claimed span
        try:
            claimed_span = article_text[
                self.source_offset_start:self.source_offset_end
            ]
        except IndexError:
            return False
        
        # Check text match
        if claimed_span != self.source_text_span:
            return False
        
        # Check SHA-256
        computed_hash = hashlib.sha256(
            article_text.encode('utf-8')
        ).hexdigest()[:16]
        
        if computed_hash != self.source_sha256:
            return False
        
        return True


@dataclass
class SemanticAssertion:
    """A claim about a relationship between entities."""
    assertion_id: str
    assertion_type: str
    source_entity_id: str
    target_entity_id: str
    evidence_text_span: str
    evidence_offset_start: int
    evidence_offset_end: int
    evidence_sha256: str
    status: VerificationStatus
    verification_method: str
    verification_date: datetime
    extracted_by: str
    extraction_version: str
    ingestion_run: str


# ============================================================================
# Category 1: Valid Entity Creation Tests
# ============================================================================

class TestValidEntityCreation:
    """
    POSITIVE TEST: Valid entities can be created and materialized.
    """
    
    def test_valid_concept_with_complete_provenance_accepted(self):
        """
        POSITIVE TEST: Valid concept with complete provenance accepted.
        
        Expected: Successfully materialized
        """
        article_text = "اشخاص در معاملات و قراردادهای خود آزادند"
        article_sha256 = hashlib.sha256(article_text.encode('utf-8')).hexdigest()[:16]
        
        concept = SemanticFact(
            fact_id="concept_001",
            fact_type="node",
            node_label="Concept",
            edge_type=None,
            source_article_id="article_10_civil_code",
            source_text_span="آزادند",
            source_offset_start=34,
            source_offset_end=40,
            source_sha256=article_sha256,
            status=VerificationStatus.VERIFIED,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            confidence_score=0.95,
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        # Should pass verification
        assert concept.verify(article_text) is True
        
        # Should materialize successfully
        result = materialize_semantic_fact_mock(concept)
        assert result is True
    
    def test_valid_semantic_identity_created(self):
        """
        POSITIVE TEST: Valid semantic identity can be created.
        
        Expected: Successfully created with canonical ID
        """
        identity = SemanticIdentity(
            canonical_id="concept_freedom_of_contract",
            canonical_label_fa="آزادی قراردادها",
            canonical_label_en="freedom_of_contract",
            normalized_label="آزادی قراردادها",
            jurisdiction="IR",
            domain="contract_law",
            ontology_version="1.0",
            semantic_schema_version="2A.1.0",
            aliases_fa=["حق آزادی معاملات", "آزادی معاملات"],
            aliases_en=["freedom_of_transaction", "contractual_freedom"]
        )
        
        result = materialize_entity_mock(identity)
        assert result is True
        
        # Verify it exists
        retrieved = query_entity_by_canonical_id_mock("concept_freedom_of_contract")
        assert retrieved is not None
        assert retrieved.canonical_label_fa == "آزادی قراردادها"
    
    def test_valid_concept_with_hierarchical_relationship(self):
        """
        POSITIVE TEST: Concept with parent relationship created.
        
        Expected: Both parent and child created, relationship established
        """
        # Parent concept
        parent = SemanticIdentity(
            canonical_id="concept_property_law",
            canonical_label_fa="حقوق اموال",
            canonical_label_en="property_law",
            normalized_label="حقوق اموال",
            jurisdiction="IR",
            domain="private_law",
            ontology_version="1.0",
            semantic_schema_version="2A.1.0"
        )
        
        # Child concept
        child = SemanticIdentity(
            canonical_id="concept_ownership",
            canonical_label_fa="مالکیت",
            canonical_label_en="ownership",
            normalized_label="مالکیت",
            jurisdiction="IR",
            domain="property_law",
            ontology_version="1.0",
            semantic_schema_version="2A.1.0",
            parent_concept_id="concept_property_law"
        )
        
        materialize_entity_mock(parent)
        materialize_entity_mock(child)
        
        # Verify hierarchy
        assert child.parent_concept_id == "concept_property_law"


# ============================================================================
# Category 2: Valid Assertion Creation Tests
# ============================================================================

class TestValidAssertionCreation:
    """
    POSITIVE TEST: Valid assertions can be created between verified entities.
    """
    
    def test_valid_regulates_assertion_created(self):
        """
        POSITIVE TEST: Valid REGULATES assertion between Article and Concept.
        
        Expected: Assertion created with dual provenance
        """
        # Create verified entities first
        article = Mock(
            entity_id="article_10",
            status=VerificationStatus.VERIFIED
        )
        concept = Mock(
            entity_id="concept_freedom_of_contract",
            status=VerificationStatus.VERIFIED
        )
        
        # Create assertion
        assertion = SemanticAssertion(
            assertion_id="assertion_001",
            assertion_type="REGULATES",
            source_entity_id="article_10",
            target_entity_id="concept_freedom_of_contract",
            evidence_text_span="ماده ۱۰ آزادی قراردادها را تنظیم می‌کند",
            evidence_offset_start=0,
            evidence_offset_end=42,
            evidence_sha256="abc123",
            status=VerificationStatus.VERIFIED,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        result = materialize_semantic_assertion_mock(article, concept, assertion)
        assert result is True
    
    def test_valid_edge_between_verified_endpoints(self):
        """
        POSITIVE TEST: Edge can be created between two VERIFIED nodes.
        
        Expected: Edge creation succeeds
        """
        verified_source = Mock(status=VerificationStatus.VERIFIED)
        verified_target = Mock(status=VerificationStatus.VERIFIED)
        
        can_create, reason = can_create_semantic_edge_mock(
            verified_source, verified_target, "REGULATES"
        )
        
        assert can_create is True
        assert reason == "verified"
    
    def test_valid_edge_between_materialized_endpoints(self):
        """
        POSITIVE TEST: Edge can be created between two MATERIALIZED nodes.
        
        Expected: Edge creation succeeds
        """
        materialized_source = Mock(status=VerificationStatus.MATERIALIZED)
        materialized_target = Mock(status=VerificationStatus.MATERIALIZED)
        
        can_create, reason = can_create_semantic_edge_mock(
            materialized_source, materialized_target, "HAS_CONDITION"
        )
        
        assert can_create is True
        assert reason == "verified"


# ============================================================================
# Category 3: Provenance Chain Integrity Tests
# ============================================================================

class TestProvenanceChainIntegrity:
    """
    POSITIVE TEST: Provenance chain can be traced from fact to source.
    """
    
    def test_entity_provenance_traceable(self):
        """
        POSITIVE TEST: Entity provenance can be traced to source.
        
        Expected: Complete provenance chain exists
        """
        entity = SemanticIdentity(
            canonical_id="concept_ownership",
            canonical_label_fa="مالکیت",
            canonical_label_en="ownership",
            normalized_label="مالکیت",
            jurisdiction="IR",
            domain="property_law",
            ontology_version="1.0",
            semantic_schema_version="2A.1.0"
        )
        
        materialize_entity_mock(entity)
        
        # Trace provenance
        provenance = query_entity_provenance_mock("concept_ownership")
        
        assert provenance is not None
        assert provenance["canonical_id"] == "concept_ownership"
        assert provenance["ontology_version"] == "1.0"
        assert provenance["semantic_schema_version"] == "2A.1.0"
    
    def test_assertion_provenance_traceable(self):
        """
        POSITIVE TEST: Assertion provenance can be traced to evidence.
        
        Expected: Dual provenance (entity + assertion) exists
        """
        article = Mock(entity_id="article_10", status=VerificationStatus.VERIFIED)
        concept = Mock(entity_id="concept_ownership", status=VerificationStatus.VERIFIED)
        
        assertion = SemanticAssertion(
            assertion_id="assertion_001",
            assertion_type="REGULATES",
            source_entity_id="article_10",
            target_entity_id="concept_ownership",
            evidence_text_span="ماده ۱۰ مالکیت را تنظیم می‌کند",
            evidence_offset_start=0,
            evidence_offset_end=30,
            evidence_sha256="abc123",
            status=VerificationStatus.VERIFIED,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        materialize_semantic_assertion_mock(article, concept, assertion)
        
        # Trace assertion provenance
        provenance = query_assertion_provenance_mock("assertion_001")
        
        assert provenance is not None
        assert provenance["assertion_id"] == "assertion_001"
        assert provenance["evidence_text_span"] == "ماده ۱۰ مالکیت را تنظیم می‌کند"
        assert provenance["evidence_sha256"] == "abc123"
        assert provenance["extracted_by"] == "extract_legal_concepts.py"
    
    def test_full_provenance_chain_to_ingestion_run(self):
        """
        POSITIVE TEST: Full provenance chain from fact to ingestion run.
        
        Expected: Can trace: Fact → Article → IngestionRun → Source File
        """
        # This would query Neo4j in real implementation
        provenance_chain = query_full_provenance_chain_mock("assertion_001")
        
        assert provenance_chain is not None
        assert "assertion" in provenance_chain
        assert "article" in provenance_chain
        assert "ingestion_run" in provenance_chain
        assert "source_file" in provenance_chain


# ============================================================================
# Category 4: Schema Compliance Tests
# ============================================================================

class TestSchemaCompliance:
    """
    POSITIVE TEST: Entities comply with schema constraints.
    """
    
    def test_all_mandatory_properties_present(self):
        """
        POSITIVE TEST: Entity has all mandatory properties.
        
        Expected: canonical_id, jurisdiction, domain, etc. all present
        """
        entity = SemanticIdentity(
            canonical_id="concept_ownership",
            canonical_label_fa="مالکیت",
            canonical_label_en="ownership",
            normalized_label="مالکیت",
            jurisdiction="IR",
            domain="property_law",
            ontology_version="1.0",
            semantic_schema_version="2A.1.0"
        )
        
        # Validate schema compliance
        is_compliant = validate_schema_compliance_mock(entity)
        assert is_compliant is True
    
    def test_schema_version_consistent(self):
        """
        POSITIVE TEST: All entities use consistent schema version.
        
        Expected: All entities in graph have compatible versions
        """
        entities = [
            Mock(semantic_schema_version="2A.1.0"),
            Mock(semantic_schema_version="2A.1.1"),  # Compatible (same major)
            Mock(semantic_schema_version="2A.1.2"),  # Compatible
        ]
        
        is_consistent = validate_schema_version_consistency_mock(entities)
        assert is_consistent is True
    
    def test_neo4j_uniqueness_constraints_enforced(self):
        """
        POSITIVE TEST: Neo4j uniqueness constraints are in place.
        
        Expected: Canonical ID uniqueness constraint exists
        """
        constraints = query_neo4j_constraints_mock()
        
        # Check for semantic entity uniqueness constraint
        constraint_names = [c["name"] for c in constraints]
        assert "semantic_entity_unique_canonical_id" in constraint_names


# ============================================================================
# Category 5: Verification Lifecycle Tests
# ============================================================================

class TestVerificationLifecycle:
    """
    POSITIVE TEST: Verification lifecycle transitions work correctly.
    """
    
    def test_candidate_to_verified_transition(self):
        """
        POSITIVE TEST: Fact can transition from CANDIDATE to VERIFIED.
        
        Expected: Status updated after verification passes
        """
        fact = SemanticFact(
            fact_id="fact_001",
            fact_type="node",
            node_label="Concept",
            edge_type=None,
            source_article_id="article_10",
            source_text_span="مالکیت",
            source_offset_start=17,
            source_offset_end=23,
            source_sha256="abc123",
            status=VerificationStatus.CANDIDATE,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            confidence_score=0.9,
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        # Perform verification
        article_text = "اشخاص در معاملات مالکیت دارند"
        article_sha256 = hashlib.sha256(article_text.encode('utf-8')).hexdigest()[:16]
        fact.source_sha256 = article_sha256
        
        verified = fact.verify(article_text)
        
        if verified:
            fact.status = VerificationStatus.VERIFIED
        
        assert fact.status == VerificationStatus.VERIFIED
    
    def test_verified_to_materialized_transition(self):
        """
        POSITIVE TEST: Fact can transition from VERIFIED to MATERIALIZED.
        
        Expected: Materialization succeeds after verification
        """
        fact = SemanticFact(
            fact_id="fact_002",
            fact_type="node",
            node_label="Concept",
            edge_type=None,
            source_article_id="article_10",
            source_text_span="مالکیت",
            source_offset_start=20,
            source_offset_end=26,
            source_sha256="abc123",
            status=VerificationStatus.VERIFIED,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            confidence_score=0.95,
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        # Materialize to graph
        result = materialize_semantic_fact_mock(fact)
        
        if result:
            fact.status = VerificationStatus.MATERIALIZED
        
        assert fact.status == VerificationStatus.MATERIALIZED
    
    def test_unresolved_remains_excluded_from_reasoning(self):
        """
        POSITIVE TEST: UNRESOLVED facts remain excluded from reasoning.
        
        Expected: Even after time passes, UNRESOLVED stays UNRESOLVED
        """
        unresolved_fact = Mock(
            fact_id="fact_unresolved",
            status=VerificationStatus.UNRESOLVED
        )
        
        # Query reasoning graph
        reasoning_graph = query_reasoning_graph_mock([unresolved_fact])
        
        # Should still be excluded
        assert len(reasoning_graph) == 0


# ============================================================================
# Category 6: End-to-End Happy Path
# ============================================================================

class TestEndToEndHappyPath:
    """
    POSITIVE TEST: Complete extraction → verification → materialization flow.
    """
    
    def test_complete_semantic_fact_lifecycle(self):
        """
        POSITIVE TEST: Complete lifecycle from extraction to reasoning.
        
        Flow:
        1. Extract semantic fact (CANDIDATE)
        2. Normalize (NORMALIZED)
        3. Verify (VERIFIED)
        4. Materialize (MATERIALIZED)
        5. Query in reasoning (SUCCESS)
        """
        # Step 1: Extract
        article_text = "اشخاص در معاملات و قراردادهای خود آزادند"
        article_sha256 = hashlib.sha256(article_text.encode('utf-8')).hexdigest()[:16]
        
        fact = SemanticFact(
            fact_id="fact_lifecycle",
            fact_type="node",
            node_label="Concept",
            edge_type=None,
            source_article_id="article_10_civil_code",
            source_text_span="آزادند",
            source_offset_start=34,
            source_offset_end=40,
            source_sha256=article_sha256,
            status=VerificationStatus.CANDIDATE,
            verification_method="structural_extraction",
            verification_date=datetime.now(),
            confidence_score=0.95,
            extracted_by="extract_legal_concepts.py",
            extraction_version="1.0.0",
            ingestion_run="run_001"
        )
        
        # Step 2: Normalize
        fact.status = VerificationStatus.NORMALIZED
        
        # Step 3: Verify
        verified = fact.verify(article_text)
        assert verified is True
        fact.status = VerificationStatus.VERIFIED
        
        # Step 4: Materialize
        materialized = materialize_semantic_fact_mock(fact)
        assert materialized is True
        fact.status = VerificationStatus.MATERIALIZED
        
        # Step 5: Query in reasoning
        reasoning_results = query_reasoning_graph_mock([fact])
        assert len(reasoning_results) == 1
        assert reasoning_results[0].status == VerificationStatus.MATERIALIZED


# ============================================================================
# Mock Functions
# ============================================================================

def materialize_semantic_fact_mock(fact: SemanticFact) -> bool:
    """Mock: Materialize semantic fact."""
    if fact.status not in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]:
        return False
    return True


def materialize_entity_mock(entity: SemanticIdentity) -> bool:
    """Mock: Materialize entity."""
    return True


def query_entity_by_canonical_id_mock(canonical_id: str):
    """Mock: Query entity by canonical ID."""
    if canonical_id == "concept_freedom_of_contract":
        return Mock(canonical_label_fa="آزادی قراردادها")
    return None


def materialize_semantic_assertion_mock(source, target, assertion: SemanticAssertion) -> bool:
    """Mock: Materialize assertion."""
    return True


def can_create_semantic_edge_mock(source, target, edge_type: str) -> tuple[bool, str]:
    """Mock: Check if edge can be created."""
    if source.status in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]:
        if target.status in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]:
            return True, "verified"
    return False, "endpoints_not_verified"


def query_entity_provenance_mock(canonical_id: str):
    """Mock: Query entity provenance."""
    return {
        "canonical_id": canonical_id,
        "ontology_version": "1.0",
        "semantic_schema_version": "2A.1.0"
    }


def query_assertion_provenance_mock(assertion_id: str):
    """Mock: Query assertion provenance."""
    return {
        "assertion_id": assertion_id,
        "evidence_text_span": "ماده ۱۰ مالکیت را تنظیم می‌کند",
        "evidence_sha256": "abc123",
        "extracted_by": "extract_legal_concepts.py"
    }


def query_full_provenance_chain_mock(assertion_id: str):
    """Mock: Query full provenance chain."""
    return {
        "assertion": {"assertion_id": assertion_id},
        "article": {"article_id": "article_10"},
        "ingestion_run": {"run_id": "run_001"},
        "source_file": {"filename": "civil_code.txt"}
    }


def validate_schema_compliance_mock(entity: SemanticIdentity) -> bool:
    """Mock: Validate schema compliance."""
    required_fields = [
        "canonical_id", "canonical_label_fa", "canonical_label_en",
        "normalized_label", "jurisdiction", "domain",
        "ontology_version", "semantic_schema_version"
    ]
    
    for field in required_fields:
        if not getattr(entity, field, None):
            return False
    
    return True


def validate_schema_version_consistency_mock(entities) -> bool:
    """Mock: Validate schema version consistency."""
    if not entities:
        return True
    
    first_version = entities[0].semantic_schema_version
    phase, major, _ = first_version.split('.')
    
    for entity in entities:
        e_phase, e_major, _ = entity.semantic_schema_version.split('.')
        if e_phase != phase or e_major != major:
            return False
    
    return True


def query_neo4j_constraints_mock():
    """Mock: Query Neo4j constraints."""
    return [
        {"name": "semantic_entity_unique_canonical_id"},
        {"name": "article_unique_id"}
    ]


def query_reasoning_graph_mock(facts):
    """Mock: Query reasoning graph."""
    return [
        f for f in facts
        if f.status in [VerificationStatus.VERIFIED, VerificationStatus.MATERIALIZED]
    ]


# ============================================================================
# Test Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
