"""
Entity Linker - Graph Normalization Layer
==========================================
Enterprise-grade entity linking for Neo4j graph construction.

This module converts raw NER output into normalized graph structures,
creating or merging nodes and building edges while ensuring semantic integrity.

Responsibilities:
- Convert raw NER output into normalized graph structures
- Create or merge nodes (idempotent operations)
- Build directional edges
- Validate uniqueness and semantic integrity

Operational Rules:
- Idempotent operations only (safe to re-run)
- Silent fail on missing entities (no ingestion-blocking exceptions)
- Aligned with existing graph_rag builder patterns

Usage:
    from mahoun.graph.builders.entity_linker import EntityLinker, link_entities_to_graph
    
    # Quick linking
    result = link_entities_to_graph(entities, case_id="case_001")
    
    # Advanced usage
    linker = EntityLinker()
    nodes, edges = linker.link(entities, case_id="case_001")

Graph Schema Contract:
    NODES:
        (:Case { case_id, title, date, court, … })
        (:Person { name, national_id?, normalized_name })
        (:Organization { name, registration_id?, normalized_name })
        (:Court { name, level, city })
        (:LawArticle { code, article, clause, description })
        (:Topic { label })
    
    EDGES:
        (:Person)-[:PARTY_IN]->(:Case)
        (:Organization)-[:PARTY_IN]->(:Case)
        (:Case)-[:REFERS_TO]->(:LawArticle)
        (:Case)-[:HANDLED_BY]->(:Court)
        (:Case)-[:ABOUT]->(:Topic)
"""

import re
import logging
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph

logger = logging.getLogger(__name__)

# ============================================================================
# Node/Edge Data Classes
# ============================================================================

@dataclass
class GraphNodeSpec:
    """Specification for a graph node to be created/merged"""
    label: str  # Node label (Person, Organization, Court, etc.)
    node_id: str  # Unique identifier for MERGE operations
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    source_case_id: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class GraphEdgeSpec:
    """Specification for a graph edge to be created"""
    from_label: str
    from_id: str
    to_label: str
    to_id: str
    relationship_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    confidence: float = 1.0


@dataclass
class LinkingResult:
    """Result of entity linking operation"""
    success: bool
    case_id: str
    nodes_created: int = 0
    edges_created: int = 0
    nodes_merged: int = 0
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


# ============================================================================
# Entity Linker
# ============================================================================

class EntityLinker:
    """
    Enterprise-grade entity linker for graph construction.
    
    Converts NER output into normalized graph nodes and edges,
    supporting idempotent MERGE operations for Neo4j.
    
    Features:
    - Idempotent node creation (MERGE semantics)
    - Automatic edge construction
    - Entity normalization and deduplication
    - Cross-document entity resolution (future Phase 2)
    
    Usage:
        linker = EntityLinker()
        nodes, edges = linker.link(entities, case_id="case_001")
        
        # Or get full result
        result = linker.link_with_result(entities, case_id="case_001")
    """
    
    def __init__(
        self,
        enable_normalization: bool = True,
        enable_deduplication: bool = True,
        neo4j_adapter=None
    ):
        """
        Initialize Entity Linker.
        
        Args:
            enable_normalization: Normalize entity values before linking
            enable_deduplication: Remove duplicate nodes
            neo4j_adapter: Optional Neo4j adapter for direct graph updates
        """
        self.settings = get_runtime_settings()
        self.enable_normalization = enable_normalization
        self.enable_deduplication = enable_deduplication
        self.neo4j_adapter = neo4j_adapter
        
        # Statistics
        self.stats = {
            "total_linked": 0,
            "total_nodes": 0,
            "total_edges": 0,
            "errors": 0
        }
        
        logger.info("EntityLinker initialized")
    
    def link(
        self,
        entities: Dict[str, List[Dict[str, Any]]],
        case_id: str,
        case_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """
        Link entities to graph structures.
        
        Args:
            entities: NER output dictionary with entity lists
            case_id: Unique case/document identifier
            case_metadata: Optional metadata for the case node
        
        Returns:
            Tuple of (nodes, edges) specifications
        """
        import time
        start_time = time.time()
        
        # Skip in desktop-minimal mode
        if should_skip_graph():
            logger.debug("EntityLinker: Skipping in desktop-minimal mode")
            return [], []
        
        nodes: List[GraphNodeSpec] = []
        edges: List[GraphEdgeSpec] = []
        seen_node_ids: Set[str] = set()
        
        try:
            # Create Case node first
            case_node = self._create_case_node(case_id, case_metadata)
            nodes.append(case_node)
            seen_node_ids.add(case_node.node_id)
            
            # Process each entity type
            person_nodes, person_edges = self._link_persons(
                entities.get("persons", []), case_id, seen_node_ids
            )
            nodes.extend(person_nodes)
            edges.extend(person_edges)
            
            org_nodes, org_edges = self._link_organizations(
                entities.get("organizations", []), case_id, seen_node_ids
            )
            nodes.extend(org_nodes)
            edges.extend(org_edges)
            
            court_nodes, court_edges = self._link_courts(
                entities.get("courts", []), case_id, seen_node_ids
            )
            nodes.extend(court_nodes)
            edges.extend(court_edges)
            
            law_nodes, law_edges = self._link_laws(
                entities.get("laws", []), case_id, seen_node_ids
            )
            nodes.extend(law_nodes)
            edges.extend(law_edges)
            
            topic_nodes, topic_edges = self._link_topics(
                entities.get("topics", []), case_id, seen_node_ids
            )
            nodes.extend(topic_nodes)
            edges.extend(topic_edges)
            
            # Update statistics
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_stats(len(nodes), len(edges), processing_time_ms)
            
            logger.info(
                f"NER_PIPELINE: Linked entities for case {case_id} - "
                f"nodes={len(nodes)}, edges={len(edges)} "
                f"({processing_time_ms:.1f}ms)"
            )
            
        except Exception as e:
            logger.error(f"EntityLinker error for case {case_id}: {e}")
            self.stats["errors"] += 1
            # Silent fail - return what we have
        
        return nodes, edges
    
    def link_with_result(
        self,
        entities: Dict[str, List[Dict[str, Any]]],
        case_id: str,
        case_metadata: Optional[Dict[str, Any]] = None
    ) -> LinkingResult:
        """
        Link entities and return detailed result.
        
        Args:
            entities: NER output dictionary
            case_id: Case identifier
            case_metadata: Optional case metadata
        
        Returns:
            LinkingResult with statistics
        """
        import time
        start_time = time.time()
        
        nodes, edges = self.link(entities, case_id, case_metadata)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return LinkingResult(
            success=True,
            case_id=case_id,
            nodes_created=len(nodes),
            edges_created=len(edges),
            processing_time_ms=processing_time_ms
        )
    
    # ========================================================================
    # Entity Type Processors
    # ========================================================================
    
    def _create_case_node(
        self,
        case_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GraphNodeSpec:
        """Create Case node specification"""
        properties = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat()
        }
        
        if metadata:
            # Add relevant metadata
            if metadata.get("case_type"):
                properties["case_type"] = metadata["case_type"]
            if metadata.get("court_level"):
                properties["court_level"] = metadata["court_level"]
            if metadata.get("is_final") is not None:
                properties["is_final"] = metadata["is_final"]
            if metadata.get("decision_date"):
                properties["decision_date"] = metadata["decision_date"]
        
        return GraphNodeSpec(
            label="Case",
            node_id=f"case_{case_id}",
            properties=properties,
            source_case_id=case_id
        )
    
    def _link_persons(
        self,
        persons: List[Dict[str, Any]],
        case_id: str,
        seen_ids: Set[str]
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """Link person entities to graph"""
        nodes: List[Any] = []
        edges: List[Any] = []
        for person in persons:
            try:
                # Generate unique node ID
                name = person.get("name", "")
                normalized_name = person.get("normalized_name") or self._normalize_string(name)
                node_id = self._generate_person_id(normalized_name, person.get("national_id"))
                
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                
                # Create node
                properties = {
                    "name": name,
                    "normalized_name": normalized_name,
                }
                
                if person.get("title"):
                    properties["title"] = person["title"]
                if person.get("father_name"):
                    properties["father_name"] = person["father_name"]
                if person.get("national_id"):
                    properties["national_id"] = person["national_id"]
                if person.get("role"):
                    properties["role"] = person["role"]
                
                nodes.append(GraphNodeSpec(
                    label="Person",
                    node_id=node_id,
                    properties=properties,
                    source_case_id=case_id,
                    confidence=person.get("confidence", 0.9)
                ))
                
                # Create edge to case
                edge_props: Dict[str, Any] = {}
                if person.get("role"):
                    edge_props["role"] = person["role"]
                
                edges.append(GraphEdgeSpec(
                    from_label="Person",
                    from_id=node_id,
                    to_label="Case",
                    to_id=f"case_{case_id}",
                    relationship_type="PARTY_IN",
                    properties=edge_props,
                    confidence=person.get("confidence", 0.9)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to link person: {e}")
                continue
        
        return nodes, edges
    
    def _link_organizations(
        self,
        organizations: List[Dict[str, Any]],
        case_id: str,
        seen_ids: Set[str]
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """Link organization entities to graph"""
        nodes: List[Any] = []
        edges: List[Any] = []
        for org in organizations:
            try:
                name = org.get("name", "")
                normalized_name = org.get("normalized_name") or self._normalize_string(name)
                node_id = self._generate_org_id(normalized_name, org.get("registration_id"))
                
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                
                properties = {
                    "name": name,
                    "normalized_name": normalized_name,
                }
                
                if org.get("org_type"):
                    properties["org_type"] = org["org_type"]
                if org.get("registration_id"):
                    properties["registration_id"] = org["registration_id"]
                
                nodes.append(GraphNodeSpec(
                    label="Organization",
                    node_id=node_id,
                    properties=properties,
                    source_case_id=case_id,
                    confidence=org.get("confidence", 0.85)
                ))
                
                edges.append(GraphEdgeSpec(
                    from_label="Organization",
                    from_id=node_id,
                    to_label="Case",
                    to_id=f"case_{case_id}",
                    relationship_type="PARTY_IN",
                    properties={},
                    confidence=org.get("confidence", 0.85)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to link organization: {e}")
                continue
        
        return nodes, edges
    
    def _link_courts(
        self,
        courts: List[Dict[str, Any]],
        case_id: str,
        seen_ids: Set[str]
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """Link court entities to graph"""
        nodes: List[Any] = []
        edges: List[Any] = []
        for court in courts:
            try:
                # Use normalized name or generate from components
                name = court.get("normalized_name") or court.get("text", "")
                node_id = self._generate_court_id(
                    court.get("level"),
                    court.get("branch"),
                    court.get("city")
                )
                
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                
                properties = {
                    "name": name,
                }
                
                if court.get("level"):
                    properties["level"] = court["level"]
                if court.get("branch"):
                    properties["branch"] = court["branch"]
                if court.get("city"):
                    properties["city"] = court["city"]
                if court.get("province"):
                    properties["province"] = court["province"]
                
                nodes.append(GraphNodeSpec(
                    label="Court",
                    node_id=node_id,
                    properties=properties,
                    source_case_id=case_id,
                    confidence=court.get("confidence", 0.9)
                ))
                
                edges.append(GraphEdgeSpec(
                    from_label="Case",
                    from_id=f"case_{case_id}",
                    to_label="Court",
                    to_id=node_id,
                    relationship_type="HANDLED_BY",
                    properties={},
                    confidence=court.get("confidence", 0.9)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to link court: {e}")
                continue
        
        return nodes, edges
    
    def _link_laws(
        self,
        laws: List[Dict[str, Any]],
        case_id: str,
        seen_ids: Set[str]
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """Link law/article entities to graph"""
        nodes: List[Any] = []
        edges: List[Any] = []
        for law in laws:
            try:
                article_num = law.get("article_number", "")
                law_name = law.get("law_name", "")
                
                # Generate node ID from article reference
                node_id = self._generate_law_id(article_num, law_name)
                
                if node_id in seen_ids:
                    # Still create edge to existing node
                    edges.append(GraphEdgeSpec(
                        from_label="Case",
                        from_id=f"case_{case_id}",
                        to_label="LawArticle",
                        to_id=node_id,
                        relationship_type="REFERS_TO",
                        properties={},
                        confidence=law.get("confidence", 0.85)
                    ))
                    continue
                seen_ids.add(node_id)
                
                # Parse law code from name
                code = self._extract_law_code(law_name)
                
                properties = {
                    "article": article_num,
                    "law_name": law_name,
                    "code": code,
                    "description": law.get("normalized_ref", f"ماده {article_num} {law_name}")
                }
                
                if law.get("clause"):
                    properties["clause"] = law["clause"]
                
                nodes.append(GraphNodeSpec(
                    label="LawArticle",
                    node_id=node_id,
                    properties=properties,
                    source_case_id=case_id,
                    confidence=law.get("confidence", 0.85)
                ))
                
                edges.append(GraphEdgeSpec(
                    from_label="Case",
                    from_id=f"case_{case_id}",
                    to_label="LawArticle",
                    to_id=node_id,
                    relationship_type="REFERS_TO",
                    properties={},
                    confidence=law.get("confidence", 0.85)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to link law: {e}")
                continue
        
        return nodes, edges
    
    def _link_topics(
        self,
        topics: List[Dict[str, Any]],
        case_id: str,
        seen_ids: Set[str]
    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
        """Link topic entities to graph"""
        nodes: List[Any] = []
        edges: List[Any] = []
        for topic in topics:
            try:
                label = topic.get("topic") or topic.get("text", "")
                node_id = self._generate_topic_id(label)
                
                if node_id in seen_ids:
                    # Still create edge
                    edges.append(GraphEdgeSpec(
                        from_label="Case",
                        from_id=f"case_{case_id}",
                        to_label="Topic",
                        to_id=node_id,
                        relationship_type="ABOUT",
                        properties={},
                        confidence=topic.get("confidence", 0.8)
                    ))
                    continue
                seen_ids.add(node_id)
                
                properties = {
                    "label": label,
                }
                
                if topic.get("category"):
                    properties["category"] = topic["category"]
                
                nodes.append(GraphNodeSpec(
                    label="Topic",
                    node_id=node_id,
                    properties=properties,
                    source_case_id=case_id,
                    confidence=topic.get("confidence", 0.8)
                ))
                
                edges.append(GraphEdgeSpec(
                    from_label="Case",
                    from_id=f"case_{case_id}",
                    to_label="Topic",
                    to_id=node_id,
                    relationship_type="ABOUT",
                    properties={},
                    confidence=topic.get("confidence", 0.8)
                ))
                
            except Exception as e:
                logger.warning(f"Failed to link topic: {e}")
                continue
        
        return nodes, edges
    
    # ========================================================================
    # ID Generation (Ensures Uniqueness for MERGE)
    # ========================================================================
    
    def _generate_person_id(self, normalized_name: str, national_id: Optional[str] = None) -> str:
        """Generate unique person ID"""
        if national_id:
            return f"person_nid_{national_id}"
        # Use hash of normalized name
        name_hash = hashlib.md5(normalized_name.encode('utf-8')).hexdigest()[:12]
        return f"person_{name_hash}"
    
    def _generate_org_id(self, normalized_name: str, registration_id: Optional[str] = None) -> str:
        """Generate unique organization ID"""
        if registration_id:
            return f"org_reg_{registration_id}"
        name_hash = hashlib.md5(normalized_name.encode('utf-8')).hexdigest()[:12]
        return f"org_{name_hash}"
    
    def _generate_court_id(
        self,
        level: Optional[str],
        branch: Optional[str],
        city: Optional[str]
    ) -> str:
        """Generate unique court ID"""
        parts: List[Any] = []
        if level:
            parts.append(level)
        if branch:
            parts.append(f"شعبه{branch}")
        if city:
            parts.append(city)
        
        combined = "_".join(parts) if parts else "unknown"
        court_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()[:12]
        return f"court_{court_hash}"
    
    def _generate_law_id(self, article_num: str, law_name: str) -> str:
        """Generate unique law article ID"""
        code = self._extract_law_code(law_name)
        return f"law_{code}_{article_num}".replace(" ", "_")
    
    def _generate_topic_id(self, label: str) -> str:
        """Generate unique topic ID"""
        normalized = self._normalize_string(label)
        return f"topic_{normalized}".replace(" ", "_")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _normalize_string(self, s: str) -> str:
        """Normalize string for ID generation and comparison"""
        if not s:
            return ""
        # Remove extra whitespace
        s = re.sub(r'\s+', ' ', s.strip())
        return s.lower()
    
    def _extract_law_code(self, law_name: str) -> str:
        """Extract short code from law name"""
        if not law_name:
            return "unknown"
        
        # Common law name mappings
        law_codes = {
            "مدنی": "civil",
            "آیین دادرسی مدنی": "cpc",
            "آیین دادرسی کیفری": "cpp",
            "مجازات اسلامی": "ipc",
            "تجارت": "commercial",
            "کار": "labor",
            "ثبت": "registration",
            "مالیات": "tax",
        }
        
        for key, code in law_codes.items():
            if key in law_name:
                return code
        
        # Generate hash for unknown laws
        return hashlib.md5(law_name.encode('utf-8')).hexdigest()[:8]
    
    def _update_stats(self, nodes: int, edges: int, time_ms: float):
        """Update linker statistics"""
        self.stats["total_linked"] += 1
        self.stats["total_nodes"] += nodes
        self.stats["total_edges"] += edges
    
    def get_stats(self) -> Dict[str, Any]:
        """Get linker statistics"""
        return self.stats.copy()
    
    # ========================================================================
    # Neo4j Direct Integration (Optional)
    # ========================================================================
    
    def submit_to_neo4j(
        self,
        nodes: List[GraphNodeSpec],
        edges: List[GraphEdgeSpec]
    ) -> bool:
        """
        Submit nodes and edges directly to Neo4j.
        
        Args:
            nodes: List of node specifications
            edges: List of edge specifications
        
        Returns:
            True if successful
        """
        if not self.neo4j_adapter:
            logger.warning("No Neo4j adapter configured for direct submission")
            return False
        
        if should_skip_graph():
            logger.debug("EntityLinker: Skipping Neo4j submission in desktop-minimal mode")
            return True
        
        try:
            # Create nodes using MERGE
            for node in nodes:
                self._merge_node(node)
            
            # Create edges
            for edge in edges:
                self._create_edge(edge)
            
            logger.info(f"Submitted {len(nodes)} nodes and {len(edges)} edges to Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"Neo4j submission failed: {e}")
            return False
    
    def _merge_node(self, node: GraphNodeSpec):
        """Merge a single node into Neo4j"""
        if not self.neo4j_adapter:
            return
        
        # Build MERGE query
        props_str = ", ".join([f"n.{k} = ${k}" for k in node.properties.keys()])
        query = f"""
            MERGE (n:{node.label} {{node_id: $node_id}})
            SET {props_str}
        """
        
        params = {"node_id": node.node_id, **node.properties}
        self.neo4j_adapter._execute_query(query, params)
    
    def _create_edge(self, edge: GraphEdgeSpec):
        """Create an edge in Neo4j"""
        if not self.neo4j_adapter:
            return
        
        query = f"""
            MATCH (a:{edge.from_label} {{node_id: $from_id}})
            MATCH (b:{edge.to_label} {{node_id: $to_id}})
            MERGE (a)-[r:{edge.relationship_type}]->(b)
        """
        
        params = {"from_id": edge.from_id, "to_id": edge.to_id}
        self.neo4j_adapter._execute_query(query, params)


# ============================================================================
# Convenience Functions
# ============================================================================

# Global linker instance
_linker: Optional[EntityLinker] = None


def _get_linker() -> EntityLinker:
    """Get or create global linker instance"""
    global _linker
    if _linker is None:
        _linker = EntityLinker()
    return _linker


def link_entities_to_graph(
    entities: Dict[str, List[Dict[str, Any]]],
    case_id: str,
    case_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Link NER entities to graph structures.
    
    Main API function for entity linking.
    
    Args:
        entities: NER output from legal_ner.extract_entities()
        case_id: Unique case/document identifier
        case_metadata: Optional case metadata
    
    Returns:
        Tuple of (nodes, edges) as dictionaries
    
    Example:
        >>> from mahoun.pipelines.ingestion.legal_ner import extract_entities
        >>> from mahoun.graph.builders.entity_linker import link_entities_to_graph
        >>> 
        >>> entities = extract_entities(text)
        >>> nodes, edges = link_entities_to_graph(entities, case_id="case_001")
    """
    linker = _get_linker()
    nodes, edges = linker.link(entities, case_id, case_metadata)
    
    # Convert to dictionaries for serialization
    nodes_dicts = [
        {
            "label": n.label,
            "node_id": n.node_id,
            "properties": n.properties,
            "confidence": n.confidence
        }
        for n in nodes
    ]
    
    edges_dicts = [
        {
            "from_label": e.from_label,
            "from_id": e.from_id,
            "to_label": e.to_label,
            "to_id": e.to_id,
            "relationship_type": e.relationship_type,
            "properties": e.properties,
            "confidence": e.confidence
        }
        for e in edges
    ]
    
    return nodes_dicts, edges_dicts


def link_and_submit(
    entities: Dict[str, List[Dict[str, Any]]],
    case_id: str,
    case_metadata: Optional[Dict[str, Any]] = None,
    neo4j_adapter=None
) -> LinkingResult:
    """
    Link entities and optionally submit to Neo4j.
    
    Args:
        entities: NER output
        case_id: Case identifier
        case_metadata: Optional case metadata
        neo4j_adapter: Optional Neo4j adapter for direct submission
    
    Returns:
        LinkingResult with statistics
    """
    linker = EntityLinker(neo4j_adapter=neo4j_adapter)
    result = linker.link_with_result(entities, case_id, case_metadata)
    
    if neo4j_adapter and result.success:
        nodes, edges = linker.link(entities, case_id, case_metadata)
        linker.submit_to_neo4j(nodes, edges)
    
    return result


# ============================================================================
# Module Test
# ============================================================================

if __name__ == "__main__":
    print("🔗 Testing Entity Linker")
    print("=" * 60)
    
    # Sample NER output
    entities = {
        "persons": [
            {
                "text": "آقای احمد احمدی فرزند محمد",
                "name": "احمد احمدی",
                "title": "آقای",
                "father_name": "محمد",
                "confidence": 0.9
            }
        ],
        "organizations": [
            {
                "text": "شرکت توسعه فناوری",
                "name": "توسعه فناوری",
                "org_type": "شرکت",
                "registration_id": "12345",
                "confidence": 0.85
            }
        ],
        "courts": [
            {
                "text": "شعبه ۱۰ دادگاه عمومی حقوقی تهران",
                "level": "دادگاه عمومی حقوقی",
                "branch": "10",
                "city": "تهران",
                "confidence": 0.9
            }
        ],
        "laws": [
            {
                "article_number": "10",
                "law_name": "قانون مدنی",
                "confidence": 0.85
            }
        ],
        "topics": [
            {
                "topic": "مطالبه وجه",
                "category": "مالی",
                "confidence": 0.8
            }
        ]
    }
    
    nodes, edges = link_entities_to_graph(entities, case_id="test_001")
    
    print(f"\n📊 Created {len(nodes)} nodes:")
    for node in nodes:
        print(f"   • ({node['label']}) {node['node_id']}")
    
    print(f"\n🔗 Created {len(edges)} edges:")
    for edge in edges:
        print(f"   • ({edge['from_label']})-[:{edge['relationship_type']}]->({edge['to_label']})")
    
    print("\n" + "=" * 60)
    print("✅ Entity Linker Test Complete")

