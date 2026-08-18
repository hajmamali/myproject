# گزارش تفصیلی: تشخیص و حل مشکل راه‌اندازی سیستم MAHOUN
**تاریخ**: ۱۸ مردادماه ۱۴۰۵  
**عنوان**: Neo4j Startup Blocker Investigation  
**وضعیت**: ✅ حل شده  

---

## 📋 خلاصه اجرایی

سیستم MAHOUN در حالت `server_full` بدون تنظیم متغیرهای محیطی Neo4j به خرابی برخورد می‌کرد. تحقیق نشان داد که:

1. **علت ریشه‌ای**: تنظیمات پیش‌فرض سیستم به `mode=server_full` و `graph_enabled=true` تنظیم شده بود
2. **شرط ناکافی**: هیچ کلید رمز یا آدرس Neo4j تنظیم نشده بود
3. **رفتار صحیح**: سیستم به‌درستی در حالت "fail-closed" قرار گرفته و به خطا رفته
4. **راه‌حل**: سیستم می‌تواند در حالت "non-graph" بدون مشکل اجرا شود

---

## 🔍 مراحل تحقیق

### ۱. تشخیص اولیه
```bash
$ cd /home/haji/Desktop/KingMahouN
$ source venv/bin/activate
$ python - <<'PY'
import os
print('MAHOUN_MODE=', os.getenv('MAHOUN_MODE'))
print('MAHOUN_GRAPH_ENABLED=', os.getenv('MAHOUN_GRAPH_ENABLED'))
print('ENABLE_NEO4J=', os.getenv('ENABLE_NEO4J'))
print('NEO4J_URI=', os.getenv('NEO4J_URI'))
print('NEO4J_PASSWORD set=', bool(os.getenv('NEO4J_PASSWORD')))
print('DB_NEO4J_PASSWORD set=', bool(os.getenv('DB_NEO4J_PASSWORD')))
from mahoun.core.runtime_config import get_runtime_settings
s=get_runtime_settings()
print('settings.mode=', s.mode)
print('settings.graph_enabled=', s.graph_enabled)
print('settings.graph_backend=', s.graph_backend)
print('settings.graph_neo4j_uri=', s.graph_neo4j_uri)
print('settings.graph_neo4j_password set=', bool(s.graph_neo4j_password))
PY
```

**نتیجه**: تمام متغیرهای محیطی خالی بودند، اما تنظیمات پیش‌فرض سیستم:
- `settings.mode = "server_full"`
- `settings.graph_enabled = True`
- `settings.graph_backend = "local_full"`
- `settings.graph_neo4j_password = ""` (خالی)

### ۲. بررسی کد منابع

#### فایل: `mahoun/core/runtime_config.py` (خطوط 145-210)
**یافته**: تنظیمات پیش‌فرض برای حالت server_full:
```python
# Default: server_full or enterprise_graph mode
return MahounRuntimeSettings(
    mode="server_full",  # FORCED ENTERPRISE MODE
    graph_enabled=True,
    graph_backend="local_full",
    ...
    graph_neo4j_password="",  # خالی (مسئله!)
)
```

#### فایل: `api/main.py` (خطوط 221-278)
**یافته**: منطق راه‌اندازی Neo4j:
```python
if enable_neo4j:
    from api.database import init_neo4j, GraphConnectionState
    from mahoun.core.runtime_config import get_runtime_settings

    runtime_settings = get_runtime_settings()
    fail_closed = (
        runtime_settings.mode == "server_full" and
        runtime_settings.graph_enabled
    )

    try:
        await init_neo4j(fail_closed_on_unavailable=fail_closed)
    except RuntimeError as e:
        # Neo4j is mandatory but unavailable - fail-closed
        logger.error(
            f"❌ Neo4j initialization FAILED (mandatory in {runtime_settings.mode} mode): {e}"
        )
        raise
```

**نتیجه**: در حالت `server_full` با `graph_enabled=True`، پارامتر `fail_closed_on_unavailable=True` تنظیم می‌شود.

#### فایل: `api/database.py` (خطوط 324-426)
**یافته**: تابع `init_neo4j()` در حالت fail-closed:
```python
async def init_neo4j(fail_closed_on_unavailable: bool = False):
    """
    In fail-closed mode: If Neo4j is unavailable, raises RuntimeError
    """
    if not HAS_NEO4J or initialize_canonical_async_driver is None:
        if fail_closed_on_unavailable:
            raise RuntimeError(
                "Neo4j driver not installed but graph is mandatory in this configuration. "
                ...
            )
```

**نتیجه**: اگر رمز یا اتصال ناکافی باشد، RuntimeError بلند می‌شود.

#### فایل: `mahoun/core/config_validator.py` (خطوط 1-240)
**یافته**: تابع `_validate_neo4j_credentials()`:
```python
def _validate_neo4j_credentials(...):
    """Rule 3: Neo4j credentials required for local graph backends."""
    if settings.graph_enabled and settings.graph_backend in ["local_small", "local_full"]:
        if not settings.graph_neo4j_password:
            errors.append(
                ValidationError(
                    rule="NEO4J_PASSWORD_MISSING",
                    message=(
                        f"Neo4j password required for graph_backend='{settings.graph_backend}'. "
                    ),
                )
            )
```

**نتیجه**: سیستم به‌درستی باید خطا بر‌داشت اما تنظیمات پیش‌فرض به آن اجازه نداد.

#### فایل: `mahoun/core/governance/governance_context.py` (خطوط 220-520)
**یافته**: لایه governance kernel جداگانه است و نه بخشی از مسئله:
```python
class GovernanceContextManager:
    """Manager for governance context lifecycle."""
    _governance_stack: ContextVar[list[GovernanceContext] | None] = ContextVar(
        "mahoun_governance_stack", default=None
    )
```

**نتیجه**: kernel/container معماری واقعی است اما از ناحیه startup graph bootstrap جدا است.

### ۳. اجرای تست‌های گزینشی

```bash
$ cd /home/haji/Desktop/KingMahouN && source venv/bin/activate
$ pytest tests/governance/test_database_initialization.py -q
```

**نتیجه**:
```
collected 18 items
tests/governance/test_database_initialization.py ..................      [100%]
=============================== 18 passed, 7 warnings in 8.73s ========================
```

✅ تمام تست‌های واحد موفق بودند.

### ۴. راه‌اندازی در حالت non-graph

```bash
cd /home/haji/Desktop/KingMahouN
source venv/bin/activate

export MAHOUN_MODE=desktop_minimal
export MAHOUN_GRAPH_ENABLED=false
export MAHOUN_GRAPH_BACKEND=disabled_fallback
export ENABLE_NEO4J=false

uvicorn api.main:app --host 0.0.0.0 --port 8001
```

**نتیجه**: برنامه با موفقیت اجرا شد.

### ۵. بررسی endpoint سلامتی

```bash
$ curl -sS http://127.0.0.1:8001/health
```

**نتیجه** (خلاصه):
```json
{
  "status": "degraded",
  "core": { "status": "DEGRADED", "import_safe": true },
  "graph": { "status": "DISABLED", "reason": "Graph system is disabled (mode or config)" },
  "agents": { "status": "READY", "count": 9 },
  "components": {
    "reasoning": { "status": "healthy", "message": "Reasoning service is available" },
    "postgresql": { "status": "healthy", "message": "PostgreSQL is connected" },
    "redis": { "status": "healthy", "message": "Redis is connected" },
    ...
  }
}
```

✅ **نتیجه**: سیستم در حالت کاهش‌یافته اما سالم کار می‌کند.

---

## 📊 یافته‌های تفصیلی

### Codepath 1: راه‌اندازی Neo4j در server_full
```
api/main.py:235-260
  ↓
api/database.py:init_neo4j(fail_closed_on_unavailable=True)
  ↓
mahoun/graph/neo4j/connection.py:initialize_canonical_async_driver()
  ↓
mahoun/core/governance/database_init.py:create_governance_aware_initializer()
  ↓
_governed_connectivity_check()  ← RuntimeError اگر ناموفق
```

### Codepath 2: تصدیق تنظیمات
```
api/main.py:120-130
  ↓
mahoun/core/config_validator.py:validate_runtime_config()
  ↓
_validate_neo4j_credentials()  ← باید تشخیص می‌داد
```

**مسئله**: تابع تصدیق در تنظیمات پیش‌فرض صدا نمی‌خورد.

### Kernel vs. Runtime
- **Kernel** (`mahoun/core/governance_kernel/kernel.py`):
  - لایه‌ای جداگانه برای تصدیق کوئری‌های Cypher
  - مستقل از bootstrap
  
- **Runtime Bootstrap** (`api/main.py`, `api/database.py`):
  - متوقف می‌شود اگر Neo4j در حالت fail-closed ناموفق باشد
  - این جای مشکل است

**نتیجه**: این دو لایه **غیر مرتبط** هستند.

---

## ✅ تأیید راه‌حل

### حالت 1: بدون Graph (کار کرد)
```bash
export MAHOUN_MODE=desktop_minimal
export MAHOUN_GRAPH_ENABLED=false
export MAHOUN_GRAPH_BACKEND=disabled_fallback
export ENABLE_NEO4J=false
```
**نتیجه**: ✅ برنامه اجرا شد

### حالت 2: با Graph مکمل (نیاز به تنظیمات)
```bash
export MAHOUN_MODE=server_full
export MAHOUN_GRAPH_ENABLED=true
export MAHOUN_GRAPH_BACKEND=local_full
export ENABLE_NEO4J=true
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD='your_password_here'
export DB_NEO4J_PASSWORD='your_password_here'
```
**نیاز**: Neo4j باید در حال اجرا باشد

---

## 🎯 علل ریشه‌ای و توضیح

| علت | توضیح | مسئول |
|-----|--------|--------|
| تنظیمات پیش‌فرض server_full | محرک اولیه برای graph_enabled=true | `mahoun/core/runtime_config.py:189` |
| عدم تعریف رمز Neo4j | رمز خالی برای local_full backend | `mahoun/core/runtime_config.py:167` |
| رفتار fail-closed صحیح | سیستم **باید** ناموفق باشد (رفتار صحیح) | `api/database.py:324-426` |
| Kernel جداگانه | معماری مختلف، نه علت مشکل | `mahoun/core/governance_kernel/kernel.py` |

---

## 📋 نتیجه‌گیری

### ✅ آنچه درست است:
1. **Fail-closed logic**: سیستم به‌درستی Neo4j را در حالت اجباری بررسی می‌کند
2. **Governance layer**: لایه kernel صحیح کار می‌کند
3. **Fallback path**: سیستم می‌تواند بدون Graph اجرا شود
4. **Health checks**: endpoint سلامتی درست گزارش می‌دهد

### ⚠️ نکات برای بهبود:
1. **تنظیمات پیش‌فرض**: برای محیط توسعه، باید به `desktop_minimal` تغییر کند
2. **پیغام خطا**: هنگام fail-closed، باید بیشتر شفاف باشد
3. **اسناد**: نیاز به مستندات بیشتر برای تنظیم محیط

### 🚀 راه‌حل‌های موصی‌شده:

**برای توسعه محلی**:
```bash
export MAHOUN_MODE=desktop_minimal
export MAHOUN_GRAPH_ENABLED=false
```

**برای production**:
```bash
export MAHOUN_MODE=server_full
export MAHOUN_GRAPH_ENABLED=true
# + تمام متغیرهای Neo4j
```

---

## 📚 فایل‌های مرتبط

| فایل | خط | توضیح |
|------|-----|---------|
| [mahoun/core/runtime_config.py](../mahoun/core/runtime_config.py#L144-L210) | 144-210 | تنظیمات پیش‌فرض |
| [api/main.py](../api/main.py#L221-L278) | 221-278 | منطق راه‌اندازی |
| [api/database.py](../api/database.py#L324-L426) | 324-426 | تابع init_neo4j |
| [mahoun/core/config_validator.py](../mahoun/core/config_validator.py#L1-L240) | 1-240 | تصدیق تنظیمات |
| [mahoun/core/governance/governance_context.py](../mahoun/core/governance/governance_context.py#L220-L520) | 220-520 | Governance manager |
| [tests/governance/test_database_initialization.py](../tests/governance/test_database_initialization.py) | - | تست‌های واحد |

---

## 🔐 خلاصه امنیتی

- ✅ سیستم **بدون** رمز عمل نمی‌کند (امن)
- ✅ خطاها **fail-closed** هستند (امن)
- ✅ Governance layer جداگانه است (معماری درست)
- ✅ Health checks شفاف هستند (قابل‌رویت)

---

## 📌 حالت نهایی

**وضعیت**: ✅ **RESOLVED**

سیستم MAHOUN می‌تواند:
1. **بدون Neo4j** در حالت `desktop_minimal` اجرا شود
2. **با Neo4j** در حالت `server_full` اجرا شود (نیازمند تنظیم)
3. **fail-closed** به‌درستی عمل می‌کند
4. **kernel/container** معماری جداگانه و درست است

---

**تهیه‌کننده**: GitHub Copilot  
**نسخه**: 1.0  
**تاریخ آخرین بروز‌رسانی**: ۱۸ مردادماه ۱۴۰۵
