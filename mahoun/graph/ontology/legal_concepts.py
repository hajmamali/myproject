"""
Canonical Iranian Legal Concepts Ontology (Phase 2B)
====================================================
Classification: CANONICAL DOMAIN ONTOLOGY
Purpose: Formal semantic hierarchy of legal principles, concepts, and relationships.
"""

from typing import Dict, List, Optional
from mahoun.core.models.semantic import SemanticIdentity


# ============================================================================
# CANONICAL TAXONOMY DEFINITION
# ============================================================================

CANONICAL_LEGAL_CONCEPTS: Dict[str, SemanticIdentity] = {
    # ------------------------------------------------------------------------
    # 1. General Contract Law (حقوق عمومی قراردادها)
    # ------------------------------------------------------------------------
    "concept:freedom_of_contract": SemanticIdentity(
        canonical_id="concept:freedom_of_contract",
        canonical_label_fa="اصل آزادی قراردادها",
        canonical_label_en="freedom_of_contract",
        normalized_label="اصل آزادی قراردادها",
        domain="contract_law",
        aliases_fa=["حق آزادی معاملات", "آزادی اراده در عقود", "حاکمیت اراده", "آزادی قراردادها"],
        aliases_en=["contractual_freedom", "party_autonomy", "freedom_of_agreement"],
        parent_concept_id=None,
        description_fa="اصل نافذ بودن قراردادهای خصوصی میان طرفین مادامی که مخالف صریح قانون آمره نباشد (ماده ۱۰ قانون مدنی)"
    ),
    "concept:validity_of_contracts": SemanticIdentity(
        canonical_id="concept:validity_of_contracts",
        canonical_label_fa="شرایط اساسی صحت معامله",
        canonical_label_en="validity_of_contracts",
        normalized_label="شرایط اساسی صحت معامله",
        domain="contract_law",
        aliases_fa=["صحت عقد", "شرایط صحت قرارداد", "ارکان صحت معامله"],
        aliases_en=["essential_validity_conditions", "contract_validity"],
        parent_concept_id=None,
        description_fa="چهار شرط اساسی برای درستی هر معامله: قصد و رضا، اهلیت، موضوع معین و مشروعیت جهت (ماده ۱۹۰ قانون مدنی)"
    ),
    "concept:binding_force_of_contract": SemanticIdentity(
        canonical_id="concept:binding_force_of_contract",
        canonical_label_fa="اصل لزوم قراردادها",
        canonical_label_en="binding_force_of_contract",
        normalized_label="اصل لزوم قراردادها",
        domain="contract_law",
        aliases_fa=["اصاله اللزوم", "لازم‌الاتباع بودن عقد", "اصل لزوم"],
        aliases_en=["pacta_sunt_servanda", "binding_effect", "principle_of_necessity"],
        parent_concept_id="concept:validity_of_contracts",
        description_fa="عقودی که بر طبق قانون واقع شده بین متعاملین و قائم‌مقام آنها لازم‌الاتباع است (ماده ۲۱۹ قانون مدنی)"
    ),
    "concept:liquidated_damages": SemanticIdentity(
        canonical_id="concept:liquidated_damages",
        canonical_label_fa="وجه التزام قراردادی",
        canonical_label_en="liquidated_damages",
        normalized_label="وجه التزام قراردادی",
        domain="contract_law",
        aliases_fa=["خسارت عدم انجام تعهد مقطوع", "جریمه قراردادی", "وجه التزام"],
        aliases_en=["agreed_damages", "penalty_clause", "liquidated_compensation"],
        parent_concept_id="concept:binding_force_of_contract",
        description_fa="تعیین مبلغ مقطوع خسارت در متن قرارداد در صورت تخلف متعهد از انجام تعهد یا تاخیر (ماده ۲۳۰ قانون مدنی و رای ۸۰۵ دیوان عالی)"
    ),
    "concept:force_majeure": SemanticIdentity(
        canonical_id="concept:force_majeure",
        canonical_label_fa="قوه قاهره و حوادث غیرمترقبه",
        canonical_label_en="force_majeure",
        normalized_label="قوه قاهره و حوادث غیرمترقبه",
        domain="contract_law",
        aliases_fa=["قوه قاهره", "حوادث غیرمترقبه", "حوادث غیر مترقبه", "فورس ماژور", "حوادث قهری", "عذر موجه عدم انجام تعهد"],
        aliases_en=["act_of_god", "unforeseen_circumstances"],
        parent_concept_id=None,
        description_fa="حادثه خارجی، غیرقابل پیش‌بینی و غیرقابل دفع که مانع از اجرای تعهد قراردادی می‌شود (مواد ۲۲۷ و ۲۲۹ قانون مدنی و ماده ۴۳ نشریه ۴۳۱۱)"
    ),

    # ------------------------------------------------------------------------
    # 2. Commercial Law & Securities (حقوق تجارت و اسناد تجاری)
    # ------------------------------------------------------------------------
    "concept:commercial_paper": SemanticIdentity(
        canonical_id="concept:commercial_paper",
        canonical_label_fa="اسناد تجاری",
        canonical_label_en="commercial_paper",
        normalized_label="اسناد تجاری",
        domain="commercial_law",
        aliases_fa=["اوراق تجارتی", "اسناد پرداخت تجاری", "اسناد براتی"],
        aliases_en=["negotiable_instruments", "commercial_instruments"],
        parent_concept_id=None,
        description_fa="اسناد بهادار قابل نقل و انتقال دارای وصف تجریدی و مسئولیت تضامنی شامل برات، سفته و چک"
    ),
    "concept:cheque": SemanticIdentity(
        canonical_id="concept:cheque",
        canonical_label_fa="چک و اسناد صیادی",
        canonical_label_en="cheque",
        normalized_label="چک و اسناد صیادی",
        domain="commercial_law",
        aliases_fa=["چک بانکی", "چک صیادی", "چک بلامحل", "قانون صدور چک"],
        aliases_en=["bank_check", "sayad_cheque", "dishonored_cheque"],
        parent_concept_id="concept:commercial_paper",
        description_fa="سند تجاری برای دستور پرداخت وجه که دارای قابلیت صدور مستقیم اجراییه طبق ماده ۲۳ قانون صدور چک است"
    ),
    "concept:promissory_note": SemanticIdentity(
        canonical_id="concept:promissory_note",
        canonical_label_fa="سفته و فته‌طلب",
        canonical_label_en="promissory_note",
        normalized_label="سفته و فته طلب",
        domain="commercial_law",
        aliases_fa=["سفته تجاری", "فته طلب"],
        aliases_en=["promissory_bill"],
        parent_concept_id="concept:commercial_paper",
        description_fa="سند تجاری تعهد پرداخت وجه در موعد معین یا عندالمطالبه به دارنده (ماده ۳۰۷ قانون تجارت)"
    ),
    "concept:bankruptcy": SemanticIdentity(
        canonical_id="concept:bankruptcy",
        canonical_label_fa="ورشکستگی و توقف تاجر",
        canonical_label_en="bankruptcy",
        normalized_label="ورشکستگی و توقف تاجر",
        domain="commercial_law",
        aliases_fa=["حکم ورشکستگی", "توقف از تادیه دیون", "تصفیه ورشکستگی"],
        aliases_en=["insolvency", "corporate_bankruptcy", "cessation_of_payments"],
        parent_concept_id=None,
        description_fa="وضعیت تاجری که از پرداخت وجوهی که بر عهده اوست متوقف شده و اداره اموالش به مدیر تصفیه واگذار می‌شود (ماده ۴۱۲ قانون تجارت)"
    ),

    # ------------------------------------------------------------------------
    # 3. Engineering & Construction Law (حقوق احداث، نظام مهندسی و پیمانکاری)
    # ------------------------------------------------------------------------
    "concept:contract_permissible_delay": SemanticIdentity(
        canonical_id="concept:contract_permissible_delay",
        canonical_label_fa="تأخیرات مجاز پیمانکاری",
        canonical_label_en="contract_permissible_delay",
        normalized_label="تاخیرات مجاز پیمانکاری",
        domain="construction_law",
        aliases_fa=["تمدید مدت پیمان", "تاخیرات موجه پیمانکار", "تمدید مجاز ماده ۳۰"],
        aliases_en=["excusable_delay", "permissible_contract_extension"],
        parent_concept_id=None,
        description_fa="مواردی که خارج از قصور پیمانکار موجب افزایش مدت اجرای پروژه شده و طبق ماده ۳۰ نشریه ۴۳۱۱ مشمول تمدید مدت می‌شود"
    ),
    "concept:contract_impermissible_delay": SemanticIdentity(
        canonical_id="concept:contract_impermissible_delay",
        canonical_label_fa="تأخیرات غیرمجاز و خسارت تأخیر",
        canonical_label_en="contract_impermissible_delay",
        normalized_label="تاخیرات غیرمجاز و خسارت تاخیر",
        domain="construction_law",
        aliases_fa=["خسارت تاخیر کار ماده ۵۰", "تاخیر غیرموجه پیمانکار", "جریمه تاخیر پروژه"],
        aliases_en=["unexcusable_delay", "liquidated_delay_damages"],
        parent_concept_id="concept:contract_permissible_delay",
        description_fa="تأخیر ناشی از قصور پیمانکار در اجرای تعهدات که موجب اعمال جریمه خسارت تأخیر موضوع ماده ۵۰ نشریه ۴۳۱۱ می‌شود"
    ),
    "concept:contract_suspension": SemanticIdentity(
        canonical_id="concept:contract_suspension",
        canonical_label_fa="تعلیق پیمان",
        canonical_label_en="contract_suspension",
        normalized_label="تعلیق پیمان",
        domain="construction_law",
        aliases_fa=["توقف موقت کارها", "تعلیق ماده ۴۹"],
        aliases_en=["suspension_of_work", "contract_hold"],
        parent_concept_id=None,
        description_fa="اختیار کارفرما در توقف موقت اجرای عملیات پیمانکاری برای مدت حداکثر ۳ ماه با پرداخت هزینه‌های بالاسری (ماده ۴۹ نشریه ۴۳۱۱)"
    ),
    "concept:contract_termination": SemanticIdentity(
        canonical_id="concept:contract_termination",
        canonical_label_fa="فسخ و خاتمه پیمان",
        canonical_label_en="contract_termination",
        normalized_label="فسخ و خاتمه پیمان",
        domain="construction_law",
        aliases_fa=["فسخ ماده ۴۶", "خاتمه پیمان ماده ۴۸", "انحلال قرارداد ساخت"],
        aliases_en=["termination_for_default", "termination_for_convenience"],
        parent_concept_id=None,
        description_fa="فسخ پیمان به دلیل تخلف پیمانکار (ماده ۴۶) یا خاتمه پیمان به صلاحدید کارفرما بدون تقصیر پیمانکار (ماده ۴۸ نشریه ۴۳۱۱)"
    ),
    "concept:construction_supervision_duty": SemanticIdentity(
        canonical_id="concept:construction_supervision_duty",
        canonical_label_fa="مسئولیت نظارت و مهندسی ساختمان",
        canonical_label_en="construction_supervision_duty",
        normalized_label="مسئولیت نظارت و مهندسی ساختمان",
        domain="construction_law",
        aliases_fa=["وظایف مهندس ناظر", "مسئولیت انتظامی مهندسان", "نظارت ساختمانی", "کنترل ساختمان"],
        aliases_en=["engineering_supervision_liability", "building_control_duty"],
        parent_concept_id=None,
        description_fa="الزام مهندسان ناظر و طراح به نظارت مستمر بر انطباق عملیات اجرایی با مقررات ملی ساختمان و مسئولیت انتظامی و مدنی ناشی از تخلف (مواد ۳۴ و ۳۵ قانون نظام مهندسی)"
    ),

    # ------------------------------------------------------------------------
    # 4. Civil Liability & Torts (مسئولیت مدنی و ضمان قهری)
    # ------------------------------------------------------------------------
    "concept:civil_liability": SemanticIdentity(
        canonical_id="concept:civil_liability",
        canonical_label_fa="مسئولیت مدنی و جبران خسارت",
        canonical_label_en="civil_liability",
        normalized_label="مسئولیت مدنی و جبران خسارت",
        domain="tort_law",
        aliases_fa=["ضمان قهری", "جبران ضرر و زیان", "مسئولیت غیرقراردادی"],
        aliases_en=["tort_liability", "civil_damages", "non_contractual_liability"],
        parent_concept_id=None,
        description_fa="تعهد قانونی شخص به جبران خسارت وارده به دیگری ناشی از تقصیر، اتلاف یا تسبیب (ماده ۱ قانون مسئولیت مدنی و ماده ۳۲۸ به بعد قانون مدنی)"
    ),
    "concept:late_payment_damages": SemanticIdentity(
        canonical_id="concept:late_payment_damages",
        canonical_label_fa="خسارت تأخیر تأدیه",
        canonical_label_en="late_payment_damages",
        normalized_label="خسارت تاخیر تادیه",
        domain="civil_procedure",
        aliases_fa=["خسارت تاخیر پرداخت", "شاخص تورم بانک مرکزی", "ماده ۵۲۲ آیین دادرسی مدنی"],
        aliases_en=["interest_for_late_payment", "inflation_delay_damages"],
        parent_concept_id="concept:civil_liability",
        description_fa="مطالبه خسارت کاهش ارزش پول ناشی از امتناع مدیون از پرداخت دین پولی بر مبنای شاخص سالانه بانک مرکزی (ماده ۵۲۲ قانون آیین دادرسی مدنی)"
    ),
}


def get_concept(canonical_id: str) -> Optional[SemanticIdentity]:
    """Retrieve canonical concept by ID."""
    return CANONICAL_LEGAL_CONCEPTS.get(canonical_id)


def list_concepts_by_domain(domain: str) -> List[SemanticIdentity]:
    """List concepts in a given legal domain."""
    return [c for c in CANONICAL_LEGAL_CONCEPTS.values() if c.domain == domain]
