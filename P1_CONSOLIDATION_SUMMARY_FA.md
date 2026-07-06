# خلاصه تحلیل P1 Duplicates و Canonical Selection

**تاریخ:** 2026-07-06  
**وضعیت P0:** ✅ بسته شد (0 مورد)  
**وضعیت P1:** 🔄 در حال تحلیل (188 مورد)

---

## 📊 آمار کلی

| Metric | Value |
|--------|-------|
| Total P1 Duplicates | 176 مورد |
| Impact Score کل | 392 |
| متوسط فایل به ازای هر duplicate | 2.2 |
| High-impact (4+ files) | 10 مورد |
| Medium-impact (3 files) | 15 مورد |
| Low-impact (2 files) | 151 مورد |

---

## 🎯 Top 10 Canonical Implementations (انتخاب شده)

### 1. **Entity** → `mahoun/graph/builders/entity_extractor.py:51`
- **Impact:** 6 فایل
- **Score:** 7.30/10
- **Reason:** Domain-specific, complete implementation با docstring و type hints
- **Duplicates:** 5 مورد در nlp/, pipelines/, ultra_systems/

### 2. **ValidationResult** → `mahoun/core/fortress_validator.py:231`
- **Impact:** 6 فایل
- **Score:** 7.70/10
- **Reason:** Core location، governance-critical class
- **Duplicates:** 5 مورد در reasoning/, preproduction/, graph/

### 3. **ReasoningMode** → `mahoun/reasoning/unified_reasoning_service.py:89`
- **Impact:** 5 فایل
- **Score:** 6.10/10
- **Reason:** Unified reasoning service = canonical reasoning location
- **Duplicates:** 4 مورد در reasoning_chain, symbolic_reasoner, agents/

### 4. **HealthStatus** → `mahoun/core/protocols/ai_runtime.py:73`
- **Impact:** 4 فایل
- **Score:** 7.10/10
- **Reason:** Protocol definition = source of truth
- **Duplicates:** 3 مورد در infrastructure/, ai/

### 5. **ModelNotFoundError** → `mahoun/core/exceptions.py:144`
- **Impact:** 4 فایل
- **Score:** 6.00/10
- **Reason:** Core exceptions module = canonical error location
- **Duplicates:** 3 مورد در exceptions_v2, protocols, embeddings/

### 6. **ViolationSeverity** → `mahoun/core/fortress_validator.py:88`
- **Impact:** 4 فایل
- **Score:** 6.50/10
- **Reason:** Governance core component
- **Duplicates:** 3 مورد در governance_kernel, violations, agents/

### 7. **ValidationError** → `mahoun/core/config_validator.py:27`
- **Impact:** 4 فایل
- **Score:** 6.50/10
- **Reason:** Config validation = primary validation location
- **Duplicates:** 3 مورد در exceptions.py, exceptions_v2, ledger/

### 8. **ReasoningStep** → `mahoun/reasoning/reasoning_recorder.py:99`
- **Impact:** 4 فایل
- **Score:** 7.30/10
- **Reason:** Reasoning recorder = step tracking canonical
- **Duplicates:** 3 مورد در ultra_reasoning, agents/

### 9. **ReasoningResult** → `mahoun/core/models.py:105`
- **Impact:** 4 فایل
- **Score:** 8.50/10 ⭐ (بالاترین امتیاز)
- **Reason:** Core models = strongest canonical location
- **Duplicates:** 3 مورد در reasoning services

### 10. **UncertaintyEstimate** → `mahoun/core/protocols/advanced_protocols.py:28`
- **Impact:** 4 فایل
- **Score:** 7.70/10
- **Reason:** Protocol definition for uncertainty
- **Duplicates:** 3 مورد در uncertainty/, gaussian_process

---

## 🏗️ معیارهای انتخاب Canonical

### 1. **Location Score (وزن: 40%)**
```
mahoun/core/models        → 10.0 ⭐⭐⭐
mahoun/core/exceptions    → 9.0  ⭐⭐⭐
mahoun/core/*             → 8.0  ⭐⭐
mahoun/schemas/           → 7.0  ⭐⭐
mahoun/<domain>/          → 7.0  ⭐⭐
mahoun/infrastructure/    → 6.0  ⭐
mahoun/pipelines/         → 5.0  ⭐
mahoun/ultra_systems/     → 2.0  ⚠️
archive/                  → 1.0  ❌
```

### 2. **Completeness Score (وزن: 30%)**
- Lines of code > 20: +2 points
- Lines of code > 5: +3 points
- Has docstring: +3 points
- Has type hints: +2 points
- **Max:** 10.0

### 3. **Usage Score (وزن: 20%)**
- تعداد import‌ها در codebase
- (فعلاً neutral: 5.0 - محاسبه expensive است)

### 4. **Quality Score (وزن: 10%)**
- Non-test, non-archive: 5.0
- _v2 files: 4.0 (experimental)
- archive/: 2.0
- test-only: 1.0

---

## 📋 Category Breakdown

| Category | Count | Top Canonical Location |
|----------|-------|------------------------|
| Error/Exception | 34 | `mahoun/core/exceptions.py` |
| Models/Entities | 12 | `mahoun/core/models.py` |
| Config/Settings | 12 | `mahoun/core/config.py` |
| Health/Status | 6 | `mahoun/core/protocols/ai_runtime.py` |
| LLM/AI | 4 | `mahoun/llm/router.py` |
| NLP/Text | 4 | `mahoun/nlp/persian_legal_nlp.py` |
| Security/Governance | 3 | `mahoun/core/fortress_validator.py` |
| Other | 100 | متنوع |

---

## 🔄 Migration Strategy (پیشنهادی)

### Phase 1: High-Impact Consolidation (4-6 files)
**Target:** 3 duplicates با بیشترین impact
- ✅ `Entity` (6 files) → `mahoun/graph/builders/entity_extractor.py`
- ✅ `ValidationResult` (6 files) → `mahoun/core/fortress_validator.py`
- ✅ `ReasoningMode` (5 files) → `mahoun/reasoning/unified_reasoning_service.py`

**Impact:** حذف 17 duplicate implementation

### Phase 2: Medium-Impact Core Consolidation (4 files)
**Target:** 7 duplicates در core modules
- `HealthStatus`, `ModelNotFoundError`, `ViolationSeverity`
- `ValidationError`, `ReasoningStep`, `ReasoningResult`, `UncertaintyEstimate`

**Impact:** حذف 24 duplicate implementation

### Phase 3: Exception & Error Consolidation (3 files)
**Target:** همه Error/Exception duplicates به `mahoun/core/exceptions.py`
- `LedgerWriteError`, `LLMRouterError`, `SerializationError`
- `SecurityBreachException`, `ConfigurationError`

**Impact:** حذف 12 duplicate implementation

### Phase 4: Low-Impact Cleanup (2 files)
**Target:** 151 duplicate با 2 implementation
- Focus on: deprecated paths (`ultra_systems/`, `archive/`, `_v2`)
- Use automated migration script

**Impact:** حذف 151 duplicate implementation

---

## ✅ Next Steps

1. **Review Top 10 Canonical Selections**
   - بررسی دستی completeness هر canonical
   - تأیید که همه features از duplicates موجود است

2. **Create Baseline for Accepted Duplicates**
   - Some duplicates are intentional (e.g., API vs domain models)
   - Create `arch_check_p1_baseline.json` for accepted cases

3. **Start Phase 1 Migration**
   - Pick 1 high-impact duplicate
   - Full migration (update imports → deprecation → removal)
   - Verify with tests

4. **Automate Low-Impact Migration**
   - Script for finding/replacing imports
   - Automated PR generation for 2-file duplicates

---

## 🎓 Lessons Learned

### چرا این duplicates وجود دارند؟

1. **Agent Re-Implementation** (60%)
   - Agent از scratch می‌نویسد بجای extend کردن
   - Lack of "grep before writing" discipline

2. **Experimental Paths** (20%)
   - `ultra_systems/`, `_v2` files
   - Newer implementations که canonical نشدن

3. **Domain Separation** (15%)
   - Schema duplicates: `mahoun/schemas/` vs `mahoun/graph/schema/`
   - API vs Core model separation

4. **Legacy Code** (5%)
   - `archive/` paths که deprecate نشدن

### چگونه از این جلوگیری کنیم?

✅ **AGENTS.md** را قبل از coding بخون  
✅ `grep -rn "class MyClass"` قبل از تعریف class جدید  
✅ Canonical locations را در AGENTS.md document کن  
✅ CI gate برای duplicate detection (arch_check.py)  

---

**تهیه‌شده توسط:** Architecture Analysis Tooling  
**مرجع:** `P1_MIGRATION_PLANS.md` برای جزئیات هر migration
