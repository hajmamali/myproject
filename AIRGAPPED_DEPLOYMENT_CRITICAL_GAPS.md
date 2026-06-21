# MAHOUN — شکاف‌های بحرانی برای استقرار AirGapped

**تاریخ**: 1405/03/20  
**سناریو استقرار**: 🔒 **AIRGAPPED** (بدون دسترسی اینترنت)  
**وضعیت**: 🔴 **CRITICAL — شکاف‌های جدید شناسایی شد**

---

## ⚠️ تغییر حکم با توجه به AirGap

### حکم قبلی (اشتباه):
> "سیستم برای production آماده نیست — 2 شکست بحرانی"

### حکم جدید (با AirGap):
> **سیستم برای AirGapped deployment بهتر از حالت cloud آماده است**  
> اما **4 شکاف بحرانی جدید** شناسایی شد

---

## چرا AirGap وضعیت را تغییر می‌دهد؟

### ✅ مزایا (ریسک‌های کاهش‌یافته):

1. **GAP-02 (Vendor Lock-in) → حل شد** ✅
   - در AirGap، شما **مجبورید** از local LLM استفاده کنید
   - OpenAI API در دسترس نیست
   - بنابراین model independence **از طراحی** اجباری است
   - **ریسک**: از 🔴 P0 CRITICAL → 🟢 LOW

2. **Scaling به مشکل کمتری تبدیل می‌شود** ✅
   - محیط AirGap معمولاً کاربران محدود دارد (10-50، نه 1000)
   - Load predictable است (داخلی، نه public)
   - **ریسک**: از 🔴 P0 CRITICAL → 🟡 P1 MEDIUM

3. **Security بهتر است** ✅
   - هیچ external API call نیست
   - هیچ data exfiltration risk نیست
   - Network attack surface = صفر

### 🔴 شکاف‌های جدید (ریسک‌های افزوده):

اما AirGap **4 شکاف بحرانی جدید** معرفی می‌کند که **تست نشده‌اند**:

---

## 🔴 شکاف بحرانی جدید #1: Local LLM Dependency Hell

### مشکل:
در AirGap، شما **نمی‌توانید** به OpenAI متصل شوید. باید از local LLM استفاده کنید.

### سوالات بدون پاسخ:
```python
❌ آیا سیستم با local LLM کار می‌کند؟
❌ FortressValidator با local LLM outputs کار می‌کند؟
❌ Local LLM quality کافی برای governance است؟
❌ Memory footprint local LLM در desktop_minimal fit می‌شود؟
❌ Inference latency قابل قبول است؟
```

### ریسک واقعی:
```
سناریو: AirGapped deployment روز 1
- OpenAI API unavailable (expected)
- Fallback به local LLM
- Local LLM output format متفاوت است
- FortressValidator fail → همه verdicts rejected
- سیستم غیرقابل استفاده
```

### مدرک موجود:
```python
# mahoun/llm/provider_protocol.py:14
# "Airgap-First": MAHOUN must work without external API access
```
- ✅ Design principle وجود دارد
- ❌ **هیچ تستی** این را verify نمی‌کند

### اقدام الزامی:
```bash
# تست جدید: AirGapped local LLM operation
tests/stress/test_airgapped_llm_operation.py

# باید verify کند:
1. Local LLM (e.g., Llama 3) can generate verdicts
2. FortressValidator accepts local LLM outputs
3. Agreement scores ≥ 0.85 achievable
4. Memory usage < 8 GB (desktop_minimal)
5. Inference latency < 30s per verdict
```

**مهلت**: 1 هفته (قبل از هر deployment)

---

## 🔴 شکاف بحرانی جدید #2: Offline Model Update/Versioning

### مشکل:
در AirGap، شما **نمی‌توانید** models را از HuggingFace download کنید.

### سوالات بدون پاسخ:
```python
❌ چگونه models را update می‌کنید؟
❌ آیا model versioning system وجود دارد؟
❌ چگونه از model corruption جلوگیری می‌کنید؟
❌ آیا model rollback ممکن است؟
❌ Checksum verification برای models وجود دارد؟
```

### ریسک واقعی:
```
سناریو: Model update در AirGap
- شما model جدید را روی USB stick کپی می‌کنید
- Model corrupt شده است (bad transfer)
- هیچ checksum verification نیست
- Model load می‌شود اما garbage output می‌دهد
- FortressValidator همه را reject می‌کند
- System unusable تا rollback manual
```

### مدرک موجود:
- ❌ **هیچ model versioning system یافت نشد**
- ❌ **هیچ checksum verification یافت نشد**
- ❌ **هیچ offline update procedure یافت نشد**

### اقدام الزامی:
```python
# 1. Model versioning system
mahoun/llm/model_versioning.py:
  - Model manifest با checksum
  - Version compatibility check
  - Rollback mechanism

# 2. Offline update procedure
docs/deployment/AIRGAPPED_MODEL_UPDATE.md:
  - Step-by-step update process
  - Checksum verification
  - Rollback procedure

# 3. Test
tests/stress/test_offline_model_update.py:
  - Simulate USB stick model transfer
  - Verify checksum validation
  - Test rollback on corruption
```

**مهلت**: 2 هفته

---

## 🔴 شکاف بحرانی جدید #3: Embedding Model Portability

### مشکل:
در AirGap، embedding model باید **pre-downloaded** باشد.

### سوالات بدون پاسخ:
```python
❌ آیا embedding model با documents offline کار می‌کند؟
❌ Vector store index offline rebuild می‌شود؟
❌ Semantic search quality در offline mode چگونه است؟
❌ چگونه embedding model را update می‌کنید؟
```

### ریسک واقعی:
```
سناریو: ChromaDB در AirGap
- Embedding model pre-loaded است
- 1000 legal documents upload می‌شوند
- Vector index build می‌شود
- Search quality ضعیف است (model/data mismatch)
- RAG pipeline unusable
```

### مدرک موجود:
```python
# mahoun/graph/retriever/embedding_provider.py
# Code exists for local embeddings
```
- ✅ Code برای local embeddings وجود دارد
- ❌ **هیچ تستی** offline operation را verify نمی‌کند

### اقدام الزامی:
```bash
# تست: Offline embedding + RAG
tests/stress/test_airgapped_rag_pipeline.py

# باید verify کند:
1. Local embedding model loads successfully
2. 100 docs can be indexed offline
3. Search quality acceptable (precision@5 > 0.7)
4. Index rebuild works without internet
5. Model swap procedure documented
```

**مهلت**: 1 هفته

---

## 🔴 شکاف بحرانی جدید #4: NLI Model Offline Operation

### مشکل:
FortressValidator از NLI model (microsoft/deberta-v3-base) برای contradiction detection استفاده می‌کند.

### سوالات بدون پاسخ:
```python
❌ آیا NLI model در offline mode load می‌شود؟
❌ Contradiction detection در AirGap کار می‌کند؟
❌ Model weights pre-downloaded هستند؟
❌ Fallback اگر NLI model missing باشد چیست؟
```

### ریسک واقعی:
```
سناریو: FortressValidator در AirGap
- NLI model import می‌شود
- HuggingFace download attempt → timeout
- Contradiction detection fails
- Agreement score calculation broken
- همه verdicts rejected (< 0.85 threshold)
```

### مدرک موجود:
```python
# mahoun/guardrails/ultra_nli_verifier.py
# Uses transformers.AutoModel
```
- ⚠️ Code از HuggingFace transformers استفاده می‌کند
- ❌ **هیچ offline fallback یافت نشد**
- ❌ **هیچ pre-download verification یافت نشد**

### اقدام الزامی:
```bash
# 1. Pre-download verification
scripts/verify_offline_models.py:
  - Check all required models present
  - Verify checksums
  - Test load without internet

# 2. Offline mode enforcement
mahoun/guardrails/ultra_nli_verifier.py:
  - Disable HuggingFace auto-download
  - Force local-only model loading
  - Clear error if model missing

# 3. Test
tests/governance/test_nli_offline_operation.py:
  - Mock network unavailable
  - Verify NLI loads from cache
  - Test contradiction detection works
```

**مهلت**: 3 روز (URGENT)

---

## 🟡 شکاف‌های اضافی (Medium Priority برای AirGap)

### GAP-5: PostgreSQL/Redis/Neo4j Dependencies
```
در AirGap، همه database engines باید local باشند.
آیا docker-compose برای offline deployment tested است؟
```

### GAP-6: Certificate Management
```
در AirGap، certificate renewal چگونه است؟
Self-signed certs برای internal use OK است؟
```

### GAP-7: Monitoring & Alerting
```
در AirGap، monitoring به کجا می‌رود؟
External log aggregation unavailable.
Internal Prometheus/Grafana tested است؟
```

---

## برنامه اجرایی برای AirGap (بازنگری شده)

### هفته 1 (CRITICAL — Non-negotiable):
```
روز 1-2: ✅ Verify local LLM operation
        پیاده‌سازی test_airgapped_llm_operation.py
        Test با Llama 3 / Mistral

روز 3-4: ✅ Verify NLI offline operation
        پیاده‌سازی test_nli_offline_operation.py
        Test FortressValidator بدون internet

روز 5-7: ✅ Verify embedding offline operation
        پیاده‌سازی test_airgapped_rag_pipeline.py
        Test ChromaDB با local embeddings
```

### هفته 2 (HIGH — Infrastructure):
```
روز 1-3: ✅ Model versioning system
        mahoun/llm/model_versioning.py
        Checksum verification

روز 4-5: ✅ Offline update procedure
        docs/deployment/AIRGAPPED_MODEL_UPDATE.md
        Step-by-step guide

روز 6-7: ✅ Database offline deployment
        Test docker-compose در isolated network
        Verify all services start without internet
```

### هفته 3 (MEDIUM — Nice to Have):
```
روز 1-3: Certificate management
روز 4-5: Monitoring setup
روز 6-7: Full integration test (simulated AirGap)
```

---

## معیارهای موفقیت برای AirGap Deployment

### Pre-Deployment Checklist:
```
✅ Local LLM generates valid verdicts
✅ FortressValidator accepts local LLM outputs
✅ Agreement scores ≥ 0.85 achievable offline
✅ NLI model loads without internet
✅ Contradiction detection works offline
✅ ChromaDB indexes 100 docs without internet
✅ Search quality acceptable (precision@5 > 0.7)
✅ All models checksummed and verified
✅ Model versioning system operational
✅ Offline update procedure documented
✅ Database stack starts without internet
✅ Full smoke test در simulated AirGap passes
```

### Runtime Requirements:
```
✅ Memory usage < 8 GB (desktop_minimal)
✅ Inference latency < 30s per verdict
✅ System stable for 24h continuous operation
✅ Graceful degradation if component fails
✅ Clear error messages (no vague "connection failed")
```

---

## تغییر اولویت‌ها برای AirGap

### ❌ اولویت‌های قبلی (نادرست برای AirGap):
1. 🔴 Scenario scaling (1→100 concurrent) — ~~P0 CRITICAL~~
2. 🔴 LLM model independence — ~~P0 CRITICAL~~

### ✅ اولویت‌های جدید (صحیح برای AirGap):
1. 🔴 **Local LLM operation** — P0 CRITICAL ⚡
2. 🔴 **NLI offline operation** — P0 CRITICAL ⚡
3. 🔴 **Embedding offline operation** — P0 CRITICAL ⚡
4. 🔴 **Model versioning system** — P0 CRITICAL
5. 🟡 Offline update procedure — P1 HIGH
6. 🟡 Database offline deployment — P1 HIGH
7. 🟢 Scenario scaling — P2 MEDIUM (کاربران محدود در AirGap)

---

## حکم نهایی (بازنگری شده)

### برای AirGapped Deployment:

**مثبت**: ✅
- معماری شما برای offline **طراحی شده**
- Governance kernel offline-first است
- Security posture در AirGap **عالی** است
- Vendor lock-in risk **حل شده**

**منفی**: 🔴
- **هیچ تستی** offline operation را verify نمی‌کند
- Local LLM integration **تست نشده**
- NLI offline mode **تست نشده**
- Model update procedure **وجود ندارد**

### حکم:
```
سیستم برای AirGap *طراحی* شده، اما *تست نشده*.

4 شکاف بحرانی offline operation یافت شد.
3 هفته برای fix + verification.

Deploy نکنید تا این 4 gap را close کنید.
```

---

## پیام نهایی به تیم

شما اطلاعات **بسیار مهمی** به من دادید. AirGap deployment تحلیل را **کاملاً تغییر می‌دهد**.

**خبر خوب**: معماری شما برای AirGap **مناسب** است.

**خبر بد**: شما **هیچ مدرکی** ندارید که در AirGap کار می‌کند.

**اقدام**: 4 تست بحرانی offline → 3 هفته → AirGap ready

**جایگزین**: Deploy بدون verification → سیستم در روز 1 fail می‌کند

---

**امضا**: Kiro AI Agent  
**وضعیت**: 🔴 REVISED BASED ON AIRGAP CONTEXT  
**اولویت**: تست offline operation > تست scaling

