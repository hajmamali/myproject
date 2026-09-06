"""
Semantic Validation Cypher Queries
==================================

Reusable Cypher queries for validating semantic relationships.
"""

# Semantic Direction Validation
QUERY_REFERENCES_DIRECTION = """
MATCH (a1:Article)-[:REFERENCES]->(a2:Article)
RETURN count(*) as count
"""

QUERY_AMENDS_DIRECTION = """
MATCH (a)-[:AMENDS]->(l:Law)
RETURN count(*) as count
"""

QUERY_INTERPRETS_BY_DIRECTION = """
MATCH (a:Article)-[:INTERPRETS_BY]->(p:Precedent)
RETURN count(*) as count
"""

QUERY_OVERRIDDEN_BY_DIRECTION = """
MATCH (general)-[:OVERRIDDEN_BY]->(specific)
RETURN count(*) as count
"""

# Legal Priority Validation
QUERY_CONSTITUTIONAL_OVERRIDE_ORDINARY = """
MATCH (ordinary:Law)-[:OVERRIDDEN_BY]->(constitutional:Law)
WHERE ordinary.level = 'ordinary' AND constitutional.level = 'constitutional'
RETURN count(*) as count
"""

QUERY_STATUTORY_OVERRIDE_REGULATORY = """
MATCH (regulatory:Law)-[:OVERRIDDEN_BY]->(statutory:Law)
WHERE regulatory.level = 'regulatory' AND statutory.level = 'statutory'
RETURN count(*) as count
"""

# Interpretation Chain Validation
QUERY_INTERPRETATION_CHAIN = """
MATCH path = (a:Article)-[:INTERPRETS_BY*]->(p:Precedent)
RETURN length(path) as depth, count(*) as count
"""

QUERY_CIRCULAR_INTERPRETATION = """
MATCH path = (a:Article)-[:INTERPRETS_BY*]->(a)
WHERE length(path) > 0
RETURN count(*) as count
"""

QUERY_INTERPRETATION_DEPTH = """
MATCH (a:Article)-[:INTERPRETS_BY*]->(p:Precedent)
WHERE a.canonical_id = $article_id
RETURN length(path) as depth
"""

# Contradictory Interpretations
QUERY_CONTRADICTORY_INTERPRETATIONS = """
MATCH (a:Article)<-[:INTERPRETS]-(p1:Precedent)
MATCH (a)<-[:INTERPRETS]-(p2:Precedent)
WHERE p1.canonical_id <> p2.canonical_id
AND p1.interpretation <> p2.interpretation
RETURN a.canonical_id, p1.canonical_id, p2.canonical_id
"""

# Exception Handling Validation
QUERY_EXCEPTION_WITHOUT_GENERAL_RULE = """
MATCH (exception:Article)-[:EXCEPTS]->(general:Article)
WHERE general IS NULL
RETURN count(*) as count
"""

QUERY_EXCEPTION_BROADER_THAN_GENERAL = """
MATCH (general:Article)-[:EXCEPTS]->(exception:Article)
WHERE exception.scope > general.scope
RETURN count(*) as count
"""

# Precedence Relationship Validation
QUERY_PRECEDENCE_CYCLE = """
MATCH path = (l1:Law)-[:PRECEDES*]->(l1)
WHERE length(path) > 0
RETURN count(*) as count
"""

QUERY_PRECEDENCE_HIERARCHY = """
MATCH (higher:Law)-[:PRECEDES]->(lower:Law)
WHERE higher.level < lower.level
RETURN count(*) as count
"""

# Wrong Semantic Direction Detection
QUERY_REFERENCES_REVERSED = """
MATCH (a:Article)-[:REFERENCES]->(a2:Article)
WHERE a2.references_article CONTAINS a.canonical_id
RETURN count(*) as count
"""

QUERY_AMENDS_REVERSED = """
MATCH (l:Law)-[:AMENDS]->(a:Amendment)
RETURN count(*) as count
"""

# Incorrect Legal Priority Detection
QUERY_ORDINARY_OVERRIDES_CONSTITUTIONAL = """
MATCH (ordinary:Law)-[:OVERRIDDEN_BY]->(constitutional:Law)
WHERE ordinary.level = 'ordinary' AND constitutional.level = 'constitutional'
RETURN count(*) as count
"""

QUERY_REGULATORY_OVERRIDES_STATUTORY = """
MATCH (regulatory:Law)-[:OVERRIDDEN_BY]->(statutory:Law)
WHERE regulatory.level = 'regulatory' AND statutory.level = 'statutory'
RETURN count(*) as count
"""

# Conflict Detection
QUERY_CONFLICTING_RULES = """
MATCH (a1:Article)-[:CONFLICTS_WITH]->(a2:Article)
RETURN count(*) as count
"""

QUERY_CONFLICTS_WITH_PRECEDENCE = """
MATCH (a1:Article)-[:CONFLICTS_WITH]->(a2:Article)
RETURN a1.canonical_id, a2.canonical_id, a2.priority
"""

# Semantic Relationship Validation
QUERY_ALL_SEMANTIC_RELATIONSHIPS = """
MATCH ()-[r]->()
WHERE type(r) IN ['REFERENCES', 'CITES', 'AMENDS', 'REPLACED_BY', 'OVERRIDDEN_BY', 'INTERPRETS_BY', 'IMPLEMENTS', 'CONFLICTS_WITH', 'EXCEPTS', 'PRECEDES']
RETURN type(r), count(r) as count
ORDER BY type(r)
"""

QUERY_SEMANTIC_RELATIONSHIP_BY_TYPE = """
MATCH (a)-[:{type}]->(b)
RETURN count(*) as count
"""
