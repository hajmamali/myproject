"""
Structural Validation Cypher Queries
===================================

Reusable Cypher queries for validating graph structure.
"""

# Node Label Queries
QUERY_ALL_LABELS = """
CALL db.labels() YIELD label
RETURN label
ORDER BY label
"""

QUERY_NODES_BY_LABEL = """
MATCH (n:{label})
RETURN count(n) as count
"""

# Required Label Existence
QUERY_REQUIRED_LABELS_EXIST = """
CALL db.labels() YIELD label
WHERE label IN $expected_labels
RETURN count(label) as count
"""

# Required Property Queries
QUERY_NODES_MISSING_PROPERTY = """
MATCH (n:{label})
WHERE n.{property} IS NULL OR n.{property} = ''
RETURN count(n) as count
"""

QUERY_LAW_MISSING_CANONICAL_ID = """
MATCH (l:Law)
WHERE l.canonical_id IS NULL OR l.canonical_id = ''
RETURN count(l) as count
"""

QUERY_ARTICLE_MISSING_ARTICLE_NUMBER = """
MATCH (a:Article)
WHERE a.article_number IS NULL OR a.article_number = ''
RETURN count(a) as count
"""

QUERY_ARTICLE_MISSING_TEXT_FA = """
MATCH (a:Article)
WHERE a.text_fa IS NULL OR a.text_fa = ''
RETURN count(a) as count
"""

# Orphan Node Queries
QUERY_ORPHAN_CHAPTERS = """
MATCH (c:Chapter)
WHERE NOT (c)<-[:HAS_CHAPTER]-(:Law)
RETURN count(c) as count
"""

QUERY_ORPHAN_ARTICLES = """
MATCH (a:Article)
WHERE NOT (a)<-[:HAS_ARTICLE]-(:Chapter)
AND NOT (a)<-[:HAS_ARTICLE*2]-(:Law)
RETURN count(a) as count
"""

QUERY_ORPHAN_PARAGRAPHS = """
MATCH (p:Paragraph)
WHERE NOT (p)<-[:HAS_PARAGRAPH]-(:Article)
RETURN count(p) as count
"""

QUERY_ORPHAN_CLAUSES = """
MATCH (c:Clause)
WHERE NOT (c)<-[:HAS_CLAUSE]-(:Paragraph)
RETURN count(c) as count
"""

# Duplicate Canonical ID Queries
QUERY_DUPLICATE_CANONICAL_IDS = """
MATCH (n)
WITH n.canonical_id as cid, count(n) as cnt
WHERE cnt > 1
RETURN cid, cnt
ORDER BY cnt DESC
"""

QUERY_LAW_DUPLICATE_CANONICAL_IDS = """
MATCH (l:Law)
WITH l.canonical_id as cid, count(l) as cnt
WHERE cnt > 1
RETURN cid, cnt
"""

QUERY_ARTICLE_DUPLICATE_CANONICAL_IDS = """
MATCH (a:Article)
WITH a.canonical_id as cid, count(a) as cnt
WHERE cnt > 1
RETURN cid, cnt
"""

# Relationship Type Queries
QUERY_ALL_RELATIONSHIP_TYPES = """
CALL db.relationshipTypes() YIELD relationshipType
RETURN relationshipType
ORDER BY relationshipType
"""

QUERY_RELATIONSHIPS_BY_TYPE = """
MATCH ()-[r:{type}]->()
RETURN count(r) as count
"""

QUERY_INVALID_RELATIONSHIP_TYPES = """
CALL db.relationshipTypes() YIELD relationshipType
WHERE relationshipType NOT IN $allowed_types
RETURN relationshipType
"""

# Relationship Direction Validation
QUERY_HAS_CHAPTER_WRONG_DIRECTION = """
MATCH (n)-[:HAS_CHAPTER]->()
WHERE NOT n:Law
RETURN count(n) as count
"""

QUERY_HAS_ARTICLE_WRONG_DIRECTION = """
MATCH (n)-[:HAS_ARTICLE]->()
WHERE NOT (n:Chapter AND NOT n:Law)
RETURN count(n) as count
"""

# Invalid Source/Target Node Types
QUERY_INVALID_SOURCE_FOR_HAS_CHAPTER = """
MATCH (n)-[:HAS_CHAPTER]->()
WHERE NOT n:Law
RETURN count(n) as count
"""

QUERY_INVALID_TARGET_FOR_HAS_CHAPTER = """
MATCH ()-[:HAS_CHAPTER]->(n)
WHERE NOT n:Chapter
RETURN count(n) as count
"""

QUERY_INVALID_SOURCE_FOR_HAS_ARTICLE = """
MATCH (n)-[:HAS_ARTICLE]->()
WHERE NOT (n:Chapter OR n:Law)
RETURN count(n) as count
"""

QUERY_INVALID_TARGET_FOR_HAS_ARTICLE = """
MATCH ()-[:HAS_ARTICLE]->(n)
WHERE NOT n:Article
RETURN count(n) as count
"""

# Impossible Connection Detection
QUERY_LAW_AS_CHILD_OF_ARTICLE = """
MATCH (l:Law)<-[:HAS_ARTICLE]-(a:Article)
RETURN count(l) as count
"""

QUERY_ARTICLE_AS_PARENT_OF_LAW = """
MATCH (a:Article)-[:HAS_CHAPTER]->(l:Law)
RETURN count(a) as count
"""

QUERY_CLAUSE_AS_PARENT_OF_ARTICLE = """
MATCH (c:Clause)-[:HAS_ARTICLE]->(a:Article)
RETURN count(c) as count
"""

# Broken Reference Detection
QUERY_BROKEN_ARTICLE_REFERENCES = """
MATCH (a:Article)
WHERE a.references_article IS NOT NULL
UNWIND a.references_article as ref_id
MATCH (target:Article {canonical_id: ref_id})
WITH a, ref_id, count(target) as target_count
WHERE target_count = 0
RETURN count(DISTINCT a) as count
"""

QUERY_BROKEN_LAW_REFERENCES = """
MATCH (a:Article)
WHERE a.references_law IS NOT NULL
UNWIND a.references_law as ref_id
MATCH (target:Law {canonical_id: ref_id})
WITH a, ref_id, count(target) as target_count
WHERE target_count = 0
RETURN count(DISTINCT a) as count
"""

QUERY_BROKEN_AMENDMENT_TARGETS = """
MATCH (a)-[:AMENDS]->(target)
WHERE target IS NULL
RETURN count(a) as count
"""

# Node Count by Label
QUERY_NODE_COUNT_BY_LABEL = """
MATCH (n)
WITH labels(n) as labels, count(n) as count
RETURN labels, count
ORDER BY labels
"""

# Relationship Count by Type
QUERY_RELATIONSHIP_COUNT_BY_TYPE = """
MATCH ()-[r]->()
WITH type(r) as rel_type, count(r) as count
RETURN rel_type, count
ORDER BY rel_type
"""

# Label Pair Relationship Count
QUERY_RELATIONSHIP_COUNT_BY_LABEL_PAIR = """
MATCH (a)-[r]->(b)
WITH labels(a) as source_labels, labels(b) as target_labels, type(r) as rel_type, count(r) as count
RETURN source_labels, target_labels, rel_type, count
ORDER BY source_labels, target_labels, rel_type
"""
