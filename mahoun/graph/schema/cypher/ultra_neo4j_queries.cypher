// ============================================================================
// Ultra-Advanced Neo4j Queries for RAG & Knowledge Graph
// ============================================================================
//
// Collection of production-ready Cypher queries for:
// - RAG retrieval
// - Graph analytics
// - Entity resolution
// - Citation analysis
// - Temporal queries
// - Vector similarity search
//
// Author: MAHOUN Advanced AI Team
// Date: 2024-11-08
// ============================================================================

// ============================================================================
// 1. RAG RETRIEVAL QUERIES
// ============================================================================

// --- 1.1: Hybrid Search (Vector + Full-text + Graph) ---
// Find relevant documents using multiple signals
CALL {
  // Vector similarity search
  MATCH (query:Document {id: $query_doc_id})
  CALL db.index.vector.queryNodes('document_embedding_vector', $top_k, query.embedding)
  YIELD node AS doc1, score AS vector_score
  RETURN doc1, vector_score, 0 AS text_score, 0 AS graph_score
  
  UNION
  
  // Full-text search
  CALL db.index.fulltext.queryNodes('document_text_fulltext', $query_text)
  YIELD node AS doc2, score AS text_score
  RETURN doc2, 0 AS vector_score, text_score, 0 AS graph_score
  
  UNION
  
  // Graph-based retrieval (connected documents)
  MATCH (seed:Document {id: $query_doc_id})-[:CITES|REFERENCES*1..2]-(doc3:Document)
  WITH doc3, COUNT(*) AS path_count
  RETURN doc3, 0 AS vector_score, 0 AS text_score, path_count * 0.1 AS graph_score
}
WITH node, 
     vector_score * $vector_weight + 
     text_score * $text_weight + 
     graph_score * $graph_weight AS hybrid_score
WHERE hybrid_score > $min_score
RETURN node.id, node.title, node.text, hybrid_score
ORDER BY hybrid_score DESC
LIMIT $top_k;

// --- 1.2: Multi-hop Graph Retrieval ---
// Retrieve documents through entity connections
MATCH (query:Document {id: $query_doc_id})-[:MENTIONS]->(e:Entity)
WITH COLLECT(DISTINCT e) AS query_entities
UNWIND query_entities AS qe
MATCH (qe)<-[:MENTIONS]-(doc:Document)
WHERE doc.id <> $query_doc_id
WITH doc, COUNT(DISTINCT qe) AS entity_overlap, query_entities
WITH doc, entity_overlap, SIZE(query_entities) AS total_entities
WITH doc, entity_overlap * 1.0 / total_entities AS relevance_score
WHERE relevance_score > $min_relevance
RETURN doc.id, doc.title, relevance_score
ORDER BY relevance_score DESC
LIMIT $top_k;

// --- 1.3: Citation Network Retrieval ---
// Find documents through citation network
MATCH path = (query:Document {id: $query_doc_id})-[:CITES*1..3]-(doc:Document)
WITH doc, LENGTH(path) AS hops, COUNT(path) AS path_count
WITH doc, 1.0 / (hops + 1) AS hop_score, path_count
WITH doc, hop_score * path_count AS citation_score
RETURN doc.id, doc.title, citation_score
ORDER BY citation_score DESC
LIMIT $top_k;

// --- 1.4: Temporal-aware Retrieval ---
// Retrieve recent and relevant documents
MATCH (doc:Document)
WHERE doc.created_at >= datetime($start_date)
  AND doc.created_at <= datetime($end_date)
WITH doc, 
     duration.between(doc.created_at, datetime()).days AS age_days
WITH doc, 
     EXP(-age_days / 365.0) AS recency_score
WHERE doc.text CONTAINS $query_text
RETURN doc.id, doc.title, doc.created_at, recency_score
ORDER BY recency_score DESC
LIMIT $top_k;

// ============================================================================
// 2. GRAPH ANALYTICS QUERIES
// ============================================================================

// --- 2.1: PageRank Computation ---
// Compute PageRank for all documents
CALL gds.graph.project(
  'documentGraph',
  'Document',
  {
    CITES: {orientation: 'NATURAL'},
    REFERENCES: {orientation: 'NATURAL'}
  }
);

CALL gds.pageRank.write('documentGraph', {
  writeProperty: 'pagerank',
  dampingFactor: 0.85,
  maxIterations: 20
})
YIELD nodePropertiesWritten, ranIterations;

// --- 2.2: Community Detection (Louvain) ---
// Detect communities in the graph
CALL gds.louvain.write('documentGraph', {
  writeProperty: 'community_id',
  includeIntermediateCommunities: false
})
YIELD communityCount, modularity;

// --- 2.3: Centrality Measures ---
// Compute betweenness centrality
CALL gds.betweenness.write('documentGraph', {
  writeProperty: 'betweenness_centrality'
})
YIELD centralityDistribution;

// Compute closeness centrality
CALL gds.closeness.write('documentGraph', {
  writeProperty: 'closeness_centrality'
})
YIELD centralityDistribution;

// --- 2.4: Node Similarity ---
// Find similar nodes based on relationships
CALL gds.nodeSimilarity.write('documentGraph', {
  writeRelationshipType: 'SIMILAR_TO',
  writeProperty: 'similarity_score',
  similarityCutoff: 0.7
})
YIELD nodesCompared, relationshipsWritten;

// ============================================================================
// 3. ENTITY RESOLUTION & LINKING
// ============================================================================

// --- 3.1: Find Duplicate Entities ---
// Identify potential duplicate entities
MATCH (e1:Entity), (e2:Entity)
WHERE e1.id < e2.id
  AND e1.label = e2.label
  AND (
    e1.text = e2.text OR
    e1.canonical_form = e2.canonical_form OR
    gds.similarity.cosine(e1.embedding, e2.embedding) > 0.95
  )
RETURN e1.id, e1.text, e2.id, e2.text,
       gds.similarity.cosine(e1.embedding, e2.embedding) AS similarity;

// --- 3.2: Merge Duplicate Entities ---
// Merge two entities into one
MATCH (e1:Entity {id: $entity1_id})
MATCH (e2:Entity {id: $entity2_id})
CALL apoc.refactor.mergeNodes([e1, e2], {
  properties: 'combine',
  mergeRels: true
})
YIELD node
RETURN node;

// --- 3.3: Entity Co-occurrence Analysis ---
// Find entities that frequently co-occur
MATCH (e1:Entity)<-[:MENTIONS]-(d:Document)-[:MENTIONS]->(e2:Entity)
WHERE e1.id < e2.id
WITH e1, e2, COUNT(DISTINCT d) AS co_occurrence_count, COLLECT(DISTINCT d.id) AS documents
WHERE co_occurrence_count >= $min_cooccurrence
MERGE (e1)-[r:CO_OCCURS]->(e2)
SET r.count = co_occurrence_count,
    r.documents = documents,
    r.confidence = co_occurrence_count * 1.0 / $total_documents
RETURN e1.text, e2.text, co_occurrence_count;

// --- 3.4: Entity Linking to Knowledge Base ---
// Link entities to external knowledge bases
MATCH (e:Entity)
WHERE e.knowledge_base_id IS NULL
  AND e.confidence > 0.8
WITH e
// Call external API or use pre-computed mappings
SET e.knowledge_base_id = $kb_id,
    e.updated_at = datetime()
RETURN e.id, e.text, e.knowledge_base_id;

// ============================================================================
// 4. CITATION ANALYSIS
// ============================================================================

// --- 4.1: Citation Count ---
// Count citations for each document
MATCH (doc:Document)
OPTIONAL MATCH (doc)<-[r:CITES]-(citing:Document)
WITH doc, COUNT(r) AS citation_count
SET doc.citation_count = citation_count
RETURN doc.id, doc.title, citation_count
ORDER BY citation_count DESC;

// --- 4.2: H-Index Calculation ---
// Calculate h-index for documents/authors
MATCH (doc:Document)
OPTIONAL MATCH (doc)<-[:CITES]-(citing:Document)
WITH doc, COUNT(citing) AS citations
ORDER BY citations DESC
WITH COLLECT({doc: doc, citations: citations}) AS docs
UNWIND RANGE(0, SIZE(docs)-1) AS idx
WITH docs[idx] AS item, idx + 1 AS rank
WHERE item.citations >= rank
RETURN MAX(rank) AS h_index;

// --- 4.3: Citation Network Visualization ---
// Get citation network for visualization
MATCH path = (d1:Document)-[:CITES]->(d2:Document)
WHERE d1.created_at >= datetime($start_date)
RETURN d1.id AS source, 
       d2.id AS target,
       d1.title AS source_title,
       d2.title AS target_title
LIMIT 1000;

// --- 4.4: Find Influential Papers (High Citations + PageRank) ---
// Identify most influential documents
MATCH (doc:Document)
WHERE doc.citation_count IS NOT NULL
  AND doc.pagerank IS NOT NULL
WITH doc,
     doc.citation_count * 0.5 + doc.pagerank * 100 * 0.5 AS influence_score
RETURN doc.id, doc.title, doc.citation_count, doc.pagerank, influence_score
ORDER BY influence_score DESC
LIMIT 20;

// ============================================================================
// 5. LEGAL-SPECIFIC QUERIES
// ============================================================================

// --- 5.1: Find Applicable Laws ---
// Find laws applicable to a case
MATCH (v:Verdict {id: $verdict_id})-[:CITES]->(l:Law)
RETURN l.law_number, l.title, l.status
ORDER BY l.law_number;

// --- 5.2: Find Legal Precedents ---
// Find similar verdicts (precedents)
MATCH (v1:Verdict {id: $verdict_id})
CALL db.index.vector.queryNodes('verdict_embedding_vector', 10, v1.embedding)
YIELD node AS v2, score
WHERE v2.id <> v1.id
  AND v2.date < v1.date
RETURN v2.verdict_number, v2.date, v2.summary, score
ORDER BY score DESC;

// --- 5.3: Track Law Amendments ---
// Find amendment history of a law
MATCH path = (l:Law {law_number: $law_number})<-[:AMENDS*]-(amendment:Law)
RETURN path
ORDER BY amendment.effective_date DESC;

// --- 5.4: Find Superseded Laws ---
// Find laws that have been superseded
MATCH (old:Law)-[r:SUPERSEDED_BY]->(new:Law)
WHERE old.status = 'repealed'
RETURN old.law_number, old.title, new.law_number, new.title, r.effective_date;

// --- 5.5: Court Hierarchy Analysis ---
// Analyze verdicts by court level
MATCH (v:Verdict)-[:ISSUED_BY]->(c:Court)
WITH c.level AS court_level, COUNT(v) AS verdict_count
RETURN court_level, verdict_count
ORDER BY verdict_count DESC;

// ============================================================================
// 6. ADVANCED PATTERN MATCHING
// ============================================================================

// --- 6.1: Find Reasoning Chains ---
// Find reasoning chains from query to answer
MATCH path = shortestPath(
  (query:Entity {text: $query_entity})-[*..5]-(answer:Entity {text: $answer_entity})
)
RETURN [node IN nodes(path) | node.text] AS reasoning_chain,
       [rel IN relationships(path) | type(rel)] AS relation_types,
       LENGTH(path) AS chain_length;

// --- 6.2: Subgraph Extraction ---
// Extract subgraph around a node
MATCH (center:Document {id: $doc_id})
CALL apoc.path.subgraphAll(center, {
  relationshipFilter: 'CITES>|REFERENCES>|MENTIONS>',
  minLevel: 1,
  maxLevel: 2
})
YIELD nodes, relationships
RETURN nodes, relationships;

// --- 6.3: Pattern Detection ---
// Detect specific patterns (e.g., triangles)
MATCH (d1:Document)-[:CITES]->(d2:Document)-[:CITES]->(d3:Document)-[:CITES]->(d1)
RETURN d1.id, d2.id, d3.id
LIMIT 100;

// --- 6.4: Anomaly Detection ---
// Find documents with unusual citation patterns
MATCH (doc:Document)
OPTIONAL MATCH (doc)<-[:CITES]-(citing)
WITH doc, COUNT(citing) AS in_citations
OPTIONAL MATCH (doc)-[:CITES]->(cited)
WITH doc, in_citations, COUNT(cited) AS out_citations
WHERE in_citations > 100 AND out_citations = 0
RETURN doc.id, doc.title, in_citations, out_citations;

// ============================================================================
// 7. PERFORMANCE OPTIMIZATION QUERIES
// ============================================================================

// --- 7.1: Index Usage Analysis ---
// Check index usage
CALL db.indexes()
YIELD name, type, state, populationPercent
RETURN name, type, state, populationPercent;

// --- 7.2: Query Performance Profiling ---
// Profile a query
PROFILE
MATCH (d:Document)-[:MENTIONS]->(e:Entity)
WHERE e.label = 'PERSON'
RETURN d.id, COUNT(e) AS person_count
ORDER BY person_count DESC
LIMIT 10;

// --- 7.3: Database Statistics ---
// Get database statistics
CALL apoc.meta.stats()
YIELD labelCount, relTypeCount, propertyKeyCount, nodeCount, relCount
RETURN labelCount, relTypeCount, propertyKeyCount, nodeCount, relCount;

// --- 7.4: Memory Usage ---
// Check memory usage
CALL dbms.queryJmx('java.lang:type=Memory')
YIELD attributes
RETURN attributes.HeapMemoryUsage.value.used AS heapUsed,
       attributes.HeapMemoryUsage.value.max AS heapMax;

// ============================================================================
// 8. DATA QUALITY & MAINTENANCE
// ============================================================================

// --- 8.1: Find Orphan Nodes ---
// Find nodes with no relationships
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) AS label, COUNT(n) AS count;

// --- 8.2: Remove Duplicate Relationships ---
// Remove duplicate relationships
MATCH (a)-[r:CITES]->(b)
WITH a, b, type(r) AS rel_type, COLLECT(r) AS rels
WHERE SIZE(rels) > 1
FOREACH (r IN TAIL(rels) | DELETE r);

// --- 8.3: Update Missing Properties ---
// Update nodes with missing properties
MATCH (d:Document)
WHERE d.word_count IS NULL AND d.text IS NOT NULL
SET d.word_count = SIZE(SPLIT(d.text, ' '));

// --- 8.4: Data Validation ---
// Validate data integrity
MATCH (d:Document)
WHERE d.created_at > datetime()
RETURN d.id, d.created_at AS future_date;

// ============================================================================
// 9. BATCH OPERATIONS
// ============================================================================

// --- 9.1: Batch Node Creation ---
// Create multiple nodes efficiently
UNWIND $documents AS doc
CREATE (d:Document)
SET d = doc,
    d.created_at = datetime();

// --- 9.2: Batch Relationship Creation ---
// Create multiple relationships efficiently
UNWIND $citations AS citation
MATCH (source:Document {id: citation.source_id})
MATCH (target:Document {id: citation.target_id})
MERGE (source)-[r:CITES]->(target)
SET r.created_at = datetime();

// --- 9.3: Batch Update ---
// Update multiple nodes efficiently
MATCH (d:Document)
WHERE d.language IS NULL
CALL apoc.periodic.iterate(
  'MATCH (d:Document) WHERE d.language IS NULL RETURN d',
  'SET d.language = "fa"',
  {batchSize: 1000}
);

// ============================================================================
// 10. EXPORT & BACKUP
// ============================================================================

// --- 10.1: Export to JSON ---
// Export graph data to JSON
CALL apoc.export.json.all("graph_export.json", {
  useTypes: true,
  storeNodeIds: true
});

// --- 10.2: Export Subgraph ---
// Export specific subgraph
MATCH path = (d:Document)-[r:CITES]->(d2:Document)
WHERE d.created_at >= datetime('2024-01-01')
WITH COLLECT(path) AS paths
CALL apoc.export.json.data(
  [node IN nodes(paths) | node],
  [rel IN relationships(paths) | rel],
  "subgraph_export.json",
  {}
);

// --- 10.3: Backup Specific Labels ---
// Backup specific node types
MATCH (l:Law)
WITH COLLECT(l) AS laws
CALL apoc.export.json.data(laws, [], "laws_backup.json", {});

// ============================================================================
// END OF QUERIES
// ============================================================================
