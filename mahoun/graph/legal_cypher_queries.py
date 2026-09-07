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
from dataclasses import dataclass, field
from enum import Enum
import logging

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

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
class ParameterSpec:
    """Validation spec for a single Cypher parameter.

    Each parameter on a CypherQuery can carry one of these specs;
    ``LegalQueryExecutor.execute_legal_query`` runs them through the
    OntologyEnforcer (or a built-in primitive check) before the query
    is sent to Neo4j. A parameter with no spec is passed through
    unchanged.

    The "kind" field maps to a specific validator:

    - ``"deontic_operator"`` → ``OntologyEnforcer.validate_deontic_operator``
    - ``"legal_level"``      → ``OntologyEnforcer.validate_legal_level``
    - ``"conflict_resolution"`` →
      ``OntologyEnforcer.validate_conflict_resolution``
    - ``"legal_force"``      → ``OntologyEnforcer.validate_legal_force``
    - ``"binding_scope"``    → ``OntologyEnforcer.validate_binding_scope``
    - ``"norm_status"``      → ``OntologyEnforcer.validate_norm_status``
    - ``"decision_type"``    → ``OntologyEnforcer.validate_decision_type``
    - ``"temporal_relation"``→ ``OntologyEnforcer.validate_temporal_relationship``
    - ``"iso8601_date"``     → ``OntologyEnforcer.validate_temporal_range``
      applied as a single value (valid_from only)
     - ``"non_empty_string"``→ required string; non-empty and
       non-whitespace (reuse for string identifiers like norm_id,
       base_law_id, etc.)
     - ``"iso8601_required"``→ required string; non-empty, non-
       whitespace, and a valid ISO 8601 date/datetime

    A spec with ``required=False`` allows None.
    """

    name: str
    kind: str
    required: bool = True
    description: str = ""


@dataclass
class CypherQuery:
    """
    Structured Cypher query with metadata
    
    Attributes:
        name: Query identifier
        category: Query category
        description: Query purpose and functionality
        cypher: Cypher query string
        parameters: Expected parameters (legacy text spec)
        param_specs: Per-parameter validation spec for the executor.
            When non-empty, the executor MUST run each spec through
            the appropriate validator before sending the query to
            Neo4j. A typo in an enum value, a malformed ISO 8601
            date, or a missing required field is caught at the
            application boundary and reported as a
            GovernanceViolationError, NOT as a silent empty result
            set.
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
    param_specs: List[ParameterSpec] = field(default_factory=list)


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
        OPTIONAL MATCH (law)-[:SUPERSEDED_BY]->(newer_law:Law)
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
            newer_doc.id as superseded_by_id,
            newer_doc.effective_date as superseded_date,
            repealing_doc.id as repealed_by_id,
            repealing_doc.effective_date as repeal_date,
            CASE 
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
        OPTIONAL MATCH (center_doc)-[:CITES]->(cited_doc)
        OPTIONAL MATCH (citing_doc)-[:CITES]->(center_doc)
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
        OPTIONAL MATCH (citing_doc)-[:CITES]->(doc)
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

    # ========================================================================
    # HIERARCHY (LegalLevel) QUERIES — data-driven, uses LegalLevel enum
    # Higher rank = more authoritative. The CASE ladder below mirrors the
    # rank table in OntologyEnforcer.validate_hierarchy_precedence().
    # ========================================================================

    FIND_NORMS_BY_HIERARCHY_LEVEL = CypherQuery(
        name="find_norms_by_hierarchy_level",
        category=QueryCategory.HIERARCHY,
        description=(
            "Find all norms at a given LegalLevel (or higher) so callers can "
            "resolve lex-superior conflicts. Rank ordering is canonical: "
            "CONSTITUTIONAL > ORDINARY_LAW > DECREE > REGULATION > BYLAW > "
            "CIRCULAR > JUDICIAL_PRECEDENT > DOCTRINE."
        ),
        cypher="""
        MATCH (n:Norm)
        WHERE n.legal_level IN $legal_levels
        AND (n.valid_from IS NULL OR n.valid_from <= date($as_of))
        AND (n.valid_until IS NULL OR n.valid_until >= date($as_of))
        RETURN
            n.id as norm_id,
            n.deontic_operator as deontic_operator,
            n.action as action,
            n.legal_level as legal_level,
            n.valid_from as valid_from,
            n.valid_until as valid_until,
            n.authority_score as authority_score,
            CASE n.legal_level
                WHEN 'CONSTITUTIONAL' THEN 8
                WHEN 'ORDINARY_LAW' THEN 7
                WHEN 'DECREE' THEN 6
                WHEN 'REGULATION' THEN 5
                WHEN 'BYLAW' THEN 4
                WHEN 'CIRCULAR' THEN 3
                WHEN 'JUDICIAL_PRECEDENT' THEN 2
                WHEN 'DOCTRINE' THEN 1
                ELSE 0
            END as hierarchy_rank
        ORDER BY hierarchy_rank DESC, n.authority_score DESC
        """,
        parameters={
            "legal_levels": "List of LegalLevel values to include (caller pre-validates via OntologyEnforcer.validate_legal_level)",
            "as_of": "Point-in-time ISO 8601 date; only norms in force at this date are returned",
        },
        param_specs=[
            ParameterSpec(
                name="legal_levels",
                kind="list_of_legal_level",
                required=True,
                description="Each entry must be a valid LegalLevel value",
            ),
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time date, ISO 8601",
            ),
        ],
        returns="Norms filtered by legal level, ordered by hierarchy rank DESC, then authority_score DESC",
        complexity="MEDIUM",
        use_cases=[
            "Lex-superior conflict resolution",
            "Authority-based norm filtering",
            "Hierarchy-aware retrieval",
        ],
    )

    RESOLVE_LEX_SUPERIOR_CONFLICT = CypherQuery(
        name="resolve_lex_superior_conflict",
        category=QueryCategory.HIERARCHY,
        description=(
            "Given two conflicting norms, pick the winner using the "
            "CONSTITUTIONAL > ORDINARY_LAW > ... > DOCTRINE ladder. "
            "Returns the winning norm and its rank. Ties (same level) "
            "are explicitly marked as LEX_SUPERIOR_TIE — the caller MUST "
            "escalate to RESOLVED_LEX_POSTERIOR or JUDICIAL_AUTHORITY."
        ),
        cypher="""
        MATCH (a:Norm {id: $norm_a_id}), (b:Norm {id: $norm_b_id})
        WITH a, b,
             CASE a.legal_level
                 WHEN 'CONSTITUTIONAL' THEN 8
                 WHEN 'ORDINARY_LAW' THEN 7
                 WHEN 'DECREE' THEN 6
                 WHEN 'REGULATION' THEN 5
                 WHEN 'BYLAW' THEN 4
                 WHEN 'CIRCULAR' THEN 3
                 WHEN 'JUDICIAL_PRECEDENT' THEN 2
                 WHEN 'DOCTRINE' THEN 1
                 ELSE 0
             END as a_rank,
             CASE b.legal_level
                 WHEN 'CONSTITUTIONAL' THEN 8
                 WHEN 'ORDINARY_LAW' THEN 7
                 WHEN 'DECREE' THEN 6
                 WHEN 'REGULATION' THEN 5
                 WHEN 'BYLAW' THEN 4
                 WHEN 'CIRCULAR' THEN 3
                 WHEN 'JUDICIAL_PRECEDENT' THEN 2
                 WHEN 'DOCTRINE' THEN 1
                 ELSE 0
             END as b_rank
        RETURN
            a.id as norm_a_id,
            a.legal_level as norm_a_level,
            a_rank,
            b.id as norm_b_id,
            b.legal_level as norm_b_level,
            b_rank,
            CASE
                WHEN a_rank > b_rank THEN a.id
                WHEN b_rank > a_rank THEN b.id
                ELSE null
            END as winner_id,
            CASE
                WHEN a_rank > b_rank THEN a.legal_level
                WHEN b_rank > a_rank THEN b.legal_level
                ELSE 'LEX_SUPERIOR_TIE'
            END as winner_level,
            a_rank - b_rank as rank_delta
        """,
        parameters={
            "norm_a_id": "ID of the first norm in the conflict",
            "norm_b_id": "ID of the second norm in the conflict",
        },
        param_specs=[
            ParameterSpec(
                name="norm_a_id",
                kind="non_empty_string",
                required=True,
                description="Must be a non-empty norm id",
            ),
            ParameterSpec(
                name="norm_b_id",
                kind="non_empty_string",
                required=True,
                description="Must be a non-empty norm id",
            ),
        ],
        returns="Winner norm id, its legal level, and the rank delta. Ties surface as null winner_id and LEX_SUPERIOR_TIE.",
        complexity="LOW",
        use_cases=[
            "Lex-superior conflict resolution",
            "Norm conflict adjudication",
            "Hierarchy-based precedence",
        ],
    )

    # ========================================================================
    # DEONTIC QUERIES
    # ========================================================================

    FIND_NORMS_BY_DEONTIC_OPERATOR = CypherQuery(
        name="find_norms_by_deontic_operator",
        category=QueryCategory.HIERARCHY,
        description=(
            "Find all norms with a given deontic operator (OBLIGATION, "
            "PERMISSION, or PROHIBITION), filtered by optional "
            "legal_level and bounded by the as_of temporal window."
        ),
        cypher="""
        MATCH (n:Norm)
        WHERE n.deontic_operator = $deontic_operator
        AND ($legal_level IS NULL OR n.legal_level = $legal_level)
        AND (n.valid_from IS NULL OR n.valid_from <= date($as_of))
        AND (n.valid_until IS NULL OR n.valid_until >= date($as_of))
        RETURN
            n.id as norm_id,
            n.deontic_operator as deontic_operator,
            n.action as action,
            n.legal_level as legal_level,
            n.valid_from as valid_from,
            n.valid_until as valid_until,
            n.sanction as sanction,
            n.exception as exception
        ORDER BY
            CASE n.legal_level
                WHEN 'CONSTITUTIONAL' THEN 8
                WHEN 'ORDINARY_LAW' THEN 7
                WHEN 'DECREE' THEN 6
                WHEN 'REGULATION' THEN 5
                WHEN 'BYLAW' THEN 4
                WHEN 'CIRCULAR' THEN 3
                WHEN 'JUDICIAL_PRECEDENT' THEN 2
                WHEN 'DOCTRINE' THEN 1
                ELSE 0
            END DESC,
            n.authority_score DESC
        """,
        parameters={
            "deontic_operator": "OBLIGATION | PERMISSION | PROHIBITION",
            "legal_level": "Optional LegalLevel filter (pass null to skip)",
            "as_of": "Point-in-time ISO 8601 date",
        },
        param_specs=[
            ParameterSpec(
                name="deontic_operator",
                kind="deontic_operator",
                required=True,
                description="Must be OBLIGATION, PERMISSION, or PROHIBITION",
            ),
            ParameterSpec(
                name="legal_level",
                kind="legal_level",
                required=False,
                description="Optional; pass None to skip filter",
            ),
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time ISO 8601 date",
            ),
        ],
        returns="Norms matching the deontic operator, ordered by hierarchy rank and authority",
        complexity="MEDIUM",
        use_cases=[
            "Duty extraction",
            "Permission enumeration",
            "Prohibition surface",
        ],
    )

    DETECT_DEONTIC_CONFLICT = CypherQuery(
        name="detect_deontic_conflict",
        category=QueryCategory.HIERARCHY,
        description=(
            "Find all norm pairs whose deontic operators are mutually "
            "contradictory AND whose subjects/actions overlap on a shared "
            "legal_topic. Returns pairs that must be routed through the "
            "norm-conflict resolution pipeline."
        ),
        cypher="""
        MATCH (a:Norm), (b:Norm)
        WHERE a.id < b.id
        AND (
            (a.deontic_operator = 'OBLIGATION' AND b.deontic_operator = 'PROHIBITION')
            OR (a.deontic_operator = 'PROHIBITION' AND b.deontic_operator = 'OBLIGATION')
            OR (a.deontic_operator = 'OBLIGATION' AND b.deontic_operator = 'PERMISSION')
            OR (a.deontic_operator = 'PERMISSION' AND b.deontic_operator = 'OBLIGATION')
        )
        AND (a.valid_from IS NULL OR a.valid_from <= date($as_of))
        AND (a.valid_until IS NULL OR a.valid_until >= date($as_of))
        AND (b.valid_from IS NULL OR b.valid_from <= date($as_of))
        AND (b.valid_until IS NULL OR b.valid_until >= date($as_of))
        RETURN
            a.id as norm_a_id,
            a.deontic_operator as norm_a_operator,
            a.action as norm_a_action,
            a.legal_level as norm_a_level,
            b.id as norm_b_id,
            b.deontic_operator as norm_b_operator,
            b.action as norm_b_action,
            b.legal_level as norm_b_level,
            CASE
                WHEN (a.deontic_operator = 'OBLIGATION' AND b.deontic_operator = 'PROHIBITION')
                  OR (a.deontic_operator = 'PROHIBITION' AND b.deontic_operator = 'OBLIGATION')
                THEN 'OBLIGATION_VS_PROHIBITION'
                ELSE 'OBLIGATION_VS_PERMISSION'
            END as conflict_type
        """,
        parameters={
            "as_of": "Point-in-time ISO 8601 date",
        },
        param_specs=[
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time ISO 8601 date",
            ),
        ],
        returns="Pairs of deontically-conflicting norms with conflict type",
        complexity="HIGH",
        use_cases=[
            "Norm conflict detection",
            "Contradiction auditing",
            "Pre-resolution surfacing",
        ],
    )

    # ========================================================================
    # TEMPORAL QUERIES (version-aware, complements TemporalQueryService)
    # ========================================================================

    FIND_LAWS_IN_FORCE_AT = CypherQuery(
        name="find_laws_in_force_at",
        category=QueryCategory.TEMPORAL,
        description=(
            "Return all Law nodes that were in force at the given "
            "as_of date. A law is in force iff (entry_into_force_date "
            "IS NULL OR entry_into_force_date <= as_of) AND no other "
            "law claims SUPERSEDES over it."
        ),
        cypher="""
        MATCH (l:Law)
        WHERE (l.entry_into_force_date IS NULL OR l.entry_into_force_date <= date($as_of))
        AND NOT EXISTS((l)<-[:SUPERSEDES]-(:Law))
        AND ($legal_level IS NULL OR l.legal_level = $legal_level)
        RETURN
            l.id as law_id,
            l.name as law_name,
            l.legal_level as legal_level,
            l.entry_into_force_date as entry_into_force_date,
            l.publication_date as publication_date
        ORDER BY l.legal_level ASC, l.entry_into_force_date ASC
        """,
        parameters={
            "as_of": "Point-in-time ISO 8601 date",
            "legal_level": "Optional LegalLevel filter (null to skip)",
        },
        param_specs=[
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time ISO 8601 date",
            ),
            ParameterSpec(
                name="legal_level",
                kind="legal_level",
                required=False,
                description="Optional; pass None to skip filter",
            ),
        ],
        returns="Laws in force at as_of, with hierarchy ordering",
        complexity="MEDIUM",
        use_cases=[
            "Point-in-time retrieval",
            "Historical state reconstruction",
            "Active-law filtering at a given date",
        ],
    )

    FIND_LATEST_VERSION_OF_LAW = CypherQuery(
        name="find_latest_version_of_law",
        category=QueryCategory.TEMPORAL,
        description=(
            "Return the latest LegalVersion of a given base law. The "
            "version with the highest version_number wins."
        ),
        cypher="""
        MATCH (lv:LegalVersion)
        WHERE lv.base_law_id = $base_law_id
        WITH lv
        ORDER BY lv.version_number DESC
        LIMIT 1
        RETURN
            lv.id as version_id,
            lv.base_law_id as base_law_id,
            lv.version_number as version_number,
            lv.content as content,
            lv.valid_from as valid_from,
            lv.valid_until as valid_until,
            lv.temporal_relation as temporal_relation,
            lv.status as status
        """,
        parameters={
            "base_law_id": "Base law id (the Law.node.id, not the version id)",
        },
        param_specs=[
            ParameterSpec(
                name="base_law_id",
                kind="non_empty_string",
                required=True,
                description="Base law id (Law.node.id)",
            ),
        ],
        returns="The single latest LegalVersion, or no rows if none exist",
        complexity="LOW",
        use_cases=[
            "Head-of-chain retrieval",
            "Most-recent version access",
            "Bitemporal current-state queries",
        ],
    )

    FIND_VERSIONS_EFFECTIVE_AT = CypherQuery(
        name="find_versions_effective_at",
        category=QueryCategory.TEMPORAL,
        description=(
            "Return all LegalVersion nodes whose valid_from <= as_of "
            "AND (valid_until IS NULL OR valid_until >= as_of). This is "
            "the version-aware counterpart of point-in-time law "
            "retrieval. There SHOULD be at most one such version per "
            "base_law_id / base_article_id; the query surfaces all and "
            "the caller enforces uniqueness via the temporal ontology."
        ),
        cypher="""
        MATCH (lv:LegalVersion)
        WHERE lv.base_law_id IS NOT NULL
        AND lv.valid_from <= date($as_of)
        AND (lv.valid_until IS NULL OR lv.valid_until >= date($as_of))
        RETURN
            lv.id as version_id,
            lv.base_law_id as base_law_id,
            lv.base_article_id as base_article_id,
            lv.version_number as version_number,
            lv.content as content,
            lv.valid_from as valid_from,
            lv.valid_until as valid_until,
            lv.temporal_relation as temporal_relation
        ORDER BY lv.base_law_id ASC, lv.version_number DESC
        """,
        parameters={
            "as_of": "Point-in-time ISO 8601 date",
        },
        param_specs=[
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time ISO 8601 date",
            ),
        ],
        returns="All LegalVersion nodes effective at as_of, ordered by base_law_id",
        complexity="MEDIUM",
        use_cases=[
            "Bitemporal point-in-time reconstruction",
            "Cross-version consistency auditing",
            "Historical state materialization",
        ],
    )

    # ========================================================================
    # CONFLICT RESOLUTION QUERIES
    # ========================================================================

    FIND_UNRESOLVED_NORM_CONFLICTS = CypherQuery(
        name="find_unresolved_norm_conflicts",
        category=QueryCategory.SUPERSESSION,
        description=(
            "Return all NormConflict nodes whose resolution is "
            "UNRESOLVED. These are the conflicts that still need an "
            "authoritative determination (lex-superior, lex-posterior, "
            "lex-specialis, or judicial authority)."
        ),
        cypher="""
        MATCH (nc:NormConflict {resolution: 'UNRESOLVED'})
        RETURN
            nc.id as conflict_id,
            nc.norm_a_id as norm_a_id,
            nc.norm_b_id as norm_b_id,
            nc.conflict_type as conflict_type,
            nc.detection_method as detection_method,
            nc.created_at as created_at
        ORDER BY nc.created_at ASC
        """,
        parameters={},
        returns="All NormConflict nodes still in UNRESOLVED state",
        complexity="LOW",
        use_cases=[
            "Conflict resolution backlog",
            "Audit of pending contradictions",
            "Operator dashboards",
        ],
    )

    FIND_NORM_CONFLICTS_BY_RESOLUTION = CypherQuery(
        name="find_norm_conflicts_by_resolution",
        category=QueryCategory.SUPERSESSION,
        description=(
            "Return all NormConflict nodes with a given resolution "
            "value. Resolution values: RESOLVED_SUPERIOR, "
            "RESOLVED_LEX_POSTERIOR, RESOLVED_LEX_SPECIALIS, "
            "UNRESOLVED, CONTRADICTORY."
        ),
        cypher="""
        MATCH (nc:NormConflict {resolution: $resolution})
        RETURN
            nc.id as conflict_id,
            nc.norm_a_id as norm_a_id,
            nc.norm_b_id as norm_b_id,
            nc.conflict_type as conflict_type,
            nc.resolution_basis as resolution_basis,
            nc.resolved_by_authority as resolved_by_authority,
            nc.resolved_at as resolved_at
        ORDER BY nc.resolved_at DESC
        """,
        parameters={
            "resolution": "ConflictResolution enum value",
        },
        param_specs=[
            ParameterSpec(
                name="resolution",
                kind="conflict_resolution",
                required=True,
                description="ConflictResolution enum value",
            ),
        ],
        returns="NormConflict nodes filtered by resolution",
        complexity="LOW",
        use_cases=[
            "Resolution audit",
            "Resolution method analytics",
            "Adjudication reporting",
        ],
    )

    # ========================================================================
    # JUDICIAL AUTHORITY QUERIES
    # ========================================================================

    FIND_AUTHORITY_OVER_NORM = CypherQuery(
        name="find_authority_over_norm",
        category=QueryCategory.HIERARCHY,
        description=(
            "Return all JudicialAuthority nodes that claim authority "
            "over a given Norm, plus the legal_source they rely on. "
            "Each authority carries an authority_score (0..1) AND a "
            "legal_force enum; the caller must apply the legal force "
            "weighting before treating the result as binding."
        ),
        cypher="""
        MATCH (ja:JudicialAuthority)-[:AUTHORITY_OVER]->(n:Norm {id: $norm_id})
        OPTIONAL MATCH (ja)-[:BASED_ON]->(law:Law)
        RETURN
            ja.id as authority_id,
            ja.court_id as court_id,
            ja.legal_source_type as legal_source_type,
            ja.legal_source_id as legal_source_id,
            ja.authority_scope as authority_scope,
            ja.is_active as is_active,
            ja.valid_from as valid_from,
            ja.valid_until as valid_until,
            law.id as basis_law_id,
            law.name as basis_law_name
        ORDER BY ja.is_active DESC, ja.valid_from ASC
        """,
        parameters={
            "norm_id": "Target norm id",
        },
        param_specs=[
            ParameterSpec(
                name="norm_id",
                kind="non_empty_string",
                required=True,
                description="Target norm id",
            ),
        ],
        returns="All JudicialAuthority nodes claiming AUTHORITY_OVER the given norm",
        complexity="MEDIUM",
        use_cases=[
            "Authority surfacing",
            "Binding-scope determination",
            "Court-level authority tracing",
        ],
    )

    FIND_NORMS_BY_VERDICT_BINDING_SCOPE = CypherQuery(
        name="find_norms_by_verdict_binding_scope",
        category=QueryCategory.HIERARCHY,
        description=(
            "Return all Verdict nodes whose binding_scope contains a "
            "given value (e.g., ALL_COURTS, LOWER_COURTS, PARTIES_ONLY) "
            "and that are in force at as_of. Joins through the verdict's "
            "authority_basis to the underlying law/norm for context."
        ),
        cypher="""
        MATCH (v:Verdict)
        WHERE $binding_scope IN v.binding_scope
        AND v.verdict_date <= date($as_of)
        AND v.legal_force = $legal_force
        RETURN
            v.id as verdict_id,
            v.case_number as case_number,
            v.decision_type as decision_type,
            v.legal_force as legal_force,
            v.binding_scope as binding_scope,
            v.authority_basis as authority_basis,
            v.verdict_date as verdict_date
        ORDER BY v.verdict_date DESC
        """,
        parameters={
            "binding_scope": "BindingScope value (e.g., 'ALL_COURTS')",
            "as_of": "Point-in-time ISO 8601 date",
            "legal_force": "LegalForce value (e.g., 'BINDING')",
        },
        param_specs=[
            ParameterSpec(
                name="binding_scope",
                kind="binding_scope",
                required=True,
                description="BindingScope enum value (e.g., 'ALL_COURTS')",
            ),
            ParameterSpec(
                name="as_of",
                kind="iso8601_required",
                required=True,
                description="Point-in-time ISO 8601 date",
            ),
            ParameterSpec(
                name="legal_force",
                kind="legal_force",
                required=True,
                description="LegalForce enum value (e.g., 'BINDING')",
            ),
        ],
        returns="Verdicts whose binding_scope includes the given value, filtered by legal_force",
        complexity="MEDIUM",
        use_cases=[
            "Stare decisis surfacing",
            "Binding-authority retrieval",
            "Persuasive-vs-binding partitioning",
        ],
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
        # Lazy-initialised constitutional guard. A new instance for
        # every executor is fine; OntologyEnforcer is stateless.
        self._enforcer: Optional[Any] = None
        self.query_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "queries_by_category": {}
        }

    @property
    def enforcer(self) -> Any:
        """Lazy-loaded OntologyEnforcer for parameter validation.

        Lazy because importing ontology_enforcer pulls in the
        violations module, which is not needed for callers that
        only ever use the executor with empty param_specs.
        """
        if self._enforcer is None:
            from mahoun.core.governance.ontology_enforcer import (
                OntologyEnforcer,
            )
            self._enforcer = OntologyEnforcer()
        return self._enforcer

    def _validate_parameters(
        self,
        query: "CypherQuery",
        parameters: Dict[str, Any],
    ) -> None:
        """Run each ParameterSpec against the supplied parameters.

        A parameter that is not declared in the spec is passed
        through unchanged. A spec that targets a parameter that
        is not supplied is treated as "missing": if required,
        ``GovernanceViolationError`` is raised; if optional, the
        spec is skipped.

        The contract here is: every param_spec MUST result in a
        fail-closed call to a constitutional validator. There
        must be no "we'll just pass it through and let Neo4j
        reject it" path; that is the bypass vector this method
        is designed to close.
        """
        specs_by_name = {s.name: s for s in query.param_specs}
        for name, spec in specs_by_name.items():
            value = parameters.get(name)
            if value is None:
                if spec.required:
                    raise GovernanceViolationError(
                        GovernanceViolation(
                            category=ViolationCategory.ONTOLOGY_VIOLATION,
                            severity=ViolationSeverity.CRITICAL,
                            message=(
                                f"Required parameter '{name}' missing for "
                                f"query '{query.name}'"
                            ),
                            details={
                                "query_name": query.name,
                                "parameter": name,
                                "kind": spec.kind,
                            },
                            source="LegalQueryExecutor._validate_parameters",
                        )
                    )
                continue
            self._validate_one(spec, value, query.name)

    def _validate_one(
        self,
        spec: "ParameterSpec",
        value: Any,
        query_name: str,
    ) -> None:
        """Apply a single spec to a single value.

        Dispatch is by spec.kind. Unknown kinds are a programming
        error (a developer added a spec without registering a
        validator), and are rejected with GovernanceViolationError
        rather than silently passed through.
        """
        kind = spec.kind
        if kind == "deontic_operator":
            self.enforcer.validate_deontic_operator(value)
        elif kind == "legal_level":
            self.enforcer.validate_legal_level(value)
        elif kind == "conflict_resolution":
            self.enforcer.validate_conflict_resolution(value)
        elif kind == "legal_force":
            self.enforcer.validate_legal_force(value)
        elif kind == "binding_scope":
            self.enforcer.validate_binding_scope(value)
        elif kind == "norm_status":
            self.enforcer.validate_norm_status(value)
        elif kind == "decision_type":
            self.enforcer.validate_decision_type(value)
        elif kind == "temporal_relation":
            # The query supplies a single value; the third arg of
            # validate_temporal_relationship is the relationship
            # type. We treat the value as the relationship type
            # and let the caller-specific (source, target) pair
            # be checked implicitly by the ontology if the query
            # also references source/target. For queries that
            # don't carry those, this is a soft check.
            self.enforcer.validate_temporal_relationship(
                source_type="Law",
                target_type="Law",
                relationship_type=str(value),
            )
        elif kind == "non_empty_string":
             # Reject None, non-string types, empty strings, and
             # whitespace-only strings at the boundary.
             if not isinstance(value, str) or not value.strip():
                 raise GovernanceViolationError(
                     GovernanceViolation(
                         category=ViolationCategory.ONTOLOGY_VIOLATION,
                         severity=ViolationSeverity.CRITICAL,
                         message=(
                             f"Parameter '{spec.name}' for query "
                             f"'{query_name}' must be a non-empty "
                             f"string"
                         ),
                         details={
                             "query_name": query_name,
                             "parameter": spec.name,
                             "value_type": type(value).__name__,
                         },
                         source="LegalQueryExecutor._validate_parameters",
                     )
                 )
        elif kind == "iso8601_required":
             # Treat as a single-edge temporal range with valid_until
             # omitted; the parser rejects malformed values.
             self.enforcer.validate_temporal_range(
                 valid_from=str(value),
                 valid_until=None,
             )
        elif kind == "list_of_legal_level":
            # The parameter is a list of LegalLevel values. Each
            # one must validate independently. An empty list is
            # accepted (matches "filter that excludes everything").
            if not isinstance(value, list):
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.ONTOLOGY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"Parameter '{spec.name}' for query "
                            f"'{query_name}' must be a list of legal "
                            f"levels, got {type(value).__name__}"
                        ),
                        details={
                            "query_name": query_name,
                            "parameter": spec.name,
                            "value_type": type(value).__name__,
                        },
                        source="LegalQueryExecutor._validate_parameters",
                    )
                )
            for v in value:
                self.enforcer.validate_legal_level(v)
        else:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Unknown parameter spec kind '{kind}' on "
                        f"query '{query_name}'; the executor cannot "
                        f"validate a spec it does not understand"
                    ),
                    details={
                        "query_name": query_name,
                        "parameter": spec.name,
                        "kind": kind,
                    },
                    source="LegalQueryExecutor._validate_parameters",
                )
            )
    
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

        # Constitutional guard: every declared param_spec is
        # validated through OntologyEnforcer BEFORE the query
        # reaches Neo4j. A typo in an enum value or a malformed
        # ISO 8601 date is now a GovernanceViolationError at the
        # call site, not a silent empty result set hours later.
        self._validate_parameters(query, parameters)

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
                    result = session.execute_cypher(query.cypher, parameters)
                    records = [
                        record.data() if hasattr(record, "data") else dict(record)
                        for record in result
                    ]
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