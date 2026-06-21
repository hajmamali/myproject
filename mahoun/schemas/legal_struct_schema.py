"""
Legal Structure Schema - L2 (VerdictStruct)
============================================
Canonical Pydantic models for structured verdict data extracted by the parser.

This schema represents the L2 layer: structured legal information extracted
from Persian court verdicts by minimal_verdict_parser.py.

All models match the actual output of parse_verdict_text() to ensure
zero-friction integration with existing parsing logic.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


# ============================================================================
# Party Information
# ============================================================================

class PartyInfo(BaseModel):
    """Individual party information (plaintiff, defendant, objector, etc.)"""
    title: Optional[str] = None  # خانم، آقای
    name: Optional[str] = None
    father_name: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class Parties(BaseModel):
    """All parties involved in the case"""
    respondents: List[PartyInfo] = Field(default_factory=list)
    third_party_objector: Optional[PartyInfo] = None

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Case Metadata
# ============================================================================

class CaseMeta(BaseModel):
    """
    Case metadata extracted from verdict header.
    
    Includes court information, case type, procedural stage, and finality status.
    """
    court_level: Optional[str] = None  # e.g., "دادگاه تجدیدنظر"
    procedure_stage: Optional[str] = None  # e.g., "تجدیدنظر", "بدوی"
    case_type: Optional[str] = None  # e.g., "اعتراض ثالث اجرایی"
    is_final: Optional[bool] = None  # قطعیت
    finality_basis: Optional[str] = None  # دلیل قطعیت
    branch_number: Optional[str] = None  # شماره شعبه
    city: Optional[str] = None  # شهر
    province: Optional[str] = None  # استان
    decision_date: Optional[str] = None  # تاریخ تصمیم (ISO format YYYY-MM-DD)

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Claims
# ============================================================================

class Claims(BaseModel):
    """Claims and execution file references"""
    main: List[str] = Field(default_factory=list)  # خواسته‌های اصلی
    execution_files: List[str] = Field(default_factory=list)  # ارجاع به پرونده‌های اجرایی

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Court Decisions
# ============================================================================

class FirstInstanceSummary(BaseModel):
    """Summary of first instance court decision"""
    court: Optional[str] = None  # دادگاه بدوی
    result: Optional[str] = None  # نتیجه

    model_config = ConfigDict(extra="forbid")


class AppealCourtReasoning(BaseModel):
    """Appeal court reasoning and decision"""
    extract: Optional[str] = None  # استخراج از متن
    result: Optional[str] = None  # نتیجه

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Verdict Sections
# ============================================================================

class VerdictSections(BaseModel):
    """Semantic sections of the verdict text"""
    summary: Optional[str] = None  # گردشکار (procedural history)
    verdict: Optional[str] = None  # رأی دادگاه (court decision)

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Legal References
# ============================================================================

class LegalReferences(BaseModel):
    """
    Legal article references cited in the verdict.
    
    Includes substantive law (ماهوی), procedural law (شکلی),
    and Islamic jurisprudence principles (فقه).
    """
    substantive_law: List[str] = Field(default_factory=list)  # مواد قانون ماهوی
    procedural_law: List[str] = Field(default_factory=list)  # مواد قانون شکلی
    fiqh_principles: List[str] = Field(default_factory=list)  # اصول فقهی

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# NER Entities (Enterprise NER Subsystem)
# ============================================================================

class PersonEntityInfo(BaseModel):
    """Person entity extracted by NER"""
    text: str
    title: Optional[str] = None  # خانم/آقای
    name: Optional[str] = None
    father_name: Optional[str] = None
    role: Optional[str] = None  # خواهان، خوانده، وکیل
    national_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start: int = 0
    end: int = 0

    model_config = ConfigDict(extra="forbid")


class OrganizationEntityInfo(BaseModel):
    """Organization entity extracted by NER"""
    text: str
    name: Optional[str] = None
    org_type: Optional[str] = None  # شرکت، بانک، مؤسسه
    registration_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start: int = 0
    end: int = 0

    model_config = ConfigDict(extra="forbid")


class CourtEntityInfo(BaseModel):
    """Court entity extracted by NER"""
    text: str
    name: Optional[str] = None
    level: Optional[str] = None  # بدوی، تجدیدنظر، دیوان عالی
    branch: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start: int = 0
    end: int = 0

    model_config = ConfigDict(extra="forbid")


class LawEntityInfo(BaseModel):
    """Law/Article reference entity extracted by NER"""
    text: str
    article_number: Optional[str] = None
    law_name: Optional[str] = None
    clause: Optional[str] = None
    normalized_ref: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start: int = 0
    end: int = 0

    model_config = ConfigDict(extra="forbid")


class TopicEntityInfo(BaseModel):
    """
    Legal topic/category entity extracted by NER.
    
    Categories include: ملکی، عقود، عیوب_اراده، تعهدات، مسئولیت_مدنی،
    خانواده، ارث، تجاری، کیفری، مجازات، دیات، کار، اداری،
    آیین_دادرسی_مدنی، آیین_دادرسی_کیفری، اجرا، فقهی، مقامات_قضایی،
    دادگاه، نتایج، ثبت، مالی، بیمه، مالکیت_فکری
    """
    text: str
    category: Optional[str] = None
    parent_topic: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    start: int = 0
    end: int = 0

    model_config = ConfigDict(extra="forbid")


class ExtractedEntities(BaseModel):
    """
    All entities extracted by the Enterprise NER subsystem.
    
    Contains 5 entity types with 25 topic categories and 300+ keywords.
    """
    persons: List[PersonEntityInfo] = Field(default_factory=list)
    organizations: List[OrganizationEntityInfo] = Field(default_factory=list)
    courts: List[CourtEntityInfo] = Field(default_factory=list)
    laws: List[LawEntityInfo] = Field(default_factory=list)
    topics: List[TopicEntityInfo] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Final Decision
# ============================================================================

class FinalDecision(BaseModel):
    """
    Final decision of the court.
    
    Includes appeal result, third-party objection status, and finality.
    """
    appeal_result: Optional[str] = None  # نتیجه تجدیدنظر
    third_party_objection: Optional[str] = None  # وضعیت اعتراض ثالث
    is_final: Optional[bool] = None  # قطعیت

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Quality & Source Metadata
# ============================================================================

class ParsingQuality(BaseModel):
    """
    Quality metrics for parsing confidence.
    
    Helps identify low-quality extractions that may need manual review.
    """
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class SourceInfo(BaseModel):
    """Source file metadata"""
    filename: Optional[str] = None
    filepath: Optional[str] = None
    file_size_bytes: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


# ============================================================================
# Top-Level VerdictStruct
# ============================================================================

class VerdictStruct(BaseModel):
    """
    Complete structured verdict information (L2 Schema).
    
    This is the canonical representation of a parsed legal verdict,
    matching the output of minimal_verdict_parser.parse_verdict_text().
    
    Includes:
    - Case metadata (court, type, finality)
    - Parties (plaintiffs, defendants, attorneys)
    - Claims and execution files
    - Court decisions (first instance, appeal)
    - Legal references (substantive, procedural, fiqh)
    - NER entities (persons, organizations, courts, laws, topics)
    - System tags and quality metrics
    
    Usage:
        >>> from mahoun.pipelines.ingestion.minimal_verdict_parser import parse_verdict_text
        >>> raw_dict = parse_verdict_text(verdict_text)
        >>> verdict = VerdictStruct(**raw_dict)
    """
    case_meta: CaseMeta = Field(default_factory=CaseMeta)
    parties: Parties = Field(default_factory=Parties)
    claims: Claims = Field(default_factory=Claims)
    first_instance_summary: FirstInstanceSummary = Field(default_factory=FirstInstanceSummary)
    appeal_court_reasoning: AppealCourtReasoning = Field(default_factory=AppealCourtReasoning)
    sections: VerdictSections = Field(default_factory=VerdictSections)
    legal_references: LegalReferences = Field(default_factory=LegalReferences)
    final_decision: FinalDecision = Field(default_factory=FinalDecision)
    system_tags: List[str] = Field(default_factory=list)
    
    # NER Extracted Entities (Enterprise NER Subsystem)
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    
    # Internal metadata (prefixed with _)
    parsing_quality: ParsingQuality = Field(
        default_factory=ParsingQuality,
        alias="_parsing_quality"
    )
    source: Optional[SourceInfo] = Field(
        default=None,
        alias="_source"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
