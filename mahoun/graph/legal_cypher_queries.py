"""
Legal Cypher Queries Collection
===============================
Enterprise-grade Cypher queries for legal document validation and retrieval.

This module provides a comprehensive collection of Cypher queries specifically
designed for legal document analysis, supersession detection, and court
hierarchy validation with zero-hallucination guarantees.

Key Features:
- Supersession chain detection and validation
- Court hierarchy enforcement queries
- Legal validity status verification
- Temporal precedence resolution
- Citation network analysis
- Audit trail generation
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryCategory(str, Enum):
    """Categories of legal Cypher queries"""
    SUPERSESSION = "supersession"
    HIERARCHY = "hierarchy"
    VALIDITY = "validity"
    CITATION = "citation"
    TEMPORAL = "temporal"
    AUDIT = "audit"


@dataclass
class CypherQuery:
    """
    Structured Cypher query with metadata
    
    Attributes:
        name: Query identifier
        category: Query category
        description: Query purpose and functionality
        cypher: Cypher query string
        parameters: Expected parameters
        returns: Description of returned data
        complexity: Query complexity (LOW, MEDIUM, HIGH)
        use_cases: Common use cases for this query
    """
    name: str
    category: QueryCategory
    description: str
    cypher: str
    parameters: Dict[str, str]
    returns: str
    complexity: str
    use_cases: List[str]


class LegalCypherQueries:
    """
    Enterprise Legal Cypher Queries Collection
    
    Provides a comprehensive set of validated Cypher queries for legal
    document analysis, supersession detection, and court hierarchy validation.
    
    All queries are designed with:
    - Zero-hallucination guarantees
    - Performance optimization
    - Audit trail compliance
    - Regulatory compliance support
    """
    
    # ========================================================================
    # SUPERSESSION QUERIES
    # ========================================================================
    
    FIND_SUPERSEDED_LAWS = CypherQuery(
        name="find_superseded_laws",
        category=QueryCategory.SUPERSESSION,
        description="Find laws that have been superseded and should not be returned to agents",
        cypher="""
        MATCH (law:Law)-[:SUPERSEDED_BY]->(newer_law:Law)
        WHERE law.id = $law_id
        AND law._deleted IS NULL AND newer_law._deleted IS NULL
        RETURN 
            law.id as superseded_law_id,
            law.name as superseded_law_name,
            newer_law.id as superseding_law_id,
            newer_law.name as superseding_law_name,
            newer_law.effective_date as effective_date,
            EXISTS((law)-[:SUPERSEDED_BY]->()) as is_superseded
        """,
        parameters={
            "law_id": "ID of the law to check for supersession"
        },
        returns="Supersession information including newer law details",
        complexity="LOW",
        use_cases=[
            "Pre-retrieval filtering of superseded laws",
            "Legal validity verification",
            "Temporal precedence resolution"
        ]
    )
    
    FIND_SUPERSESSION_CHAIN = CypherQuery(
        name="find_supersession_chain",
        category=QueryCategory.SUPERSESSION,
        description="Find complete supersession chain for a law (all versions)",
        cypher="""
        MATCH path = (start_law:Law)-[:SUPERSEDED_BY*]->(end_law:Law)
        WHERE start_law.id = $law_id
        AND NOT EXISTS((end_law)-[:SUPERSEDED_BY]->())
        AND NONE(n IN nodes(path) WHERE n._deleted = true)
        RETURN 
            [node in nodes(path) | {
                id: node.id,
                name: node.name,
                effective_date: node.effective_date,
                status: node.status
            }] as supersession_chain,
            length(path) as chain_length,
            end_law.id as current_active_law_id,
            end_law.name as current_active_law_name
        ORDER BY chain_length DESC
        LIMIT 1
        """,
        parameters={
            "law_id": "ID of any law in the supersession chain"
        },
        returns="Complete supersession chain from oldest to newest law",
        complexity="MEDIUM",
        use_cases=[
            "Legal history analysis",
            "Finding current active version of a law",
            "Supersession audit trails"
        ]
    )
    
    VALIDATE_NO_SUPERSESSION = CypherQuery(
        name="validate_no_supersession",
        category=QueryCategory.SUPERSESSION,
        description="Validate that a law has not been superseded before returning to agent",
        cypher="""
        MATCH (law:Law {id: $law_id})
        WHERE law._deleted IS NULL
        OPTIONAL MATCH (law)-[:SUPERSEDED_BY]->(newer_law:Law)
        WHERE newer_law IS NULL OR newer_law._deleted IS NULL
        RETURN 
            law.id as law_id,
            law.name as law_name,
            law.status as status,
            CASE 
                WHEN newer_law IS NULL THEN true 
                ELSE false 
            END as is_valid_for_retrieval,
            newer_law.id as superseded_by_law_id,
            newer_law.name as superseded_by_law_name
        """,
        parameters={
            "law_id": "ID of the law to validate"
        },
        returns="Validation result and superseding law information if applicable",
        complexity="LOW",
        use_cases=[
            "Pre-retrieval validation",
            "Legal document filtering",
            "Zero-hallucination compliance"
        ]
    )
    
    # ========================================================================
    # COURT HIERARCHY QUERIES
    # ========================================================================
    
    RANK_BY_COURT_HIERARCHY = CypherQuery(
        name="rank_by_court_hierarchy",
        category=QueryCategory.HIERARCHY,
        description="Rank legal documents by court hierarchy (Supreme > Appeals > First Instance)",
        cypher="""
        MATCH (verdict:Verdict)-[:DECIDED_BY]->(court:Court)
        WHERE verdict.case_type CONTAINS $case_type
        AND verdict._deleted IS NULL
        RETURN 
            verdict.id as verdict_id,
            verdict.content as content,
            court.name as court_name,
            court.level as court_level,
            CASE court.level
                WHEN 'دیوان عالی' THEN 1
                WHEN 'تجدیدنظر' THEN 2
                WHEN 'بدوی' THEN 3
                WHEN 'تخصصی' THEN 4
                WHEN 'اداری' THEN 5
                ELSE 6
            END as court_rank,
            verdict.authority_score as authority_score
        ORDER BY court_rank ASC, authority_score DESC
        LIMIT $limit
        """,
        parameters={
            "case_type": "Type of case to search for",
            "limit": "Maximum number of results to return"
        },
        returns="Verdicts ranked by court hierarchy and authority score",
        complexity="MEDIUM",
        use_cases=[
            "Legal precedent ranking",
            "Authority-based document retrieval",
            "Court hierarchy enforcement"
        ]
    )
    
    FIND_HIGHER_COURT_PRECEDENTS = CypherQuery(
        name="find_higher_court_precedents",
        category=QueryCategory.HIERARCHY,
        description="Find precedents from higher courts that override lower court decisions",
        cypher="""
        MATCH (lower_verdict:Verdict)-[:DECIDED_BY]->(lower_court:Court),
              (higher_verdict:Verdict)-[:DECIDED_BY]->(higher_court:Court)
        WHERE lower_verdict.case_number = $case_number
        AND higher_court.level IN ['دیوان عالی', 'تجدیدنظر']
        AND lower_court.level IN ['بدوی', 'تخصصی']
        AND higher_verdict.case_type = lower_verdict.case_type
        AND lower_verdict._deleted IS NULL AND higher_verdict._deleted IS NULL
        OPTIONAL MATCH (higher_verdict)-[override:OVERRULES]->(lower_verdict)
        RETURN 
            higher_verdict.id as higher_court_verdict_id,
            higher_verdict.content as higher_court_content,
            higher_court.name as higher_court_name,
            higher_court.level as higher_court_level,
            lower_verdict.id as lower_court_verdict_id,
            lower_court.name as lower_court_name,
            override IS NOT NULL as explicitly_overrules
        ORDER BY 
            CASE higher_court.level
                WHEN 'دیوان عالی' THEN 1
                WHEN 'تجدیدنظر' THEN 2
            END ASC
        """,
        parameters={
            "case_number": "Case number to find higher court precedents for"
        },
        returns="Higher court precedents that may override lower court decisions",
        complexity="HIGH",
        use_cases=[
            "Precedent hierarchy validation",
            "Legal contradiction detection",
            "Authority-based filtering"
        ]
    )
    
    # ========================================================================
    # VALIDITY STATUS QUERIES
    # ========================================================================
    
    FILTER_ACTIVE_DOCUMENTS = CypherQuery(
        name="filter_active_documents",
        category=QueryCategory.VALIDITY,
        description="Filter documents to return only active (non-repealed) legal documents",
        cypher="""
        MATCH (doc)
        WHERE doc:Law OR doc:Article OR doc:Verdict
        AND doc.status = 'active'
        AND doc._deleted IS NULL
        AND NOT EXISTS((doc)-[:SUPERSEDED_BY]->())
        AND doc.content CONTAINS $search_term
        RETURN 
            doc.id as document_id,
            doc.content as content,
            labels(doc)[0] as document_type,
            doc.status as status,
            doc.effective_date as effective_date,
            doc.authority_score as authority_score
        ORDER BY doc.authority_score DESC
        LIMIT $limit
        """,
        parameters={
            "search_term": "Term to search for in document content",
            "limit": "Maximum number of results to return"
        },
        returns="Only active, non-superseded legal documents",
        complexity="MEDIUM",
        use_cases=[
            "Legal document retrieval",
            "Active law filtering",
            "Zero-hallucination compliance"
        ]
    )
    
    CHECK_DOCUMENT_VALIDITY = CypherQuery(
        name="check_document_validity",
        category=QueryCategory.VALIDITY,
        description="Comprehensive validity check for a legal document",
        cypher="""
        MATCH (doc {id: $document_id})
        OPTIONAL MATCH (doc)-[:SUPERSEDED_BY]->(newer_doc)
        OPTIONAL MATCH (doc)-[:REPEALED_BY]->(repealing_doc)
        RETURN 
            doc.id as document_id,
            doc.status as current_status,
            doc.effective_date as effective_date,
            doc.expiry_date as expiry_date,
            doc._deleted IS NOT NULL as is_tombstoned,
            newer_doc.id as superseded_by_id,
            newer_doc.effective_date as superseded_date,
            repealing_doc.id as repealed_by_id,
            repealing_doc.effective_date as repeal_date,
            CASE 
                WHEN doc._deleted IS NOT NULL THEN false
                WHEN doc.status = 'repealed' THEN false
                WHEN newer_doc IS NOT NULL THEN false
                WHEN repealing_doc IS NOT NULL THEN false
                WHEN doc.expiry_date IS NOT NULL AND date(doc.expiry_date) < date() THEN false
                ELSE true
            END as is_currently_valid
        """,
        parameters={
            "document_id": "ID of the document to check"
        },
        returns="Comprehensive validity status with reasons for invalidity",
        complexity="MEDIUM",
        use_cases=[
            "Document validity verification",
            "Legal compliance checking",
            "Audit trail generation"
        ]
    )
    
    # ========================================================================
    # CITATION NETWORK QUERIES
    # ========================================================================
    
    FIND_CITATION_NETWORK = CypherQuery(
        name="find_citation_network",
        category=QueryCategory.CITATION,
        description="Find citation network around a legal document",
        cypher="""
        MATCH (center_doc {id: $document_id})
        WHERE center_doc._deleted IS NULL
        OPTIONAL MATCH (center_doc)-[:CITES]->(cited_doc)
        WHERE cited_doc IS NULL OR cited_doc._deleted IS NULL
        OPTIONAL MATCH (citing_doc)-[:CITES]->(center_doc)
        WHERE citing_doc IS NULL OR citing_doc._deleted IS NULL
        RETURN 
            center_doc.id as center_document_id,
            collect(DISTINCT {
                id: cited_doc.id,
                name: cited_doc.name,
                type: labels(cited_doc)[0],
                authority_score: cited_doc.authority_score
            }) as documents_cited_by_center,
            collect(DISTINCT {
                id: citing_doc.id,
                name: citing_doc.name,
                type: labels(citing_doc)[0],
                authority_score: citing_doc.authority_score
            }) as documents_citing_center,
            size(collect(DISTINCT cited_doc)) as outgoing_citations,
            size(collect(DISTINCT citing_doc)) as incoming_citations
        """,
        parameters={
            "document_id": "ID of the central document"
        },
        returns="Citation network with incoming and outgoing citations",
        complexity="MEDIUM",
        use_cases=[
            "Citation analysis",
            "Authority score calculation",
            "Legal network analysis"
        ]
    )
    
    CALCULATE_AUTHORITY_SCORE = CypherQuery(
        name="calculate_authority_score",
        category=QueryCategory.CITATION,
        description="Calculate authority score based on citation patterns and court hierarchy",
        cypher="""
        MATCH (doc {id: $document_id})
        WHERE doc._deleted IS NULL
        OPTIONAL MATCH (citing_doc)-[:CITES]->(doc)
        WHERE citing_doc IS NULL OR citing_doc._deleted IS NULL
        OPTIONAL MATCH (citing_doc)-[:DECIDED_BY]->(citing_court:Court)
        WITH doc, 
             count(citing_doc) as total_citations,
             collect(citing_court.level) as citing_court_levels
        RETURN 
            doc.id as document_id,
            total_citations,
            citing_court_levels,
            size([level IN citing_court_levels WHERE level = 'دیوان عالی']) as supreme_court_citations,
            size([level IN citing_court_levels WHERE level = 'تجدیدنظر']) as appeals_court_citations,
            size([level IN citing_court_levels WHERE level = 'بدوی']) as first_instance_citations,
            CASE 
                WHEN total_citations = 0 THEN 0.0
                ELSE (
                    size([level IN citing_court_levels WHERE level = 'دیوان عالی']) * 1.0 +
                    size([level IN citing_court_levels WHERE level = 'تجدیدنظر']) * 0.7 +
                    size([level IN citing_court_levels WHERE level = 'بدوی']) * 0.4
                ) / total_citations
            END as calculated_authority_score
        """,
        parameters={
            "document_id": "ID of the document to calculate authority score for"
        },
        returns="Calculated authority score based on citation patterns",
        complexity="HIGH",
        use_cases=[
            "Authority score calculation",
            "Document ranking",
            "Citation-based filtering"
        ]
    )
    
    # ========================================================================
    # TEMPORAL PRECEDENCE QUERIES
    # ========================================================================
    
    RESOLVE_TEMPORAL_CONFLICTS = CypherQuery(
        name="resolve_temporal_conflicts",
        category=QueryCategory.TEMPORAL,
        description="Resolve conflicts between documents using temporal precedence (newer wins)",
        cypher="""
        MATCH (doc1), (doc2)
        WHERE doc1.id = $document_id_1 AND doc2.id = $document_id_2
        AND doc1._deleted IS NULL AND doc2._deleted IS NULL
        AND (doc1.legal_topic = doc2.legal_topic OR doc1.article_number = doc2.article_number)
        RETURN 
            doc1.id as document_1_id,
            doc1.effective_date as document_1_date,
            doc2.id as document_2_id,
            doc2.effective_date as document_2_date,
            CASE 
                WHEN date(doc1.effective_date) > date(doc2.effective_date) THEN doc1.id
                WHEN date(doc2.effective_date) > date(doc1.effective_date) THEN doc2.id
                ELSE null
            END as temporally_precedent_document,
            CASE 
                WHEN date(doc1.effective_date) > date(doc2.effective_date) THEN 'document_1_newer'
                WHEN date(doc2.effective_date) > date(doc1.effective_date) THEN 'document_2_newer'
                ELSE 'same_date'
            END as temporal_relationship
        """,
        parameters={
            "document_id_1": "ID of first document",
            "document_id_2": "ID of second document"
        },
        returns="Temporal precedence resolution between two documents",
        complexity="MEDIUM",
        use_cases=[
            "Conflict resolution",
            "Temporal precedence enforcement",
            "Legal contradiction handling"
        ]
    )
    
    # ========================================================================
    # AUDIT TRAIL QUERIES
    # ========================================================================
    
    GENERATE_RETRIEVAL_AUDIT_TRAIL = CypherQuery(
        name="generate_retrieval_audit_trail",
        category=QueryCategory.AUDIT,
        description="Generate complete audit trail for document retrieval decision",
        cypher="""
        MATCH (doc {id: $document_id})
        OPTIONAL MATCH (doc)-[:SUPERSEDED_BY]->(newer_doc)
        OPTIONAL MATCH (doc)-[:DECIDED_BY]->(court:Court)
        OPTIONAL MATCH (citing_doc)-[:CITES]->(doc)
        RETURN 
            doc.id as document_id,
            doc.name as document_name,
            labels(doc)[0] as document_type,
            doc.status as status,
            doc.effective_date as effective_date,
            court.name as deciding_court,
            court.level as court_level,
            newer_doc.id as superseded_by,
            count(citing_doc) as citation_count,
            doc.authority_score as authority_score,
            CASE 
                WHEN doc._deleted IS NOT NULL THEN 'EXCLUDED: Document is soft-deleted (tombstoned)'
                WHEN doc.status = 'repealed' THEN 'EXCLUDED: Document is repealed'
                WHEN newer_doc IS NOT NULL THEN 'EXCLUDED: Document is superseded by ' + newer_doc.id
                WHEN doc.authority_score < 0.5 THEN 'WARNING: Low authority score'
                ELSE 'INCLUDED: Document meets all criteria'
            END as retrieval_decision_reason,
            timestamp() as audit_timestamp
        """,
        parameters={
            "document_id": "ID of the document being audited"
        },
        returns="Complete audit trail for retrieval decision",
        complexity="HIGH",
        use_cases=[
            "Regulatory compliance",
            "Audit trail generation",
            "Decision transparency"
        ]
    )
    
    @classmethod
    def get_query(cls, query_name: str) -> Optional[CypherQuery]:
        """
        Get a specific query by name
        
        Args:
            query_name: Name of the query to retrieve
            
        Returns:
            CypherQuery object or None if not found
        """
        # Get all class attributes that are CypherQuery instances
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr_value = getattr(cls, attr_name)
                if isinstance(attr_value, CypherQuery) and attr_value.name == query_name:
                    return attr_value
        return None
    
    @classmethod
    def get_queries_by_category(cls, category: QueryCategory) -> List[CypherQuery]:
        """
        Get all queries in a specific category
        
        Args:
            category: Query category to filter by
            
        Returns:
            List of CypherQuery objects in the category
        """
        queries = []
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr_value = getattr(cls, attr_name)
                if isinstance(attr_value, CypherQuery) and attr_value.category == category:
                    queries.append(attr_value)
        return queries
    
    @classmethod
    def list_all_queries(cls) -> List[CypherQuery]:
        """
        Get all available queries
        
        Returns:
            List of all CypherQuery objects
        """
        queries = []
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr_value = getattr(cls, attr_name)
                if isinstance(attr_value, CypherQuery):
                    queries.append(attr_value)
        return queries
    
    # ========================================================================
    # CUSTOM MIGRATION QUERIES
    # ========================================================================
    
    UPDATE_DOCUMENT_METADATA = CypherQuery(
        name="update_document_metadata",
        category=QueryCategory.VALIDITY,
        description="Update document metadata with legal-aware fields",
        cypher="""
        MATCH (doc {id: $doc_id})
        WHERE doc._deleted IS NULL
        SET doc.court_rank = $court_rank,
            doc.statute_status = $statute_status,
            doc.authority_score = $authority_score,
            doc.date_jalali = $date_jalali,
            doc.citation_count = $citation_count,
            doc.cited_by_higher_courts = $cited_by_higher_courts,
            doc.legal_domain = $legal_domain,
            doc.updated_at = datetime()
        RETURN doc.id as updated_doc_id, doc.updated_at as update_timestamp
        """,
        parameters={
            "doc_id": "Document identifier to update",
            "court_rank": "Court hierarchy rank (1-5)",
            "statute_status": "Legal validity status",
            "authority_score": "Authority score (0.0-1.0)",
            "date_jalali": "Persian calendar date",
            "citation_count": "Number of citations",
            "cited_by_higher_courts": "Boolean for higher court citations",
            "legal_domain": "Legal domain classification"
        },
        returns="Updated document ID and timestamp",
        complexity="LOW",
        use_cases=[
            "Legal metadata migration",
            "Document metadata updates",
            "Schema enhancement"
        ]
    )
    
    CREATE_LEGAL_RELATIONSHIPS = CypherQuery(
        name="create_legal_relationships",
        category=QueryCategory.SUPERSESSION,
        description="Create legal relationships between documents",
        cypher="""
        MATCH (source {id: $source_id}), (target {id: $target_id})
        WHERE source._deleted IS NULL AND target._deleted IS NULL
        MERGE (source)-[r:LEGAL_RELATIONSHIP {type: $relationship_type}]->(target)
        SET r.status = $status,
            r.effective_date = $effective_date,
            r.confidence = $confidence,
            r.created_at = datetime()
        RETURN r.type as relationship_type, r.status as status
        """,
        parameters={
            "source_id": "Source document ID",
            "target_id": "Target document ID",
            "relationship_type": "Type of legal relationship",
            "status": "Relationship status (active, inactive)",
            "effective_date": "Date when relationship became effective",
            "confidence": "Confidence score for relationship"
        },
        returns="Created relationship type and status",
        complexity="MEDIUM",
        use_cases=[
            "Creating supersession relationships",
            "Establishing citation links",
            "Building legal hierarchies"
        ]
    )
    
    VALIDATE_CROSS_SYSTEM_SYNC = CypherQuery(
        name="validate_cross_system_sync",
        category=QueryCategory.AUDIT,
        description="Validate synchronization between vector and graph stores",
        cypher="""
        MATCH (doc)
        WHERE doc.id IS NOT NULL
        RETURN 
            doc.id as document_id,
            doc._deleted IS NOT NULL as is_tombstoned,
            labels(doc) as node_labels,
            doc.court_rank as court_rank,
            doc.statute_status as statute_status,
            doc.authority_score as authority_score,
            doc.updated_at as last_updated,
            EXISTS((doc)-[:SUPERSEDED_BY]->()) as has_supersession,
            size((doc)<-[:CITES]-()) as incoming_citations
        ORDER BY doc.updated_at DESC
        LIMIT $limit
        """,
        parameters={
            "limit": "Maximum number of documents to validate"
        },
        returns="Document metadata for cross-system validation",
        complexity="MEDIUM",
        use_cases=[
            "Cross-system synchronization validation",
            "Data consistency checks",
            "Migration verification"
        ]
    )


# ============================================================================
# Query Execution Helper
# ============================================================================

class LegalQueryExecutor:
    """
    Helper class for executing legal Cypher queries with validation and logging.
    
    Constructor Injection Contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``connection`` MUST be a ``Neo4jConnection`` instance obtained via
    ``get_connection()`` (the authorised singleton factory). Bootstrap is
    the sole wiring authority — callers must never pass a raw driver.
    
    Pre-conditions
    ~~~~~~~~~~~~~~
    * ``connection`` is not None and is a live ``Neo4jConnection``.
    
    Post-conditions
    ~~~~~~~~~~~~~~~
    * All read-only queries use ``connection.execute_query()`` for optimal routing.
    * All mutation queries use ``connection.governed_session()`` with full audit trail.
    * Zero raw ``driver.session()`` calls exist in this class.
    """
    
    def __init__(self, connection: 'Neo4jConnection'):
        """
        Initialize query executor with injected Neo4jConnection.
        
        Args:
            connection: Neo4jConnection instance (from get_connection())
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        
        if not isinstance(connection, Neo4jConnection):
            raise TypeError(
                f"connection must be Neo4jConnection instance, got {type(connection).__name__}"
            )
        
        self.connection = connection
        self.query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "queries_by_category": {}
        }
    
    async def execute_legal_query(
        self,
        query_name: str,
        parameters: Dict[str, Any],
        timeout: int = 30
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Execute a legal query with validation and audit logging.
        
        Routing Logic
        ~~~~~~~~~~~~~
        * Read-only queries → ``connection.execute_query()`` (optimal read path)
        * Mutation queries → ``connection.governed_session()`` (full audit trail)
        
        Args:
            query_name: Name of the query to execute
            parameters: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Tuple of (results, metadata)
        """
        import uuid
        
        query = LegalCypherQueries.get_query(query_name)
        if not query:
            raise ValueError(f"Query '{query_name}' not found")
        
        self.query_stats["total_queries"] += 1
        category_stats = self.query_stats["queries_by_category"]
        category_stats[query.category.value] = category_stats.get(query.category.value, 0) + 1
        
        try:
            # Detect if query is mutation or read-only
            is_mutation = self._is_mutation_query(query.cypher)
            
            if is_mutation:
                # Mutation path: use governed_session with full audit trail
                correlation_id = str(uuid.uuid4())
                with self.connection.governed_session(
                    correlation_id=correlation_id,
                    actor_id="legal-query-executor",
                    operation_type="legal_mutation"
                ) as session:
                    result = session.run(query.cypher, parameters)
                    records = [record.data() for record in result]
            else:
                # Read-only path: use execute_query for optimal routing
                records = self.connection.execute_query(query.cypher, parameters)
            
            self.query_stats["successful_queries"] += 1
            
            # Generate metadata
            metadata = {
                "query_name": query_name,
                "query_category": query.category.value,
                "query_complexity": query.complexity,
                "parameters_used": parameters,
                "results_count": len(records),
                "execution_status": "success",
                "query_type": "mutation" if is_mutation else "read"
            }
            
            logger.info(
                f"Legal query '{query_name}' executed successfully: "
                f"{len(records)} results (type: {'mutation' if is_mutation else 'read'})"
            )
            
            return records, metadata
            
        except Exception as e:
            self.query_stats["failed_queries"] += 1
            
            metadata = {
                "query_name": query_name,
                "query_category": query.category.value,
                "parameters_used": parameters,
                "execution_status": "failed",
                "error": str(e)
            }
            
            logger.error(f"Legal query '{query_name}' failed: {e}")
            raise
    
    def _is_mutation_query(self, cypher: str) -> bool:
        """
        Detect if a Cypher query is a mutation (write) or read-only.
        
        Mutation keywords: CREATE, MERGE, SET, DELETE, REMOVE, DETACH DELETE
        Read-only keywords: MATCH, RETURN, WITH, UNWIND (without mutations)
        
        Returns:
            True if query contains mutation keywords, False otherwise
        """
        cypher_upper = cypher.upper()
        mutation_keywords = [
            'CREATE ', 'MERGE ', 'SET ', 'DELETE ', 'REMOVE ', 'DETACH DELETE'
        ]
        return any(keyword in cypher_upper for keyword in mutation_keywords)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query execution statistics"""
        return self.query_stats.copy()