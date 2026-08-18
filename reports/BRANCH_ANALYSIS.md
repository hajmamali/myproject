# تحلیل دلایل عدم Merge کردن Branches

## 🔴 مسئله اصلی: **Unrelated Histories**

هر چهار شاخه‌ی اصلی (`kernel_stress_test`, `sun-wildebeest`, `opencode/mighty-island`, `fix/test-suite-recovery`) دارای **history جداگانه** هستند و نمی‌توانند بدون `--allow-unrelated-histories` merge شوند.

---

## 📊 وضعیت هر شاخه

### 1. **kernel_stress_test** (25 commits)
- **شروع:** `d1be57b4` (Initial commit)
- **آخرین commit:** `e6e5a4f4` - "Stop tracking venv"
- **کارهای انجام شده:**
  - Cleanup venv tracking
  - کامیت‌های فارسی و خودکار
  - Governance boundary refactoring
- **چرا merge نشده:**
  - ❌ Unrelated history
  - ❌ شاید برای testing و stress testing استفاده می‌شد
  - ❌ هنوز درحال توسعه یا تست بوده

### 2. **sun-wildebeest** (24 commits)
- **شروع:** `d1be57b4` (Initial commit)
- **آخرین commit:** `a35d7b5d` - "Synchronize P0 governance bypass vector fixes"
- **کارهای انجام شده:**
  - P0 governance bypass vector fixes
  - Evidence integration
  - Documentation
- **چرا merge نشده:**
  - ❌ Unrelated history
  - ❌ شاید فکس‌های P0 هنوز validate نشده بودند
  - ❌ جدایی deliberate برای testing

### 3. **opencode/mighty-island** (13 commits)
- **شروع:** `d1be57b4` (Initial commit)
- **آخرین commit:** `6299be0f` - "Update governance infrastructure and test fixtures"
- **کارهای انجام شده:**
  - Airgap Phase 1 P0 critical fixes
  - HuggingFace local_files_only modifications
  - Governance infrastructure updates
  - Ledger governance tests (48 passing)
- **چرا merge نشده:**
  - ❌ Unrelated history
  - ❌ "airgap" یعنی offline operation - شاید experimental
  - ❌ P0 critical fixes نیاز به validation بیشتری دارند

### 4. **fix/test-suite-recovery** (7 commits)
- **شروع:** `d1be57b4` (Initial commit)
- **آخرین commit:** `10d1fde4` - "Fix JWT token expiry test timing issue"
- **کارهای انجام شده:**
  - Security tests (API keys, RBAC, JWT)
  - JWT token expiry timing fixes
  - Auth timezone import fixes
  - P0 Blocker Elimination
- **چرا merge نشده:**
  - ❌ Unrelated history
  - ❌ شاید برای تست کردن security و timing issues استفاده می‌شد
  - ❌ نیاز به اجرای تمام tests برای validation

---

## 🎯 دلایل عدم Merge

### الف) **معماری Worktree‌ها**
```
این repo از worktree‌های جداگانه استفاده می‌کند:
- .kilo/worktrees/    (gleaming-magician, mud-koala, etc.)
- .windsurf/worktrees/ (cascade branches)
- .local/share/opencode/ (mighty-island)

هر worktree می‌تواند isolated development داشته باشد
```

### ب) **التزام به Phase-based Development**
- `Phase 0.6 bootstrap work` - شاخه‌ها جدا برای تست کردن
- `P0 critical fixes` - نیاز به validation دقیق
- `Stress testing` - تحت نظارت جداگانه

### ج) **سیاست Governance**
- **git worktree** patterns برای isolated experiments
- Deliberate جدایی برای testing و validation
- هر شاخه برای purpose خاص (stress test, security fixes, airgap)

### د) **وضعیت Synchronization**
```
Last sync dates:
- kernel_stress_test: commit e6e5a4f4 (جداگانه)
- sun-wildebeest: commit a35d7b5d (جداگانه)
- opencode/mighty-island: commit 6299be0f (جداگانه)
- fix/test-suite-recovery: commit 10d1fde4 (جداگانه)

هیچ synchronized commit با main نیست!
```

---

## ✅ راه‌حل‌های ممکن

### گزینه 1: **Cherry-pick Commits**
```bash
# برای گرفتن commits مهم از هر شاخه
git cherry-pick <commit-hash>
```

### گزینه 2: **Merge با Allow Unrelated**
```bash
git merge --allow-unrelated-histories sun-wildebeest
```
⚠️ **ریسک:** ممکن است conflicts یا duplicate changes ایجاد کند

### گزینه 3: **Rebase و Merge**
```bash
git rebase main sun-wildebeest
git checkout main && git merge sun-wildebeest
```

### گزینه 4: **Manual Review و Selective Integration**
- بررسی هر شاخه
- گرفتن فقط commits مهم
- ادغام selective

---

## 📋 توصیه

**بر اساس AGENTS.md و Constitutional Authority:**

شاخه‌های جداگانه شاید **deliberately** جدا شده‌اند برای:
1. ✅ **Isolated Testing** (stress tests, security validation)
2. ✅ **Phase-based Development** (Phase 0.6, P0 Fixes)
3. ✅ **Risk Mitigation** (P0 critical fixes نیاز به validation دقیق)

**پیش از هر merge، باید:**
- ✅ هر شاخه کاملاً tested شود
- ✅ Governance compliance checks pass شود
- ✅ CI/CD pipeline green شود
- ✅ Constitutional Authority approval

---

## 🔍 جزئیات Test Status

```
kernel_stress_test:     ⚠️ Unvalidated
sun-wildebeest:         ⚠️ Awaiting P0 approval
opencode/mighty-island: ⚠️ Experimental (airgap)
fix/test-suite-recovery:✅ Partially tested (security tests)
```

