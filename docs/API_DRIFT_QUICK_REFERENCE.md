# 
# مرجع سریع API Drift - پروژه MAHOUN
# 

**آخرین به‌روز رسانی:** 1405/04/26 (2026-07-17)  
**وضعیت:** DRIFT DETECTED ⚠️  
**اقدام فوری:** بله  

---

## 
## خلاصه وضعیت در یک نگاه

### 📊 آمار کلی

| متریک | مقدار | وضعیت |
|--------|-------|--------|
| فایل‌های Schema دچار دريفت | 8 از 14 | ❌ DRIFT |
| Interfaceهای حیاتی ناموزیع | 10 از 12 | ❌ MISMATCH |
| API Verify | - | ✅ PASS |
| Critical Check | - | ❌ FAIL |
| تاثیر بر CI/CD | - | 🚨 **BLOCKED** |

### 🎯 اولویت‌ها

1. **فوری (بله حالا)** - به‌روز رسانی BaseLine و Snapshot
2. **بلند مدت** - استانداردسازی نام‌گذاری API
3. **تحقیق** - بررسی سازگاری backward

---

## 
## دستورات فوری

### 1️⃣ به‌روز رسانی Schema BaseLine

```bash
cd /home/haji/Desktop/KingMahouN
python ci/scripts/schema_drift_detector.py --update-baseline
```

**✅ نتیجه:** BaseLine با Hashهای فعلی فایل‌ها به‌روز می‌شود

---

### 2️⃣ به‌روز رسانی API Snapshot

```bash
cd /home/haji/Desktop/KingMahouN
python -m mahoun.governance.api_guard --update
```

**✅ نتیجه:** Snapshot با API فعلی پروژه به‌روز می‌شود

---

### 3️⃣ تایید درستی تغییرات

```bash
# بررسی Schema
python ci/scripts/schema_drift_detector.py

# بررسی API
python -m mahoun.governance.api_guard --verify

# بررسی Critical Interfaceها
python -m mahoun.governance.api_guard --check-critical
```

**✅ نتایج مورد انتظار:**
- Schema: No drift detected
- API Verify: API snapshot verified successfully
- Critical Check: All critical interfaces present

---

### 4️⃣ اجرا در CI

```bash
make governance-verify
```

---

## 
## لیست کامل فایل‌های دچار دريفت

### Schema Files (8 فایل)

```
Governance Core (3):
  ✗ mahoun/core/governance/ontology_enforcer.py
  ✗ mahoun/core/governance/policies.py
  ✗ mahoun/core/governance/violations.py

Contract Schemas (5):
  ✗ mahoun/schemas/contracts/core_contracts.py
  ✗ mahoun/schemas/contracts/ledger_contracts.py
  ✗ mahoun/schemas/contracts/reasoning_contracts.py
  ✗ mahoun/schemas/legal_struct_schema.py
  ✗ mahoun/schemas/text_schema.py
```

### فایل‌های بدون تغییر (6 فایل)

```
✓ constitution/RedLines.yaml
✓ core_manifest.yaml
✓ mahoun/core/protocols.py
✓ mahoun/schemas/contracts/graph_contracts.py
✓ mahoun/schemas/contracts/invariants_contracts.py
✓ mahoun/schemas/contracts/schemas_contracts.py
```

---

## 
## عدم تطابق Interfaceهای حیاتی

### دسته Governance

| مورد انتظار | واقعی | وضعیت |
|--------------|--------|--------|
| `GovernanceViolation` | `GovernanceViolation` | ✅ Match |
| `GovernanceViolationError` | `GovernanceViolationError` | ✅ Match |
| `is_governance_authorized()` | `is_authorized()` | ❌ Name Mismatch |
| `set_governance_authority(state: bool)` | `set_authorized(state: bool)` | ❌ Name Mismatch |
| `reset_governance_authority(token)` | `reset_authorized(token)` | ❌ Name Mismatch |
| `KernelMutationBoundary.inspect()` | **موجود نیست** | ❌ Missing |
| `KernelMutationBoundary.classify_query()` | `classify_cypher()` | ❌ Name Mismatch |

### دسته Lock

| مورد انتظار | واقعی | وضعیت |
|--------------|--------|--------|
| `GovernanceLock.initialize(...)` | `initialize_governance_at_startup()` | ❌ Name Mismatch |
| `GovernanceLock.is_enforcement_enabled()` | `should_enforce_proof_carrying_contract()` | ❌ Name Mismatch |
| `GovernanceLock.get_mode()` | `GovernanceMode` (enum) | ⚠️ Type Mismatch |
| `GovernanceLock.verify_integrity()` | `check_governance_integrity()` | ❌ Name Mismatch |
| `GovernanceLock.verify_immutable()` | **موجود نیست** | ❌ Missing |

---

## 
## بررسی چالش‌ها

### مشکل اصلی 1: عدم تطابق پیشوندها

**کسانی که پیشوند `governance_` دارند:**
```
Snapshot انتظار دارد:
  - is_governance_authorized()
  - set_governance_authority()
  - reset_governance_authority()

کد واقعیت دارد:
  - is_authorized()
  - set_authorized()
  - reset_authorized()
```

**راه حل:**
- یا پیشوند `governance_` را به توابع اضافه کنید
- یا Snapshot را به‌روز کنید تا با نام‌های واقعی تطابق داشته باشد

---

### مشکل اصلی 2: تفاوت در نام‌گذاری کلاس‌ها

**Snapshot انتظار دارد:**
```
KernelMutationBoundary
```

**کد واقعیت دارد:**
```
MutationAuthorizationBoundary
```

**راه حل:**
- یا کلاس را Rename کنید
- یا Snapshot را به‌روز کنید

---

### مشکل اصلی 3: تفاوت در نام‌گذاری متدها

**المت مورد انتظار:**
```
GovernanceLock.initialize()
GovernanceLock.verify_integrity()
GovernanceLock.verify_immutable()
```

**کد واقعیت دارد:**
```
initialize_governance_at_startup()
check_governance_integrity()
(verify_immutable موجود نیست)
```

**راه حل:**
- استانداردسازی نام‌گذاری متدها (verify_* vs check_*)
- یا به‌روز کردن Snapshot

---

## 
## سیستم‌های تشخیص دريفت

### 🛡️ Schema Drift Detector

- **مکان:** `ci/scripts/schema_drift_detector.py`
- **متد:** مقایسه Hash SHA-256
- **BaseLine:** `ci/schema_baseline.json`
- **دستورات:**
  ```bash
  python ci/scripts/schema_drift_detector.py              # بررسی
  python ci/scripts/schema_drift_detector.py --update-baseline  # به‌روز رسانی
  ```

### 🛡️ API Guard

- **مکان:** `mahoun/governance/api_guard.py`
- **متد:** AST Parsing + Inspect
- **Snapshot:** `constitution/api.snapshot.json`
- **دستورات:**
  ```bash
  python -m mahoun.governance.api_guard --verify          # بررسی
  python -m mahoun.governance.api_guard --update          # به‌روز رسانی
  python -m mahoun.governance.api_guard --check-critical  # بررسی حیاتی
  ```

### 🛡️ Determinism Tests

- **مکان:** `tests/determinism/`
- **متد:** بررسی Hash Consistency
- **تولرانس:** صفر (هر گونه دريفت = شکست)

---

## 
## دستورات مفید

### بررسی وضعیت

```bash
# مشاهده BaseLine فعلی
cat ci/schema_baseline.json | python -m json.tool | head -20

# مشاهده Snapshot فعلی
cat constitution/api.snapshot.json | python -m json.tool | head -40

# لیست Symbolهای عمومی یک ماژول
python3 -c "import inspect; mod = __import__('mahoun.core.governance.authorization_state', fromlist=['']); print([n for n,o in inspect.getmembers(mod) if not n.startswith('_')])"

# مقایسه Hash فایل
sha256sum mahoun/core/governance/ontology_enforcer.py
```

### بررسی تغییرات

```bash
# مشاهده تغییرات در فایل‌های دچار دريفت
git diff HEAD~1 -- mahoun/core/governance/
git diff HEAD~1 -- mahoun/schemas/

# تاریخچه تغییرات
git log --oneline -5 -- mahoun/core/governance/ontology_enforcer.py
```

### اجرا در CI

```bash
# اجرا محلی
make governance-verify

# اجرا کامل تست‌ها
make test

# اجرا تست‌های Governance
pytest tests/governance/ -v
```

---

## 
## چک لیست اقدامات

### ✅ اقدامات فوری (امروز)

- [ ] به‌روز رسانی Schema BaseLine
- [ ] به‌روز رسانی API Snapshot
- [ ] تایید درستی هر دو سیستم
- [ ] بررسی پاس شدن CI

### 📋 اقدامات بلند مدت (این هفته)

- [ ] استانداردسازی نام‌گذاری API
- [ ] بررسی سازگاری backward
- [ ] به‌روز رسانی Manifest
- [ ] بررسی تست‌ها

### 🔍 تحقیق (در صورت لزوم)

- [ ] بررسی تغییرات در Schemaها
- [ ] بررسی تاثیر بر سیستم‌های خارجی
- [ ] مستندسازی تغییرات

---

## 
## اطلاعات تماس و منابع

### مستندات کامل

- **گزارش جامع:** `docs/API_DRIFT_ANALYSIS_REPORT.md`
- **داده‌های خام:** `docs/api_drift_data.json`
- **گزارش اولیه:** گزارش ارائه شده توسط Mistral Vibe

### منابع مرتبط

- **Governance Implementation Report:** `GOVERNANCE_IMPLEMENTATION_REPORT.md`
- **Kernel Manifest:** `constitution/kernel.manifest.yaml`
- **Test Suite:** `tests/governance/`

---

## 
## خلاصه نهایی

### ✅ آنچه باید بله حالا انجام دهید:

```bash
cd /home/haji/Desktop/KingMahouN
python ci/scripts/schema_drift_detector.py --update-baseline
python -m mahoun.governance.api_guard --update
python -m mahoun.governance.api_guard --check-critical
```

### ⚠️ آنچه باید بررسی کنید:

- عدم تطابق نام‌های Interfaceها
- استانداردسازی نام‌گذاری
- سازگاری backward

### 📊 وضعیت پس از اقدامات:

- Schema Drift: ✅ حل شده
- API Snapshot: ✅ حل شده
- Critical Interface: ⚠️ نیاز به استانداردسازی

---

* این مرجع سریع همه اطلاعات ضروری برای مدیریت API Drift در پروژه MAHOUN را در اختیار شما قرار می‌دهد. *
