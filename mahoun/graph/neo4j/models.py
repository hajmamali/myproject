"""
Legal Knowledge Graph Node Models
==================================

Pydantic models for all node types in the legal knowledge graph.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LawCategory(str, Enum):
    """Law category enumeration"""
    CIVIL = "مدنی"
    CRIMINAL = "کیفری"
    COMMERCIAL = "تجاری"
    ADMINISTRATIVE = "اداری"
    CONSTITUTIONAL = "قانون اساسی"
    LABOR = "کار"
    TAX = "مالیاتی"
    OTHER = "سایر"


class LawStatus(str, Enum):
    """Law status enumeration"""
    ACTIVE = "active"
    REPEALED = "repealed"
    AMENDED = "amended"


class LawNode(BaseModel):
    """Law (قانون) node model"""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Law name")
    full_name: str = Field(..., description="Full official name")
    year: int = Field(..., description="Approval year")
    approval_date: Optional[date] = Field(None, description="Approval date")
    category: LawCategory = Field(..., description="Law category")
    status: LawStatus = Field(LawStatus.ACTIVE, description="Law status")
    source_url: Optional[str] = Field(None, description="Source URL")
    full_text: Optional[str] = Field(None, description="Full text of law")
    embedding: Optional[List[float]] = Field(None, description="Text embedding (1024 dim)")
    article_count: int = Field(0, description="Number of articles")
    citation_count: int = Field(0, description="Number of citations")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v):
        if v is not None and len(v) != 1024:
            raise ValueError('Embedding must have 1024 dimensions')
        return v
    
    model_config = ConfigDict(use_enum_values=True)


class ArticleNode(BaseModel):
    """Article (ماده) node model"""
    id: str = Field(..., description="Unique identifier")
    number: int = Field(..., description="Article number")
    law_id: str = Field(..., description="Parent law ID")
    law_name: str = Field(..., description="Parent law name")
    content: str = Field(..., description="Article content")
    has_note: bool = Field(False, description="Has note/تبصره")
    note_count: int = Field(0, description="Number of notes")
    has_clause: bool = Field(False, description="Has clause/بند")
    clause_count: int = Field(0, description="Number of clauses")
    category: Optional[str] = Field(None, description="Article category")
    embedding: Optional[List[float]] = Field(None, description="Text embedding (1024 dim)")
    citation_count: int = Field(0, description="Number of citations")
    pagerank_score: float = Field(0.0, description="PageRank score")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v):
        if v is not None and len(v) != 1024:
            raise ValueError('Embedding must have 1024 dimensions')
        return v
    
    @field_validator('number')
    @classmethod
    def validate_article_number(cls, v):
        if v < 1:
            raise ValueError('Article number must be positive')
        return v


class NoteNode(BaseModel):
    """Note (تبصره) node model"""
    id: str = Field(..., description="Unique identifier")
    article_id: str = Field(..., description="Parent article ID")
    number: int = Field(..., description="Note number")
    content: str = Field(..., description="Note content")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ClauseNode(BaseModel):
    """Clause (بند) node model"""
    id: str = Field(..., description="Unique identifier")
    article_id: str = Field(..., description="Parent article ID")
    number: int = Field(..., description="Clause number")
    content: str = Field(..., description="Clause content")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CourtType(str, Enum):
    """Court type enumeration"""
    GENERAL = "عمومی"
    APPEAL = "تجدیدنظر"
    SUPREME = "دیوان"
    SPECIAL = "ویژه"


class CourtLevel(str, Enum):
    """Court level enumeration"""
    PRIMARY = "بدوی"
    APPEAL = "تجدیدنظر"
    SUPREME = "دیوان"


class CourtJurisdiction(str, Enum):
    """Court jurisdiction enumeration"""
    CIVIL = "حقوقی"
    CRIMINAL = "کیفری"
    FAMILY = "خانواده"
    COMMERCIAL = "تجاری"
    ADMINISTRATIVE = "اداری"


class CourtNode(BaseModel):
    """Court (دادگاه) node model"""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Court name")
    type: CourtType = Field(..., description="Court type")
    level: CourtLevel = Field(..., description="Court level")
    jurisdiction: CourtJurisdiction = Field(..., description="Court jurisdiction")
    province: Optional[str] = Field(None, description="Province")
    city: Optional[str] = Field(None, description="City")
    address: Optional[str] = Field(None, description="Address")
    branch_count: int = Field(0, description="Number of branches")
    established_year: Optional[int] = Field(None, description="Establishment year")
    verdict_count: int = Field(0, description="Number of verdicts")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(use_enum_values=True)


class BranchNode(BaseModel):
    """Branch (شعبه) node model"""
    id: str = Field(..., description="Unique identifier")
    court_id: str = Field(..., description="Parent court ID")
    branch_number: int = Field(..., description="Branch number")
    name: Optional[str] = Field(None, description="Branch name")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class VerdictType(str, Enum):
    """Verdict type enumeration"""
    FINAL = "قطعی"
    ABSENT = "غیابی"
    PRESENT = "حضوری"
    PRIMARY = "بدوی"


class VerdictResult(str, Enum):
    """Verdict result enumeration"""
    CONVICTION = "محکومیت"
    ACQUITTAL = "برائت"
    REJECTION = "رد"
    CONFIRMATION = "تایید"
    ANNULMENT = "نقض"


class VerdictNode(BaseModel):
    """Verdict (حکم/رأی) node model"""
    id: str = Field(..., description="Unique identifier")
    verdict_number: Optional[str] = Field(None, description="Verdict number")
    case_number: str = Field(..., description="Case number")
    type: VerdictType = Field(..., description="Verdict type")
    verdict_date: date = Field(..., description="Verdict date")
    is_final: bool = Field(False, description="Is final verdict")
    content: str = Field(..., description="Verdict content")
    reasoning: Optional[str] = Field(None, description="Legal reasoning")
    result: VerdictResult = Field(..., description="Verdict result")
    embedding: Optional[List[float]] = Field(None, description="Text embedding (1024 dim)")
    cited_articles: List[str] = Field(default_factory=list, description="Cited article IDs")
    similarity_cluster: Optional[int] = Field(None, description="Similarity cluster ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v):
        if v is not None and len(v) != 1024:
            raise ValueError('Embedding must have 1024 dimensions')
        return v
    
    model_config = ConfigDict(use_enum_values=True)


class CaseType(str, Enum):
    """Case type enumeration"""
    CIVIL = "حقوقی"
    CRIMINAL = "کیفری"
    FAMILY = "خانواده"
    COMMERCIAL = "تجاری"


class CaseStatus(str, Enum):
    """Case status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    APPEALED = "appealed"


class CaseNode(BaseModel):
    """Case (پرونده) node model"""
    id: str = Field(..., description="Unique identifier")
    case_number: str = Field(..., description="Case number")
    type: CaseType = Field(..., description="Case type")
    status: CaseStatus = Field(CaseStatus.OPEN, description="Case status")
    filing_date: date = Field(..., description="Case filing date")
    description: Optional[str] = Field(None, description="Case description")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(use_enum_values=True)


class PersonNode(BaseModel):
    """Person (شخص) node model"""
    id: str = Field(..., description="Unique identifier (hashed)")
    name_hash: str = Field(..., description="Hashed name for privacy")
    role: Optional[str] = Field(None, description="Role (judge, lawyer, etc.)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PartyType(str, Enum):
    """Party type enumeration"""
    PLAINTIFF = "خواهان"
    DEFENDANT = "خوانده"
    THIRD_PARTY = "شخص ثالث"


class PartyNode(BaseModel):
    """Party (طرف دعوا) node model"""
    id: str = Field(..., description="Unique identifier")
    case_id: str = Field(..., description="Parent case ID")
    party_type: PartyType = Field(..., description="Party type")
    name_hash: str = Field(..., description="Hashed name for privacy")
    is_legal_entity: bool = Field(False, description="Is legal entity")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(use_enum_values=True)
