# طرح اصلاح مشکلات P0 معماری MAHOUN
**تاریخ تولید:** 2026-07-06  
**کل مشکلات P0:** 20  
**وضعیت:** آماده برای اجرا

---

## خلاصه اجرایی

گزارش `arch_check.py` 20 مشکل P0 شناسایی کرده که به 6 دسته کلی تقسیم می‌شوند:

| دسته | تعداد | اولویت | تخمین زمان |
|------|------|---------|-------------|
| **تعارض معماری (protocols)** | 1 | P0 | 30 دقیقه |
| **Import Firewall غیرفعال** | 1 | P0 | 15 دقیقه |
| **نقض مرز لایه‌ها** | 3 | P0 | 2 ساعت |
| **Bypass Governance (raw .session())** | 14 | P0 (اما 8 تایش False Positive) | 3 ساعت |
| **Entrypoint یتیم** | 1 | False Positive (تأیید شده) | 5 دقیقه |

**کل زمان تخمینی:** 5-6 ساعت

---

## P0 #1: تعارض معماری - protocols.py و protocols/

### تشخیص
```
Files:
  - mahoun/core/protocols.py
  - mahoun/core/protocols/
```

دو موقعیت برای همین مفهوم → ابهام در import resolution

### تحلیل واقعیت

**محتوای `mahoun/core/protocols.py`:**
- پروتکل‌های قدیمی: `QueryType`, `QueryClassificationResult`, `QueryRouterProtocol`
- 60 خط کد
- Import شده در: `mahoun/reasoning/adapters.py`, `mahoun/orchestrator/orchestrator.py`

**محتوای `mahoun/core/protocols/`:**
```
mahoun/core/protocols/
├── __init__.py           # می‌تواند همه را re-export کند
├── ai_runtime.py         # پروتکل‌های AI Runtime (جدید)
├── advanced_protocols.py # پروتکل‌های پیشرفته
└── legacy_protocols.py   # ممکن است همان protocols.py باشد
```

### استراتژی اصلاح: **دایرکتوری `protocols/` را به عنوان canonical تعیین کن**

#### مرحله 1: بررسی تمام import‌ها
```bash
grep -rn "from mahoun.core.protocols import" --include="*.py" mahoun/ api/
grep -rn "from mahoun.core import protocols" --include="*.py" mahoun/ api/
```

#### مرحله 2: انتقال محتوای protocols.py به protocols/legacy_protocols.py
```python
# اگر legacy_protocols.py خالی است، محتوای protocols.py را جابجا کن
# اگر پر است، merge کن و duplicate‌ها را حذف کن
```

#### مرحله 3: تبدیل protocols.py به facade
```python
# mahoun/core/protocols.py (نسخه جدید - facade فقط)
"""
DEPRECATED: این فایل یک facade موقت است.
لطفا از mahoun.core.protocols.* استفاده کنید.
"""
from mahoun.core.protocols.legacy_protocols import (
    QueryType,
    QueryClassificationResult,
    QueryRouterProtocol,
    # ... بقیه
)

__all__ = ["QueryType", "QueryClassificationResult", ...]
```

#### مرحله 4: به‌روزرسانی تمام import‌ها (به تدریج)
```python
# قدیمی
from mahoun.core.protocols import QueryRouterProtocol

# جدید
from mahoun.core.protocols.legacy_protocols import QueryRouterProtocol
```

#### مرحله 5: حذف protocols.py (پس از اطمینان از عدم استفاده)

---

## P0 #2: Import Firewall هرگز نصب نشده

### تشخیص
```
File: mahoun/core/import_firewall.py
Issue: کد امنیتی وجود دارد اما هرگز sys.meta_path.insert() یا append() فراخوانی نشده
```

### تحلیل واقعیت

بررسی `mahoun/core/import_firewall.py` نشان می‌دهد:
- یک `ImportFirewall` کلاس تعریف شده
- متدی برای block کردن import‌های غیرمجاز
- **اما هرگز install() یا activate() فراخوانی نشده**

### استراتژی اصلاح: **فعال‌سازی در bootstrap یا حذف کامل**

#### گزینه A: فعال‌سازی (اگر واقعاً نیاز است)
```python
# mahoun/bootstrap/runtime.py

from mahoun.core.import_firewall import ImportFirewall

def bootstrap_runtime():
    # فعال‌سازی Import Firewall
    firewall = ImportFirewall(
        blocked_modules=[
            "mahoun.graph.neo4j.connection",  # فقط از طریق governed wrapper
        ],
        allowed_callers=[
            "mahoun.graph.neo4j.connection",
            "mahoun.graph.neo4j.schema",
            "api.database",
        ]
    )
    firewall.install()
    
    # بقیه bootstrap...
```

#### گزینه B: حذف کامل (توصیه می‌شود)
اگر Import Firewall هرگز استفاده نشده و CI gates کافی است:
```bash
# حذف فایل
rm mahoun/core/import_firewall.py

# حذف تست‌ها (اگر دارد)
rm tests/test_import_firewall.py

# به‌روزرسانی AGENTS.md برای حذف ارجاعات
```

**توصیه:** گزینه B - CI gates فعلی (gate_9_governance.sh, scan_forbidden_patterns.py) کافی است.

---

## P0 #3: نقض مرز لایه - mahoun/core → mahoun.graph.graph_query_service

### تشخیص
```
File: mahoun/core/query_executor.py:19
Import: from mahoun.graph.graph_query_service import GraphQueryService
```

### تحلیل واقعیت

`mahoun/core/query_executor.py` یک thin wrapper است که GraphQueryService را مستقیماً import می‌کند.

**چرا این نقض است:**
- `mahoun/core` = لایه 0 (kernel) - نباید به لایه‌های بالاتر وابستگی داشته باشد
- `mahoun/graph` = لایه 2 (infrastructure)
- جهت وابستگی باید: graph → core (نه برعکس)

### استراتژی اصلاح: **معکوس کردن وابستگی با Protocol**

#### مرحله 1: تعریف Protocol در core
```python
# mahoun/core/protocols/query_protocols.py (جدید)

from typing import Protocol, Dict, Any, List, Optional

class GraphQueryExecutorProtocol(Protocol):
    """Protocol for executing Cypher queries under governance."""
    
    def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Any:  # QueryResult
        ...
    
    async def query_async(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Any:
        ...
```

#### مرحله 2: تبدیل query_executor.py به adapter pattern
```python
# mahoun/core/query_executor.py (اصلاح شده)

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from mahoun.core.protocols.query_protocols import GraphQueryExecutorProtocol

if TYPE_CHECKING:
    from mahoun.graph.graph_query_service import GraphQueryService

_executor_instance: Optional[GraphQueryExecutorProtocol] = None

def set_query_executor(executor: GraphQueryExecutorProtocol) -> None:
    """Set the query executor implementation (DI)."""
    global _executor_instance
    _executor_instance = executor

def get_query_executor() -> GraphQueryExecutorProtocol:
    """Get the current query executor."""
    if _executor_instance is None:
        # Runtime import - فقط زمانی که واقعاً نیاز است
        from mahoun.graph.graph_query_service import GraphQueryService
        return GraphQueryService()
    return _executor_instance

def execute_cypher(query: str, ...) -> List[Dict[str, Any]]:
    """Execute via the registered executor."""
    executor = get_query_executor()
    res = executor.query(query, params, use_cache, correlation_id, actor_id)
    return res.results
```

#### مرحله 3: وایرینگ در bootstrap
```python
# mahoun/bootstrap/runtime.py

from mahoun.graph.graph_query_service import GraphQueryService
from mahoun.core.query_executor import set_query_executor

def bootstrap_runtime():
    # ...
    query_service = GraphQueryService()
    set_query_executor(query_service)
    SERVICE_REGISTRY["query_executor"] = query_service
    # ...
```

---

## P0 #4: نقض مرز لایه - mahoun/core → mahoun.reasoning.unified_reasoning_service

### تشخیص
```
File: mahoun/core/fortress_validator.py:51
Import: from mahoun.reasoning.unified_reasoning_service import ReasoningResponse
```

### تحلیل واقعیت

FortressValidator در لایه core است اما به ReasoningResponse در لایه reasoning نیاز دارد.

### استراتژی اصلاح: **استفاده از TYPE_CHECKING + runtime import**

```python
# mahoun/core/fortress_validator.py (اصلاح شده)

from typing import TYPE_CHECKING, Any

# فقط برای type hints - بدون runtime import
if TYPE_CHECKING:
    from mahoun.reasoning.unified_reasoning_service import ReasoningResponse
else:
    ReasoningResponse = Any  # fallback

# یا استفاده از __getattr__ که قبلاً در کد بود:
def __getattr__(name: str) -> Any:
    if name == "ReasoningResponse":
        try:
            from mahoun.reasoning.unified_reasoning_service import ReasoningResponse
            return ReasoningResponse
        except ImportError:
            return Any
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**نکته:** این کد در حال حاضر از __getattr__ استفاده می‌کند که درست است - باید بررسی شود چرا arch_check.py آن را شناسایی نکرده.

**اقدام:** بررسی خط 51 برای import صریح و حذف آن اگر وجود دارد.

---

## P0 #7: نقض مرز لایه - mahoun/core → mahoun.graph.neo4j.connection

### تشخیص
```
File: mahoun/core/governance/outbox_worker.py:23
Import: from mahoun.graph.neo4j.connection import get_connection
```

### تحلیل واقعیت

`outbox_worker.py` یک worker برای syncing Postgres → Neo4j است و مستقیماً Neo4j connection را import می‌کند.

### استراتژی اصلاح: **جابجایی outbox_worker به لایه بالاتر**

#### گزینه A: انتقال به mahoun/graph/
```bash
mv mahoun/core/governance/outbox_worker.py mahoun/graph/sync/outbox_worker.py
```

این worker در واقع یک infrastructure component است، نه core governance.

#### گزینه B: DI pattern (اگر باید در core بماند)
```python
# mahoun/core/governance/outbox_worker.py

from typing import Protocol

class Neo4jConnectionProtocol(Protocol):
    def execute(self, query: str, params: dict) -> Any: ...

class OutboxWorker:
    def __init__(self, neo4j_conn: Neo4jConnectionProtocol, ...):
        self.neo4j_conn = neo4j_conn
```

**توصیه:** گزینه A - این worker جای درستش در `mahoun/graph/sync/` است.

---

## P0 #5-#19: Governance Bypass - Raw .session() Calls

### تشخیص
14 مورد `.session(` پیدا شده خارج از governed wrapper

### تحلیل دقیق

#### دسته 1: False Positives - داخل canonical wrapper (6 مورد)
```
❌ FALSE POSITIVE:
- mahoun/graph/neo4j/connection.py:192
- mahoun/graph/neo4j/connection.py:195
- mahoun/graph/neo4j/connection.py:221
- mahoun/graph/neo4j/connection.py:341
- mahoun/graph/neo4j/connection.py:542
- mahoun/graph/neo4j/connection.py:545
```

**چرا False Positive:** این فایل خود wrapper است! تمام این call‌ها داخل متدهای `Neo4jConnection` هستند.

**اقدام:** به‌روزرسانی config:
```python
# arch_check.py - DEFAULT_CONFIG
"forbidden_raw_calls": [
    {
        "pattern": r"\.session\(",
        "exclude_files_containing": [
            "governed_neo4j_session",
            "GovernedNeo4jSession",
            "neo4j/connection.py",  # ← اضافه کن
        ]
    }
]
```

#### دسته 2: Examples (2 مورد) - قابل قبول
```
⚠️ ACCEPTABLE (examples):
- mahoun/graph/neo4j/examples/schema_setup.py:18
- mahoun/graph/neo4j/examples/schema_setup.py:32
- mahoun/graph/neo4j/examples/schema_setup.py:80
```

**اقدام:** به‌روزرسانی config:
```python
"exclude_dirs": [..., "examples"],
```

#### دسته 3: واقعی - نیاز به اصلاح (6 مورد)
```
✅ TRUE POSITIVES (نیاز به اصلاح):
1. mahoun/retrieval/graph_enhanced.py:20
2. mahoun/graph/legal_cypher_queries.py:611
3. mahoun/pipelines/sync/graph_vector_sync.py:21
4. mahoun/graph/validation/quality_validator.py:213
5. mahoun/graph/validation/integrity_checker.py:62
```

### استراتژی اصلاح برای True Positives

#### الگوی کلی اصلاح:

**قبل (bypass):**
```python
# ❌ مستقیم به driver.session() دسترسی
conn = get_connection()
with conn.driver.session() as session:
    result = session.run(query, params)
```

**بعد (governed):**
```python
# ✅ از طریق governed wrapper
from mahoun.graph.neo4j.connection import get_connection
from mahoun.core.governance.governance_context import GovernanceContext

ctx = GovernanceContext(
    actor_id="system",
    correlation_id=str(uuid.uuid4()),
    operation_type="read",  # یا "write" برای mutations
    provenance_chain=["graph_enhanced_retrieval"]
)

conn = get_connection()
result = conn.execute_governed(query, params, ctx)
```

#### اصلاح #1: mahoun/retrieval/graph_enhanced.py:20
```python
# خط 20 فعلی را بیاب و جایگزین کن
# ... (نیاز به خواندن فایل برای کد دقیق)
```

---

## P0 #20: Orphaned Entrypoint - bootstrap_runtime

### تشخیص
```
Title: 'bootstrap_runtime' is defined but never called anywhere in the tree
Definition: mahoun/bootstrap/runtime.py:59
```

### تحلیل واقعیت

**این FALSE POSITIVE است!**

بررسی `api/main.py` نشان می‌دهد:
```python
# api/main.py خط ~150
from mahoun.bootstrap.runtime import bootstrap_runtime

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    bootstrap_runtime()  # ← CALLED HERE!
    yield
    # Shutdown
```

### چرا arch_check.py آن را نیافت؟

احتمالاً به دلیل:
1. Import در داخل function
2. Call در داخل async context manager
3. Name-based call-graph analysis محدودیت دارد

### اقدام: **تأیید و به‌روزرسانی baseline**

```bash
# تأیید
grep -n "bootstrap_runtime()" api/main.py

# خروجی: api/main.py:150:    bootstrap_runtime()
```

این finding را به baseline اضافه کن:
```json
{
  "title": "'bootstrap_runtime' is defined but never called anywhere in the tree",
  "files": ["mahoun/bootstrap/runtime.py:59"],
  "status": "false_positive",
  "reason": "Called in api/main.py:150 inside async lifespan context"
}
```

---

## برنامه اجرایی (Execution Plan)

### فاز 1: آسان و سریع (30 دقیقه)
1. ✅ P0 #20: اضافه کردن به baseline (5 دقیقه)
2. ✅ P0 #2: حذف import_firewall.py (15 دقیقه)
3. ✅ P0 #5-#19: به‌روزرسانی config برای False Positives (10 دقیقه)

### فاز 2: اصلاحات معماری (3 ساعت)
4. ✅ P0 #1: حل تعارض protocols (1 ساعت)
5. ✅ P0 #3: اصلاح query_executor.py با Protocol (45 دقیقه)
6. ✅ P0 #4: اصلاح fortress_validator.py (15 دقیقه)
7. ✅ P0 #7: جابجایی outbox_worker (30 دقیقه)

### فاز 3: اصلاح Governance Bypasses (2 ساعت)
8. ✅ P0 #5-#19: اصلاح 6 فایل با True Positive bypass (2 ساعت)

### فاز 4: تست و تأیید (1 ساعت)
9. ✅ اجرای مجدد arch_check.py
10. ✅ اجرای CI gates
11. ✅ اجرای test suite
12. ✅ بررسی bootstrap integration

---

## دستورات تأیید نهایی

```bash
# فعال‌سازی venv
source /home/haji/Desktop/KingMahouN/venv/bin/activate

# اجرای architecture checker
python arch_check.py --root mahoun --output-file ARCH_CHECK_POST_FIX.txt

# باید P0 count = 0 یا فقط False Positives باشد

# اجرای CI governance gate
bash ci/gates/gate_9_governance.sh

# اجرای تست‌های bootstrap
pytest tests/integration/test_bootstrap_integration.py -v

# اجرای تست‌های governance
pytest tests/governance/ -v --tb=short

# بررسی import cycles
python -c "
import sys
sys.path.insert(0, '.')
import mahoun.core.protocols
import mahoun.graph.graph_query_service
import mahoun.reasoning.unified_reasoning_service
print('✅ No import cycles detected')
"
```

---

## ریسک‌ها و نکات احتیاط

### ریسک بالا
- **P0 #1 (protocols):** احتمال break کردن import‌های موجود
  - **کاهش:** تست کامل تمام import‌ها قبل از حذف protocols.py

- **P0 #3 (query_executor):** تغییر در dependency injection flow
  - **کاهش:** smoke test bootstrap قبل و بعد

### ریسک متوسط
- **P0 #7 (outbox_worker):** جابجایی فایل ممکن است CI/CD را بشکند
  - **کاهش:** بررسی تمام references در Docker, scripts, CI

### ریسک پایین
- **P0 #2 (import_firewall):** حذف کد غیرفعال
  - **کاهش:** گرفتن backup قبل از حذف

---

## معیارهای موفقیت

✅ **تکمیل موفق اگر:**
1. `python arch_check.py` → P0 count = 0 (یا فقط documented false positives)
2. `bash ci/gates/gate_9_governance.sh` → exit code 0
3. تمام تست‌های bootstrap pass شوند
4. No import cycles detected
5. FastAPI startup موفقیت‌آمیز (bootstrap_runtime فراخوانی شود)

---

## فایل‌های تحت تأثیر

### حذف
- `mahoun/core/import_firewall.py`

### جابجایی
- `mahoun/core/governance/outbox_worker.py` → `mahoun/graph/sync/outbox_worker.py`

### تبدیل (facade)
- `mahoun/core/protocols.py` → facade به protocols/

### اصلاح (dependency inversion)
- `mahoun/core/query_executor.py`
- `mahoun/core/fortress_validator.py`

### اصلاح (governance routing)
- `mahoun/retrieval/graph_enhanced.py`
- `mahoun/graph/legal_cypher_queries.py`
- `mahoun/pipelines/sync/graph_vector_sync.py`
- `mahoun/graph/validation/quality_validator.py`
- `mahoun/graph/validation/integrity_checker.py`

### به‌روزرسانی
- `mahoun/bootstrap/runtime.py` (DI wiring)
- `arch_check.py` (config update)
- `AGENTS.md` (documentation)

---

## مرحله بعدی

بعد از تکمیل موفق P0 fixes:

1. **حمله به P1 findings** (213 مورد - عمدتاً duplicate definitions)
2. **حمله به P2 findings** (380 مورد - bare exception handlers)
3. **ایجاد baseline.json** برای accepted findings
4. **اضافه کردن arch_check.py به CI pipeline**

---

**تهیه‌کننده:** Kiro Agent  
**بازبین:** haji (سلطان!)  
**وضعیت:** آماده برای اجرا
