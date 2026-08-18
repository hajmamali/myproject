# AIRGAP PHASE 1 REMEDIATION — P0 CRITICAL FIXES

**Date**: 2026-06-11  
**Phase**: 1 of 3 (Critical Air-Gap Compliance)  
**Duration**: 1 week  
**Status**: 🟡 IN PROGRESS  
**Priority**: 🔴 P0 PRODUCTION BLOCKER

---

## Manifest Summary

**Objective**: Block ALL network calls in MAHOUN codebase for air-gapped deployment

**Scope**:
- ✅ IN: All `from_pretrained()` calls across 10+ files
- ✅ IN: OCR engine auto-download prevention
- ✅ IN: ChromaDB telemetry disabling
- ❌ OUT: Architecture cleanup (Phase 2)
- ❌ OUT: Documentation improvements (Phase 3)

**Risk Level**: **HIGH** — Production blocker, but changes are surgical and testable

---

## P0 Blockers Identified

### BLOCKER-1: ModelManager Air-Gap Violations
**File**: `mahoun/llm/model_manager.py`  
**Lines**: 241-252, 286-289  
**Issue**: Missing `local_files_only=True` in 3 locations  
**Impact**: System attempts HuggingFace downloads in air-gap → CRASH

### BLOCKER-2: OCRHandler Auto-Downloads  
**File**: `mahoun/pipelines/ingestion/ocr_handler.py`  
**Lines**: 90, 118  
**Issue**: PaddleOCR and EasyOCR missing local model directory overrides  
**Impact**: First OCR call triggers 500MB+ downloads

### BLOCKER-3: DocumentClassifier HuggingFace Downloads  
**File**: `mahoun/graph/ingestion/document_classifier.py`  
**Lines**: 717-718  
**Issue**: Unprotected `from_pretrained()` calls  
**Impact**: Graph construction blocked in air-gap

### BLOCKER-4: SemanticChunker NER Pipeline  
**File**: `mahoun/graph/gnn/semantic_chunker.py`  
**Lines**: 175-176  
**Issue**: NER pipeline auto-downloads models  
**Impact**: Document chunking fails in air-gap

### BLOCKER-5: NLI Verifier HuggingFace Downloads  
**File**: `mahoun/guardrails/ultra_nli_verifier.py`  
**Lines**: 97-98  
**Issue**: Missing `local_files_only=True`  
**Impact**: FortressValidator fails → ALL verdicts rejected

### BLOCKER-6: Additional Model Loading Points
**Files**:
- `mahoun/pipelines/retrieve_rag.py` (Lines 303-308)
- `mahoun/rag/ultra_indexing_system.py` (Lines 401-402)
- `mahoun/llm/model_fallback.py` (Lines 152-153)
- `mahoun/llm/ultra_loader.py` (Lines 26-32)

**Total locations**: **10 files, 15+ call sites**

---

## Remediation Plan (Step-by-Step)

### Step 1: Fix ModelManager (CRITICAL)
**File**: `mahoun/llm/model_manager.py`

**Changes**:
```python
# Line 241-244 (NLI model loading)
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    cache_dir=self.cache_dir,
    local_files_only=True,  # ← ADD THIS
    **self._get_quantization_config(),
    **kwargs
)

# Line 249-253 (General model loading)
model = AutoModel.from_pretrained(
    model_name,
    cache_dir=self.cache_dir,
    local_files_only=True,  # ← ADD THIS
    **self._get_quantization_config(),
    **kwargs
)

# Line 286-290 (Tokenizer loading)
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    cache_dir=self.cache_dir,
    local_files_only=True,  # ← ADD THIS
    **kwargs
)
```

**Test**: Run `tests/stress/test_airgapped_llm_operation.py`

---

### Step 2: Fix DocumentClassifier
**File**: `mahoun/graph/ingestion/document_classifier.py`

**Changes**:
```python
# Line 717-718
self.tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    local_files_only=True  # ← ADD THIS
)
self.model = AutoModel.from_pretrained(
    model_name,
    local_files_only=True  # ← ADD THIS
)
```

**Test**: Verify with document classification tests

---

### Step 3: Fix SemanticChunker
**File**: `mahoun/graph/gnn/semantic_chunker.py`

**Changes**:
```python
# Line 175-176
tokenizer = AutoTokenizer.from_pretrained(
    ner_model,
    local_files_only=True  # ← ADD THIS
)
model = AutoModelForTokenClassification.from_pretrained(
    ner_model,
    local_files_only=True  # ← ADD THIS
)
```

**Test**: Verify with graph construction tests

---

### Step 4: Fix NLI Verifier (CRITICAL for FortressValidator)
**File**: `mahoun/guardrails/ultra_nli_verifier.py`

**Changes**:
```python
# Line 97-98
self.tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    local_files_only=True  # ← ADD THIS
)
self.model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    output_attentions=True,
    local_files_only=True  # ← ADD THIS
)
```

**Test**: Run `tests/governance/test_nli_offline_operation.py`

---

### Step 5: Fix OCRHandler (Model Directory Overrides)
**File**: `mahoun/pipelines/ingestion/ocr_handler.py`

**Changes**:
```python
# Line 90 (PaddleOCR)
self.paddle_ocr = PaddleOCR(
    use_angle_cls=True,
    lang='fa',
    det_model_dir=os.getenv('PADDLE_DET_MODEL_DIR', '/app/models/paddle/det'),
    rec_model_dir=os.getenv('PADDLE_REC_MODEL_DIR', '/app/models/paddle/rec'),
    cls_model_dir=os.getenv('PADDLE_CLS_MODEL_DIR', '/app/models/paddle/cls'),
    use_gpu=False
)

# Line 118 (EasyOCR)
self.easyocr_reader = self._easyocr_module.Reader(
    ['fa', 'en'],
    gpu=False,
    model_storage_directory=os.getenv('EASYOCR_MODEL_DIR', '/app/models/easyocr'),
    download_enabled=False  # ← CRITICAL
)
```

**Test**: Verify with OCR tests

---

### Step 6: Fix Remaining Model Loading Points

**File**: `mahoun/pipelines/retrieve_rag.py` (Lines 303-308)
```python
_RERANK_TOKENIZER = AutoTokenizer.from_pretrained(
    self.cfg.rerank_model,
    local_files_only=True
)
_RERANK_MODEL = AutoModelForSequenceClassification.from_pretrained(
    self.cfg.rerank_model,
    local_files_only=True
)
```

**File**: `mahoun/rag/ultra_indexing_system.py` (Lines 401-402)
```python
self.model = CLIPModel.from_pretrained(
    self.config.model.value,
    local_files_only=True
)
self.tokenizer = CLIPProcessor.from_pretrained(
    self.config.model.value,
    local_files_only=True
)
```

**File**: `mahoun/llm/model_fallback.py` (Lines 152-153)
```python
model = AutoModel.from_pretrained(
    config.model_id,
    local_files_only=True
)
tokenizer = AutoTokenizer.from_pretrained(
    config.model_id,
    local_files_only=True
)
```

**File**: `mahoun/llm/ultra_loader.py` (Lines 26-32)
```python
tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    trust_remote_code=True,
    local_files_only=True
)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    local_files_only=True
)
```

---

### Step 7: ChromaDB Telemetry Disable

**Files to modify**: All ChromaDB instantiation points

**Search pattern**: `chromadb.PersistentClient` or `chromadb.Client`

**Change**:
```python
# Before:
client = chromadb.PersistentClient(path=persist_dir)

# After:
from chromadb.config import Settings
client = chromadb.PersistentClient(
    path=persist_dir,
    settings=Settings(anonymized_telemetry=False)
)
```

---

## Acceptance Criteria

### ✅ Must Pass Before Delivery:

1. **All `from_pretrained()` calls have `local_files_only=True`**
   - Verified via grep: `grep -r "from_pretrained(" --include="*.py" | grep -v "local_files_only"`
   - Result: ZERO matches outside tests

2. **OCR engines force local model paths**
   - PaddleOCR: `det_model_dir`, `rec_model_dir`, `cls_model_dir` set
   - EasyOCR: `download_enabled=False`

3. **ChromaDB telemetry disabled everywhere**
   - All instantiations use `Settings(anonymized_telemetry=False)`

4. **All air-gap tests pass**
   - `tests/stress/test_airgapped_llm_operation.py`: ≥90% pass rate
   - `tests/governance/test_nli_offline_operation.py`: ≥90% pass rate
   - `tests/stress/test_airgapped_rag_pipeline.py`: ≥90% pass rate

5. **Network isolation test passes**
   - Run system with `iptables -A OUTPUT -j REJECT`
   - System must start and function without network errors

---

## Tests to Run

```bash
# Activate venv
source /home/haji/Desktop/KingMahouN/venv/bin/activate

# Run air-gap test suite
pytest tests/stress/test_airgapped_llm_operation.py -v
pytest tests/governance/test_nli_offline_operation.py -v
pytest tests/stress/test_airgapped_rag_pipeline.py -v

# Verify no network calls (grep check)
grep -r "from_pretrained(" mahoun/ --include="*.py" | grep -v "local_files_only" | grep -v "#"

# Expected: Only test files and commented code
```

---

## Rollback Plan

**If any change breaks the system:**

1. **Git revert individual commits**
   ```bash
   git log --oneline -10  # Find commit hash
   git revert <commit_hash>
   ```

2. **Test suite verification**
   ```bash
   pytest tests/ -v --tb=short -x  # Stop on first failure
   ```

3. **Fallback to pre-Phase-1 state**
   ```bash
   git reset --hard <pre-phase-1-commit>
   ```

**Recovery time**: < 5 minutes (single file changes, easy revert)

---

## Risks & Mitigations

### Risk 1: Models not pre-downloaded
**Severity**: HIGH  
**Mitigation**: Pre-deployment verification script (Phase 3)  
**Workaround**: Clear error messages guide user to download models

### Risk 2: Bootstrap DI not validated
**Severity**: MEDIUM  
**Mitigation**: Add bootstrap validation test  
**Workaround**: System will fail-closed (good for security)

### Risk 3: Performance degradation
**Severity**: LOW  
**Mitigation**: `local_files_only=True` has NO performance impact  
**Workaround**: N/A

---

## Next Actions (Priority Order)

### Immediate (Today):
1. ✅ Review this manifest
2. ⬜ Implement ModelManager fixes (30 min)
3. ⬜ Implement DocumentClassifier fixes (15 min)
4. ⬜ Implement SemanticChunker fixes (15 min)
5. ⬜ Implement NLI Verifier fixes (15 min)

### Week 1 (P0 Completion):
1. ⬜ Implement OCRHandler fixes (1 hour)
2. ⬜ Implement remaining model loading fixes (2 hours)
3. ⬜ ChromaDB telemetry disable (1 hour)
4. ⬜ Run full air-gap test suite (2 hours)
5. ⬜ Network isolation test (1 hour)
6. ⬜ Code review + approval (4 hours)

**Total estimated time**: 1.5 days hands-on + 2.5 days testing/review = **4 days**

---

## Verification Commands

```bash
# 1. Grep verification (no unprotected from_pretrained)
grep -rn "from_pretrained(" mahoun/ --include="*.py" \
  | grep -v "local_files_only" \
  | grep -v "^#" \
  | grep -v "test_"

# Expected output: ZERO results

# 2. OCR directory verification
grep -rn "PaddleOCR(" mahoun/ --include="*.py" -A 3 \
  | grep "det_model_dir"

# Expected: All PaddleOCR calls have det_model_dir

# 3. ChromaDB telemetry verification
grep -rn "chromadb.PersistentClient" mahoun/ --include="*.py" -A 2 \
  | grep "anonymized_telemetry"

# Expected: All clients have anonymized_telemetry=False

# 4. Test execution
pytest tests/stress/test_airgapped_*.py tests/governance/test_nli_*.py -v --tb=short

# Expected: ≥90% pass rate (27/30 minimum)
```

---

## Files to Modify (Complete List)

```
P0 CRITICAL (10 files):
1. mahoun/llm/model_manager.py              (3 locations)
2. mahoun/graph/ingestion/document_classifier.py (2 locations)
3. mahoun/graph/gnn/semantic_chunker.py     (2 locations)
4. mahoun/guardrails/ultra_nli_verifier.py  (2 locations)
5. mahoun/pipelines/ingestion/ocr_handler.py (2 locations)
6. mahoun/pipelines/retrieve_rag.py         (2 locations)
7. mahoun/rag/ultra_indexing_system.py      (2 locations)
8. mahoun/llm/model_fallback.py             (2 locations)
9. mahoun/llm/ultra_loader.py               (2 locations)
10. [TBD: All ChromaDB instantiation points]

Total modifications: ~20 call sites across 10+ files
```

---

## Delivery Format

**Patch Size**: Small, surgical changes (1-2 lines per fix)  
**Review**: Easy to review (clear before/after)  
**Testing**: Isolated (each fix independently testable)  
**Deployment**: Low risk (fail-closed design)

---

## Certification

**Prepared by**: Kiro AI Agent (Principal Systems Architect Mode)  
**Date**: 2026-06-11  
**Phase**: 1 of 3  
**Confidence**: 95% (based on grep analysis + test coverage)  
**Production Impact**: CRITICAL — Blocks air-gap deployment until complete

---

**STATUS**: 🟡 **READY FOR IMPLEMENTATION**  
**NEXT**: Execute Step 1 (ModelManager fixes)

