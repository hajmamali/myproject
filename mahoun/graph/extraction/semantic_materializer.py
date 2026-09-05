"""
MAHOUN Semantic Materializer (Phase 2B)
======================================
Classification: CANONICAL SEMANTIC MATERIALIZATION ENGINE
Purpose: Materializes structured semantic ontology, article logical decompositions
         (Conditions, Sanctions, Exceptions), and taxonomic assertions into Neo4j.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from mahoun.core.models.semantic import (
    ArticleDecomposition,
    ConditionClause,
    ExceptionClause,
    SanctionClause,
    SemanticAssertion,
)
from mahoun.graph.extraction.semantic_extractor import SemanticExtractor
from mahoun.graph.ontology.legal_concepts import (
    CANONICAL_LEGAL_CONCEPTS,
    SemanticIdentity,
)

logger = logging.getLogger(__name__)


class SemanticMaterializer:
    """
    Materializes extracted semantic structures into Neo4j with full
    cryptographic and span provenance.
    """

    def __init__(
        self,
        extractor: Optional[SemanticExtractor] = None,
        ontology: Optional[Dict[str, SemanticIdentity]] = None,
    ) -> None:
        self.extractor = extractor or SemanticExtractor()
        self.ontology = ontology or CANONICAL_LEGAL_CONCEPTS

    def generate_ontology_cypher(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate parameterized Cypher statements to materialize the concept taxonomy."""
        statements: List[Tuple[str, Dict[str, Any]]] = []

        # 1. Merge Concepts
        for concept_id, concept in self.ontology.items():
            cypher = """
            MERGE (c:Concept {id: $id})
            SET c.canonical_label_fa = $label_fa,
                c.canonical_label_en = $label_en,
                c.normalized_label = $norm_label,
                c.domain = $domain,
                c.jurisdiction = $jurisdiction,
                c.ontology_version = $onto_ver,
                c.semantic_schema_version = $schema_ver,
                c.description_fa = $desc_fa,
                c.aliases_fa = $aliases_fa,
                c.aliases_en = $aliases_en
            """
            params = {
                "id": concept.canonical_id,
                "label_fa": concept.canonical_label_fa,
                "label_en": concept.canonical_label_en,
                "norm_label": concept.normalized_label,
                "domain": concept.domain,
                "jurisdiction": concept.jurisdiction,
                "onto_ver": concept.ontology_version,
                "schema_ver": concept.semantic_schema_version,
                "desc_fa": concept.description_fa or "",
                "aliases_fa": concept.aliases_fa,
                "aliases_en": concept.aliases_en,
            }
            statements.append((cypher, params))

        # 2. Concept Hierarchy (INHERITS_FROM)
        for concept_id, concept in self.ontology.items():
            if concept.parent_concept_id:
                cypher = """
                MATCH (child:Concept {id: $child_id})
                MATCH (parent:Concept {id: $parent_id})
                MERGE (child)-[:INHERITS_FROM]->(parent)
                """
                params = {
                    "child_id": concept.canonical_id,
                    "parent_id": concept.parent_concept_id,
                }
                statements.append((cypher, params))

        return statements

    def generate_decomposition_cypher(
        self, decomposition: ArticleDecomposition
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate Cypher statements for article conditions, sanctions, and exceptions."""
        statements: List[Tuple[str, Dict[str, Any]]] = []
        art_id = decomposition.article_id

        # 1. Conditions
        for cond in decomposition.conditions:
            cypher = """
            MATCH (a:Article {id: $art_id})
            MERGE (c:Condition {id: $cond_id})
            SET c.article_id = $art_id,
                c.condition_text = $text,
                c.trigger_keyword = $trigger,
                c.span_start = $start,
                c.span_end = $end
            MERGE (a)-[:HAS_CONDITION]->(c)
            """
            params = {
                "art_id": art_id,
                "cond_id": cond.id,
                "text": cond.condition_text,
                "trigger": cond.trigger_keyword,
                "start": cond.span_start,
                "end": cond.span_end,
            }
            statements.append((cypher, params))

        # 2. Sanctions
        for sanc in decomposition.sanctions:
            cypher = """
            MATCH (a:Article {id: $art_id})
            MERGE (s:Sanction {id: $sanc_id})
            SET s.article_id = $art_id,
                s.sanction_text = $text,
                s.sanction_type = $type,
                s.span_start = $start,
                s.span_end = $end
            MERGE (a)-[:HAS_SANCTION]->(s)
            """
            params = {
                "art_id": art_id,
                "sanc_id": sanc.id,
                "text": sanc.sanction_text,
                "type": sanc.sanction_type,
                "start": sanc.span_start,
                "end": sanc.span_end,
            }
            statements.append((cypher, params))

        # 3. Exceptions
        for exc in decomposition.exceptions:
            cypher = """
            MATCH (a:Article {id: $art_id})
            MERGE (e:Exception {id: $exc_id})
            SET e.article_id = $art_id,
                e.exception_text = $text,
                e.trigger_keyword = $trigger,
                e.span_start = $start,
                e.span_end = $end
            MERGE (a)-[:HAS_EXCEPTION]->(e)
            """
            params = {
                "art_id": art_id,
                "exc_id": exc.id,
                "text": exc.exception_text,
                "trigger": exc.trigger_keyword,
                "start": exc.span_start,
                "end": exc.span_end,
            }
            statements.append((cypher, params))

        return statements

    def generate_assertions_cypher(
        self, assertions: List[SemanticAssertion]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Generate Cypher statements for Article -> Concept assertions."""
        statements: List[Tuple[str, Dict[str, Any]]] = []

        for assertion in assertions:
            # REGULATES relationship with proof metadata
            cypher = f"""
            MATCH (a:Article {{id: $art_id}})
            MATCH (c:Concept {{id: $concept_id}})
            MERGE (a)-[r:{assertion.assertion_type}]->(c)
            SET r.assertion_id = $assertion_id,
                r.evidence_text_span = $evidence_span,
                r.evidence_offset_start = $start,
                r.evidence_offset_end = $end,
                r.evidence_sha256 = $sha256,
                r.status = $status,
                r.verification_method = $method
            """
            params = {
                "art_id": assertion.source_entity_id,
                "concept_id": assertion.target_entity_id,
                "assertion_id": assertion.assertion_id,
                "evidence_span": assertion.evidence_text_span,
                "start": assertion.evidence_offset_start,
                "end": assertion.evidence_offset_end,
                "sha256": assertion.evidence_sha256,
                "status": assertion.status.value,
                "method": assertion.verification_method,
            }
            statements.append((cypher, params))

        return statements
