#!/usr/bin/env python3
"""
نمایش عملی قابلیت‌های پیشرفته MAHOUN
=====================================

این مثال نشون می‌ده که سه قابلیت جدید integrate شده چطور کار می‌کنن:
1. Uncertainty Service - تخمین عدم قطعیت
2. Ontology Gate - اعتبارسنجی schema گراف
3. Ultra RAG - جستجوی پیشرفته با استدلال گرافی

هر قسمت با مثال واقعی توضیح داده شده.
"""

import asyncio
from typing import List


# ============================================================================
# مثال 1: Uncertainty Service
# ============================================================================

def demo_uncertainty_service():
    """
    🎯 مثال عملی: تخمین عدم قطعیت در تصمیم‌گیری قضایی
    
    سناریو: قاضی می‌خواد بدونه prediction های مدل AI چقدر قابل اعتماده.
    """
    print("\n" + "="*70)
    print("🔬 مثال 1: Uncertainty Service")
    print("="*70)
    
    from mahoun.uncertainty.service import UncertaintyService
    
    # فرض کن مدل AI سه بار روی یک پرونده اجرا شده:
    predictions = [
        0.85,  # اجرا اول: احتمال برد 85%
        0.82,  # اجرا دوم: احتمال برد 82%
        0.88,  # اجرا سوم: احتمال برد 88%
    ]
    
    print("\n📊 نتایج مدل AI برای یک پرونده:")
    print(f"   - Prediction 1: {predictions[0]:.2%}")
    print(f"   - Prediction 2: {predictions[1]:.2%}")
    print(f"   - Prediction 3: {predictions[2]:.2%}")
    
    # ایجاد سرویس uncertainty
    service = UncertaintyService()
    
    # محاسبه عدم قطعیت
    estimate = service.estimate(predictions, method="ensemble")
    
    print("\n📈 تحلیل عدم قطعیت:")
    print(f"   ✓ Epistemic Uncertainty (عدم قطعیت مدل): {estimate.epistemic_uncertainty:.3f}")
    print(f"     → این مقدار نشون می‌ده مدل چقدر مطمئن هست")
    print(f"   ✓ Aleatoric Uncertainty (عدم قطعیت داده): {estimate.aleatoric_uncertainty:.3f}")
    print(f"     → این مقدار نشون می‌ده خود داده چقدر پیچیده است")
    print(f"   ✓ Total Uncertainty: {estimate.total_uncertainty:.3f}")
    print(f"   ✓ Confidence: {estimate.confidence:.1%}")
    
    # تفسیر نتیجه
    print("\n💡 تفسیر برای قاضی:")
    if estimate.is_high_confidence(threshold=0.8):
        print("   ✅ مدل با اطمینان بالا این prediction رو داده")
        print("   ✅ می‌تونید بهش اعتماد کنید")
    else:
        print("   ⚠️ مدل مطمئن نیست، نیاز به بررسی دستی")
    
    print("\n🎓 چرا این مهمه؟")
    print("   → در پرونده‌های حساس، قاضی باید بدونه AI چقدر مطمئنه")
    print("   → اگه uncertainty بالا باشه، باید بیشتر بررسی بشه")


# ============================================================================
# مثال 2: Ontology Gate
# ============================================================================

def demo_ontology_gate():
    """
    🎯 مثال عملی: اعتبارسنجی روابط گراف قانونی
    
    سناریو: یک پرونده جدید می‌خواد به گراف اضافه بشه، باید چک کنیم
    که روابطش با قوانین ontology سازگاره.
    """
    print("\n" + "="*70)
    print("🏛️ مثال 2: Ontology Gate")
    print("="*70)
    
    from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
    from mahoun.core.governance.ontology_gate_adapter import OntologyGateAdapter
    
    # ایجاد ontology gate
    enforcer = OntologyEnforcer()
    gate = OntologyGateAdapter(enforcer)
    
    print("\n📋 سناریو: اضافه کردن یک رأی قضایی جدید")
    print("   پرونده: رای شماره ۱۲۳۴ دادگاه تجدیدنظر")
    
    # Node ها
    nodes = [
        {"type": "Case", "id": "case_1234"},
        {"type": "Law", "id": "law_civil_219"},
        {"type": "Person", "id": "person_plaintiff"},
    ]
    
    # روابط معتبر
    valid_relationships = [
        {
            "type": "CITES",  # پرونده قانون رو cite می‌کنه
            "source_type": "Case",
            "target_type": "Law"
        },
        {
            "type": "PARTY_TO",  # شخص طرف پرونده است
            "source_type": "Person",
            "target_type": "Case"
        }
    ]
    
    print("\n✅ بررسی روابط معتبر:")
    result = gate.validate_schema(nodes=nodes, relationships=valid_relationships)
    print(f"   ✓ تعداد روابط بررسی شده: {result.validated_relationships}")
    print(f"   ✓ نتیجه: {'✅ همه روابط معتبر هستند' if result.is_valid else '❌ روابط نامعتبر پیدا شد'}")
    
    # حالا یه رابطه نامعتبر رو تست کنیم
    print("\n❌ تست یک رابطه نامعتبر:")
    invalid_relationships = [
        {
            "type": "EMPLOYS",  # این رابطه برای Case و Law معنا نداره!
            "source_type": "Case",
            "target_type": "Law"
        }
    ]
    
    result_invalid = gate.validate_schema(
        nodes=nodes,
        relationships=invalid_relationships,
        strict=False
    )
    
    if not result_invalid.is_valid:
        print("   ✓ سیستم رابطه نامعتبر رو تشخیص داد:")
        for violation in result_invalid.violations:
            print(f"     → {violation}")
    
    print("\n🎓 چرا این مهمه؟")
    print("   → جلوگیری از اضافه شدن روابط بی‌معنا به گراف")
    print("   → حفظ consistency و یکپارچگی دانش حقوقی")
    print("   → تضمین اینکه AI فقط با روابط معتبر استدلال کنه")


# ============================================================================
# مثال 3: Ultra RAG
# ============================================================================

async def demo_ultra_rag():
    """
    🎯 مثال عملی: جستجوی پیشرفته با استدلال گرافی
    
    سناریو: وکیل می‌خواد پرونده‌های مشابه رو پیدا کنه، ولی نه فقط
    based on text similarity، بلکه با استفاده از روابط گرافی.
    """
    print("\n" + "="*70)
    print("🔍 مثال 3: Ultra Graph-RAG")
    print("="*70)
    
    from mahoun.rag.ultra_graph_rag import UltraGraphRAG
    from mahoun.rag.ultra_rag_adapter import UltraRAGAdapter
    
    print("\n📋 سناریو: جستجوی پرونده‌های مشابه")
    print("   سوال وکیل: 'پرونده‌هایی که ماده ۲۱۹ قانون مدنی رو نقض کردن'")
    
    # در محیط واقعی، از graph و retriever واقعی استفاده می‌شه
    # اینجا فقط یه mock ساده هست
    print("\n🔄 در حال جستجو...")
    print("   ✓ Step 1: Text Search - پیدا کردن اسناد مرتبط")
    print("   ✓ Step 2: Graph Traversal - پیدا کردن روابط")
    print("   ✓ Step 3: Causal Inference - تحلیل علت و معلول")
    print("   ✓ Step 4: Attention Scoring - امتیازدهی هوشمند")
    
    # نتایج فرضی
    print("\n📊 نتایج (Simulated):")
    print("   ✅ پیدا شد: 5 پرونده مرتبط")
    print("\n   🔗 Reasoning Path 1:")
    print("      پرونده ۱۰۱ → [CITES] → ماده ۲۱۹ → [RELATED_TO] → ماده ۲۲۰")
    print("      (Score: 0.92)")
    
    print("\n   🔗 Reasoning Path 2:")
    print("      پرونده ۲۰۵ → [INTERPRETS] → ماده ۲۱۹ → [APPLIED_IN] → پرونده ۳۰۰")
    print("      (Score: 0.87)")
    
    print("\n   🧠 Causal Links:")
    print("      نقض ماده ۲۱۹ → باطل شدن قرارداد (Strength: 0.85)")
    
    print("\n🎓 چرا این مهمه؟")
    print("   → جستجوی ساده فقط text رو می‌بینه")
    print("   → Ultra RAG روابط منطقی و علت‌ها رو هم می‌بینه")
    print("   → نتایج دقیق‌تر و قابل توجیه‌تر")


# ============================================================================
# مثال 4: استفاده ترکیبی
# ============================================================================

async def demo_combined_usage():
    """
    🎯 مثال عملی: استفاده ترکیبی از هر سه قابلیت
    
    سناریو واقعی: یک پرونده حقوقی کامل از شروع تا پایان
    """
    print("\n" + "="*70)
    print("🏆 مثال 4: استفاده ترکیبی (Real-World Scenario)")
    print("="*70)
    
    print("\n📋 سناریو: بررسی یک پرونده حقوقی کامل")
    print("   موضوع: نقض قرارداد اجاره")
    
    # Step 1: جستجوی پرونده‌های مشابه با Ultra RAG
    print("\n🔍 Step 1: جستجوی پرونده‌های مشابه")
    print("   → استفاده از Ultra RAG")
    print("   → پیدا شد: 8 پرونده مرتبط با قوانین اجاره")
    
    # Step 2: اعتبارسنجی روابط با Ontology Gate
    print("\n🏛️ Step 2: اعتبارسنجی روابط گراف")
    print("   → استفاده از Ontology Gate")
    print("   → بررسی شد: آیا روابط پرونده با قوانین سازگاره؟")
    print("   → نتیجه: ✅ همه روابط معتبر")
    
    # Step 3: تحلیل عدم قطعیت
    print("\n🔬 Step 3: تحلیل اطمینان از نتیجه")
    print("   → استفاده از Uncertainty Service")
    print("   → مدل AI سه بار اجرا شد:")
    print("     • اجرا ۱: احتمال برد مستأجر = 78%")
    print("     • اجرا ۲: احتمال برد مستأجر = 82%")
    print("     • اجرا ۳: احتمال برد مستأجر = 80%")
    print("   → Total Uncertainty: 0.15")
    print("   → Confidence: 85%")
    
    # نتیجه نهایی
    print("\n📝 گزارش نهایی برای قاضی:")
    print("   ✅ پرونده‌های مشابه: 8 مورد پیدا شد")
    print("   ✅ روابط گرافی: معتبر و consistent")
    print("   ✅ اطمینان مدل AI: 85% (قابل قبول)")
    print("   💡 توصیه: می‌توان به پیشنهاد AI اعتماد کرد")
    
    print("\n🎓 ارزش افزوده:")
    print("   ✓ قاضی نتیجه دقیق‌تر می‌گیره")
    print("   ✓ تصمیم based on evidence و استدلال منطقی")
    print("   ✓ Transparency کامل (هر قدم قابل ردیابی)")


# ============================================================================
# مثال 5: نمایش DI Container
# ============================================================================

def demo_di_container():
    """
    🎯 مثال عملی: Dependency Injection Container
    
    نشون می‌ده که سیستم چطور این سرویس‌ها رو مدیریت می‌کنه
    """
    print("\n" + "="*70)
    print("🏗️ مثال 5: Dependency Injection Container")
    print("="*70)
    
    from mahoun.reasoning.adapters import ReasoningDependencyContainer
    
    print("\n📦 ایجاد Container:")
    container = ReasoningDependencyContainer()
    
    print("\n🔍 وضعیت اولیه (قبل از استفاده):")
    status = container.get_initialization_status()
    for service, initialized in status.items():
        icon = "✅" if initialized else "⏳"
        print(f"   {icon} {service}: {'Initialized' if initialized else 'Not Loaded Yet'}")
    
    print("\n💡 Lazy Loading:")
    print("   → سرویس‌ها فقط وقتی load می‌شن که بهشون نیاز باشه")
    print("   → باعث سرعت بالاتر و مصرف کمتر RAM می‌شه")
    
    # دسترسی به یکی از سرویس‌ها
    print("\n🔄 دسترسی به Uncertainty Service...")
    uncertainty = container.uncertainty_service
    
    print("\n🔍 وضعیت بعد از استفاده:")
    status = container.get_initialization_status()
    for service, initialized in status.items():
        icon = "✅" if initialized else "⏳"
        state = "Initialized" if initialized else "Not Loaded Yet"
        if service == "uncertainty_service":
            state += " ← جدیدا load شد!"
        print(f"   {icon} {service}: {state}")
    
    print("\n🎓 چرا این مهمه؟")
    print("   → مدیریت منابع بهینه")
    print("   → Thread-safe (چند کاربر همزمان مشکل ندارن)")
    print("   → قابلیت test (می‌تونیم mock injection کنیم)")


# ============================================================================
# Main
# ============================================================================

def main():
    """اجرای همه مثال‌ها"""
    print("\n" + "="*70)
    print("🚀 MAHOUN Advanced Features - نمایش عملی")
    print("="*70)
    
    # مثال 1: Uncertainty
    demo_uncertainty_service()
    
    # مثال 2: Ontology
    demo_ontology_gate()
    
    # مثال 3: Ultra RAG (async)
    asyncio.run(demo_ultra_rag())
    
    # مثال 4: ترکیبی (async)
    asyncio.run(demo_combined_usage())
    
    # مثال 5: Container
    demo_di_container()
    
    print("\n" + "="*70)
    print("✅ همه مثال‌ها با موفقیت اجرا شدند!")
    print("="*70)
    print("\n💡 نکته: این‌ها مثال‌های ساده‌شده هستن")
    print("   در محیط واقعی با گراف و داده‌های واقعی کار می‌کنن\n")


if __name__ == "__main__":
    main()
