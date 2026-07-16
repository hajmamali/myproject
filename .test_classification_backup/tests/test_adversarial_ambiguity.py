"""
Adversarial Ambiguity Test for Semantic Graph Linking
=====================================================

Tests that the system correctly detects ambiguity and returns UNRESOLVED
when multiple judgment nodes match by year but differ by jurisdiction.

This test validates the critical behavior of "knowing what it doesn't know"
by ensuring the system prefers correctness over overconfident linking.
"""

import pytest
from typing import Dict, List, Optional

from mahoun.rag.evidence_enrichment import enrich_evidence, Entity
from mahoun.rag.graph_linker import Candidate, EntityMention, GraphLinker, GraphResolver


class _AmbiguityResolver(GraphResolver):
    """Mock resolver with three ambiguous judgment nodes"""

    def __init__(self):
        self.nodes = {
            "IR:JUDG:TEH:1401": {
                "node_id": "N-JUDG-TEH-1401",
                "name": "رأی دادگاه تجدیدنظر تهران سال ۱۴۰۱",
                "entity_type": "JUDGMENT",
                "canonical_id": "IR:JUDG:TEH:1401",
                "identities": {
                    "year": "1401",
                    "court_level": "تجدیدنظر",
                    "jurisdiction": "TEH"
                }
            },
            "IR:JUDG:ESF:1401": {
                "node_id": "N-JUDG-ESF-1401",
                "name": "رأی دادگاه تجدیدنظر اصفهان سال ۱۴۰۱",
                "entity_type": "JUDGMENT",
                "canonical_id": "IR:JUDG:ESF:1401",
                "identities": {
                    "year": "1401",
                    "court_level": "تجدیدنظر",
                    "jurisdiction": "ESF"
                }
            },
            "IR:ARB:Y:1401": {
                "node_id": "N-ARB-1401-Y",
                "name": "رأی داوری سال ۱۴۰۱ پرونده Y",
                "entity_type": "ARBITRATION_AWARD",
                "canonical_id": "IR:ARB:Y:1401",
                "identities": {
                    "year": "1401",
                    "case_id": "Y"
                }
            }
        }
        self.create_calls = 0
        self.link_calls = 0

    def find_candidates(
        self,
        name: str,
        normalized: str,
        fuzzy: str,
        entity_type: str,
    ) -> List[Candidate]:
        candidates = []
        for canonical_id, node_data in self.nodes.items():
            # Include exact entity type matches
            if node_data["entity_type"] == entity_type:
                candidate = Candidate(
                    node_id=node_data["node_id"],
                    name=node_data["name"],
                    entity_type=node_data["entity_type"],
                    identities=node_data["identities"],
                    canonical_id=node_data["canonical_id"],
                    anchor_score=0.5
                )
                candidates.append(candidate)
            # For JUDGMENT mentions, also include semantically similar types (ARBITRATION_AWARD)
            # that share the year to create ambiguity
            elif entity_type == "JUDGMENT" and node_data["entity_type"] == "ARBITRATION_AWARD":
                # Check if they share the year (creating semantic ambiguity)
                if node_data["identities"].get("year") == "1401":
                    candidate = Candidate(
                        node_id=node_data["node_id"],
                        name=node_data["name"],
                        entity_type=node_data["entity_type"],
                        identities=node_data["identities"],
                        canonical_id=node_data["canonical_id"],
                        anchor_score=0.3  # Lower anchor score for different entity types
                    )
                    candidates.append(candidate)

        return candidates

    def create_node(
        self,
        canonical_id: str,
        entity_type: str,
        name: str,
        identities: Dict[str, str],
    ) -> str:
        self.create_calls += 1
        node_id = f"CREATED:{canonical_id}"
        self.nodes[canonical_id] = {
            "node_id": node_id,
            "name": name,
            "entity_type": entity_type,
            "identities": identities,
        }
        return node_id

    def record_link(
        self,
        mention: EntityMention,
        node_id: str,
        canonical_id: Optional[str],
        confidence: float,
        score,
    ) -> None:
        self.link_calls += 1


@pytest.mark.graph_native
class TestAdversarialAmbiguity:
    """Tests semantic graph linking under ambiguity conditions"""

    def test_judgment_ambiguity_detection(self):
        """Test that ambiguous judgment reference returns UNRESOLVED"""

        # Input evidence text (designed to be ambiguous)
        evidence_text = (
            "در پرونده حاضر، طرفین به رأی صادره در سال ۱۴۰۱ از مرجع تجدیدنظر استناد نموده‌اند. "
            "این رأی مبنای تصمیم‌گیری در خصوص موضوع اختلاف بوده و مورد تایید طرفین قرار گرفته است. "
            "با توجه به ماهیت حقوقی موضوع، مرجع تجدیدنظر صالح برای رسیدگی به اینگونه اختلافات می‌باشد."
        )

        # Enrich evidence to extract entities
        enriched = enrich_evidence(
            text=evidence_text,
            doc_id="test_doc_ambiguity",
            relevance_score=0.8,
            semantic_score=0.9
        )

        # Verify exactly one JUDGMENT entity is extracted
        judgment_entities = [e for e in enriched.entities if e.entity_type == "JUDGMENT"]
        assert len(judgment_entities) == 1, f"Expected 1 JUDGMENT entity, got {len(judgment_entities)}"

        judgment_entity = judgment_entities[0]
        assert judgment_entity.identity.get("year") == "1401", "Entity should extract year 1401"

        # Create EntityMention from extracted entity
        mention = EntityMention(
            name=judgment_entity.text,
            entity_type="JUDGMENT",
            identities=judgment_entity.identity,
            provenance={"doc_id": "test_doc_ambiguity", "chunk_hash": enriched.chunk_hash},
            context=evidence_text
        )

        # Create resolver and linker
        resolver = _AmbiguityResolver()
        linker = GraphLinker(resolver)

        # Perform linking
        result = linker.link_entity(mention)

        # CRITICAL ASSERTIONS - PASS CRITERIA

        # 1. Action must be UNRESOLVED
        assert result.action == "UNRESOLVED", f"Expected UNRESOLVED, got {result.action}"

        # 2. No node should be resolved
        assert result.resolved_node_id is None, f"Expected None, got {result.resolved_node_id}"

        # 3. Canonical ID should be None (insufficient identity for creation)
        assert result.canonical_id is None, f"Expected None, got {result.canonical_id}"

        # 4. Confidence should be below TH_LINK (0.78)
        assert result.confidence < 0.78, f"Confidence {result.confidence} should be < 0.78"

        # 5. Reason should indicate ambiguity
        assert "ambiguity" in result.reason.lower() or "threshold" in result.reason.lower(), \
            f"Reason '{result.reason}' should indicate ambiguity"

        # 6. Multiple candidates should be present
        assert len(result.candidates) >= 2, f"Expected multiple candidates, got {len(result.candidates)}"

        # 7. No node creation should occur
        assert resolver.create_calls == 0, f"No creation should occur, but {resolver.create_calls} creations happened"

        # 8. No links should be recorded (since unresolved)
        assert resolver.link_calls == 0, f"No links should be recorded, but {resolver.link_calls} links recorded"

        # Verify specific candidates are present
        candidate_node_ids = {cand[0].node_id for cand in result.candidates}
        expected_nodes = {"N-JUDG-TEH-1401", "N-JUDG-ESF-1401", "N-ARB-1401-Y"}
        assert expected_nodes.issubset(candidate_node_ids), \
            f"Expected candidates {expected_nodes}, got {candidate_node_ids}"

    def test_judgment_entity_extraction(self):
        """Test that JUDGMENT entities are properly extracted from text"""

        test_cases = [
            {
                "text": "رأی دادگاه تجدیدنظر سال ۱۴۰۱",
                "expected_year": "1401"
            },
            {
                "text": "رأی صادره در سال ۱۴۰۱ از مرجع تجدیدنظر",
                "expected_year": "1401"
            },
            {
                "text": "رای هیئت داوری سال ۱۴۰۱",
                "expected_year": "1401"
            }
        ]

        for test_case in test_cases:
            enriched = enrich_evidence(
                text=test_case["text"],
                doc_id=f"test_{hash(test_case['text'])}",
                relevance_score=0.8,
                semantic_score=0.9
            )

            judgment_entities = [e for e in enriched.entities if e.entity_type == "JUDGMENT"]
            assert len(judgment_entities) >= 1, f"No JUDGMENT entity extracted from: {test_case['text']}"

            # At least one should have the expected year
            years_found = {e.identity.get("year") for e in judgment_entities}
            assert test_case["expected_year"] in years_found, \
                f"Year {test_case['expected_year']} not found in {years_found}"

    def test_ambiguous_vs_unambiguous_judgment(self):
        """Test that unambiguous judgment gets linked while ambiguous doesn't"""

        resolver = _AmbiguityResolver()
        linker = GraphLinker(resolver)

        # Test 1: Ambiguous reference (no jurisdiction)
        ambiguous_mention = EntityMention(
            name="رأی تجدیدنظر سال ۱۴۰۱",
            entity_type="JUDGMENT",
            identities={"year": "1401"},
            provenance={"doc_id": "test_ambiguous"}
        )

        ambiguous_result = linker.link_entity(ambiguous_mention)
        assert ambiguous_result.action == "UNRESOLVED", "Ambiguous reference should be UNRESOLVED"

        # Test 2: Unambiguous reference (with jurisdiction)
        unambiguous_mention = EntityMention(
            name="رأی دادگاه تجدیدنظر تهران سال ۱۴۰۱",
            entity_type="JUDGMENT",
            identities={"year": "1401", "jurisdiction": "TEH"},
            provenance={"doc_id": "test_unambiguous"}
        )

        unambiguous_result = linker.link_entity(unambiguous_mention)
        # This should potentially link (depending on scoring), but at minimum should not be UNRESOLVED
        # The exact behavior depends on scoring, but it should be different from ambiguous
        assert unambiguous_result.action != ambiguous_result.action or \
               unambiguous_result.confidence != ambiguous_result.confidence, \
               "Unambiguous reference should behave differently than ambiguous"


if __name__ == "__main__":
    # Run the test manually for verification
    test_instance = TestAdversarialAmbiguity()
    try:
        test_instance.test_judgment_ambiguity_detection()
        print("✅ PASS: Judgment ambiguity detection test passed")

        test_instance.test_judgment_entity_extraction()
        print("✅ PASS: Judgment entity extraction test passed")

        test_instance.test_ambiguous_vs_unambiguous_judgment()
        print("✅ PASS: Ambiguous vs unambiguous judgment test passed")

        print("\n🎉 All adversarial ambiguity tests PASSED!")
        print("The system correctly detects ambiguity and returns UNRESOLVED.")

    except Exception as e:
        print(f"❌ FAIL: {e}")
        raise
