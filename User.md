## User

Project root: KingMahouN. Apply minimal constitutional hardening patches ONLY in these files: `mahoun/graph/builders/entity_linker.py`, `mahoun/graph/ultra_graph_builder.py`, `mahoun/ultra_systems/graph/ultra_graph_builder.py`.

Context and goals:
- Governance must be fail-closed. No raw mutation Cypher from builders. No Neo4jAdapter/free-form adapter patterns.
- User confirmed `self_improve` is disconnected for now; do not edit self_improve.
- Preserve architecture; patch only.

Required changes:
1) `entity_linker.py`
- Replace free-form `neo4j_adapter` parameter in `link_and_submit` with `connection: Optional[Neo4jConnection]` (or equivalent explicit typing); enforce constructor/call-site type with `isinstance(connection, Neo4jConnection)` before submission.
- Remove raw `session.run(...)` mutation calls from `_merge_node` and `_create_edge`; use `connection.governed_session(...): session.write_node(...)` and `session.write_relationship(...)`.
- Fix bug using `self.connection`; must use passed `connection`.
- Add explicit local label/property/relationship allowlists for this builder; reject unknown properties fail-closed.
- Avoid unsupported `operation_type` kwargs.
2) `mahoun/graph/ultra_graph_builder.py`
- Remove stale `Neo4jAdapter` import/dummy adapter pattern if unused.
- Keep governed export path, but add explicit local allowlists/validation for labels, edge types, and exported property keys before calling `write_node/write_relationship`.
- No raw mutation strings added.
3) `mahoun/ultra_systems/graph/ultra_graph_builder.py`
- Replace raw Cypher + `session.run(...)` export path with typed governed writes (`write_node`/`write_relationship`), `Neo4jConnection` enforcement, and local allowlists.
- Remove legacy `graph.neo4j_adapter` import/dummy adapter pattern.
- Avoid unsupported `operation_type` kwargs.

After edits, report exact files changed and key changes. Do not touch other files.

## Assistant

<thinking>
**Inspecting file paths and connections**

I’m thinking about reading files directly since the full path is known. The paths are within the root, so I can access them. I have to ensure I know the full project-relative path, like `KingMahouN/mahoun/graph/builders/entity_linker.py`. I might also need to search for the Neo4jConnection definition and any session methods. Inspecting the connection/session API will help me understand how to patch things accurately, even if I can’t edit it. I'll use grep and inspect files and symbols in parallel.
</thinking>

I’ll inspect the three target files plus the governed Neo4j APIs they depend on so I can make the hardening changes precisely.

**Tool Call: Read file `mahoun/graph/builders/entity_linker.py` (lines 1-400)**
Status: Completed

```KingMahouN/mahoun/graph/builders/entity_linker.py
     1	"""
     2	Entity Linker - Graph Normalization Layer
     3	==========================================
     4	Enterprise-grade entity linking for Neo4j graph construction.
     5	
     6	This module converts raw NER output into normalized graph structures,
     7	creating or merging nodes and building edges while ensuring semantic integrity.
     8	
     9	Responsibilities:
    10	- Convert raw NER output into normalized graph structures
    11	- Create or merge nodes (idempotent operations)
    12	- Build directional edges
    13	- Validate uniqueness and semantic integrity
    14	
    15	Operational Rules:
    16	- Idempotent operations only (safe to re-run)
    17	- Silent fail on missing entities (no ingestion-blocking exceptions)
    18	- Aligned with existing graph_rag builder patterns
    19	
    20	Usage:
    21	    from mahoun.graph.builders.entity_linker import EntityLinker, link_entities_to_graph
    22	    
    23	    # Quick linking
    24	    result = link_entities_to_graph(entities, case_id="case_001")
    25	    
    26	    # Advanced usage
    27	    linker = EntityLinker()
    28	    nodes, edges = linker.link(entities, case_id="case_001")
    29	
    30	Graph Schema Contract:
    31	    NODES:
    32	        (:Case { case_id, title, date, court, … })
    33	        (:Person { name, national_id?, normalized_name })
    34	        (:Organization { name, registration_id?, normalized_name })
    35	        (:Court { name, level, city })
    36	        (:LawArticle { code, article, clause, description })
    37	        (:Topic { label })
    38	    
    39	    EDGES:
    40	        (:Person)-[:PARTY_IN]->(:Case)
    41	        (:Organization)-[:PARTY_IN]->(:Case)
    42	        (:Case)-[:REFERS_TO]->(:LawArticle)
    43	        (:Case)-[:HANDLED_BY]->(:Court)
    44	        (:Case)-[:ABOUT]->(:Topic)
    45	"""
    46	
    47	import re
    48	import logging
    49	import hashlib
    50	from typing import Any, Dict, List, Optional, Set, Tuple
    51	from dataclasses import dataclass, field
    52	from datetime import datetime
    53	
    54	from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph
    55	
    56	logger = logging.getLogger(__name__)
    57	
    58	# ============================================================================
    59	# Node/Edge Data Classes
    60	# ============================================================================
    61	
    62	@dataclass
    63	class GraphNodeSpec:
    64	    """Specification for a graph node to be created/merged"""
    65	    label: str  # Node label (Person, Organization, Court, etc.)
    66	    node_id: str  # Unique identifier for MERGE operations
    67	    properties: Dict[str, Any] = field(default_factory=dict)
    68	    
    69	    # Metadata
    70	    source_case_id: Optional[str] = None
    71	    confidence: float = 1.0
    72	    created_at: datetime = field(default_factory=datetime.now)
    73	
    74	
    75	@dataclass
    76	class GraphEdgeSpec:
    77	    """Specification for a graph edge to be created"""
    78	    from_label: str
    79	    from_id: str
    80	    to_label: str
    81	    to_id: str
    82	    relationship_type: str
    83	    properties: Dict[str, Any] = field(default_factory=dict)
    84	    
    85	    # Metadata
    86	    confidence: float = 1.0
    87	
    88	
    89	@dataclass
    90	class LinkingResult:
    91	    """Result of entity linking operation"""
    92	    success: bool
    93	    case_id: str
    94	    nodes_created: int = 0
    95	    edges_created: int = 0
    96	    nodes_merged: int = 0
    97	    errors: List[str] = field(default_factory=list)
    98	    processing_time_ms: float = 0.0
    99	
   100	
   101	# ============================================================================
   102	# Entity Linker
   103	# ============================================================================
   104	
   105	class EntityLinker:
   106	    """
   107	    Enterprise-grade entity linker for graph construction.
   108	    
   109	    Converts NER output into normalized graph nodes and edges,
   110	    supporting idempotent MERGE operations for Neo4j.
   111	    
   112	    Features:
   113	    - Idempotent node creation (MERGE semantics)
   114	    - Automatic edge construction
   115	    - Entity normalization and deduplication
   116	    - Cross-document entity resolution (future Phase 2)
   117	    
   118	    Usage:
   119	        linker = EntityLinker()
   120	        nodes, edges = linker.link(entities, case_id="case_001")
   121	        
   122	        # Or get full result
   123	        result = linker.link_with_result(entities, case_id="case_001")
   124	    """
   125	    
   126	    def __init__(
   127	        self,
   128	        enable_normalization: bool = True,
   129	        enable_deduplication: bool = True
   130	    ):
   131	        """
   132	        Initialize Entity Linker.
   133	        
   134	        Args:
   135	            enable_normalization: Normalize entity values before linking
   136	            enable_deduplication: Remove duplicate nodes
   137	        """
   138	        self.settings = get_runtime_settings()
   139	        self.enable_normalization = enable_normalization
   140	        self.enable_deduplication = enable_deduplication
   141	        
   142	        # Statistics
   143	        self.stats = {
   144	            "total_linked": 0,
   145	            "total_nodes": 0,
   146	            "total_edges": 0,
   147	            "errors": 0
   148	        }
   149	        
   150	        logger.info("EntityLinker initialized")
   151	    
   152	    def link(
   153	        self,
   154	        entities: Dict[str, List[Dict[str, Any]]],
   155	        case_id: str,
   156	        case_metadata: Optional[Dict[str, Any]] = None
   157	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   158	        """
   159	        Link entities to graph structures.
   160	        
   161	        Args:
   162	            entities: NER output dictionary with entity lists
   163	            case_id: Unique case/document identifier
   164	            case_metadata: Optional metadata for the case node
   165	        
   166	        Returns:
   167	            Tuple of (nodes, edges) specifications
   168	        """
   169	        import time
   170	        start_time = time.time()
   171	        
   172	        # Skip in desktop-minimal mode
   173	        if should_skip_graph():
   174	            logger.debug("EntityLinker: Skipping in desktop-minimal mode")
   175	            return [], []
   176	        
   177	        nodes: List[GraphNodeSpec] = []
   178	        edges: List[GraphEdgeSpec] = []
   179	        seen_node_ids: Set[str] = set()
   180	        
   181	        try:
   182	            # Create Case node first
   183	            case_node = self._create_case_node(case_id, case_metadata)
   184	            nodes.append(case_node)
   185	            seen_node_ids.add(case_node.node_id)
   186	            
   187	            # Process each entity type
   188	            person_nodes, person_edges = self._link_persons(
   189	                entities.get("persons", []), case_id, seen_node_ids
   190	            )
   191	            nodes.extend(person_nodes)
   192	            edges.extend(person_edges)
   193	            
   194	            org_nodes, org_edges = self._link_organizations(
   195	                entities.get("organizations", []), case_id, seen_node_ids
   196	            )
   197	            nodes.extend(org_nodes)
   198	            edges.extend(org_edges)
   199	            
   200	            court_nodes, court_edges = self._link_courts(
   201	                entities.get("courts", []), case_id, seen_node_ids
   202	            )
   203	            nodes.extend(court_nodes)
   204	            edges.extend(court_edges)
   205	            
   206	            law_nodes, law_edges = self._link_laws(
   207	                entities.get("laws", []), case_id, seen_node_ids
   208	            )
   209	            nodes.extend(law_nodes)
   210	            edges.extend(law_edges)
   211	            
   212	            topic_nodes, topic_edges = self._link_topics(
   213	                entities.get("topics", []), case_id, seen_node_ids
   214	            )
   215	            nodes.extend(topic_nodes)
   216	            edges.extend(topic_edges)
   217	            
   218	            # Update statistics
   219	            processing_time_ms = (time.time() - start_time) * 1000
   220	            self._update_stats(len(nodes), len(edges), processing_time_ms)
   221	            
   222	            logger.info(
   223	                f"NER_PIPELINE: Linked entities for case {case_id} - "
   224	                f"nodes={len(nodes)}, edges={len(edges)} "
   225	                f"({processing_time_ms:.1f}ms)"
   226	            )
   227	            
   228	        except Exception as e:
   229	            logger.error(f"EntityLinker error for case {case_id}: {e}")
   230	            self.stats["errors"] += 1
   231	            # Silent fail - return what we have
   232	        
   233	        return nodes, edges
   234	    
   235	    def link_with_result(
   236	        self,
   237	        entities: Dict[str, List[Dict[str, Any]]],
   238	        case_id: str,
   239	        case_metadata: Optional[Dict[str, Any]] = None
   240	    ) -> LinkingResult:
   241	        """
   242	        Link entities and return detailed result.
   243	        
   244	        Args:
   245	            entities: NER output dictionary
   246	            case_id: Case identifier
   247	            case_metadata: Optional case metadata
   248	        
   249	        Returns:
   250	            LinkingResult with statistics
   251	        """
   252	        import time
   253	        start_time = time.time()
   254	        
   255	        nodes, edges = self.link(entities, case_id, case_metadata)
   256	        
   257	        processing_time_ms = (time.time() - start_time) * 1000
   258	        
   259	        return LinkingResult(
   260	            success=True,
   261	            case_id=case_id,
   262	            nodes_created=len(nodes),
   263	            edges_created=len(edges),
   264	            processing_time_ms=processing_time_ms
   265	        )
   266	    
   267	    # ========================================================================
   268	    # Entity Type Processors
   269	    # ========================================================================
   270	    
   271	    def _create_case_node(
   272	        self,
   273	        case_id: str,
   274	        metadata: Optional[Dict[str, Any]] = None
   275	    ) -> GraphNodeSpec:
   276	        """Create Case node specification"""
   277	        properties = {
   278	            "case_id": case_id,
   279	            "created_at": datetime.now().isoformat()
   280	        }
   281	        
   282	        if metadata:
   283	            # Add relevant metadata
   284	            if metadata.get("case_type"):
   285	                properties["case_type"] = metadata["case_type"]
   286	            if metadata.get("court_level"):
   287	                properties["court_level"] = metadata["court_level"]
   288	            if metadata.get("is_final") is not None:
   289	                properties["is_final"] = metadata["is_final"]
   290	            if metadata.get("decision_date"):
   291	                properties["decision_date"] = metadata["decision_date"]
   292	        
   293	        return GraphNodeSpec(
   294	            label="Case",
   295	            node_id=f"case_{case_id}",
   296	            properties=properties,
   297	            source_case_id=case_id
   298	        )
   299	    
   300	    def _link_persons(
   301	        self,
   302	        persons: List[Dict[str, Any]],
   303	        case_id: str,
   304	        seen_ids: Set[str]
   305	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   306	        """Link person entities to graph"""
   307	        nodes: List[Any] = []
   308	        edges: List[Any] = []
   309	        for person in persons:
   310	            try:
   311	                # Generate unique node ID
   312	                name = person.get("name", "")
   313	                normalized_name = person.get("normalized_name") or self._normalize_string(name)
   314	                node_id = self._generate_person_id(normalized_name, person.get("national_id"))
   315	                
   316	                if node_id in seen_ids:
   317	                    continue
   318	                seen_ids.add(node_id)
   319	                
   320	                # Create node
   321	                properties = {
   322	                    "name": name,
   323	                    "normalized_name": normalized_name,
   324	                }
   325	                
   326	                if person.get("title"):
   327	                    properties["title"] = person["title"]
   328	                if person.get("father_name"):
   329	                    properties["father_name"] = person["father_name"]
   330	                if person.get("national_id"):
   331	                    properties["national_id"] = person["national_id"]
   332	                if person.get("role"):
   333	                    properties["role"] = person["role"]
   334	                
   335	                nodes.append(GraphNodeSpec(
   336	                    label="Person",
   337	                    node_id=node_id,
   338	                    properties=properties,
   339	                    source_case_id=case_id,
   340	                    confidence=person.get("confidence", 0.9)
   341	                ))
   342	                
   343	                # Create edge to case
   344	                edge_props: Dict[str, Any] = {}
   345	                if person.get("role"):
   346	                    edge_props["role"] = person["role"]
   347	                
   348	                edges.append(GraphEdgeSpec(
   349	                    from_label="Person",
   350	                    from_id=node_id,
   351	                    to_label="Case",
   352	                    to_id=f"case_{case_id}",
   353	                    relationship_type="PARTY_IN",
   354	                    properties=edge_props,
   355	                    confidence=person.get("confidence", 0.9)
   356	                ))
   357	                
   358	            except Exception as e:
   359	                logger.warning(f"Failed to link person: {e}")
   360	                continue
   361	        
   362	        return nodes, edges
   363	    
   364	    def _link_organizations(
   365	        self,
   366	        organizations: List[Dict[str, Any]],
   367	        case_id: str,
   368	        seen_ids: Set[str]
   369	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   370	        """Link organization entities to graph"""
   371	        nodes: List[Any] = []
   372	        edges: List[Any] = []
   373	        for org in organizations:
   374	            try:
   375	                name = org.get("name", "")
   376	                normalized_name = org.get("normalized_name") or self._normalize_string(name)
   377	                node_id = self._generate_org_id(normalized_name, org.get("registration_id"))
   378	                
   379	                if node_id in seen_ids:
   380	                    continue
   381	                seen_ids.add(node_id)
   382	                
   383	                properties = {
   384	                    "name": name,
   385	                    "normalized_name": normalized_name,
   386	                }
   387	                
   388	                if org.get("org_type"):
   389	                    properties["org_type"] = org["org_type"]
   390	                if org.get("registration_id"):
   391	                    properties["registration_id"] = org["registration_id"]
   392	                
   393	                nodes.append(GraphNodeSpec(
   394	                    label="Organization",
   395	                    node_id=node_id,
   396	                    properties=properties,
   397	                    source_case_id=case_id,
   398	                    confidence=org.get("confidence", 0.85)
   399	                ))
   400	                

```


**Tool Call: Read file `mahoun/graph/ultra_graph_builder.py` (lines 1-400)**
Status: Completed

```KingMahouN/mahoun/graph/ultra_graph_builder.py
     1	"""
     2	Ultra-Advanced Graph Builder
     3	============================
     4	Enterprise-grade knowledge graph construction and management.
     5	
     6	Features:
     7	- Multi-source graph construction
     8	- Real-time graph updates
     9	- Graph neural network integration
    10	- Distributed graph processing
    11	- Graph quality assessment
    12	- Automated graph validation
    13	- Graph versioning and rollback
    14	- Cross-domain graph linking
    15	- Graph analytics and insights
    16	- Performance optimization
    17	"""
    18	
    19	import time
    20	import json
    21	import logging
    22	from enum import Enum
    23	from typing import Any, Dict, List, Optional, Set, Tuple
    24	from dataclasses import dataclass, field
    25	from datetime import datetime
    26	from collections import defaultdict, deque, Counter
    27	from types import MappingProxyType
    28	
    29	try:
    30	    import numpy as np
    31	
    32	    HAS_NUMPY = True
    33	except ImportError:
    34	    np = None  # type: ignore
    35	    HAS_NUMPY = False
    36	
    37	from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph
    38	from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    39	
    40	logger = logging.getLogger(__name__)
    41	
    42	
    43	# ============================================================================
    44	# Graph Operation Modes
    45	# ============================================================================
    46	
    47	
    48	class GraphMode(str, Enum):
    49	    """
    50	    Graph operation modes for different use cases.
    51	
    52	    Modes:
    53	    - STRICT: Full validation, fail on any errors (production, high-stakes)
    54	    - PERMISSIVE: Log warnings but continue (development, exploratory)
    55	    - MINIMAL: Skip heavy operations, minimal resource usage (laptop, CI)
    56	    """
    57	
    58	    STRICT = "strict"
    59	    PERMISSIVE = "permissive"
    60	    MINIMAL = "minimal"
    61	
    62	
    63	# Try to import Neo4j adapter
    64	try:
    65	    from mahoun.graph.neo4j_adapter import Neo4jAdapter
    66	
    67	    HAS_NEO4J = True
    68	except ImportError:
    69	    Neo4jAdapter = object  # Dummy class for type hints
    70	    HAS_NEO4J = False
    71	
    72	# ============================================================================
    73	# Graph Data Structures
    74	# ============================================================================
    75	
    76	
    77	@dataclass
    78	class GraphNode:
    79	    """Enhanced graph node with provenance"""
    80	
    81	    id: str
    82	    label: str
    83	    node_type: str
    84	    provenance: ProvenanceMetadata
    85	    properties: Dict[str, Any] = field(default_factory=dict)
    86	
    87	    # Advanced features
    88	    confidence: float = 1.0
    89	    source_documents: List[str] = field(default_factory=list)
    90	    created_at: datetime = field(default_factory=datetime.now)
    91	    updated_at: datetime = field(default_factory=datetime.now)
    92	
    93	    # Quality metrics
    94	    quality_score: float = 0.0
    95	    validation_status: str = "pending"
    96	
    97	
    98	@dataclass
    99	class GraphEdge:
   100	    """Enhanced graph edge"""
   101	
   102	    source_id: str
   103	    target_id: str
   104	    relationship_type: str
   105	    properties: Dict[str, Any] = field(default_factory=dict)
   106	
   107	    # Advanced features
   108	    weight: float = 1.0
   109	    confidence: float = 1.0
   110	    evidence: List[str] = field(default_factory=list)
   111	    created_at: datetime = field(default_factory=datetime.now)
   112	
   113	    # Quality metrics
   114	    quality_score: float = 0.0
   115	    validation_status: str = "pending"
   116	
   117	
   118	@dataclass
   119	class GraphMetrics:
   120	    """Graph quality and performance metrics"""
   121	
   122	    total_nodes: int = 0
   123	    total_edges: int = 0
   124	    avg_degree: float = 0.0
   125	    clustering_coefficient: float = 0.0
   126	    density: float = 0.0
   127	
   128	    # Quality metrics
   129	    avg_node_quality: float = 0.0
   130	    avg_edge_quality: float = 0.0
   131	    validation_rate: float = 0.0
   132	
   133	    # Performance metrics
   134	    build_time_seconds: float = 0.0
   135	    memory_usage_mb: float = 0.0
   136	    query_latency_ms: float = 0.0
   137	
   138	
   139	# ============================================================================
   140	# Graph Quality Assessor
   141	# ============================================================================
   142	
   143	
   144	class GraphQualityAssessor:
   145	    """Assess and improve graph quality"""
   146	
   147	    def __init__(self):
   148	        self.quality_rules = self._build_quality_rules()
   149	        logger.debug("Graph Quality Assessor initialized")
   150	
   151	    def assess_graph_quality(
   152	        self, nodes: List[GraphNode], edges: List[GraphEdge]
   153	    ) -> GraphMetrics:
   154	        """Assess overall graph quality"""
   155	        metrics = GraphMetrics()
   156	
   157	        # Basic metrics
   158	        metrics.total_nodes = len(nodes)
   159	        metrics.total_edges = len(edges)
   160	
   161	        if nodes:
   162	            # Degree distribution
   163	            degree_count = defaultdict(int)
   164	            for edge in edges:
   165	                degree_count[edge.source_id] += 1
   166	                degree_count[edge.target_id] += 1
   167	
   168	            degrees = list(degree_count.values())
   169	            metrics.avg_degree = sum(degrees) / len(degrees) if degrees else 0
   170	
   171	            # Density
   172	            max_edges = len(nodes) * (len(nodes) - 1) / 2
   173	            metrics.density = len(edges) / max_edges if max_edges > 0 else 0
   174	
   175	            # Quality scores
   176	            node_qualities = [self._assess_node_quality(node) for node in nodes]
   177	            edge_qualities = [self._assess_edge_quality(edge) for edge in edges]
   178	
   179	            metrics.avg_node_quality = (
   180	                sum(node_qualities) / len(node_qualities) if node_qualities else 0
   181	            )
   182	            metrics.avg_edge_quality = (
   183	                sum(edge_qualities) / len(edge_qualities) if edge_qualities else 0
   184	            )
   185	
   186	            # Validation rate
   187	            validated_nodes = sum(
   188	                1 for node in nodes if node.validation_status == "validated"
   189	            )
   190	            validated_edges = sum(
   191	                1 for edge in edges if edge.validation_status == "validated"
   192	            )
   193	
   194	            total_elements = len(nodes) + len(edges)
   195	            validated_elements = validated_nodes + validated_edges
   196	
   197	            metrics.validation_rate = (
   198	                validated_elements / total_elements if total_elements > 0 else 0
   199	            )
   200	
   201	        return metrics
   202	
   203	    def _assess_node_quality(self, node: GraphNode) -> float:
   204	        """Assess individual node quality"""
   205	        score = 0.5  # Base score
   206	
   207	        # Check properties completeness
   208	        if node.properties:
   209	            score += 0.2
   210	
   211	        # Check confidence
   212	        score += 0.2 * node.confidence
   213	
   214	        # Check source documents
   215	        if node.source_documents:
   216	            score += 0.1
   217	
   218	        return min(1.0, score)
   219	
   220	    def _assess_edge_quality(self, edge: GraphEdge) -> float:
   221	        """Assess individual edge quality"""
   222	        score = 0.5  # Base score
   223	
   224	        # Check confidence
   225	        score += 0.3 * edge.confidence
   226	
   227	        # Check evidence
   228	        if edge.evidence:
   229	            score += 0.2
   230	
   231	        return min(1.0, score)
   232	
   233	    def _build_quality_rules(self) -> List[Dict]:
   234	        """Build quality assessment rules"""
   235	        return [
   236	            {
   237	                "name": "node_completeness",
   238	                "description": "Nodes should have complete properties",
   239	                "weight": 0.3,
   240	            },
   241	            {
   242	                "name": "edge_evidence",
   243	                "description": "Edges should have supporting evidence",
   244	                "weight": 0.4,
   245	            },
   246	            {
   247	                "name": "confidence_threshold",
   248	                "description": "Elements should meet confidence threshold",
   249	                "weight": 0.3,
   250	            },
   251	        ]
   252	
   253	
   254	# ============================================================================
   255	# Graph Analytics Engine
   256	# ============================================================================
   257	
   258	
   259	class GraphAnalyticsEngine:
   260	    """Advanced graph analytics"""
   261	
   262	    def __init__(self):
   263	        logger.debug("Graph Analytics Engine initialized")
   264	
   265	    def compute_centrality(
   266	        self, nodes: List[GraphNode], edges: List[GraphEdge]
   267	    ) -> Dict[str, float]:
   268	        """Compute node centrality scores"""
   269	        # Build adjacency list
   270	        adjacency = defaultdict(list)
   271	        for edge in edges:
   272	            adjacency[edge.source_id].append(edge.target_id)
   273	            adjacency[edge.target_id].append(edge.source_id)
   274	
   275	        # Compute degree centrality
   276	        centrality: Dict[str, Any] = {}
   277	        max_degree = len(nodes) - 1 if len(nodes) > 1 else 1
   278	
   279	        for node in nodes:
   280	            degree = len(adjacency[node.id])
   281	            centrality[node.id] = degree / max_degree
   282	
   283	        return centrality
   284	
   285	    def find_communities(
   286	        self, nodes: List[GraphNode], edges: List[GraphEdge]
   287	    ) -> Dict[str, int]:
   288	        """Detect communities in graph"""
   289	        # Simplified community detection using connected components
   290	        adjacency = defaultdict(set)
   291	        for edge in edges:
   292	            adjacency[edge.source_id].add(edge.target_id)
   293	            adjacency[edge.target_id].add(edge.source_id)
   294	
   295	        communities: Dict[str, Any] = {}
   296	        visited = set()
   297	        community_id = 0
   298	
   299	        for node in nodes:
   300	            if node.id not in visited:
   301	                # BFS to find connected component
   302	                queue = deque([node.id])
   303	                visited.add(node.id)
   304	
   305	                while queue:
   306	                    current = queue.popleft()
   307	                    communities[current] = community_id
   308	
   309	                    for neighbor in adjacency[current]:
   310	                        if neighbor not in visited:
   311	                            visited.add(neighbor)
   312	                            queue.append(neighbor)
   313	
   314	                community_id += 1
   315	
   316	        return communities
   317	
   318	    def compute_shortest_paths(
   319	        self, nodes: List[GraphNode], edges: List[GraphEdge], source_id: str
   320	    ) -> Dict[str, int]:
   321	        """Compute shortest paths from source node"""
   322	        # Build adjacency list
   323	        adjacency = defaultdict(list)
   324	        for edge in edges:
   325	            adjacency[edge.source_id].append(edge.target_id)
   326	            adjacency[edge.target_id].append(edge.source_id)
   327	
   328	        # BFS for shortest paths
   329	        distances = {source_id: 0}
   330	        queue = deque([source_id])
   331	
   332	        while queue:
   333	            current = queue.popleft()
   334	            current_dist = distances[current]
   335	
   336	            for neighbor in adjacency[current]:
   337	                if neighbor not in distances:
   338	                    distances[neighbor] = current_dist + 1
   339	                    queue.append(neighbor)
   340	
   341	        return distances
   342	
   343	
   344	# ============================================================================
   345	# Ultra Graph Builder
   346	# ============================================================================
   347	
   348	
   349	class UltraGraphBuilder:
   350	    """
   351	    Ultra-advanced graph builder
   352	
   353	    Features:
   354	    - Multi-source construction
   355	    - Real-time updates
   356	    - Quality assessment
   357	    - Advanced analytics
   358	    - Performance optimization
   359	    """
   360	
   361	    def __init__(
   362	        self,
   363	        enable_quality_assessment: bool = True,
   364	        enable_analytics: bool = True,
   365	        enable_real_time_updates: bool = True,
   366	        batch_size: int = 1000,
   367	        mode: Optional[GraphMode] = None,
   368	    ):
   369	        # Runtime settings (mode-aware configuration)
   370	        self.settings = get_runtime_settings()
   371	
   372	        # Determine mode (explicit > runtime config > default)
   373	        if mode is None:
   374	            if should_skip_graph():
   375	                mode = GraphMode.MINIMAL
   376	            else:
   377	                mode = GraphMode.STRICT
   378	
   379	        self.mode = mode
   380	
   381	        # Mode-specific configuration
   382	        if self.mode == GraphMode.MINIMAL:
   383	            logger.info(
   384	                "MINIMAL mode: graph builder initialized with minimal operations"
   385	            )
   386	            enable_quality_assessment = False
   387	            enable_analytics = False
   388	            enable_real_time_updates = False
   389	        elif self.mode == GraphMode.PERMISSIVE:
   390	            logger.info("PERMISSIVE mode: graph builder will log warnings but continue")
   391	        elif self.mode == GraphMode.STRICT:
   392	            logger.info("STRICT mode: graph builder will fail on any errors")
   393	
   394	        self.enable_quality_assessment = enable_quality_assessment
   395	        self.enable_analytics = enable_analytics
   396	        self.enable_real_time_updates = enable_real_time_updates
   397	        self.batch_size = batch_size
   398	
   399	        # Components
   400	        if enable_quality_assessment:

```


**Tool Call: Read file `mahoun/ultra_systems/graph/ultra_graph_builder.py` (lines 1-400)**
Status: Completed

```KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py
     1	"""
     2	Ultra-Advanced Graph Builder
     3	============================
     4	Enterprise-grade knowledge graph construction and management.
     5	
     6	Features:
     7	- Multi-source graph construction
     8	- Real-time graph updates
     9	- Graph neural network integration
    10	- Distributed graph processing
    11	- Graph quality assessment
    12	- Automated graph validation
    13	- Graph versioning and rollback
    14	- Cross-domain graph linking
    15	- Graph analytics and insights
    16	- Performance optimization
    17	"""
    18	
    19	import time
    20	import json
    21	import numpy as np
    22	from typing import List, Dict, Optional, Tuple, Set, Any
    23	from dataclasses import dataclass, field
    24	from datetime import datetime
    25	from collections import defaultdict, deque, Counter
    26	
    27	# Try to import Neo4j adapter
    28	try:
    29	    from graph.neo4j_adapter import Neo4jAdapter
    30	    HAS_NEO4J = True
    31	except ImportError:
    32	    Neo4jAdapter = object  # Dummy class for type hints
    33	    HAS_NEO4J = False
    34	
    35	# ============================================================================
    36	# Graph Data Structures
    37	# ============================================================================
    38	
    39	@dataclass
    40	class GraphNode:
    41	    """Enhanced graph node"""
    42	    id: str
    43	    label: str
    44	    node_type: str
    45	    properties: Dict[str, Any] = field(default_factory=dict)
    46	    
    47	    # Advanced features
    48	    confidence: float = 1.0
    49	    source_documents: List[str] = field(default_factory=list)
    50	    created_at: datetime = field(default_factory=datetime.now)
    51	    updated_at: datetime = field(default_factory=datetime.now)
    52	    
    53	    # Quality metrics
    54	    quality_score: float = 0.0
    55	    validation_status: str = "pending"
    56	
    57	
    58	@dataclass
    59	class GraphEdge:
    60	    """Enhanced graph edge"""
    61	    source_id: str
    62	    target_id: str
    63	    relationship_type: str
    64	    properties: Dict[str, Any] = field(default_factory=dict)
    65	    
    66	    # Advanced features
    67	    weight: float = 1.0
    68	    confidence: float = 1.0
    69	    evidence: List[str] = field(default_factory=list)
    70	    created_at: datetime = field(default_factory=datetime.now)
    71	    
    72	    # Quality metrics
    73	    quality_score: float = 0.0
    74	    validation_status: str = "pending"
    75	
    76	
    77	@dataclass
    78	class GraphMetrics:
    79	    """Graph quality and performance metrics"""
    80	    total_nodes: int = 0
    81	    total_edges: int = 0
    82	    avg_degree: float = 0.0
    83	    clustering_coefficient: float = 0.0
    84	    density: float = 0.0
    85	    
    86	    # Quality metrics
    87	    avg_node_quality: float = 0.0
    88	    avg_edge_quality: float = 0.0
    89	    validation_rate: float = 0.0
    90	    
    91	    # Performance metrics
    92	    build_time_seconds: float = 0.0
    93	    memory_usage_mb: float = 0.0
    94	    query_latency_ms: float = 0.0
    95	
    96	
    97	# ============================================================================
    98	# Graph Quality Assessor
    99	# ============================================================================
   100	
   101	class GraphQualityAssessor:
   102	    """Assess and improve graph quality"""
   103	    
   104	    def __init__(self):
   105	        self.quality_rules = self._build_quality_rules()
   106	        print("📊 Graph Quality Assessor initialized")
   107	    
   108	    def assess_graph_quality(
   109	        self,
   110	        nodes: List[GraphNode],
   111	        edges: List[GraphEdge]
   112	    ) -> GraphMetrics:
   113	        """Assess overall graph quality"""
   114	        metrics = GraphMetrics()
   115	        
   116	        # Basic metrics
   117	        metrics.total_nodes = len(nodes)
   118	        metrics.total_edges = len(edges)
   119	        
   120	        if nodes:
   121	            # Degree distribution
   122	            degree_count = defaultdict(int)
   123	            for edge in edges:
   124	                degree_count[edge.source_id] += 1
   125	                degree_count[edge.target_id] += 1
   126	            
   127	            degrees = list(degree_count.values())
   128	            metrics.avg_degree = sum(degrees) / len(degrees) if degrees else 0
   129	            
   130	            # Density
   131	            max_edges = len(nodes) * (len(nodes) - 1) / 2
   132	            metrics.density = len(edges) / max_edges if max_edges > 0 else 0
   133	            
   134	            # Quality scores
   135	            node_qualities = [self._assess_node_quality(node) for node in nodes]
   136	            edge_qualities = [self._assess_edge_quality(edge) for edge in edges]
   137	            
   138	            metrics.avg_node_quality = sum(node_qualities) / len(node_qualities) if node_qualities else 0
   139	            metrics.avg_edge_quality = sum(edge_qualities) / len(edge_qualities) if edge_qualities else 0
   140	            
   141	            # Validation rate
   142	            validated_nodes = sum(1 for node in nodes if node.validation_status == "validated")
   143	            validated_edges = sum(1 for edge in edges if edge.validation_status == "validated")
   144	            
   145	            total_elements = len(nodes) + len(edges)
   146	            validated_elements = validated_nodes + validated_edges
   147	            
   148	            metrics.validation_rate = validated_elements / total_elements if total_elements > 0 else 0
   149	        
   150	        return metrics
   151	    
   152	    def _assess_node_quality(self, node: GraphNode) -> float:
   153	        """Assess individual node quality"""
   154	        score = 0.5  # Base score
   155	        
   156	        # Check properties completeness
   157	        if node.properties:
   158	            score += 0.2
   159	        
   160	        # Check confidence
   161	        score += 0.2 * node.confidence
   162	        
   163	        # Check source documents
   164	        if node.source_documents:
   165	            score += 0.1
   166	        
   167	        return min(1.0, score)
   168	    
   169	    def _assess_edge_quality(self, edge: GraphEdge) -> float:
   170	        """Assess individual edge quality"""
   171	        score = 0.5  # Base score
   172	        
   173	        # Check confidence
   174	        score += 0.3 * edge.confidence
   175	        
   176	        # Check evidence
   177	        if edge.evidence:
   178	            score += 0.2
   179	        
   180	        return min(1.0, score)
   181	    
   182	    def _build_quality_rules(self) -> List[Dict]:
   183	        """Build quality assessment rules"""
   184	        return [
   185	            {
   186	                "name": "node_completeness",
   187	                "description": "Nodes should have complete properties",
   188	                "weight": 0.3,
   189	            },
   190	            {
   191	                "name": "edge_evidence",
   192	                "description": "Edges should have supporting evidence",
   193	                "weight": 0.4,
   194	            },
   195	            {
   196	                "name": "confidence_threshold",
   197	                "description": "Elements should meet confidence threshold",
   198	                "weight": 0.3,
   199	            },
   200	        ]
   201	
   202	
   203	# ============================================================================
   204	# Graph Analytics Engine
   205	# ============================================================================
   206	
   207	class GraphAnalyticsEngine:
   208	    """Advanced graph analytics"""
   209	    
   210	    def __init__(self):
   211	        print("📈 Graph Analytics Engine initialized")
   212	    
   213	    def compute_centrality(
   214	        self,
   215	        nodes: List[GraphNode],
   216	        edges: List[GraphEdge]
   217	    ) -> Dict[str, float]:
   218	        """Compute node centrality scores"""
   219	        # Build adjacency list
   220	        adjacency = defaultdict(list)
   221	        for edge in edges:
   222	            adjacency[edge.source_id].append(edge.target_id)
   223	            adjacency[edge.target_id].append(edge.source_id)
   224	        
   225	        # Compute degree centrality
   226	        centrality = {}
   227	        max_degree = len(nodes) - 1 if len(nodes) > 1 else 1
   228	        
   229	        for node in nodes:
   230	            degree = len(adjacency[node.id])
   231	            centrality[node.id] = degree / max_degree
   232	        
   233	        return centrality
   234	    
   235	    def find_communities(
   236	        self,
   237	        nodes: List[GraphNode],
   238	        edges: List[GraphEdge]
   239	    ) -> Dict[str, int]:
   240	        """Detect communities in graph"""
   241	        # Simplified community detection using connected components
   242	        adjacency = defaultdict(set)
   243	        for edge in edges:
   244	            adjacency[edge.source_id].add(edge.target_id)
   245	            adjacency[edge.target_id].add(edge.source_id)
   246	        
   247	        communities = {}
   248	        visited = set()
   249	        community_id = 0
   250	        
   251	        for node in nodes:
   252	            if node.id not in visited:
   253	                # BFS to find connected component
   254	                queue = deque([node.id])
   255	                visited.add(node.id)
   256	                
   257	                while queue:
   258	                    current = queue.popleft()
   259	                    communities[current] = community_id
   260	                    
   261	                    for neighbor in adjacency[current]:
   262	                        if neighbor not in visited:
   263	                            visited.add(neighbor)
   264	                            queue.append(neighbor)
   265	                
   266	                community_id += 1
   267	        
   268	        return communities
   269	    
   270	    def compute_shortest_paths(
   271	        self,
   272	        nodes: List[GraphNode],
   273	        edges: List[GraphEdge],
   274	        source_id: str
   275	    ) -> Dict[str, int]:
   276	        """Compute shortest paths from source node"""
   277	        # Build adjacency list
   278	        adjacency = defaultdict(list)
   279	        for edge in edges:
   280	            adjacency[edge.source_id].append(edge.target_id)
   281	            adjacency[edge.target_id].append(edge.source_id)
   282	        
   283	        # BFS for shortest paths
   284	        distances = {source_id: 0}
   285	        queue = deque([source_id])
   286	        
   287	        while queue:
   288	            current = queue.popleft()
   289	            current_dist = distances[current]
   290	            
   291	            for neighbor in adjacency[current]:
   292	                if neighbor not in distances:
   293	                    distances[neighbor] = current_dist + 1
   294	                    queue.append(neighbor)
   295	        
   296	        return distances
   297	
   298	
   299	# ============================================================================
   300	# Ultra Graph Builder
   301	# ============================================================================
   302	
   303	class UltraGraphBuilder:
   304	    """
   305	    Ultra-advanced graph builder
   306	    
   307	    Features:
   308	    - Multi-source construction
   309	    - Real-time updates
   310	    - Quality assessment
   311	    - Advanced analytics
   312	    - Performance optimization
   313	    """
   314	    
   315	    def __init__(
   316	        self,
   317	        enable_quality_assessment: bool = True,
   318	        enable_analytics: bool = True,
   319	        enable_real_time_updates: bool = True,
   320	        batch_size: int = 1000,
   321	    ):
   322	        self.enable_quality_assessment = enable_quality_assessment
   323	        self.enable_analytics = enable_analytics
   324	        self.enable_real_time_updates = enable_real_time_updates
   325	        self.batch_size = batch_size
   326	        
   327	        # Components
   328	        if enable_quality_assessment:
   329	            self.quality_assessor = GraphQualityAssessor()
   330	        
   331	        if enable_analytics:
   332	            self.analytics_engine = GraphAnalyticsEngine()
   333	        
   334	        # Graph storage
   335	        self.nodes: Dict[str, GraphNode] = {}
   336	        self.edges: List[GraphEdge] = []
   337	        
   338	        # Indexes
   339	        self.node_index = {}  # For fast lookup
   340	        self.edge_index = defaultdict(list)  # Adjacency list
   341	        
   342	        # Update queue for real-time processing
   343	        self.update_queue = deque()
   344	        
   345	        # Statistics
   346	        self.stats = {
   347	            "total_builds": 0,
   348	            "total_updates": 0,
   349	            "avg_build_time": 0.0,
   350	            "quality_improvements": 0,
   351	        }
   352	        
   353	        print("🏗️ Ultra Graph Builder initialized")
   354	    
   355	    def build_graph(
   356	        self,
   357	        entities: List[Dict],
   358	        relationships: List[Dict],
   359	        source_id: Optional[str] = None,
   360	    ) -> Dict[str, Any]:
   361	        """
   362	        Build graph from entities and relationships
   363	        
   364	        Args:
   365	            entities: List of entities
   366	            relationships: List of relationships
   367	            source_id: Source document/dataset ID
   368	        
   369	        Returns:
   370	            Graph build result
   371	        """
   372	        start_time = time.time()
   373	        
   374	        print(f"🏗️ Building graph with {len(entities)} entities and {len(relationships)} relationships...")
   375	        
   376	        # Process entities
   377	        self._process_entities(entities, source_id)
   378	        
   379	        # Process relationships
   380	        self._process_relationships(relationships, source_id)
   381	        
   382	        # Quality assessment
   383	        if self.enable_quality_assessment:
   384	            self._assess_and_improve_quality()
   385	        
   386	        # Build indexes
   387	        self._build_indexes()
   388	        
   389	        # Calculate metrics
   390	        metrics = self._calculate_metrics()
   391	        
   392	        build_time = time.time() - start_time
   393	        metrics.build_time_seconds = build_time
   394	        
   395	        # Update statistics
   396	        self.stats["total_builds"] += 1
   397	        self.stats["avg_build_time"] = (
   398	            (self.stats["avg_build_time"] * (self.stats["total_builds"] - 1) + build_time)
   399	            / self.stats["total_builds"]
   400	        )

```


**Tool Call: Search files for regex `class\s+Neo4jConnection|def\s+governed_session|def\s+write_node|def\s+write_relationship|class\s+GovernedNeo4jSession`**
Status: Completed

Found 12 matches:

## Matches in KingMahouN/.test_classification_backup/tests/governance/test_hardened_infrastructure.py

### def governed_session › L84-93
```
def governed_session(mock_raw_executor):
    """Create a governed session with mock validation pipeline."""
    pipeline = ValidatorPipeline()
    session = GovernedNeo4jSession(
        raw_executor=mock_raw_executor,
        pipeline=pipeline,
        correlation_id="test-corr-id-999",
        actor_id="test_actor",
    )
    return session
```

## Matches in KingMahouN/mahoun/bootstrap/runtime.py

### def bootstrap_runtime › def governed_session_factory › L89-93
```
    # GNNGraphBuilder: session_factory is the governed Neo4j write surface.
    # Bootstrap owns this factory — GNNGraphBuilder never creates connections itself.
    def governed_session_factory():
        return get_connection().governed_session()

```

## Matches in KingMahouN/mahoun/core/governance/mutation_boundary.py

### class GovernedNeo4jSession › L365-375
```
class GovernedNeo4jSession:
    """
    The ONLY surface through which mutation Cypher may reach Neo4j.

    Callers do NOT get raw session access.
    They call typed write methods (write_node, write_relationship).
    Each call:
        1. Validates provenance via ValidatorPipeline (fail-closed)
        2. Validates ontology via ValidatorPipeline (fail-closed)
        3. Sets the thread-local authorization flag
        4. Executes the pre-built Cypher
```

472 lines remaining in ancestor node. Read the file to see all.

### class GovernedNeo4jSession › def write_node › L452-456
```
    # ------------------------------------------------------------------

    def write_node(
        self,
        label: str,
```

### class GovernedNeo4jSession › def write_relationship › L569-573
```
        return receipt

    def write_relationship(
        self,
        source_type: str,
```

## Matches in KingMahouN/mahoun/core/governance/protocols.py

### class GovernedGraphSession › def write_node › L61-65
```
    """

    def write_node(
        self,
        label: str,
```

### class GovernedGraphSession › def write_relationship › L70-74
```
        ...

    def write_relationship(
        self,
        source_type: str,
```

## Matches in KingMahouN/mahoun/graph/graph_query_service.py

### class Neo4jConnectionManager › L332-342
```
class Neo4jConnectionManager:
    """
    Connection manager for governance-compliant graph queries.
    
    All queries MUST go through governed_session. Direct driver usage is forbidden.
    """
    
    _instance: Optional["Neo4jConnectionManager"] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
```

305 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/graph/neo4j/connection.py

### class Neo4jConnection › L71-81
```
class Neo4jConnection:
    """
    Thread-safe Neo4j connection with connection pooling
    
    Features:
    - Thread-safe singleton pattern via ThreadSafeSingleton
    - Connection pooling
    - Automatic reconnection
    - Configuration from file or env
    - Health checks
    
```

400 lines remaining in ancestor node. Read the file to see all.

### class Neo4jConnection › def governed_session › L249-259
```
    @contextmanager
    def governed_session(
        self,
        pipeline: Optional["ValidatorPipeline"] = None,
        correlation_id: str = "",
        actor_id: str = "",
    ) -> Generator["GovernedNeo4jSession", None, None]:
        """
        The ONLY authorized entry point for graph mutation.

        Yields a GovernedNeo4jSession which is the only surface that
```

31 lines remaining in ancestor node. Read the file to see all.

### class Neo4jConnectionPool › L484-494
```
class Neo4jConnectionPool:
    """
    Connection pool manager for Neo4j
    
    Uses Neo4j driver's built-in connection pooling for high-throughput scenarios.
    This is a lightweight wrapper that leverages the driver's native pool management.
    """
    
    def __init__(
        self,
        uri: str,
```

62 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/tests/governance/test_hardened_infrastructure.py

### def governed_session › L87-96
```
def governed_session(mock_raw_executor):
    """Create a governed session with mock validation pipeline."""
    pipeline = ValidatorPipeline()
    session = GovernedNeo4jSession(
        raw_executor=mock_raw_executor,
        pipeline=pipeline,
        correlation_id="test-corr-id-999",
        actor_id="test_actor",
    )
    return session
```


**Tool Call: Search files for regex `Neo4jAdapter|neo4j_adapter`**
Status: Completed

Found 8 matches:

## Matches in KingMahouN/mahoun/graph/builders/entity_linker.py

### def link_and_submit › L881-886
```
def link_and_submit(
    entities: Dict[str, List[Dict[str, Any]]],
    case_id: str,
    case_metadata: Optional[Dict[str, Any]] = None,
    neo4j_adapter=None
) -> LinkingResult:
```

### def link_and_submit › L887-897
```
    """
    Link entities and optionally submit to Neo4j.
    
    Args:
        entities: NER output
        case_id: Case identifier
        case_metadata: Optional case metadata
        neo4j_adapter: Optional Neo4j adapter for direct submission (must be Neo4jConnection)
    
    Returns:
        LinkingResult with statistics
```

1 lines remaining in ancestor node. Read the file to see all.

### def link_and_submit › L900-904
```
    result = linker.link_with_result(entities, case_id, case_metadata)
    
    if neo4j_adapter and result.success:
        nodes, edges = linker.link(entities, case_id, case_metadata)
        linker.submit_to_neo4j(nodes, edges, connection=neo4j_adapter)
```

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### L64-70
```
try:
    from mahoun.graph.neo4j_adapter import Neo4jAdapter

    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```

### class UltraGraphBuilder › def export_to_neo4j › L755-765
```
        """
        Export graph to Neo4j database through GovernedNeo4jSession.

        GOVERNANCE ENFORCEMENT: All writes MUST go through GovernedNeo4jSession.
        Direct neo4j_adapter._execute_query() is FORBIDDEN.

        Args:
            governed_session: Initialized GovernedNeo4jSession instance
                (NOT a raw Neo4j adapter — that would bypass governance)

        Returns:
```

2 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/self_improve/ultra_self_improvement_system.py

### class UltraSelfImprovementSystem › def __init__ › L1299-1314
```
        
        # Neo4j integration (if configured)
        self.neo4j_adapter = None
        if self.config.get("enable_neo4j", False):
            try:
                from mahoun.graph.neo4j_adapter import Neo4jAdapter
                self.neo4j_adapter = Neo4jAdapter(
                    uri=self.config.get("neo4j_uri", "bolt://localhost:7687"),
                    user=self.config.get("neo4j_user", "neo4j"),
                    password=self.config["neo4j_password"],  # Required - will raise KeyError if missing
                    database=self.config.get("neo4j_database", "neo4j")
                )
                # Initialize the adapter
                import asyncio
                asyncio.run(self.neo4j_adapter.initialize())
                print("🔗 Neo4j adapter initialized")
```

### class UltraSelfImprovementSystem › def build_knowledge_graph › L2002-2009
```
        
        # Export to Neo4j if adapter is available
        if hasattr(self, 'neo4j_adapter') and self.neo4j_adapter:
            success = self.graph_builder.export_to_neo4j(self.neo4j_adapter)
            if success:
                print("   📤 Graph exported to Neo4j successfully")
            else:
                print("   ⚠️  Graph export to Neo4j failed")
```

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### L28-33
```
try:
    from graph.neo4j_adapter import Neo4jAdapter
    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```


## Assistant

<thinking>
**Reviewing function details**

I need to read more about files that are close to relevant functions. Specifically, I’m looking for the full file on `entity_linker` near the `submit` functions and the `_merge_node`/`_create_edge`. I should also check the API signatures for `write_node` and `write_relationship`, alongside `Neo4jConnection.governed_session`. I’ll need to get the `export_to_neo4j` functions from both builder files too. Even if diagnostics after the patch seems impossible, I think we can still analyze by reading targeted sections.
</thinking>

I’ve identified the relevant export and submission paths. Next I’m reading the exact methods and the governed session API so I can patch the call sites without guessing.

**Tool Call: Read file `mahoun/graph/builders/entity_linker.py` (lines 400-1050)**
Status: Completed

```KingMahouN/mahoun/graph/builders/entity_linker.py
   400	                
   401	                edges.append(GraphEdgeSpec(
   402	                    from_label="Organization",
   403	                    from_id=node_id,
   404	                    to_label="Case",
   405	                    to_id=f"case_{case_id}",
   406	                    relationship_type="PARTY_IN",
   407	                    properties={},
   408	                    confidence=org.get("confidence", 0.85)
   409	                ))
   410	                
   411	            except Exception as e:
   412	                logger.warning(f"Failed to link organization: {e}")
   413	                continue
   414	        
   415	        return nodes, edges
   416	    
   417	    def _link_courts(
   418	        self,
   419	        courts: List[Dict[str, Any]],
   420	        case_id: str,
   421	        seen_ids: Set[str]
   422	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   423	        """Link court entities to graph"""
   424	        nodes: List[Any] = []
   425	        edges: List[Any] = []
   426	        for court in courts:
   427	            try:
   428	                # Use normalized name or generate from components
   429	                name = court.get("normalized_name") or court.get("text", "")
   430	                node_id = self._generate_court_id(
   431	                    court.get("level"),
   432	                    court.get("branch"),
   433	                    court.get("city")
   434	                )
   435	                
   436	                if node_id in seen_ids:
   437	                    continue
   438	                seen_ids.add(node_id)
   439	                
   440	                properties = {
   441	                    "name": name,
   442	                }
   443	                
   444	                if court.get("level"):
   445	                    properties["level"] = court["level"]
   446	                if court.get("branch"):
   447	                    properties["branch"] = court["branch"]
   448	                if court.get("city"):
   449	                    properties["city"] = court["city"]
   450	                if court.get("province"):
   451	                    properties["province"] = court["province"]
   452	                
   453	                nodes.append(GraphNodeSpec(
   454	                    label="Court",
   455	                    node_id=node_id,
   456	                    properties=properties,
   457	                    source_case_id=case_id,
   458	                    confidence=court.get("confidence", 0.9)
   459	                ))
   460	                
   461	                edges.append(GraphEdgeSpec(
   462	                    from_label="Case",
   463	                    from_id=f"case_{case_id}",
   464	                    to_label="Court",
   465	                    to_id=node_id,
   466	                    relationship_type="HANDLED_BY",
   467	                    properties={},
   468	                    confidence=court.get("confidence", 0.9)
   469	                ))
   470	                
   471	            except Exception as e:
   472	                logger.warning(f"Failed to link court: {e}")
   473	                continue
   474	        
   475	        return nodes, edges
   476	    
   477	    def _link_laws(
   478	        self,
   479	        laws: List[Dict[str, Any]],
   480	        case_id: str,
   481	        seen_ids: Set[str]
   482	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   483	        """Link law/article entities to graph"""
   484	        nodes: List[Any] = []
   485	        edges: List[Any] = []
   486	        for law in laws:
   487	            try:
   488	                article_num = law.get("article_number", "")
   489	                law_name = law.get("law_name", "")
   490	                
   491	                # Generate node ID from article reference
   492	                node_id = self._generate_law_id(article_num, law_name)
   493	                
   494	                if node_id in seen_ids:
   495	                    # Still create edge to existing node
   496	                    edges.append(GraphEdgeSpec(
   497	                        from_label="Case",
   498	                        from_id=f"case_{case_id}",
   499	                        to_label="LawArticle",
   500	                        to_id=node_id,
   501	                        relationship_type="REFERS_TO",
   502	                        properties={},
   503	                        confidence=law.get("confidence", 0.85)
   504	                    ))
   505	                    continue
   506	                seen_ids.add(node_id)
   507	                
   508	                # Parse law code from name
   509	                code = self._extract_law_code(law_name)
   510	                
   511	                properties = {
   512	                    "article": article_num,
   513	                    "law_name": law_name,
   514	                    "code": code,
   515	                    "description": law.get("normalized_ref", f"ماده {article_num} {law_name}")
   516	                }
   517	                
   518	                if law.get("clause"):
   519	                    properties["clause"] = law["clause"]
   520	                
   521	                nodes.append(GraphNodeSpec(
   522	                    label="LawArticle",
   523	                    node_id=node_id,
   524	                    properties=properties,
   525	                    source_case_id=case_id,
   526	                    confidence=law.get("confidence", 0.85)
   527	                ))
   528	                
   529	                edges.append(GraphEdgeSpec(
   530	                    from_label="Case",
   531	                    from_id=f"case_{case_id}",
   532	                    to_label="LawArticle",
   533	                    to_id=node_id,
   534	                    relationship_type="REFERS_TO",
   535	                    properties={},
   536	                    confidence=law.get("confidence", 0.85)
   537	                ))
   538	                
   539	            except Exception as e:
   540	                logger.warning(f"Failed to link law: {e}")
   541	                continue
   542	        
   543	        return nodes, edges
   544	    
   545	    def _link_topics(
   546	        self,
   547	        topics: List[Dict[str, Any]],
   548	        case_id: str,
   549	        seen_ids: Set[str]
   550	    ) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
   551	        """Link topic entities to graph"""
   552	        nodes: List[Any] = []
   553	        edges: List[Any] = []
   554	        for topic in topics:
   555	            try:
   556	                label = topic.get("topic") or topic.get("text", "")
   557	                node_id = self._generate_topic_id(label)
   558	                
   559	                if node_id in seen_ids:
   560	                    # Still create edge
   561	                    edges.append(GraphEdgeSpec(
   562	                        from_label="Case",
   563	                        from_id=f"case_{case_id}",
   564	                        to_label="Topic",
   565	                        to_id=node_id,
   566	                        relationship_type="ABOUT",
   567	                        properties={},
   568	                        confidence=topic.get("confidence", 0.8)
   569	                    ))
   570	                    continue
   571	                seen_ids.add(node_id)
   572	                
   573	                properties = {
   574	                    "label": label,
   575	                }
   576	                
   577	                if topic.get("category"):
   578	                    properties["category"] = topic["category"]
   579	                
   580	                nodes.append(GraphNodeSpec(
   581	                    label="Topic",
   582	                    node_id=node_id,
   583	                    properties=properties,
   584	                    source_case_id=case_id,
   585	                    confidence=topic.get("confidence", 0.8)
   586	                ))
   587	                
   588	                edges.append(GraphEdgeSpec(
   589	                    from_label="Case",
   590	                    from_id=f"case_{case_id}",
   591	                    to_label="Topic",
   592	                    to_id=node_id,
   593	                    relationship_type="ABOUT",
   594	                    properties={},
   595	                    confidence=topic.get("confidence", 0.8)
   596	                ))
   597	                
   598	            except Exception as e:
   599	                logger.warning(f"Failed to link topic: {e}")
   600	                continue
   601	        
   602	        return nodes, edges
   603	    
   604	    # ========================================================================
   605	    # ID Generation (Ensures Uniqueness for MERGE)
   606	    # ========================================================================
   607	    
   608	    def _generate_person_id(self, normalized_name: str, national_id: Optional[str] = None) -> str:
   609	        """Generate unique person ID"""
   610	        if national_id:
   611	            return f"person_nid_{national_id}"
   612	        # Use hash of normalized name
   613	        name_hash = hashlib.md5(normalized_name.encode('utf-8')).hexdigest()[:12]
   614	        return f"person_{name_hash}"
   615	    
   616	    def _generate_org_id(self, normalized_name: str, registration_id: Optional[str] = None) -> str:
   617	        """Generate unique organization ID"""
   618	        if registration_id:
   619	            return f"org_reg_{registration_id}"
   620	        name_hash = hashlib.md5(normalized_name.encode('utf-8')).hexdigest()[:12]
   621	        return f"org_{name_hash}"
   622	    
   623	    def _generate_court_id(
   624	        self,
   625	        level: Optional[str],
   626	        branch: Optional[str],
   627	        city: Optional[str]
   628	    ) -> str:
   629	        """Generate unique court ID"""
   630	        parts: List[Any] = []
   631	        if level:
   632	            parts.append(level)
   633	        if branch:
   634	            parts.append(f"شعبه{branch}")
   635	        if city:
   636	            parts.append(city)
   637	        
   638	        combined = "_".join(parts) if parts else "unknown"
   639	        court_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()[:12]
   640	        return f"court_{court_hash}"
   641	    
   642	    def _generate_law_id(self, article_num: str, law_name: str) -> str:
   643	        """Generate unique law article ID"""
   644	        code = self._extract_law_code(law_name)
   645	        return f"law_{code}_{article_num}".replace(" ", "_")
   646	    
   647	    def _generate_topic_id(self, label: str) -> str:
   648	        """Generate unique topic ID"""
   649	        normalized = self._normalize_string(label)
   650	        return f"topic_{normalized}".replace(" ", "_")
   651	    
   652	    # ========================================================================
   653	    # Utility Methods
   654	    # ========================================================================
   655	    
   656	    def _normalize_string(self, s: str) -> str:
   657	        """Normalize string for ID generation and comparison"""
   658	        if not s:
   659	            return ""
   660	        # Remove extra whitespace
   661	        s = re.sub(r'\s+', ' ', s.strip())
   662	        return s.lower()
   663	    
   664	    def _extract_law_code(self, law_name: str) -> str:
   665	        """Extract short code from law name"""
   666	        if not law_name:
   667	            return "unknown"
   668	        
   669	        # Common law name mappings
   670	        law_codes = {
   671	            "مدنی": "civil",
   672	            "آیین دادرسی مدنی": "cpc",
   673	            "آیین دادرسی کیفری": "cpp",
   674	            "مجازات اسلامی": "ipc",
   675	            "تجارت": "commercial",
   676	            "کار": "labor",
   677	            "ثبت": "registration",
   678	            "مالیات": "tax",
   679	        }
   680	        
   681	        for key, code in law_codes.items():
   682	            if key in law_name:
   683	                return code
   684	        
   685	        # Generate hash for unknown laws
   686	        return hashlib.md5(law_name.encode('utf-8')).hexdigest()[:8]
   687	    
   688	    def _update_stats(self, nodes: int, edges: int, time_ms: float):
   689	        """Update linker statistics"""
   690	        self.stats["total_linked"] += 1
   691	        self.stats["total_nodes"] += nodes
   692	        self.stats["total_edges"] += edges
   693	    
   694	    def get_stats(self) -> Dict[str, Any]:
   695	        """Get linker statistics"""
   696	        return self.stats.copy()
   697	    
   698	    # ========================================================================
   699	    # Neo4j Direct Integration (Optional)
   700	    # ========================================================================
   701	    
   702	    def submit_to_neo4j(
   703	        self,
   704	        nodes: List[GraphNodeSpec],
   705	        edges: List[GraphEdgeSpec],
   706	        connection: 'Neo4jConnection'
   707	    ) -> bool:
   708	        """
   709	        Submit nodes and edges directly to Neo4j.
   710	        
   711	        Args:
   712	            nodes: List of node specifications
   713	            edges: List of edge specifications
   714	            connection: Initialized Neo4jConnection instance
   715	        
   716	        Returns:
   717	            True if successful
   718	        """
   719	        from mahoun.graph.neo4j.connection import Neo4jConnection
   720	        
   721	        if not isinstance(connection, Neo4jConnection):
   722	            raise TypeError(
   723	                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
   724	            )
   725	            
   726	        if should_skip_graph():
   727	            logger.debug("EntityLinker: Skipping Neo4j submission in desktop-minimal mode")
   728	            return True
   729	        
   730	        try:
   731	            # Create nodes using MERGE
   732	            for node in nodes:
   733	                self._merge_node(node, connection)
   734	            
   735	            # Create edges
   736	            for edge in edges:
   737	                self._create_edge(edge, connection)
   738	            
   739	            logger.info(f"Submitted {len(nodes)} nodes and {len(edges)} edges to Neo4j")
   740	            return True
   741	            
   742	        except Exception as e:
   743	            logger.error(f"Neo4j submission failed: {e}")
   744	            return False
   745	    
   746	    def _merge_node(self, node: GraphNodeSpec, connection: 'Neo4jConnection'):
   747	        """Merge a single node into Neo4j"""
   748	        if not connection:
   749	            return
   750	            
   751	        # Validate label to prevent Cypher injection
   752	        ALLOWED_LABELS = {"Case", "Person", "Organization", "Court", "LawArticle", "Topic"}
   753	        if node.label not in ALLOWED_LABELS:
   754	            raise ValueError(f"Invalid node label: {node.label}")
   755	        
   756	        # Build MERGE query using APOC for properties
   757	        query = f"""
   758	            MERGE (n:{node.label} {{node_id: $node_id}})
   759	            WITH n
   760	            CALL apoc.create.setProperties(n, $props_map) YIELD node
   761	            RETURN node
   762	        """
   763	        
   764	        params = {"node_id": node.node_id, "props_map": node.properties}
   765	        
   766	        import uuid
   767	        correlation_id = str(uuid.uuid4())
   768	        with connection.governed_session(
   769	            correlation_id=correlation_id,
   770	            actor_id="entity-linker",
   771	            operation_type="entity_merge_node"
   772	        ) as session:
   773	            session.run(query, params)
   774	    
   775	    def _create_edge(self, edge: GraphEdgeSpec, connection: 'Neo4jConnection'):
   776	        """Create an edge in Neo4j"""
   777	        if not connection:
   778	            return
   779	            
   780	        # Validate labels and relationship type to prevent Cypher injection
   781	        ALLOWED_LABELS = {"Case", "Person", "Organization", "Court", "LawArticle", "Topic"}
   782	        ALLOWED_REL_TYPES = {"PARTY_IN", "REFERS_TO", "HANDLED_BY", "ABOUT"}
   783	        
   784	        if edge.from_label not in ALLOWED_LABELS or edge.to_label not in ALLOWED_LABELS:
   785	            raise ValueError(f"Invalid node label: {edge.from_label} or {edge.to_label}")
   786	        if edge.relationship_type not in ALLOWED_REL_TYPES:
   787	            raise ValueError(f"Invalid relationship type: {edge.relationship_type}")
   788	        
   789	        query = f"""
   790	            MATCH (a:{edge.from_label} {{node_id: $from_id}})
   791	            MATCH (b:{edge.to_label} {{node_id: $to_id}})
   792	            MERGE (a)-[r:{edge.relationship_type}]->(b)
   793	            WITH r
   794	            CALL apoc.create.setRelProperties(r, $props_map) YIELD rel
   795	            RETURN rel
   796	        """
   797	        
   798	        params = {"from_id": edge.from_id, "to_id": edge.to_id, "props_map": edge.properties}
   799	        
   800	        import uuid
   801	        correlation_id = str(uuid.uuid4())
   802	        with self.connection.governed_session(
   803	            correlation_id=correlation_id,
   804	            actor_id="entity-linker",
   805	            operation_type="entity_create_edge"
   806	        ) as session:
   807	            session.run(query, params)
   808	
   809	
   810	# ============================================================================
   811	# Convenience Functions
   812	# ============================================================================
   813	
   814	# Global linker instance
   815	_linker: Optional[EntityLinker] = None
   816	
   817	
   818	def _get_linker() -> EntityLinker:
   819	    """Get or create global linker instance"""
   820	    global _linker
   821	    if _linker is None:
   822	        _linker = EntityLinker()
   823	    return _linker
   824	
   825	
   826	def link_entities_to_graph(
   827	    entities: Dict[str, List[Dict[str, Any]]],
   828	    case_id: str,
   829	    case_metadata: Optional[Dict[str, Any]] = None
   830	) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
   831	    """
   832	    Link NER entities to graph structures.
   833	    
   834	    Main API function for entity linking.
   835	    
   836	    Args:
   837	        entities: NER output from legal_ner.extract_entities()
   838	        case_id: Unique case/document identifier
   839	        case_metadata: Optional case metadata
   840	    
   841	    Returns:
   842	        Tuple of (nodes, edges) as dictionaries
   843	    
   844	    Example:
   845	        >>> from mahoun.pipelines.ingestion.legal_ner import extract_entities
   846	        >>> from mahoun.graph.builders.entity_linker import link_entities_to_graph
   847	        >>> 
   848	        >>> entities = extract_entities(text)
   849	        >>> nodes, edges = link_entities_to_graph(entities, case_id="case_001")
   850	    """
   851	    linker = _get_linker()
   852	    nodes, edges = linker.link(entities, case_id, case_metadata)
   853	    
   854	    # Convert to dictionaries for serialization
   855	    nodes_dicts = [
   856	        {
   857	            "label": n.label,
   858	            "node_id": n.node_id,
   859	            "properties": n.properties,
   860	            "confidence": n.confidence
   861	        }
   862	        for n in nodes
   863	    ]
   864	    
   865	    edges_dicts = [
   866	        {
   867	            "from_label": e.from_label,
   868	            "from_id": e.from_id,
   869	            "to_label": e.to_label,
   870	            "to_id": e.to_id,
   871	            "relationship_type": e.relationship_type,
   872	            "properties": e.properties,
   873	            "confidence": e.confidence
   874	        }
   875	        for e in edges
   876	    ]
   877	    
   878	    return nodes_dicts, edges_dicts
   879	
   880	
   881	def link_and_submit(
   882	    entities: Dict[str, List[Dict[str, Any]]],
   883	    case_id: str,
   884	    case_metadata: Optional[Dict[str, Any]] = None,
   885	    neo4j_adapter=None
   886	) -> LinkingResult:
   887	    """
   888	    Link entities and optionally submit to Neo4j.
   889	    
   890	    Args:
   891	        entities: NER output
   892	        case_id: Case identifier
   893	        case_metadata: Optional case metadata
   894	        neo4j_adapter: Optional Neo4j adapter for direct submission (must be Neo4jConnection)
   895	    
   896	    Returns:
   897	        LinkingResult with statistics
   898	    """
   899	    linker = EntityLinker()
   900	    result = linker.link_with_result(entities, case_id, case_metadata)
   901	    
   902	    if neo4j_adapter and result.success:
   903	        nodes, edges = linker.link(entities, case_id, case_metadata)
   904	        linker.submit_to_neo4j(nodes, edges, connection=neo4j_adapter)
   905	    
   906	    return result
   907	
   908	
   909	# ============================================================================
   910	# Module Test
   911	# ============================================================================
   912	
   913	if __name__ == "__main__":
   914	    print("🔗 Testing Entity Linker")
   915	    print("=" * 60)
   916	    
   917	    # Sample NER output
   918	    entities = {
   919	        "persons": [
   920	            {
   921	                "text": "آقای احمد احمدی فرزند محمد",
   922	                "name": "احمد احمدی",
   923	                "title": "آقای",
   924	                "father_name": "محمد",
   925	                "confidence": 0.9
   926	            }
   927	        ],
   928	        "organizations": [
   929	            {
   930	                "text": "شرکت توسعه فناوری",
   931	                "name": "توسعه فناوری",
   932	                "org_type": "شرکت",
   933	                "registration_id": "12345",
   934	                "confidence": 0.85
   935	            }
   936	        ],
   937	        "courts": [
   938	            {
   939	                "text": "شعبه ۱۰ دادگاه عمومی حقوقی تهران",
   940	                "level": "دادگاه عمومی حقوقی",
   941	                "branch": "10",
   942	                "city": "تهران",
   943	                "confidence": 0.9
   944	            }
   945	        ],
   946	        "laws": [
   947	            {
   948	                "article_number": "10",
   949	                "law_name": "قانون مدنی",
   950	                "confidence": 0.85
   951	            }
   952	        ],
   953	        "topics": [
   954	            {
   955	                "topic": "مطالبه وجه",
   956	                "category": "مالی",
   957	                "confidence": 0.8
   958	            }
   959	        ]
   960	    }
   961	    
   962	    nodes, edges = link_entities_to_graph(entities, case_id="test_001")
   963	    
   964	    print(f"\n📊 Created {len(nodes)} nodes:")
   965	    for node in nodes:
   966	        print(f"   • ({node['label']}) {node['node_id']}")
   967	    
   968	    print(f"\n🔗 Created {len(edges)} edges:")
   969	    for edge in edges:
   970	        print(f"   • ({edge['from_label']})-[:{edge['relationship_type']}]->({edge['to_label']})")
   971	    
   972	    print("\n" + "=" * 60)
   973	    print("✅ Entity Linker Test Complete")
   974	

```


**Tool Call: Read file `mahoun/graph/ultra_graph_builder.py` (lines 700-860)**
Status: Completed

```KingMahouN/mahoun/graph/ultra_graph_builder.py
   700	        ]
   701	
   702	        return {"nodes": subgraph_nodes, "edges": subgraph_edges}
   703	
   704	    def compute_analytics(self) -> Dict[str, Any]:
   705	        """Compute advanced graph analytics"""
   706	        if not self.enable_analytics:
   707	            return {}
   708	
   709	        nodes = list(self.nodes.values())
   710	
   711	        analytics = {
   712	            "centrality": self.analytics_engine.compute_centrality(nodes, self.edges),
   713	            "communities": self.analytics_engine.find_communities(nodes, self.edges),
   714	        }
   715	
   716	        return analytics
   717	
   718	    def get_statistics(self) -> Dict:
   719	        """Get builder statistics"""
   720	        return self.stats
   721	
   722	    def export_to_json(self, filepath: str):
   723	        """Export graph to JSON"""
   724	        graph_data = {
   725	            "nodes": [
   726	                {
   727	                    "id": node.id,
   728	                    "label": node.label,
   729	                    "type": node.node_type,
   730	                    "properties": node.properties,
   731	                    "confidence": node.confidence,
   732	                    "quality_score": node.quality_score,
   733	                }
   734	                for node in self.nodes.values()
   735	            ],
   736	            "edges": [
   737	                {
   738	                    "source": edge.source_id,
   739	                    "target": edge.target_id,
   740	                    "type": edge.relationship_type,
   741	                    "weight": edge.weight,
   742	                    "confidence": edge.confidence,
   743	                    "quality_score": edge.quality_score,
   744	                }
   745	                for edge in self.edges
   746	            ],
   747	        }
   748	
   749	        with open(filepath, "w", encoding="utf-8") as f:
   750	            json.dump(graph_data, f, ensure_ascii=False, indent=2)
   751	
   752	        logger.info(f"Graph exported to {filepath}")
   753	
   754	    def export_to_neo4j(self, governed_session) -> bool:
   755	        """
   756	        Export graph to Neo4j database through GovernedNeo4jSession.
   757	
   758	        GOVERNANCE ENFORCEMENT: All writes MUST go through GovernedNeo4jSession.
   759	        Direct neo4j_adapter._execute_query() is FORBIDDEN.
   760	
   761	        Args:
   762	            governed_session: Initialized GovernedNeo4jSession instance
   763	                (NOT a raw Neo4j adapter — that would bypass governance)
   764	
   765	        Returns:
   766	            True if export successful, False otherwise
   767	        """
   768	        try:
   769	            logger.info("Exporting graph to Neo4j via GovernedNeo4jSession")
   770	
   771	            # Validate that we received a governed session, not a raw adapter
   772	            from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
   773	            if not isinstance(governed_session, GovernedNeo4jSession):
   774	                raise TypeError(
   775	                    f"GOVERNANCE VIOLATION: export_to_neo4j requires GovernedNeo4jSession, "
   776	                    f"got {type(governed_session).__name__}. Direct Neo4j access is FORBIDDEN."
   777	                )
   778	
   779	            # Export nodes
   780	            for node in self.nodes.values():
   781	                # Determine label: quarantine low-confidence nodes
   782	                label = node.node_type or "GraphNode"
   783	                if node.confidence < 1.0:
   784	                    label = f"Quarantined{label}"
   785	                    logger.warning(
   786	                        f"Node '{node.id}' routed to quarantine (confidence={node.confidence:.2f})"
   787	                    )
   788	
   789	                node_data = {
   790	                    "id": node.id,
   791	                    "label": node.label,
   792	                    "node_type": node.node_type,
   793	                    "confidence": node.confidence,
   794	                    "quality_score": node.quality_score,
   795	                    "provenance": {
   796	                        "source": "ultra_graph_builder",
   797	                        "source_documents": node.source_documents,
   798	                        "created_at": node.created_at.isoformat() if node.created_at else None,
   799	                    },
   800	                    **{k: v for k, v in node.properties.items()
   801	                       if k not in ("id", "label", "node_type", "confidence", "quality_score", "provenance")},
   802	                }
   803	
   804	                governed_session.write_node(label=label, node_data=node_data, merge=True)
   805	
   806	            # Export relationships
   807	            for edge in self.edges:
   808	                # Determine source/target types for quarantine-aware routing
   809	                source_node = self.nodes.get(edge.source_id)
   810	                target_node = self.nodes.get(edge.target_id)
   811	
   812	                source_type = (source_node.node_type or "GraphNode") if source_node else "GraphNode"
   813	                target_type = (target_node.node_type or "GraphNode") if target_node else "GraphNode"
   814	
   815	                # Quarantine labels for low-confidence source/target
   816	                if source_node and source_node.confidence < 1.0:
   817	                    source_type = f"Quarantined{source_type}"
   818	                if target_node and target_node.confidence < 1.0:
   819	                    target_type = f"Quarantined{target_type}"
   820	
   821	                rel_data = {
   822	                    "weight": edge.weight,
   823	                    "confidence": edge.confidence,
   824	                    "quality_score": edge.quality_score,
   825	                    "provenance": {
   826	                        "source": "ultra_graph_builder",
   827	                        "evidence": edge.evidence,
   828	                        "created_at": edge.created_at.isoformat() if edge.created_at else None,
   829	                    },
   830	                    **{k: v for k, v in edge.properties.items()
   831	                       if k not in ("weight", "confidence", "quality_score", "provenance")},
   832	                }
   833	
   834	                governed_session.write_relationship(
   835	                    source_type=source_type,
   836	                    source_id=edge.source_id,
   837	                    relationship_type=edge.relationship_type,
   838	                    target_type=target_type,
   839	                    target_id=edge.target_id,
   840	                    rel_data=rel_data,
   841	                    merge=True,
   842	                )
   843	
   844	            logger.info(
   845	                f"Exported {len(self.nodes)} nodes and {len(self.edges)} relationships "
   846	                f"to Neo4j via GovernedNeo4jSession"
   847	            )
   848	            return True
   849	
   850	        except Exception as e:
   851	            logger.error(f"Neo4j governed export failed: {e}")
   852	            raise  # Fail-closed: do NOT return False silently
   853	
   854	
   855	# ============================================================================
   856	# Example Usage
   857	# ============================================================================
   858	
   859	
   860	def test_ultra_graph_builder():

```


**Tool Call: Read file `mahoun/ultra_systems/graph/ultra_graph_builder.py` (lines 700-860)**
Status: Completed

```KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py
   700	                    actor_id="ultra-graph-builder",
   701	                    operation_type="export_edge"
   702	                ) as session:
   703	                    session.run(create_edge_query, params)
   704	            
   705	            print(f"   ✅ Exported {len(self.nodes)} nodes and {len(self.edges)} relationships to Neo4j")
   706	            return True
   707	            
   708	        except Exception as e:
   709	            print(f"   ❌ Neo4j export failed: {e}")
   710	            return False
   711	
   712	# ============================================================================
   713	# Example Usage
   714	# ============================================================================
   715	
   716	def test_ultra_graph_builder():
   717	    """Test ultra graph builder"""
   718	    print("🚀 Testing Ultra Graph Builder")
   719	    print("=" * 60)
   720	    
   721	    # Create builder
   722	    builder = UltraGraphBuilder(
   723	        enable_quality_assessment=True,
   724	        enable_analytics=True
   725	    )
   726	    
   727	    # Sample entities
   728	    entities = [
   729	        {"id": "1", "text": "ماده 10", "label": "ARTICLE", "type": "legal", "confidence": 0.9},
   730	        {"id": "2", "text": "قانون مدنی", "label": "LAW", "type": "legal", "confidence": 0.95},
   731	        {"id": "3", "text": "دادگاه تهران", "label": "COURT", "type": "organization", "confidence": 0.85},
   732	    ]
   733	    
   734	    # Sample relationships
   735	    relationships = [
   736	        {"source_id": "1", "target_id": "2", "type": "PART_OF", "confidence": 0.9},
   737	        {"source_id": "3", "target_id": "1", "type": "CITES", "confidence": 0.8},
   738	    ]
   739	    
   740	    # Build graph
   741	    result = builder.build_graph(entities, relationships, source_id="doc_001")
   742	    
   743	    print(f"\n📊 Graph Metrics:")
   744	    metrics = result["metrics"]
   745	    print(f"   Nodes: {metrics.total_nodes}")
   746	    print(f"   Edges: {metrics.total_edges}")
   747	    print(f"   Avg Degree: {metrics.avg_degree:.2f}")
   748	    print(f"   Density: {metrics.density:.3f}")
   749	    print(f"   Avg Node Quality: {metrics.avg_node_quality:.2f}")
   750	    print(f"   Avg Edge Quality: {metrics.avg_edge_quality:.2f}")
   751	    
   752	    # Query neighbors
   753	    neighbors = builder.query_neighbors("1", max_depth=1)
   754	    print(f"\n🔍 Neighbors of node '1': {[n.id for n in neighbors]}")
   755	    
   756	    # Find path
   757	    path = builder.find_path("3", "2")
   758	    print(f"🛤️ Path from '3' to '2': {path}")
   759	    
   760	    # Analytics
   761	    analytics = builder.compute_analytics()
   762	    print(f"\n📈 Analytics:")
   763	    print(f"   Centrality: {analytics.get('centrality', {})}")
   764	    print(f"   Communities: {analytics.get('communities', {})}")
   765	    
   766	    # Statistics
   767	    stats = builder.get_statistics()
   768	    print(f"\n📊 Statistics: {stats}")
   769	
   770	
   771	if __name__ == "__main__":
   772	    test_ultra_graph_builder()

```


**Tool Call: Read file `mahoun/graph/neo4j/connection.py` (lines 200-330)**
Status: Completed

```KingMahouN/mahoun/graph/neo4j/connection.py
   200	    
   201	    def _raw_execute(
   202	        self,
   203	        query: str,
   204	        parameters: Optional[Dict[str, Any]] = None,
   205	        **kwargs
   206	    ) -> List[Any]:
   207	        """
   208	        Internal execution method — calls MutationAuthorizationBoundary
   209	        on EVERY query before reaching the driver.
   210	
   211	        This is the single chokepoint for all Cypher execution.
   212	        MutationAuthorizationBoundary.inspect() raises GovernanceViolationError
   213	        if mutation Cypher is detected outside GovernedNeo4jSession.
   214	        """
   215	        # Lazy import to avoid import-time overhead
   216	        from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
   217	        
   218	        MutationAuthorizationBoundary.inspect(query)
   219	        with self.session(**kwargs) as s:
   220	            result = s.run(query, parameters or {})
   221	            return [record for record in result]
   222	
   223	    @retry_on_failure(max_attempts=3)
   224	    def execute_query(
   225	        self,
   226	        query: str,
   227	        parameters: Optional[Dict[str, Any]] = None,
   228	        **kwargs
   229	    ) -> List[Any]:
   230	        """
   231	        Execute a READ-ONLY query.
   232	
   233	        Mutation Cypher (MERGE/CREATE/DELETE/SET) will raise
   234	        GovernanceViolationError unless called from GovernedNeo4jSession.
   235	        Use governed_session() to perform any writes.
   236	
   237	        Args:
   238	            query: Cypher query (READ operations only)
   239	            parameters: Query parameters
   240	
   241	        Returns:
   242	            Query results
   243	
   244	        Raises:
   245	            GovernanceViolationError: If mutation Cypher is detected.
   246	        """
   247	        return self._raw_execute(query, parameters, **kwargs)
   248	
   249	    @contextmanager
   250	    def governed_session(
   251	        self,
   252	        pipeline: Optional["ValidatorPipeline"] = None,
   253	        correlation_id: str = "",
   254	        actor_id: str = "",
   255	    ) -> Generator["GovernedNeo4jSession", None, None]:
   256	        """
   257	        The ONLY authorized entry point for graph mutation.
   258	
   259	        Yields a GovernedNeo4jSession which is the only surface that
   260	        may execute mutation Cypher.  Direct execute_query() with
   261	        MERGE/CREATE/DELETE/SET will raise GovernanceViolationError.
   262	
   263	        Enforces P0: GovernanceContext MUST be active, else fail-closed.
   264	
   265	        Usage::
   266	
   267	            async with GovernanceContextManager.active_context(...):
   268	                with connection.governed_session(correlation_id="op-123", actor_id="judge-42") as session:
   269	                    session.write_node(...)
   270	
   271	        Args:
   272	            pipeline: Optional ValidatorPipeline.
   273	            correlation_id: Correlation ID (falls back to active context).
   274	            actor_id: Actor responsible for the mutation (for provenance).
   275	
   276	        Yields:
   277	            GovernedNeo4jSession
   278	        """
   279	        # Lazy imports to avoid import-time overhead
   280	        from mahoun.core.governance.governance_context import GovernanceContextManager
   281	        from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
   282	        
   283	        # Enforce governance context at the boundary entry (fail-closed)
   284	        GovernanceContextManager.require_context()
   285	        yield GovernedNeo4jSession(
   286	            raw_executor=self._raw_execute,
   287	            pipeline=pipeline,
   288	            correlation_id=correlation_id,
   289	            actor_id=actor_id,
   290	        )
   291	    
   292	    def execute_write(self, *args, **kwargs):  # type: ignore[override]
   293	        """
   294	        REMOVED — constitutional violation.
   295	
   296	        Direct execute_write() is forbidden. It bypasses the
   297	        MutationAuthorizationBoundary. Use governed_session() instead.
   298	
   299	        Raises:
   300	            GovernanceViolationError: Always.
   301	        """
   302	        from mahoun.core.governance.violations import (
   303	            GovernanceViolation, ViolationSeverity, ViolationCategory,
   304	            GovernanceViolationError,
   305	        )
   306	        raise GovernanceViolationError(
   307	            GovernanceViolation(
   308	                category=ViolationCategory.ARCHITECTURE_BOUNDARY,
   309	                severity=ViolationSeverity.CRITICAL,
   310	                message=(
   311	                    "execute_write() is constitutionally forbidden. "
   312	                    "Use connection.governed_session() for all graph mutations."
   313	                ),
   314	                details={},
   315	                source="Neo4jConnection.execute_write",
   316	            )
   317	        )
   318	    
   319	    @retry_on_failure(max_attempts=3)
   320	    def execute_read(
   321	        self,
   322	        func: Callable,
   323	        *args,
   324	        **kwargs
   325	    ):
   326	        """
   327	        Execute a read transaction with retry logic
   328	        
   329	        Args:
   330	            func: Transaction function

```


**Tool Call: Read file `mahoun/core/governance/mutation_boundary.py` (lines 440-660)**
Status: Completed

```KingMahouN/mahoun/core/governance/mutation_boundary.py
   440	                        "Every mutation must carry a verified actor identity."
   441	                    ),
   442	                    details={"actor_id_provided": repr(actor_id)},
   443	                    source="GovernedNeo4jSession.__init__",
   444	                )
   445	            )
   446	        self._actor_id = resolved_actor.strip()
   447	        self._governance_scope_id = ctx.context_id
   448	        self._ledger: List[MutationReceipt] = []
   449	
   450	    # ------------------------------------------------------------------
   451	    # Public write API
   452	    # ------------------------------------------------------------------
   453	
   454	    def write_node(
   455	        self,
   456	        label: str,
   457	        node_data: Dict[str, Any],
   458	        merge: bool = True,
   459	    ) -> MutationReceipt:
   460	        """
   461	        Write a node through the governed boundary.
   462	
   463	        Requires:
   464	            - node_data["id"] — unique identifier
   465	            - node_data["provenance"] — provenance metadata dict (or will be injected)
   466	
   467	        CRITICAL ORDER (P0 TRANSACTIONAL GOVERNANCE ORDERING):
   468	            1. governance validation (context + pipeline)
   469	            2. provenance generation
   470	            3. immutable audit append (must succeed or mutation aborts)
   471	            4. graph mutation commit
   472	            5. attestation finalization
   473	
   474	        Raises:
   475	            GovernanceViolationError: fail-closed on any violation.
   476	        """
   477	        # STEP 0: Node label allowlist enforcement (I4)
   478	        # Import here to avoid circular import at module level.
   479	        from mahoun.core.governance.validator_pipeline import validate_node_label
   480	        validate_node_label(label, self._correlation_id)
   481	
   482	        # STEP 1: Governance validation (already enforced at __init__ via require_context)
   483	        ctx = GovernanceContextManager.require_context()
   484	
   485	        # Ensure provenance is complete before validation.
   486	        provenance_entry = node_data.get("provenance")
   487	        source = "graph_mutation:write_node"
   488	        if isinstance(provenance_entry, dict) and provenance_entry.get("source"):
   489	            source = provenance_entry.get("source")
   490	
   491	        generated_provenance = GovernanceContextManager.require_provenance(
   492	            source=source,
   493	            author=self._actor_id,
   494	        ).to_dict()
   495	        node_data["provenance"] = generated_provenance
   496	
   497	        result = self._pipeline.validate_node_write(
   498	            node_data, self._correlation_id
   499	        )
   500	
   501	        # STEP 1.5: Confidence-based quarantine routing
   502	        confidence = node_data.get("confidence", 1.0)
   503	        if isinstance(confidence, (int, float)) and confidence < 1.0:
   504	            if not label.startswith("Quarantined"):
   505	                original_label = label
   506	                label = f"Quarantined{label}"
   507	                logger.warning(
   508	                    "[MAB] QUARANTINE: Node '%s' routed to quarantine label '%s' "
   509	                    "(confidence=%.2f < 1.0, original_label='%s')",
   510	                    node_data.get("id", "?"), label, confidence, original_label,
   511	                )
   512	
   513	        # STEP 2: Provenance generation (must succeed before audit/mutation)
   514	        provenance = GovernanceContextManager.require_provenance(
   515	            source=source,
   516	            author=self._actor_id,
   517	        )
   518	
   519	        # Phase 2: Build Cypher (provenance stays out of graph properties)
   520	        cypher_props = {k: v for k, v in node_data.items() if k != "provenance"}
   521	        assignments = ", ".join(f"n.{k} = ${k}" for k in cypher_props)
   522	
   523	        if merge:
   524	            query = (
   525	                f"MERGE (n:{label} {{id: $id}}) "
   526	                f"ON CREATE SET n.created_at = datetime() "
   527	                f"SET {assignments}, n.updated_at = datetime()"
   528	            )
   529	            m_type = MutationType.NODE_MERGE
   530	        else:
   531	            query = (
   532	                f"CREATE (n:{label}) "
   533	                f"SET {assignments}, n.created_at = datetime()"
   534	            )
   535	            m_type = MutationType.NODE_CREATE
   536	
   537	        # STEP 3: Immutable audit append — FAILS CLOSED if this raises
   538	        audit_entry = {
   539	            "timestamp": datetime.now(timezone.utc).isoformat(),
   540	            "correlation_id": self._correlation_id,
   541	            "governance_scope_id": self._governance_scope_id,
   542	            "actor_id": self._actor_id,
   543	            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
   544	            "operation": "write_node",
   545	            "label": label,
   546	            "entity_id": str(node_data.get("id", "")),
   547	            "query_preview": query[:200],
   548	            "params_keys": list(cypher_props.keys()),
   549	        }
   550	        _append_governance_audit(audit_entry)
   551	
   552	        # STEP 4: Execute under authorization (mutation only after audit success)
   553	        self._execute_authorized(query, cypher_props)
   554	
   555	        # Phase 4: Receipt
   556	        receipt = _make_receipt(
   557	            mutation_type=m_type,
   558	            label=label,
   559	            entity_id=str(node_data.get("id", "")),
   560	            correlation_id=self._correlation_id,
   561	            payload=node_data,
   562	            pipeline_hash=result.pipeline_hash,
   563	        )
   564	        self._ledger.append(receipt)
   565	        logger.info(
   566	            "[MAB] Node write authorized: %s/%s receipt=%s",
   567	            label, node_data.get("id"), receipt.receipt_id,
   568	        )
   569	        return receipt
   570	
   571	    def write_relationship(
   572	        self,
   573	        source_type: str,
   574	        source_id: str,
   575	        relationship_type: str,
   576	        target_type: str,
   577	        target_id: str,
   578	        rel_data: Dict[str, Any],
   579	        merge: bool = True,
   580	    ) -> MutationReceipt:
   581	        """
   582	        Write a relationship through the governed boundary.
   583	
   584	        Requires:
   585	            - rel_data["provenance"] — provenance metadata dict
   586	            - relationship_type must be in OntologyEnforcer ruleset
   587	
   588	        CRITICAL ORDER (P0 TRANSACTIONAL GOVERNANCE ORDERING):
   589	            1. governance validation
   590	            2. provenance generation
   591	            3. immutable audit append (must succeed)
   592	            4. graph mutation
   593	            5. attestation
   594	
   595	        Raises:
   596	            GovernanceViolationError: fail-closed on any violation.
   597	        """
   598	        # STEP 1: Governance validation
   599	        ctx = GovernanceContextManager.require_context()
   600	
   601	        # Ensure provenance entry is complete before validation.
   602	        provenance_entry = rel_data.get("provenance")
   603	        source = "graph_mutation:write_relationship"
   604	        if isinstance(provenance_entry, dict) and provenance_entry.get("source"):
   605	            source = provenance_entry.get("source")
   606	
   607	        generated_provenance = GovernanceContextManager.require_provenance(
   608	            source=source,
   609	            author=self._actor_id,
   610	        ).to_dict()
   611	        rel_data["provenance"] = generated_provenance
   612	
   613	        result = self._pipeline.validate_relationship_write(
   614	            source_type=source_type,
   615	            relationship_type=relationship_type,
   616	            target_type=target_type,
   617	            relationship_data=rel_data,
   618	            correlation_id=self._correlation_id,
   619	        )
   620	
   621	        # STEP 2: Provenance generation
   622	        provenance = GovernanceContextManager.require_provenance(
   623	            source=source,
   624	            author=self._actor_id,
   625	        )
   626	
   627	        # Phase 2: Build Cypher
   628	        cypher_props = {k: v for k, v in rel_data.items() if k != "provenance"}
   629	        assignments = ", ".join(f"r.{k} = ${k}" for k in cypher_props)
   630	        set_clause = f"SET {assignments}" if assignments else ""
   631	
   632	        if merge:
   633	            query = (
   634	                f"MATCH (a:{source_type} {{id: $__src}}) "
   635	                f"MATCH (b:{target_type} {{id: $__tgt}}) "
   636	                f"MERGE (a)-[r:{relationship_type}]->(b) "
   637	                f"ON CREATE SET r.created_at = datetime() "
   638	                f"{set_clause}"
   639	            )
   640	            m_type = MutationType.RELATIONSHIP_MERGE
   641	        else:
   642	            query = (
   643	                f"MATCH (a:{source_type} {{id: $__src}}) "
   644	                f"MATCH (b:{target_type} {{id: $__tgt}}) "
   645	                f"CREATE (a)-[r:{relationship_type}]->(b) "
   646	                f"SET r.created_at = datetime() {set_clause}"
   647	            )
   648	            m_type = MutationType.RELATIONSHIP_CREATE
   649	
   650	        params = {"__src": source_id, "__tgt": target_id, **cypher_props}
   651	
   652	        # STEP 3: Immutable audit append — must succeed or abort
   653	        audit_entry = {
   654	            "timestamp": datetime.now(timezone.utc).isoformat(),
   655	            "correlation_id": self._correlation_id,
   656	            "governance_scope_id": self._governance_scope_id,
   657	            "actor_id": self._actor_id,
   658	            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
   659	            "operation": "write_relationship",
   660	            "relationship_type": relationship_type,

```


## Assistant

I’ve confirmed the governed write API shape. I’m now reading the older `ultra_systems` export implementation in full so I can replace the raw Cypher path cleanly and minimally.

**Tool Call: Read file `mahoun/ultra_systems/graph/ultra_graph_builder.py` (lines 620-720)**
Status: Completed

```KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py
   620	    
   621	    def export_to_neo4j(self, connection: 'Neo4jConnection') -> bool:
   622	        """
   623	        Export graph to Neo4j database
   624	        
   625	        Args:
   626	            connection: Initialized Neo4jConnection instance
   627	            
   628	        Returns:
   629	            True if export successful, False otherwise
   630	        """
   631	        from mahoun.graph.neo4j.connection import Neo4jConnection
   632	        import uuid
   633	        
   634	        if not isinstance(connection, Neo4jConnection):
   635	            raise TypeError(
   636	                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
   637	            )
   638	
   639	        try:
   640	            print("📤 Exporting graph to Neo4j...")
   641	            
   642	            # Create nodes
   643	            for node in self.nodes.values():
   644	                create_node_query = """
   645	                    MERGE (n:GraphNode {id: $node_id})
   646	                    SET n.label = $label,
   647	                        n.type = $node_type,
   648	                        n.confidence = $confidence,
   649	                        n.quality_score = $quality_score
   650	                    WITH n
   651	                    CALL apoc.create.setProperties(n, $props_map) YIELD node
   652	                    RETURN node
   653	                """
   654	                
   655	                # Prepare parameters
   656	                params = {
   657	                    "node_id": node.id,
   658	                    "label": node.label,
   659	                    "node_type": node.node_type,
   660	                    "confidence": node.confidence,
   661	                    "quality_score": node.quality_score,
   662	                    "props_map": node.properties
   663	                }
   664	                
   665	                correlation_id = str(uuid.uuid4())
   666	                with connection.governed_session(
   667	                    correlation_id=correlation_id,
   668	                    actor_id="ultra-graph-builder",
   669	                    operation_type="export_node"
   670	                ) as session:
   671	                    session.run(create_node_query, params)
   672	            
   673	            # Create relationships
   674	            for edge in self.edges:
   675	                create_edge_query = """
   676	                    MATCH (a:GraphNode {id: $source_id}), (b:GraphNode {id: $target_id})
   677	                    MERGE (a)-[r:RELATED {type: $relationship_type}]->(b)
   678	                    SET r.weight = $weight,
   679	                        r.confidence = $confidence,
   680	                        r.quality_score = $quality_score
   681	                    WITH r
   682	                    CALL apoc.create.setRelProperties(r, $props_map) YIELD rel
   683	                    RETURN rel
   684	                """
   685	                
   686	                # Prepare parameters
   687	                params = {
   688	                    "source_id": edge.source_id,
   689	                    "target_id": edge.target_id,
   690	                    "relationship_type": edge.relationship_type,
   691	                    "weight": edge.weight,
   692	                    "confidence": edge.confidence,
   693	                    "quality_score": edge.quality_score,
   694	                    "props_map": edge.properties
   695	                }
   696	                
   697	                correlation_id = str(uuid.uuid4())
   698	                with connection.governed_session(
   699	                    correlation_id=correlation_id,
   700	                    actor_id="ultra-graph-builder",
   701	                    operation_type="export_edge"
   702	                ) as session:
   703	                    session.run(create_edge_query, params)
   704	            
   705	            print(f"   ✅ Exported {len(self.nodes)} nodes and {len(self.edges)} relationships to Neo4j")
   706	            return True
   707	            
   708	        except Exception as e:
   709	            print(f"   ❌ Neo4j export failed: {e}")
   710	            return False
   711	
   712	# ============================================================================
   713	# Example Usage
   714	# ============================================================================
   715	
   716	def test_ultra_graph_builder():
   717	    """Test ultra graph builder"""
   718	    print("🚀 Testing Ultra Graph Builder")
   719	    print("=" * 60)
   720	    

```


**Tool Call: Search files for regex `def\s+export_to_neo4j|session\.run\(|governed_session\(|write_node\(|write_relationship\(`**
Status: Completed

Found 3 matches:

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def export_to_neo4j › L619-623
```
        print(f"📁 Graph exported to {filepath}")
    
    def export_to_neo4j(self, connection: 'Neo4jConnection') -> bool:
        """
        Export graph to Neo4j database
```

### class UltraGraphBuilder › def export_to_neo4j › L664-671
```
                
                correlation_id = str(uuid.uuid4())
                with connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="ultra-graph-builder",
                    operation_type="export_node"
                ) as session:
                    session.run(create_node_query, params)
```

### class UltraGraphBuilder › def export_to_neo4j › L696-703
```
                
                correlation_id = str(uuid.uuid4())
                with connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="ultra-graph-builder",
                    operation_type="export_edge"
                ) as session:
                    session.run(create_edge_query, params)
```


**Tool Call: Search files for regex `def\s+export_to_neo4j|session\.run\(|governed_session\(|write_node\(|write_relationship\(`**
Status: Completed

Found 3 matches:

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def export_to_neo4j › L752-756
```
        logger.info(f"Graph exported to {filepath}")

    def export_to_neo4j(self, governed_session) -> bool:
        """
        Export graph to Neo4j database through GovernedNeo4jSession.
```

### class UltraGraphBuilder › def export_to_neo4j › L802-806
```
                }

                governed_session.write_node(label=label, node_data=node_data, merge=True)

            # Export relationships
```

### class UltraGraphBuilder › def export_to_neo4j › L832-836
```
                }

                governed_session.write_relationship(
                    source_type=source_type,
                    source_id=edge.source_id,
```


**Tool Call: Search files for regex `from\s+mahoun\.graph\.neo4j\.connection\s+import\s+Neo4jConnection|from\s+graph\.neo4j_adapter\s+import\s+Neo4jAdapter|from\s+mahoun\.graph\.neo4j_adapter\s+import\s+Neo4jAdapter`**
Status: Completed

Found 11 matches:

## Matches in KingMahouN/mahoun/graph/builders/entity_linker.py

### class EntityLinker › def submit_to_neo4j › L717-721
```
            True if successful
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        if not isinstance(connection, Neo4jConnection):
```

## Matches in KingMahouN/mahoun/graph/legal_cypher_queries.py

### class LegalQueryExecutor › def __init__ › L688-698
```
        """
        Initialize query executor with injected Neo4jConnection.
        
        Args:
            connection: Neo4jConnection instance (from get_connection())
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        if not isinstance(connection, Neo4jConnection):
            raise TypeError(
                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
```

9 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/graph/neo4j/__init__.py

### def __getattr__ › L71-81
```
    if name == "Neo4jConnection":
        from mahoun.graph.neo4j.connection import Neo4jConnection
        return Neo4jConnection
    elif name == "get_connection":
        from mahoun.graph.neo4j.connection import get_connection
        return get_connection
    elif name == "CypherQueryBuilder":
        from mahoun.graph.neo4j.query_builder import CypherQueryBuilder
        return CypherQueryBuilder
    elif name == "QueryBuilder":
        # Alias
```

23 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/graph/neo4j/algorithms.py

### L1-11
```
"""
Graph Algorithms
================

Advanced graph algorithms using Neo4j GDS.
"""


from typing import Any, Dict, List, Optional, Tuple
from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection

```

265 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/graph/neo4j/operations.py

### L18-22
```
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from mahoun.graph.neo4j.connection import Neo4jConnection, get_connection
from mahoun.graph.neo4j.monitoring import Neo4jMetrics

```

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### L64-70
```
try:
    from mahoun.graph.neo4j_adapter import Neo4jAdapter

    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```

## Matches in KingMahouN/mahoun/pipelines/sync/graph_vector_sync.py

### L31-35
```
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mahoun.graph.neo4j.connection import Neo4jConnection

if TYPE_CHECKING:
```

## Matches in KingMahouN/mahoun/retrieval/graph_enhanced.py

### L30-34
```
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING

from mahoun.graph.neo4j.connection import Neo4jConnection

if TYPE_CHECKING:
```

## Matches in KingMahouN/mahoun/self_improve/ultra_self_improvement_system.py

### class UltraSelfImprovementSystem › def __init__ › L1303-1313
```
            try:
                from mahoun.graph.neo4j_adapter import Neo4jAdapter
                self.neo4j_adapter = Neo4jAdapter(
                    uri=self.config.get("neo4j_uri", "bolt://localhost:7687"),
                    user=self.config.get("neo4j_user", "neo4j"),
                    password=self.config["neo4j_password"],  # Required - will raise KeyError if missing
                    database=self.config.get("neo4j_database", "neo4j")
                )
                # Initialize the adapter
                import asyncio
                asyncio.run(self.neo4j_adapter.initialize())
```

3 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### L28-33
```
try:
    from graph.neo4j_adapter import Neo4jAdapter
    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```

### class UltraGraphBuilder › def export_to_neo4j › L622-632
```
        """
        Export graph to Neo4j database
        
        Args:
            connection: Initialized Neo4jConnection instance
            
        Returns:
            True if export successful, False otherwise
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        import uuid
```

78 lines remaining in ancestor node. Read the file to see all.


## Assistant

<thinking>
**Examining code updates**

I need to consider the full file headers in `ultra_systems` to patch imports. I should also look at the `graph/ultra_graph_builder.py` for exact imports if we plan to add `Neo4jConnection`. The current `export_to_neo4j` function accepts `governed_session` instead of a connection, which the user didn't initially ask to change, but we do need to remove stale imports and add local allowlists.

It's essential to inspect the `_process_entities` methods and relationship patterns to ensure everything aligns properly. I'll have to check if `export_to_neo4j` is called elsewhere, as it may affect interface changes.

**Investigating call sites**

I need to find out where the call sites are, especially those that might be expecting an adapter. It seems important to identify these locations to ensure proper integration and functionality. I'll conduct a search to see where these calls are made and how they might interact with the adapter. It’s a small but crucial task, as it can influence the overall efficiency of the system.
</thinking>

I need a bit more context on the builders’ in-memory node/edge shapes and any call sites, so I’m checking the processing methods and direct uses of these export helpers.

**Tool Call: Search files for regex `link_and_submit\(`**
Status: Completed

Found 1 matches:

## Matches in KingMahouN/mahoun/graph/builders/entity_linker.py

### def link_and_submit › L881-891
```
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
```

15 lines remaining in ancestor node. Read the file to see all.


**Tool Call: Search files for regex `export_to_neo4j\(`**
Status: Completed

Found 9 matches:

## Matches in KingMahouN/.test_classification_backup/tests/governance/test_hardened_infrastructure.py

### class TestFacadeBackdoorSeal › def test_graph_builder_rejects_raw_adapter › L282-283
```
        with pytest.raises(TypeError) as exc_info:
            builder.export_to_neo4j(raw_adapter)
```

### class TestFacadeBackdoorSeal › def test_graph_builder_export_via_governed_session › L314-318
```
        
        # Export via governed session
        builder.export_to_neo4j(governed_session)
        
        # Ensure raw executor was called (node writes + relationship write)
```

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def export_to_neo4j › L752-756
```
        logger.info(f"Graph exported to {filepath}")

    def export_to_neo4j(self, governed_session) -> bool:
        """
        Export graph to Neo4j database through GovernedNeo4jSession.
```

## Matches in KingMahouN/mahoun/self_improve/ultra_self_improvement_system.py

### class UltraSelfImprovementSystem › def build_knowledge_graph › L2004-2009
```
        if hasattr(self, 'neo4j_adapter') and self.neo4j_adapter:
            success = self.graph_builder.export_to_neo4j(self.neo4j_adapter)
            if success:
                print("   📤 Graph exported to Neo4j successfully")
            else:
                print("   ⚠️  Graph export to Neo4j failed")
```

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def export_to_neo4j › L619-623
```
        print(f"📁 Graph exported to {filepath}")
    
    def export_to_neo4j(self, connection: 'Neo4jConnection') -> bool:
        """
        Export graph to Neo4j database
```

## Matches in KingMahouN/tests/governance/test_hardened_infrastructure.py

### class TestFacadeBackdoorSeal › def test_graph_builder_rejects_raw_adapter › L285-286
```
        with pytest.raises(TypeError) as exc_info:
            builder.export_to_neo4j(raw_adapter)
```

### class TestFacadeBackdoorSeal › def test_graph_builder_export_via_governed_session › L317-321
```
        
        # Export via governed session
        builder.export_to_neo4j(governed_session)
        
        # Ensure raw executor was called (node writes + relationship write)
```

## Matches in KingMahouN/tests/test_governance_bypass_prevention.py

### class TestGraphBuildersGovernance › def test_ultra_graph_builder_type_enforcement › L188-189
```
        with pytest.raises(TypeError, match="Neo4jConnection"):
            builder.export_to_neo4j("not_a_connection")
```

### class TestGraphBuildersGovernance › def test_ultra_graph_builder_uses_governed_session › L217-227
```
        from mahoun.ultra_systems.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode
        from mahoun.graph.neo4j.connection import get_connection
        
        connection = get_connection()
        builder = UltraGraphBuilder()
        
        builder.nodes["test"] = GraphNode(id="test", label="GraphNode", node_type="test")
        
        mock_session = mock_governed_session.return_value.__enter__.return_value
        builder.export_to_neo4j(connection)
        
```

2 lines remaining in ancestor node. Read the file to see all.


**Tool Call: Search files for regex `def\s+_process_entities|def\s+_process_relationships|GraphNode\(|GraphEdge\(`**
Status: Completed

Found 3 matches:

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def _process_entities › L496-500
```
        }

    def _process_entities(self, entities: List[Dict], source_id: Optional[str]):
        """Process entities into graph nodes"""
        for entity in entities:
```

### class UltraGraphBuilder › def _process_entities › L509-523
```
            else:
                # Create new node
                node = GraphNode(
                    id=node_id,
                    label=entity.get("label", "UNKNOWN"),
                    node_type=entity.get("type", "entity"),
                    properties=entity.get("properties", {}),
                    confidence=entity.get("confidence", 1.0),
                    source_documents=[source_id] if source_id else [],
                )
                self.nodes[node_id] = node

    def _process_relationships(
        self, relationships: List[Dict], source_id: Optional[str]
    ):
```

### class UltraGraphBuilder › def _process_relationships › L525-535
```
        for rel in relationships:
            edge = GraphEdge(
                source_id=rel.get("source_id", ""),
                target_id=rel.get("target_id", ""),
                relationship_type=rel.get("type", "RELATED"),
                properties=rel.get("properties", {}),
                weight=rel.get("weight", 1.0),
                confidence=rel.get("confidence", 1.0),
                evidence=rel.get("evidence", []),
            )
            self.edges.append(edge)
```


**Tool Call: Search files for regex `def\s+_process_entities|def\s+_process_relationships|GraphNode\(|GraphEdge\(`**
Status: Completed

Found 3 matches:

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def _process_entities › L410-414
```
        }
    
    def _process_entities(self, entities: List[Dict], source_id: Optional[str]):
        """Process entities into graph nodes"""
        for entity in entities:
```

### class UltraGraphBuilder › def _process_entities › L426-436
```
                try:
                    from mahoun.core.governance.validator_pipeline import validate_node_label
                    validate_node_label(entity.get('label', 'UNKNOWN'))
                except Exception:
                    # Re-raise governance violations to callers
                    raise

                node = GraphNode(
                    id=node_id,
                    label=entity.get('label', 'UNKNOWN'),
                    node_type=entity.get('type', 'entity'),
```

5 lines remaining in ancestor node. Read the file to see all.

### class UltraGraphBuilder › def _process_relationships › L441-455
```
                self.nodes[node_id] = node
    
    def _process_relationships(self, relationships: List[Dict], source_id: Optional[str]):
        """Process relationships into graph edges"""
        for rel in relationships:
            edge = GraphEdge(
                source_id=rel.get('source_id', ''),
                target_id=rel.get('target_id', ''),
                relationship_type=rel.get('type', 'RELATED'),
                properties=rel.get('properties', {}),
                weight=rel.get('weight', 1.0),
                confidence=rel.get('confidence', 1.0),
                evidence=rel.get('evidence', [])
            )
            self.edges.append(edge)
```


**Tool Call: Read file `mahoun/graph/ultra_graph_builder.py` (lines 400-620)**
Status: Completed

```KingMahouN/mahoun/graph/ultra_graph_builder.py
   400	        if enable_quality_assessment:
   401	            self.quality_assessor = GraphQualityAssessor()
   402	
   403	        if enable_analytics:
   404	            self.analytics_engine = GraphAnalyticsEngine()
   405	
   406	        # Graph storage
   407	        self.nodes: Dict[str, GraphNode] = {}
   408	        self.edges: List[GraphEdge] = []
   409	
   410	        # Indexes
   411	        self.node_index = {}  # For fast lookup
   412	        self.edge_index = defaultdict(list)  # Adjacency list
   413	
   414	        # Update queue for real-time processing
   415	        self.update_queue = deque()
   416	
   417	        # Statistics
   418	        self.stats = {
   419	            "total_builds": 0,
   420	            "total_updates": 0,
   421	            "avg_build_time": 0.0,
   422	            "quality_improvements": 0,
   423	        }
   424	
   425	        logger.info("Ultra Graph Builder initialized")
   426	
   427	    def build_graph(
   428	        self,
   429	        entities: List[Dict],
   430	        relationships: List[Dict],
   431	        source_id: Optional[str] = None,
   432	    ) -> Dict[str, Any]:
   433	        """
   434	        Build graph from entities and relationships
   435	
   436	        Args:
   437	            entities: List of entities
   438	            relationships: List of relationships
   439	            source_id: Source document/dataset ID
   440	
   441	        Returns:
   442	            Graph build result
   443	        """
   444	        # Desktop-Minimal mode: Fail-fast to prevent semantic degradation
   445	        if should_skip_graph():
   446	            raise RuntimeError(
   447	                "Graph construction is disabled in DESKTOP_MINIMAL mode. "
   448	                "This operation requires full graph reasoning to maintain "
   449	                "zero-hallucination guarantees and complete audit trails. "
   450	                "\n\nTo enable graph construction:"
   451	                "\n  1. Set environment variable: MAHOUN_MODE=enterprise_full"
   452	                "\n  2. Or run on production infrastructure with sufficient resources"
   453	                "\n\nCurrent mode is optimized for development/testing on resource-constrained environments."
   454	            )
   455	
   456	        start_time = time.time()
   457	
   458	        logger.info(
   459	            f"Building graph with {len(entities)} entities and {len(relationships)} relationships"
   460	        )
   461	
   462	        # Process entities
   463	        self._process_entities(entities, source_id)
   464	
   465	        # Process relationships
   466	        self._process_relationships(relationships, source_id)
   467	
   468	        # Quality assessment
   469	        if self.enable_quality_assessment:
   470	            self._assess_and_improve_quality()
   471	
   472	        # Build indexes
   473	        self._build_indexes()
   474	
   475	        # Calculate metrics
   476	        metrics = self._calculate_metrics()
   477	
   478	        build_time = time.time() - start_time
   479	        metrics.build_time_seconds = build_time
   480	
   481	        # Update statistics
   482	        self.stats["total_builds"] += 1
   483	        self.stats["avg_build_time"] = (
   484	            self.stats["avg_build_time"] * (self.stats["total_builds"] - 1) + build_time
   485	        ) / self.stats["total_builds"]
   486	
   487	        logger.info(
   488	            f"Graph built in {build_time:.2f}s - Nodes: {metrics.total_nodes}, Edges: {metrics.total_edges}"
   489	        )
   490	
   491	        return {
   492	            "nodes": list(self.nodes.values()),
   493	            "edges": self.edges,
   494	            "metrics": metrics,
   495	            "build_time": build_time,
   496	        }
   497	
   498	    def _process_entities(self, entities: List[Dict], source_id: Optional[str]):
   499	        """Process entities into graph nodes"""
   500	        for entity in entities:
   501	            node_id = entity.get("id") or entity.get("text", "")
   502	
   503	            if node_id in self.nodes:
   504	                # Update existing node
   505	                node = self.nodes[node_id]
   506	                node.updated_at = datetime.now()
   507	                if source_id and source_id not in node.source_documents:
   508	                    node.source_documents.append(source_id)
   509	            else:
   510	                # Create new node
   511	                node = GraphNode(
   512	                    id=node_id,
   513	                    label=entity.get("label", "UNKNOWN"),
   514	                    node_type=entity.get("type", "entity"),
   515	                    properties=entity.get("properties", {}),
   516	                    confidence=entity.get("confidence", 1.0),
   517	                    source_documents=[source_id] if source_id else [],
   518	                )
   519	                self.nodes[node_id] = node
   520	
   521	    def _process_relationships(
   522	        self, relationships: List[Dict], source_id: Optional[str]
   523	    ):
   524	        """Process relationships into graph edges"""
   525	        for rel in relationships:
   526	            edge = GraphEdge(
   527	                source_id=rel.get("source_id", ""),
   528	                target_id=rel.get("target_id", ""),
   529	                relationship_type=rel.get("type", "RELATED"),
   530	                properties=rel.get("properties", {}),
   531	                weight=rel.get("weight", 1.0),
   532	                confidence=rel.get("confidence", 1.0),
   533	                evidence=rel.get("evidence", []),
   534	            )
   535	            self.edges.append(edge)
   536	
   537	    def _assess_and_improve_quality(self):
   538	        """Assess and improve graph quality"""
   539	        if not self.enable_quality_assessment:
   540	            return
   541	
   542	        # Assess quality
   543	        metrics = self.quality_assessor.assess_graph_quality(
   544	            list(self.nodes.values()), self.edges
   545	        )
   546	
   547	        # Update node quality scores
   548	        for node in self.nodes.values():
   549	            node.quality_score = self.quality_assessor._assess_node_quality(node)
   550	            if node.quality_score >= 0.7:
   551	                node.validation_status = "validated"
   552	
   553	        # Update edge quality scores
   554	        for edge in self.edges:
   555	            edge.quality_score = self.quality_assessor._assess_edge_quality(edge)
   556	            if edge.quality_score >= 0.7:
   557	                edge.validation_status = "validated"
   558	
   559	    def _build_indexes(self):
   560	        """Build graph indexes for fast lookup"""
   561	        # Node index
   562	        self.node_index = {node.id: node for node in self.nodes.values()}
   563	
   564	        # Edge index (adjacency list)
   565	        self.edge_index = defaultdict(list)
   566	        for edge in self.edges:
   567	            self.edge_index[edge.source_id].append(edge)
   568	
   569	    # ------------------------------------------------------------------
   570	    # Graph traversal helpers (exposed for reasoning components)
   571	    # ------------------------------------------------------------------
   572	
   573	    def ensure_indexes(self):
   574	        """Ensure adjacency indexes are available"""
   575	        if not self.node_index or not self.edge_index:
   576	            self._build_indexes()
   577	
   578	    def get_nodes(self) -> Dict[str, GraphNode]:
   579	        """Return mapping of graph nodes"""
   580	        return self.nodes
   581	
   582	    def get_edges(self) -> List[GraphEdge]:
   583	        """Return list of graph edges"""
   584	        return self.edges
   585	
   586	    def get_neighbors(self, node_id: str) -> List[str]:
   587	        """Return adjacent node IDs for a given source"""
   588	        self.ensure_indexes()
   589	        return [edge.target_id for edge in self.edge_index.get(node_id, [])]
   590	
   591	    def has_edge(self, source_id: str, target_id: str) -> bool:
   592	        """Check whether an edge exists between two nodes"""
   593	        self.ensure_indexes()
   594	        return any(
   595	            edge.target_id == target_id for edge in self.edge_index.get(source_id, [])
   596	        )
   597	
   598	    def remove_node(self, node_id: str):
   599	        """Remove node and all incident edges"""
   600	        if node_id in self.nodes:
   601	            del self.nodes[node_id]
   602	        self.edges = [
   603	            edge
   604	            for edge in self.edges
   605	            if edge.source_id != node_id and edge.target_id != node_id
   606	        ]
   607	        self._build_indexes()
   608	
   609	    def clear_edges(self):
   610	        """Remove all edges (used for test mutations)"""
   611	        self.edges = []
   612	        self._build_indexes()
   613	
   614	    def remove_edge(self, source_id: str, target_id: str):
   615	        """Remove a specific directed edge"""
   616	        self.edges = [
   617	            edge
   618	            for edge in self.edges
   619	            if not (edge.source_id == source_id and edge.target_id == target_id)
   620	        ]

```


**Tool Call: Read file `mahoun/ultra_systems/graph/ultra_graph_builder.py` (lines 360-620)**
Status: Completed

```KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py
   360	    ) -> Dict[str, Any]:
   361	        """
   362	        Build graph from entities and relationships
   363	        
   364	        Args:
   365	            entities: List of entities
   366	            relationships: List of relationships
   367	            source_id: Source document/dataset ID
   368	        
   369	        Returns:
   370	            Graph build result
   371	        """
   372	        start_time = time.time()
   373	        
   374	        print(f"🏗️ Building graph with {len(entities)} entities and {len(relationships)} relationships...")
   375	        
   376	        # Process entities
   377	        self._process_entities(entities, source_id)
   378	        
   379	        # Process relationships
   380	        self._process_relationships(relationships, source_id)
   381	        
   382	        # Quality assessment
   383	        if self.enable_quality_assessment:
   384	            self._assess_and_improve_quality()
   385	        
   386	        # Build indexes
   387	        self._build_indexes()
   388	        
   389	        # Calculate metrics
   390	        metrics = self._calculate_metrics()
   391	        
   392	        build_time = time.time() - start_time
   393	        metrics.build_time_seconds = build_time
   394	        
   395	        # Update statistics
   396	        self.stats["total_builds"] += 1
   397	        self.stats["avg_build_time"] = (
   398	            (self.stats["avg_build_time"] * (self.stats["total_builds"] - 1) + build_time)
   399	            / self.stats["total_builds"]
   400	        )
   401	        
   402	        print(f"   ✅ Graph built in {build_time:.2f}s")
   403	        print(f"   📊 Nodes: {metrics.total_nodes}, Edges: {metrics.total_edges}")
   404	        
   405	        return {
   406	            "nodes": list(self.nodes.values()),
   407	            "edges": self.edges,
   408	            "metrics": metrics,
   409	            "build_time": build_time
   410	        }
   411	    
   412	    def _process_entities(self, entities: List[Dict], source_id: Optional[str]):
   413	        """Process entities into graph nodes"""
   414	        for entity in entities:
   415	            node_id = entity.get('id') or entity.get('text', '')
   416	            
   417	            if node_id in self.nodes:
   418	                # Update existing node
   419	                node = self.nodes[node_id]
   420	                node.updated_at = datetime.now()
   421	                if source_id and source_id not in node.source_documents:
   422	                    node.source_documents.append(source_id)
   423	            else:
   424	                # Create new node
   425	                # Validate label against governance allowlist
   426	                try:
   427	                    from mahoun.core.governance.validator_pipeline import validate_node_label
   428	                    validate_node_label(entity.get('label', 'UNKNOWN'))
   429	                except Exception:
   430	                    # Re-raise governance violations to callers
   431	                    raise
   432	
   433	                node = GraphNode(
   434	                    id=node_id,
   435	                    label=entity.get('label', 'UNKNOWN'),
   436	                    node_type=entity.get('type', 'entity'),
   437	                    properties=entity.get('properties', {}),
   438	                    confidence=entity.get('confidence', 1.0),
   439	                    source_documents=[source_id] if source_id else []
   440	                )
   441	                self.nodes[node_id] = node
   442	    
   443	    def _process_relationships(self, relationships: List[Dict], source_id: Optional[str]):
   444	        """Process relationships into graph edges"""
   445	        for rel in relationships:
   446	            edge = GraphEdge(
   447	                source_id=rel.get('source_id', ''),
   448	                target_id=rel.get('target_id', ''),
   449	                relationship_type=rel.get('type', 'RELATED'),
   450	                properties=rel.get('properties', {}),
   451	                weight=rel.get('weight', 1.0),
   452	                confidence=rel.get('confidence', 1.0),
   453	                evidence=rel.get('evidence', [])
   454	            )
   455	            self.edges.append(edge)
   456	    
   457	    def _assess_and_improve_quality(self):
   458	        """Assess and improve graph quality"""
   459	        if not self.enable_quality_assessment:
   460	            return
   461	        
   462	        # Assess quality
   463	        metrics = self.quality_assessor.assess_graph_quality(
   464	            list(self.nodes.values()),
   465	            self.edges
   466	        )
   467	        
   468	        # Update node quality scores
   469	        for node in self.nodes.values():
   470	            node.quality_score = self.quality_assessor._assess_node_quality(node)
   471	            if node.quality_score >= 0.7:
   472	                node.validation_status = "validated"
   473	        
   474	        # Update edge quality scores
   475	        for edge in self.edges:
   476	            edge.quality_score = self.quality_assessor._assess_edge_quality(edge)
   477	            if edge.quality_score >= 0.7:
   478	                edge.validation_status = "validated"
   479	    
   480	    def _build_indexes(self):
   481	        """Build graph indexes for fast lookup"""
   482	        # Node index
   483	        self.node_index = {node.id: node for node in self.nodes.values()}
   484	        
   485	        # Edge index (adjacency list)
   486	        self.edge_index = defaultdict(list)
   487	        for edge in self.edges:
   488	            self.edge_index[edge.source_id].append(edge)
   489	    
   490	    def _calculate_metrics(self) -> GraphMetrics:
   491	        """Calculate graph metrics"""
   492	        if self.enable_quality_assessment:
   493	            return self.quality_assessor.assess_graph_quality(
   494	                list(self.nodes.values()),
   495	                self.edges
   496	            )
   497	        else:
   498	            return GraphMetrics(
   499	                total_nodes=len(self.nodes),
   500	                total_edges=len(self.edges)
   501	            )
   502	    
   503	    def query_neighbors(self, node_id: str, max_depth: int = 1) -> List[GraphNode]:
   504	        """Query neighbors of a node"""
   505	        if node_id not in self.node_index:
   506	            return []
   507	        
   508	        neighbors = set()
   509	        queue = deque([(node_id, 0)])
   510	        visited = {node_id}
   511	        
   512	        while queue:
   513	            current_id, depth = queue.popleft()
   514	            
   515	            if depth >= max_depth:
   516	                continue
   517	            
   518	            # Get outgoing edges
   519	            for edge in self.edge_index[current_id]:
   520	                target_id = edge.target_id
   521	                
   522	                if target_id not in visited:
   523	                    visited.add(target_id)
   524	                    neighbors.add(target_id)
   525	                    queue.append((target_id, depth + 1))
   526	        
   527	        return [self.node_index[nid] for nid in neighbors if nid in self.node_index]
   528	    
   529	    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
   530	        """Find shortest path between two nodes"""
   531	        if source_id not in self.node_index or target_id not in self.node_index:
   532	            return None
   533	        
   534	        # BFS
   535	        queue = deque([(source_id, [source_id])])
   536	        visited = {source_id}
   537	        
   538	        while queue:
   539	            current_id, path = queue.popleft()
   540	            
   541	            if current_id == target_id:
   542	                return path
   543	            
   544	            for edge in self.edge_index[current_id]:
   545	                neighbor_id = edge.target_id
   546	                
   547	                if neighbor_id not in visited:
   548	                    visited.add(neighbor_id)
   549	                    queue.append((neighbor_id, path + [neighbor_id]))
   550	        
   551	        return None
   552	    
   553	    def get_subgraph(self, node_ids: List[str]) -> Dict[str, Any]:
   554	        """Extract subgraph containing specified nodes"""
   555	        subgraph_nodes = [
   556	            self.node_index[nid] for nid in node_ids
   557	            if nid in self.node_index
   558	        ]
   559	        
   560	        node_id_set = set(node_ids)
   561	        subgraph_edges = [
   562	            edge for edge in self.edges
   563	            if edge.source_id in node_id_set and edge.target_id in node_id_set
   564	        ]
   565	        
   566	        return {
   567	            "nodes": subgraph_nodes,
   568	            "edges": subgraph_edges
   569	        }
   570	    
   571	    def compute_analytics(self) -> Dict[str, Any]:
   572	        """Compute advanced graph analytics"""
   573	        if not self.enable_analytics:
   574	            return {}
   575	        
   576	        nodes = list(self.nodes.values())
   577	        
   578	        analytics = {
   579	            "centrality": self.analytics_engine.compute_centrality(nodes, self.edges),
   580	            "communities": self.analytics_engine.find_communities(nodes, self.edges),
   581	        }
   582	        
   583	        return analytics
   584	    
   585	    def get_statistics(self) -> Dict:
   586	        """Get builder statistics"""
   587	        return self.stats
   588	    
   589	    def export_to_json(self, filepath: str):
   590	        """Export graph to JSON"""
   591	        graph_data = {
   592	            "nodes": [
   593	                {
   594	                    "id": node.id,
   595	                    "label": node.label,
   596	                    "type": node.node_type,
   597	                    "properties": node.properties,
   598	                    "confidence": node.confidence,
   599	                    "quality_score": node.quality_score
   600	                }
   601	                for node in self.nodes.values()
   602	            ],
   603	            "edges": [
   604	                {
   605	                    "source": edge.source_id,
   606	                    "target": edge.target_id,
   607	                    "type": edge.relationship_type,
   608	                    "weight": edge.weight,
   609	                    "confidence": edge.confidence,
   610	                    "quality_score": edge.quality_score
   611	                }
   612	                for edge in self.edges
   613	            ]
   614	        }
   615	        
   616	        with open(filepath, 'w', encoding='utf-8') as f:
   617	            json.dump(graph_data, f, ensure_ascii=False, indent=2)
   618	        
   619	        print(f"📁 Graph exported to {filepath}")
   620	    

```


## Assistant

<thinking>
**Inspecting tests for behavior**

I need to check tests to understand the expected behavior and see what might break if the interface changes. The user mentioned not to edit the self_improve call that uses `graph_builder.export_to_neo4j(self.neo4j_adapter)`, but maybe it’s okay to change if we adjust the graph_builder interface. It seems the export function is tightly linked to tests under `governed_session`. I should also look into tests for `entity_linker` and validate entity properties and allowed relationships. I’ll make sure to read relevant sections carefully.
</thinking>

I’ve found the existing tests, which helps preserve the current public shape. I’m checking the governance validators next so the new local allowlists line up with the kernel’s expectations instead of fighting them.

**Tool Call: Search files for regex `def\s+validate_node_label|ALLOWED_NODE_LABELS|allowed.*relationship|validate_relationship_write|validate_node_write`**
Status: Completed

Found 11 matches:

## Matches in KingMahouN/mahoun/core/governance/mutation_boundary.py

### class GovernedNeo4jSession › def write_node › L495-499
```
        node_data["provenance"] = generated_provenance

        result = self._pipeline.validate_node_write(
            node_data, self._correlation_id
        )
```

### class GovernedNeo4jSession › def write_relationship › L611-615
```
        rel_data["provenance"] = generated_provenance

        result = self._pipeline.validate_relationship_write(
            source_type=source_type,
            relationship_type=relationship_type,
```

### class GovernedWriteTransaction › def queue_node › def validate › L880-883
```
        def validate():
            return self._session._pipeline.validate_node_write(
                node_data, self._session._correlation_id
            )
```

### class GovernedWriteTransaction › def queue_relationship › def validate › L918-925
```
        def validate():
            return self._session._pipeline.validate_relationship_write(
                source_type=source_type,
                relationship_type=relationship_type,
                target_type=target_type,
                relationship_data=rel_data,
                correlation_id=self._session._correlation_id,
            )
```

## Matches in KingMahouN/mahoun/core/governance/validator_pipeline.py

### L44-54
```
ALLOWED_NODE_LABELS: frozenset[str] = frozenset({
    # Legal domain
    "Law", "Case", "Document", "Entity", "Topic",
    "LawArticle", "Verdict", "Evidence", "Person",
    "Article",
    "Organization", "Court", "Tag",
    # Graph infrastructure
    "GraphNode",
    # Pipeline / ingestion
    "Chunk",
})
```

### def validate_node_label › L57-67
```
def validate_node_label(label: str, correlation_id: Optional[str] = None) -> None:
    """Reject any node label not in ALLOWED_NODE_LABELS.

    Quarantined* prefixes are stripped before lookup so that
    GovernedNeo4jSession's quarantine routing still works.

    Raises:
        GovernanceViolationError: category=ONTOLOGY_VIOLATION, severity=CRITICAL
    """
    # Basic empty / whitespace check
    if not label or not label.strip():
```

83 lines remaining in ancestor node. Read the file to see all.

### def validate_node_label › L131-135
```

    # Final allowlist membership check
    if base_label not in ALLOWED_NODE_LABELS:
        raise GovernanceViolationError(
            GovernanceViolation(
```

### def validate_node_label › L139-140
```
                    f"Node label '{base_label}' is not in the MAHOUN ontology allowlist. "
                    f"Allowed labels: {sorted(ALLOWED_NODE_LABELS)}"
```

### def validate_node_label › L142-146
```
                details={
                    "label": label,
                    "base_label": base_label,
                    "allowed": sorted(ALLOWED_NODE_LABELS),
                },
```

### class ValidatorPipeline › def validate_node_write › L212-216
```
        self._custom_gates.append((name, gate_fn))

    def validate_node_write(
        self,
        node_data: Dict[str, Any],
```

### class ValidatorPipeline › def validate_relationship_write › L282-286
```
        )

    def validate_relationship_write(
        self,
        source_type: str,
```


**Tool Call: Read file `mahoun/core/governance/validator_pipeline.py` (lines 1-260)**
Status: Completed

```KingMahouN/mahoun/core/governance/validator_pipeline.py
     1	"""
     2	MAHOUN Validator Pipeline
     3	==========================
     4	
     5	Classification: CRITICAL / RUNTIME GOVERNANCE
     6	Purpose: Unified validation pipeline for all graph mutations.
     7	
     8	Every graph write passes through this pipeline before persistence.
     9	The pipeline composes ProvenanceTracker, OntologyEnforcer, and
    10	schema validation into a single fail-closed gate.
    11	
    12	Author: MAHOUN Platform Governance Council
    13	Version: 1.0.0
    14	"""
    15	
    16	from __future__ import annotations
    17	
    18	import hashlib
    19	import json
    20	import re
    21	import unicodedata
    22	from dataclasses import dataclass, field
    23	from datetime import datetime, timezone
    24	from typing import Any, Callable, Dict, List, Optional, Sequence
    25	
    26	from mahoun.core.governance.violations import (
    27	    GovernanceViolation,
    28	    GovernanceViolationError,
    29	    ViolationCategory,
    30	    ViolationSeverity,
    31	)
    32	from mahoun.core.governance.provenance_tracker import ProvenanceMetadata, ProvenanceTracker
    33	from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
    34	
    35	
    36	# ============================================================================
    37	# AUTHORITATIVE NODE LABEL ALLOWLIST (I4)
    38	# ============================================================================
    39	# Every node label that may exist in the MAHOUN graph must appear here.
    40	# write_node() rejects any label not in this set — fail-closed.
    41	# To add a new label: add it here AND add the corresponding OntologyRule.
    42	# Quarantined* prefixes are handled by the quarantine routing in write_node;
    43	# only the BASE label needs to be in this allowlist.
    44	ALLOWED_NODE_LABELS: frozenset[str] = frozenset({
    45	    # Legal domain
    46	    "Law", "Case", "Document", "Entity", "Topic",
    47	    "LawArticle", "Verdict", "Evidence", "Person",
    48	    "Article",
    49	    "Organization", "Court", "Tag",
    50	    # Graph infrastructure
    51	    "GraphNode",
    52	    # Pipeline / ingestion
    53	    "Chunk",
    54	})
    55	
    56	
    57	def validate_node_label(label: str, correlation_id: Optional[str] = None) -> None:
    58	    """Reject any node label not in ALLOWED_NODE_LABELS.
    59	
    60	    Quarantined* prefixes are stripped before lookup so that
    61	    GovernedNeo4jSession's quarantine routing still works.
    62	
    63	    Raises:
    64	        GovernanceViolationError: category=ONTOLOGY_VIOLATION, severity=CRITICAL
    65	    """
    66	    # Basic empty / whitespace check
    67	    if not label or not label.strip():
    68	        raise GovernanceViolationError(
    69	            GovernanceViolation(
    70	                category=ViolationCategory.ONTOLOGY_VIOLATION,
    71	                severity=ViolationSeverity.CRITICAL,
    72	                message="Node label must be a non-empty string.",
    73	                details={"label": repr(label)},
    74	                source="validate_node_label",
    75	                correlation_id=correlation_id,
    76	            )
    77	        )
    78	
    79	    # Normalize Unicode to NFKC to collapse homoglyphs and compatibility forms
    80	    norm_label = unicodedata.normalize("NFKC", label)
    81	
    82	    # If normalization changes the label, treat as possible homoglyph injection
    83	    if norm_label != label:
    84	        raise GovernanceViolationError(
    85	            GovernanceViolation(
    86	                category=ViolationCategory.ONTOLOGY_VIOLATION,
    87	                severity=ViolationSeverity.CRITICAL,
    88	                message=(
    89	                    "Node label contains compatibility/unicode variants (homoglyphs). "
    90	                    "Use ASCII canonical labels only."
    91	                ),
    92	                details={"label": label, "normalized": norm_label},
    93	                source="validate_node_label",
    94	                correlation_id=correlation_id,
    95	            )
    96	        )
    97	
    98	    # Strip Quarantined prefix for allowlist lookup (preserve normalization)
    99	    base_label = norm_label[len("Quarantined"):] if norm_label.startswith("Quarantined") else norm_label
   100	
   101	    # Reject any non-ASCII characters to prevent homoglyph attacks
   102	    if any(ord(ch) > 127 for ch in base_label):
   103	        raise GovernanceViolationError(
   104	            GovernanceViolation(
   105	                category=ViolationCategory.ONTOLOGY_VIOLATION,
   106	                severity=ViolationSeverity.CRITICAL,
   107	                message=(
   108	                    "Node label contains non-ASCII characters — possible homoglyph injection."
   109	                ),
   110	                details={"label": label, "normalized": norm_label},
   111	                source="validate_node_label",
   112	                correlation_id=correlation_id,
   113	            )
   114	        )
   115	
   116	    # Enforce strict label character rules (no punctuation, no whitespace)
   117	    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", base_label):
   118	        raise GovernanceViolationError(
   119	            GovernanceViolation(
   120	                category=ViolationCategory.ONTOLOGY_VIOLATION,
   121	                severity=ViolationSeverity.CRITICAL,
   122	                message=(
   123	                    "Node label contains forbidden characters or formatting. "
   124	                    "Allowed pattern: ^[A-Za-z][A-Za-z0-9_]*$"
   125	                ),
   126	                details={"label": label, "normalized": norm_label},
   127	                source="validate_node_label",
   128	                correlation_id=correlation_id,
   129	            )
   130	        )
   131	
   132	    # Final allowlist membership check
   133	    if base_label not in ALLOWED_NODE_LABELS:
   134	        raise GovernanceViolationError(
   135	            GovernanceViolation(
   136	                category=ViolationCategory.ONTOLOGY_VIOLATION,
   137	                severity=ViolationSeverity.CRITICAL,
   138	                message=(
   139	                    f"Node label '{base_label}' is not in the MAHOUN ontology allowlist. "
   140	                    f"Allowed labels: {sorted(ALLOWED_NODE_LABELS)}"
   141	                ),
   142	                details={
   143	                    "label": label,
   144	                    "base_label": base_label,
   145	                    "allowed": sorted(ALLOWED_NODE_LABELS),
   146	                },
   147	                source="validate_node_label",
   148	                correlation_id=correlation_id,
   149	            )
   150	        )
   151	
   152	
   153	@dataclass(frozen=True)
   154	class ValidationGateResult:
   155	    """Immutable result of a single validation gate."""
   156	    gate_name: str
   157	    passed: bool
   158	    violation: Optional[GovernanceViolation] = None
   159	
   160	
   161	@dataclass(frozen=True)
   162	class PipelineResult:
   163	    """Immutable result of the full validation pipeline."""
   164	    passed: bool
   165	    gate_results: tuple  # Tuple[ValidationGateResult, ...]
   166	    correlation_id: str
   167	    timestamp: str
   168	    pipeline_hash: str
   169	
   170	    @property
   171	    def violations(self) -> List[GovernanceViolation]:
   172	        return [g.violation for g in self.gate_results if g.violation is not None]
   173	
   174	
   175	# Type alias for custom validation functions
   176	ValidationGate = Callable[[Dict[str, Any], Optional[str]], None]
   177	
   178	
   179	class ValidatorPipeline:
   180	    """Unified validation pipeline for graph mutations.
   181	
   182	    Composes multiple validation gates into a single fail-closed pipeline.
   183	    If any gate fails, the entire pipeline fails immediately.
   184	
   185	    Built-in gates:
   186	        1. Provenance validation (via ProvenanceTracker)
   187	        2. Ontology validation (via OntologyEnforcer, for relationships)
   188	        3. Schema validation (required fields check)
   189	
   190	    Custom gates can be added via add_gate().
   191	    """
   192	
   193	    def __init__(
   194	        self,
   195	        provenance_tracker: Optional[ProvenanceTracker] = None,
   196	        ontology_enforcer: Optional[OntologyEnforcer] = None,
   197	    ) -> None:
   198	        self._provenance = provenance_tracker or ProvenanceTracker()
   199	        self._ontology = ontology_enforcer or OntologyEnforcer()
   200	        self._custom_gates: List[tuple] = []  # List of (name, gate_fn)
   201	
   202	    def add_gate(self, name: str, gate_fn: ValidationGate) -> None:
   203	        """Add a custom validation gate to the pipeline.
   204	
   205	        Args:
   206	            name: Gate name for audit trail.
   207	            gate_fn: Function(data, correlation_id) -> None.
   208	                     Must raise GovernanceViolationError on failure.
   209	        """
   210	        if not name:
   211	            raise ValueError("Gate name cannot be empty")
   212	        self._custom_gates.append((name, gate_fn))
   213	
   214	    def validate_node_write(
   215	        self,
   216	        node_data: Dict[str, Any],
   217	        correlation_id: Optional[str] = None,
   218	    ) -> PipelineResult:
   219	        """Validate a node write through the full pipeline.
   220	
   221	        Gates executed:
   222	            1. Provenance check
   223	            2. Required fields check
   224	            3. Custom gates
   225	
   226	        Args:
   227	            node_data: Node data dictionary. Must contain 'provenance'.
   228	            correlation_id: Optional correlation ID.
   229	
   230	        Returns:
   231	            PipelineResult (always passed=True if we return).
   232	
   233	        Raises:
   234	            GovernanceViolationError: On any gate failure (fail-fast).
   235	        """
   236	        results: List[ValidationGateResult] = []
   237	        ts = datetime.now(timezone.utc).isoformat()
   238	        cid = correlation_id or ""
   239	
   240	        # Gate 0: Node label allowlist (I4 — ontology enforcement)
   241	        label = node_data.get("_label") or node_data.get("label", "")
   242	        # label may also be passed separately; if absent we skip here and
   243	        # rely on write_node() to pass it explicitly via validate_node_label().
   244	        if label:
   245	            validate_node_label(label, correlation_id)
   246	        results.append(ValidationGateResult(gate_name="label_allowlist", passed=True))
   247	
   248	        # Gate 1: Provenance
   249	        try:
   250	            self._provenance.validate_node_provenance(node_data, correlation_id)
   251	            results.append(ValidationGateResult(gate_name="provenance", passed=True))
   252	        except GovernanceViolationError:
   253	            raise  # Fail-fast, no catch
   254	
   255	        # Gate 2: Required fields
   256	        required = {"id"}
   257	        missing = required - set(node_data.keys())
   258	        if missing:
   259	            raise GovernanceViolationError(
   260	                GovernanceViolation(

```


**Tool Call: Read file `tests/test_governance_bypass_prevention.py` (lines 160-260)**
Status: Completed

```KingMahouN/tests/test_governance_bypass_prevention.py
   160	    """Test that core modules maintain dependency purity"""
   161	    
   162	    def test_core_dependency_validation_works(self):
   163	        """Core dependency validator should detect violations"""
   164	        from mahoun.core.dependency_validator import validate_core_dependencies
   165	        
   166	        # This test verifies the validator works
   167	        violations = validate_core_dependencies()
   168	        
   169	        # Print violations for debugging (if any)
   170	        if violations:
   171	            print("Dependency violations found:")
   172	            for violation in violations:
   173	                print(f"  - {violation}")
   174	        
   175	        # In a clean system, there should be minimal violations
   176	        # (we allow pydantic and yaml as documented exceptions)
   177	
   178	
   179	class TestGraphBuildersGovernance:
   180	    """Test that Graph builders enforce governance kernel rules"""
   181	    
   182	    def test_ultra_graph_builder_type_enforcement(self):
   183	        from mahoun.ultra_systems.graph.ultra_graph_builder import UltraGraphBuilder
   184	        
   185	        builder = UltraGraphBuilder()
   186	        
   187	        # Must raise TypeError with non-Neo4jConnection
   188	        with pytest.raises(TypeError, match="Neo4jConnection"):
   189	            builder.export_to_neo4j("not_a_connection")
   190	            
   191	    def test_entity_linker_type_enforcement(self):
   192	        from mahoun.graph.builders.entity_linker import EntityLinker
   193	        
   194	        linker = EntityLinker()
   195	        
   196	        # Must raise TypeError with non-Neo4jConnection
   197	        with pytest.raises(TypeError, match="Neo4jConnection"):
   198	            linker.submit_to_neo4j([], [], connection="not_a_connection")
   199	            
   200	    def test_entity_linker_label_validation(self):
   201	        from mahoun.graph.builders.entity_linker import EntityLinker, GraphNodeSpec, GraphEdgeSpec
   202	        from mahoun.graph.neo4j.connection import get_connection
   203	        
   204	        connection = get_connection()
   205	        linker = EntityLinker()
   206	        
   207	        invalid_node = GraphNodeSpec(label="HackerLabel", node_id="test1")
   208	        with pytest.raises(ValueError, match="Invalid node label"):
   209	            linker._merge_node(invalid_node, connection)
   210	            
   211	        invalid_edge = GraphEdgeSpec(from_label="Case", from_id="1", to_label="Case", to_id="2", relationship_type="HACKER_REL")
   212	        with pytest.raises(ValueError, match="Invalid relationship type"):
   213	            linker._create_edge(invalid_edge, connection)
   214	            
   215	    @patch('mahoun.graph.neo4j.connection.Neo4jConnection.governed_session')
   216	    def test_ultra_graph_builder_uses_governed_session(self, mock_governed_session):
   217	        from mahoun.ultra_systems.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode
   218	        from mahoun.graph.neo4j.connection import get_connection
   219	        
   220	        connection = get_connection()
   221	        builder = UltraGraphBuilder()
   222	        
   223	        builder.nodes["test"] = GraphNode(id="test", label="GraphNode", node_type="test")
   224	        
   225	        mock_session = mock_governed_session.return_value.__enter__.return_value
   226	        builder.export_to_neo4j(connection)
   227	        
   228	        mock_governed_session.assert_called()
   229	        mock_session.run.assert_called()
   230	
   231	    @patch('mahoun.graph.neo4j.connection.Neo4jConnection.governed_session')
   232	    def test_entity_linker_uses_governed_session(self, mock_governed_session):
   233	        from mahoun.graph.builders.entity_linker import EntityLinker, GraphNodeSpec
   234	        from mahoun.graph.neo4j.connection import get_connection
   235	        
   236	        connection = get_connection()
   237	        linker = EntityLinker()
   238	        
   239	        valid_node = GraphNodeSpec(label="Case", node_id="test1")
   240	        
   241	        mock_session = mock_governed_session.return_value.__enter__.return_value
   242	        linker._merge_node(valid_node, connection)
   243	        
   244	        mock_governed_session.assert_called()
   245	        mock_session.run.assert_called()
   246	
   247	if __name__ == "__main__":
   248	    pytest.main([__file__, "-v", "--tb=short"])
```


**Tool Call: Read file `tests/governance/test_hardened_infrastructure.py` (lines 260-360)**
Status: Completed

```KingMahouN/tests/governance/test_hardened_infrastructure.py
   260	        with pytest.raises(GraduationError) as exc_info:
   261	            manager.graduate_node(
   262	                node_id="node-200",
   263	                quarantined_label="Verdict",  # Invalid quarantined label format
   264	                target_label="Verdict",
   265	                verified_confidence=1.0,
   266	                attestation_source="human_verifier:ali",
   267	            )
   268	            
   269	        assert "does not start with 'Quarantined'" in str(exc_info.value)
   270	
   271	
   272	# ============================================================================
   273	# TESTS: Facade Backdoor Seal
   274	# ============================================================================
   275	
   276	class TestFacadeBackdoorSeal:
   277	    """Verifies that all pipelines route writes through governed session only."""
   278	
   279	    def test_graph_builder_rejects_raw_adapter(self):
   280	        """Test that UltraGraphBuilder throws exception if raw adapter is passed."""
   281	        builder = UltraGraphBuilder()
   282	        raw_adapter = MagicMock()
   283	        
   284	        # Should raise TypeError because raw adapter bypasses governance
   285	        with pytest.raises(TypeError) as exc_info:
   286	            builder.export_to_neo4j(raw_adapter)
   287	            
   288	        assert "GOVERNANCE VIOLATION" in str(exc_info.value)
   289	
   290	    def test_graph_builder_export_via_governed_session(self, governed_session, mock_raw_executor):
   291	        """Test that UltraGraphBuilder successfully exports via GovernedNeo4jSession."""
   292	        builder = UltraGraphBuilder()
   293	        
   294	        # Populate nodes/edges in builder
   295	        node_1 = GraphNode(
   296	            id="node-300",
   297	            label="ماده 10",
   298	            node_type="Verdict",
   299	            confidence=1.0,
   300	        )
   301	        node_2 = GraphNode(
   302	            id="node-400",
   303	            label="ماده 11",
   304	            node_type="Verdict",
   305	            confidence=0.75,  # Low confidence! Routes to quarantine
   306	        )
   307	        builder.nodes[node_1.id] = node_1
   308	        builder.nodes[node_2.id] = node_2
   309	        
   310	        edge = GraphEdge(
   311	            source_id="node-300",
   312	            target_id="node-400",
   313	            relationship_type="CITES",
   314	            confidence=0.9,
   315	        )
   316	        builder.edges.append(edge)
   317	        
   318	        # Export via governed session
   319	        builder.export_to_neo4j(governed_session)
   320	        
   321	        # Ensure raw executor was called (node writes + relationship write)
   322	        assert mock_raw_executor.call_count == 3
   323	
   324	
   325	# ============================================================================
   326	# TESTS: Parallel LLM Refinement & High-Throughput
   327	# ============================================================================
   328	
   329	class TestParallelLLMRefinement:
   330	    """Verifies that the concurrent LLM refinement performs safely and fast."""
   331	
   332	    @pytest.mark.asyncio
   333	    async def test_parallel_refinement_performance(self):
   334	        """Test that parallelized refinement runs under concurrency controls."""
   335	        # Create pipeline instance
   336	        ner_engine = MagicMock()
   337	        ner_engine.extract.return_value = {
   338	            "Verdict": [{"text": f"Entity {i}", "confidence": 0.9} for i in range(15)]
   339	        }
   340	        
   341	        mapper = MagicMock()
   342	        
   343	        # Mock LLM validation helper to be async with a slight sleep
   344	        async def mock_llm_validate(entity, text):
   345	            await asyncio.sleep(0.05)  # Simulate API latency
   346	            return True, 0.95, "Valid entity"
   347	
   348	        gate = MagicMock()
   349	        id_gen = MagicMock()
   350	        id_gen.generate_entity_id.side_effect = lambda entity_type, entity_data, context: f"id-{entity_data['text']}"
   351	
   352	        # Initialize pipeline
   353	        pipeline = HardenedLegalPipeline(
   354	            ner_engine=ner_engine,
   355	            mapper=mapper,
   356	            llm_refiner=MagicMock(),
   357	            gate=gate,
   358	            id_gen=id_gen,
   359	        )
   360	        pipeline._llm_validate_entity = mock_llm_validate

```


## Assistant

<thinking>
**Considering test requirements**

I see that tests currently expect session.run in entity_linker and ultra_systems. It seems like there will likely need to be some updates if we can patch. The user mentioned patching only files and not the tests, but I’m concerned that any changes might cause tests to fail. Perhaps I should inspect the ontology enforcer relation allowlist to ensure edge types like CITES are addressed. Let’s search for more information.
</thinking>

I want the local relationship allowlists to stay consistent with the canonical ontology, so I’m checking the ontology rules for the edge types these builders currently emit.

**Tool Call: Search files for regex `PARTY_IN|REFERS_TO|HANDLED_BY|ABOUT|RELATED|CITES|PART_OF`**
Status: Completed

Found 3 matches:

## Matches in KingMahouN/mahoun/core/governance/ontology_enforcer.py

### class OntologyRule › L31-39
```
    """Immutable ontology rule defining valid relationship patterns.

    Attributes:
        source_type: Type of the source node (e.g., 'Law', 'Case').
        relationship_type: Type of relationship (e.g., 'CITES', 'AMENDS').
        target_type: Type of the target node.
        description: Human-readable description of the rule.
        bidirectional: Whether the relationship can go both ways.
    """
```

### L49-59
```
_DEFAULT_ONTOLOGY_RULES: Tuple[OntologyRule, ...] = (
    # Law relationships
    OntologyRule("Law", "AMENDS", "Law", "A law amends another law"),
    OntologyRule("Law", "REPEALS", "Law", "A law repeals another law"),
    OntologyRule("Law", "SUPERSEDES", "Law", "A law supersedes another law"),
    OntologyRule("Law", "REFERENCES", "Law", "A law references another law"),
    OntologyRule("Law", "IMPLEMENTS", "Law", "A law implements another law"),
    # Case relationships
    OntologyRule("Case", "CITES", "Law", "A case cites a law"),
    OntologyRule("Case", "CITES", "Case", "A case cites another case"),
    OntologyRule("Case", "APPLIES", "Law", "A case applies a law"),
```

35 lines remaining in ancestor node. Read the file to see all.

### L81-91
```
OntologyRule("Evidence", "EXTRACTED_FROM", "Document", "Evidence extracted from a document"),
# Verdict ingestion relationships (used by upsert_verdict_struct)
OntologyRule("Verdict", "REFERS_TO", "LawArticle", "A verdict refers to a law article"),
OntologyRule("Verdict", "HAS_PARTY", "Person", "A verdict has a party"),
OntologyRule("Verdict", "HAS_TAG", "Tag", "A verdict has a tag"),
# Test/Quarantine relationships (used by test_graph_builder_export_via_governed_session)
OntologyRule("Verdict", "CITES", "QuarantinedVerdict", "A verdict cites a quarantined verdict used in tests"),
    # Graph builder relationships (used by UltraGraphBuilder.export_to_neo4j)
    OntologyRule("GraphNode", "RELATED", "GraphNode", "Generic graph node relationship"),
    # Document-LawArticle linkage
    OntologyRule("Document", "REFERENCES", "LawArticle", "A document references a law article"),
```


**Tool Call: Read file `mahoun/core/governance/ontology_enforcer.py` (lines 1-320)**
Status: Completed

```KingMahouN/mahoun/core/governance/ontology_enforcer.py
     1	"""
     2	MAHOUN Ontology Enforcer
     3	=========================
     4	
     5	Classification: CRITICAL / RUNTIME GOVERNANCE
     6	Purpose: Enforce ontology rules before relationship creation.
     7	
     8	Relationships between graph nodes must conform to the MAHOUN legal
     9	ontology. Invalid relationships are rejected immediately with
    10	GovernanceViolationError.
    11	
    12	Author: MAHOUN Platform Governance Council
    13	Version: 1.0.0
    14	"""
    15	
    16	from __future__ import annotations
    17	
    18	from dataclasses import dataclass, field
    19	from typing import Dict, FrozenSet, Optional, Set, Tuple
    20	
    21	from mahoun.core.governance.violations import (
    22	    GovernanceViolation,
    23	    GovernanceViolationError,
    24	    ViolationCategory,
    25	    ViolationSeverity,
    26	)
    27	
    28	
    29	@dataclass(frozen=True)
    30	class OntologyRule:
    31	    """Immutable ontology rule defining valid relationship patterns.
    32	
    33	    Attributes:
    34	        source_type: Type of the source node (e.g., 'Law', 'Case').
    35	        relationship_type: Type of relationship (e.g., 'CITES', 'AMENDS').
    36	        target_type: Type of the target node.
    37	        description: Human-readable description of the rule.
    38	        bidirectional: Whether the relationship can go both ways.
    39	    """
    40	
    41	    source_type: str
    42	    relationship_type: str
    43	    target_type: str
    44	    description: str = ""
    45	    bidirectional: bool = False
    46	
    47	
    48	# Default MAHOUN legal ontology rules
    49	_DEFAULT_ONTOLOGY_RULES: Tuple[OntologyRule, ...] = (
    50	    # Law relationships
    51	    OntologyRule("Law", "AMENDS", "Law", "A law amends another law"),
    52	    OntologyRule("Law", "REPEALS", "Law", "A law repeals another law"),
    53	    OntologyRule("Law", "SUPERSEDES", "Law", "A law supersedes another law"),
    54	    OntologyRule("Law", "REFERENCES", "Law", "A law references another law"),
    55	    OntologyRule("Law", "IMPLEMENTS", "Law", "A law implements another law"),
    56	    # Case relationships
    57	    OntologyRule("Case", "CITES", "Law", "A case cites a law"),
    58	    OntologyRule("Case", "CITES", "Case", "A case cites another case"),
    59	    OntologyRule("Case", "APPLIES", "Law", "A case applies a law"),
    60	    OntologyRule("Case", "INTERPRETS", "Law", "A case interprets a law"),
    61	    OntologyRule("Case", "OVERRULES", "Case", "A case overrules another case"),
    62	    OntologyRule("Case", "FOLLOWS", "Case", "A case follows another case"),
    63	    OntologyRule("Case", "DISTINGUISHES", "Case", "A case distinguishes another"),
    64	    # Document relationships
    65	    OntologyRule("Document", "REFERENCES", "Law", "A document references a law"),
    66	    OntologyRule("Document", "REFERENCES", "Case", "A document references a case"),
    67	    OntologyRule("Document", "CONTAINS", "Entity", "A document contains an entity"),
    68	    OntologyRule("Document", "DISCUSSES", "Topic", "A document discusses a topic"),
    69	    # Entity relationships
    70	    OntologyRule("Entity", "MENTIONED_IN", "Document", "An entity is mentioned in a document"),
    71	    OntologyRule("Entity", "PARTY_TO", "Case", "An entity is party to a case"),
    72	    OntologyRule("Entity", "SUBJECT_OF", "Law", "An entity is subject of a law"),
    73	    # Topic relationships
    74	    OntologyRule("Topic", "RELATES_TO", "Topic", "A topic relates to another topic", bidirectional=True),
    75	# Verdict/Reasoning relationships
    76	OntologyRule("Verdict", "BASED_ON", "Law", "A verdict is based on a law"),
    77	OntologyRule("Verdict", "BASED_ON", "Case", "A verdict is based on a case"),
    78	OntologyRule("Verdict", "DERIVED_FROM", "Evidence", "A verdict is derived from evidence"),
    79	OntologyRule("Evidence", "SUPPORTS", "Verdict", "Evidence supports a verdict"),
    80	OntologyRule("Evidence", "CONTRADICTS", "Verdict", "Evidence contradicts a verdict"),
    81	OntologyRule("Evidence", "EXTRACTED_FROM", "Document", "Evidence extracted from a document"),
    82	# Verdict ingestion relationships (used by upsert_verdict_struct)
    83	OntologyRule("Verdict", "REFERS_TO", "LawArticle", "A verdict refers to a law article"),
    84	OntologyRule("Verdict", "HAS_PARTY", "Person", "A verdict has a party"),
    85	OntologyRule("Verdict", "HAS_TAG", "Tag", "A verdict has a tag"),
    86	# Test/Quarantine relationships (used by test_graph_builder_export_via_governed_session)
    87	OntologyRule("Verdict", "CITES", "QuarantinedVerdict", "A verdict cites a quarantined verdict used in tests"),
    88	    # Graph builder relationships (used by UltraGraphBuilder.export_to_neo4j)
    89	    OntologyRule("GraphNode", "RELATED", "GraphNode", "Generic graph node relationship"),
    90	    # Document-LawArticle linkage
    91	    OntologyRule("Document", "REFERENCES", "LawArticle", "A document references a law article"),
    92	    # Person reverse lookup
    93	    OntologyRule("Person", "PARTY_TO", "Verdict", "A person is party to a verdict"),
    94	)
    95	
    96	
    97	class OntologyEnforcer:
    98	    """Enforce ontology rules before relationship creation.
    99	
   100	    This enforcer validates that relationship types between node types
   101	    conform to the MAHOUN legal ontology. Invalid relationships are
   102	    rejected with GovernanceViolationError.
   103	
   104	    The enforcer operates in STRICT mode only — no warnings, no soft
   105	    failures, no fallbacks.
   106	    """
   107	
   108	    def __init__(
   109	        self,
   110	        rules: Optional[Tuple[OntologyRule, ...]] = None,
   111	    ) -> None:
   112	        """Initialize the ontology enforcer.
   113	
   114	        Args:
   115	            rules: Ontology rules to enforce. Defaults to MAHOUN legal ontology.
   116	        """
   117	        effective_rules = rules if rules is not None else _DEFAULT_ONTOLOGY_RULES
   118	        # Build lookup index: (source_type, relationship_type, target_type) -> rule
   119	        self._rules: Dict[Tuple[str, str, str], OntologyRule] = {}
   120	        for rule in effective_rules:
   121	            key = (rule.source_type, rule.relationship_type, rule.target_type)
   122	            self._rules[key] = rule
   123	            if rule.bidirectional:
   124	                reverse_key = (
   125	                    rule.target_type,
   126	                    rule.relationship_type,
   127	                    rule.source_type,
   128	                )
   129	                self._rules[reverse_key] = rule
   130	
   131	        # Build valid relationship types per source type
   132	        self._valid_relationships: Dict[str, Set[str]] = {}
   133	        for src, rel, tgt in self._rules:
   134	            if src not in self._valid_relationships:
   135	                self._valid_relationships[src] = set()
   136	            self._valid_relationships[src].add(rel)
   137	
   138	    def validate_relationship(
   139	        self,
   140	        source_type: str,
   141	        relationship_type: str,
   142	        target_type: str,
   143	        correlation_id: Optional[str] = None,
   144	    ) -> None:
   145	        """Validate that a relationship conforms to the ontology.
   146	
   147	        Args:
   148	            source_type: Type of the source node.
   149	            relationship_type: Type of the relationship.
   150	            target_type: Type of the target node.
   151	            correlation_id: Optional correlation ID for tracing.
   152	
   153	        Raises:
   154	            GovernanceViolationError: If the relationship is not in the ontology.
   155	        """
   156	        key = (source_type, relationship_type, target_type)
   157	
   158	        if key not in self._rules:
   159	            # Determine the specific failure reason
   160	            if source_type not in self._valid_relationships:
   161	                detail_msg = (
   162	                    f"Unknown source type '{source_type}'. "
   163	                    f"Known types: {sorted(self._valid_relationships.keys())}"
   164	                )
   165	            elif relationship_type not in self._valid_relationships.get(
   166	                source_type, set()
   167	            ):
   168	                detail_msg = (
   169	                    f"Invalid relationship '{relationship_type}' for "
   170	                    f"source type '{source_type}'. "
   171	                    f"Valid relationships: "
   172	                    f"{sorted(self._valid_relationships.get(source_type, set()))}"
   173	                )
   174	            else:
   175	                detail_msg = (
   176	                    f"Relationship '{source_type} -[{relationship_type}]-> "
   177	                    f"{target_type}' does not match any ontology rule"
   178	                )
   179	
   180	            raise GovernanceViolationError(
   181	                GovernanceViolation(
   182	                    category=ViolationCategory.ONTOLOGY_VIOLATION,
   183	                    severity=ViolationSeverity.CRITICAL,
   184	                    message=(
   185	                        f"Ontology violation: {source_type} "
   186	                        f"-[{relationship_type}]-> {target_type}"
   187	                    ),
   188	                    details={
   189	                        "source_type": source_type,
   190	                        "relationship_type": relationship_type,
   191	                        "target_type": target_type,
   192	                        "detail": detail_msg,
   193	                    },
   194	                    source="OntologyEnforcer",
   195	                    correlation_id=correlation_id,
   196	                )
   197	            )
   198	
   199	    def get_valid_relationships(
   200	        self, source_type: str
   201	    ) -> FrozenSet[str]:
   202	        """Get valid relationship types for a given source type.
   203	
   204	        Args:
   205	            source_type: Node type to query.
   206	
   207	        Returns:
   208	            Frozen set of valid relationship type names.
   209	        """
   210	        return frozenset(self._valid_relationships.get(source_type, set()))
   211	
   212	    def get_valid_targets(
   213	        self, source_type: str, relationship_type: str
   214	    ) -> FrozenSet[str]:
   215	        """Get valid target types for a source type and relationship.
   216	
   217	        Args:
   218	            source_type: Source node type.
   219	            relationship_type: Relationship type.
   220	
   221	        Returns:
   222	            Frozen set of valid target node types.
   223	        """
   224	        targets: Set[str] = set()
   225	        for (src, rel, tgt), _rule in self._rules.items():
   226	            if src == source_type and rel == relationship_type:
   227	                targets.add(tgt)
   228	        return frozenset(targets)
   229	
   230	    @property
   231	    def rule_count(self) -> int:
   232	        """Total number of ontology rules (including bidirectional expansions)."""
   233	        return len(self._rules)

```


## Assistant

<thinking>
**Investigating ontology issues**

I’m noticing that the ontology doesn’t include specific entity-linking relationships like PARTY_IN. That seems like it could be a governance issue. Currently, the functions _merge_node and _create_edge are using node labels such as Person and Case. When write_relationship is called, it checks against validate_relationship_write, which might fail if there’s no corresponding ontology rule. I should take a closer look at validate_relationship_write—it could be using relation data alone, without relying on labels. I'll need to search through the code for clarification.
</thinking>

I noticed the canonical ontology may not currently include some `entity_linker` edge shapes, so I’m reading the relationship validator to see exactly what governed writes will enforce there.

**Tool Call: Read file `mahoun/core/governance/validator_pipeline.py` (lines 280-400)**
Status: Completed

```KingMahouN/mahoun/core/governance/validator_pipeline.py
   280	            timestamp=ts,
   281	            pipeline_hash=self._compute_hash(node_data),
   282	        )
   283	
   284	    def validate_relationship_write(
   285	        self,
   286	        source_type: str,
   287	        relationship_type: str,
   288	        target_type: str,
   289	        relationship_data: Dict[str, Any],
   290	        correlation_id: Optional[str] = None,
   291	    ) -> PipelineResult:
   292	        """Validate a relationship write through the full pipeline.
   293	
   294	        Gates executed:
   295	            1. Ontology check
   296	            2. Provenance check (on relationship data)
   297	            3. Custom gates
   298	
   299	        Raises:
   300	            GovernanceViolationError: On any gate failure.
   301	        """
   302	        results: List[ValidationGateResult] = []
   303	        ts = datetime.now(timezone.utc).isoformat()
   304	        cid = correlation_id or ""
   305	
   306	        # Gate 1: Ontology
   307	        self._ontology.validate_relationship(
   308	            source_type, relationship_type, target_type, correlation_id
   309	        )
   310	        results.append(ValidationGateResult(gate_name="ontology", passed=True))
   311	
   312	        # Gate 2: Provenance on relationship
   313	        prov = relationship_data.get("provenance")
   314	        if prov is None:
   315	            raise GovernanceViolationError(
   316	                GovernanceViolation(
   317	                    category=ViolationCategory.MISSING_PROVENANCE,
   318	                    severity=ViolationSeverity.CRITICAL,
   319	                    message=(
   320	                        f"Relationship write rejected: missing provenance for "
   321	                        f"{source_type} -[{relationship_type}]-> {target_type}"
   322	                    ),
   323	                    details={
   324	                        "source_type": source_type,
   325	                        "relationship_type": relationship_type,
   326	                        "target_type": target_type,
   327	                    },
   328	                    source="ValidatorPipeline",
   329	                    correlation_id=correlation_id,
   330	                )
   331	            )
   332	        results.append(ValidationGateResult(gate_name="provenance", passed=True))
   333	
   334	        # Gate 3+: Custom gates
   335	        for gate_name, gate_fn in self._custom_gates:
   336	            gate_fn(relationship_data, correlation_id)
   337	            results.append(ValidationGateResult(gate_name=gate_name, passed=True))
   338	
   339	        return PipelineResult(
   340	            passed=True,
   341	            gate_results=tuple(results),
   342	            correlation_id=cid,
   343	            timestamp=ts,
   344	            pipeline_hash=self._compute_hash(relationship_data),
   345	        )
   346	
   347	    @staticmethod
   348	    def _compute_hash(data: Dict[str, Any]) -> str:
   349	        """Compute deterministic hash of mutation data."""
   350	        canonical = json.dumps(data, sort_keys=True, default=str)
   351	        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
   352	
   353	
   354	# ============================================================================
   355	# Strict Schema Validation Gate
   356	# ============================================================================
   357	
   358	import logging
   359	from pydantic import BaseModel, ValidationError
   360	
   361	logger = logging.getLogger(__name__)
   362	
   363	# Central registry mapping Neo4j node labels to their Pydantic schemas.
   364	# Any label not in this registry will be rejected by the schema gate.
   365	SCHEMA_REGISTRY: Dict[str, type] = {}
   366	
   367	
   368	def register_schema(label: str, model_cls: type) -> None:
   369	    """Register a Pydantic model for a given Neo4j label.
   370	
   371	    Args:
   372	        label: Neo4j node label (e.g., "Verdict", "LawArticle").
   373	        model_cls: Pydantic BaseModel subclass with extra="forbid".
   374	    """
   375	    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
   376	        raise TypeError(f"model_cls must be a Pydantic BaseModel subclass, got {model_cls}")
   377	    SCHEMA_REGISTRY[label] = model_cls
   378	    logger.info(f"Schema registered: {label} → {model_cls.__name__}")
   379	
   380	
   381	def strict_schema_validation_gate(
   382	    data: Dict[str, Any],
   383	    correlation_id: Optional[str] = None,
   384	    *,
   385	    label: Optional[str] = None,
   386	) -> None:
   387	    """Validate node properties against the registered Pydantic schema.
   388	
   389	    This function is designed to be used as a custom gate in ValidatorPipeline.
   390	
   391	    Args:
   392	        data: Node data dictionary.
   393	        correlation_id: Optional correlation ID.
   394	        label: Neo4j label to validate against. If None, checks data["_label"].
   395	
   396	    Raises:
   397	        GovernanceViolationError: If schema validation fails.
   398	    """
   399	    resolved_label = label or data.get("_label")
   400	    if not resolved_label:

```


**Tool Call: Search files for regex `PARTY_IN|HANDLED_BY|ABOUT|REFERS_TO`**
Status: Completed

Showing matches 1-20 (there were more matches found; use offset: 20 to see next page):

## Matches in KingMahouN/.test_classification_backup/tests/contracts/test_core_contracts.py

### class TestReasoningStepContract › def test_valid_reasoning_step › L328-333
```
        step = ReasoningStepContract(
            step="Analyze question",
            reasoning="The question asks about...",
            confidence=0.9,
            evidence=["fact1", "fact2"]
        )
```

## Matches in KingMahouN/.test_classification_backup/tests/test_config_validator.py

### class TestConfigurationValidator › def test_graph_disabled_warning › L147-157
```
    def test_graph_disabled_warning(self, caplog):
        """Test: Graph disabled generates warning about verdict generation"""
        import logging
        caplog.set_level(logging.WARNING)

        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=False,
            graph_backend="disabled_fallback",
            lora_training_enabled=False,
            lora_inference_backend="remote",
```

14 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/.test_classification_backup/tests/test_core_comprehensive.py

### class TestPartyInfo › def test_party_info_empty › L18-28
```
    """Tests for PartyInfo schema"""
    
    def test_party_info_empty(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo()
        assert party.title is None
        assert party.name is None
        assert party.father_name is None
    
    def test_party_info_full(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
```

10 lines remaining in ancestor node. Read the file to see all.

### class TestPartyInfo › def test_party_info_extra_fields › L32-36
```
        assert party.father_name == "محمد"
    
    def test_party_info_extra_fields(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo(name="Test", custom_field="extra")
```

## Matches in KingMahouN/.test_classification_backup/tests/test_e2e_scenario.py

### async def test_legal_dispute_workflow › L59-69
```
    with patch("mahoun.rag.query_router.QueryRouter.route") as mock_route:
        # Simulate RAG finding the relevant chunk about payment
        mock_route.return_value.rag_result.results = [
            MagicMock(content="خریدار از پرداخت وجه خودداری کرده", doc_id="doc_123", score=0.9)
        ]
        
        dispute_result = await dispute_agent.process({
            "query": "مشکل پرداخت وجه",
            "documents": ["doc_123"]
        })
        
```

14 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/.test_classification_backup/tests/test_extreme_hard_scenario.py

### class TestExtremeHardScenario › def test_extreme_legal_dispute_with_multiple_contradictions › L371-375
```
        # 12. ENFORCE SEMANTIC COVERAGE OF THE QUESTION
        # ============================================================
        # The question asks about 4 decision dimensions:
        # 1. Contract binding / الزام‌آور بودن
        # 2. Damages / خسارت
```

## Matches in KingMahouN/.test_classification_backup/tests/test_graph_native_extreme_hard.py

### class TestGraphNativeExtremeHardAudit › def test_extreme_graph_native_audit_ablated_graph › L291-295
```
        # ============================================================
        # Reasoning chain should be shorter OR used_rule_ids fewer than FULL GRAPH case
        # OR final_answer must explicitly warn about degraded mode
        
        final_answer_lower = result_ablated.final_answer.lower()
```

## Matches in KingMahouN/.test_classification_backup/tests/test_graph_native_ultra_extreme.py

### class TestUltraExtremeGraphNative › def _setup_full_graph_engine › L108-112
```
        
        # ============================================================
        # Temporal Override Rules (NOT about confidence; test temporal conflict)
        # ============================================================
        # r_old_law: N10 -> N4A (0.70)
```

## Matches in KingMahouN/.test_classification_backup/tests/test_graph_to_fol.py

### def sample_graph › L92-98
```
        {
            "source_id": "person_123",
            "target_id": "case_001",
            "type": "PARTY_IN",
            "properties": {"role": "plaintiff"},
            "confidence": 0.9
        },
```

### def sample_graph › L99-104
```
        {
            "source_id": "case_001",
            "target_id": "law_article_10",
            "type": "REFERS_TO",
            "confidence": 0.85
        }
```

## Matches in KingMahouN/.test_classification_backup/tests/test_graph_to_fol_standalone.py

### def test_edge_conversion › L133-139
```
        GraphEdge(
            source_id="person_123",
            target_id="case_001",
            relationship_type="PARTY_IN",
            properties={"role": "plaintiff"},
            confidence=0.9
        ),
```

### def test_edge_conversion › L140-145
```
        GraphEdge(
            source_id="case_001",
            target_id="law_article_10",
            relationship_type="REFERS_TO",
            confidence=0.85
        )
```

### def test_combined_conversion › L201-207
```
        GraphEdge(
            source_id="person_123",
            target_id="case_001",
            relationship_type="PARTY_IN",
            properties={"role": "plaintiff"},
            confidence=0.9
        )
```

## Matches in KingMahouN/.test_classification_backup/tests/test_knowledge_graph_semantic.py

### class TestSemanticRuleMatching › def test_semantic_rule_matching_enabled › L150-154
```
        assert len(results) > 0
        
        # Should find RULE_001 (about فسخ and عدم پرداخت)
        rule_ids = [r["rule_id"] for r in results]
        assert "RULE_001" in rule_ids
```

## Matches in KingMahouN/api/main.py

### async def submit_feedback › L649-654
```
    """
    Submit user feedback

    This endpoint receives feedback from users about query responses
    and feeds it into the self-improvement loop.
    """
```

## Matches in KingMahouN/api/routers/finetuning.py

### async def get_finetuning_job › L256-258
```
    """
    Get detailed information about a specific job.
    """
```

## Matches in KingMahouN/api/routers/ingest.py

### async def get_chunking_stats › L673-677
```
    """
    Get chunking statistics from the pipeline

    Returns statistics about chunking performance and quality.
    """
```

## Matches in KingMahouN/api/routers/mahoun.py

### class ContractQueryRequest › L110-115
```
    """Request for contract query"""

    query: str = Field(..., description="Question about contract")
    clause_number: Optional[str] = Field(None, description="Specific clause number")
    contract_id: Optional[str] = Field(None, description="Contract identifier")
    top_k: int = Field(10, description="Number of results", ge=1, le=20)
```

### L378-384
```
@router.post(
    "/ask-contract",
    response_model=ContractQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask contract question",
    description="Ask questions about contracts and get answers with citations",
)
```

## Matches in KingMahouN/demos/demo_bank_scenario.py

### class MockEngine › async def generate_verdict › L13-23
```
    async def generate_verdict(self, question, facts):
        print(f"Thinking about: {question}")
        print(f"Processing facts: {facts}")
        await asyncio.sleep(1) # Simulate thinking
        
        return {
            "final_verdict": "REJECTED",
            "confidence": 0.95,
            "steps": [
                {
                    "step": 1,
```

20 lines remaining in ancestor node. Read the file to see all.


## Assistant

I have enough to draft the hardening logic, but I still need the top of the legacy `ultra_systems` file to patch imports cleanly and keep the edit minimal.

**Tool Call: Read file `mahoun/ultra_systems/graph/ultra_graph_builder.py` (lines 1-120)**
Status: Completed

```KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py
     1	"""
     2	Ultra-Advanced Graph Builder
     3	============================
     4	Enterprise-grade knowledge graph construction and management.
     5	
     6	Features:
     7	- Multi-source graph construction
     8	- Real-time graph updates
     9	- Graph neural network integration
    10	- Distributed graph processing
    11	- Graph quality assessment
    12	- Automated graph validation
    13	- Graph versioning and rollback
    14	- Cross-domain graph linking
    15	- Graph analytics and insights
    16	- Performance optimization
    17	"""
    18	
    19	import time
    20	import json
    21	import numpy as np
    22	from typing import List, Dict, Optional, Tuple, Set, Any
    23	from dataclasses import dataclass, field
    24	from datetime import datetime
    25	from collections import defaultdict, deque, Counter
    26	
    27	# Try to import Neo4j adapter
    28	try:
    29	    from graph.neo4j_adapter import Neo4jAdapter
    30	    HAS_NEO4J = True
    31	except ImportError:
    32	    Neo4jAdapter = object  # Dummy class for type hints
    33	    HAS_NEO4J = False
    34	
    35	# ============================================================================
    36	# Graph Data Structures
    37	# ============================================================================
    38	
    39	@dataclass
    40	class GraphNode:
    41	    """Enhanced graph node"""
    42	    id: str
    43	    label: str
    44	    node_type: str
    45	    properties: Dict[str, Any] = field(default_factory=dict)
    46	    
    47	    # Advanced features
    48	    confidence: float = 1.0
    49	    source_documents: List[str] = field(default_factory=list)
    50	    created_at: datetime = field(default_factory=datetime.now)
    51	    updated_at: datetime = field(default_factory=datetime.now)
    52	    
    53	    # Quality metrics
    54	    quality_score: float = 0.0
    55	    validation_status: str = "pending"
    56	
    57	
    58	@dataclass
    59	class GraphEdge:
    60	    """Enhanced graph edge"""
    61	    source_id: str
    62	    target_id: str
    63	    relationship_type: str
    64	    properties: Dict[str, Any] = field(default_factory=dict)
    65	    
    66	    # Advanced features
    67	    weight: float = 1.0
    68	    confidence: float = 1.0
    69	    evidence: List[str] = field(default_factory=list)
    70	    created_at: datetime = field(default_factory=datetime.now)
    71	    
    72	    # Quality metrics
    73	    quality_score: float = 0.0
    74	    validation_status: str = "pending"
    75	
    76	
    77	@dataclass
    78	class GraphMetrics:
    79	    """Graph quality and performance metrics"""
    80	    total_nodes: int = 0
    81	    total_edges: int = 0
    82	    avg_degree: float = 0.0
    83	    clustering_coefficient: float = 0.0
    84	    density: float = 0.0
    85	    
    86	    # Quality metrics
    87	    avg_node_quality: float = 0.0
    88	    avg_edge_quality: float = 0.0
    89	    validation_rate: float = 0.0
    90	    
    91	    # Performance metrics
    92	    build_time_seconds: float = 0.0
    93	    memory_usage_mb: float = 0.0
    94	    query_latency_ms: float = 0.0
    95	
    96	
    97	# ============================================================================
    98	# Graph Quality Assessor
    99	# ============================================================================
   100	
   101	class GraphQualityAssessor:
   102	    """Assess and improve graph quality"""
   103	    
   104	    def __init__(self):
   105	        self.quality_rules = self._build_quality_rules()
   106	        print("📊 Graph Quality Assessor initialized")
   107	    
   108	    def assess_graph_quality(
   109	        self,
   110	        nodes: List[GraphNode],
   111	        edges: List[GraphEdge]
   112	    ) -> GraphMetrics:
   113	        """Assess overall graph quality"""
   114	        metrics = GraphMetrics()
   115	        
   116	        # Basic metrics
   117	        metrics.total_nodes = len(nodes)
   118	        metrics.total_edges = len(edges)
   119	        
   120	        if nodes:

```


**Tool Call: Read file `mahoun/graph/ultra_graph_builder.py` (lines 1-120)**
Status: Completed

```KingMahouN/mahoun/graph/ultra_graph_builder.py
     1	"""
     2	Ultra-Advanced Graph Builder
     3	============================
     4	Enterprise-grade knowledge graph construction and management.
     5	
     6	Features:
     7	- Multi-source graph construction
     8	- Real-time graph updates
     9	- Graph neural network integration
    10	- Distributed graph processing
    11	- Graph quality assessment
    12	- Automated graph validation
    13	- Graph versioning and rollback
    14	- Cross-domain graph linking
    15	- Graph analytics and insights
    16	- Performance optimization
    17	"""
    18	
    19	import time
    20	import json
    21	import logging
    22	from enum import Enum
    23	from typing import Any, Dict, List, Optional, Set, Tuple
    24	from dataclasses import dataclass, field
    25	from datetime import datetime
    26	from collections import defaultdict, deque, Counter
    27	from types import MappingProxyType
    28	
    29	try:
    30	    import numpy as np
    31	
    32	    HAS_NUMPY = True
    33	except ImportError:
    34	    np = None  # type: ignore
    35	    HAS_NUMPY = False
    36	
    37	from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph
    38	from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    39	
    40	logger = logging.getLogger(__name__)
    41	
    42	
    43	# ============================================================================
    44	# Graph Operation Modes
    45	# ============================================================================
    46	
    47	
    48	class GraphMode(str, Enum):
    49	    """
    50	    Graph operation modes for different use cases.
    51	
    52	    Modes:
    53	    - STRICT: Full validation, fail on any errors (production, high-stakes)
    54	    - PERMISSIVE: Log warnings but continue (development, exploratory)
    55	    - MINIMAL: Skip heavy operations, minimal resource usage (laptop, CI)
    56	    """
    57	
    58	    STRICT = "strict"
    59	    PERMISSIVE = "permissive"
    60	    MINIMAL = "minimal"
    61	
    62	
    63	# Try to import Neo4j adapter
    64	try:
    65	    from mahoun.graph.neo4j_adapter import Neo4jAdapter
    66	
    67	    HAS_NEO4J = True
    68	except ImportError:
    69	    Neo4jAdapter = object  # Dummy class for type hints
    70	    HAS_NEO4J = False
    71	
    72	# ============================================================================
    73	# Graph Data Structures
    74	# ============================================================================
    75	
    76	
    77	@dataclass
    78	class GraphNode:
    79	    """Enhanced graph node with provenance"""
    80	
    81	    id: str
    82	    label: str
    83	    node_type: str
    84	    provenance: ProvenanceMetadata
    85	    properties: Dict[str, Any] = field(default_factory=dict)
    86	
    87	    # Advanced features
    88	    confidence: float = 1.0
    89	    source_documents: List[str] = field(default_factory=list)
    90	    created_at: datetime = field(default_factory=datetime.now)
    91	    updated_at: datetime = field(default_factory=datetime.now)
    92	
    93	    # Quality metrics
    94	    quality_score: float = 0.0
    95	    validation_status: str = "pending"
    96	
    97	
    98	@dataclass
    99	class GraphEdge:
   100	    """Enhanced graph edge"""
   101	
   102	    source_id: str
   103	    target_id: str
   104	    relationship_type: str
   105	    properties: Dict[str, Any] = field(default_factory=dict)
   106	
   107	    # Advanced features
   108	    weight: float = 1.0
   109	    confidence: float = 1.0
   110	    evidence: List[str] = field(default_factory=list)
   111	    created_at: datetime = field(default_factory=datetime.now)
   112	
   113	    # Quality metrics
   114	    quality_score: float = 0.0
   115	    validation_status: str = "pending"
   116	
   117	
   118	@dataclass
   119	class GraphMetrics:
   120	    """Graph quality and performance metrics"""

```


**Tool Call: Search files for regex `operation_type\s*=`**
Status: Completed

Found 5 matches:

## Matches in KingMahouN/mahoun/graph/builders/entity_linker.py

### class EntityLinker › def _merge_node › L768-772
```
        with connection.governed_session(
            correlation_id=correlation_id,
            actor_id="entity-linker",
            operation_type="entity_merge_node"
        ) as session:
```

### class EntityLinker › def _create_edge › L802-806
```
        with self.connection.governed_session(
            correlation_id=correlation_id,
            actor_id="entity-linker",
            operation_type="entity_create_edge"
        ) as session:
```

## Matches in KingMahouN/mahoun/graph/legal_cypher_queries.py

### class LegalQueryExecutor › async def execute_legal_query › L748-752
```
                with self.connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="legal-query-executor",
                    operation_type="legal_mutation"
                ) as session:
```

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def export_to_neo4j › L666-670
```
                with connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="ultra-graph-builder",
                    operation_type="export_node"
                ) as session:
```

### class UltraGraphBuilder › def export_to_neo4j › L698-702
```
                with connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="ultra-graph-builder",
                    operation_type="export_edge"
                ) as session:
```


## Assistant

<thinking>
**Investigating GraphNode issues**

I'm exploring why another file is using an unsupported operation type. It seems I shouldn’t alter that file. Instead, I want to dive into the `GraphNode` dataclass within `mahoun/graph/ultra_graph_builder.py`, which has a required field for provenance without a default. The `build_graph` function creates `GraphNode` instances without providing provenance, which could be a bug. I should check lines 77-85 for clarity. It's also puzzling that `_process_entities` constructs `GraphNode` without this required field, leading to potential TypeErrors. I wonder if tests instantiate it successfully, or if a default provenance is being set somewhere.

**Searching for provenance issues**

I'm planning to search within the file for occurrences of "provenance=" and "__post_init__". This could help me pinpoint where provenance is being handled or if there are issues with its initialization. I want to be thorough in my search to ensure I find any related code or comments that clarify how provenance is supposed to function. Hopefully, this provides insight into any potential bugs related to the `GraphNode` construction. Let's see what I can discover!
</thinking>

There’s a suspicious `GraphNode` provenance requirement in `mahoun/graph/ultra_graph_builder.py`, so I’m checking whether the class defines a default or post-init behavior before I assume anything about export-time property shaping.

**Tool Call: Search files for regex `__post_init__|provenance\s*=|ProvenanceMetadata\(`**
Status: Completed

No matches found

**Tool Call: Read file `mahoun/core/governance/provenance_tracker.py` (lines 1-220)**
Status: Completed

```KingMahouN/mahoun/core/governance/provenance_tracker.py
     1	"""
     2	MAHOUN Provenance Tracker
     3	==========================
     4	
     5	Classification: CRITICAL / RUNTIME GOVERNANCE
     6	Purpose: Enforce mandatory provenance metadata on all graph writes.
     7	
     8	Every node and relationship added to the knowledge graph MUST carry
     9	provenance metadata. Writes without provenance are rejected immediately
    10	with GovernanceViolationError.
    11	
    12	Provenance metadata is immutable after creation (frozen dataclass).
    13	
    14	Author: MAHOUN Platform Governance Council
    15	Version: 1.0.0
    16	"""
    17	
    18	from __future__ import annotations
    19	
    20	from dataclasses import dataclass
    21	from datetime import datetime, timezone
    22	from typing import Any, Dict, FrozenSet, Optional
    23	
    24	from mahoun.core.governance.violations import (
    25	    GovernanceViolation,
    26	    GovernanceViolationError,
    27	    ViolationCategory,
    28	    ViolationSeverity,
    29	)
    30	
    31	# Fields that MUST be present in every provenance record
    32	REQUIRED_PROVENANCE_FIELDS: FrozenSet[str] = frozenset(
    33	    {"source", "timestamp", "correlation_id", "author"}
    34	)
    35	
    36	
    37	# ============================================================================
    38	# INFERENCE PROVENANCE (CRITICAL)
    39	# ============================================================================
    40	
    41	
    42	@dataclass(frozen=True)
    43	class InferenceProvenance:
    44	    """Provenance for reasoning operations (separate from Graph Provenance).
    45	    
    46	    Tracks the symbolic execution path, rule chains, evidence nodes,
    47	    and contradiction branches that led to a conclusion.
    48	    
    49	    CRITICAL: This is separate from GraphProvenance because:
    50	    - Graph provenance tracks WHERE data came from (source document, ingestion pipeline)
    51	    - Inference provenance tracks HOW conclusions were derived (rule chains, evidence nodes)
    52	    
    53	    Usage:
    54	        inference_prov = InferenceProvenance.create(
    55	            proof_id="proof-123",
    56	            rule_chain=("rule_1", "rule_2", "rule_3"),
    57	            evidence_nodes=("node_a", "node_b"),
    58	            contradiction_branches=("branch_x",),
    59	            symbolic_trace_hash="abc123...",
    60	            governance_scope_id="scope-789"
    61	        )
    62	    """
    63	
    64	    # Unique identifier for this inference
    65	    proof_id: str
    66	    
    67	    # Tuple of rule IDs used in this inference (symbolic execution path)
    68	    rule_chain: tuple[str, ...]
    69	    
    70	    # Tuple of evidence node IDs referenced
    71	    evidence_nodes: tuple[str, ...]
    72	    
    73	    # Tuple of contradiction branches encountered
    74	    contradiction_branches: tuple[str, ...]
    75	    
    76	    # Hash of the symbolic execution trace
    77	    symbolic_trace_hash: str
    78	    
    79	    # ID of the governance scope that created this provenance
    80	    governance_scope_id: str
    81	
    82	    @classmethod
    83	    def create(
    84	        cls,
    85	        proof_id: str,
    86	        rule_chain: tuple[str, ...],
    87	        evidence_nodes: tuple[str, ...],
    88	        contradiction_branches: tuple[str, ...],
    89	        symbolic_trace_hash: str,
    90	        governance_scope_id: str,
    91	    ) -> InferenceProvenance:
    92	        """Create inference provenance with governance scope binding.
    93	
    94	        Args:
    95	            proof_id: Unique identifier for this inference.
    96	            rule_chain: Tuple of rule IDs used in this inference.
    97	            evidence_nodes: Tuple of evidence node IDs referenced.
    98	            contradiction_branches: Tuple of contradiction branches encountered.
    99	            symbolic_trace_hash: Hash of the symbolic execution trace.
   100	            governance_scope_id: ID of the governance scope.
   101	
   102	        Returns:
   103	            InferenceProvenance instance.
   104	        """
   105	        return cls(
   106	            proof_id=proof_id,
   107	            rule_chain=rule_chain,
   108	            evidence_nodes=evidence_nodes,
   109	            contradiction_branches=contradiction_branches,
   110	            symbolic_trace_hash=symbolic_trace_hash,
   111	            governance_scope_id=governance_scope_id,
   112	        )
   113	
   114	    def to_dict(self) -> Dict[str, Any]:
   115	        """Serialize to dictionary for storage."""
   116	        return {
   117	            "proof_id": self.proof_id,
   118	            "rule_chain": list(self.rule_chain),
   119	            "evidence_nodes": list(self.evidence_nodes),
   120	            "contradiction_branches": list(self.contradiction_branches),
   121	            "symbolic_trace_hash": self.symbolic_trace_hash,
   122	            "governance_scope_id": self.governance_scope_id,
   123	        }
   124	
   125	
   126	# ============================================================================
   127	# PROVENANCE METADATA
   128	# ============================================================================
   129	"""Immutable provenance record for graph entities.
   130	
   131	Every graph node and relationship must be created with
   132	132: a ProvenanceMetadata instance. This record is immutable
   133	133: and cannot be modified after creation.
   134	
   135	CRITICAL SECURITY ENHANCEMENTS:
   136	136: - provenance_hash: SHA256 hash for cryptographic integrity
   137	137: - provenance_signature: Cryptographic signature for attestation
   138	138: - governance_scope_id: ID of governance scope that created this
   139	139: - runtime_attestation_id: ID of runtime attestation for execution binding
   140	140: - lineage_parent: ID of parent provenance for correlation continuity
   141	141: - timestamp: Internally generated, monotonic, governance-controlled (NOT externally writable)
   142	
   143	Usage:
   144	144: # ONLY via factory method (constructor is disabled)
   145	145: provenance = ProvenanceMetadata.create(
   146	146:     source="document_ingestion",
   147	147:     correlation_id="req-123",
   148	148:     author="user-456",
   149	149:     governance_scope_id="scope-789",
   150	150:     runtime_attestation_id="attest-abc",
   151	151:     lineage_parent=None
   152	152: )
   153	"""
   154	
   155	@dataclass(frozen=True)
   156	class ProvenanceMetadata:
   157	    # Cryptographic attestation fields (GOVERNANCE-CONTROLLED)
   158	    provenance_hash: str
   159	    provenance_signature: str
   160	    governance_scope_id: str
   161	    runtime_attestation_id: str
   162	    lineage_parent: Optional[str]
   163	
   164	    # Core metadata fields (SET AT CREATION TIME ONLY)
   165	    source: str
   166	    timestamp: str
   167	    correlation_id: str
   168	    author: str
   169	    document_id: Optional[str] = None
   170	    pipeline_version: Optional[str] = None
   171	
   172	    def __init_subclass__(cls, **kwargs):
   173	        """Prevent subclassing - only ProvenanceMetadata allowed."""
   174	        super().__init_subclass__(**kwargs)
   175	        # Disable direct instantiation - only create() factory method allowed
   176	
   177	    def __init__(
   178	        self,
   179	        source: str,
   180	        timestamp: str,
   181	        correlation_id: str,
   182	        author: str,
   183	        provenance_hash: str,
   184	        provenance_signature: str,
   185	        governance_scope_id: str,
   186	        runtime_attestation_id: str,
   187	        lineage_parent: Optional[str] = None,
   188	        document_id: Optional[str] = None,
   189	        pipeline_version: Optional[str] = None,
   190	    ) -> None:
   191	        """
   192	        Internal constructor - ONLY called by create() factory method.
   193	        
   194	        CRITICAL: This constructor is for internal use ONLY.
   195	        External code MUST use ProvenanceMetadata.create() factory method.
   196	        """
   197	        # Use object.__setattr__ to bypass frozen dataclass restrictions
   198	        object.__setattr__(self, 'source', source)
   199	        object.__setattr__(self, 'timestamp', timestamp)
   200	        object.__setattr__(self, 'correlation_id', correlation_id)
   201	        object.__setattr__(self, 'author', author)
   202	        object.__setattr__(self, 'provenance_hash', provenance_hash)
   203	        object.__setattr__(self, 'provenance_signature', provenance_signature)
   204	        object.__setattr__(self, 'governance_scope_id', governance_scope_id)
   205	        object.__setattr__(self, 'runtime_attestation_id', runtime_attestation_id)
   206	        object.__setattr__(self, 'lineage_parent', lineage_parent)
   207	        object.__setattr__(self, 'document_id', document_id)
   208	        object.__setattr__(self, 'pipeline_version', pipeline_version)
   209	        
   210	        # Validate all required fields are non-empty
   211	        if not self.source:
   212	            raise ValueError("Provenance 'source' cannot be empty")
   213	        if not self.timestamp:
   214	            raise ValueError("Provenance 'timestamp' cannot be empty")
   215	        if not self.correlation_id:
   216	            raise ValueError("Provenance 'correlation_id' cannot be empty")
   217	        if not self.author:
   218	            raise ValueError("Provenance 'author' cannot be empty")
   219	        if not self.provenance_hash:
   220	            raise ValueError("Provenance 'provenance_hash' cannot be empty")

```


## Assistant

<thinking>
**Evaluating export properties**

I need to inspect the `graph/ultra_graph_builder.py` tests, especially around export properties. It seems like the `ultra_systems` builder always writes the label `GraphNode` and the relation type `RELATED`, while flattening both node and edge properties. I'm considering local allowlists that include base keys, along with extra property keys, which could potentially be empty. I might need to reject non-empty properties to streamline things further.

**Exploring type checking**

I'm considering using `TYPE_CHECKING` to avoid runtime issues. By importing it within the function, I can utilize string annotations, which seems like a solid plan. To ensure everything is explicitly typed, I might want to add `TYPE_CHECKING` at the top of the file. This way, I can keep my code cleaner and more efficient! There’s a lot to think about with these types, but I feel like I'm on the right track.

**Considering module constants**

I think I need to keep things minimal, possibly by defining module constants at the top. Since there aren't any editing constraints from the tool, I feel like I can propose this idea clearly. It’s about setting a good foundation for organization, and I wonder how best to implement this without overcomplicating things. Let’s focus on keeping the code clean and efficient!

**Updating code structure**

I’m considering changing the signature of `submit_to_neo4j` to either `connection: "Neo4jConnection"` or `connection: Neo4jConnection` with TYPE_CHECKING. It looks like I also need to update the docstring for `link_and_submit` to reflect `connection: Optional Neo4jConnection`. Maybe I should use `Optional["Neo4jConnection"]` in the signature due to import constraints.  

In `ultra_graph_builder.py`, I need to remove the Neo4jAdapter import and the try/except block. I’m thinking it might be beneficial to import `ALLOWED_NODE_LABELS` from governance. However, since the user prefers an explicit local allowlist, I could copy those values to define local constants. I wonder if defining `LOCAL_ALLOWED_EXPORT_LABELS = frozenset(ALLOWED_NODE_LABELS)` would work?

**Evaluating flexibility options**

The user requested only a patch, so I’ll keep things minimal and reject anything unknown. I could set the allowlist as empty in the generic builders, but then any single property in `node.properties` would cause a failure. It might be better to allow some commonly used keys instead. I’m considering checking where `UltraGraphBuilder` is present and what properties are passed, but searching for `.build_graph(` or specific usage of properties might be too broad. I’ll see if searching for `"properties": {` near relevant uses works better.
</thinking>

To choose property-key allowlists that won’t be gratuitously disruptive, I’m scanning a few actual `UltraGraphBuilder` call sites and sample payloads for the kinds of `properties` keys they pass today.

**Tool Call: Search files for regex `build_graph\(|properties\s*:\s*\{`**
Status: Completed

Showing matches 1-20 (there were more matches found; use offset: 20 to see next page):

## Matches in KingMahouN/mahoun/graph/concurrent_graph_builder.py

### class ConcurrentGraphBuilder › def build_graph › L104-108
```
            self._read_lock.release()
    
    def build_graph(
        self,
        entities: List[Dict[str, Any]],
```

### class ConcurrentGraphBuilder › def build_graph › L114-117
```
            log.debug(f"Building graph: {len(entities)} entities, {len(relationships)} relationships")
            result = super().build_graph(entities, relationships, **kwargs)
            log.debug("Graph build complete")
            return result
```

## Matches in KingMahouN/mahoun/graph/gnn/gat_reranker.py

### class GATRerankerService › def build_graph_for_document › L673-677
```
            PyG Data object or None
        """
        return self.graph_builder.build_graph(document)
    
    def generate_reasoning(
```

## Matches in KingMahouN/mahoun/graph/gnn/gnn_graph_builder.py

### class GNNGraphBuilder › def build_from_jsonl › L203-207
```
        log.info(f"Loaded {len(documents)} documents")

        graph_data = self.build_graph(documents)

        if output_path:
```

### class GNNGraphBuilder › def build_graph › L225-229
```
        return graph_data

    def build_graph(self, documents: List[Dict[str, Any]]) -> Any:
        """
        Build PyG graph from documents
```

## Matches in KingMahouN/mahoun/graph/gnn/graph_builder.py

### class LegalGraphBuilder › def build_graph › L121-125
```
        return self._embedding_model

    def build_graph(self, document: LegalDocument) -> Optional[Data]:
        """
        Build graph representation of legal document
```

### class LegalGraphBuilder › def build_batch_graphs › L609-611
```
        for doc in iterator:
            graph = self.build_graph(doc)
            graphs.append(graph)
```

## Matches in KingMahouN/mahoun/graph/reasoning/graph_to_fol.py

### def test_graph_to_fol_converter › L1673-1677
```

    # Build graph
    graph.build_graph(entities, relationships)

    # Convert to FOL facts
```

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def build_graph › L425-429
```
        logger.info("Ultra Graph Builder initialized")

    def build_graph(
        self,
        entities: List[Dict],
```

### def test_ultra_graph_builder › L898-902
```

    # Build graph
    result = builder.build_graph(entities, relationships, source_id="doc_001")

    print(f"\n📊 Graph Metrics:")
```

## Matches in KingMahouN/mahoun/mcp/tools/maintenance.py

### class MaintenanceTool › def rebuild_graph › L57-61
```
        }
    
    def rebuild_graph(self) -> Dict[str, Any]:
        """
        Trigger full graph rebuild.
```

## Matches in KingMahouN/mahoun/pipelines/ingestion/nlp_hardening.py

### class HardenedGraphEntityProcessor › L496-500
```
        )

        # graph_entities is List[Dict] ready for UltraGraphBuilder.build_graph()
    """

```

### class HardenedGraphEntityProcessor › def process › L521-531
```
        """
        Run NER on full text, then map entities to chunks with provenance.

        Args:
            text: Full normalized document text
            chunks: List of chunk objects (must have .chunk_id, .text, .start, .end)
            doc_id: Document identifier

        Returns:
            List of dicts ready for UltraGraphBuilder.build_graph(entities=...)

```

3 lines remaining in ancestor node. Read the file to see all.

### def validate_entity_provenance › L610-621
```

    # Provenance fields
    assert "doc_id" in props, f"Entity missing 'doc_id' in properties: {entity}"
    assert "chunk_id" in props, f"Entity missing 'chunk_id' in properties: {entity}"
    assert "doc_start" in props, f"Entity missing 'doc_start' in properties: {entity}"
    assert "doc_end" in props, f"Entity missing 'doc_end' in properties: {entity}"
    assert "chunk_start" in props, (
        f"Entity missing 'chunk_start' in properties: {entity}"
    )
    assert "chunk_end" in props, f"Entity missing 'chunk_end' in properties: {entity}"

    # Integrity checks
```

## Matches in KingMahouN/mahoun/reasoning/reasoning_engine.py

### class DeepLegalReasoningEngine › def _register_rule_with_graph › L148-152
```
            }
        ]
        self.graph_builder.build_graph(entities, relationships)
    
    def deep_reason(
```

## Matches in KingMahouN/mahoun/schemas/contracts/graph_contracts.py

### class BuildGraphInput › L147-151
```
    """
    Input contract for UltraGraphBuilder.build_graph()
    
    Validates: Requirement 2.1 - Graph construction input
    """
```

### class BuildGraphOutput › L364-368
```
    """
    Output contract for UltraGraphBuilder.build_graph()
    
    Validates: Requirement 2.2 - Graph construction output
    """
```

### class BuildGraphError › L432-442
```
    """
    Error contract for UltraGraphBuilder.build_graph() failures.
    
    Validates: Requirement 2.3 - Error handling
    
    Failure Modes:
    - empty_entities: No entities provided
    - invalid_entity_structure: Entity missing required fields
    - invalid_relationship: Relationship references non-existent nodes
    - quality_assessment_failed: Quality assessment failed
    """
```

## Matches in KingMahouN/mahoun/self_improve/ultra_self_improvement_system.py

### class UltraSelfImprovementSystem › def build_knowledge_graph › L1982-1986
```
        
        # Build graph using the graph builder
        result = self.graph_builder.build_graph(entities, relationships, source_id)
        
        # Compute analytics
```

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### class UltraGraphBuilder › def build_graph › L353-357
```
        print("🏗️ Ultra Graph Builder initialized")
    
    def build_graph(
        self,
        entities: List[Dict],
```


**Tool Call: Search files for regex `GraphNode\(|GraphEdge\(`**
Status: Completed

Showing matches 1-20 (there were more matches found; use offset: 20 to see next page):

## Matches in KingMahouN/tests/governance/test_hardened_infrastructure.py

### class TestFacadeBackdoorSeal › def test_graph_builder_export_via_governed_session › L291-301
```
        """Test that UltraGraphBuilder successfully exports via GovernedNeo4jSession."""
        builder = UltraGraphBuilder()
        
        # Populate nodes/edges in builder
        node_1 = GraphNode(
            id="node-300",
            label="ماده 10",
            node_type="Verdict",
            confidence=1.0,
        )
        node_2 = GraphNode(
```

21 lines remaining in ancestor node. Read the file to see all.

### class TestFacadeBackdoorSeal › def test_graph_builder_export_via_governed_session › L308-312
```
        builder.nodes[node_2.id] = node_2
        
        edge = GraphEdge(
            source_id="node-300",
            target_id="node-400",
```

## Matches in KingMahouN/tests/integration/test_complex_legal_reasoning_scenario.py

### def complex_case_graph › L75-85
```
    """Build knowledge graph for complex contract dispute"""
    builder = UltraGraphBuilder()
    
    # === قوانین مرتبط (Relevant Laws) ===
    
    # قانون مدنی - ماده 219: شرط جریمه
    
    law_219 = GraphNode(
        id="law_civil_219",
        label="قانون مدنی ماده 219",
        node_type="Statute",
```

242 lines remaining in ancestor node. Read the file to see all.

### def complex_case_graph › L94-98
```
    
    # ماده 227: قوه قهریه
    law_227 = GraphNode(
        id="law_civil_227",
        label="قانون مدنی ماده 227",
```

### def complex_case_graph › L108-112
```
    
    # قانون تجارت - ماده 10: مسئولیت پیمانکار
    law_commerce_10 = GraphNode(
        id="law_commerce_10",
        label="قانون تجارت ماده 10",
```

### def complex_case_graph › L122-126
```
    # === رویه قضایی (Precedents) ===
    
    precedent_force_majeure = GraphNode(
        id="precedent_940315",
        label="رأی هیأت عمومی دیوان عدالت - 940315",
```

### def complex_case_graph › L135-139
```
    builder.add_node(precedent_force_majeure)
    
    precedent_material_supply = GraphNode(
        id="precedent_920820",
        label="رأی شعبه 12 دیوان عدالت - 920820",
```

### def complex_case_graph › L149-153
```
    # === وقایع پرونده (Case Facts) ===
    
    fact_contract = GraphNode(
        id="fact_contract_value",
        label="مبلغ قرارداد",
```

### def complex_case_graph › L162-166
```
    builder.add_node(fact_contract)
    
    fact_delay = GraphNode(
        id="fact_delay_180_days",
        label="تاخیر 180 روزه",
```

### def complex_case_graph › L176-180
```
    builder.add_node(fact_delay)
    
    fact_covid = GraphNode(
        id="fact_covid_period",
        label="دوره کرونا",
```

### def complex_case_graph › L191-195
```
    builder.add_node(fact_covid)
    
    fact_material_shortage = GraphNode(
        id="fact_material_shortage",
        label="کمبود مصالح",
```

### def complex_case_graph › L204-208
```
    builder.add_node(fact_material_shortage)
    
    fact_penalty_clause = GraphNode(
        id="fact_penalty_0_5_percent",
        label="شرط جریمه",
```

### def complex_case_graph › L217-221
```
    builder.add_node(fact_penalty_clause)
    
    fact_employer_claim = GraphNode(
        id="fact_employer_damage_claim",
        label="ادعای خسارت کارفرما",
```

### def complex_case_graph › L231-235
```
    # === ادعاهای طرفین (Party Claims) ===
    
    claim_contractor = GraphNode(
        id="claim_contractor_not_liable",
        label="ادعای پیمانکار",
```

### def complex_case_graph › L243-247
```
    builder.add_node(claim_contractor)
    
    claim_employer = GraphNode(
        id="claim_employer_full_penalty",
        label="ادعای کارفرما",
```

### def complex_case_graph › L258-262
```
    
    # قوانین به یکدیگر
    builder.add_edge(GraphEdge(
        source_id="law_civil_227",
        target_id="law_civil_219",
```

### def complex_case_graph › L266-270
```
    
    # رویه قضایی به قوانین
    builder.add_edge(GraphEdge(
        source_id="precedent_force_majeure",
        target_id="law_civil_227",
```

### def complex_case_graph › L273-277
```
    ))
    
    builder.add_edge(GraphEdge(
        source_id="precedent_material_supply",
        target_id="law_commerce_10",
```

### def complex_case_graph › L281-285
```
    
    # وقایع به قوانین
    builder.add_edge(GraphEdge(
        source_id="fact_covid_period",
        target_id="law_civil_227",
```

### def complex_case_graph › L288-292
```
    ))
    
    builder.add_edge(GraphEdge(
        source_id="fact_penalty_0_5_percent",
        target_id="law_civil_219",
```


**Tool Call: Search files for regex `properties\s*=\s*\{|"properties"\s*:\s*\{`**
Status: Completed

Showing matches 1-20 (there were more matches found; use offset: 20 to see next page):

## Matches in KingMahouN/tests/contracts/test_core_contracts.py

### class TestLegalEntityInput › def test_valid_entity_input › L261-267
```
        entity = LegalEntityInput(
            entity_id="ENT-001",
            entity_type="PERSON",
            name="John Doe",
            properties={"role": "plaintiff"},
            confidence=0.95
        )
```

## Matches in KingMahouN/tests/fixtures/in_memory_knowledge_graph.py

### class InMemoryKnowledgeGraph › def find_applicable_rules › L130-140
```
                applicable.append({
                    "rule": rule,
                    "match_score": match_score,
                    "id": rule.rule_id,
                    "condition": rule.condition,
                    "conclusion": rule.conclusion,
                    "confidence": rule.confidence,
                    "source": rule.source,
                    "properties": {
                        "condition": rule.condition,
                        "conclusion": rule.conclusion,
```

3 lines remaining in ancestor node. Read the file to see all.

### class InMemoryKnowledgeGraph › def find_similar_precedents › L189-199
```
                similar.append({
                    "precedent": precedent,
                    "match_score": match_score,
                    "id": precedent.precedent_id,
                    "case_name": precedent.case_name,
                    "facts": precedent.facts,
                    "ruling": precedent.ruling,
                    "confidence": precedent.confidence,
                    "jurisdiction": precedent.jurisdiction,
                    "year": precedent.year,
                    "properties": {
```

6 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/tests/nightmare_aml_test.py

### class NightmareModeAML › def run › L107-120
```
        print("\n" + "🔥"*40)
        print("💀 MAHOUN NIGHTMARE MODE: THE PHANTOM MERGER")
        print("🔥"*40)
        print("\n⚠️  CHALLENGE: Find temporal fraud in 15 documents (7 signal, 8 noise)")
        
        # Build Graph
        builder = UltraGraphBuilder(enable_quality_assessment=False)
        entities = [{"id": d["doc_id"], "label": "Document", "text": d["content"], "properties": {"date": d.get("date", "")}} for d in self.documents]
        entities.extend([
            {"id": "CYPRUS_ENTITY", "label": "Company", "properties": {"name": "CyberTech Cyprus", "status": "DISSOLVED"}},
            {"id": "PARS_COMPANY", "label": "Company", "properties": {"name": "Pars Tech"}},
            {"id": "CEO_NODE", "label": "Person", "properties": {"name": "Reza Motaghaleb"}},
            {"id": "FORGERY_NODE", "label": "Crime", "properties": {"type": "Document Forgery"}},
        ])
```

98 lines remaining in ancestor node. Read the file to see all.

## Matches in KingMahouN/tests/reasoning_logic_test.py

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L77-87
```
            GraphNode(
                id="article_10",
                label="LawArticle",
                node_type="law_article",
                properties={
                    "article_number": "10",
                    "law_name": "قانون مالیات",
                    "text": "هر شهروند باید ۱۰٪ مالیات بر دارایی دیجیتال بپردازد",
                    "approval_date": "1400/01/01",
                    "legal_level": "law"
                },
```

2 lines remaining in ancestor node. Read the file to see all.

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L90-100
```
            GraphNode(
                id="note_1_article_10",
                label="LawNote",
                node_type="law_note",
                properties={
                    "note_number": "1",
                    "parent_article": "10",
                    "text": "دانشجویان از مالیات دارایی دیجیتال معاف هستند",
                    "approval_date": "1401/01/01",
                    "legal_level": "note"
                },
```

2 lines remaining in ancestor node. Read the file to see all.

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L103-113
```
            GraphNode(
                id="circular_505",
                label="Circular",
                node_type="circular",
                properties={
                    "circular_number": "505",
                    "issuer": "سازمان مالیات",
                    "text": "همه افراد (از جمله دانشجویان) باید ۵٪ هزینه نگهداری سرور بپردازند",
                    "issue_date": "1402/01/01",
                    "legal_level": "circular"
                },
```

2 lines remaining in ancestor node. Read the file to see all.

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L116-126
```
            GraphNode(
                id="student_123",
                label="Person",
                node_type="person",
                properties={
                    "name": "محمد رضایی",
                    "role": "student",
                    "activity": "bitcoin_trading"
                },
                confidence=1.0
            )
```

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L131-137
```
            GraphEdge(
                source_id="note_1_article_10",
                target_id="article_10",
                relationship_type="HAS_EXCEPTION",
                properties={"exception_type": "exemption"},
                confidence=1.0
            ),
```

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L138-144
```
            GraphEdge(
                source_id="circular_505",
                target_id="article_10",
                relationship_type="REFERENCES",
                properties={"reference_type": "related"},
                confidence=0.9
            ),
```

### class TestLogicalReasoningScenario › def synthetic_legal_graph › L145-151
```
            GraphEdge(
                source_id="student_123",
                target_id="note_1_article_10",
                relationship_type="QUALIFIES_FOR",
                properties={"qualification": "student_status"},
                confidence=1.0
            )
```

## Matches in KingMahouN/tests/test_deep_validation.py

### class TestDeepValidation › def test_deep_validation_with_graph_builder › L125-130
```
            {
                "id": "rule_1",
                "label": "Article 219",
                "type": "LegalRule",
                "properties": {}
            },
```

### class TestDeepValidation › def test_deep_validation_with_graph_builder › L131-136
```
            {
                "id": "fact_1",
                "label": "Contract signed on 2024-01-15",
                "type": "Fact",
                "properties": {}
            }
```

## Matches in KingMahouN/tests/test_deterministic_resolution.py

### class TestDeterministicResolution › async def test_tie_breaking_is_deterministic › L82-88
```
        node1 = GraphNode(
            id="rule_b",  # Lexicographically after "rule_a"
            label="Rule B",
            node_type="LegalRule",
            properties={"condition": "test", "conclusion": "result B"},
            confidence=0.9,
        )
```

### class TestDeterministicResolution › async def test_tie_breaking_is_deterministic › L89-95
```
        node2 = GraphNode(
            id="rule_a",  # Lexicographically before "rule_b"
            label="Rule A",
            node_type="LegalRule",
            properties={"condition": "test", "conclusion": "result A"},
            confidence=0.9,  # Same confidence as node1
        )
```

### class TestDeterministicResolution › async def test_confidence_threshold_prevents_floating_point_issues › L114-120
```
        node1 = GraphNode(
            id="rule_1",
            label="Rule 1",
            node_type="LegalRule",
            properties={},
            confidence=0.900001,  # Very close to 0.9
        )
```

### class TestDeterministicResolution › async def test_confidence_threshold_prevents_floating_point_issues › L121-127
```
        node2 = GraphNode(
            id="rule_2",
            label="Rule 2",
            node_type="LegalRule",
            properties={},
            confidence=0.900000,  # Very close to 0.9
        )
```

### class TestDeterministicResolution › async def test_date_based_resolution_is_deterministic › L223-229
```
        node1 = GraphNode(
            id="precedent_1",
            label="Precedent 1",
            node_type="LegalPrecedent",
            properties={"date": "2023-01-01"},
            confidence=0.9,
        )
```

### class TestDeterministicResolution › async def test_date_based_resolution_is_deterministic › L230-236
```
        node2 = GraphNode(
            id="precedent_2",
            label="Precedent 2",
            node_type="LegalPrecedent",
            properties={"date": "2024-01-01"},  # Newer
            confidence=0.9,
        )
```

### class TestDeterministicResolution › async def test_credibility_based_resolution_is_deterministic › L255-261
```
        node1 = GraphNode(
            id="rule_1",
            label="Rule 1",
            node_type="LegalRule",
            properties={"credibility": 0.95},
            confidence=0.9,
        )
```


## Assistant

<thinking>
**Evaluating graph builder limitations**

I see that the grep results highlight the use of ultra_graph_builder with labels like Company, Crime, and LegalPrecedent, which aren't part of the standard ALLOWED_NODE_LABELS. This raises concerns. For the `mahoun/graph/ultra_graph_builder.py`, it seems the export_to_neo4j function might not cover all possible labels, which is a notable issue. The user wants to ensure explicit local allowlists are in place to prevent failures. It might be beneficial to reject those labels during export. I should also check the add_node and add_edge methods to understand label and source type choices better.

**Exploring graph builder export limitations**

I think I should look for `add_node` in `graph/ultra_graph_builder.py` to see how the generic builder manages various labels, particularly since export only allows for the local canonical set. This seems acceptable. I should check `tests/governance/test_hardened_infrastructure.py` to confirm that the expected call count is three and verify label types. The local allowlist should include Verdict and CITES. It might also be useful to review the tests in `tests/test_governance_bypass_prevention.py`. After making these updates, I want to ensure I’m thinking about the interface for `governed_session` in `ultra_systems` carefully. Using a single correlation ID could streamline things nicely!

**Evaluating Neo4j properties**

I’m realizing that using explicit and minimal property keys is better; it keeps the top-level keys while still preserving nested properties. I need to check if Neo4j supports maps since node properties can’t be nested maps. Actually, Neo4j only accepts primitive values or lists, not maps as properties. So, if session.write_node sends a map as a property, it could get rejected. It looks like I’ll need to flatten everything to persist properties effectively.

**Considering storage models**

Creating an explicit key to preserve arbitrary properties seems viable. For instance, I could use something like: `node_data = {..., "properties_json": json.dumps(validated_props, sort_keys=True, ensure_ascii=False)}`. This approach would allow me to maintain those properties, but I need to note it changes the storage model. I should think about how this impacts both retrieval and overall data structure because that might complicate things if the model changes significantly.

**Evaluating property handling**

I'm thinking about preserving architecture and the possibility of patching only. Maybe using the `props_map` property isn’t feasible because the map is unsupported. The user explicitly asked for allowlists, which complicates things. 

An alternative could be implementing explicit local allowlists for `node.properties` and `edge.properties`, based on observed keys. However, there are many options. I should also check the BuildGraph contracts or nlp_hardening entities to gather expected property keys for generic exports. The grep result shows keys like doc_id, chunk_id, etc., which should possibly be included in the allowlist.
</thinking>

I found ingestion code that feeds `UltraGraphBuilder` structured provenance-like properties, so I’m reading that mapping to avoid choosing an unrealistically tiny property allowlist.

**Tool Call: Read file `mahoun/pipelines/ingestion/nlp_hardening.py` (lines 496-660)**
Status: Completed

```KingMahouN/mahoun/pipelines/ingestion/nlp_hardening.py
   496	        )
   497	
   498	        # graph_entities is List[Dict] ready for UltraGraphBuilder.build_graph()
   499	    """
   500	
   501	    def __init__(self, ner_engine=None):
   502	        """
   503	        Args:
   504	            ner_engine: An instance of LegalNEREngine.
   505	                        If None, a default engine is created.
   506	        """
   507	        if ner_engine is None:
   508	            from mahoun.pipelines.ingestion.legal_ner import LegalNEREngine
   509	
   510	            ner_engine = LegalNEREngine()
   511	
   512	        self.ner_engine = ner_engine
   513	        self.mapper = ProvenanceAwareNERMapper()
   514	
   515	    def process(
   516	        self,
   517	        text: str,
   518	        chunks: list,
   519	        doc_id: str,
   520	    ) -> List[Dict[str, Any]]:
   521	        """
   522	        Run NER on full text, then map entities to chunks with provenance.
   523	
   524	        Args:
   525	            text: Full normalized document text
   526	            chunks: List of chunk objects (must have .chunk_id, .text, .start, .end)
   527	            doc_id: Document identifier
   528	
   529	        Returns:
   530	            List of dicts ready for UltraGraphBuilder.build_graph(entities=...)
   531	
   532	        Raises:
   533	            ValueError: If text is empty or chunks have invalid offsets
   534	        """
   535	        if not text or not text.strip():
   536	            logger.warning(f"HardenedGraphEntityProcessor: Empty text for doc {doc_id}")
   537	            return []
   538	
   539	        # Step 1: Run NER on full document text
   540	        raw_entities = self.ner_engine.extract(text)
   541	
   542	        # Step 2: Convert chunks to ChunkInfo
   543	        chunk_infos = []
   544	        for c in chunks:
   545	            # Support both Chunk dataclass and dict-like objects
   546	            if hasattr(c, "chunk_id"):
   547	                chunk_infos.append(
   548	                    ChunkInfo(
   549	                        chunk_id=c.chunk_id,
   550	                        text=c.text,
   551	                        doc_start=c.start,
   552	                        doc_end=c.end,
   553	                    )
   554	                )
   555	            elif isinstance(c, dict):
   556	                chunk_infos.append(
   557	                    ChunkInfo(
   558	                        chunk_id=c.get("chunk_id", ""),
   559	                        text=c.get("text", ""),
   560	                        doc_start=c.get("start", 0),
   561	                        doc_end=c.get("end", 0),
   562	                    )
   563	                )
   564	            else:
   565	                raise TypeError(
   566	                    f"Unsupported chunk type: {type(c)}. "
   567	                    f"Expected Chunk dataclass or dict."
   568	                )
   569	
   570	        # Step 3: Map entities to chunks with provenance
   571	        provenance_records = self.mapper.map_entities_to_chunks(
   572	            entities=raw_entities,
   573	            chunks=chunk_infos,
   574	            doc_id=doc_id,
   575	        )
   576	
   577	        # Step 4: Convert to graph entity dicts
   578	        graph_entities = [r.to_graph_entity() for r in provenance_records]
   579	
   580	        logger.info(
   581	            f"HardenedGraphEntityProcessor: Produced {len(graph_entities)} "
   582	            f"graph entities from {sum(len(v) for v in raw_entities.values())} "
   583	            f"raw NER results for doc {doc_id}"
   584	        )
   585	
   586	        return graph_entities
   587	
   588	
   589	# ============================================================================
   590	# 5. Evidence Integrity Validators
   591	# ============================================================================
   592	
   593	
   594	def validate_entity_provenance(entity: Dict[str, Any]) -> bool:
   595	    """
   596	    Validate that an entity dict has complete provenance metadata.
   597	
   598	    This is the assertion function used in tests and in production
   599	    STRICT mode to ensure zero-hallucination compliance.
   600	
   601	    Returns:
   602	        True if valid, raises AssertionError otherwise
   603	    """
   604	    props = entity.get("properties", {})
   605	
   606	    # Required fields
   607	    assert entity.get("id"), f"Entity missing deterministic 'id': {entity}"
   608	    assert entity.get("label"), f"Entity missing 'label' (category): {entity}"
   609	    assert entity.get("text"), f"Entity missing 'text': {entity}"
   610	
   611	    # Provenance fields
   612	    assert "doc_id" in props, f"Entity missing 'doc_id' in properties: {entity}"
   613	    assert "chunk_id" in props, f"Entity missing 'chunk_id' in properties: {entity}"
   614	    assert "doc_start" in props, f"Entity missing 'doc_start' in properties: {entity}"
   615	    assert "doc_end" in props, f"Entity missing 'doc_end' in properties: {entity}"
   616	    assert "chunk_start" in props, (
   617	        f"Entity missing 'chunk_start' in properties: {entity}"
   618	    )
   619	    assert "chunk_end" in props, f"Entity missing 'chunk_end' in properties: {entity}"
   620	
   621	    # Integrity checks
   622	    assert props["doc_start"] >= 0, f"Negative doc_start: {props['doc_start']}"
   623	    assert props["doc_end"] > props["doc_start"], (
   624	        f"doc_end ({props['doc_end']}) must be > doc_start ({props['doc_start']})"
   625	    )
   626	    assert props["chunk_start"] >= 0, f"Negative chunk_start: {props['chunk_start']}"
   627	    assert props["chunk_end"] >= props["chunk_start"], (
   628	        f"chunk_end ({props['chunk_end']}) must be >= chunk_start ({props['chunk_start']})"
   629	    )
   630	
   631	    return True
   632	
   633	
   634	def validate_no_duplicate_ids(entities: List[Dict[str, Any]]) -> bool:
   635	    """
   636	    Validate that no two entities share the same deterministic ID.
   637	
   638	    Returns:
   639	        True if no duplicates, raises AssertionError otherwise
   640	    """
   641	    seen: Dict[str, str] = {}
   642	    for entity in entities:
   643	        eid = entity.get("id")
   644	        etext = entity.get("text", "?")
   645	        if eid in seen:
   646	            raise AssertionError(
   647	                f"Duplicate entity ID '{eid}': first='{seen[eid]}', second='{etext}'"
   648	            )
   649	        seen[eid] = etext
   650	
   651	    return True

```


**Tool Call: Read file `tests/nightmare_aml_test.py` (lines 100-160)**
Status: Completed

```KingMahouN/tests/nightmare_aml_test.py
   100	            
   101	            # Legal Framework
   102	            {"source_id": "MERGER-ANNOUNCE", "target_id": "LAW-IRAN-MERGER", "type": "GOVERNED_BY", "weight": 0.7},
   103	            {"source_id": "FORGERY_NODE", "target_id": "LAW-IRAN-MERGER", "type": "VIOLATES", "weight": 1.0},
   104	        ]
   105	
   106	    def run(self):
   107	        print("\n" + "🔥"*40)
   108	        print("💀 MAHOUN NIGHTMARE MODE: THE PHANTOM MERGER")
   109	        print("🔥"*40)
   110	        print("\n⚠️  CHALLENGE: Find temporal fraud in 15 documents (7 signal, 8 noise)")
   111	        
   112	        # Build Graph
   113	        builder = UltraGraphBuilder(enable_quality_assessment=False)
   114	        entities = [{"id": d["doc_id"], "label": "Document", "text": d["content"], "properties": {"date": d.get("date", "")}} for d in self.documents]
   115	        entities.extend([
   116	            {"id": "CYPRUS_ENTITY", "label": "Company", "properties": {"name": "CyberTech Cyprus", "status": "DISSOLVED"}},
   117	            {"id": "PARS_COMPANY", "label": "Company", "properties": {"name": "Pars Tech"}},
   118	            {"id": "CEO_NODE", "label": "Person", "properties": {"name": "Reza Motaghaleb"}},
   119	            {"id": "FORGERY_NODE", "label": "Crime", "properties": {"type": "Document Forgery"}},
   120	        ])
   121	        
   122	        builder.build_graph(entities, self.relationships)
   123	        
   124	        nx_graph = nx.DiGraph()
   125	        for edge in builder._edges:
   126	            nx_graph.add_edge(edge.source_id, edge.target_id, type=edge.relationship_type, weight=edge.weight)
   127	        
   128	        # Ultra-Aggressive Config
   129	        config = SearchConfig(
   130	            use_bm25=True, use_dense=True, use_graph=True,
   131	            graph_weight=0.95,  # Maximum graph reliance
   132	            bm25_weight=0.3,
   133	            dense_weight=0.4,
   134	            rrf_k=30,
   135	            top_k=100,
   136	            final_k=10
   137	        )
   138	        
   139	        engine = UltraHybridSearch(config, embedding_provider=self._mock_embedder())
   140	        engine.graph_retriever.max_hops = 7  # DEEP SEARCH
   141	        engine.set_graph(nx_graph)
   142	        engine.index(self.documents)
   143	        
   144	        # The Impossible Query
   145	        query = "آیا ادغام شرکت پارس قانونی است؟ اسناد تاریخی و حسابرسی را بررسی کن"
   146	        print(f"\n🔍 Investigator's Query: '{query}'")
   147	        print("\n" + "-"*80)
   148	        
   149	        results, metrics = engine.search(query, top_k=10)
   150	        
   151	        print("\n📋 EVIDENCE DOSSIER (Ranked by Relevance):\n")
   152	        
   153	        critical_finds = {
   154	            "temporal_conflict": False,
   155	            "legal_basis": False,
   156	            "audit_fraud": False,
   157	            "precedent": False,
   158	            "noise_filtered": 0
   159	        }
   160	        

```


**Tool Call: Read file `tests/reasoning_logic_test.py` (lines 70-160)**
Status: Completed

```KingMahouN/tests/reasoning_logic_test.py
    70	    
    71	    @pytest.fixture
    72	    def synthetic_legal_graph(self):
    73	        """Create synthetic legal graph with conflicting rules"""
    74	        
    75	        # Create nodes
    76	        nodes = [
    77	            GraphNode(
    78	                id="article_10",
    79	                label="LawArticle",
    80	                node_type="law_article",
    81	                properties={
    82	                    "article_number": "10",
    83	                    "law_name": "قانون مالیات",
    84	                    "text": "هر شهروند باید ۱۰٪ مالیات بر دارایی دیجیتال بپردازد",
    85	                    "approval_date": "1400/01/01",
    86	                    "legal_level": "law"
    87	                },
    88	                confidence=1.0
    89	            ),
    90	            GraphNode(
    91	                id="note_1_article_10",
    92	                label="LawNote",
    93	                node_type="law_note",
    94	                properties={
    95	                    "note_number": "1",
    96	                    "parent_article": "10",
    97	                    "text": "دانشجویان از مالیات دارایی دیجیتال معاف هستند",
    98	                    "approval_date": "1401/01/01",
    99	                    "legal_level": "note"
   100	                },
   101	                confidence=1.0
   102	            ),
   103	            GraphNode(
   104	                id="circular_505",
   105	                label="Circular",
   106	                node_type="circular",
   107	                properties={
   108	                    "circular_number": "505",
   109	                    "issuer": "سازمان مالیات",
   110	                    "text": "همه افراد (از جمله دانشجویان) باید ۵٪ هزینه نگهداری سرور بپردازند",
   111	                    "issue_date": "1402/01/01",
   112	                    "legal_level": "circular"
   113	                },
   114	                confidence=0.9
   115	            ),
   116	            GraphNode(
   117	                id="student_123",
   118	                label="Person",
   119	                node_type="person",
   120	                properties={
   121	                    "name": "محمد رضایی",
   122	                    "role": "student",
   123	                    "activity": "bitcoin_trading"
   124	                },
   125	                confidence=1.0
   126	            )
   127	        ]
   128	        
   129	        # Create edges
   130	        edges = [
   131	            GraphEdge(
   132	                source_id="note_1_article_10",
   133	                target_id="article_10",
   134	                relationship_type="HAS_EXCEPTION",
   135	                properties={"exception_type": "exemption"},
   136	                confidence=1.0
   137	            ),
   138	            GraphEdge(
   139	                source_id="circular_505",
   140	                target_id="article_10",
   141	                relationship_type="REFERENCES",
   142	                properties={"reference_type": "related"},
   143	                confidence=0.9
   144	            ),
   145	            GraphEdge(
   146	                source_id="student_123",
   147	                target_id="note_1_article_10",
   148	                relationship_type="QUALIFIES_FOR",
   149	                properties={"qualification": "student_status"},
   150	                confidence=1.0
   151	            )
   152	        ]
   153	        
   154	        return {"nodes": nodes, "edges": edges}
   155	    
   156	    @pytest.fixture
   157	    def legal_rules(self):
   158	        """Define legal reasoning rules in FOL"""
   159	        
   160	        # Variables

```


**Tool Call: Read file `tests/integration/test_complex_legal_reasoning_scenario.py` (lines 70-330)**
Status: Completed

```KingMahouN/tests/integration/test_complex_legal_reasoning_scenario.py
    70	)
    71	
    72	
    73	@pytest.fixture
    74	def complex_case_graph():
    75	    """Build knowledge graph for complex contract dispute"""
    76	    builder = UltraGraphBuilder()
    77	    
    78	    # === قوانین مرتبط (Relevant Laws) ===
    79	    
    80	    # قانون مدنی - ماده 219: شرط جریمه
    81	    
    82	    law_219 = GraphNode(
    83	        id="law_civil_219",
    84	        label="قانون مدنی ماده 219",
    85	        node_type="Statute",
    86	        content="شرط جریمه در قراردادها نافذ است مگر در موارد قوه قهریه",
    87	        metadata={
    88	            "article": 219,
    89	            "law": "civil_code",
    90	            "category": "penalty_clause"
    91	        }
    92	    )
    93	    builder.add_node(law_219)
    94	    
    95	    # ماده 227: قوه قهریه
    96	    law_227 = GraphNode(
    97	        id="law_civil_227",
    98	        label="قانون مدنی ماده 227",
    99	        node_type="Statute",
   100	        content="در موارد قوه قهریه، متعهد از مسئولیت عدم انجام تعهد معاف است",
   101	        metadata={
   102	            "article": 227,
   103	            "law": "civil_code",
   104	            "category": "force_majeure"
   105	        }
   106	    )
   107	    builder.add_node(law_227)
   108	    
   109	    # قانون تجارت - ماده 10: مسئولیت پیمانکار
   110	    law_commerce_10 = GraphNode(
   111	        id="law_commerce_10",
   112	        label="قانون تجارت ماده 10",
   113	        node_type="Statute",
   114	        content="پیمانکار موظف است طبق شرایط قرارداد عمل نماید",
   115	        metadata={
   116	            "article": 10,
   117	            "law": "commerce_code"
   118	        }
   119	    )
   120	    builder.add_node(law_commerce_10)
   121	    
   122	    # === رویه قضایی (Precedents) ===
   123	    
   124	    precedent_force_majeure = GraphNode(
   125	        id="precedent_940315",
   126	        label="رأی هیأت عمومی دیوان عدالت - 940315",
   127	        node_type="Precedent",
   128	        content="شیوع کرونا در صورت اثبات تأثیر مستقیم بر اجرای تعهد، قوه قهریه محسوب می‌شود",
   129	        metadata={
   130	            "date": "1394-03-15",
   131	            "court": "supreme_court",
   132	            "binding": True
   133	        }
   134	    )
   135	    builder.add_node(precedent_force_majeure)
   136	    
   137	    precedent_material_supply = GraphNode(
   138	        id="precedent_920820",
   139	        label="رأی شعبه 12 دیوان عدالت - 920820",
   140	        node_type="Precedent",
   141	        content="تأمین مصالح در قراردادهای پیمانکاری بر عهده کارفرماست مگر توافق صریح",
   142	        metadata={
   143	            "date": "1392-08-20",
   144	            "court": "supreme_court_branch_12"
   145	        }
   146	    )
   147	    builder.add_node(precedent_material_supply)
   148	    
   149	    # === وقایع پرونده (Case Facts) ===
   150	    
   151	    fact_contract = GraphNode(
   152	        id="fact_contract_value",
   153	        label="مبلغ قرارداد",
   154	        node_type="Fact",
   155	        content="قرارداد به مبلغ 10,000,000,000 ریال منعقد شد",
   156	        metadata={
   157	            "amount": 10_000_000_000,
   158	            "currency": "IRR",
   159	            "verified": True
   160	        }
   161	    )
   162	    builder.add_node(fact_contract)
   163	    
   164	    fact_delay = GraphNode(
   165	        id="fact_delay_180_days",
   166	        label="تاخیر 180 روزه",
   167	        node_type="Fact",
   168	        content="پیمانکار با 180 روز تاخیر پروژه را تحویل داد",
   169	        metadata={
   170	            "delay_days": 180,
   171	            "deadline": "1400-06-15",
   172	            "delivery": "1400-12-12",
   173	            "verified": True
   174	        }
   175	    )
   176	    builder.add_node(fact_delay)
   177	    
   178	    fact_covid = GraphNode(
   179	        id="fact_covid_period",
   180	        label="دوره کرونا",
   181	        node_type="Fact",
   182	        content="90 روز از تاخیر مصادف با شیوع کرونا بود (1399-01-01 تا 1399-03-30)",
   183	        metadata={
   184	            "duration_days": 90,
   185	            "start": "1399-01-01",
   186	            "end": "1399-03-30",
   187	            "verified": True,
   188	            "force_majeure_candidate": True
   189	        }
   190	    )
   191	    builder.add_node(fact_covid)
   192	    
   193	    fact_material_shortage = GraphNode(
   194	        id="fact_material_shortage",
   195	        label="کمبود مصالح",
   196	        node_type="Fact",
   197	        content="پیمانکار ادعا کرده کارفرما مصالح را به موقع تأمین نکرده",
   198	        metadata={
   199	            "claim_by": "contractor",
   200	            "disputed": True,
   201	            "evidence_provided": True
   202	        }
   203	    )
   204	    builder.add_node(fact_material_shortage)
   205	    
   206	    fact_penalty_clause = GraphNode(
   207	        id="fact_penalty_0_5_percent",
   208	        label="شرط جریمه",
   209	        node_type="Fact",
   210	        content="شرط جریمه 0.5 درصد روزانه از مبلغ قرارداد",
   211	        metadata={
   212	            "penalty_rate": 0.005,
   213	            "per_day": True,
   214	            "contract_clause": "article_12"
   215	        }
   216	    )
   217	    builder.add_node(fact_penalty_clause)
   218	    
   219	    fact_employer_claim = GraphNode(
   220	        id="fact_employer_damage_claim",
   221	        label="ادعای خسارت کارفرما",
   222	        node_type="Fact",
   223	        content="کارفرما درخواست 2,000,000,000 ریال خسارت کرده",
   224	        metadata={
   225	            "claimed_amount": 2_000_000_000,
   226	            "claimant": "employer"
   227	        }
   228	    )
   229	    builder.add_node(fact_employer_claim)
   230	    
   231	    # === ادعاهای طرفین (Party Claims) ===
   232	    
   233	    claim_contractor = GraphNode(
   234	        id="claim_contractor_not_liable",
   235	        label="ادعای پیمانکار",
   236	        node_type="Claim",
   237	        content="تاخیر به دلیل عدم تأمین مصالح و قوه قهریه بوده، مسئولیتی ندارم",
   238	        metadata={
   239	            "party": "contractor",
   240	            "type": "defense"
   241	        }
   242	    )
   243	    builder.add_node(claim_contractor)
   244	    
   245	    claim_employer = GraphNode(
   246	        id="claim_employer_full_penalty",
   247	        label="ادعای کارفرما",
   248	        node_type="Claim",
   249	        content="پیمانکار باید کل جریمه دیرکرد را بپردازد",
   250	        metadata={
   251	            "party": "employer",
   252	            "type": "demand"
   253	        }
   254	    )
   255	    builder.add_node(claim_employer)
   256	    
   257	    # === ایجاد روابط (Create Edges) ===
   258	    
   259	    # قوانین به یکدیگر
   260	    builder.add_edge(GraphEdge(
   261	        source_id="law_civil_227",
   262	        target_id="law_civil_219",
   263	        edge_type="MODIFIES",
   264	        metadata={"relationship": "exception"}
   265	    ))
   266	    
   267	    # رویه قضایی به قوانین
   268	    builder.add_edge(GraphEdge(
   269	        source_id="precedent_force_majeure",
   270	        target_id="law_civil_227",
   271	        edge_type="INTERPRETS",
   272	        metadata={"interpretation_type": "application"}
   273	    ))
   274	    
   275	    builder.add_edge(GraphEdge(
   276	        source_id="precedent_material_supply",
   277	        target_id="law_commerce_10",
   278	        edge_type="INTERPRETS",
   279	        metadata={"interpretation_type": "clarification"}
   280	    ))
   281	    
   282	    # وقایع به قوانین
   283	    builder.add_edge(GraphEdge(
   284	        source_id="fact_covid_period",
   285	        target_id="law_civil_227",
   286	        edge_type="APPLIES_TO",
   287	        metadata={"relevance": "force_majeure"}
   288	    ))
   289	    
   290	    builder.add_edge(GraphEdge(
   291	        source_id="fact_penalty_0_5_percent",
   292	        target_id="law_civil_219",
   293	        edge_type="APPLIES_TO",
   294	        metadata={"relevance": "penalty_enforcement"}
   295	    ))
   296	    
   297	    # ادعاها به وقایع
   298	    builder.add_edge(GraphEdge(
   299	        source_id="claim_contractor_not_liable",
   300	        target_id="fact_covid_period",
   301	        edge_type="SUPPORTS",
   302	        metadata={"support_type": "evidence"}
   303	    ))
   304	    
   305	    builder.add_edge(GraphEdge(
   306	        source_id="claim_contractor_not_liable",
   307	        target_id="fact_material_shortage",
   308	        edge_type="SUPPORTS",
   309	        metadata={"support_type": "evidence"}
   310	    ))
   311	    
   312	    builder.add_edge(GraphEdge(
   313	        source_id="claim_employer_full_penalty",
   314	        target_id="fact_delay_180_days",
   315	        edge_type="SUPPORTS",
   316	        metadata={"support_type": "evidence"}
   317	    ))
   318	    
   319	    # تناقضات
   320	    builder.add_edge(GraphEdge(
   321	        source_id="claim_contractor_not_liable",
   322	        target_id="claim_employer_full_penalty",
   323	        edge_type="CONTRADICTS",
   324	        metadata={"contradiction_type": "direct_opposition"}
   325	    ))
   326	    
   327	    return builder
   328	
   329	
   330	class TestComplexLegalReasoningScenario:

```


## Assistant

<thinking>
**Adjusting Adapter Imports**

I'm looking at the `ultra_systems` and thinking about removing the `graph.neo4j_adapter` import because it's just a dummy. I wonder if I should import `logging`, but maybe it’s not necessary. I also need to check if `HAS_NEO4J` is being used elsewhere in these files, so searching through them is the next step. It feels a bit like piecing a puzzle together!
</thinking>

Before I settle the import cleanup, I’m checking whether `HAS_NEO4J` or the adapter symbol is referenced anywhere else inside the two builder files.

**Tool Call: Search files for regex `HAS_NEO4J|Neo4jAdapter`**
Status: Completed

Found 2 matches:

## Matches in KingMahouN/mahoun/graph/ultra_graph_builder.py

### L64-67
```
try:
    from mahoun.graph.neo4j_adapter import Neo4jAdapter

    HAS_NEO4J = True
```

3 lines remaining in ancestor node. Read the file to see all.

### L68-70
```
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```


**Tool Call: Search files for regex `HAS_NEO4J|Neo4jAdapter`**
Status: Completed

Found 2 matches:

## Matches in KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py

### L28-30
```
try:
    from graph.neo4j_adapter import Neo4jAdapter
    HAS_NEO4J = True
```

3 lines remaining in ancestor node. Read the file to see all.

### L31-33
```
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```


## Assistant

<thinking>
**Considering file modifications**

I’m pondering whether to remove the `json` import, since it’s only for exporting to JSON. Without an edit tool, I think providing a unified diff could be the final solution, but the user might expect actual edits. It's crucial to be transparent about the lack of file-write capability. Should I ask if they want the patch? I think it makes sense to provide it automatically since we can't make edits ourselves. I'll clarify that I can only prepare the patch and can't run any validation.

**Crafting patch notes**

I’m considering mentioning that I didn’t run validation since I can’t write or apply changes in this environment. I think it’s essential to craft the patch carefully and accurately. Should I provide full replacement snippets or minimal diffs? I believe the best option might be to create unified diff sections for the three files involved. Being precise is crucial to ensure the user understands exactly what changes are needed. I'll focus on clarity and accuracy while preparing this information.

**Evaluating connection validation**

I’m considering whether to check if `node.node_id` or `str` is valid. The current code seems to rely on it, but I think a fail-closed approach could work. I wonder if I should call `validate_node_label(node.label)`? It might not be necessary if the local allowlist is enough, since the session will validate anyway. Maybe I could define a `_validate_connection` helper to keep things neat and avoid repeated imports. That seems like a minimal patch!

**Considering node type defaults**

I'm thinking about the `node.node_type` property. If it’s not in the allowed semantic labels or if it's empty, maybe I should default to GraphNode. However, the current export stores the node.node_type as a string, which could lead to failure if the type is unknown. That might be overly strict, especially since there are already many examples. But then again, that’s what fail-closed means, so I could mention this point.

**Evaluating integration test issues**

I’m noticing a potential problem with the `GraphNode` and `GraphEdge` dataclasses in the integration tests. It seems like they’re using fields that aren’t actually present in the file, which could cause confusion. For example, the `complex_case_graph` GraphNode is utilizing `content` and `metadata` fields that don’t match up with the dataclass we have. I’ll need to figure out what’s going on and ensure everything aligns properly!

**Reviewing code structure**

I’m considering a type check to ensure everything functions correctly. The current code already checks types before skipping, so that should be fine.

In my `_merge_node` method, I ensure the connection is valid and then validate the node data. I use a correlation ID to govern the session when writing the node.

For the `_create_edge` method, I again validate the connection and the relationship data, using a correlation ID for that process too.

The `link_and_submit` function checks for a connection before submitting, which looks solid.

**Evaluating potential file modifications**

I'm considering issues with `edge.properties`, particularly around potential collisions with `weight` and other reserved terms. For `write_node` and `write_relationship`, they seem to expect provenance being injected, which is good. However, since I don’t have an edit tool available, my final output should be concise and may include separate code blocks for changes. It’s clear that the user wants exact files and key changes, even if I explain that I couldn't modify them directly. I can supply patches instead.

**Considering diff creation**

I'm thinking about how to produce the patch with diff headers. I need to ensure that the context fits the actual file, so maybe providing just replacement snippets could help prevent mismatches. But detailed diffs are more precise, which may be better. Since I don't have a file-write tool in this session, I could clarify that I'm providing an exact patch for the three requested files. I'll also consider if combining the diffs would be beneficial, even if it's lengthy. Keeping it concise is important!

**Crafting patch files**

I'm considering that since the patch only involves three files, each can define its own specifics. For readability in the diff, it might be helpful to truncate some constants, but I want to ensure it's exact. There’s a potential risk of syntax errors in the diff if things aren't perfect, so I need to verify everything mentally. I'll create more compact constants using one tuple each and `frozenset({...})` to keep it clean. Sounds good!

**Evaluating export properties**

I’m wondering if the reserved keys in `_validate_export_properties` could accept `properties` as None. There might be an issue with `Set` imported in ultra_systems and graph files since it’s already in entity_linker. I’m considering whether to open one governed_session for each export node/edge in ultra_systems, or just one session overall. 

Should `ultra_systems` export use `actor_id="ultra-graph-builder"? Yes! I’m also thinking `mahoun/graph/ultra_graph_builder.py` should add validation for governed_session type. The connection remains unchanged, and it could be safe to remove `HAS_NEO4J` variable references. I'll check the import and possible inclusion of `GraphNode`.

**Considering operation types**

I'm thinking about the file `graph/ultra_graph_builder.py` where I noticed that no `operation_type` kwargs exist. That's fine, but I wonder if I could just provide a summary without including a diff since the user requested minimal patches. I want to make sure I'm meeting the user's request effectively while keeping things concise. It's all about striking the right balance here!

**Crafting final references**

I think I need to mention specific files: `KingMahouN/mahoun/graph/builders/entity_linker.py`, `KingMahouN/mahoun/graph/ultra_graph_builder.py`, and `KingMahouN/mahoun/ultra_systems/graph/ultra_graph_builder.py`. Since no other files were changed in the session, I'll clarify that the patch targets exactly these three files. 

I wonder if I should use project-relative paths like `mahoun/...` or `KingMahouN/mahoun/...` instead. Hmm, I’ll go with `mahoun/...` for clarity!

**Finalizing summary and patches**

I need to mention file paths without the root for clarity, but the developer suggested using project-relative paths. Since the rules say to only use the root prefix for tools, I’ll just use `mahoun/...`, as the user knows the root. 

I should mention that I couldn’t run the post-edit validation due to a lack of file-write tools. I might add that if needed, I can adapt the patch after the user applies it or if write access is enabled. Let’s summarize: a brief honesty statement, then provide the exact patch in concise code blocks.

**Limiting patch details**

I realize the final answer might get lengthy due to the diff details. To keep it manageable, I should focus on providing exact replacement methods and constants instead of the full diff. While an “exact patch” might still be enough, limiting the information will help prevent any overwhelming responses. I want to ensure the user gets clear, concise information without unnecessary complexity. So, I’ll aim for clarity while being thorough!

**Considering patch options**

The user is asking about edits, so I think I should offer a response like, "I can't write from this session, but here's the minimal patch." For each file, I could show the exact snippets to replace, which might be simpler than providing a full unified diff. It’s important to be clear about where to insert or replace code, but the user will likely need to apply changes manually. Either snippets or a unified diff could work, so I’ll need to consider their familiarity with code.

**Summarizing changes clearly**

I think a good approach is to provide a concise summary along with specific replacement blocks for the touched methods and added constants, since that should be easier for the user. It’s also important to include notes about two behavior changes: `entity_linker.submit_to_neo4j()` now uses governed writes and fails closed if there are schema violations, and both ultra builders reject unknown property keys before export. I could mention needing to update specific tests and ask if the user wants companion test updates. I should consider diagnostics for potential type checking issues as well.

**Clarifying file changes**

I need to mention that while no files were actually changed in this session, I can state, "Intended file list (and only file list): ..." to be transparent. The user might expect exact changes, so I should clarify that "No files changed in-session," and then provide the intended patch files. I could also explain that my environment doesn't allow for `edit_file` or `write_file`, which means I couldn't apply the patch directly. It's important to accurately craft the code snippets, and I should also note that I didn't touch `mahoun/self_improve/...`.

**Evaluating builder properties**

I'm considering the builder export property allowlist names, and I think the sets of strings might be too broad, but that's okay. I'm wondering if a typo or missing keys could be the reason exports that previously worked are failing—it's generally acceptable for it to fail-closed. Maybe I should check for any reserved key collisions. I also need to address potential syntax issues in annotations and static methods, and look into long line lengths while considering property sets.

**Considering relation properties**

I'm thinking the relation property key `evidence` might not need to be in extras, since provenance already contains the evidence list. I should consider if the `governed_session.write_node` and `relationship` methods return a MutationReceipt, but in the ultra_systems export, we ignore those returns. In tests, I could assert the call count, though I haven’t touched that yet. Also, it’s important to note that `connection.governed_session` requires an active GovernanceContext. Since the user asked not to touch other files, I might propose minimal test adjustments later.

**Evaluating code structure**

I’m thinking about whether any of our suggested constants or helpers could be moved to the module level to minimize code repetition. For the ultra_systems file, it might be helpful to use the same property allowlist sets as in graph/ultra_graph_builder.py but keep them local instead. There seems to be a potential issue with the ultra_systems file importing `numpy as np` unconditionally, which could lead to a missing dependency situation, but maybe that’s not too relevant right now.

**Considering code summary options**

I think it’s better to offer a compact summary and optionally generate a `git apply` diff since the patch blocks can be lengthy. However, I want to include at least the essential code. Leaning toward a unified diff is tempting, but it might get too long due to repeated property sets. An alternative could be providing a conceptual edit list, but the user asked for specific changes. 

So, I’m thinking to offer a summary alongside a gist-like patch with concise instructions on what to replace, which could work well!

**Evaluating architectural decisions**

I’m realizing that I need to find a balance. It’s shorter, which is good, but it might miss some important aspects. A fail-closed approach seems okay since it preserves the architecture, and moderating could help. Plus, this may also make the patch length shorter. I’m considering limiting it to about 20 keys, which feels like a reasonable choice. Let’s see how I can make this work effectively!

**Evaluating code structure**

I'm looking at a potential issue in the code block involving helper methods. It uses `Optional[Dict[str, Any]]`, along with `allowed_keys` and `reserved_keys`. Since `Optional` has already been imported, that's good! I want to ensure the use of `Optional` makes sense here since it can help manage the presence of values. I'm curious if everything is correctly set up with those keys to avoid any unintended consequences! Let's figure this out!
</thinking>

I can’t apply the edits directly in this session because the available tools are read/search only — there’s no `edit_file`/`write_file`/shell write path exposed. So **no files were changed in-session**.

I did keep scope to exactly your three requested files, and below is the **minimal patch content** for only:

- `mahoun/graph/builders/entity_linker.py`
- `mahoun/graph/ultra_graph_builder.py`
- `mahoun/ultra_systems/graph/ultra_graph_builder.py`

I did **not** touch `self_improve`.

---

## 1) `mahoun/graph/builders/entity_linker.py`

### A. Update imports

Change the import block near the top to include `TYPE_CHECKING` and `MappingProxyType`:

```python
import re
import logging
import hashlib
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from mahoun.core.runtime_config import get_runtime_settings, should_skip_graph

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from mahoun.graph.neo4j.connection import Neo4jConnection
```

### B. Add local builder allowlists after `logger = logging.getLogger(__name__)`

```python
_ENTITY_LINKER_ALLOWED_LABELS = frozenset(
    {"Case", "Person", "Organization", "Court", "LawArticle", "Topic"}
)

_ENTITY_LINKER_ALLOWED_NODE_PROPERTIES = MappingProxyType(
    {
        "Case": frozenset(
            {"case_id", "created_at", "case_type", "court_level", "is_final", "decision_date"}
        ),
        "Person": frozenset(
            {"name", "normalized_name", "title", "father_name", "national_id", "role"}
        ),
        "Organization": frozenset(
            {"name", "normalized_name", "org_type", "registration_id"}
        ),
        "Court": frozenset({"name", "level", "branch", "city", "province"}),
        "LawArticle": frozenset({"article", "law_name", "code", "description", "clause"}),
        "Topic": frozenset({"label", "category"}),
    }
)

_ENTITY_LINKER_ALLOWED_RELATIONSHIP_TYPES = frozenset(
    {"PARTY_IN", "REFERS_TO", "HANDLED_BY", "ABOUT"}
)

_ENTITY_LINKER_ALLOWED_RELATIONSHIP_PROPERTIES = MappingProxyType(
    {
        "PARTY_IN": frozenset({"role"}),
        "REFERS_TO": frozenset(),
        "HANDLED_BY": frozenset(),
        "ABOUT": frozenset(),
    }
)

_ENTITY_LINKER_ALLOWED_RELATIONSHIP_ENDPOINTS = MappingProxyType(
    {
        "PARTY_IN": frozenset({("Person", "Case"), ("Organization", "Case")}),
        "REFERS_TO": frozenset({("Case", "LawArticle")}),
        "HANDLED_BY": frozenset({("Case", "Court")}),
        "ABOUT": frozenset({("Case", "Topic")}),
    }
)
```

### C. Add helper methods inside `EntityLinker`, just before `# Neo4j Direct Integration (Optional)`

```python
    @staticmethod
    def _require_connection(
        connection: Optional["Neo4jConnection"],
    ) -> "Neo4jConnection":
        from mahoun.graph.neo4j.connection import Neo4jConnection

        if not isinstance(connection, Neo4jConnection):
            raise TypeError(
                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
            )
        return connection

    @staticmethod
    def _validate_allowed_properties(
        properties: Optional[Dict[str, Any]],
        *,
        allowed_keys: Set[str],
        entity_kind: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        if properties is None:
            return {}

        if not isinstance(properties, dict):
            raise TypeError(
                f"{entity_kind} properties for '{entity_id}' must be a dict, "
                f"got {type(properties).__name__}"
            )

        unknown_keys = set(properties) - set(allowed_keys)
        if unknown_keys:
            raise ValueError(
                f"Invalid {entity_kind} properties for '{entity_id}': "
                f"{sorted(unknown_keys)}"
            )

        return dict(properties)

    def _validated_node_data(self, node: GraphNodeSpec) -> Dict[str, Any]:
        if node.label not in _ENTITY_LINKER_ALLOWED_LABELS:
            raise ValueError(f"Invalid node label: {node.label}")

        node_properties = self._validate_allowed_properties(
            node.properties,
            allowed_keys=_ENTITY_LINKER_ALLOWED_NODE_PROPERTIES[node.label],
            entity_kind=f"{node.label} node",
            entity_id=node.node_id,
        )

        return {
            "id": node.node_id,
            "node_id": node.node_id,
            **node_properties,
        }

    def _validated_relationship_data(self, edge: GraphEdgeSpec) -> Dict[str, Any]:
        if edge.from_label not in _ENTITY_LINKER_ALLOWED_LABELS or edge.to_label not in _ENTITY_LINKER_ALLOWED_LABELS:
            raise ValueError(f"Invalid node label: {edge.from_label} or {edge.to_label}")

        if edge.relationship_type not in _ENTITY_LINKER_ALLOWED_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type: {edge.relationship_type}")

        if (edge.from_label, edge.to_label) not in _ENTITY_LINKER_ALLOWED_RELATIONSHIP_ENDPOINTS[edge.relationship_type]:
            raise ValueError(
                f"Invalid relationship endpoints: "
                f"{edge.from_label}-[{edge.relationship_type}]->{edge.to_label}"
            )

        return self._validate_allowed_properties(
            edge.properties,
            allowed_keys=_ENTITY_LINKER_ALLOWED_RELATIONSHIP_PROPERTIES[edge.relationship_type],
            entity_kind=f"{edge.relationship_type} relationship",
            entity_id=f"{edge.from_id}->{edge.to_id}",
        )
```

### D. Replace `submit_to_neo4j`, `_merge_node`, `_create_edge`

Replace the existing methods with:

```python
    def submit_to_neo4j(
        self,
        nodes: List[GraphNodeSpec],
        edges: List[GraphEdgeSpec],
        connection: "Neo4jConnection",
    ) -> bool:
        """
        Submit nodes and edges directly to Neo4j.

        Args:
            nodes: List of node specifications
            edges: List of edge specifications
            connection: Initialized Neo4jConnection instance

        Returns:
            True if successful
        """
        connection = self._require_connection(connection)

        if should_skip_graph():
            logger.debug("EntityLinker: Skipping Neo4j submission in desktop-minimal mode")
            return True

        try:
            for node in nodes:
                self._merge_node(node, connection)

            for edge in edges:
                self._create_edge(edge, connection)

            logger.info(f"Submitted {len(nodes)} nodes and {len(edges)} edges to Neo4j")
            return True

        except Exception as e:
            logger.error(f"Neo4j submission failed: {e}")
            return False

    def _merge_node(self, node: GraphNodeSpec, connection: "Neo4jConnection"):
        """Merge a single node into Neo4j via the governed write surface."""
        connection = self._require_connection(connection)
        node_data = self._validated_node_data(node)

        import uuid

        correlation_id = str(uuid.uuid4())
        with connection.governed_session(
            correlation_id=correlation_id,
            actor_id="entity-linker",
        ) as session:
            session.write_node(label=node.label, node_data=node_data, merge=True)

    def _create_edge(self, edge: GraphEdgeSpec, connection: "Neo4jConnection"):
        """Create an edge in Neo4j via the governed write surface."""
        connection = self._require_connection(connection)
        rel_data = self._validated_relationship_data(edge)

        import uuid

        correlation_id = str(uuid.uuid4())
        with connection.governed_session(
            correlation_id=correlation_id,
            actor_id="entity-linker",
        ) as session:
            session.write_relationship(
                source_type=edge.from_label,
                source_id=edge.from_id,
                relationship_type=edge.relationship_type,
                target_type=edge.to_label,
                target_id=edge.to_id,
                rel_data=rel_data,
                merge=True,
            )
```

### E. Replace `link_and_submit`

Replace the free-form adapter signature with explicit connection typing:

```python
def link_and_submit(
    entities: Dict[str, List[Dict[str, Any]]],
    case_id: str,
    case_metadata: Optional[Dict[str, Any]] = None,
    connection: Optional["Neo4jConnection"] = None,
) -> LinkingResult:
    """
    Link entities and optionally submit to Neo4j.

    Args:
        entities: NER output
        case_id: Case identifier
        case_metadata: Optional case metadata
        connection: Optional Neo4jConnection for governed submission

    Returns:
        LinkingResult with statistics
    """
    linker = EntityLinker()
    result = linker.link_with_result(entities, case_id, case_metadata)

    if connection is not None:
        EntityLinker._require_connection(connection)

    if connection and result.success:
        nodes, edges = linker.link(entities, case_id, case_metadata)
        linker.submit_to_neo4j(nodes, edges, connection=connection)

    return result
```

---

## 2) `mahoun/graph/ultra_graph_builder.py`

### A. Remove the stale adapter import block

Delete this entire block:

```python
# Try to import Neo4j adapter
try:
    from mahoun.graph.neo4j_adapter import Neo4jAdapter

    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```

Also remove this unused import:

```python
from types import MappingProxyType
```

### B. Add local export allowlists after `logger = logging.getLogger(__name__)`

```python
_ULTRA_EXPORT_ALLOWED_LABELS = frozenset(
    {
        "Article",
        "Case",
        "Chunk",
        "Court",
        "Document",
        "Entity",
        "Evidence",
        "GraphNode",
        "Law",
        "LawArticle",
        "Organization",
        "Person",
        "Tag",
        "Topic",
        "Verdict",
    }
)

_ULTRA_EXPORT_ALLOWED_EDGE_TYPES = frozenset(
    {
        "AMENDS",
        "APPLIES",
        "BASED_ON",
        "CITES",
        "CONTAINS",
        "CONTRADICTS",
        "DERIVED_FROM",
        "DISCUSSES",
        "DISTINGUISHES",
        "EXTRACTED_FROM",
        "FOLLOWS",
        "HAS_PARTY",
        "HAS_TAG",
        "IMPLEMENTS",
        "INTERPRETS",
        "MENTIONED_IN",
        "OVERRULES",
        "PARTY_TO",
        "REFERENCES",
        "REFERS_TO",
        "RELATED",
        "RELATES_TO",
        "REPEALS",
        "SUBJECT_OF",
        "SUPERSEDES",
        "SUPPORTS",
    }
)

_ULTRA_EXPORT_RESERVED_NODE_KEYS = frozenset(
    {"id", "label", "node_type", "confidence", "quality_score", "provenance"}
)

_ULTRA_EXPORT_RESERVED_EDGE_KEYS = frozenset(
    {"weight", "confidence", "quality_score", "provenance"}
)

_ULTRA_EXPORT_ALLOWED_NODE_PROPERTY_KEYS = frozenset(
    {
        "article",
        "article_number",
        "branch",
        "case_id",
        "case_type",
        "category",
        "chunk_end",
        "chunk_id",
        "chunk_start",
        "city",
        "code",
        "condition",
        "conclusion",
        "court_level",
        "date",
        "decision_date",
        "description",
        "doc_end",
        "doc_id",
        "doc_start",
        "father_name",
        "is_final",
        "law_name",
        "name",
        "national_id",
        "normalized_name",
        "org_type",
        "party",
        "province",
        "registration_id",
        "role",
        "source",
        "status",
        "summary",
        "text",
        "title",
        "type",
    }
)

_ULTRA_EXPORT_ALLOWED_EDGE_PROPERTY_KEYS = frozenset(
    {
        "contradiction_type",
        "description",
        "exception_type",
        "qualification",
        "reference_type",
        "relevance",
        "role",
        "source",
        "status",
        "support_type",
        "type",
    }
)
```

### C. Add helper methods inside `UltraGraphBuilder`, before `export_to_json`

```python
    @staticmethod
    def _validate_export_label(label: str) -> str:
        base_label = label[len("Quarantined"):] if label.startswith("Quarantined") else label
        if base_label not in _ULTRA_EXPORT_ALLOWED_LABELS:
            raise ValueError(f"Invalid export label: {label}")
        return label

    @staticmethod
    def _validate_export_relationship_type(relationship_type: str) -> str:
        if relationship_type not in _ULTRA_EXPORT_ALLOWED_EDGE_TYPES:
            raise ValueError(f"Invalid export relationship type: {relationship_type}")
        return relationship_type

    @staticmethod
    def _validate_export_properties(
        properties: Optional[Dict[str, Any]],
        *,
        allowed_keys: Set[str],
        reserved_keys: Set[str],
        entity_kind: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        if properties is None:
            return {}

        if not isinstance(properties, dict):
            raise TypeError(
                f"{entity_kind} properties for '{entity_id}' must be a dict, "
                f"got {type(properties).__name__}"
            )

        collisions = set(properties) & set(reserved_keys)
        if collisions:
            raise ValueError(
                f"{entity_kind} properties for '{entity_id}' override reserved keys: "
                f"{sorted(collisions)}"
            )

        unknown = set(properties) - set(allowed_keys)
        if unknown:
            raise ValueError(
                f"{entity_kind} properties for '{entity_id}' contain unsupported keys: "
                f"{sorted(unknown)}"
            )

        return dict(properties)
```

### D. Replace `export_to_neo4j`

```python
    def export_to_neo4j(self, governed_session) -> bool:
        """
        Export graph to Neo4j database through GovernedNeo4jSession.

        GOVERNANCE ENFORCEMENT: All writes MUST go through GovernedNeo4jSession.
        Direct adapter access is FORBIDDEN.

        Args:
            governed_session: Initialized GovernedNeo4jSession instance
                (NOT a raw Neo4j adapter — that would bypass governance)

        Returns:
            True if export successful, False otherwise
        """
        try:
            logger.info("Exporting graph to Neo4j via GovernedNeo4jSession")

            from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession

            if not isinstance(governed_session, GovernedNeo4jSession):
                raise TypeError(
                    f"GOVERNANCE VIOLATION: export_to_neo4j requires GovernedNeo4jSession, "
                    f"got {type(governed_session).__name__}. Direct Neo4j access is FORBIDDEN."
                )

            for node in self.nodes.values():
                label = node.node_type or "GraphNode"
                if node.confidence < 1.0:
                    label = f"Quarantined{label}"
                    logger.warning(
                        f"Node '{node.id}' routed to quarantine (confidence={node.confidence:.2f})"
                    )

                self._validate_export_label(label)

                node_properties = self._validate_export_properties(
                    node.properties,
                    allowed_keys=_ULTRA_EXPORT_ALLOWED_NODE_PROPERTY_KEYS,
                    reserved_keys=_ULTRA_EXPORT_RESERVED_NODE_KEYS,
                    entity_kind="node",
                    entity_id=node.id,
                )

                node_data = {
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "confidence": node.confidence,
                    "quality_score": node.quality_score,
                    "provenance": {
                        "source": "ultra_graph_builder",
                        "source_documents": node.source_documents,
                        "created_at": node.created_at.isoformat() if node.created_at else None,
                    },
                    **node_properties,
                }

                governed_session.write_node(label=label, node_data=node_data, merge=True)

            for edge in self.edges:
                source_node = self.nodes.get(edge.source_id)
                target_node = self.nodes.get(edge.target_id)

                source_type = (source_node.node_type or "GraphNode") if source_node else "GraphNode"
                target_type = (target_node.node_type or "GraphNode") if target_node else "GraphNode"

                if source_node and source_node.confidence < 1.0:
                    source_type = f"Quarantined{source_type}"
                if target_node and target_node.confidence < 1.0:
                    target_type = f"Quarantined{target_type}"

                self._validate_export_label(source_type)
                self._validate_export_label(target_type)
                self._validate_export_relationship_type(edge.relationship_type)

                rel_properties = self._validate_export_properties(
                    edge.properties,
                    allowed_keys=_ULTRA_EXPORT_ALLOWED_EDGE_PROPERTY_KEYS,
                    reserved_keys=_ULTRA_EXPORT_RESERVED_EDGE_KEYS,
                    entity_kind="relationship",
                    entity_id=f"{edge.source_id}->{edge.target_id}",
                )

                rel_data = {
                    "weight": edge.weight,
                    "confidence": edge.confidence,
                    "quality_score": edge.quality_score,
                    "provenance": {
                        "source": "ultra_graph_builder",
                        "evidence": edge.evidence,
                        "created_at": edge.created_at.isoformat() if edge.created_at else None,
                    },
                    **rel_properties,
                }

                governed_session.write_relationship(
                    source_type=source_type,
                    source_id=edge.source_id,
                    relationship_type=edge.relationship_type,
                    target_type=target_type,
                    target_id=edge.target_id,
                    rel_data=rel_data,
                    merge=True,
                )

            logger.info(
                f"Exported {len(self.nodes)} nodes and {len(self.edges)} relationships "
                f"to Neo4j via GovernedNeo4jSession"
            )
            return True

        except Exception as e:
            logger.error(f"Neo4j governed export failed: {e}")
            raise
```

---

## 3) `mahoun/ultra_systems/graph/ultra_graph_builder.py`

### A. Remove the legacy adapter block

Delete:

```python
# Try to import Neo4j adapter
try:
    from graph.neo4j_adapter import Neo4jAdapter
    HAS_NEO4J = True
except ImportError:
    Neo4jAdapter = object  # Dummy class for type hints
    HAS_NEO4J = False
```

### B. Add local export allowlists near the top

```python
_ULTRA_SYSTEMS_EXPORT_LABELS = frozenset({"GraphNode"})
_ULTRA_SYSTEMS_EXPORT_RELATIONSHIP_TYPES = frozenset({"RELATED"})

_ULTRA_SYSTEMS_RESERVED_NODE_KEYS = frozenset(
    {"id", "label", "node_type", "confidence", "quality_score"}
)

_ULTRA_SYSTEMS_RESERVED_EDGE_KEYS = frozenset(
    {"type", "weight", "confidence", "quality_score"}
)

_ULTRA_SYSTEMS_ALLOWED_NODE_PROPERTY_KEYS = frozenset(
    {
        "article",
        "article_number",
        "branch",
        "case_id",
        "case_type",
        "category",
        "chunk_end",
        "chunk_id",
        "chunk_start",
        "city",
        "code",
        "condition",
        "conclusion",
        "court_level",
        "date",
        "decision_date",
        "description",
        "doc_end",
        "doc_id",
        "doc_start",
        "father_name",
        "is_final",
        "law_name",
        "name",
        "national_id",
        "normalized_name",
        "org_type",
        "party",
        "province",
        "registration_id",
        "role",
        "source",
        "status",
        "summary",
        "text",
        "title",
        "type",
    }
)

_ULTRA_SYSTEMS_ALLOWED_EDGE_PROPERTY_KEYS = frozenset(
    {
        "contradiction_type",
        "description",
        "exception_type",
        "qualification",
        "reference_type",
        "relevance",
        "role",
        "source",
        "status",
        "support_type",
    }
)
```

### C. Add helper methods inside `UltraGraphBuilder`, before `export_to_json`

```python
    @staticmethod
    def _validate_export_label(label: str) -> str:
        if label not in _ULTRA_SYSTEMS_EXPORT_LABELS:
            raise ValueError(f"Invalid export label: {label}")
        return label

    @staticmethod
    def _validate_export_relationship_type(relationship_type: str) -> str:
        if relationship_type not in _ULTRA_SYSTEMS_EXPORT_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid export relationship type: {relationship_type}")
        return relationship_type

    @staticmethod
    def _validate_export_properties(
        properties: Optional[Dict[str, Any]],
        *,
        allowed_keys: Set[str],
        reserved_keys: Set[str],
        entity_kind: str,
        entity_id: str,
    ) -> Dict[str, Any]:
        if properties is None:
            return {}

        if not isinstance(properties, dict):
            raise TypeError(
                f"{entity_kind} properties for '{entity_id}' must be a dict, "
                f"got {type(properties).__name__}"
            )

        collisions = set(properties) & set(reserved_keys)
        if collisions:
            raise ValueError(
                f"{entity_kind} properties for '{entity_id}' override reserved keys: "
                f"{sorted(collisions)}"
            )

        unknown = set(properties) - set(allowed_keys)
        if unknown:
            raise ValueError(
                f"{entity_kind} properties for '{entity_id}' contain unsupported keys: "
                f"{sorted(unknown)}"
            )

        return dict(properties)
```

### D. Replace `export_to_neo4j`

```python
    def export_to_neo4j(self, connection: "Neo4jConnection") -> bool:
        """
        Export graph to Neo4j database through the governed write surface.

        Args:
            connection: Initialized Neo4jConnection instance

        Returns:
            True if export successful, False otherwise
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        import uuid

        if not isinstance(connection, Neo4jConnection):
            raise TypeError(
                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
            )

        try:
            print("📤 Exporting graph to Neo4j...")

            export_label = self._validate_export_label("GraphNode")
            export_relationship_type = self._validate_export_relationship_type("RELATED")
            correlation_id = str(uuid.uuid4())

            with connection.governed_session(
                correlation_id=correlation_id,
                actor_id="ultra-graph-builder",
            ) as session:
                for node in self.nodes.values():
                    node_properties = self._validate_export_properties(
                        node.properties,
                        allowed_keys=_ULTRA_SYSTEMS_ALLOWED_NODE_PROPERTY_KEYS,
                        reserved_keys=_ULTRA_SYSTEMS_RESERVED_NODE_KEYS,
                        entity_kind="node",
                        entity_id=node.id,
                    )

                    node_data = {
                        "id": node.id,
                        "label": node.label,
                        "node_type": node.node_type,
                        "confidence": node.confidence,
                        "quality_score": node.quality_score,
                        **node_properties,
                    }

                    session.write_node(label=export_label, node_data=node_data, merge=True)

                for edge in self.edges:
                    edge_properties = self._validate_export_properties(
                        edge.properties,
                        allowed_keys=_ULTRA_SYSTEMS_ALLOWED_EDGE_PROPERTY_KEYS,
                        reserved_keys=_ULTRA_SYSTEMS_RESERVED_EDGE_KEYS,
                        entity_kind="relationship",
                        entity_id=f"{edge.source_id}->{edge.target_id}",
                    )

                    rel_data = {
                        "type": edge.relationship_type,
                        "weight": edge.weight,
                        "confidence": edge.confidence,
                        "quality_score": edge.quality_score,
                        **edge_properties,
                    }

                    session.write_relationship(
                        source_type=export_label,
                        source_id=edge.source_id,
                        relationship_type=export_relationship_type,
                        target_type=export_label,
                        target_id=edge.target_id,
                        rel_data=rel_data,
                        merge=True,
                    )

            print(
                f"   ✅ Exported {len(self.nodes)} nodes and {len(self.edges)} "
                f"relationships to Neo4j"
            )
            return True

        except Exception as e:
            print(f"   ❌ Neo4j export failed: {e}")
            return False
```

---

## Key changes this patch makes

Only these three files are in scope:

- `mahoun/graph/builders/entity_linker.py`
- `mahoun/graph/ultra_graph_builder.py`
- `mahoun/ultra_systems/graph/ultra_graph_builder.py`

And the changes are:

- `entity_linker.py`
  - replaces free-form `neo4j_adapter` with explicit `connection: Optional[Neo4jConnection]`
  - enforces `Neo4jConnection` via `isinstance(...)`
  - removes raw mutation `session.run(...)`
  - fixes the `self.connection` bug by using the passed `connection`
  - adds explicit local label/property/relationship allowlists
  - removes unsupported `operation_type=` kwargs

- `mahoun/graph/ultra_graph_builder.py`
  - removes stale `Neo4jAdapter` import/dummy pattern
  - keeps governed export via `GovernedNeo4jSession`
  - adds local allowlists for labels, edge types, and exported property keys
  - keeps all writes on `write_node(...)` / `write_relationship(...)`
  - adds no raw mutation strings

- `mahoun/ultra_systems/graph/ultra_graph_builder.py`
  - removes legacy adapter import/dummy pattern
  - replaces raw Cypher + `session.run(...)` with governed typed writes
  - preserves `Neo4jConnection` enforcement
  - adds local allowlists
  - removes unsupported `operation_type=` kwargs

## Important note

After this hardening, `EntityLinker` edge submission will now be fully governed by `write_relationship(...)`. If your current ontology does **not** admit shapes like `Person -[PARTY_IN]-> Case`, those writes will now correctly **fail closed** instead of mutating via raw Cypher.

## Validation

I did **not** run validation, because I could not actually apply the edits in this read-only tool session.

If you want, I can turn the above into a single `git apply`-ready unified diff block next.
