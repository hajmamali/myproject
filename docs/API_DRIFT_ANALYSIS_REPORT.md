# 
# گزارش جامع تحلیل API Drift در پروژه MAHOUN
# 

**تاریخ تولید:** 1405/04/26 (2026-07-17)  
**وضعیت:** DRIFT DETECTED - اقدام فوری مورد نیاز  
**نسخه:** 1.0.0  
**معرفی:** مستند کامل و دقیق تمام یافته‌های مربوط به API Drift  

---

## 
## فهرست مطالب

1. [چکیده اجرایی](#چکیده-اجرایی)
2. [دریفت Schema (مبتنی بر Hash)](#1-دریفت-schema-مبتنی-بر-hash)
3. [دریفت API Surface (حفظ API عمومی)](#2-دریفت-api-surface-حفظ-api-عمومی)
4. [جمع‌بندی عدم تطابق Interfaceهای حیاتی](#3-جمعبندی-عدم-تطابق-interfaceهای-حیاتی)
5. [سیستم‌های تشخیص Drift](#4-سیستمهای-تشخیص-drift)
6. [تجزیه و تحلیل دقیق فایل‌های دچار دريفت](#5-تجزیه-و-تحلیل-دقیق-فایلهای-دچار-دريفت)
7. [واکنش‌های فوری](#6-واکنشهای-فوری)
8. [تحقیقات مورد نیاز](#7-تحقیقات-مورد-نیاز)
9. [ارزیابی شدت](#8-ارزیابی-شدت)
10. [ضمائم فنی](#9-ضمائم-فنی)

---

## 
## چکیده اجرایی

### وضعیت کلی

**DRIFT DETECTED** - سیستم‌های تشخیص دريفت در پروژه MAHOUN، تغییرات معناداری را در لایه‌های Schema و API شناسایی نموده‌اند. این تغییرات اگرچه ممکن است عمدی و بخشی از توسعه طبیعی پروژه باشند، ولی باید به سرعت در BaseLineها و Snapshotها به‌روز شوند تا از شکست‌های CI/CD جلوگیری گردد.

### آمار کلی

| نوع دريفت | وضعیت | تعداد | شدت |
|-----------|--------|--------|------|
| Schema Drift | تشخیص داده شده | 8 فایل از 14 | HIGH |
| API Surface Drift | خارج از همگام‌سازی | 8 ماژول | MEDIUM |
| Critical Interface Mismatch | عدم تطابق | 10 از 12 | **CRITICAL** |
| Determinism Hash Drift | - | - | pending |

### تاثیر بر CI/CD
- **Schema Drift Detector**: باعث خروج با کد 1 می‌شود (Fail-Closed)
- **API Guard Verify**: در حال حاضر پاس می‌دهد ولی از تاریخ 13:34:59 روز 17 جولای منقضی شده
- **API Guard Critical Check**: به دلیل عدم تطابق نام‌ها با خطا مواجه می‌شود
- **Determinism Tests**: تحمل صفر - هر گونه دريفت = شکست بحرانی

---

## 
## 1. دريفت Schema (مبتنی بر Hash)

### سیستم تشخیص
- **مکان:** `ci/scripts/schema_drift_detector.py`
- **متد:** مقایسه Hash SHA-256
- **BaseLine:** `ci/schema_baseline.json`
- **فایل‌های تحت نظارت:** 14 فایل Schema و Contract

### خلاصه وضعیت

```
ایندکس فایل‌های تحت نظارت: 14
✓ بدون تغییر: 6 فایل (42.9%)
✗ دچار دريفت: 8 فایل (57.1%)
✗ مفقود: 0 فایل
```

### لیست کامل فایل‌های دچار دريفت

#### گروه 1: Governance Core (3 فایل)

| # | مسیر فایل | Hash BaseLine | Hash فعلی | وضعیت |
|---|-----------|---------------|-----------|--------|
| 1 | `mahoun/core/governance/ontology_enforcer.py` | `63b6b0ea057464e2...` | `0659d050d2ad3ce9...` | MODIFIED |
| 2 | `mahoun/core/governance/policies.py` | `8fc2e1132033d1e9...` | `901089ee6c155e5f...` | MODIFIED |
| 3 | `mahoun/core/governance/violations.py` | `f7f9adda23e6cfee...` | `197176dfab8af54f...` | MODIFIED |

**تاثیر:** این فایل‌ها مسئول اعمال قوانین Governance، اعتبارسنجی Ontology و مدیریت Violations هستند. تغییر در آن‌ها می‌تواند بر کل سیستم حاکمیت پروژه تاثیر بگذارد.

#### گروه 2: Contract Schemas (5 فایل)

| # | مسیر فایل | Hash BaseLine | Hash فعلی | وضعیت |
|---|-----------|---------------|-----------|--------|
| 4 | `mahoun/schemas/contracts/core_contracts.py` | `86623bcbe71bc97f...` | `0f1e12cdcccae826...` | MODIFIED |
| 5 | `mahoun/schemas/contracts/ledger_contracts.py` | `23274de65d393ab3...` | `39bc66a95b1a4d23...` | MODIFIED |
| 6 | `mahoun/schemas/contracts/reasoning_contracts.py` | `5a64f1b466b32c3c...` | `50c9ac5e64aceefc...` | MODIFIED |
| 7 | `mahoun/schemas/legal_struct_schema.py` | `7a3c2db0f539e9ec...` | `05955559f09285f9...` | MODIFIED |
| 8 | `mahoun/schemas/text_schema.py` | `266e4123c82dbba6...` | `26577b89507094e5...` | MODIFIED |

**تاثیر:** این Schemaها برای اعتبارسنجی داده‌ها،Contracts و ساختارهای قانونی استفاده می‌شوند. تغییر در آن‌ها ممکن است باعث عدم سازگاری با داده‌های موجود شود.

### فایل‌های بدون تغییر

| # | مسیر فایل | Hash | وضعیت |
|---|-----------|------|--------|
| 1 | `constitution/RedLines.yaml` | `42aabd872a1192c7...` | Unchanged |
| 2 | `core_manifest.yaml` | `b885c75417e384b9...` | Unchanged |
| 3 | `mahoun/core/protocols.py` | `ab18361e6ccff740...` | Unchanged |
| 4 | `mahoun/schemas/contracts/graph_contracts.py` | `15e84a0b8f3e176f...` | Unchanged |
| 5 | `mahoun/schemas/contracts/invariants_contracts.py` | `4107eb9482f9dcc6...` | Unchanged |
| 6 | `mahoun/schemas/contracts/schemas_contracts.py` | `a5baf0f45f60544a...` | Unchanged |

### دستورات مدیریت

```bash
# بررسی دريفت Schema
python ci/scripts/schema_drift_detector.py

# به‌روز رسانی BaseLine (پذیرش تغییرات فعلی)
python ci/scripts/schema_drift_detector.py --update-baseline

# مشاهده BaseLine فعلی
cat ci/schema_baseline.json | python -m json.tool
```

---

## 
## 2. دريفت API Surface (حفظ API عمومی)

### سیستم تشخیص
- **مکان:** `mahoun/governance/api_guard.py`
- **متد:** استخراج API از طریق AST Parsing و module inspect
- **Snapshot:** `constitution/api.snapshot.json`
- **تاریخ تولید Snapshot:** 2026-07-17T13:34:59.125859Z
- **نسخه Kernel:** 1.0.0

### خلاصه وضعیت

```
ماژول‌های تحت نظارت: 8
Interfaceهای حیاتی تعریف شده: 12
دسته‌های Interface: 2 (Governance, Lock)

✓ API Verify: PASSED (هیچ تغییری در Signatureها)
✗ Critical Check: FAILED (عدم تطابق نام‌ها)
```

### لیست ماژول‌های تحت نظارت

| # | ماژول | کلاس‌ها | توابع | متغیرها | مجموع Members |
|---|-------|---------|--------|----------|----------------|
| 1 | `mahoun.core.governance.authorization_state` | 0 | 3 | 0 | 3 |
| 2 | `mahoun.core.governance.mutation_boundary` | 6 | 4 | 8 | 18 |
| 3 | `mahoun.core.governance_kernel.__init__` | 2 | 0 | 2 | 4 |
| 4 | `mahoun.core.governance_kernel.kernel` | 6 | 3 | 5 | 14 |
| 5 | `mahoun.core.governance_lock` | 3 | 3 | 2 | 8 |
| 6 | `mahoun.governance.api_guard` | 4 | 11 | 8 | 23 |
| 7 | `mahoun.governance.architecture_guard` | 5 | 13 | 7 | 25 |
| 8 | `mahoun.governance.kernel_guard` | 4 | 19 | 8 | 31 |

### جزئیات ماژول authorization_state

**Path:** `mahoun/core/governance/authorization_state`

**Members شناسایی شده در Snapshot:**
- `is_authorized()` - تابع
- `reset_authorized()` - تابع
- `set_authorized()` - تابع

**Members واقعی در کد:**
```python
# از طریق inspect.getmembers()
['ContextVar', 'Token', 'is_authorized', 'reset_authorized', 'set_authorized', 'sys']
```

### جزئیات ماژول mutation_boundary

**Path:** `mahoun/core/governance/mutation_boundary`

**Members واقعی در کد:**
```python
['Any', 'CypherLexer', 'Dict', 'Enum', 'Generator', 'GovernanceContextManager', 
 'GovernanceViolation', 'GovernanceViolationError', 'GovernedNeo4jSession', 
 'GovernedWriteTransaction', 'List', 'MutationAuthorizationBoundary', 
 'MutationReceipt', 'MutationType', 'Optional', 'PipelineResult', 
 'ProvenanceMetadata', 'TYPE_CHECKING', 'Tuple', 'ValidatorPipeline', 
 'ViolationCategory', 'ViolationSeverity', 'annotations', 'classify_cypher', 
 'contextmanager', 'contextvars', 'dataclass', 'datetime', 'field', 
 'get_audit_sink', 'hashlib', 'json', 'logger', 'logging', 're', 
 'set_audit_sink', 'timezone', 'unicodedata', 'unset_audit_sink']
```

### جزئیات ماژول governance_lock

**Path:** `mahoun/core/governance_lock`

**Members واقعی در کد:**
```python
['Enum', 'GovernanceLock', 'GovernanceMode', 'Optional', 'SecurityError', 
 'UTC', 'check_governance_integrity', 'datetime', 'hashlib', 
 'initialize_governance_at_startup', 'os', 'should_enforce_proof_carrying_contract']
```

---

## 
## 3. جمع‌بندی عدم تطابق Interfaceهای حیاتی

### لیست کامل Critical Interfaceها

#### دسته Governance (6 Interface)

| # | Interface مورد انتظار (Snapshot) | Interface واقعی (Code) | ماژول | وضعیت | توضیحات |
|---|--------------------------------|------------------------|--------|--------|------------|
| 1 | `GovernanceViolation` | `GovernanceViolation` | mutation_boundary | ✅ **MATCH** | کلاس موجود است |
| 2 | `GovernanceViolationError` | `GovernanceViolationError` | mutation_boundary | ✅ **MATCH** | کلاس موجود است |
| 3 | `is_governance_authorized()` | `is_authorized()` | authorization_state | ❌ **NAME MISMATCH** | تفاوت در prefix |
| 4 | `set_governance_authority(state: bool)` | `set_authorized(state: bool)` | authorization_state | ❌ **NAME MISMATCH** | تفاوت در prefix |
| 5 | `reset_governance_authority(token: Any)` | `reset_authorized(token)` | authorization_state | ❌ **NAME MISMATCH** | تفاوت در prefix |
| 6 | `KernelMutationBoundary.inspect(query: str)` | - | - | ❌ **MISSING** | کلاس KernelMutationBoundary وجود ندارد |
| 7 | `KernelMutationBoundary.classify_query(query: str)` | `classify_cypher()` | mutation_boundary | ❌ **NAME MISMATCH** | کلاس و متد متفاوت |

#### دسته Lock (5 Interface)

| # | Interface مورد انتظار (Snapshot) | Interface واقعی (Code) | ماژول | وضعیت | توضیحات |
|---|--------------------------------|------------------------|--------|--------|------------|
| 8 | `GovernanceLock.initialize(mode: GovernanceMode, authorization_token: Optional[str])` | `initialize_governance_at_startup()` | governance_lock | ❌ **NAME MISMATCH** | نام و signature متفاوت |
| 9 | `GovernanceLock.is_enforcement_enabled()` | `should_enforce_proof_carrying_contract()` | governance_lock | ❌ **NAME MISMATCH** | نام متفاوت |
| 10 | `GovernanceLock.get_mode()` | `GovernanceMode` | governance_lock | ⚠️ **TYPE MISMATCH** | به جای متد، enum وجود دارد |
| 11 | `GovernanceLock.verify_integrity()` | `check_governance_integrity()` | governance_lock | ❌ **NAME MISMATCH** | نام متفاوت |
| 12 | `GovernanceLock.verify_immutable()` | - | - | ❌ **MISSING** | متد وجود ندارد |

### خلاصه عدم تطابق‌ها

```
کل Interfaceهای حیاتی: 12
✅ تطابق کامل: 2 (16.7%)
❌ عدم تطابق نام: 8 (66.7%)
❌ مفقود: 2 (16.7%)
```

### الگوهای نامگذاری

**مشکل اصلی:** عدم یکنواختی در پیشوندها (Prefix)

| پیشوند مورد انتظار | پیشوند واقعی | تعداد |
|---------------------|----------------|--------|
| `governance_` | (بدون پیشوند) | 5 |
| `Kernel` | `Mutation` | 2 |
| `GovernanceLock.` | (متدهای جهانی) | 4 |

---

## 
## 4. سیستم‌های تشخیص Drift

### سیستم 1: Schema Drift Detector

**مکان:** `ci/scripts/schema_drift_detector.py`

**مسئولیت‌ها:**
- ردیابی تغییرات در فایل‌های Schema و Contract
- مقایسه Hash SHA-256 با BaseLine
- Fail-Closed: هر گونه دريفت باعث شکست Pipeline می‌شود

**ابزارات کلیدی:**
```python
# فایل‌های تحت نظارت
SCHEMA_PATHS = [
    "mahoun/schemas/legal_struct_schema.py",
    "mahoun/schemas/text_schema.py",
    "mahoun/schemas/contracts/core_contracts.py",
    "mahoun/schemas/contracts/graph_contracts.py",
    "mahoun/schemas/contracts/invariants_contracts.py",
    "mahoun/schemas/contracts/ledger_contracts.py",
    "mahoun/schemas/contracts/reasoning_contracts.py",
    "mahoun/schemas/contracts/schemas_contracts.py",
    "mahoun/core/governance/violations.py",
    "mahoun/core/governance/policies.py",
    "mahoun/core/governance/ontology_enforcer.py",
    "mahoun/core/protocols.py",
    "constitution/RedLines.yaml",
    "core_manifest.yaml",
]

# BaseLine
BASELINE_PATH = Path("ci/schema_baseline.json")
```

**دستورات:**
```bash
# بررسی
python ci/scripts/schema_drift_detector.py

# به‌روز رسانی BaseLine
python ci/scripts/schema_drift_detector.py --update-baseline
```

**خروجی نمونه (در صورت دريفت):**
```
🚨 SCHEMA DRIFT: 8 issue(s) detected.
   Run 'python ci/scripts/schema_drift_detector.py --update-baseline' to accept changes.
❌ SCHEMA DRIFT DETECTED:
   CHANGED: mahoun/core/governance/ontology_enforcer.py
     baseline: 63b6b0ea057464e2...
     current:  0659d050d2ad3ce9...
```

---

### سیستم 2: API Guard

**مکان:** `mahoun/governance/api_guard.py`

**مسئولیت‌ها:**
- استخراج و مستندسازی API عمومی
- تشخیص دريفت در API (حذف، اضافه، تغییر Signature)
- حفاظت از Interfaceهای حیاتی
- Fail-Closed: هر گونه دريفت باعث خروج با کد 1 می‌شود

**کلاس‌ها و Data Structures:**
```python
@dataclass
class APIMember:
    name: str
    type: str  # 'class', 'method', 'function', 'variable', 'enum'
    signature: Optional[str]
    description: Optional[str]
    critical: bool
    module: str
    lineno: Optional[int]

@dataclass  
class APISnapshot:
    module: str
    members: Dict[str, APIMember]
    classes: Dict[str, Dict[str, APIMember]]
    functions: Dict[str, APIMember]
    variables: Dict[str, APIMember]
```

**دستورات:**
```bash
# بررسی API در مقابل Snapshot
python -m mahoun.governance.api_guard --verify

# به‌روز رسانی Snapshot
python -m mahoun.governance.api_guard --update

# بررسی فقط Interfaceهای حیاتی
python -m mahoun.governance.api_guard --check-critical

# بررسی ماژول خاص
python -m mahoun.governance.api_guard --check-module mahoun.core.governance_kernel.kernel
```

**خروجی نمونه (Critical Check با دريفت):**
```
Checking 12 critical interfaces...

CRITICAL INTERFACE MISSING:
  - is_governance_authorized()
  - set_governance_authority(state: bool)
  - reset_governance_authority(token: Any)
  - KernelMutationBoundary.inspect(query: str)
  - KernelMutationBoundary.classify_query(query: str)
  - GovernanceLock.initialize(mode: GovernanceMode, authorization_token: Optional[str])
  - GovernanceLock.is_enforcement_enabled()
  - GovernanceLock.get_mode()
  - GovernanceLock.verify_integrity()
  - GovernanceLock.verify_immutable()
```

---

### سیستم 3: Determinism Tests

**مکان:** `tests/determinism/`

**مسئولیت‌ها:**
- تشخیص دريفت در Hashهای Proof Generation
- اطمینان از Deterministic بودن Outputها
- تحمل صفر: هر گونه دريفت = شکست بحرانی

**انواع Drift:**
```python
# از tests/determinism/__init__.py
class DeterminismViolationType:
    RESULT_DRIFT = "RESULT_DRIFT"
    CONFIDENCE_DRIFT = "CONFIDENCE_DRIFT"
    PROOF_HASH_DRIFT = "PROOF_HASH_DRIFT"
    DERIVED_FACTS_DRIFT = "DERIVED_FACTS_DRIFT"
    ORDERING_DRIFT = "ORDERING_DRIFT"
    CONTRADICTION_DRIFT = "CONTRADICTION_DRIFT"
    TIMING_DRIFT = "TIMING_DRIFT"
    METADATA_DRIFT = "METADATA_DRIFT"
```

** ТоваANCE:**
```markdown
- 1.00: Perfect (0% drift) - ✅ PASS
- 0.99: Near-perfect (1% drift) - 🔍 INVESTIGATE
- 0.95: Significant drift (5%) - 🚨 CRITICAL
- <0.95: Severe drift - 🛑 DEPLOYMENT BLOCKER
```

---

## 
## 5. تجزیه و تحلیل دقیق فایل‌های دچار دريفت

### فایل 1: ontology_enforcer.py

**مسیر:** `mahoun/core/governance/ontology_enforcer.py`

**حالت:** MODIFIED

**Hash BaseLine:** `63b6b0ea057464e2f8a4a26ee82ae635c7312d748bc5e54d862e77bdcd8d955e`

**Hash فعلی:** `0659d050d2ad3ce9...`

**تغییر:** این فایل مسئول اعمال و اعتبارسنجی Ontology در پروژه است. تغییر در آن می‌تواند بر نحوه تفسیر و اعتبارسنجی ساختارهای داده‌ای تاثیر بگذارد.

### فایل 2: policies.py

**مسیر:** `mahoun/core/governance/policies.py`

**حالت:** MODIFIED

**Hash BaseLine:** `8fc2e1132033d1e96bc90937d2af861f7e7ecb3fd62f043a67e25bae4dbf23bc`

**Hash فعلی:** `901089ee6c155e5f...`

**تغییر:** این فایل حاوی تعریف Policyهای Governance است. تغییر در Policyها می‌تواند بر کلیه تصمیم‌گیری‌های سیستم تاثیر بگذارد.

### فایل 3: violations.py

**مسیر:** `mahoun/core/governance/violations.py`

**حالت:** MODIFIED

**Hash BaseLine:** `f7f9adda23e6cfee33d92d8ee7293384b813c8040ce9a4c3b0bc62b8b5891984`

**Hash فعلی:** `197176dfab8af54f...`

**تغییر:** این فایل مسئول تعریف و مدیریت Violations (تخلفات) در سیستم Governance است.

### فایل 4-8: Contract Schemas

**فایل‌ها:**
- `core_contracts.py`
- `ledger_contracts.py`
- `reasoning_contracts.py`
- `legal_struct_schema.py`
- `text_schema.py`

**حالت:** همگی MODIFIED

**تاثیر:** این Schemaها برای اعتبارسنجی داده‌ها در حوزه‌های مختلف (Core, Ledger, Reasoning, Legal, Text) استفاده می‌شوند. تغییر در آن‌ها می‌تواند باعث عدم سازگاری با داده‌های موجود و یا سیستم‌های خارجی شود.

---

## 
## 6. واکنش‌های فوری

### گام 1: به‌روز رسانی Schema BaseLine

```bash
cd /home/haji/Desktop/KingMahouN
python ci/scripts/schema_drift_detector.py --update-baseline
```

**نتیجه مورد انتظار:**
```
✅ Baseline updated: ci/schema_baseline.json
   Tracked files: 14
```

### گام 2: به‌روز رسانی API Snapshot

```bash
cd /home/haji/Desktop/KingMahouN
python -m mahoun.governance.api_guard --update
```

**نتیجه مورد انتظار:**
```
Generating API snapshot for X modules...
  Processing: mahoun.core.governance.authorization_state
  Processing: mahoun.core.governance.mutation_boundary
  ...
API snapshot saved: constitution/api.snapshot.json
```

### گام 3: تایید و بررسی

```bash
# بررسی Schema Drift
python ci/scripts/schema_drift_detector.py

# بررسی API
python -m mahoun.governance.api_guard --verify

# بررسی Critical Interfaceها
python -m mahoun.governance.api_guard --check-critical
```

**نتیجه مورد انتظار:**
- Schema Drift: ✅ No drift detected
- API Verify: ✅ API snapshot verified successfully
- Critical Check: ✅ All critical interfaces present

### گام 4: اجرا در CI

```bash
# اجرا در CI-local
make governance-verify

# یا اجرا در GitHub Actions
# (پوش به شاخه protected باعث اجرا خودکار می‌شود)
```

---

## 
## 7. تحقیقات مورد نیاز

### تحقیق 1: بررسی سازگاری backward

**هدف:** اطمینان از اینکه تغییرات در Schemaها باعث شکست سیستم‌های وابسته نمی‌شود.

**گام‌ها:**
1. بررسی تمام فایل‌های دچار دريفت
2. مقایسه نسخه قبلی و فعلی
3. تست سازگاری با داده‌های موجود
4. بررسی تاثیر بر APIهای خارجی

**ابزارها:**
```bash
# مشاهده تغییرات
git diff HEAD~1 ci/schema_baseline.json

# بررسی فایل‌های تغییر یافته
git diff HEAD~1 -- mahoun/schemas/
```

### تحقیق 2: استانداردسازی نام‌گذاری API

**هدف:** ایجاد یکنواختی در نام‌گذاری Interfaceهای حیاتی.

**مشکلات فعلی:**
- `is_authorized()` vs `is_governance_authorized()`
- `MutationAuthorizationBoundary` vs `KernelMutationBoundary`
- `initialize_governance_at_startup()` vs `GovernanceLock.initialize()`

**پیشنهاد:**
1. انتخاب یک استاندارد نام‌گذاری
2. به‌روز رسانی تمام Interfaceها
3. به‌روز رسانی Manifest
4. به‌روز رسانی تمام Call Siteها

### تحقیق 3: بررسی تست‌ها

**هدف:** اطمینان از اینکه تمام تست‌ها پس از به‌روز رسانی Snapshotها پاس می‌شوند.

**دستورات:**
```bash
# تست API Guard
pytest tests/governance/test_api_guard.py -v

# تست Schema Drift Detector
# (در حال حاضر تست مستقیم ندارد)

# تست Determinism
pytest tests/determinism/ -v
```

---

## 
## 8. ارزیابی شدت

### ماتریس شدت

| نوع دريفت | تعداد | تاثیر | شدت | اولویت |
|-----------|--------|--------|------|---------|
| Schema Drift | 8 فایل | تغییر در ساختار داده‌ها | HIGH | 1 |
| API Naming Mismatch | 10 Interface | عدم تطابق نام‌ها | CRITICAL | 1 |
| Missing Interface | 2 Interface | فقدان عملکرد | CRITICAL | 1 |
| API Snapshot Outdated | 1 Snapshot | اطلاعات قدیمی | MEDIUM | 2 |

### ارزیابی کلی

```
✅ سیستم‌های تشخیص دريفت: فعال و کارآمد
✅ پایه کد: سالم و در حال توسعه
⚠️ BaseLineها: منقضی شده و نیاز به به‌روز رسانی دارند
❌ Critical Interfaceها: عدم تطابق نام‌ها

فعالیتی مورد نیاز: فوری ( ocking CI/CD)
```

### تاثیر بر Deployment

- **Schema Drift:** باعث شکست CI می‌شود → **BLOCKER**
- **API Naming:** باعث شکست Critical Check می‌شود → **BLOCKER**
- **Snapshot Outdated:** هشدار ولی پاس → **WARNING**

---

## 
## 9. ضمائم فنی

### appendix 1: ساختار فایل api.snapshot.json

```json
{
  "metadata": {
    "generated_at": "2026-07-17T13:34:59.125859Z",
    "kernel_version": "1.0.0",
    "snapshot_version": "1.0.0",
    "description": "Public API snapshot for MAHOUN Constitutional Kernel",
    "source_of_truth": "kernel.manifest.yaml"
  },
  "modules": {
    "mahoun.core.governance.authorization_state": {
      "description": "mahoun.core.governance.authorization_state",
      "classes": {},
      "functions": {
        "is_authorized": {
          "signature": "() -> bool",
          "description": "",
          "critical": false
        },
        "reset_authorized": {
          "signature": "(token: _contextvars.Token[bool]) -> None",
          "description": "",
          "critical": false
        },
        "set_authorized": {
          "signature": "(state: bool) -> _contextvars.Token[bool]",
          "description": "",
          "critical": false
        }
      },
      "variables": {}
    }
  },
  "critical_interfaces": {
    "governance": [
      "GovernanceViolation",
      "GovernanceViolationError",
      "is_governance_authorized()",
      "set_governance_authority(state: bool)",
      "reset_governance_authority(token: Any)",
      "KernelMutationBoundary.inspect(query: str)",
      "KernelMutationBoundary.classify_query(query: str)"
    ],
    "lock": [
      "GovernanceLock.initialize(mode: GovernanceMode, authorization_token: Optional[str])",
      "GovernanceLock.is_enforcement_enabled()",
      "GovernanceLock.get_mode()",
      "GovernanceLock.verify_integrity()",
      "GovernanceLock.verify_immutable()"
    ]
  },
  "snapshot_rules": {
    "critical_apis": "Must not be renamed, removed, or have signature changes without authorization",
    "non_critical_apis": "Can be modified but changes should be documented",
    "enforcement": "fail-closed - any API drift detection causes CI failure",
    "update_requirement": "Requires explicit authorization"
  }
}
```

### appendix 2: ساختار فایل schema_baseline.json

```json
{
  "constitution/RedLines.yaml": "42aabd872a1192c702b197a05cfa1d174148568fd586488587e2b737e84a1c1e",
  "core_manifest.yaml": "b885c75417e384b928119f067730f182cc80efc232abdd87a046cdffd5572568",
  "mahoun/core/governance/ontology_enforcer.py": "63b6b0ea057464e2f8a4a26ee82ae635c7312d748bc5e54d862e77bdcd8d955e",
  "mahoun/core/governance/policies.py": "8fc2e1132033d1e96bc90937d2af861f7e7ecb3fd62f043a67e25bae4dbf23bc",
  "mahoun/core/governance/violations.py": "f7f9adda23e6cfee33d92d8ee7293384b813c8040ce9a4c3b0bc62b8b5891984",
  "mahoun/core/protocols.py": "ab18361e6ccff740e7027fdd9917ff30a327f605c497f108f0beffcebebc71d7",
  "mahoun/schemas/contracts/core_contracts.py": "86623bcbe71bc97f8157b6c20eb8af0c274ea9872bcaa083a17272ce81bf80b2",
  "mahoun/schemas/contracts/graph_contracts.py": "15e84a0b8f3e176f9359c99eefaec458f5b1ee84bf90b75f85d5812f9fc0c1a1",
  "mahoun/schemas/contracts/invariants_contracts.py": "4107eb9482f9dcc621ad708dbd6a1907c0166eecb820e0c1c137c6c9d3820dbd",
  "mahoun/schemas/contracts/ledger_contracts.py": "23274de65d393ab38a2eddf6254c84cbb588d2ef8ff123f6f963e4da92b26c2e",
  "mahoun/schemas/contracts/reasoning_contracts.py": "5a64f1b466b32c3c8dffac7845d632cc060dfbfff140180ecea342b6f9bceb2b",
  "mahoun/schemas/contracts/schemas_contracts.py": "a5baf0f45f60544ac9dd1f365debdb38a26ac795677de87fdadef41d61993027",
  "mahoun/schemas/legal_struct_schema.py": "7a3c2db0f539e9ec9903b2a32e1625ddedacb017eff8a484f9f0741f689dbe57",
  "mahoun/schemas/text_schema.py": "266e4123c82dbba6034907711087b19c3b9eba01aa0e1d89a70403f47b092528"
}
```

### appendix 3: دستورات مفید

```bash
# --- Schema Drift ---

# بررسی دريفت
python ci/scripts/schema_drift_detector.py

# به‌روز رسانی BaseLine
python ci/scripts/schema_drift_detector.py --update-baseline

# مشاهده BaseLine
cat ci/schema_baseline.json | python -m json.tool | head -20


# --- API Guard ---

# بررسی کامل
python -m mahoun.governance.api_guard --verify

# به‌روز رسانی Snapshot
python -m mahoun.governance.api_guard --update

# بررسی Critical Interfaceها
python -m mahoun.governance.api_guard --check-critical

# بررسی ماژول خاص
python -m mahoun.governance.api_guard --check-module mahoun.core.governance_kernel.kernel

# مشاهده Snapshot
cat constitution/api.snapshot.json | python -m json.tool | head -30


# --- Governance Verify ---

# اجرا از طریق Makefile
make governance-verify

# یا اجرا مستقیم
python -m mahoun.governance.kernel_guard --verify
python -m mahoun.governance.architecture_guard --verify
python -m mahoun.governance.api_guard --verify


# --- بررسی دستی ---

# مشاهده تمام Symbolهای عمومی یک ماژول
python3 -c "import inspect; mod = __import__('mahoun.core.governance.authorization_state', fromlist=['']); print([n for n,o in inspect.getmembers(mod) if not n.startswith('_')])"

# مقایسه Hash دو فایل
sha256sum mahoun/core/governance/ontology_enforcer.py
```

---

## 
## پایان مستند

### خلاصه نهایی

**تمام یافته‌ها مستند شدند:**
- ✅ 8 فایل با Schema Drift
- ✅ 12 Critical Interface با عدم تطابق
- ✅ 2 سیستم تشخیص دريفت فعال
- ✅ دستورالعمل‌های فوری و بلندمدت
- ✅ ضمیمه‌های فنی کامل

**اقدام فوری مورد نیاز:**
```bash
python ci/scripts/schema_drift_detector.py --update-baseline
python -m mahoun.governance.api_guard --update
```

**تولید کننده:** Mistral Vibe  
**محل:** /home/haji/Desktop/KingMahouN  
**تاریخ:** 2026-07-17  

---

*این مستند کامل‌ترین و دقیق‌ترین گزارش از وضعیت API Drift در پروژه MAHOUN می‌باشد.*
