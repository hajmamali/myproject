"""
MAHOUN Schemas Module
=====================
Pydantic models and field labels for legal document structures.

Exports:
- VerdictStruct: Complete verdict structure (L2 Schema)
- Entity models: PersonEntityInfo, CourtEntityInfo, LawEntityInfo, etc.
- Field labels: Persian labels for UI/reporting
"""

# L2 Schema - Verdict Structure
from .legal_struct_schema import (
    # Core models
    VerdictStruct,
    CaseMeta,
    Parties,
    PartyInfo,
    Claims,
    FirstInstanceSummary,
    AppealCourtReasoning,
    VerdictSections,
    LegalReferences,
    FinalDecision,
    ParsingQuality,
    SourceInfo,
    # NER Entity models
    ExtractedEntities,
    PersonEntityInfo,
    OrganizationEntityInfo,
    CourtEntityInfo,
    LawEntityInfo,
    TopicEntityInfo,
)

# Persian Field Labels
from .field_labels_fa import (
    FIELD_LABELS_FA,
    get_persian_label,
    get_all_labels,
    has_label,
)

# L1 Schema - Text Document (if available)
try:
    from .text_schema import TextDocument, DocumentType
    HAS_TEXT_SCHEMA = True
except ImportError:
    HAS_TEXT_SCHEMA = False
    TextDocument = None
    DocumentType = None


__all__ = [
    # L2 Schema
    "VerdictStruct",
    "CaseMeta",
    "Parties",
    "PartyInfo",
    "Claims",
    "FirstInstanceSummary",
    "AppealCourtReasoning",
    "VerdictSections",
    "LegalReferences",
    "FinalDecision",
    "ParsingQuality",
    "SourceInfo",
    # NER Entities
    "ExtractedEntities",
    "PersonEntityInfo",
    "OrganizationEntityInfo",
    "CourtEntityInfo",
    "LawEntityInfo",
    "TopicEntityInfo",
    # Field Labels
    "FIELD_LABELS_FA",
    "get_persian_label",
    "get_all_labels",
    "has_label",
    # L1 Schema (if available)
    "TextDocument",
    "DocumentType",
]
