# 🎯 نقشه راه مراجع حقیقت (Sources of Truth) — MahouN

## 📋 خلاصه اجرایی

این سند **نقشه راه ساخت و تکمیل ۳ مرجع حقیقت اصلی** سیستم MahouN را ارائه می‌دهد که بدون آن‌ها سیستم **قابل کاربرد عملی نیست**.

---

## 🔍 **وضعیت فعلی (Current State)**

### ✅ **۱. Knowledge Graph (Neo4j)** — 70% آماده

**موجود:**
- ✅ `integrity_checker.py` — بررسی یکپارچگی گراف
- ✅ `mahoun/graph/neo4j/operations.py` — عملیات CRUD
- ✅ `mahoun/graph/builders/entity_extractor.py` — استخراج موجودیت‌ها
- ✅ `mahoun/graph/gnn/graph_builder.py` — ساخت گراف
- ✅ `mahoun/graph/validation/` — Validation pipeline

**ناقص:**
- ❌ **پرکردن اولیه گراف** (Seed Data) — قوانین ایران، سوابق قضایی
- ❌ **Schema یکپارچه** برای domain های مختلف (جرایم اقتصادی، حقوق تجاری، etc)
- ❌ **Tools برای بازپرس** جهت اضافه کردن سوابق جدید
- ❌ **Import Pipeline** برای قوانین مصوب از منابع رسمی

---

### ✅ **۲. Fine-tuned Models** — 60% آماده

**موجود:**
- ✅ `model_manager.py` — مدیریت مدل‌ها
- ✅ `model_versioning.py` — ورژن‌بندی
- ✅ `profile_manager.py` — پروفایل‌های مختلف (BASE/FULL/AIRGAP)
- ✅ `mahoun/ai/runtime_manager.py` — اجرای مدل‌ها

**ناقص:**
- ❌ **مدل Fine-tuned روی قوانین ایران** (NER, Classification, QA)
- ❌ **Dataset آموزشی** — قوانین، آراء قضایی، قراردادها
- ❌ **Fine-tuning Pipeline** — scripts برای train کردن
- ❌ **Evaluation Benchmarks** — accuracy, F1 روی داده‌های حقوقی ایران

---

### ✅ **۳. Legal Knowledge Base** — 50% آماده

**موجود:**
- ✅ `knowledge_graph.py` — ساختار LegalRule, LegalPrecedent
- ✅ `find_applicable_rules()` — جستجوی قوانین مرتبط
- ✅ `find_similar_precedents()` — جستجوی آراء مشابه
- ✅ **Provenance tracking** — پیگیری منبع هر قانون

**ناقص:**
- ❌ **پرکردن با قوانین واقعی** — هیچ قانونی وارد نشده!
- ❌ **آراء قضایی** — هیچ سابقه قضایی وارد نشده!
- ❌ **رویه‌های رسمی** — بخش‌نامه‌ها، دستورالعمل‌ها
- ❌ **UI مدیریتی** — برای اضافه/ویرایش قوانین توسط کارشناسان

---

## 🚀 **فازهای پیاده‌سازی**

### **فاز ۱: Foundation — پایه‌گذاری (۲-۳ هفته)**

#### **Task 1.1: Schema Design**
- طراحی schema نهایی Neo4j برای domain های مختلف
- تعریف Node Types: Person, Company, Transaction, Contract, Evidence
- تعریف Relationship Types: OWNS, TRANSACTED_WITH, SIGNED, REFERENCED_IN
- Document در `docs/schema/neo4j_legal_schema.md`

#### **Task 1.2: Seed Data Collection**
```python
# هدف: جمع‌آوری اولین ۱۰۰ قانون و ۵۰ سابقه قضایی

Sources:
  - قوانین جزایی ایران (کتاب پنجم — جرایم علیه اموال)
  - قانون تجارت ایران
  - قانون مبارزه با پولشویی
  - آراء شعبه ویژه دیوان عالی کشور
  
Format: JSON structured
Location: data/seed/legal_knowledge/
```

#### **Task 1.3: Import Pipeline**
```python
# Script: scripts/import_legal_knowledge.py

Features:
  - Parse JSON seed data
  - Validate structure
  - Insert into LegalKnowledgeGraph
  - Sync with Neo4j
  - Generate audit trail
```

---

### **فاز ۲: Model Training — آموزش مدل‌ها (۳-۴ هفته)**

#### **Task 2.1: Dataset Preparation**
```python
# Dataset: data/training/

Structure:
  /ner/           # Named Entity Recognition
    - contracts/  # ۵۰۰ قرارداد با annotation
    - cases/      # ۳۰۰ پرونده با entity labels
  
  /classification/ # Document Classification
    - doc_types/  # ۱۰۰۰ سند با برچسب نوع
  
  /qa/            # Question Answering
    - legal_qa/   # ۵۰۰ جفت سوال-جواب از قوانین
```

#### **Task 2.2: Fine-tuning Scripts**
```python
# scripts/finetune/

Scripts:
  - finetune_ner.py       # NER برای اشخاص، شرکت‌ها، مبالغ
  - finetune_classifier.py # تشخیص نوع سند
  - finetune_qa.py        # پاسخ به سوالات حقوقی
  
Base Model: ParsBERT or XLM-RoBERTa-Persian

Output:
  - models/mahoun-legal-ner-v1/
  - models/mahoun-legal-classifier-v1/
  - models/mahoun-legal-qa-v1/
```

#### **Task 2.3: Model Integration**
- ادغام مدل‌های fine-tuned شده با `model_manager.py`
- تست accuracy روی validation set
- بروزرسانی `profile_manager.py` با مدل‌های جدید

---

### **فاز ۳: Admin Tools — ابزارهای مدیریتی (۲-۳ هفته)**

#### **Task 3.1: Legal KB Admin UI**
```typescript
// frontend/src/pages/LegalKnowledgeAdmin.tsx

Features:
  - ✅ Add new legal rule
  - ✅ Edit existing rule
  - ✅ Add precedent (case law)
  - ✅ Search & filter
  - ✅ Import from file (JSON/CSV)
  - ✅ Export to file
  - ✅ Approval workflow (کارشناس → مدیر → تأیید نهایی)
```

#### **Task 3.2: Graph Explorer UI**
```typescript
// frontend/src/pages/GraphExplorer.tsx

Features:
  - ✅ Visualize knowledge graph
  - ✅ Interactive node/edge exploration
  - ✅ Search by entity
  - ✅ Show provenance chain
  - ✅ Integrity check reports
```

#### **Task 3.3: Model Management UI**
```typescript
// frontend/src/pages/ModelManagement.tsx

Features:
  - ✅ List available models
  - ✅ Upload new model
  - ✅ Benchmark performance
  - ✅ Switch active model
  - ✅ Model versioning
```

---

### **فاز ۴: Integration & Testing (۲ هفته)**

#### **Task 4.1: End-to-End Testing**
```python
# tests/e2e/test_sources_of_truth_integration.py

Scenarios:
  1. بازپرس پرونده جدید باز می‌کند
  2. سیستم اسناد را پردازش می‌کند (OCR)
  3. موجودیت‌ها استخراج می‌شوند (با مدل fine-tuned)
  4. گراف شواهد ساخته می‌شود
  5. قوانین مرتبط از Legal KB فراخوانی می‌شوند
  6. سوابق مشابه از Precedents پیدا می‌شوند
  7. Verdict نهایی تولید می‌شود
  8. همه در Ledger ثبت می‌شوند
```

#### **Task 4.2: Performance Optimization**
- Caching قوانین پرکاربرد
- Indexing Neo4j برای جستجوی سریع
- Model quantization برای سرعت بیشتر

---

## 📊 **Milestones & Timeline**

| فاز | مدت زمان | Deliverables | وضعیت |
|-----|----------|--------------|--------|
| **فاز ۱** | ۲-۳ هفته | Schema + ۱۰۰ قانون + ۵۰ سابقه | ⏳ Not Started |
| **فاز ۲** | ۳-۴ هفته | ۳ مدل fine-tuned + benchmarks | ⏳ Not Started |
| **فاز ۳** | ۲-۳ هفته | ۳ Admin UI component | ⏳ Not Started |
| **فاز ۴** | ۲ هفته | E2E tests + optimization | ⏳ Not Started |
| **کل** | **۹-۱۲ هفته** | سیستم کامل و کاربردی | - |

---

## 🎯 **اولویت‌بندی**

### **Priority P0 (فوری — بدون این‌ها سیستم کار نمی‌کنه):**
1. ✅ **Seed Data** — حداقل ۱۰۰ قانون + ۵۰ سابقه
2. ✅ **Import Pipeline** — برای وارد کردن قوانین
3. ✅ **Basic NER Model** — استخراج اشخاص، شرکت‌ها، مبالغ

### **Priority P1 (بالا — کاربردی می‌کند):**
4. ✅ **Legal KB Admin UI** — مدیریت قوانین توسط کارشناسان
5. ✅ **Document Classifier** — تشخیص نوع سند
6. ✅ **Graph Explorer** — نمایش گراف شواهد

### **Priority P2 (متوسط — بهبود تجربه):**
7. Model Management UI
8. Advanced benchmarking
9. Performance optimization

---

## 🛠️ **ابزارهای مورد نیاز**

### **Data Collection:**
- [ ] ۱۰۰ قانون (JSON format)
- [ ] ۵۰ رأی قضایی (JSON format)
- [ ] ۵۰۰ قرارداد نمونه (برای NER training)

### **Development:**
- [ ] Hugging Face Transformers
- [ ] PyTorch
- [ ] Neo4j Desktop (برای schema design)
- [ ] Label Studio (برای annotation)

### **Deployment:**
- [ ] Model Registry (MLflow یا Hugging Face Hub)
- [ ] CI/CD برای model deployment
- [ ] Monitoring برای model drift

---

## 💡 **نکات مهم**

### **۱. شروع از کوچک:**
- اول ۱۰-۲۰ قانون وارد کنید، test کنید
- بعد مقیاس دهید

### **۲. کیفیت > کمیت:**
- ۱۰۰ قانون دقیق بهتر از ۱۰۰۰ قانون اشتباه

### **۳. ورژن‌بندی:**
- هر تغییر در Legal KB یک version جدید
- هر مدل fine-tuned یک version جدید

### **۴. Audit Trail:**
- هر قانون وارد شده → چه کسی، کی، چرا
- هر مدل deploy شده → performance metrics

---

## 📞 **تماس و پشتیبانی**

برای شروع:
1. تأیید اولویت‌ها
2. تخصیص resource (data collector, ML engineer)
3. شروع فاز ۱

---

**Last Updated**: 2025-01-07  
**Status**: 🔴 Not Started — منتظر تأیید برای شروع
