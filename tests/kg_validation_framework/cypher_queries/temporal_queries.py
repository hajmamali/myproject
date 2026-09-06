"""
Temporal Validation Cypher Queries
===================================

Reusable Cypher queries for validating temporal consistency.
"""

# Effective Date Validation
QUERY_EFFECTIVE_DATE_BEFORE_PUBLICATION = """
MATCH (l:Law)
WHERE date(l.effective_date) < date(l.publication_date)
RETURN count(l) as count
"""

QUERY_FUTURE_LAWS_ACTIVE = """
MATCH (l:Law)
WHERE date(l.publication_date) > date()
AND l.status = 'active'
RETURN count(l) as count
"""

QUERY_ACTIVE_LAW_MISSING_EFFECTIVE_DATE = """
MATCH (l:Law)
WHERE l.status = 'active'
AND (l.effective_date IS NULL OR l.effective_date = '')
RETURN count(l) as count
"""

# Repealed Law Validation
QUERY_REPEALED_LAW_MISSING_REPEAL_DATE = """
MATCH (l:Law)
WHERE l.status = 'repealed'
AND (l.repeal_date IS NULL OR l.repeal_date = '')
RETURN count(l) as count
"""

QUERY_REPEAL_DATE_BEFORE_EFFECTIVE = """
MATCH (l:Law)
WHERE l.repeal_date IS NOT NULL
AND date(l.repeal_date) < date(l.effective_date)
RETURN count(l) as count
"""

QUERY_REPEALED_LAW_MARKED_ACTIVE = """
MATCH (l:Law)
WHERE l.status = 'repealed'
AND l.active = true
RETURN count(l) as count
"""

QUERY_REPEALED_LAW_MISSING_REPLACED_BY = """
MATCH (l:Law)
WHERE l.status = 'repealed'
AND (l.replaced_by IS NULL OR l.replaced_by = '')
RETURN count(l) as count
"""

# Amendment Validation
QUERY_AMENDMENT_MISSING_TARGET = """
MATCH (a:Amendment)
WHERE a.amends IS NULL OR a.amends = ''
RETURN count(a) as count
"""

QUERY_AMENDMENT_BEFORE_ORIGINAL = """
MATCH (a:Amendment)-[:AMENDS]->(l:Law)
WHERE date(a.amendment_date) < date(l.publication_date)
RETURN count(*) as count
"""

QUERY_AMENDMENT_EFFECTIVE_BEFORE_AMENDMENT = """
MATCH (a:Amendment)
WHERE date(a.effective_date) < date(a.amendment_date)
RETURN count(a) as count
"""

# Historical Version Validation
QUERY_VERSIONS_NOT_SEQUENTIAL = """
MATCH (v1:Law)-[:REPLACED_BY]->(v2:Law)
WITH v1.version as v1_ver, v2.version as v2_ver
WHERE toInteger(v1_ver) + 1 <> toInteger(v2_ver)
RETURN count(*) as count
"""

QUERY_MULTIPLE_CURRENT_VERSIONS = """
MATCH (v:Law)
WHERE v.is_current = true
WITH v.law_base as base, count(v) as current_count
WHERE current_count > 1
RETURN base, current_count
"""

QUERY_HISTORICAL_VERSION_MARKED_CURRENT = """
MATCH (v1:Law)-[:REPLACED_BY]->(v2:Law)
WHERE v1.is_current = true
RETURN count(*) as count
"""

QUERY_VERSION_MISSING_REPLACED_BY = """
MATCH (v:Law)
WHERE NOT (v)-[:REPLACED_BY]->()
AND NOT (v)<-[:REPLACED_BY]-()
AND v.version <> '1'
RETURN count(*) as count
"""

# Multiple Active Conflicting Versions
QUERY_MULTIPLE_ACTIVE_SAME_LAW = """
MATCH (v1:Law), (v2:Law)
WHERE v1.law_base = v2.law_base
AND v1.canonical_id <> v2.canonical_id
AND v1.status = 'active'
AND v2.status = 'active'
RETURN count(*) as count
"""

QUERY_ACTIVE_VERSION_FUTURE_EFFECTIVE = """
MATCH (v:Law)
WHERE v.status = 'active'
AND date(v.effective_date) > date()
RETURN count(*) as count
"""

QUERY_ACTIVE_VERSION_REPEALED = """
MATCH (v:Law)
WHERE v.status = 'active'
AND v.repeal_date IS NOT NULL
RETURN count(*) as count
"""

# Future Law Detection
QUERY_FUTURE_LAWS = """
MATCH (l:Law)
WHERE date(l.publication_date) > date()
RETURN count(*) as count
"""

QUERY_FUTURE_LAWS_NOT_PENDING = """
MATCH (l:Law)
WHERE date(l.publication_date) > date()
AND l.status <> 'pending'
RETURN count(*) as count
"""

# Repealed Article Usage
QUERY_REFERENCES_TO_REPEALED_ARTICLES = """
MATCH (a:Article)-[:REFERENCES]->(target:Article)
WHERE target.status = 'repealed'
RETURN count(*) as count
"""

QUERY_REPEALED_ARTICLE_MISSING_REPEAL_DATE = """
MATCH (a:Article)
WHERE a.status = 'repealed'
AND (a.repeal_date IS NULL OR a.repeal_date = '')
RETURN count(*) as count
"""

# Temporal Consistency
QUERY_TEMPORAL_INCONSISTENCY = """
MATCH (l:Law)
WHERE l.effective_date IS NOT NULL
AND l.repeal_date IS NOT NULL
AND date(l.effective_date) > date(l.repeal_date)
RETURN count(*) as count
"""

QUERY_VERSION_CHAIN_GAPS = """
MATCH (v1:Law)-[:REPLACED_BY*]->(v2:Law)
WHERE toInteger(v2.version) - toInteger(v1.version) > 1
RETURN count(*) as count
"""

QUERY_AMENDMENT_CHAIN_GAPS = """
MATCH (a1:Amendment)-[:AMENDS]->(l:Law)
MATCH (a2:Amendment)-[:AMENDS]->(l)
WHERE a2.amendment_date > a1.amendment_date
AND NOT EXISTS((a1)-[:FOLLOWS]->(a2))
RETURN count(*) as count
"""
