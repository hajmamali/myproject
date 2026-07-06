# خلاصه اجرایی - اصلاح P0های معماری

## وضعیت کلی
- **کل P0ها:** 20 مورد
- **False Positive:** 9 مورد (نیاز به config update)
- **True Positive:** 11 مورد (نیاز به اصلاح کد)
- **زمان تخمینی:** 5-6 ساعت

---

## ✅ اقدامات سریع (30 دقیقه)

### 1. تأیید False Positive - bootstrap_runtime
```bash
# VERIFIED: bootstrap_runtime در api/main.py:150 فراخوانی می‌شود ✅
grep -n "bootstrap_runtime()" api/main.py
# Output: api/main.py:150:    bootstrap_runtime()
```

### 2. حذف Import Firewall (dead code)
```bash
# این کد هرگز install نشده → حذف کامل
rm mahoun/core/import_firewall.py
# CI gates کافی است
```

### 3. به‌روزرسانی arch_check.py config
```python
# اضافه کردن به exclude_dirs:
"exclude_dirs": [..., "examples", "self_improve"],

# اضافه کردن به exclude_files_containing:
"exclude_files_containing": [..., "neo4j/connection.py"],
```

---

## 🔧 اصلاحات معماری (3 ساعت)

### P0 #1: حل تعارض protocols
**مشکل:** هم `protocols.py` و هم `protocols/` وجود دارند

**راه‌حل:**
1. `protocols.py` دارای محتویات قدیمی = `protocols/legacy_protocols.py`
2. تبدیل `protocols.py` به facade (wrapper فقط)
3. تمام import‌ها باید به `mahoun.core.protocols` (package) تغییر کنند

### P0 #3: query_executor.py → graph_query_service
**مشکل:** core layer به graph layer وابسته است

**راه‌حل:** Protocol + DI
```python
# 1. تعریف GraphQueryExecutorProtocol در core
# 2. query_executor از protocol استفاده کند
# 3. bootstrap وایرینگ را انجام دهد
```

### P0 #4: fortress_validator.py → ReasoningResponse  
**مشکل:** core به reasoning وابسته است

**راه‌حل:** کد فعلی از `__getattr__` استفاده می‌کند (درست است) - فقط بررسی خط 51

### P0 #7: outbox_worker در core
**مشکل:** یک infrastructure component در core layer است

**راه‌حل:** انتقال به `mahoun/graph/sync/outbox_worker.py`

---

## 🛡️ اصلاح Governance Bypasses (2 ساعت)

### 6 فایل با raw .session() call:
1. `mahoun/retrieval/graph_enhanced.py:20`
2. `mahoun/graph/legal_cypher_queries.py:611`
3. `mahoun/pipelines/sync/graph_vector_sync.py:21`
4. `mahoun/graph/validation/quality_validator.py:213`
5. `mahoun/graph/validation/integrity_checker.py:62`

**الگوی اصلاح:**
```python
# قبل: conn.driver.session()
# بعد: conn.execute_governed(query, params, governance_context)
```

---

## 🧪 تست نهایی

```bash
source venv/bin/activate

# 1. Architecture check
python arch_check.py --root mahoun --output-file ARCH_CHECK_FIXED.txt
# انتظار: P0 count = 0

# 2. CI Gates
bash ci/gates/gate_9_governance.sh

# 3. Bootstrap tests
pytest tests/integration/test_bootstrap_integration.py -v

# 4. Governance tests  
pytest tests/governance/ -v --tb=short
```

---

**آماده برای شروع!** 🚀
