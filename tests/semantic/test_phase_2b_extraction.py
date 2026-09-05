"""
MAHOUN Phase 2B Test Suite
==========================
Classification: TEST / SEMANTIC EXTRACTION & TAXONOMY SUITE
Purpose: Test the Phase 2B Semantic Extractor, Materializer, Proof-Carrying Facts,
         and Canonical Legal Ontology for strict determinism, validity, and robustness.
"""

import pytest
import hashlib

from mahoun.core.models.semantic import (
    ArticleDecomposition,
    ConditionClause,
    ExceptionClause,
    SanctionClause,
    SemanticAssertion,
    SemanticFact,
    VerificationStatus,
)
from mahoun.graph.ontology.legal_concepts import (
    CANONICAL_LEGAL_CONCEPTS,
    get_concept,
    list_concepts_by_domain,
)
from mahoun.graph.extraction.semantic_extractor import SemanticExtractor
from mahoun.graph.extraction.semantic_materializer import SemanticMaterializer


# ============================================================================
# 1. CANONICAL ONTOLOGY TAXONOMY TESTS
# ============================================================================

def test_canonical_ontology_non_empty():
    """Verify the canonical ontology has concepts across all target legal domains."""
    assert len(CANONICAL_LEGAL_CONCEPTS) >= 12
    domains = {c.domain for c in CANONICAL_LEGAL_CONCEPTS.values()}
    assert "contract_law" in domains
    assert "commercial_law" in domains
    assert "construction_law" in domains
    assert "tort_law" in domains or "civil_procedure" in domains


def test_canonical_ontology_concept_integrity():
    """Verify every concept has valid ID, labels, and parent references."""
    for cid, concept in CANONICAL_LEGAL_CONCEPTS.items():
        assert concept.canonical_id == cid
        assert concept.canonical_label_fa != ""
        assert concept.canonical_label_en != ""
        assert concept.normalized_label != ""
        assert concept.jurisdiction == "IR"
        assert concept.semantic_schema_version == "2B.1.0"

        if concept.parent_concept_id:
            assert concept.parent_concept_id in CANONICAL_LEGAL_CONCEPTS, (
                f"Parent concept '{concept.parent_concept_id}' of '{cid}' not found in ontology."
            )


def test_ontology_query_helpers():
    """Verify get_concept and list_concepts_by_domain helpers."""
    concept = get_concept("concept:freedom_of_contract")
    assert concept is not None
    assert "ماده ۱۰" in concept.description_fa

    construction_concepts = list_concepts_by_domain("construction_law")
    assert len(construction_concepts) >= 4
    c_ids = [c.canonical_id for c in construction_concepts]
    assert "concept:contract_permissible_delay" in c_ids
    assert "concept:contract_suspension" in c_ids


# ============================================================================
# 2. PROOF-CARRYING SEMANTIC MODELS TESTS
# ============================================================================

def test_semantic_fact_verification_pass():
    """Verify a SemanticFact verifies True when text and hash match perfectly."""
    text = "قراردادهای خصوصی در صورتی که مخالف صریح قانون نباشد، نافذ است."
    start = text.find("نافذ است")
    end = start + len("نافذ است")
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    fact = SemanticFact(
        fact_id="fact:1",
        fact_type="sub_clause",
        node_label="Sanction",
        edge_type="HAS_SANCTION",
        source_article_id="art:10",
        source_text_span="نافذ است",
        source_offset_start=start,
        source_offset_end=end,
        source_sha256=h,
        status=VerificationStatus.VERIFIED,
    )
    assert fact.verify(text) is True


def test_semantic_fact_verification_tamper_fails():
    """Verify a SemanticFact verifies False when text is tampered or offsets mismatch."""
    text = "قراردادهای خصوصی در صورتی که مخالف صریح قانون نباشد، نافذ است."
    start = text.find("نافذ است")
    end = start + len("نافذ است")
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    # Tampered span
    fact = SemanticFact(
        fact_id="fact:1",
        fact_type="sub_clause",
        node_label="Sanction",
        edge_type="HAS_SANCTION",
        source_article_id="art:10",
        source_text_span="باطل است",  # tampered
        source_offset_start=start,
        source_offset_end=end,
        source_sha256=h,
    )
    assert fact.verify(text) is False

    # Tampered offset
    fact_offset = SemanticFact(
        fact_id="fact:2",
        fact_type="sub_clause",
        node_label="Sanction",
        edge_type="HAS_SANCTION",
        source_article_id="art:10",
        source_text_span="نافذ است",
        source_offset_start=0,  # tampered
        source_offset_end=len("نافذ است"),
        source_sha256=h,
    )
    assert fact_offset.verify(text) is False

    # Tampered text hash
    fact_hash = SemanticFact(
        fact_id="fact:3",
        fact_type="sub_clause",
        node_label="Sanction",
        edge_type="HAS_SANCTION",
        source_article_id="art:10",
        source_text_span="نافذ است",
        source_offset_start=start,
        source_offset_end=end,
        source_sha256="0000000000000000",  # tampered
    )
    assert fact_hash.verify(text) is False


# ============================================================================
# 3. ARTICLE DECOMPOSITION TESTS
# ============================================================================

@pytest.fixture
def extractor():
    return SemanticExtractor()


def test_decompose_civil_code_article_10(extractor):
    """Test Civil Code Article 10 (Freedom of Contract)."""
    text = "قراردادهای خصوصی نسبت به کسانی که آن را منعقد نموده‌اند، در صورتی که مخالف صریح قانون نباشد، نافذ است."
    decomp = extractor.decompose_article("art:civil_10", "law:civil_code", text)

    assert decomp.article_id == "art:civil_10"
    assert decomp.is_conditional is True
    assert len(decomp.conditions) >= 1
    assert "در صورتی که" in decomp.conditions[0].condition_text

    assert len(decomp.sanctions) >= 1
    assert any(s.sanction_type == "VALIDITY" for s in decomp.sanctions)
    assert decomp.has_exceptions is False

    facts = extractor.extract_proof_carrying_facts("art:civil_10", text)
    assert len(facts) >= 2
    for f in facts:
        assert f.verify(text) is True


def test_decompose_civil_code_article_219(extractor):
    """Test Civil Code Article 219 (Binding Force & Exceptions)."""
    text = "عقودی که بر طبق قانون واقع شده باشد بین متعاملین و قائم‌مقام آنها لازم‌الاتباع است مگر اینکه به رضای طرفین اقاله یا به علت قانونی فسخ شود."
    decomp = extractor.decompose_article("art:civil_219", "law:civil_code", text)

    assert decomp.article_id == "art:civil_219"
    assert len(decomp.sanctions) >= 1
    assert any(s.sanction_type == "VALIDITY" for s in decomp.sanctions)

    assert decomp.has_exceptions is True
    assert len(decomp.exceptions) >= 1
    assert "مگر اینکه" in decomp.exceptions[0].exception_text

    facts = extractor.extract_proof_carrying_facts("art:civil_219", text)
    assert len(facts) >= 2
    for f in facts:
        assert f.verify(text) is True


def test_decompose_nashrieh_4311_article_46(extractor):
    """Test Nashrieh 4311 Article 46 (Contract Termination for Default)."""
    text = "کارفرما می‌تواند در صورت بروز هر یک از موارد زیر پیمان را فسخ کند. در صورتی که پیمانکار تأخیر غیرموجه داشته باشد، کارفرما حق دارد تضمین انجام تعهدات را ضبط نماید."
    decomp = extractor.decompose_article("art:4311_46", "law:conditions_of_contract_4311", text)

    assert decomp.is_conditional is True
    assert len(decomp.conditions) >= 1
    assert len(decomp.sanctions) >= 1

    facts = extractor.extract_proof_carrying_facts("art:4311_46", text)
    assert len(facts) >= 2
    for f in facts:
        assert f.verify(text) is True


def test_decompose_engineering_law_article_34(extractor):
    """Test Engineering System Law Article 34 (Mandatory Supervision & Enforcement)."""
    text = "شهرداری‌ها و مراجع صدور پروانه ساختمان موظفند مقررات ملی ساختمان را رعایت نمایند و مهندسان ناظر مکلفند بر عملیات اجرایی نظارت مستمر داشته باشند."
    decomp = extractor.decompose_article("art:eng_34", "law:engineering_system", text)

    assert len(decomp.sanctions) >= 1
    assert any(s.sanction_type == "OBLIGATION" for s in decomp.sanctions)

    facts = extractor.extract_proof_carrying_facts("art:eng_34", text)
    assert len(facts) >= 1
    for f in facts:
        assert f.verify(text) is True


# ============================================================================
# 4. CONCEPT ASSERTION & TAXONOMIC LINKING TESTS
# ============================================================================

def test_concept_assertion_extraction(extractor):
    """Test matching and assertion generation for canonical concepts."""
    text = "اصل آزادی قراردادها و شرایط اساسی صحت معامله در کلیه عقود لازم‌الاتباع است و در صورت بروز حوادث قوه قاهره تعلیق پیمان اعمال می‌گردد."
    assertions = extractor.extract_concept_assertions("art:sample_1", text)

    assert len(assertions) >= 3
    target_ids = [a.target_entity_id for a in assertions]
    assert "concept:freedom_of_contract" in target_ids
    assert "concept:validity_of_contracts" in target_ids
    assert "concept:force_majeure" in target_ids

    for a in assertions:
        assert a.assertion_type == "REGULATES"
        assert a.status == VerificationStatus.VERIFIED
        # Verify text span
        assert text[a.evidence_offset_start:a.evidence_offset_end] == a.evidence_text_span


# ============================================================================
# 5. CYPHERS GENERATION & MATERIALIZER TESTS
# ============================================================================

def test_materializer_cypher_generation(extractor):
    """Test Cypher generation for ontology, decomposition, and assertions."""
    materializer = SemanticMaterializer(extractor=extractor)

    # 1. Ontology Cyphers
    onto_statements = materializer.generate_ontology_cypher()
    assert len(onto_statements) >= len(CANONICAL_LEGAL_CONCEPTS)
    for cypher, params in onto_statements:
        assert "MERGE (c:Concept" in cypher or "MERGE (child)-[:INHERITS_FROM]->(parent)" in cypher
        assert "id" in params or "child_id" in params

    # 2. Decomposition Cyphers
    text = "در صورتی که متعهد تخلف کند، مسئول جبران خسارت است مگر اینکه عذر موجه داشته باشد."
    decomp = extractor.decompose_article("art:test_decomp", "law:civil_code", text)
    decomp_statements = materializer.generate_decomposition_cypher(decomp)
    assert len(decomp_statements) == len(decomp.conditions) + len(decomp.sanctions) + len(decomp.exceptions)

    for cypher, params in decomp_statements:
        assert params["art_id"] == "art:test_decomp"
        assert "MERGE" in cypher


# ============================================================================
# 6. NEGATIVE & EDGE CASE TESTS
# ============================================================================

def test_extractor_empty_text(extractor):
    """Verify empty text returns empty decomposition without crashing."""
    decomp = extractor.decompose_article("art:empty", "law:test", "")
    assert decomp.article_id == "art:empty"
    assert len(decomp.conditions) == 0
    assert len(decomp.sanctions) == 0
    assert len(decomp.exceptions) == 0

    facts = extractor.extract_proof_carrying_facts("art:empty", "")
    assert facts == []

    assertions = extractor.extract_concept_assertions("art:empty", "")
    assert assertions == []


def test_extractor_no_clauses(extractor):
    """Verify plain text without triggers returns 0 clauses gracefully."""
    text = "این یک متن ساده بدون هیچ شرط یا ضمانت اجرا است."
    decomp = extractor.decompose_article("art:plain", "law:test", text)
    assert len(decomp.conditions) == 0
    assert len(decomp.sanctions) == 0
    assert len(decomp.exceptions) == 0
    assert decomp.is_conditional is False
    assert decomp.has_exceptions is False
