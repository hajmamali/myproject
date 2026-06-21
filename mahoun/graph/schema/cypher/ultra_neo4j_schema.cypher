// ============================================================================
// Ultra-Advanced Neo4j Schema for Knowledge Graph
// ============================================================================
// 
// Features:
// - Multi-modal nodes (documents, entities, concepts)
// - Rich relationship types
// - Temporal properties
// - Vector embeddings
// - Graph analytics properties
// - Constraints and indexes
// - Full-text search
// 
// Author: MAHOUN Advanced AI Team
// Date: 2024-11-08
// Version: 2.0.0
// ============================================================================

// ============================================================================
// 1. CONSTRAINTS (Uniqueness & Existence)
// ============================================================================

// Document constraints
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT document_id_exists IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS NOT NULL;

// Entity constraints
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT entity_text_exists IF NOT EXISTS
FOR (e:Entity) REQUIRE e.text IS NOT NULL;

// Person constraints
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

// Organization constraints
CREATE CONSTRAINT org_id_unique IF NOT EXISTS
FOR (o:Organization) REQUIRE o.id IS UNIQUE;

// Location constraints
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.id IS UNIQUE;

// Law constraints
CREATE CONSTRAINT law_id_unique IF NOT EXISTS
FOR (l:Law) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT law_number_unique IF NOT EXISTS
FOR (l:Law) REQUIRE l.law_number IS UNIQUE;

// Article constraints
CREATE CONSTRAINT article_id_unique IF NOT EXISTS
FOR (a:Article) REQUIRE a.id IS UNIQUE;

// Verdict constraints
CREATE CONSTRAINT verdict_id_unique IF NOT EXISTS
FOR (v:Verdict) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT verdict_number_unique IF NOT EXISTS
FOR (v:Verdict) REQUIRE v.verdict_number IS UNIQUE;

// Court constraints
CREATE CONSTRAINT court_id_unique IF NOT EXISTS
FOR (c:Court) REQUIRE c.id IS UNIQUE;

// Concept constraints
CREATE CONSTRAINT concept_id_unique IF NOT EXISTS
FOR (c:Concept) REQUIRE c.id IS UNIQUE;

// ============================================================================
// 2. INDEXES (Performance Optimization)
// ============================================================================

// --- Document Indexes ---
CREATE INDEX document_created_at IF NOT EXISTS
FOR (d:Document) ON (d.created_at);

CREATE INDEX document_language IF NOT EXISTS
FOR (d:Document) ON (d.language);

CREATE INDEX document_source IF NOT EXISTS
FOR (d:Document) ON (d.source);

CREATE FULLTEXT INDEX document_text_fulltext IF NOT EXISTS
FOR (d:Document) ON EACH [d.text, d.title];

// Vector index for embeddings (Neo4j 5.11+)
CREATE VECTOR INDEX document_embedding_vector IF NOT EXISTS
FOR (d:Document) ON (d.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};

// --- Entity Indexes ---
CREATE INDEX entity_label IF NOT EXISTS
FOR (e:Entity) ON (e.label);

CREATE INDEX entity_confidence IF NOT EXISTS
FOR (e:Entity) ON (e.confidence);

CREATE FULLTEXT INDEX entity_text_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.text, e.canonical_form];

CREATE VECTOR INDEX entity_embedding_vector IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};

// --- Person Indexes ---
CREATE INDEX person_name IF NOT EXISTS
FOR (p:Person) ON (p.name);

CREATE FULLTEXT INDEX person_fulltext IF NOT EXISTS
FOR (p:Person) ON EACH [p.name, p.aliases];

// --- Organization Indexes ---
CREATE INDEX org_name IF NOT EXISTS
FOR (o:Organization) ON (o.name);

CREATE INDEX org_type IF NOT EXISTS
FOR (o:Organization) ON (o.org_type);

CREATE FULLTEXT INDEX org_fulltext IF NOT EXISTS
FOR (o:Organization) ON EACH [o.name, o.aliases];

// --- Location Indexes ---
CREATE INDEX location_name IF NOT EXISTS
FOR (l:Location) ON (l.name);

CREATE INDEX location_country IF NOT EXISTS
FOR (l:Location) ON (l.country);

// --- Law Indexes ---
CREATE INDEX law_number IF NOT EXISTS
FOR (l:Law) ON (l.law_number);

CREATE INDEX law_date IF NOT EXISTS
FOR (l:Law) ON (l.approval_date);

CREATE INDEX law_status IF NOT EXISTS
FOR (l:Law) ON (l.status);

CREATE FULLTEXT INDEX law_fulltext IF NOT EXISTS
FOR (l:Law) ON EACH [l.title, l.text];

// --- Article Indexes ---
CREATE INDEX article_number IF NOT EXISTS
FOR (a:Article) ON (a.article_number);

CREATE INDEX article_law IF NOT EXISTS
FOR (a:Article) ON (a.law_id);

CREATE FULLTEXT INDEX article_fulltext IF NOT EXISTS
FOR (a:Article) ON EACH [a.text];

// --- Verdict Indexes ---
CREATE INDEX verdict_number IF NOT EXISTS
FOR (v:Verdict) ON (v.verdict_number);

CREATE INDEX verdict_date IF NOT EXISTS
FOR (v:Verdict) ON (v.date);

CREATE INDEX verdict_court IF NOT EXISTS
FOR (v:Verdict) ON (v.court_id);

CREATE FULLTEXT INDEX verdict_fulltext IF NOT EXISTS
FOR (v:Verdict) ON EACH [v.text, v.summary];

// --- Court Indexes ---
CREATE INDEX court_name IF NOT EXISTS
FOR (c:Court) ON (c.name);

CREATE INDEX court_level IF NOT EXISTS
FOR (c:Court) ON (c.level);

CREATE INDEX court_jurisdiction IF NOT EXISTS
FOR (c:Court) ON (c.jurisdiction);

// --- Concept Indexes ---
CREATE INDEX concept_name IF NOT EXISTS
FOR (c:Concept) ON (c.name);

CREATE INDEX concept_category IF NOT EXISTS
FOR (c:Concept) ON (c.category);

CREATE FULLTEXT INDEX concept_fulltext IF NOT EXISTS
FOR (c:Concept) ON EACH [c.name, c.description];

// --- Relationship Indexes ---
CREATE INDEX rel_cites_date IF NOT EXISTS
FOR ()-[r:CITES]-() ON (r.created_at);

CREATE INDEX rel_mentions_confidence IF NOT EXISTS
FOR ()-[r:MENTIONS]-() ON (r.confidence);

CREATE INDEX rel_references_type IF NOT EXISTS
FOR ()-[r:REFERENCES]-() ON (r.reference_type);

// ============================================================================
// 3. NODE LABELS & PROPERTIES
// ============================================================================

// --- Document Node ---
// Properties:
// - id: STRING (unique identifier)
// - text: STRING (document content)
// - title: STRING (document title)
// - language: STRING (language code: fa, en, ar)
// - source: STRING (source system/file)
// - format: STRING (pdf, docx, html, etc.)
// - embedding: LIST<FLOAT> (768-dim vector)
// - page_count: INTEGER
// - word_count: INTEGER
// - created_at: DATETIME
// - updated_at: DATETIME
// - metadata: MAP (additional properties)
// 
// Graph Analytics Properties:
// - pagerank: FLOAT
// - betweenness_centrality: FLOAT
// - closeness_centrality: FLOAT
// - community_id: INTEGER
// - authority_score: FLOAT
// - hub_score: FLOAT

// --- Entity Node ---
// Properties:
// - id: STRING (unique identifier)
// - text: STRING (entity text)
// - canonical_form: STRING (normalized form)
// - label: STRING (entity type: PERSON, ORG, LOC, etc.)
// - confidence: FLOAT (0-1)
// - embedding: LIST<FLOAT> (768-dim vector)
// - knowledge_base_id: STRING (Wikidata/DBpedia ID)
// - created_at: DATETIME
// - metadata: MAP

// --- Person Node ---
// Properties:
// - id: STRING
// - name: STRING
// - aliases: LIST<STRING>
// - birth_date: DATE
// - nationality: STRING
// - occupation: STRING
// - metadata: MAP

// --- Organization Node ---
// Properties:
// - id: STRING
// - name: STRING
// - aliases: LIST<STRING>
// - org_type: STRING (company, government, ngo, etc.)
// - founded_date: DATE
// - country: STRING
// - metadata: MAP

// --- Location Node ---
// Properties:
// - id: STRING
// - name: STRING
// - country: STRING
// - region: STRING
// - coordinates: POINT (latitude, longitude)
// - metadata: MAP

// --- Law Node ---
// Properties:
// - id: STRING
// - law_number: STRING (unique)
// - title: STRING
// - text: STRING
// - approval_date: DATE
// - effective_date: DATE
// - status: STRING (active, repealed, amended)
// - category: STRING
// - embedding: LIST<FLOAT>
// - metadata: MAP

// --- Article Node ---
// Properties:
// - id: STRING
// - article_number: STRING
// - law_id: STRING
// - text: STRING
// - notes: LIST<STRING>
// - embedding: LIST<FLOAT>
// - metadata: MAP

// --- Verdict Node ---
// Properties:
// - id: STRING
// - verdict_number: STRING (unique)
// - date: DATE
// - court_id: STRING
// - text: STRING
// - summary: STRING
// - outcome: STRING
// - judges: LIST<STRING>
// - embedding: LIST<FLOAT>
// - metadata: MAP

// --- Court Node ---
// Properties:
// - id: STRING
// - name: STRING
// - level: STRING (supreme, appellate, district)
// - jurisdiction: STRING
// - location: STRING
// - metadata: MAP

// --- Concept Node ---
// Properties:
// - id: STRING
// - name: STRING
// - description: STRING
// - category: STRING
// - embedding: LIST<FLOAT>
// - metadata: MAP

// ============================================================================
// 4. RELATIONSHIP TYPES
// ============================================================================

// --- CITES ---
// (Document)-[:CITES]->(Document)
// (Verdict)-[:CITES]->(Law)
// (Verdict)-[:CITES]->(Verdict)
// Properties:
// - citation_type: STRING (direct, indirect)
// - context: STRING
// - confidence: FLOAT
// - created_at: DATETIME

// --- REFERENCES ---
// (Document)-[:REFERENCES]->(Entity)
// (Article)-[:REFERENCES]->(Concept)
// Properties:
// - reference_type: STRING
// - confidence: FLOAT
// - created_at: DATETIME

// --- MENTIONS ---
// (Document)-[:MENTIONS]->(Entity)
// Properties:
// - count: INTEGER (number of mentions)
// - positions: LIST<INTEGER>
// - confidence: FLOAT
// - created_at: DATETIME

// --- PART_OF ---
// (Article)-[:PART_OF]->(Law)
// (Entity)-[:PART_OF]->(Organization)
// Properties:
// - order: INTEGER
// - created_at: DATETIME

// --- AUTHORED_BY ---
// (Document)-[:AUTHORED_BY]->(Person)
// (Law)-[:AUTHORED_BY]->(Organization)
// Properties:
// - role: STRING
// - created_at: DATETIME

// --- ISSUED_BY ---
// (Verdict)-[:ISSUED_BY]->(Court)
// Properties:
// - date: DATE
// - created_at: DATETIME

// --- SUPERSEDES ---
// (Law)-[:SUPERSEDES]->(Law)
// (Verdict)-[:SUPERSEDES]->(Verdict)
// Properties:
// - effective_date: DATE
// - reason: STRING
// - created_at: DATETIME

// --- AMENDS ---
// (Law)-[:AMENDS]->(Law)
// Properties:
// - amendment_type: STRING
// - effective_date: DATE
// - created_at: DATETIME

// --- RELATED_TO ---
// (Entity)-[:RELATED_TO]->(Entity)
// (Concept)-[:RELATED_TO]->(Concept)
// Properties:
// - relation_type: STRING
// - confidence: FLOAT
// - created_at: DATETIME

// --- CO_OCCURS ---
// (Entity)-[:CO_OCCURS]->(Entity)
// Properties:
// - count: INTEGER
// - documents: LIST<STRING>
// - confidence: FLOAT
// - created_at: DATETIME

// --- LOCATED_IN ---
// (Organization)-[:LOCATED_IN]->(Location)
// (Person)-[:LOCATED_IN]->(Location)
// Properties:
// - from_date: DATE
// - to_date: DATE
// - created_at: DATETIME

// --- WORKS_FOR ---
// (Person)-[:WORKS_FOR]->(Organization)
// Properties:
// - position: STRING
// - from_date: DATE
// - to_date: DATE
// - created_at: DATETIME

// --- SIMILAR_TO ---
// (Document)-[:SIMILAR_TO]->(Document)
// (Entity)-[:SIMILAR_TO]->(Entity)
// Properties:
// - similarity_score: FLOAT (0-1)
// - similarity_method: STRING (embedding, text, hybrid)
// - created_at: DATETIME

// ============================================================================
// 5. SAMPLE DATA (for testing)
// ============================================================================

// Create sample law
CREATE (l:Law {
  id: 'law_001',
  law_number: 'قانون مدنی',
  title: 'قانون مدنی جمهوری اسلامی ایران',
  approval_date: date('1928-05-08'),
  effective_date: date('1928-05-08'),
  status: 'active',
  category: 'civil',
  created_at: datetime(),
  metadata: {
    source: 'official_gazette',
    version: '1.0'
  }
});

// Create sample article
CREATE (a:Article {
  id: 'article_001',
  article_number: 'ماده 10',
  law_id: 'law_001',
  text: 'هر ایرانی می‌تواند در ایران اقامت اختیار کند.',
  created_at: datetime(),
  metadata: {}
});

// Link article to law
MATCH (a:Article {id: 'article_001'})
MATCH (l:Law {id: 'law_001'})
CREATE (a)-[:PART_OF {order: 10, created_at: datetime()}]->(l);

// Create sample court
CREATE (c:Court {
  id: 'court_001',
  name: 'دیوان عالی کشور',
  level: 'supreme',
  jurisdiction: 'national',
  location: 'تهران',
  created_at: datetime(),
  metadata: {}
});

// Create sample verdict
CREATE (v:Verdict {
  id: 'verdict_001',
  verdict_number: 'رأی شماره 1234',
  date: date('2024-01-15'),
  court_id: 'court_001',
  summary: 'رأی دیوان در خصوص تفسیر ماده 10 قانون مدنی',
  outcome: 'approved',
  created_at: datetime(),
  metadata: {}
});

// Link verdict to court
MATCH (v:Verdict {id: 'verdict_001'})
MATCH (c:Court {id: 'court_001'})
CREATE (v)-[:ISSUED_BY {date: date('2024-01-15'), created_at: datetime()}]->(c);

// Link verdict to law (citation)
MATCH (v:Verdict {id: 'verdict_001'})
MATCH (l:Law {id: 'law_001'})
CREATE (v)-[:CITES {
  citation_type: 'direct',
  context: 'تفسیر قانون',
  confidence: 1.0,
  created_at: datetime()
}]->(l);

// ============================================================================
// 6. UTILITY QUERIES
// ============================================================================

// --- Query 1: Find all laws cited by a verdict ---
// MATCH (v:Verdict {verdict_number: 'رأی شماره 1234'})-[r:CITES]->(l:Law)
// RETURN v.verdict_number, l.law_number, l.title, r.citation_type;

// --- Query 2: Find articles of a specific law ---
// MATCH (a:Article)-[:PART_OF]->(l:Law {law_number: 'قانون مدنی'})
// RETURN a.article_number, a.text
// ORDER BY a.article_number;

// --- Query 3: Find entities mentioned in a document ---
// MATCH (d:Document {id: 'doc_001'})-[r:MENTIONS]->(e:Entity)
// RETURN e.text, e.label, r.count, r.confidence
// ORDER BY r.count DESC;

// --- Query 4: Find similar documents using vector similarity ---
// MATCH (d:Document {id: 'doc_001'})
// CALL db.index.vector.queryNodes('document_embedding_vector', 10, d.embedding)
// YIELD node, score
// WHERE node.id <> d.id
// RETURN node.id, node.title, score
// ORDER BY score DESC;

// --- Query 5: Find co-occurring entities ---
// MATCH (e1:Entity)-[r:CO_OCCURS]->(e2:Entity)
// WHERE r.count > 5
// RETURN e1.text, e2.text, r.count
// ORDER BY r.count DESC
// LIMIT 20;

// --- Query 6: PageRank analysis ---
// CALL gds.pageRank.stream('myGraph')
// YIELD nodeId, score
// RETURN gds.util.asNode(nodeId).id AS id, score
// ORDER BY score DESC
// LIMIT 10;

// --- Query 7: Community detection ---
// CALL gds.louvain.stream('myGraph')
// YIELD nodeId, communityId
// RETURN gds.util.asNode(nodeId).id AS id, communityId
// ORDER BY communityId;

// --- Query 8: Shortest path between two entities ---
// MATCH path = shortestPath(
//   (e1:Entity {text: 'دیوان عالی'})-[*..5]-(e2:Entity {text: 'قانون مدنی'})
// )
// RETURN path;

// --- Query 9: Find influential documents (high PageRank) ---
// MATCH (d:Document)
// WHERE d.pagerank IS NOT NULL
// RETURN d.id, d.title, d.pagerank
// ORDER BY d.pagerank DESC
// LIMIT 10;

// --- Query 10: Temporal query (documents in date range) ---
// MATCH (d:Document)
// WHERE d.created_at >= datetime('2024-01-01') 
//   AND d.created_at <= datetime('2024-12-31')
// RETURN d.id, d.title, d.created_at
// ORDER BY d.created_at DESC;

// ============================================================================
// END OF SCHEMA
// ============================================================================
