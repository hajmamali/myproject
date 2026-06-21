"""
Persian Field Labels for MAHOUN Schema
=======================================
Programmatic Persian labels for UI/reporting components.

This module provides Persian translations for all schema field paths,
enabling user-friendly Persian interfaces and reports.

Usage:
    >>> from mahoun.schemas.field_labels_fa import FIELD_LABELS_FA, get_persian_label
    >>> label = get_persian_label("case_meta.court_level")
    >>> print(label)  # "درجه دادگاه"
"""
from typing import Optional

# ============================================================================
# Persian Field Labels Dictionary
# ============================================================================

FIELD_LABELS_FA = {
    # ========== L2 Schema: VerdictStruct ==========
    
    # case_meta
    "case_meta": "اطلاعات پرونده",
    "case_meta.court_level": "درجه دادگاه",
    "case_meta.procedure_stage": "مرحله رسیدگی",
    "case_meta.case_type": "نوع دعوا",
    "case_meta.is_final": "قطعیت",
    "case_meta.finality_basis": "دلیل قطعیت",
    "case_meta.branch_number": "شماره شعبه",
    "case_meta.city": "شهر",
    "case_meta.province": "استان",
    "case_meta.decision_date": "تاریخ تصمیم",
    
    # parties
    "parties": "اطراف دعوا",
    "parties.respondents": "خواندگان",
    "parties.third_party_objector": "معترض ثالث",
    "party.title": "عنوان",
    "party.name": "نام",
    "party.father_name": "نام پدر",
    
    # claims
    "claims": "خواسته‌ها",
    "claims.main": "خواسته‌های اصلی",
    "claims.execution_files": "پرونده‌های اجرایی",
    
    # first_instance_summary
    "first_instance_summary": "خلاصه دادگاه بدوی",
    "first_instance_summary.court": "دادگاه بدوی",
    "first_instance_summary.result": "نتیجه",
    
    # appeal_court_reasoning
    "appeal_court_reasoning": "استدلال دادگاه تجدیدنظر",
    "appeal_court_reasoning.extract": "استخراج از متن",
    "appeal_court_reasoning.result": "نتیجه",
    
    # sections
    "sections": "بخش‌های رأی",
    "sections.summary": "گردشکار",
    "sections.verdict": "رأی دادگاه",
    
    # legal_references
    "legal_references": "مراجع قانونی",
    "legal_references.substantive_law": "مواد ماهوی",
    "legal_references.procedural_law": "مواد شکلی",
    "legal_references.fiqh_principles": "اصول فقهی",
    
    # final_decision
    "final_decision": "تصمیم نهایی",
    "final_decision.appeal_result": "نتیجه تجدیدنظر",
    "final_decision.third_party_objection": "وضعیت اعتراض ثالث",
    "final_decision.is_final": "قطعیت",
    
    # system_tags
    "system_tags": "برچسب‌های سیستمی",
    
    # ========== Entities (NER Extracted) ==========
    "entities": "موجودیت‌های استخراج‌شده",
    "entities.persons": "اشخاص",
    "entities.organizations": "سازمان‌ها و شرکت‌ها",
    "entities.courts": "مراجع قضایی",
    "entities.laws": "مواد قانونی",
    "entities.topics": "موضوعات حقوقی",
    "entities.dates": "تاریخ‌ها",
    "entities.amounts": "مبالغ",
    
    # Entity attributes
    "entity.text": "متن",
    "entity.confidence": "اطمینان",
    "entity.start": "موقعیت شروع",
    "entity.end": "موقعیت پایان",
    "entity.normalized": "نرمال‌شده",
    
    # Person entity
    "person.title": "عنوان",
    "person.name": "نام",
    "person.father_name": "نام پدر",
    "person.role": "نقش",
    "person.national_id": "کد ملی",
    
    # Organization entity
    "organization.name": "نام سازمان",
    "organization.org_type": "نوع سازمان",
    "organization.registration_id": "شماره ثبت",
    
    # Court entity
    "court.name": "نام دادگاه",
    "court.level": "سطح دادگاه",
    "court.branch": "شماره شعبه",
    "court.city": "شهر",
    "court.province": "استان",
    
    # Law entity
    "law.article_number": "شماره ماده",
    "law.law_name": "نام قانون",
    "law.clause": "بند",
    "law.normalized_ref": "ارجاع نرمال‌شده",
    
    # Topic entity
    "topic.category": "دسته‌بندی",
    "topic.parent_topic": "موضوع والد",
    
    # ========== Topic Categories (25 categories) ==========
    "topic_category.ملکی": "دعاوی ملکی",
    "topic_category.عقود": "عقود و قراردادها",
    "topic_category.عیوب_اراده": "عیوب اراده",
    "topic_category.تعهدات": "تعهدات",
    "topic_category.مسئولیت_مدنی": "مسئولیت مدنی",
    "topic_category.خانواده": "حقوق خانواده",
    "topic_category.ارث": "ارث و وصیت",
    "topic_category.تجاری": "حقوق تجارت",
    "topic_category.کیفری": "حقوق کیفری",
    "topic_category.مجازات": "مجازات‌ها",
    "topic_category.دیات": "دیات",
    "topic_category.کار": "حقوق کار",
    "topic_category.اداری": "حقوق اداری",
    "topic_category.آیین_دادرسی_مدنی": "آیین دادرسی مدنی",
    "topic_category.آیین_دادرسی_کیفری": "آیین دادرسی کیفری",
    "topic_category.اجرا": "اجرای احکام",
    "topic_category.فقهی": "اصول و قواعد فقهی",
    "topic_category.مقامات_قضایی": "مقامات قضایی",
    "topic_category.دادگاه": "انواع دادگاه‌ها",
    "topic_category.نتایج": "نتایج رسیدگی",
    "topic_category.ثبت": "ثبت و اسناد",
    "topic_category.مالی": "امور مالی و بانکی",
    "topic_category.بیمه": "بیمه",
    "topic_category.مالکیت_فکری": "مالکیت فکری",
    
    # _parsing_quality
    "_parsing_quality": "کیفیت پردازش",
    "_parsing_quality.confidence_score": "امتیاز اطمینان",
    "_parsing_quality.metrics": "معیارهای کیفیت",
    
    # _source
    "_source": "منبع",
    "_source.filename": "نام فایل",
    "_source.filepath": "مسیر فایل",
    "_source.file_size_bytes": "حجم فایل (بایت)",
    
    # ========== L1 Schema: TextDocument ==========
    
    "document_id": "شناسه سند",
    "document_type": "نوع سند",
    "title": "عنوان",
    "full_text": "متن کامل",
    "clean_text": "متن نرمال‌شده",
    "date_issued": "تاریخ صدور",
    "court": "مرجع صادرکننده",
    "source_file_path": "مسیر فایل منبع",
    "ingestion_timestamp": "زمان ایجاد",
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_persian_label(field_path: str, default: Optional[str] = None) -> str:
    """
    Get Persian label for a field path.
    
    Args:
        field_path: Dot-separated field path (e.g., "case_meta.court_level")
        default: Default value if label not found (returns field_path if None)
    
    Returns:
        Persian label string
    
    Examples:
        >>> get_persian_label("case_meta.court_level")
        "درجه دادگاه"
        
        >>> get_persian_label("unknown.field", default="نامشخص")
        "نامشخص"
    """
    if default is None:
        default = field_path
    
    return FIELD_LABELS_FA.get(field_path, default)


def get_all_labels() -> dict:
    """
    Get all Persian labels.
    
    Returns:
        Dictionary of all field paths and their Persian labels
    """
    return FIELD_LABELS_FA.copy()


def has_label(field_path: str) -> bool:
    """
    Check if a field path has a Persian label.
    
    Args:
        field_path: Dot-separated field path
    
    Returns:
        True if label exists, False otherwise
    """
    return field_path in FIELD_LABELS_FA
