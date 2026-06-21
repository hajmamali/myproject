"""
Neo4j Graph Operations
=======================

High-level operations for graph manipulation.

ARCHITECTURAL MANDATE:
All write operations MUST use `connection.governed_session()`.
Generating raw mutation Cypher in this file is strictly forbidden.
All mutations must include provenance and pass the ValidatorPipeline.
"""

import logging
import time
import re
import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection
from mahoun.graph.neo4j.monitoring import Neo4jMetrics

if TYPE_CHECKING:
    from mahoun.core.governance.validator_pipeline import ValidatorPipeline
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata

_log = logging.getLogger(__name__)


class GraphOperations:
    """High-level graph operations backed by GovernedNeo4jSession.

    Direct raw mutations are architecturally forbidden.
    All write paths execute through the GovernedWriteTransaction.
    """

    def __init__(
        self,
        connection: Optional[Neo4jConnection] = None,
        metrics: Optional[Neo4jMetrics] = None,
        validator_pipeline: Optional["ValidatorPipeline"] = None,
    ):
        # Lazy import for ValidatorPipeline
        from mahoun.core.governance.validator_pipeline import ValidatorPipeline
        
        self.conn = connection or get_connection()
        self.metrics = metrics or Neo4jMetrics()
        self._pipeline = validator_pipeline or ValidatorPipeline()

    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
        merge: bool = True,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or merge a node through the governed boundary."""
        start = time.time()
        node_data = {**properties}
        if "id" not in node_data:
            node_data["id"] = node_data.get("node_id", node_data.get("verdict_id", ""))

        with self.conn.governed_session(
            pipeline=self._pipeline, correlation_id=correlation_id or ""
        ) as session:
            receipt = session.write_node(
                label=label,
                node_data=node_data,
                merge=merge,
            )

        self.metrics.record_query(time.time() - start)
        return {"_governed": True, "_receipt_id": receipt.receipt_id}

    def create_relationship(
        self,
        from_label: str,
        from_id: str,
        to_label: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
        merge: bool = True,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Create relationship between nodes through the governed boundary."""
        start = time.time()
        
        with self.conn.governed_session(
            pipeline=self._pipeline, correlation_id=correlation_id or ""
        ) as session:
            session.write_relationship(
                source_type=from_label,
                source_id=from_id,
                relationship_type=rel_type,
                target_type=to_label,
                target_id=to_id,
                relationship_data=properties or {},
                merge=merge,
            )

        self.metrics.record_query(time.time() - start)
        return True
    
    def batch_create_nodes(
        self,
        label: str,
        nodes: List[Dict[str, Any]],
        batch_size: int = 1000,
        merge: bool = True,
        correlation_id: Optional[str] = None,
    ) -> int:
        """Batch create nodes atomically via GovernedWriteTransaction."""
        total_created = 0
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            start = time.time()
            
            try:
                with self.conn.governed_session(
                    pipeline=self._pipeline, correlation_id=correlation_id or ""
                ) as session:
                    tx = session.begin_transaction()
                    for node_data in batch:
                        data = {**node_data}
                        if "id" not in data:
                            data["id"] = data.get("node_id", data.get("verdict_id", ""))
                        tx.queue_node(label=label, node_data=data, merge=merge)
                    
                    receipts = tx.commit()
                    total_created += len(receipts)
                self.metrics.record_query(time.time() - start)
            except Exception as e:
                self.metrics.record_error()
                _log.error(f"❌ Batch {i//batch_size + 1} failed: {e}")
        
        return total_created
    
    def batch_create_relationships(
        self,
        relationships: List[Tuple[str, str, str, Dict[str, Any]]],
        from_label: str = "Document",
        to_label: str = "Document",
        batch_size: int = 1000,
        merge: bool = True,
        correlation_id: Optional[str] = None,
    ) -> int:
        """Batch create relationships atomically."""
        total_created = 0
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            start = time.time()
            
            try:
                with self.conn.governed_session(
                    pipeline=self._pipeline, correlation_id=correlation_id or ""
                ) as session:
                    tx = session.begin_transaction()
                    for from_id, to_id, rel_type, props in batch:
                        tx.queue_relationship(
                            source_type=from_label,
                            source_id=from_id,
                            relationship_type=rel_type,
                            target_type=to_label,
                            target_id=to_id,
                            relationship_data=props,
                            merge=merge,
                        )
                    
                    receipts = tx.commit()
                    total_created += len(receipts)
                self.metrics.record_query(time.time() - start)
            except Exception as e:
                self.metrics.record_error()
                _log.error(f"❌ Batch {i//batch_size + 1} failed: {e}")
        
        return total_created

    def batch_create_typed_relationships(
        self,
        relationships: List[Tuple[str, str, str, str, str, Dict[str, Any]]],
        batch_size: int = 1000,
        merge: bool = True,
        correlation_id: Optional[str] = None,
    ) -> int:
        """Batch create relationships with different types atomically."""
        total_created = 0
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            start = time.time()
            
            try:
                with self.conn.governed_session(
                    pipeline=self._pipeline, correlation_id=correlation_id or ""
                ) as session:
                    tx = session.begin_transaction()
                    for from_label, from_id, to_label, to_id, rel_type, props in batch:
                        tx.queue_relationship(
                            source_type=from_label,
                            source_id=from_id,
                            relationship_type=rel_type,
                            target_type=to_label,
                            target_id=to_id,
                            relationship_data=props,
                            merge=merge,
                        )
                    
                    receipts = tx.commit()
                    total_created += len(receipts)
                self.metrics.record_query(time.time() - start)
            except Exception as e:
                self.metrics.record_error()
                _log.error(f"❌ Batch {i//batch_size + 1} failed: {e}")
        
        return total_created

    def get_node(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID (Read-only query, passes boundary)."""
        query = f"MATCH (n:{label} {{id: $id}}) RETURN n"
        result = self.conn.execute_query(query, {"id": node_id})
        return dict(result[0]["n"]) if result else None


# Convenience functions
def create_document(doc_id: str, title: str, content: str, **kwargs) -> Dict[str, Any]:
    # Lazy import for ProvenanceMetadata
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    
    ops = GraphOperations()
    prov = ProvenanceMetadata.create_synthetic(source="convenience_api", author="system").to_dict()
    return ops.create_node("Document", {"id": doc_id, "title": title, "content": content, "provenance": prov, **kwargs})


def create_relationship(from_id: str, to_id: str, rel_type: str = "CITES", **properties) -> bool:
    # Lazy import for ProvenanceMetadata
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    
    ops = GraphOperations()
    prov = ProvenanceMetadata.create_synthetic(source="convenience_api", author="system").to_dict()
    props = {"provenance": prov, **properties}
    return ops.create_relationship("Document", from_id, "Document", to_id, rel_type, props)


def batch_create_nodes(label: str, nodes: List[Dict[str, Any]], batch_size: int = 1000) -> int:
    ops = GraphOperations()
    return ops.batch_create_nodes(label, nodes, batch_size)


def batch_create_relationships(relationships: List[Tuple[str, str, str, Dict[str, Any]]], batch_size: int = 1000) -> int:
    ops = GraphOperations()
    return ops.batch_create_relationships(relationships, batch_size=batch_size)


# ============================================================================
# Bootstrap Verdict Ingestion Support (Scenario B)
# ============================================================================

def _parse_law_article(article_str: str) -> Dict[str, str]:
    match = re.search(r'ماده\s+(\d+)\s+(.+)', article_str)
    if match:
        return {"article_no": match.group(1), "code": match.group(2).strip(), "label": article_str}
    return {"article_no": "", "code": "", "label": article_str}


def _generate_verdict_id(verdict_struct: Dict[str, Any]) -> str:
    source = verdict_struct.get("_source", {})
    filepath = source.get("filepath")
    if filepath:
        return os.path.splitext(os.path.basename(filepath))[0]
    
    case_meta = verdict_struct.get("case_meta", {})
    hash_input = f"{case_meta.get('court_level', '')}|{case_meta.get('case_type', '')}|{case_meta.get('procedure_stage', '')}"
    return hashlib.md5(hash_input.encode('utf-8')).hexdigest()[:16]


def upsert_verdict_struct(verdict_struct: Dict[str, Any]) -> str:
    """
    Upsert a parsed verdict structure into the Neo4j graph database.
    Now architecturally governed via GovernedWriteTransaction.
    """
    # Lazy imports for governance modules
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    from mahoun.core.governance.validator_pipeline import ValidatorPipeline
    
    _log.info("[GRAPH] Upserting verdict into Neo4j via Governance Boundary")
    verdict_id = _generate_verdict_id(verdict_struct)
    
    # Generate Synthetic Provenance for this ingestion
    prov_dict = ProvenanceMetadata.create_synthetic(
        source="upsert_verdict_struct",
        correlation_id=verdict_id,
        author="system-bootstrap"
    ).to_dict()
    
    conn = get_connection()
    pipeline = ValidatorPipeline()
    
    with conn.governed_session(pipeline=pipeline, correlation_id=verdict_id) as session:
        tx = session.begin_transaction()
        
        # 1. Verdict
        case_meta = verdict_struct.get("case_meta", {})
        verdict_props = {
            "id": verdict_id,
            "verdict_id": verdict_id,
            "court_level": case_meta.get("court_level", "نامشخص"),
            "procedure_stage": case_meta.get("procedure_stage", "نامشخص"),
            "case_type": case_meta.get("case_type", "نامشخص"),
            "is_final": case_meta.get("is_final", False),
            "finality_basis": case_meta.get("finality_basis", "") or "",
            "provenance": prov_dict
        }
        tx.queue_node("Verdict", verdict_props, merge=True)
        
        # 2. LawArticles
        legal_refs = verdict_struct.get("legal_references", {})
        all_articles = legal_refs.get("substantive_law", []) + legal_refs.get("procedural_law", [])
        
        for article_str in all_articles[:50]:
            parsed = _parse_law_article(article_str)
            article_id = f"law_{hashlib.md5(parsed['label'].encode()).hexdigest()[:8]}"
            article_props = {
                "id": article_id,
                "label": parsed["label"],
                "code": parsed["code"],
                "article_no": parsed["article_no"],
                "provenance": prov_dict
            }
            tx.queue_node("LawArticle", article_props, merge=True)
            tx.queue_relationship(
                source_type="Verdict", source_id=verdict_id,
                relationship_type="REFERS_TO",
                target_type="LawArticle", target_id=article_id,
                rel_data={"provenance": prov_dict}, merge=True
            )
            
        # 3. Tags
        system_tags = verdict_struct.get("system_tags", [])
        for tag in system_tags[:30]:
            tag_id = f"tag_{hashlib.md5(tag.encode()).hexdigest()[:8]}"
            tx.queue_node("Tag", {"id": tag_id, "name": tag, "provenance": prov_dict}, merge=True)
            tx.queue_relationship(
                source_type="Verdict", source_id=verdict_id,
                relationship_type="HAS_TAG",
                target_type="Tag", target_id=tag_id,
                rel_data={"provenance": prov_dict}, merge=True
            )
            
        # 4. Persons
        parties = verdict_struct.get("parties", {})
        
        def _add_person(person_data, role):
            if not person_data or not person_data.get("name"):
                return
            display_name = f"{person_data.get('title', '')} {person_data.get('name', '')}".strip()
            father_name = person_data.get("father_name", "")
            p_id = f"person_{hashlib.md5((display_name + father_name).encode()).hexdigest()[:8]}"
            
            tx.queue_node("Person", {
                "id": p_id, "display_name": display_name, "father_name": father_name, "provenance": prov_dict
            }, merge=True)
            
            tx.queue_relationship(
                source_type="Verdict", source_id=verdict_id,
                relationship_type="HAS_PARTY",
                target_type="Person", target_id=p_id,
                rel_data={"role": role, "provenance": prov_dict}, merge=True
            )

        _add_person(parties.get("third_party_objector"), "third_party_objector")
        _add_person(parties.get("third_party_objector_attorney"), "third_party_objector_attorney")
        for resp in parties.get("respondents", [])[:10]:
            _add_person(resp, "respondent")
        for att in parties.get("respondents_attorneys", [])[:10]:
            _add_person(att, "respondent_attorney")
            
        # Execute the transaction
        tx.commit()
    
    _log.info(f"[GRAPH] ✓ Upserted verdict {verdict_id} with full atomic governance")
    return verdict_id


# ============================================================================
# Read Helpers for Verdict Search Enrichment
# ============================================================================

def _graph_get_law_articles_for_verdict(self, verdict_id: str) -> List[str]:
    query = "MATCH (v:Verdict {verdict_id: $id})-[:REFERS_TO]->(a:LawArticle) RETURN a.label AS label"
    try:
        return [r["label"] for r in self.conn.execute_query(query, {"id": verdict_id}) if r.get("label")]
    except Exception:
        return []

def _graph_get_tags_for_verdict(self, verdict_id: str) -> List[str]:
    query = "MATCH (v:Verdict {verdict_id: $id})-[:HAS_TAG]->(t:Tag) RETURN t.name AS name"
    try:
        return [r["name"] for r in self.conn.execute_query(query, {"id": verdict_id}) if r.get("name")]
    except Exception:
        return []

def _graph_get_parties_for_verdict(self, verdict_id: str) -> List[Dict[str, str]]:
    query = "MATCH (v:Verdict {verdict_id: $id})-[r:HAS_PARTY]->(p:Person) RETURN p.display_name AS display_name, p.father_name AS father_name, r.role AS role"
    try:
        return [{"display_name": r.get("display_name", ""), "father_name": r.get("father_name", ""), "role": r.get("role", "")} for r in self.conn.execute_query(query, {"id": verdict_id})]
    except Exception:
        return []

def _graph_get_verdict_by_id(self, verdict_id: str) -> Optional[Dict[str, Any]]:
    query = "MATCH (v:Verdict {verdict_id: $id}) RETURN v"
    try:
        results = self.conn.execute_query(query, {"id": verdict_id})
        return dict(results[0]["v"]) if results else None
    except Exception:
        return None

GraphOperations.get_law_articles_for_verdict = _graph_get_law_articles_for_verdict
GraphOperations.get_tags_for_verdict = _graph_get_tags_for_verdict
GraphOperations.get_parties_for_verdict = _graph_get_parties_for_verdict
GraphOperations.get_verdict_by_id = _graph_get_verdict_by_id
