# MAHOUN — راهنمای به‌روزرسانی مدل در محیط AirGapped

**نسخه**: 1.0.0  
**تاریخ**: 1405/03/20  
**وضعیت**: ✅ PRODUCTION-READY  
**اولویت**: 🔴 CRITICAL — این سند برای دپلویمنت AirGapped ضروری است

---

## خلاصه اجرایی

این سند فرآیند **ایمن، قابل ممیزی و قابل برگشت** برای به‌روزرسانی مدل‌های AI در محیط AirGapped را شرح می‌دهد.

**زمان خواندن**: 10 دقیقه  
**زمان اجرا**: 30-60 دقیقه (بسته به سایز مدل)  
**سطح مهارت مورد نیاز**: System Administrator با آشنایی به Linux و Docker

---

## 🎯 اهداف

1. ✅ به‌روزرسانی مدل بدون قطع سرویس (zero-downtime)
2. ✅ اعتبارسنجی یکپارچگی (checksum verification)
3. ✅ امکان برگشت (rollback) در صورت مشکل
4. ✅ حفظ audit trail کامل
5. ✅ عدم نقض governance constraints

---

## 📋 پیش‌نیازها

### مهارت‌های فنی:
- آشنایی با Linux command line
- آشنایی با Docker و docker-compose
- توانایی انتقال فایل به محیط AirGapped (USB/DVD/isolated network)
- دسترسی به server با `sudo` یا `root`

### ابزارهای مورد نیاز:
```bash
# در server AirGapped باید نصب باشد:
- sha256sum (برای checksum verification)
- rsync یا cp (برای کپی ایمن)
- docker و docker-compose
- Python 3.12+
```

### فضای ذخیره‌سازی مورد نیاز:
| مدل | سایز تقریبی | فضای لازم (با backup) |
|-----|-------------|------------------------|
| Llama-3.2-1B (Q6_K) | ~800 MB | 2.5 GB |
| Qwen-2.5-3B (Q5_K) | ~2 GB | 6 GB |
| DeBERTa-v3-base | ~500 MB | 1.5 GB |
| BGE-small-en-v1.5 | ~130 MB | 400 MB |

**توصیه**: حداقل 10 GB فضای آزاد برای به‌روزرسانی ایمن

---

## 🔍 معماری مدل‌ها در MAHOUN

### انواع مدل‌ها:

1. **LLM (Large Language Model)** — `mahoun/llm/`
   - **کاربرد**: تولید reasoning و verdicts
   - **مدل‌های پشتیبانی شده**: Llama, Qwen, Mistral, DeepSeek (فرمت GGUF)
   - **محل**: `/home/haji/Desktop/KingMahouN/models/*.gguf`

2. **NLI (Natural Language Inference)** — `mahoun/guardrails/`
   - **کاربرد**: تشخیص تناقض در FortressValidator
   - **مدل**: microsoft/deberta-v3-base
   - **محل**: `~/.cache/huggingface/transformers/`
   - **⚠️ CRITICAL**: بدون این مدل، FortressValidator fail می‌شود

3. **Embedding** — `mahoun/rag/`
   - **کاربرد**: تولید embeddings برای RAG pipeline
   - **مدل‌های پشتیبانی شده**: BGE, all-MiniLM, multilingual
   - **محل**: `~/.cache/huggingface/transformers/` یا `models/embeddings/`

4. **Reranker** — `mahoun/retrieval/`
   - **کاربرد**: بهبود کیفیت جستجو
   - **مدل**: cross-encoder/ms-marco-MiniLM-L-6-v2
   - **محل**: `~/.cache/huggingface/transformers/`

---

## 🚀 فرآیند به‌روزرسانی (گام به گام)

### مرحله 1: آماده‌سازی در محیط آنلاین (خارج از AirGap)

این مرحله در یک سیستم **با اینترنت** انجام می‌شود.

#### 1.1 — دانلود مدل جدید

```bash
# محیط: سیستم با اینترنت

# برای LLM (GGUF):
wget https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q6_K.gguf

# برای مدل‌های HuggingFace:
python3 << 'EOF'
from transformers import AutoModel, AutoTokenizer

model_name = "microsoft/deberta-v3-base"
cache_dir = "./model_cache"

# دانلود مدل و tokenizer
model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)

print(f"✅ Model downloaded to {cache_dir}")
EOF
```

#### 1.2 — محاسبه Checksum

```bash
# محاسبه SHA-256 checksum
sha256sum llama-2-7b.Q6_K.gguf > llama-2-7b.Q6_K.gguf.sha256

# برای دایرکتوری کامل (HuggingFace models):
find ./model_cache -type f -exec sha256sum {} \; > model_checksums.txt
```

#### 1.3 — ایجاد Model Manifest

```bash
cat > model_manifest.json << 'EOF'
{
  "model_id": "llama-2-7b-q6k",
  "model_type": "llm",
  "version": "2.0.0",
  "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "file_path": "llama-2-7b.Q6_K.gguf",
  "file_size_bytes": 5368709120,
  "created_at": "2024-01-15T10:30:00Z",
  "metadata": {
    "source": "TheBloke/Llama-2-7B-GGUF",
    "quantization": "Q6_K",
    "use_case": "legal_reasoning",
    "tested_by": "admin",
    "approved_by": "security_team"
  }
}
EOF
```

#### 1.4 — بسته‌بندی برای انتقال

```bash
# ایجاد دایرکتوری انتقال
mkdir model_update_package
cd model_update_package

# کپی فایل‌ها
cp ../llama-2-7b.Q6_K.gguf .
cp ../llama-2-7b.Q6_K.gguf.sha256 .
cp ../model_manifest.json .

# ایجاد README
cat > TRANSFER_README.txt << 'EOF'
MAHOUN Model Update Package
===========================
Date: 2024-01-15
Model: Llama-2-7B-Q6_K
Target: /home/haji/Desktop/KingMahouN/models/

IMPORTANT: Verify checksum before installation!
EOF

# ایجاد آرشیو
cd ..
tar -czf model_update_llama2_7b.tar.gz model_update_package/

# محاسبه checksum آرشیو
sha256sum model_update_llama2_7b.tar.gz > model_update_llama2_7b.tar.gz.sha256

echo "✅ Package ready for transfer: model_update_llama2_7b.tar.gz"
```

---

### مرحله 2: انتقال به محیط AirGapped

انتقال فایل به محیط AirGapped از طریق:
- ✅ **USB Drive** (توصیه‌شده: encrypted USB)
- ✅ **DVD/Blu-ray**
- ✅ **Isolated network transfer** (اگر شبکه داخلی دارید)

```bash
# بعد از انتقال، verify checksum:
sha256sum -c model_update_llama2_7b.tar.gz.sha256

# اگر OK بود:
# ✅ model_update_llama2_7b.tar.gz: OK

# استخراج:
tar -xzf model_update_llama2_7b.tar.gz
cd model_update_package/
```

---

### مرحله 3: Pre-Installation Verification (در AirGap)

⚠️ **CRITICAL**: این مرحله را skip نکنید!

#### 3.1 — Verify Checksum فایل مدل

```bash
# محیط: server AirGapped

cd model_update_package/

# بررسی checksum
sha256sum -c llama-2-7b.Q6_K.gguf.sha256

# خروجی باید باشد:
# ✅ llama-2-7b.Q6_K.gguf: OK

# اگر FAILED بود → STOP! فایل corrupt است
```

#### 3.2 — Verify Model Manifest

```bash
# بررسی فرمت manifest
python3 << 'EOF'
import json
import sys

with open('model_manifest.json') as f:
    manifest = json.load(f)

required_fields = ['model_id', 'model_type', 'version', 'checksum', 'file_path']
missing = [f for f in required_fields if f not in manifest]

if missing:
    print(f"❌ Missing fields: {missing}")
    sys.exit(1)

print("✅ Manifest is valid")
print(f"   Model: {manifest['model_id']} v{manifest['version']}")
print(f"   Type: {manifest['model_type']}")
print(f"   Size: {manifest['file_size_bytes'] / 1024 / 1024:.1f} MB")
EOF
```

#### 3.3 — Disk Space Check

```bash
# بررسی فضای آزاد
df -h /home/haji/Desktop/KingMahouN/models/

# باید حداقل 3x سایز فایل مدل آزاد باشد (برای backup + staging + final)
```

---

### مرحله 4: Backup مدل فعلی

⚠️ **NON-NEGOTIABLE**: همیشه قبل از به‌روزرسانی backup بگیرید!

```bash
# محیط: server AirGapped

# تعریف مسیرها
MODELS_DIR="/home/haji/Desktop/KingMahouN/models"
BACKUP_DIR="/home/haji/Desktop/KingMahouN/backups/models"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ایجاد دایرکتوری backup
mkdir -p "$BACKUP_DIR"

# Backup مدل فعلی (اگر وجود دارد)
if [ -f "$MODELS_DIR/llama-2-7b.Q6_K.gguf" ]; then
    echo "📦 Creating backup..."
    cp -a "$MODELS_DIR/llama-2-7b.Q6_K.gguf" \
       "$BACKUP_DIR/llama-2-7b.Q6_K.gguf.backup_$TIMESTAMP"
    
    # محاسبه checksum backup
    sha256sum "$BACKUP_DIR/llama-2-7b.Q6_K.gguf.backup_$TIMESTAMP" \
        > "$BACKUP_DIR/llama-2-7b.Q6_K.gguf.backup_$TIMESTAMP.sha256"
    
    echo "✅ Backup created: llama-2-7b.Q6_K.gguf.backup_$TIMESTAMP"
else
    echo "ℹ️  No existing model to backup (first installation)"
fi

# Backup model manifest (اگر وجود دارد)
if [ -f "$MODELS_DIR/../data/model_manifest.json" ]; then
    cp -a "$MODELS_DIR/../data/model_manifest.json" \
       "$BACKUP_DIR/model_manifest.json.backup_$TIMESTAMP"
    echo "✅ Manifest backup created"
fi
```

---

### مرحله 5: Installation (Atomic Update)

این مرحله به صورت atomic انجام می‌شود (all-or-nothing).

#### 5.1 — Stop Services (اختیاری برای zero-downtime)

```bash
# اگر می‌خواهید zero-downtime داشته باشید، این قدم را SKIP کنید
# مدل جدید در محل staging کپی می‌شود و سپس atomic rename

# اگر می‌خواهید services را stop کنید:
cd /home/haji/Desktop/KingMahouN
docker-compose down
```

#### 5.2 — Atomic Model Update

```bash
# محیط: server AirGapped
cd model_update_package/

MODELS_DIR="/home/haji/Desktop/KingMahouN/models"
MODEL_FILE="llama-2-7b.Q6_K.gguf"
STAGING_FILE="$MODELS_DIR/${MODEL_FILE}.staging"

# کپی به staging location
echo "📥 Copying to staging..."
cp "$MODEL_FILE" "$STAGING_FILE"

# Verify checksum در staging
STAGING_CHECKSUM=$(sha256sum "$STAGING_FILE" | cut -d' ' -f1)
EXPECTED_CHECKSUM=$(cut -d' ' -f1 < "${MODEL_FILE}.sha256")

if [ "$STAGING_CHECKSUM" != "$EXPECTED_CHECKSUM" ]; then
    echo "❌ CRITICAL: Checksum mismatch in staging!"
    echo "   Expected: $EXPECTED_CHECKSUM"
    echo "   Got:      $STAGING_CHECKSUM"
    rm -f "$STAGING_FILE"
    exit 1
fi

echo "✅ Staging checksum verified"

# Atomic rename (این عملیات atomic است در Linux)
echo "🔄 Activating new model (atomic rename)..."
mv "$STAGING_FILE" "$MODELS_DIR/$MODEL_FILE"

echo "✅ Model updated successfully!"
```

#### 5.3 — Update Model Manifest

```bash
# محیط: server AirGapped

# ثبت manifest جدید در سیستم versioning
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

from pathlib import Path
from mahoun.llm.model_versioning import get_versioning_system, ModelType

# Initialize versioning system
manifest_path = Path("/home/haji/Desktop/KingMahouN/data/model_manifest.json")
vs = get_versioning_system(manifest_path)

# Register new model
model_path = Path("/home/haji/Desktop/KingMahouN/models/llama-2-7b.Q6_K.gguf")

manifest = vs.register_model(
    model_path=model_path,
    model_id="llama-2-7b-q6k",
    model_type=ModelType.LLM,
    version="2.0.0",
    metadata={
        "source": "TheBloke/Llama-2-7B-GGUF",
        "quantization": "Q6_K",
        "installed_at": "2024-01-15T12:00:00Z",
        "installed_by": "admin"
    }
)

# Verify integrity
result = vs.verify_model("llama-2-7b-q6k")
if not result.is_valid:
    print(f"❌ Model integrity check FAILED: {result.error_message}")
    sys.exit(1)

# Activate model
vs.activate_model("llama-2-7b-q6k")

print("✅ Model registered and activated in versioning system")
EOF
```

#### 5.4 — Restart Services

```bash
# محیط: server AirGapped
cd /home/haji/Desktop/KingMahouN

# Activate venv
source venv/bin/activate

# Start services
docker-compose up -d

# تأخیر برای startup
sleep 10
```

---

### مرحله 6: Post-Installation Verification

⚠️ **MANDATORY**: این مرحله را حتماً انجام دهید!

#### 6.1 — Health Check

```bash
# محیط: server AirGapped

# بررسی health endpoint
curl http://localhost:8000/health/v2

# خروجی مورد انتظار:
# {
#   "status": "healthy",
#   "components": {
#     "llm": "operational",
#     "fortress_validator": "operational",
#     ...
#   }
# }
```

#### 6.2 — Smoke Test (تست عملکرد)

```bash
# تست reasoning با مدل جدید
curl -X POST http://localhost:8000/api/v1/reasoning \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is this contract valid?",
    "facts": [
      {"value": "Contract signed by all parties"},
      {"value": "Consideration exchanged"}
    ]
  }'

# بررسی خروجی:
# - success: true
# - verdict: (باید معنی‌دار باشد)
# - agreement_score: >= 0.85
```

#### 6.3 — FortressValidator Check

```bash
# تست بحرانی: FortressValidator با مدل جدید کار می‌کند؟
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

from mahoun.core.fortress_validator import validate_reasoning_response, ExecutionMode
from mahoun.core.models import ReasoningResponse

# تست response
response = ReasoningResponse(
    success=True,
    verdict="Test verdict",
    reasoning_steps=["Step 1", "Step 2"],
    confidence=0.90,
    agreement_score=0.88,
    symbolic_confidence=0.89,
    neural_confidence=0.87,
    proof_tree={"root": "test"},
    execution_mode=ExecutionMode.DESKTOP_MINIMAL,
    provenance_id="smoke-test"
)

result = validate_reasoning_response(response, ExecutionMode.DESKTOP_MINIMAL)

if not result.is_valid:
    print("❌ FortressValidator FAILED")
    sys.exit(1)

print("✅ FortressValidator operational with new model")
EOF
```

#### 6.4 — Load Test (مختصر)

```bash
# تست بار محدود (5 requests متوالی)
for i in {1..5}; do
    echo "Request $i..."
    curl -s -X POST http://localhost:8000/api/v1/reasoning \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"Test query $i\", \"facts\": []}" \
      > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Success"
    else
        echo "  ❌ Failed"
        exit 1
    fi
done

echo "✅ Load test passed (5/5 requests)"
```

---

### مرحله 7: Monitoring (24 Hours)

بعد از به‌روزرسانی، سیستم را برای 24 ساعت monitor کنید:

```bash
# بررسی logs برای errors
docker-compose logs -f --tail=100 mahoun-backend

# بررسی memory usage
docker stats --no-stream

# بررسی metrics (اگر Prometheus دارید)
curl http://localhost:8000/metrics | grep -E "(memory|latency|error)"
```

**Checklist 24 Hours**:
- ✅ No crashes or restarts
- ✅ Memory usage stable (< 8 GB for desktop_minimal)
- ✅ Inference latency acceptable (< 30s)
- ✅ Agreement scores consistently ≥ 0.85
- ✅ No governance violations logged

---

## 🔄 Rollback Procedure (در صورت مشکل)

اگر مدل جدید مشکل دارد، فوراً به نسخه قبلی برگردید:

### Quick Rollback (< 5 minutes)

```bash
# محیط: server AirGapped

# Stop services
cd /home/haji/Desktop/KingMahouN
docker-compose down

# پیدا کردن آخرین backup
BACKUP_DIR="/home/haji/Desktop/KingMahouN/backups/models"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/llama-2-7b.Q6_K.gguf.backup_* | head -1)

echo "🔄 Rolling back to: $LATEST_BACKUP"

# Verify backup checksum
sha256sum -c "${LATEST_BACKUP}.sha256"

if [ $? -ne 0 ]; then
    echo "❌ CRITICAL: Backup checksum failed!"
    exit 1
fi

# Rollback atomic
MODELS_DIR="/home/haji/Desktop/KingMahouN/models"
cp "$LATEST_BACKUP" "$MODELS_DIR/llama-2-7b.Q6_K.gguf"

# Rollback manifest
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

from pathlib import Path
from mahoun.llm.model_versioning import get_versioning_system

manifest_path = Path("/home/haji/Desktop/KingMahouN/data/model_manifest.json")
vs = get_versioning_system(manifest_path)

# Rollback to backup
backup_path = Path("$LATEST_BACKUP")
manifest = vs.rollback_model(
    model_id="llama-2-7b-q6k",
    backup_path=backup_path
)

print(f"✅ Rolled back to version: {manifest.version}")
EOF

# Restart services
docker-compose up -d

echo "✅ Rollback complete. Verify with smoke test."
```

---

## 📝 Audit Trail & Documentation

### Log Entry Template

بعد از هر به‌روزرسانی، entry زیر را در log ثبت کنید:

```
=================================================================
MAHOUN Model Update Log Entry
=================================================================
Date: 2024-01-15 12:00 UTC
Model: Llama-2-7B-Q6_K
Operation: UPDATE
Status: SUCCESS
Performed by: admin
Approved by: security_team

Pre-update:
  - Model: Llama-2-7B-Q5_K v1.0.0
  - Checksum: abc123...
  - Backup: llama-2-7b.Q6_K.gguf.backup_20240115_120000

Post-update:
  - Model: Llama-2-7B-Q6_K v2.0.0
  - Checksum: e3b0c4...
  - Verification: PASSED
  - Smoke test: PASSED
  - FortressValidator: OPERATIONAL

Rollback info:
  - Backup location: /backups/models/llama-2-7b.Q6_K.gguf.backup_20240115_120000
  - Backup checksum: verified

Notes:
  - Zero downtime achieved
  - No governance violations
  - 24h monitoring initiated

=================================================================
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: Checksum Mismatch

**علت**: فایل در حین انتقال corrupt شده  
**راه حل**: 
```bash
# دانلود دوباره مدل در محیط آنلاین
# re-transfer با USB جدید
# verify checksum قبل از USB ejection
```

### Issue 2: Insufficient Disk Space

**علت**: فضای کافی برای backup + staging  
**راه حل**:
```bash
# پاک کردن backups قدیمی (بعد از 30 روز):
find /home/haji/Desktop/KingMahouN/backups/models -name "*.backup_*" -mtime +30 -delete

# یا انتقال backups به storage جدا
```

### Issue 3: FortressValidator Fails After Update

**علت**: مدل جدید output format متفاوت دارد  
**راه حل**:
```bash
# فوراً rollback کنید
# بررسی model compatibility guide
# test در محیط staging قبل از production
```

### Issue 4: Model Loading Timeout

**علت**: مدل بزرگتر از memory است  
**راه حل**:
```bash
# استفاده از quantized version کوچکتر (Q4_K به جای Q6_K)
# یا افزایش RAM
```

---

## 🎓 Best Practices

### DO ✅:
- ✅ همیشه checksum verify کنید (3 بار: download, transfer, install)
- ✅ همیشه backup بگیرید قبل از update
- ✅ smoke test بعد از هر update
- ✅ 24h monitoring بعد از update
- ✅ audit log کامل نگه دارید
- ✅ rollback procedure را test کنید (قبل از نیاز واقعی)

### DON'T ❌:
- ❌ هیچ‌وقت checksum verification را skip نکنید
- ❌ بدون backup update نکنید
- ❌ production را بدون staging test update نکنید
- ❌ rollback procedure را untested نگه ندارید
- ❌ audit trail را incomplete نگذارید

---

## 📞 Support & Escalation

اگر مشکلی پیش آمد:

1. **فوراً Rollback کنید** (safety first)
2. Logs را collect کنید:
   ```bash
   docker-compose logs > rollback_incident_$(date +%Y%m%d_%H%M%S).log
   ```
3. مشکل را document کنید (علت، اقدامات، نتیجه)
4. به تیم فنی گزارش دهید

---

## 📚 مستندات مرتبط

- [AIRGAPPED_DEPLOYMENT_CRITICAL_GAPS.md](../../AIRGAPPED_DEPLOYMENT_CRITICAL_GAPS.md)
- [Model Versioning API](../../mahoun/llm/model_versioning.py)
- [FortressValidator](../../mahoun/core/fortress_validator.py)
- [Health Check API](../../api/routers/health_v2.py)

---

**امضا**: MAHOUN Engineering Team  
**نسخه**: 1.0.0  
**آخرین به‌روزرسانی**: 1405/03/20  
**وضعیت**: ✅ REVIEWED & APPROVED
