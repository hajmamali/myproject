"""
Legal-Aware Schema Enhancement
==============================
Enhanced Pydantic models with court hierarchy and legal validity metadata.

This module extends existing schemas with legal-specific metadata fields
required for proper legal reasoning and zero-hallucination guarantees.

Key Features:
- Court hierarchy ranking (1=Supreme, 2=Appeals, 3=First Instance)
- Legal validity status (active, repealed, amended)
- Jalali date support for Iranian legal documents
- Authority scoring based on citation analysis
- Global UID synchronization between vector and graph stores
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from enum import Enum


# ============================================================================
# Legal Metadata Enums
# ============================================================================

class CourtRank(int, Enum):
    """Court hierarchy ranking for legal authority"""
    SUPREME_COURT = 1          # دیوان عالی کشور
    APPEALS_COURT = 2          # دادگاه تجدیدنظر
    FIRST_INSTANCE = 3         # دادگاه بدوی
    SPECIALIZED_COURT = 4      # دادگاه تخصصی
    ADMINISTRATIVE_COURT = 5   # دیوان عدالت اداری


class StatuteStatus(str, Enum):
    """Legal document validity status"""
    ACTIVE = "active"          # فعال
    REPEALED = "repealed"      # منسوخ
    AMENDED = "amended"        # اصلاح شده
    SUSPENDED = "suspended"    # تعلیق
    DRAFT = "draft"           # پیش‌نویس


class LegalDocumentType(str, Enum):
    """Types of legal documents"""
    VERDICT = "verdict"        # رأی
    STATUTE = "statute"        # قانون
    REGULATION = "regulation"  # آیین‌نامه
    CIRCULAR = "circular"      # بخشنامه
    PRECEDENT = "precedent"    # سابقه قضایی
    ARTICLE = "article"        # ماده


# ============================================================================
# Enhanced Legal Metadata
# ============================================================================

class LegalMetadata(BaseModel):
    """
    Core legal metadata for all legal documents.
    
    This metadata is injected into both vector store and graph database
    to enable legal-aware retrieval and reasoning.
    """
    # Court Hierarchy
    court_rank: Optional[CourtRank] = Field(
        None,
        description="Court hierarchy rank (1=Supreme, 2=Appeals, 3=First Instance)"
    )
    
    # Legal Validity
    statute_status: StatuteStatus = Field(
        StatuteStatus.ACTIVE,
        description="Legal validity status (active, repealed, amended)"
    )
    
    # Temporal Information
    date_jalali: Optional[str] = Field(
        None,
        description="Persian calendar date (YYYY/MM/DD format)",
        pattern=r"^\d{4}/\d{2}/\d{2}$"
    )
    
    date_gregorian: Optional[str] = Field(
        None,
        description="Gregorian calendar date (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    
    # Authority Scoring
    authority_score: float = Field(
        0.0,
        description="Pre-calculated authority score based on citations",
        ge=0.0,
        le=1.0
    )
    
    # Citation Analysis
    citation_count: int = Field(
        0,
        description="Number of times this document is cited",
        ge=0
    )
    
    cited_by_higher_courts: bool = Field(
        False,
        description="Whether cited by higher court decisions"
    )
    
    # Legal Domain Classification
    legal_domain: Optional[str] = Field(
        None,
        description="Legal domain (civil, criminal, administrative, etc.)"
    )
    
    # Supersession Information
    superseded_by: Optional[str] = Field(
        None,
        description="Document ID that supersedes this document"
    )
    
    supersedes: List[str] = Field(
        default_factory=list,
        description="List of document IDs that this document supersedes"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Enhanced Vector Store Schema
# ============================================================================

class EnhancedRetrievalResult(BaseModel):
    """
    Enhanced retrieval result with legal metadata.
    
    Extends the standard RetrievalResult with legal-specific fields
    for court hierarchy, validity status, and authority scoring.
    """
    # Standard fields
    doc_id: str = Field(..., description="Global document identifier")
    content: str = Field(..., description="Document content")
    score: float = Field(..., description="Retrieval relevance score")
    rank: int = Field(..., description="Result ranking")
    source: str = Field(..., description="Retrieval source (graph, text, hybrid)")
    
    # Enhanced legal metadata
    legal_metadata: LegalMetadata = Field(
        default_factory=LegalMetadata,
        description="Legal-specific metadata"
    )
    
    # Standard metadata (preserved for compatibility)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    @field_validator('legal_metadata', mode='before')
    @classmethod
    def parse_legal_metadata(cls, v):
        """Parse legal metadata from dict if needed"""
        if isinstance(v, dict):
            return LegalMetadata(**v)
        return v
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Enhanced Graph Node Schema
# ============================================================================

class LegalGraphNode(BaseModel):
    """
    Enhanced graph node with legal metadata.
    
    Extends GraphNode with legal-specific properties for
    court hierarchy, validity, and legal relationships.
    """
    # Standard graph node fields
    id: str = Field(..., description="Global unique identifier")
    label: str = Field(..., description="Node display label")
    node_type: LegalDocumentType = Field(..., description="Legal document type")
    
    # Legal metadata
    legal_metadata: LegalMetadata = Field(
        default_factory=LegalMetadata,
        description="Legal-specific metadata"
    )
    
    # Standard properties
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional node properties"
    )
    
    # Quality metrics
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    quality_score: float = Field(0.0, ge=0.0, le=1.0)
    validation_status: str = Field("pending")
    
    # Temporal tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Legal Relationship Schema
# ============================================================================

class LegalRelationshipType(str, Enum):
    """Legal relationship types for graph edges"""
    CITES = "CITES"                    # (Verdict)-[:CITES]->(Article)
    SUPERSEDED_BY = "SUPERSEDED_BY"    # (Article)-[:SUPERSEDED_BY]->(Article)
    SUPERSEDES = "SUPERSEDES"          # (Article)-[:SUPERSEDES]->(Article)
    AFFIRMS = "AFFIRMS"                # (Verdict)-[:AFFIRMS]->(Verdict)
    REVERSES = "REVERSES"              # (Verdict)-[:REVERSES]->(Verdict)
    OVERRULES = "OVERRULES"            # (Verdict)-[:OVERRULES]->(Verdict)
    HAS_SUBJECT = "HAS_SUBJECT"        # (Law)-[:HAS_SUBJECT]->(Topic)
    PART_OF = "PART_OF"                # (Article)-[:PART_OF]->(Law)
    APPLIES_TO = "APPLIES_TO"          # (Law)-[:APPLIES_TO]->(Case)
    DECIDED_BY = "DECIDED_BY"          # (Case)-[:DECIDED_BY]->(Court)


class LegalGraphEdge(BaseModel):
    """
    Enhanced graph edge with legal relationship metadata.
    
    Represents legal relationships between documents with
    validity status and temporal information.
    """
    # Standard edge fields
    source_id: str = Field(..., description="Source node global ID")
    target_id: str = Field(..., description="Target node global ID")
    relationship_type: LegalRelationshipType = Field(..., description="Legal relationship type")
    
    # Legal relationship properties
    relationship_status: StatuteStatus = Field(
        StatuteStatus.ACTIVE,
        description="Relationship validity status"
    )
    
    effective_date: Optional[str] = Field(
        None,
        description="Date when relationship became effective"
    )
    
    # Standard properties
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional edge properties"
    )
    
    # Quality metrics
    weight: float = Field(1.0, ge=0.0)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    
    # Temporal tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Global Identifier Management
# ============================================================================

class GlobalIdentifier(BaseModel):
    """
    Global identifier for cross-system synchronization.
    
    Ensures identical doc_id in vector store = uid in Neo4j
    to prevent data silos and maintain referential integrity.
    """
    uid: str = Field(..., description="Global unique identifier")
    document_type: LegalDocumentType = Field(..., description="Document type")
    
    # System presence tracking
    in_vector_store: bool = Field(False, description="Present in vector store")
    in_graph_store: bool = Field(False, description="Present in graph store")
    
    # Metadata consistency
    vector_metadata_hash: Optional[str] = Field(None, description="Vector metadata hash")
    graph_metadata_hash: Optional[str] = Field(None, description="Graph metadata hash")
    
    # Synchronization status
    sync_status: str = Field("pending", description="Synchronization status")
    last_sync: Optional[datetime] = Field(None, description="Last synchronization time")
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Legal Query Filters
# ============================================================================

class LegalQueryFilter(BaseModel):
    """
    Legal-aware query filters for retrieval.
    
    Enables filtering by court hierarchy, validity status,
    and temporal constraints for legal document retrieval.
    """
    # Court hierarchy filters
    min_court_rank: Optional[CourtRank] = Field(
        None,
        description="Minimum court rank (higher authority)"
    )
    
    max_court_rank: Optional[CourtRank] = Field(
        None,
        description="Maximum court rank (lower authority)"
    )
    
    # Validity filters
    allowed_statuses: List[StatuteStatus] = Field(
        default_factory=lambda: [StatuteStatus.ACTIVE],
        description="Allowed document statuses"
    )
    
    exclude_repealed: bool = Field(
        True,
        description="Exclude repealed documents"
    )
    
    # Temporal filters
    date_from: Optional[str] = Field(
        None,
        description="Filter documents from this date (YYYY-MM-DD)"
    )
    
    date_to: Optional[str] = Field(
        None,
        description="Filter documents to this date (YYYY-MM-DD)"
    )
    
    # Authority filters
    min_authority_score: float = Field(
        0.0,
        description="Minimum authority score",
        ge=0.0,
        le=1.0
    )
    
    require_higher_court_citation: bool = Field(
        False,
        description="Require citation by higher courts"
    )
    
    # Domain filters
    legal_domains: List[str] = Field(
        default_factory=list,
        description="Filter by legal domains"
    )
    
    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Migration Schema
# ============================================================================

class LegalSchemaMigration(BaseModel):
    """
    Schema for tracking legal metadata migration.
    
    Tracks the process of adding legal metadata to existing
    documents in both vector and graph stores.
    """
    migration_id: str = Field(..., description="Migration batch identifier")
    document_id: str = Field(..., description="Document being migrated")
    
    # Migration status
    status: str = Field("pending", description="Migration status")
    started_at: Optional[datetime] = Field(None, description="Migration start time")
    completed_at: Optional[datetime] = Field(None, description="Migration completion time")
    
    # Migration results
    vector_store_updated: bool = Field(False, description="Vector store updated")
    graph_store_updated: bool = Field(False, description="Graph store updated")
    
    # Error tracking
    errors: List[str] = Field(default_factory=list, description="Migration errors")
    warnings: List[str] = Field(default_factory=list, description="Migration warnings")
    
    # Metadata changes
    metadata_added: Dict[str, Any] = Field(
        default_factory=dict,
        description="Legal metadata added"
    )
    
    model_config = ConfigDict(extra="forbid")