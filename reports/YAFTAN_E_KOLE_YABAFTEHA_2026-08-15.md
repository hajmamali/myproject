# 📋 گزارش کامل یافته‌های forensic سیستم MahouN

**تاریخ:** 1405/05/25 (2026-08-15)  
**بازرس:** سیستم forensic خودکار  
**وضعیت:** صرفاً کشف - بدون هیچ تغییری در کد  
**زبان:** فارسی

---

## 🎯 **فهرست مطالب**

1. [خلاصه اجرایی](#1-خلاصه-اجرایی)
2. [یافته‌های اصلی](#2-یافته‌های-اصلی)
3. [ тому analyzed‌های بدون استفاده در pipelines](#3-ماژول‌های-بدون-استفاده-در-pipelines)
4. [مشکلات راه‌اندازی سیستم](#4-مشکلات-راه‌اندازی-سیستم)
5. [تحلیل عدم استفاده از ماژول‌ها](#5-تحلیل-عدم-استفاده-از-ماژول‌ها)
6. [همبستگی بین مسائل](#6-همبستگی-بین-مسائل)
7. [شواهد دقیق](#7-شواهد-دقیق)
8. [سوال‌های بی‌پاسخ](#8-سوال‌های-بی‌پاسخ)
9. [پیشنهادات برای تحقیقات بعدی](#9-پیشنهادات-برای-تحقیقات-بعدی)

---

## 1. خلاصه اجرایی

### 🔍 **کشف اصلی**

سیستم MahouN دارای **چهار دسته مشکل اصلی** است:

#### **دسته ۱: خطاهای import در راه‌اندازی** (CRITICAL)
- عدم وجود تابع `require_permissions` در ماژول `mahoun.security.rbac`
- عدم import ماژول `asyncio` در فایل `mahoun/graph/neo4j/connection.py`

#### **دسته ۲: ماژول‌های ساخته شده اما استفاده‌نشده** (HIGH)
- ۲۸ ماژول در مسیر `mahoun/pipelines/` وجود دارند که **در هیچ جای سیستم اصلی** استفاده نمی‌شوند
- برخی از این ماژول‌ها (مثل `hardened_paddle_ocr.py` و `ocr_ensemble.py`) در `AGENTS.md` به عنوان مولفه‌های قوی گزارش شده‌اند

#### **دسته ۳: حالت‌های متضاد Neo4j** (MEDIUM)
- پیام "Canonical async driver initialized successfully" → "Neo4j unavailable" → "Neo4j initialized"
- این یک **حالت متضاد ظاهری** است که در واقع حاصل **معماری fail-soft** می‌باشد

#### **دسته ۴: عدم پوشش CI** (LOW)
- گیت‌های CI **فقط آنالیز استاتیک** انجام می‌دهند
- **تست‌های integration** برای مسیریابی راه‌اندازی وجود **ندارد**
- خطاهای import توسط CI ** تشخیص داده نمی‌شوند**

---

## 2. یافته‌های اصلی

### ⚠️ **FINDING-001: شکست بارگذاری Governance Router**

| آیتم | مقدار |
|------|-------|
| **Severity** | HIGH |
| **File** | `api/routers/governance.py:16` |
| **Error** | `ImportError: cannot import name 'require_permissions' from 'mahoun.security.rbac'` |
| **Confidence** | CRITICAL |
| **Type** | FACT |

#### **-root cause**
ماژول `api/routers/governance.py` سعی می‌کند تابع `require_permissions` (با s جمع) را از `mahoun.security.rbac` import کند:

```python
# api/routers/governance.py:16
from mahoun.security.rbac import require_permissions, Permission
```

اما در `mahoun/security/rbac.py` **فقط** موارد زیر تعریف شده‌اند:
- `Permission` (Enum)
- `require_permission` (singular) - تابع decorator
- `RBACManager.require_permission()` - متد کلاس

**تابع `require_permissions` (plural) در هیچ جای کدبیس وجود ندارد.**

#### **مکان‌های استفاده**
این تابع در ۴ endpoint از router استفاده می‌شود:
- خط ۳۶۶: `get_governance_health`
- خط ۳۹۹: `get_constitution_health`
- خط ۴۲۱: `get_audit_trail`
- خط ۴۳۹: `get_governance_metrics`

همه به صورت `Depends(require_permissions([Permission.READ]))`

#### **تاثیر**
- **Router کامل governance** (`/api/v1/governance/*`) **غیرفعال** است
- **تنها governance middleware** فعال می‌ماند
- startup **ادامه می‌یابد** (fail-soft)

#### **چرا ادامه می‌یابد؟**
در `api/main.py:463-469`:

```python
# Register Governance Center router (CRITICAL - Constitutional Compliance)
try:
    from api.routers import governance as governance_router
    app.include_router(governance_router.router)
    logger.info("✓ Governance Center router registered at /api/v1/governance")
except ImportError as e:
    logger.warning(f"Governance router not available: {e}")
```

**ImportError گرفته شده و به عنوان WARNING لاگ می‌شود.**

---

### ⚠️ **FINDING-002: NameError در Neo4j Handshake**

| آیتم | مقدار |
|------|-------|
| **Severity** | CRITICAL |
| **File** | `mahoun/graph/neo4j/connection.py:749` |
| **Error** | `NameError: name 'asyncio' is not defined` |
| **Confidence** | CRITICAL |
| **Type** | FACT |

#### **Root Cause**
فایل `mahoun/graph/neo4j/connection.py` **ماژول `asyncio` را import نکرده** اما در چندین جا از آن استفاده می‌کند:

```python
# خطوط ۷۳۹، ۷۴۹، ۷۶۴
# خط ۷۳۹ (در docstring):
Raises: asyncio.TimeoutError

# خط ۷۴۹ (در کد):
result = await asyncio.wait_for(...)

# خط ۷۶۴ (در exception handler):
except asyncio.TimeoutError:
```

**importهای فعلی در این فایل:**
```python
import logging
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TYPE_CHECKING
```

**`import asyncio` وجود ندارد.**

#### **مسیر اجرا**
```
api/main.py:208 → init_neo4j()
  ↓
api/database.py:276 → initialize_canonical_async_driver() → SUCCESS
  ↓
api/database.py:301 → _handshake_neo4j()
  ↓
api/database.py:230 → verify_async_driver_connectivity()
  ↓
mahoun/graph/neo4j/connection.py:749 → asyncio.wait_for() → NameError
```

#### **تاثیر**
- **Phase 1**: درایور Neo4j ساخته می‌شود → ✅ "Canonical async driver initialized successfully"
- **Phase 2**: handshake شکست می‌خورد → ⚠️ "Neo4j unavailable at bolt://localhost:7687. Falling back to non-graph mode"
- **Phase 3**: `init_neo4j()` بدون exception برگشت می‌دهد → ✅ "Neo4j initialized"
- **حالت نهایی**: `neo4j_driver = None`, `GraphConnectionState.enabled = False`

---

### ⚠️ **FINDING-003: معماری Fail-Soft**

| آیتم | مقدار |
|------|-------|
| **Severity** | INFO |
| **File** | `api/database.py:18-22` |
| **Design** | Intentional |
| **Type** | FACT |

#### **شواهد**
در `api/database.py`:

```python
# Neo4j initialization is **fail-soft**: a missing, refused, or
# unauthenticated Neo4j backend must not crash startup. The driver is
# set to ``None`` and :data:`GraphConnectionState` is flipped to
# ``enabled=False / backend="disabled"`` so the rest of the system
# degrades to non-graph mode.
```

#### **تاثیر**
- **خطاهای Neo4j** → fallback به mode غیر-graph
- **خطاهای Router** → ادامه startup با warning
- **سیستم ادامه می‌دهد** حتی با اجزا critical غیرفعال

---

### ⚠️ **FINDING-004: عدم پوشش CI**

| آیتم | مقدار |
|------|-------|
| **Severity** | LOW |
| **Files** | `ci/enforcement/api_database_firewall.py` |
| **Type** | FACT |

#### **چه چیزهایی چک می‌شوند:**
- Import مستقیم `neo4j` در مسیر `api/`
- فراخوانی مستقیم `GraphDatabase.driver()`
- فراخوانی مستقیم `AsyncGraphDatabase.driver()`

#### **چه چیزهایی چک نمی‌شوند:**
- خطاهای import عمومی (مثل `require_permissions`)
- عدم import ماژول‌ها (مثل `asyncio`)
- رفتار runtime و startup
- تست‌های integration

#### **تاثیر**
- این bugها ** توسط CI تشخیص داده نمی‌شوند**
- این کار **بتĵo طراحی** است - CI فقط آنالیز استاتیک انجام می‌دهد

---

## 3. ماژول‌های بدون استفاده در pipelines

### 📁 **از مسیر `mahoun/pipelines/`**

| # | ماژول | نوع | وضعیت | توضیحات |
|---|-------|------|--------|-----------|
| 1 | `advanced_query_enhancement.py` | Query Enhancement | ❌ استفاده‌نشده | - |
| 2 | `build_bm25.py` | BM25 Builder | ❌ استفاده‌نشده | - |
| 3 | `chunker.py` | Chunking | ❌ استفاده‌نشده | - |
| 4 | `data_loader.py` | Data Loading | ❌ استفاده‌نشده | - |
| 5 | `eval_retrieval.py` | Evaluation | ❌ استفاده‌نشده | - |
| 6 | `persian_legal_nlp.py` | NLP | ❌ استفاده‌نشده | **توجه:** `mahoun/nlp/persian_legal_nlp.py` جدا و استفاده شده است |
| 7 | `preprocess.py` | Preprocessing | ❌ استفاده‌نشده | - |
| 8 | `retrieval_cache.py` | Caching | ❌ استفاده‌نشده | - |
| 9 | `retrieve_rag.py` | RAG | ❌ استفاده‌نشده | - |
| 10 | `smart_chunker.py` | Chunking | ❌ استفاده‌نشده | - |
| 11 | `ingestion_pipeline.py` | Pipeline | ❌ استفاده‌نشده | **توجه:** `pipelines/ingestion/pipeline.py` جدا و استفاده شده است |
| 12 | `utils_text.py` | Utilities | ❌ استفاده‌نشده | - |

---

### 📁 **از مسیر `mahoun/pipelines/graph/`**

| # | ماژول | نوع | وضعیت | توضیحات |
|---|-------|------|--------|-----------|
| 1 | `entity_linker.py` | Entity Linking | ❌ استفاده‌نشده | - |

---

### 📁 **از مسیر `mahoun/pipelines/ingestion/`**

| # | ماژول | نوع | وضعیت | توضیحات |
|---|-------|------|--------|-----------|
| 1 | `base_pipeline.py` | Base Pipeline | ⚠️ غیرمستقیم | توسط `pipeline.py` import می‌شود |
| 2 | `chunker_factory.py` | Factory | ❌ استفاده‌نشده | - |
| 3 | `deterministic_id_generator.py` | ID Generation | ❌ استفاده‌نشده | - |
| 4 | `example_integration.py` | Example | ❌ استفاده‌نشده | **توجه:** احتمالاً نمونه کد |
| 5 | **`hardened_paddle_ocr.py`** | OCR | ❌ استفاده‌نشده | **مهم:** در `AGENTS.md` به عنوان OCR سخت‌افزاری گزارش شده |
| 6 | `ingestion_logger.py` | Logging | ❌ استفاده‌نشده | - |
| 7 | `llm_enhanced_parser.py` | Parsing | ❌ استفاده‌نشده | - |
| 8 | `llm_refiner.py` | Refinement | ❌ استفاده‌نشده | - |
| 9 | `nlp_hardening.py` | NLP | ❌ استفاده‌نشده | - |
| 10 | **`ocr_ensemble.py`** | OCR Ensemble | ❌ استفاده‌نشده | **مهم:** در `AGENTS.md` به عنوان سیستم چند موتوره گزارش شده |
| 11 | `ocr_post_processor.py` | OCR Post-Processing | ❌ استفاده‌نشده | - |
| 12 | `ocr_preprocessing.py` | OCR Preprocessing | ❌ استفاده‌نشده | - |
| 13 | `provenance_aware_mapper.py` | Mapping | ❌ استفاده‌نشده | - |
| 14 | `schema_builder.py` | Schema | ❌ استفاده‌نشده | - |
| 15 | `validation_quality.py` | Validation | ❌ استفاده‌نشده | - |

---

### 📁 **از مسیر `mahoun/pipelines/llm/`**

| # | ماژول | نوع | وضعیت | توضیحات |
|---|-------|------|--------|-----------|
| 1 | `__init__.py` | Package Init | ❌ استفاده‌نشده | **توجه:** `ollama_llm.py` در همان مسیر استفاده می‌شود |

---

### 📁 **از مسیر `mahoun/pipelines/vector_store/`**

| # | ماژول | نوع | وضعیت | توضیحات |
|---|-------|------|--------|-----------|
| 1 | `__init__.py` | Package Init | ❌ استفاده‌نشده | **توجه:** `manager.py` و `manager_v2.py` استفاده می‌شوند |

---

## 4. مشکلات راه‌اندازی سیستم

### 🔄 **timeline کامل راه‌اندازی**

| زمان | مولفه | عمل | وضعیت | پیام لاگ |
|------|--------|------|--------|----------|
| T0 | `api/main.py` | Switchboard initialization | ✅ | "Switchboard initialized" |
| T1 | `api/main.py` | Runtime bootstrap | ✅ | "Runtime bootstrap completed" |
| T1a | `bootstrap/runtime.py` | validate_governance_runtime() | ✅ | "Governance runtime validation passed: audit sink is wired" |
| T1b | `bootstrap/runtime.py` | validate_production_reasoning_config() | ✅ | "Production reasoning config validated" |
| T2 | `api/main.py` | Database initialization | START | - |
| T2a | `api/database.py` | initialize_canonical_async_driver() | ✅ | "Initializing canonical async Neo4j driver" |
| T2b | `connection.py:707` | Driver created | ✅ | **"Canonical async driver initialized successfully"** |
| T2c | `api/database.py` | _handshake_neo4j() | START | - |
| T2d | `api/database.py` | verify_async_driver_connectivity() | START | - |
| T2e | `connection.py:749` | asyncio.wait_for() | ❌ | `NameError: name 'asyncio' is not defined` |
| T2f | `connection.py:769` | Re-raise as ConnectionError | ⚠️ | - |
| T2g | `api/database.py:341` | Catch ConnectionError | ⚠️ | **"Neo4j unavailable at bolt://localhost:7687. Falling back to non-graph mode"** |
| T2h | `api/database.py` | Set neo4j_driver=None | ✅ | - |
| T2i | `api/database.py` | Return normally | ✅ | - |
| T3 | `api/main.py:211` | Log status | ✅ | **"Neo4j initialized"** |
| T3a | `api/main.py` | Register routers | START | - |
| T3b | `api/main.py:464` | Import governance router | ❌ | ImportError: require_permissions |
| T3c | `api/main.py:469` | Catch ImportError | ⚠️ | **"Governance router not available"** |
| T4 | `api/main.py` | All initialization | ✅ | "Application startup complete" |

---

### 🎭 **چرا «Neo4j initialized» گمراه‌کننده است؟**

```python
# api/main.py:208-211
if enable_neo4j:
    from api.database import init_neo4j
    await init_neo4j()
    logger.info("✅ Neo4j initialized")
```

**مولفه `init_neo4j()`**:
- ✅ درایور را می‌سازد
- ❌ handshake شکست می‌خورد
- ✅ `neo4j_driver = None` تنظیم می‌کند
- ✅ `GraphConnectionState.set_unavailable()` صدا می‌زند
- ✅ **بدون exception** برگشت می‌دهد

**نتیجه:** لاگ "Neo4j initialized" چاپ می‌شود **حتی وقتی Neo4j غیرفعال است**.

---

## 5. تحلیل عدم استفاده از ماژول‌ها

### 🔍 **چرا این ماژول‌ها استفاده نمی‌شوند؟**

#### **دلیل ۱: ماژول‌های آزمایشی/نمونه**
- `example_integration.py` - احتمالاً کد نمونه
- `ingestion_pipeline.py` - ممکن است نسخه قدیمی باشد

#### **دلیل ۲: ماژول‌های ساخته شده اما اتصال‌نیافته**
- **`hardened_paddle_ocr.py`** - در `AGENTS.md` section 1-G گزارش شده:
  > "OCR — verify current wiring before assuming which path is active"
  > "`mahoun/pipelines/ingestion/hardened_paddle_ocr.py`'s `HardenedPaddleOCR` (checkpoint/resume via `ocr_pdf_hardened()`, document-level Merkle-tree integrity proof)
  > that has, at least once, had **zero production importers**"

- **`ocr_ensemble.py`** - در `AGENTS.md` section 1-D گزارش شده:
  > "`mahoun/pipelines/ingestion/ocr_ensemble.py`'s `OCREnsemble` — a fully built multi-engine-voting OCR system"
  > "Confirmed **zero production importers**"

#### **دلیل ۳: ماژول‌های با کارایی مشابه**
- `chunker.py` و `smart_chunker.py` - در حالی که `enhanced_chunker.py` استفاده می‌شود
- `data_loader.py` - شاید توسط ماژول‌های دیگر جایگزین شده

#### **دلیل ۴: تغییر معماری**
- `persian_legal_nlp.py` در pipelines در حالی که `mahoun/nlp/persian_legal_nlp.py` استفاده می‌شود
- `ingestion_pipeline.py` در root pipelines در حالی که `pipelines/ingestion/pipeline.py` استفاده می‌شود

---

### ⚠️ **هزینه نگهداری ماژول‌های استفاده‌نشده**

| آیتم | تعداد | توضیحات |
|------|--------|-----------|
| **کد مرده** | ~28 ماژول | کدی که اجرا نمی‌شود |
| **حجم کد** | ~۵۰۰۰+ خط | برآورد تقریبی |
| **risks دامنه انفجار** | HIGH | احتمال conflict بین نسخه‌ها |
| **confusion توسعه‌دهندگان** | HIGH | کسی نمی‌داند کدام یک فعال است |
| **سياست‌هاي امنيتي** | MEDIUM | ممکن است آسیب‌پذیری داشته باشند |

---

## 6. همبستگی بین مسائل

### 🔗 **گراف دلیل اصلی**

```
SOURCE-LEVEL BUGS (2 مستقل)
├── FINDING-001: api/routers/governance.py
│   │   import require_permissions (plural)
│   │   ↓
│   │   ImportError: cannot import name 'require_permissions'
│   └── OBSERVED: "Governance router not available"
│
└── FINDING-002: mahoun/graph/neo4j/connection.py
    │   uses asyncio without importing
    │   ↓
    │   NameError: name 'asyncio' is not defined
    │   ↓
    │   raise ConnectionError(...)
    └── OBSERVED: "Neo4j unavailable... Falling back to non-graph mode"
        └── OBSERVED: "Neo4j initialized" (misleading)

ARCHITECTURAL FACTORS
├── ARC-001: Fail-soft design (documented in api/database.py:18-22)
│   ├── Governance router failure → WARNING + continue
│   └── Neo4j handshake failure → degradation + continue
│
└── ARC-002: Different governance layers
    ├── Middleware: MANDATORY (no try-except)
    ├── Runtime: MANDATORY (validated in bootstrap)
    └── Router: OPTIONAL (try-except with warning)

ORPHANED MODULES (28+)
├── Built but never wired:
│   ├── hardened_paddle_ocr.py
│   ├── ocr_ensemble.py
│   └── ... (26 others)
│
└── Cost: Maintenance burden, confusion, potential bugs
```

---

## 7. شواهد دقیق

### 📄 **FINDING-001: Governance Router Import Error**

#### **File: api/routers/governance.py**
```python
# Line 16
from mahoun.security.rbac import require_permissions, Permission

# Lines 366, 399, 421, 439
_ = Depends(require_permissions([Permission.READ]))
```

#### **File: mahoun/security/rbac.py**
```python
# Lines 24-31: Permission Enum exists
class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"
    ANONYMIZE = "anonymize"

# Line 217-235: require_permission method (singular) exists
class RBACManager:
    def require_permission(self, username: str, permission: Permission):
        ...

# Lines 359-384: require_permission decorator (singular) exists
def require_permission(permission: Permission):
    ...

# NO: require_permissions (plural) does NOT exist
```

#### **File: api/main.py (Handling)**
```python
# Lines 462-470
# Register Governance Center router (CRITICAL - Constitutional Compliance)
try:
    from api.routers import governance as governance_router
    app.include_router(governance_router.router)
    logger.info("✓ Governance Center router registered at /api/v1/governance")
except ImportError as e:
    logger.warning(f"Governance router not available: {e}")
```

---

### 📄 **FINDING-002: Asyncio NameError**

#### **File: mahoun/graph/neo4j/connection.py (Imports)**
```python
# Lines 8-13: NO asyncio import
import logging
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TYPE_CHECKING
```

#### **File: mahoun/graph/neo4j/connection.py (Usage)**
```python
# Line 739 (docstring)
Raises:
    asyncio.TimeoutError: If connectivity check times out

# Line 749 (code)
result = await asyncio.wait_for(
    initializer.initialize_with_governance(...),
    timeout=timeout_sec
)

# Line 764 (exception handler)
except asyncio.TimeoutError:
    _conn_logger.error(f"❌ Async driver connectivity check timed out after {timeout_sec}s")
    raise
```

#### **File: api/database.py (Handling)**
```python
# Lines 332-353
except (
    _Neo4jServiceUnavailable,
    _Neo4jAuthError,
    _Neo4jBoltError,
    ConnectionError,
    OSError,
) as conn_err:
    log.warning(
        f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
        f"Reason: {type(conn_err).__name__}: {conn_err}"
    )
    GraphConnectionState.set_unavailable(
        reason=f"{type(conn_err).__name__}: {conn_err}",
        uri=uri,
    )
    _update_graph_metric(enabled=False)
    try:
        await neo4j_driver.close()
    except Exception:
        pass
    neo4j_driver = None
    return
```

---

## 8. سوال‌های بی‌پاسخ

### ❓ **سوال‌های بحرانی**

1. **سوال ۱: آیا `require_permissions` (plural) به عمد طراحی شده بود؟**
   - آیا این یک API جدید است که هرگز پیاده‌سازی نشد؟
   - یا یک اشتباه تایپی ساده است؟

2. **سوال ۲: چرا `asyncio` در `connection.py` import نشده؟**
   - آیا این عمدی بوده (برای جلوگیری از import سنگین)؟
   - یا یک اشتباه ساده است؟

3. **سوال ۳: آیا معماری fail-soft با اصل fail-closed تناقض دارد؟**
   - CONSTITUTION.md Section 10: "Fail-Closed Principle: missing/failed verification evidence is a blocking condition"
   - آیا باید این خطاها باعث stop شدن startup شوند؟

4. **سوال ۴: آیا ماژول‌های استفاده‌نشده اعم از:
   - `hardened_paddle_ocr.py`
   - `ocr_ensemble.py`
   باید فعال شوند یا حذف گردند؟

5. **سوال ۵: چرا CI این مشکلات را تشخیص نمی‌دهد؟**
   - آیا باید تست‌های runtime اضافه شوند؟
   - آیا باید گیت‌های جدیدی برای import validation اضافه شوند؟

---

### ❓ **سوال‌های معماری**

6. **سوال ۶: آیا governance router باید mandatory باشد؟**
   - comment در کد می‌گوید "CRITICAL" ولی کد آن را optional در نظر می‌گیرد

7. **سوال ۷: آیا Neo4j باید در حالت عدم دسترس بودن باعث stop شدن startup شود؟**
   - document در `api/database.py` می‌گوید fail-soft intentional است

8. **سوال ۸: آیا لاگ "Neo4j initialized" باید اصلاح شود؟**
   - آیا باید به "Neo4j initialization attempted" یا "Neo4j initialization completed (degraded)" تغییر کند؟

---

## 9. پیشنهادات برای تحقیقات بعدی

### 🔍 **اولویت ۱: تایید منبع حقیقت**
```bash
# بررسی تاریخچه تغییرات
git blame api/routers/governance.py
.git blame mahoun/graph/neo4j/connection.py
```

### 🔍 **اولویت ۲: بررسی ماژول‌های استفاده‌نشده**
```bash
# بررسی هر ماژول برای یافتن دلیل عدم استفاده
# مثال برای hardened_paddle_ocr:
grep -rn "HardenedPaddleOCR\|hardened_paddle_ocr" --include="*.py" .
```

### 🔍 **اولویت ۳: بررسی انسجام معماری**
```bash
# بررسی CONSTITUTION.md برای اصول fail-closed
cat mahoun/constitutional/constitution/CONSTITUTION.md | grep -A 10 "Fail-Closed"
```

### 🔍 **اولویت ۴: بررسی پوشش تست**
```bash
# یافتن تست‌ها برای init_neo4j
grep -rn "init_neo4j\|verify_async_driver_connectivity" tests/
```

### 🔍 **اولویت ۵: بررسی Switchboard**
```bash
# دیدن تمام ماژول‌های ثبت شده
cat mahoun/switchboard.py | grep "switchboard.register"
```

---

## 📌 **خلاصه نهایی**

| دسته | تعداد | شدت | وضعیت |
|------|--------|------|--------|
| **خطاهای import** | 2 | CRITICAL | کشف شده |
| **ماژول‌های استفاده‌نشده** | 28+ | HIGH | کشف شده |
| **حالت‌های متضاد** | 1 | MEDIUM | توضیح داده شده |
| **عدم پوشش CI** | 1 | LOW | کشف شده |

**تعداد کل یافتن‌ها:** 4 دسته اصلی با 31+ مورد خاص

---

### ✅ **تضمین**

**هیچ تغییری در کد، محیط، یا حالت runtime ایجاد نشد.**

این گزارش صرفاً بر اساس **تحلیل کد منبع** و **شواهد مستقیم** تهیه شده است.

---

*این گزارش در تاریخ 1405/05/25 (2026-08-15) تهیه شده است.*
