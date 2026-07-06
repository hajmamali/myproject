# بررسی بی‌رحمانه لایه‌های 0 و 1 — MAHOUN
## تاریخ: 2026-07-04
## وضعیت: 🔴 CRITICAL ISSUES FOUND

---

## خلاصه اجرایی

بررسی دقیق لایه‌های 0 (Core/Foundation) و 1 (Domain Models) **7 مشکل حیاتی** را شناسایی کرد:

- **3 مشکل P0** (Critical - باید فوری حل شوند)
- **2 مشکل P1** (High - باید قبل از production حل شوند)  
- **2 مشکل P2** (Medium - باید در cleanup بعدی حل شوند)

**نتیجه کلی:** لایه Core دچار **تکرار معماری، boundary violation، و کد غیرفعال** است.

---

## 🔴 مشکلات P0 (CRITICAL)

### P0-1: Protocol Definition Duplication & Confusion

**شدت:** 🔴 CRITICAL  
**دسته:** Architectural Confusion

**توضیح:**  
دو منبع مختلف برای تعریف protocols وجود دارد:

1. `mahoun/core/protocols.py` - یک فایل standalone با تمام protocol ها
2. `mahoun/core/protocols/` - یک package کامل با:
   - `__init__.py` → re-export از legacy_protocols
   - `legacy_protocols.py` → protocols اصلی
   - `advanced_protocols.py` → protocols پیشرفته
   - `ai_runtime.py` → protocols جدید

**مشکل:**  
```python
# این دو import مختلف، منابع مختلف دارند:
from mahoun.core.protocols import QueryRouterProtocol  # از protocols.py
from mahoun.core.protocols.legacy_protocols import QueryRouterProtocol  # از package
```

**چرا P0:**  
- باعث confusion در imports می‌شود
- ممکن است دو نسخه مختلف از یک protocol استفاده شود
- maintenance nightmare (تغییر باید در دو جا اعمال شود)
- نقض AGENTS.md که می‌گوید "single source of truth"

**راه‌حل:**  
```bash
# گزینه 1 (توصیه شده): Package را نگه دار، فایل را حذف کن
rm mahoun/core/protocols.py
# همه imports را به mahoun.core.protocols (package) تبدیل کن

# گزینه 2: فایل را نگه دار، package را حذف کن  
rm -rf mahoun/core/protocols/
# همه imports را به mahoun.core.protocols (file) تبدیل کن

# گزینه 1 ترجیح داده می‌شود چون protocols جدید در package هستند
```

**فایل‌های تاثیرگذار:**
- `mahoun/core/protocols.py`
- `mahoun/core/protocols/__init__.py`
- `mahoun/core/protocols/legacy_protocols.py`
- `mahoun/core/protocols/advanced_protocols.py`
- `mahoun/core/protocols/ai_runtime.py`

**تست برای verify کردن:**
```bash
# بعد از fix:
grep -r "from mahoun.core.protocols import" --include="*.py" . | wc -l
# باید همه از یک منبع import کنند
```

---

### P0-2: Import Firewall NOT Installed

**شدت:** 🔴 CRITICAL  
**دسته:** Non-Functional Code

**توضیح:**  
`mahoun/core/import_firewall.py` وجود دارد اما **هیچ‌جا install نشده است**. این فایل یک `ImportHook` تعریف می‌کند اما:

```python
# import_firewall.py defines class but NEVER installs it:
class MahounImportFirewall(importlib.abc.MetaPathFinder):
    ...
```

برای اینکه فایروال کار کند، باید در startup این کار انجام شود:
```python
sys.meta_path.insert(0, MahounImportFirewall())
```

**اما این کد در هیچ‌جا نیست!**

**چرا P0:**  
- security/governance feature که کار نمی‌کند
- theatre code (به نظر می‌رسد کار می‌کند اما نمی‌کند)
- اگر روی آن حساب باز شده، یک آسیب‌پذیری است

**راه‌حل:**

**گزینه A (فعال‌سازی):**  
```python
# در api/main.py یا mahoun/bootstrap/runtime.py
from mahoun.core.import_firewall import install_firewall

@asynccontextmanager
async def lifespan(app: FastAPI):
    # BEFORE bootstrap_runtime
    install_firewall()  # باید این را اضافه کنیم به import_firewall.py
    
    runtime_registry = bootstrap_runtime()
    ...
```

**گزینه B (حذف):**  
اگر firewall استفاده نمی‌شود:
```bash
rm mahoun/core/import_firewall.py
# و همه references به آن را حذف کن
```

**توصیه:** گزینه A - فایروال را فعال کن چون governance feature است.

**فایل‌های مرتبط:**
- `mahoun/core/import_firewall.py`
- `api/main.py` (باید firewall را نصب کند)
- `mahoun/bootstrap/runtime.py` (جای بهتر برای نصب)

---

### P0-3 & P0-4: Core Layer Boundary Violations

**شدت:** 🔴 CRITICAL  
**دسته:** Architectural Boundary Violation

**توضیح:**  
دو فایل در Core layer از لایه‌های بالاتر import می‌کنند:

#### Violation 1: `mahoun/core/query_executor.py`
```python
from mahoun.graph.graph_query_service import GraphQueryService
```

#### Violation 2: `mahoun/core/fortress_validator.py`
```python
from mahoun.reasoning.unified_reasoning_service import UnifiedReasoningService
```

**چرا P0:**  
طبق `AGENTS.md` و `.kiro/steering/structure.md`:

> **Dependency direction (strict):**
> ```
> mahoun/core → nothing (pure domain)
> ```

Core layer **هیچ‌وقت** نباید از reasoning/rag/graph import کند. این باعث:
- Circular dependency risk
- Core layer دیگر "pure" نیست
- Unit testing Core بدون dependency injection غیرممکن می‌شود

**راه‌حل:**

**برای query_executor.py:**
```python
# BAD (current):
from mahoun.graph.graph_query_service import GraphQueryService

class LegalQueryExecutor:
    def __init__(self):
        self.graph_service = GraphQueryService()  # Direct instantiation!
        
# GOOD (fix):
from mahoun.core.protocols import GraphServiceProtocol

class LegalQueryExecutor:
    def __init__(self, graph_service: GraphServiceProtocol):
        self.graph_service = graph_service  # Dependency injection
```

**برای fortress_validator.py:**
```python
# BAD (current):  
from mahoun.reasoning.unified_reasoning_service import UnifiedReasoningService

# GOOD (fix):
from mahoun.core.protocols import ReasoningServiceProtocol

class FortressValidator:
    def __init__(self, reasoning_service: Optional[ReasoningServiceProtocol] = None):
        self.reasoning_service = reasoning_service  # Optional, injected
```

**فایل‌های مرتبط:**
- `mahoun/core/query_executor.py`
- `mahoun/core/fortress_validator.py`
- `mahoun/core/protocols/` (باید protocols مورد نیاز را داشته باشد)

**تست:**
```bash
# بعد از fix, این باید خالی باشد:
grep -rn "from mahoun\.\(graph\|reasoning\|rag\)" mahoun/core/*.py | grep -v "_adapter"
```

---

## 🟠 مشکلات P1 (HIGH)

### P1-1: Exception Hierarchy Duplication

**شدت:** 🟠 HIGH  
**دسته:** Code Duplication

**توضیح:**  
دو سلسله مراتب exception مجزا وجود دارد:

1. **`mahoun/core/exceptions.py`**:
   - `MahounError` (base)
   - `BaseMahounError` (با status_code)
   - 20+ exception subclasses

2. **`mahoun/core/exceptions_v2.py`**:
   - `MahounException` (unified base با HTTP awareness)
   - همان 20+ exception subclasses دوباره

**مشکل:**  
```python
# Confusion در imports:
from mahoun.core.exceptions import SecurityBreachException  # از v1
from mahoun.core.exceptions_v2 import SecurityBreachException  # از v2

# این دو کلاس DIFFERENT هستند!
```

**چرا P1:**  
- Migration path مشخص نیست
- ممکن است کد قدیمی v1 و کد جدید v2 استفاده کند
- Exception handling می‌تواند inconsistent شود
- نقض DRY principle

**راه‌حل:**

**Phase 1 (فوری):**
```python
# در exceptions.py، همه را به v2 forward کن:
from mahoun.core.exceptions_v2 import *

# Deprecation warning:
import warnings
warnings.warn(
    "mahoun.core.exceptions is deprecated. Use mahoun.core.exceptions_v2",
    DeprecationWarning,
    stacklevel=2
)
```

**Phase 2 (بعدی):**
```bash
# Find all imports:
grep -r "from mahoun.core.exceptions import" --include="*.py" .

# Replace with:
# from mahoun.core.exceptions_v2 import ...

# Script برای auto-replace:
find . -name "*.py" -exec sed -i 's/from mahoun\.core\.exceptions import/from mahoun.core.exceptions_v2 import/g' {} +
```

**Phase 3 (cleanup):**
```bash
# بعد از اطمینان که همه به v2 migrate شدند:
rm mahoun/core/exceptions.py
```

**فایل‌های تاثیرگذار:**
- `mahoun/core/exceptions.py` (باید حذف شود)
- `mahoun/core/exceptions_v2.py` (canonical)
- ~100+ فایل که import می‌کنند

---

### P1-2: Triple Health Checker Implementation

**شدت:** 🟠 HIGH  
**دسته:** Code Duplication

**توضیح:**  
سه پیاده‌سازی مختلف health checker:

1. `mahoun/core/health_checker.py` (146 lines)
2. `mahoun/infrastructure/health_checker.py` (523 lines) 
3. `mahoun/infrastructure/health/checker.py` (337 lines)

**تفاوت‌ها:**
- (1) ساده‌ترین - فقط basic checks
- (2) پیچیده‌ترین - با Neo4j, Redis, self-improvement checks
- (3) میانه - با health registry pattern

**چرا P1:**  
- نگهداری 3 implementation مختلف
- confusion در اینکه کدام یک استفاده شود
- احتمال inconsistency در health reporting

**راه‌حل:**

**Step 1: Identify Canonical**
```bash
# پیدا کردن اینکه کدام یک واقعا استفاده می‌شود:
grep -r "from mahoun.*health.*checker import" --include="*.py" . | sort | uniq -c

# نتیجه expected:
# - infrastructure/health_checker.py → used in api/main.py (probable winner)
# - core/health_checker.py → orphaned?
# - infrastructure/health/checker.py → used in ai/health.py?
```

**Step 2: Decision Tree**

```
IF infrastructure/health_checker.py is the most complete:
    → Keep it as canonical
    → Move to mahoun/infrastructure/health/checker.py (more organized)
    → Delete mahoun/core/health_checker.py
    → Ensure infrastructure/health/checker.py imports from canonical
    
ELSE IF infrastructure/health/checker.py is better:
    → Keep it as canonical
    → Delete the other two
    → Update all imports
```

**Step 3: Consolidation**
```bash
# بعد از تصمیم‌گیری:
# 1. انتخاب canonical
# 2. migrate همه functionality از دیگران
# 3. update imports
# 4. delete duplicates
# 5. test health endpoints
```

**تست:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/v2
# باید consistent response بدهند
```

---

## 🟡 مشکلات P2 (MEDIUM)

### P2-1: models.py File vs models/ Package Collision

**شدت:** 🟡 MEDIUM  
**دسته:** Naming Collision

**توضیح:**  
هم فایل و هم package با نام `models` وجود دارد:

```
mahoun/core/
├── models.py          ← فایل با ~800 lines
└── models/            ← package
    ├── __init__.py
    ├── ai_response.py
    ├── audit_event.py
    ├── deployment_profile.py
    └── prompt_template.py
```

**مشکل:**
```python
# این import چه چیزی را می‌آورد؟
from mahoun.core.models import ReasoningResult  
# از models.py؟ یا models/__init__.py؟

# Python ترجیح می‌دهد package را بیاورد (اگر __init__.py داشته باشد)
# اما این می‌تواند confusing باشد
```

**چرا P2:**  
- فعلا کار می‌کند (package precedence دارد)
- اما می‌تواند باعث confusion شود
- refactoring را سخت می‌کند

**راه‌حل:**

**Option A: Merge into Package**
```bash
# Move content of models.py into models/legacy.py or models/reasoning.py
mv mahoun/core/models.py mahoun/core/models/legacy_models.py

# Update models/__init__.py to re-export:
# from .legacy_models import *
# from .ai_response import *
# ...
```

**Option B: Rename Package**
```bash
# Rename package to something more specific:
mv mahoun/core/models mahoun/core/domain_models

# Update imports:
# from mahoun.core.domain_models import AIResponse
```

**توصیه:** Option A - merge کن چون models یک namespace خوب است.

---

## 📊 آمار نهایی

| Layer | Files Checked | P0 Issues | P1 Issues | P2 Issues | Total |
|-------|--------------|-----------|-----------|-----------|--------|
| Core (Layer 0) | 30 | 4 | 2 | 1 | 7 |
| Models (Layer 1) | 5 | 0 | 0 | 1 | 1 |
| **TOTAL** | **35** | **4** | **2** | **2** | **8** |

---

## 🎯 اقدامات پیشنهادی (به ترتیب اولویت)

### Immediate (این هفته)

1. **[P0-2] Install Import Firewall** - 30 دقیقه
   - Add install call in `mahoun/bootstrap/runtime.py`
   - Test that it blocks forbidden imports
   
2. **[P0-3, P0-4] Fix Boundary Violations** - 2 ساعت
   - Refactor `query_executor.py` to use DI
   - Refactor `fortress_validator.py` to use protocol
   - Add integration tests

3. **[P0-1] Resolve Protocol Duplication** - 1 ساعت
   - Decision: Keep package, delete file
   - Update all imports (script provided)
   - Test all modules still work

### Short-term (این ماه)

4. **[P1-1] Migrate to exceptions_v2** - 3 ساعت
   - Phase 1: Forward imports
   - Phase 2: Replace imports (script provided)  
   - Phase 3: Delete old file

5. **[P1-2] Consolidate Health Checkers** - 2 ساعت
   - Identify canonical implementation
   - Migrate functionality
   - Delete duplicates
   - Test endpoints

### Medium-term (ماه بعد)

6. **[P2-1] Resolve models collision** - 1 ساعت
   - Merge models.py into models/ package
   - Update imports
   - Test

---

## ✅ معیارهای موفقیت

بعد از حل این مشکلات، این checklist باید همگی ✅ باشند:

```bash
# 1. No protocol duplication
[ ] ls mahoun/core/protocols.py  # باید 404 باشد (یا package حذف شود)

# 2. Import firewall installed
[ ] grep -r "install_firewall" api/main.py mahoun/bootstrap/  # باید یک match پیدا کند

# 3. No boundary violations  
[ ] grep -rn "from mahoun\.\(graph\|reasoning\|rag\)" mahoun/core/*.py | grep -v adapter
      # باید خالی باشد

# 4. Single exception hierarchy
[ ] grep -r "from mahoun.core.exceptions import" --include="*.py" . | wc -l
      # باید 0 باشد (همه به exceptions_v2 migrate شده)

# 5. Single health checker
[ ] find mahoun -name "*health*checker*.py" | wc -l  # باید 1 باشد

# 6. No models collision
[ ] test -f mahoun/core/models.py && echo "FAIL: models.py still exists"
      # باید خالی باشد
```

---

## 🔒 Governance Note

این مشکلات **قبل از production release** باید حل شوند چون:

- P0 issues می‌توانند security/stability problems ایجاد کنند
- Boundary violations architecture را سست می‌کنند  
- Duplications باعث maintenance debt می‌شوند

طبق `constitution/RedLines.yaml`:
```yaml
fail_ci_on_violation: true
```

این issues باید در CI gate ها catch شوند.

---

## 📝 یادداشت‌های اضافی

### مشکلات NOT Found (خوب است!)

این چیزها که تست شدند و مشکلی نداشتند:

✅ `mahoun/core/governance/` - clean, no duplication  
✅ `mahoun/core/protocols/` submodules - well organized  
✅ `mahoun/core/models/` domain models - clean imports  
✅ No exec()/eval() in core layer  
✅ No hardcoded paths in core layer

### توصیه برای جلوگیری از تکرار

1. **Pre-commit hook** برای boundary checking:
```bash
#!/bin/bash
# .git/hooks/pre-commit
if grep -rn "from mahoun\.\(graph\|reasoning\|rag\)" mahoun/core/*.py | grep -v adapter; then
    echo "ERROR: Core layer importing from upper layers!"
    exit 1
fi
```

2. **CI gate** برای duplication detection:
```python
# ci/gates/gate_duplication_check.py
import ast
from pathlib import Path

def find_duplicate_classes():
    classes = defaultdict(list)
    for py_file in Path("mahoun").rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes[node.name].append(str(py_file))
    
    duplicates = {k: v for k, v in classes.items() if len(v) > 1}
    if duplicates:
        print("ERROR: Duplicate class names found:")
        for name, files in duplicates.items():
            print(f"  {name}: {files}")
        sys.exit(1)
```

---

**تهیه‌کننده:** Kiro Agent  
**تاریخ بررسی:** 2026-07-04  
**نسخه:** 1.0  
**وضعیت:** 🔴 REQUIRES IMMEDIATE ACTION
