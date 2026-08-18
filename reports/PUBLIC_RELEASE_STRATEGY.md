# استراتژی انتشار عمومی MAHOUN
# MAHOUN Public Release Strategy

**تاریخ:** 1405/02/23 (2026-05-13)  
**وضعیت:** پیش‌نویس استراتژیک  
**طبقه‌بندی:** محرمانه - قبل از انتشار

---

## 🎯 هدف استراتژیک

تبدیل MAHOUN از یک مخزن خصوصی به یک پروژه متن‌باز با حفظ:
- اسرار تجاری و الگوریتم‌های اختصاصی
- اطلاعات حساس مشتریان
- کلیدهای API و اعتبارنامه‌ها
- داده‌های آموزشی و مدل‌های اختصاصی

---

## ✅ پوشه‌های امن برای انتشار عمومی

### کاملاً امن (100% عمومی)
```
✅ .github/workflows/          # CI/CD workflows (بدون سیکرت)
✅ docs/                        # مستندات عمومی
✅ examples/                    # مثال‌های نمونه
✅ tests/                       # تست‌های یونیت (بدون داده واقعی)
✅ scripts/                     # اسکریپت‌های عمومی
✅ frontend/                    # کد فرانت‌اند
✅ api/                         # API endpoints (بدون سیکرت)
✅ mahoun/                      # کد اصلی پلتفرم
✅ reasoning_logic/             # منطق استدلال
✅ ci/                          # اسکریپت‌های CI
```

### فایل‌های ریشه امن
```
✅ README.md
✅ LICENSE
✅ pyproject.toml
✅ requirements.txt
✅ requirements-cpu.txt
✅ Makefile
✅ Makefile.backend
✅ docker-compose.yml (template)
✅ Dockerfile
✅ Dockerfile.backend
✅ .gitignore
✅ .dockerignore
✅ .pre-commit-config.yaml
✅ mypy.ini
✅ .env.example
✅ .env.backend.example
✅ SECURITY_GUIDELINES.md
```

---

## ⚠️ پوشه‌های نیمه‌حساس (نیاز به بررسی)

### نیاز به پاکسازی قبل از انتشار
```
⚠️ config/                     # ممکنه شامل تنظیمات داخلی باشه
⚠️ monitoring/                 # ممکنه شامل متریک‌های داخلی باشه
⚠️ demos/                      # ممکنه شامل داده واقعی باشه
⚠️ docker/                     # ممکنه شامل کانفیگ خصوصی باشه
⚠️ services/                   # بستگی به محتوا داره
```

**اقدام لازم:** بررسی دستی هر فایل قبل از انتشار

---

## 🚫 پوشه‌های کاملاً محرمانه (هرگز عمومی نشوند)

### پوشه‌های AI Agent (اختصاصی)
```
🚫 .claude/                    # تنظیمات Claude AI - اختصاصی
🚫 .kiro/                      # تنظیمات Kiro AI - اختصاصی
🚫 .kilo/                      # تنظیمات Kilo - اختصاصی
🚫 .qoder/                     # تنظیمات Qoder - اختصاصی
```

**دلیل:** شامل:
- System prompts اختصاصی
- Agent configurations
- Workflow secrets
- Internal automation logic

### پوشه‌های داده و مدل
```
🚫 data/                       # داده‌های آموزشی و تست
🚫 models/                     # مدل‌های آموزش‌دیده
🚫 vector_store_data/          # داده‌های vector store
🚫 uploads/                    # فایل‌های آپلود شده کاربران
🚫 output/                     # خروجی‌های سیستم
🚫 runtime/                    # داده‌های runtime
🚫 ledger/                     # داده‌های ledger (ممکنه حساس باشه)
```

**دلیل:** شامل:
- PII (اطلاعات شخصی)
- داده‌های مشتریان
- مدل‌های اختصاصی
- داده‌های تجاری

### پوشه‌های Build و Cache
```
🚫 venv/                       # محیط مجازی پایتون
🚫 __pycache__/                # کش پایتون
🚫 .pytest_cache/              # کش pytest
🚫 build/                      # فایل‌های build
🚫 dist/                       # فایل‌های توزیع
🚫 *.egg-info/                 # متادیتای پکیج
```

**دلیل:** فایل‌های موقت و غیرضروری

### پوشه‌های آرشیو و گزارش
```
🚫 archive/                    # فایل‌های قدیمی (ممکنه حساس باشه)
🚫 reports/                    # گزارش‌های داخلی
```

**دلیل:** ممکنه شامل اطلاعات تجاری حساس باشه

---

## 📋 فایل‌های ریشه که نباید عمومی شوند

```
🚫 *.log                       # فایل‌های لاگ
🚫 test_*.py (در ریشه)        # تست‌های موقت
🚫 *_COMPLETE.md               # گزارش‌های داخلی
🚫 FORENSIC_*.md               # تحلیل‌های داخلی
🚫 PHASE_*.md                  # اسناد پروژه داخلی
🚫 EXECUTIVE_SUMMARY_*.md      # خلاصه‌های مدیریتی
🚫 core_manifest.yaml          # مانیفست داخلی
🚫 non_core_manifest.yaml      # مانیفست داخلی
🚫 Agentrules.md               # قوانین داخلی agent
```

---

## 🔒 به‌روزرسانی .gitignore برای محافظت کامل

```gitignore
# ============================================================================
# MAHOUN PRIVATE: AI Agent Configurations (NEVER PUBLIC)
# ============================================================================
.claude/
.kiro/
.kilo/
.qoder/
.cursor/

# ============================================================================
# MAHOUN PRIVATE: Internal Documentation (NEVER PUBLIC)
# ============================================================================
*FORENSIC*.md
*PHASE_*.md
*EXECUTIVE_SUMMARY*.md
*_COMPLETE.md
*_INTERNAL*.md
core_manifest.yaml
non_core_manifest.yaml
Agentrules.md

# ============================================================================
# MAHOUN PRIVATE: Data & Models (NEVER PUBLIC)
# ============================================================================
data/
models/
vector_store_data/
uploads/
output/
runtime/
ledger/
datasets/

# ============================================================================
# MAHOUN PRIVATE: Archives & Reports (NEVER PUBLIC)
# ============================================================================
archive/
reports/
!reports/.gitkeep
!reports/ci_perf_baseline.json

# ============================================================================
# MAHOUN PRIVATE: Temporary Test Files (NEVER PUBLIC)
# ============================================================================
/test_*.py
!/tests/test_*.py
*.log
reasoning_tests.log
test_results_*.log
```

---

## 📊 آمار پیشنهادی

| دسته | تعداد پوشه | وضعیت |
|------|-----------|-------|
| ✅ عمومی امن | ~15 | آماده انتشار |
| ⚠️ نیاز به بررسی | ~5 | پاکسازی لازم |
| 🚫 کاملاً خصوصی | ~15 | هرگز عمومی نشود |

---

## 🛡️ چک‌لیست قبل از انتشار عمومی

### مرحله 1: پاکسازی Git History
- [ ] اسکن تاریخچه git برای سیکرت‌ها
- [ ] حذف فایل‌های حساس از تاریخچه
- [ ] بررسی تمام commit messages
- [ ] پاک کردن branch‌های خصوصی

### مرحله 2: بررسی محتوا
- [ ] حذف تمام API keys از کد
- [ ] حذف hardcoded passwords
- [ ] حذف URL‌های داخلی
- [ ] حذف نام‌های واقعی مشتریان
- [ ] حذف داده‌های PII از تست‌ها

### مرحله 3: به‌روزرسانی .gitignore
- [ ] اضافه کردن پوشه‌های AI agent
- [ ] اضافه کردن پوشه‌های داده
- [ ] اضافه کردن اسناد داخلی
- [ ] تست .gitignore با اسکریپت verify

### مرحله 4: مستندات عمومی
- [ ] به‌روزرسانی README.md
- [ ] حذف اطلاعات داخلی از docs
- [ ] اضافه کردن SECURITY.md
- [ ] اضافه کردن CONTRIBUTING.md
- [ ] اضافه کردن CODE_OF_CONDUCT.md

### مرحله 5: تست نهایی
- [ ] اجرای `scripts/verify-gitignore.sh`
- [ ] اجرای `.github/scripts/security-audit-pre-commit.sh`
- [ ] Clone تازه و بررسی محتوا
- [ ] اسکن با ابزارهای امنیتی (gitleaks, truffleHog)

---

## 🚀 فرآیند انتشار پیشنهادی

### گزینه 1: مخزن جدید (توصیه می‌شود)
```bash
# 1. ساخت مخزن جدید
mkdir mahoun-public
cd mahoun-public
git init

# 2. کپی فقط فایل‌های امن
rsync -av --exclude-from=.gitignore-private /path/to/mahoun/ .

# 3. اولین commit
git add .
git commit -m "Initial public release"

# 4. Push به GitHub
git remote add origin https://github.com/your-org/mahoun-public.git
git push -u origin main
```

### گزینه 2: پاکسازی مخزن فعلی (خطرناک‌تر)
```bash
# 1. Backup کامل
cp -r mahoun mahoun-backup

# 2. پاکسازی تاریخچه
git filter-repo --path-glob '.claude/' --invert-paths
git filter-repo --path-glob '.kiro/' --invert-paths
git filter-repo --path-glob 'data/' --invert-paths
# ... ادامه برای تمام پوشه‌های خصوصی

# 3. Force push (خطرناک!)
git push --force origin main
```

**⚠️ هشدار:** گزینه 2 تاریخچه git را بازنویسی می‌کند!

---

## 💡 توصیه نهایی

**بهترین رویکرد:**
1. ساخت یک مخزن عمومی جدید از صفر
2. کپی انتخابی فقط فایل‌های امن
3. نگهداری مخزن خصوصی فعلی برای توسعه داخلی
4. Sync دوطرفه با دقت بین دو مخزن

این رویکرد:
- ✅ امن‌ترین
- ✅ قابل کنترل‌ترین
- ✅ قابل برگشت
- ✅ بدون خطر افشای تاریخچه

---

## 📞 تماس

برای سوالات امنیتی:
- تیم امنیت: security@mahoun.ai
- مدیر پروژه: [نام]

**آخرین به‌روزرسانی:** 1405/02/23  
**بازبینی بعدی:** قبل از انتشار عمومی
