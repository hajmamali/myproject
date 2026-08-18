# تحلیل ماژول‌های یتیم (Orphaned Modules) - ۲۰۲۶-۰۸-۱۶

## 📊 خلاصه اجرایی

**منبع داده**: `architecture_reports/Orphan_Candidates.json`
- **کاندیداهای مبهم (Ambiguous)**: ۱۸ ماژول
- **کاندیداهای حذف (Delete)**: ۱۴۹ ماژول
- **ماژول‌های OCR بررسی شده**: ۲ ماژول (۲۱۷۱ خط کد)

---

## 🔍 دسته‌بندی و تحلیل

### دسته ۱: کاندیداهای مبهم (Ambiguous Candidates) - ۱۸ مورد

این ماژول‌ها نیاز به بررسی دقیق‌تر دارند زیرا وضعیت استفاده‌شان نامشخص است:

#### ۱. **Governance-Related Modules**
- `mahoun.core.governance_kernel.kernel` - طبق glmreport.md در حال انتقال به Tier-0
- `mahoun.core.policy_resolver` - احتمالاً مربوط به policy resolution
- `mahoun.ledger.write_gate` - طبق AGENTS.md بخشی از ledger integrity (legitimately separate)
- `mahoun.ledger.storage` - احتمالاً storage layer برای ledger

**دلیل نگهداری**: این‌ها بخشی از governance framework هستند و ممکن است در حال migration باشند.

#### ۲. **Reasoning & AI Modules**
- `mahoun.reasoning.backward_chaining` - backward chaining algorithm
- `mahoun.reasoning.forward_chaining` - forward chaining algorithm  
- `mahoun.reasoning.reasoning_recorder` - recording reasoning steps
- `mahoun.rag.citation_engine` - citation generation for RAG

**دلیل نگهداری**: این‌ها ممکن است برای future features یا alternative reasoning paths باشند.

#### ۳. **Guardrails & Safety**
- `mahoun.guardrails.exceptions` - custom exceptions for guardrails
- `mahoun.guardrails.runtime_invariants` - runtime invariant checks

**دلیل نگهداری**: safety-critical components، حتی اگر فعلاً استفاده نشوند.

#### ۴. **Bootstrap & Infrastructure**
- `mahoun.bootstrap.golden_master.behavior_recorder` - behavior recording
- `mahoun.core.exceptions_v2` - v2 of exceptions (migration in progress?)

**دلیل نگهداری**: infrastructure components که ممکن است در transition باشند.

#### ۵. **Graph Operations**
- `mahoun.graph.neo4j.operations` - high-level graph operations
- `mahoun.graph.neo4j.schema` - schema management

**دلیل نگهداری**: abstraction layers که ممکن است جایگزین raw Cypher شوند.

#### ۶. **Agents**
- `mahoun.agents.base_agent` - base class for agents
- `mahoun.agents.claim_agent` - claim-specific agent

**دلیل نگهداری**: agent framework components.

#### ۷. **Other**
- `mahoun.pipelines.ingestion` - entire ingestion package (ambiguous)
- `mahoun.preproduction.models` - preproduction model definitions

**دلیل نگهداری**: package-level ambiguity needs investigation.

---

### دسته ۲: کاندیداهای حذف (Delete Candidates) - ۱۴۹ مورد

#### ۲.۱ **Demo & Example Code** (اولویت بالا برای حذف)
- `demos.demo_bank_scenario`
- `demos.demo_gguf_embeddings`
- `demos.demo_hybrid_traversal`
- `demos.demo_local_llm`
- `demos.demo_switching_logic`
- `demos.financial_aml`
- `demos.healthcare_compliance`
- `examples.advanced_features_demo`
- `examples.finetuning_demo`
- `examples.fortress_validator_demo`
- `examples.legal_aware_usage_examples`
- `examples.reasoning_engine_demo`

**دلیل حذف**: Demo code نباید در production codebase باشد. باید به docs/ یا separate repository منتقل شود.

#### ۲.۲ **Deprecated API Components**
- `api.auth`
- `api.dependencies`
- `api.middleware`
- `api.routers`

**هشدار**: این‌ها package-level هستند، نه فایل‌های تکی. قبل از حذف باید بررسی شود که آیا جایگزین دارند یا خیر.

#### ۲.۳ **Legacy Agents**
- `mahoun.agents.evidence_protocol`
- `mahoun.agents.legacy_adapter`

**دلیل حذف**: "legacy" در نام نشان‌دهنده deprecated است.

#### ۲.۴ **Deprecated AI Modules**
- `mahoun.ai`
- `mahoun.ai.models`

**هشدار**: Package-level deletion، نیاز به بررسی دقیق.

#### ۲.۵ **Bootstrap Components**
- `mahoun.bootstrap`
- `mahoun.bootstrap.contract_validator`
- `mahoun.bootstrap.executors.critical_infrastructure`
- `mahoun.bootstrap.executors.database_storage`
- `mahoun.bootstrap.golden_master`

**هشدار**: Bootstrap components حساس هستند. قبل از حذف باید مطمئن شد که جایگزین دارند.

#### ۲.۶ **Concurrency & Distributed Systems**
- `mahoun.concurrency.deadlock_detector`
- `mahoun.concurrency.distributed_lock`

**دلیل حذف**: اگر در production استفاده نمی‌شوند، maintenance burden است.

#### ۲.۷ **Other Infrastructure**
- `first_step_ci_cd` - temporary CI/CD setup?

**دلیل حذف**: نام نشان‌دهنده temporary است.

---

### دسته ۳: OCR Modules بررسی شده

#### **ocr_ensemble.py** (۷۱۴ خط)
- **وظیفه**: Multi-engine OCR با voting strategies (majority, weighted, best-confidence, unanimous)
- **استفاده**: Zero production importers (طبق AGENTS.md)
- **کیفیت**: Well-designed با proper error handling و graceful degradation
- **هزینه**: Running N OCR engines per page has real cost implications

**توصیه**: **فعال‌سازی** اگر accuracy improvement (15-25%) ارزش cost را دارد. در غیر این صورت **حذف**.

#### **hardened_paddle_ocr.py** (۱۴۵۷ خط)
- **وظیفه**: Enterprise-grade PaddlePaddle OCR با local inference, Persian legal syntax validation
- **استفاده**: ۱ importer در `document_handlers.py:623` (conditional import)
- **کیفیت**: Very comprehensive با PaddleX integration
- **هزینه**: Heavy dependencies (PaddlePaddle, PaddleX)

**توصیه**: **نگهداری** زیرا:
1. فعلاً در production استفاده می‌شود (conditional import)
2. Hardened برای production است
3. Persian legal syntax validation برای domain مهم است

---

## 🎯 توصیه‌های عملی

### فوری (Immediate Actions)
1. **حذف demo code** - به docs/ یا separate repository منتقل شود
2. **بررسی package-level deletions** - قبل از حذف، verify کنید که جایگزین دارند
3. **بررسی bootstrap components** - حساس هستند، نیاز به approval

### کوتاه‌مدت (Short-term)
1. **OCR Ensemble decision** - تصمیم بگیرید: فعال‌سازی یا حذف
2. **Legacy agent removal** - اگر استفاده نمی‌شوند، حذف کنید
3. **Concurrency modules** - اگر distributed lock/deadlock detector استفاده نمی‌شوند، حذف کنید

### میان‌مدت (Medium-term)
1. **Governance kernel migration** - طبق glmreport.md در حال انجام است
2. **Reasoning modules** - بررسی کنید که آیا برای future features نیاز دارند یا خیر
3. **Guardrails modules** - نگهداری کنید، safety-critical هستند

---

## ⚠️ هشدارهای مهم

1. **Package-level deletions خطرناک هستند** - قبل از حذف `api.*` یا `mahoun.ai.*`، مطمئن شوید که جایگزین دارند
2. **Bootstrap components حساس هستند** - حذف bootstrap code می‌تواند startup را بشکند
3. **Governance-related modules در transition هستند** - طبق glmreport.md، governance kernel در حال migration است
4. **Hardened OCR در production استفاده می‌شود** - conditional import در document_handlers.py

---

## 📋 چک‌لیست قبل از هر حذف

- [ ] Verify that no production code imports the module
- [ ] Check if there are tests that depend on the module
- [ ] Confirm that a replacement exists (if it's infrastructure)
- [ ] Get approval from architecture team for package-level deletions
- [ ] Document the deletion reason in a commit message
- [ ] Run full test suite after deletion

---

## 🔬 روش تحقیق پیشنهادی

برای هر orphan module:

```bash
# 1. Check imports
grep -rn "from <module>" --include="*.py" . | grep -v test | grep -v ".kilo"

# 2. Check if it's in switchboard
cat mahoun/switchboard.py | grep "<module>"

# 3. Check if it's in AGENTS.md as canonical
grep "<module>" AGENTS.md

# 4. Check git history
git log --all --oneline -- <module_path>

# 5. Check if it's in constitutional docs
grep -r "<module>" mahoun/constitutional/
```

---

*این گزارش صرفاً تحلیلی است و هیچ تغییری در کد ایجاد نشده است.*
*تاریخ: ۲۰۲۶-۰۸-۱۶*
*تحلیل‌گر: Cascade AI Assistant*
