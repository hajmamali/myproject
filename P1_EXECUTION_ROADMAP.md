# P1 Duplicate Consolidation — نقشه راه اجرایی

**تاریخ**: 2026-07-06  
**وضعیت**: P0=0 ✅ | P1=188 🔶 | P2=250 ⚪

---

## 📊 تحلیل وضعیت

### آمار کلی
- **188 P1 finding** (92% duplicate، 7% dynamic import)
- **176 Duplicate Definition** قابل حذف
- **Top 20 duplicate** شناسایی شده با canonical selection
- **204+ implementation** قابل حذف در صورت اجرای کامل

### فازهای پیشنهادی
1. **Phase 1 — High-Impact** (3 symbol → 17 duplicate) 
2. **Phase 2 — Core Consolidation** (7 symbol → 24 duplicate)
3. **Phase 3 — Exceptions** (5 symbol → 12 duplicate)
4. **Phase 4 — Long-tail Cleanup** (151 symbol → 151 duplicate)

---

## 🎯 استراتژی بستن P1

### گزینه A: تمرکز روی Top 10 (سریع‌ترین تاثیر)
**هدف**: حذف 40+ duplicate در 10 symbol

| Symbol | Canonical | Duplicates | Impact |
|--------|-----------|------------|--------|
| ReasoningResult | `mahoun/core/models.py:105` | 4 | High |
| ValidationResult | `mahoun/core/fortress_validator.py:231` | 6 | High |
| UncertaintyEstimate | `mahoun/core/protocols/advanced_protocols.py:28` | 4 | Medium |
| SecurityBreachException | `mahoun/core/fortress_validator.py:126` | 3 | High |
| Entity | `mahoun/graph/builders/entity_extractor.py:51` | 6 | Medium |
| ReasoningStep | `mahoun/reasoning/reasoning_recorder.py:99` | 4 | Medium |
| LegalDocType | `mahoun/core/models.py:33` | 3 | Low |
| HealthStatus | `mahoun/core/protocols/ai_runtime.py:73` | 4 | Low |
| ViolationSeverity | `mahoun/core/fortress_validator.py:88` | 4 | Medium |
| ValidationError | `mahoun/core/config_validator.py:27` | 4 | Low |

**زمان تخمینی**: 2-3 ساعت  
**ریسک**: پایین (همه در core/infrastructure)

---

### گزینه B: Phase-by-Phase (جامع‌تر، کندتر)
**مزایا**:
- پوشش 100% duplicates
- کاهش ریسک با تقسیم کار
- امکان توقف در هر فاز

**معایب**:
- زمان‌بر (10-15 ساعت)
- نیاز به regression testing هر فاز

---

## 🔧 پلن اجرایی پیشنهادی: "Top 5 NOW"

### چرا Top 5؟
1. **ReasoningResult** — قلب سیستم reasoning (4 duplicate)
2. **ValidationResult** — استفاده گسترده در governance (6 duplicate)
3. **SecurityBreachException** — critical security boundary (3 duplicate)
4. **ReasoningStep** — core reasoning trace (4 duplicate)
5. **Entity** — graph extraction (6 duplicate)

**جمع**: 23 duplicate حذف می‌شن → P1 از 188 به 165 می‌رسه (12% کاهش)

---

## 📋 پروتکل اجرا (برای هر symbol)

### Step 1: Validation
```bash
# پیدا کردن همه تعاریف
grep -rn "^class <SymbolName>" --include="*.py" mahoun/

# بررسی import usage
grep -rn "from .* import.*<SymbolName>" --include="*.py" .
```

### Step 2: Consolidation
1. Canonical را تایید کن (scoring + manual review)
2. همه duplicates را شناسایی کن
3. Import statements را به canonical تغییر بده
4. Duplicate files را حذف کن (یا deprecate)

### Step 3: Verification
```bash
# Syntax check
python -m py_compile <modified_files>

# Import integrity
python -c "from mahoun.core.models import ReasoningResult; print('OK')"

# Re-run arch_check
python arch_check.py
```

### Step 4: Test
```bash
# Unit tests for affected modules
pytest tests/ -k "reasoning" -v

# Integration smoke test
pytest tests/integration/ -v -x
```

---

## ⚠️ ریسک‌ها و Mitigation

| ریسک | احتمال | تاثیر | Mitigation |
|------|--------|-------|-----------|
| Import cycle ایجاد شود | متوسط | بالا | Pre-check با dependency graph |
| Tests fail بعد از consolidation | بالا | متوسط | Test قبل از commit |
| Runtime error در production path | پایین | بالا | Smoke test integration |
| Canonical اشتباه انتخاب شده | پایین | متوسط | Manual review + scoring validation |

---

## 🚀 Ready to Execute?

**گزینه پیشنهادی**: Top 5 NOW  
**زمان**: 1-2 ساعت  
**ROI**: بالا (23 duplicate حذف با ریسک پایین)

### دستور شروع:
```bash
# Activate venv
source /home/haji/Desktop/KingMahouN/venv/bin/activate

# Start with ReasoningResult (highest impact)
python consolidate_duplicate.py --symbol ReasoningResult --canonical mahoun/core/models.py:105
```

---

## 📝 Checklist

- [ ] **Phase 0**: بررسی اولیه canonical selections (manual review)
- [ ] **Symbol 1**: ReasoningResult consolidation
- [ ] **Symbol 2**: ValidationResult consolidation  
- [ ] **Symbol 3**: SecurityBreachException consolidation
- [ ] **Symbol 4**: ReasoningStep consolidation
- [ ] **Symbol 5**: Entity consolidation
- [ ] **Verification**: arch_check.py re-run
- [ ] **Testing**: Integration smoke tests
- [ ] **Commit**: P1 reduction commit

---

## 🎬 بعدی چی؟

بگو از کجا شروع کنیم:
1. **Manual review** از Top 5 canonical selections؟
2. **ساخت اسکریپت** `consolidate_duplicate.py` برای automation؟
3. **شروع دستی** از ReasoningResult؟

منتظر دستورت هستم! 🫡
