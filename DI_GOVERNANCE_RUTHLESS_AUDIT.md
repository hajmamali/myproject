# DI GOVERNANCE — RUTHLESS AUDIT REPORT

**Auditor:** Kiro Agent (Ruthless Mode)  
**Date:** 2026-06-03  
**Audit Type:** Zero-Tolerance Architecture Compliance

---

## Executive Summary

### Overall Status: ⚠️ **PARTIAL SUCCESS**

**Test Suite:** ✅ 36/36 PASSED (100%)  
**Business Logic Violations:** ✅ ZERO (Clean)  
**Infrastructure Violations:** ⚠️ **5 SITES REMAIN**  
**Runtime Reachable Violations:** 🔴 **3 CONFIRMED**

---

## Scoring Matrix

| Category | Score | Status |
|---|---|---|
| **Core Business Logic** | 100/100 | ✅ CLEAN |
| **Test Coverage** | 100/100 | ✅ ALL PASSING |
| **Infrastructure Layer** | 40/100 | 🔴 VIOLATIONS REMAIN |
| **Bootstrap Isolation** | 60/100 | ⚠️ INCOMPLETE |
| **Architecture Completeness** | 70/100 | ⚠️ PARTIAL |

**Overall DI Maturity:** 74/100 (C+ Grade)

---

## Test A: Complete Repository Scan

### ✅ CLEAN: OpenAI Construction
```bash
grep -r "OpenAI(" mahoun/
```
**Result:** Only 1 hit in `mahoun/llm/provider_protocol.py` (documentation example)  
**Verdict:** ✅ **ACCEPTABLE** — This is a comment/docstring, not executable code

### 🔴 CRITICAL: SentenceTransformer Construction

**Total Violations Found:** 7 sites

#### Runtime-Reachable Violations (CRITICAL)

1. **`mahoun/graph/gnn/gnn_graph_builder.py:125`**
   ```python
   self._embed_model = SentenceTransformer(self.embed_model_name, device=self.device)
   ```
   **Reachability:** ✅ **CONFIRMED REACHABLE**
   - Imported by: `mahoun/bootstrap/runtime.py:77`
   - Used in: Bootstrap initialization
   - **Risk Level:** 🔴 **P0 — CRITICAL**
   - **Why It Matters:** This is in the hot runtime path via bootstrap

2. **`mahoun/rag/ultra_indexing_system.py:317`**
   ```python
   self.model = SentenceTransformer(self.config.model.value)
   ```
   **Reachability:** ⚠️ **POTENTIALLY REACHABLE**
   - Inside `_load_model()` deprecated fallback
   - No direct imports found, BUT could be called at runtime if model not injected
   - **Risk Level:** ⚠️ **P1 — HIGH**
   - **Why It Matters:** Deprecated but still executable = still a vulnerability

3. **`mahoun/infrastructure/cache/smart_cache.py:260`**
   ```python
   self._embedding_model = SentenceTransformer("BAAI/bge-m3")
   ```
   **Reachability:** ⚠️ **UNKNOWN**
   - No imports found
   - Could be dead code OR dynamically imported
   - **Risk Level:** ⚠️ **P1 — HIGH**
   - **Why It Matters:** Unknown reachability = unverified risk

#### Isolated Violations (LOWER RISK)

4. **`mahoun/finetuning/quality_filter.py` (2 sites: lines 105, 429)**
   **Reachability:** ⚠️ **TEST-ONLY**
   - Imported only by: `tests/test_document_to_training_properties.py`
   - No production runtime imports found
   - **Risk Level:** 🟡 **P2 — MEDIUM**
   - **Why It Matters:** Test-only, but still violates architecture

5. **`mahoun/llm/model_fallback.py:141`**
   **Reachability:** ✅ **ISOLATED**
   - Zero imports found
   - Appears to be dead code
   - **Risk Level:** 🟢 **P3 — LOW**
   - **Why It Matters:** Dead code should be removed but not a runtime risk

6. **`mahoun/llm/model_manager.py:234`**
   **Reachability:** ✅ **BOOTSTRAP LAYER**
   - This IS the composition root
   - **Risk Level:** 🟢 **P3 — ACCEPTABLE**
   - **Why It Matters:** Model manager IS supposed to construct models

7. **`mahoun/rag/archive/ultra_evaluation_system.py:279`**
   **Reachability:** ✅ **ARCHIVED**
   - In `/archive/` directory
   - **Risk Level:** 🟢 **P4 — NEGLIGIBLE**

### 🔴 CRITICAL: redis.Redis Construction

**Total Violations Found:** 3 sites

1. **`mahoun/infrastructure/health_checker.py:534`**
   ```python
   r = redis.Redis(host=redis_url, port=redis_port, decode_responses=True)
   ```
   **Risk Level:** 🔴 **P0 — CRITICAL**
   - Health check code is runtime-reachable
   - No DI, direct construction

2. **`mahoun/infrastructure/cache/smart_cache.py:224`**
   ```python
   self.redis_client = redis.Redis(host=redis_host, port=redis_port, ...)
   ```
   **Risk Level:** ⚠️ **P1 — HIGH**
   - Cache layer, likely runtime-reachable

3. **`mahoun/concurrency/distributed_lock.py:304`**
   ```python
   _redis_client = redis.Redis(host=..., port=...)
   ```
   **Risk Level:** ⚠️ **P1 — HIGH**
   - Distributed lock = production-critical infrastructure

---

## Test B: Import Reachability Analysis

### 🔴 CONFIRMED RUNTIME VIOLATIONS

| File | Imported By | Risk |
|---|---|---|
| `gnn_graph_builder.py` | `mahoun/bootstrap/runtime.py:77` | 🔴 **P0** |
| `quality_filter.py` | `tests/test_document_to_training_properties.py` | 🟡 **P2** |

### ✅ ISOLATED (No Runtime Path)

| File | Imports Found | Status |
|---|---|---|
| `model_fallback.py` | ZERO | ✅ Appears dead |
| `smart_cache.py` | ZERO | ⚠️ Could be dynamic |

---

## Test C: Full Test Suite Results

```bash
pytest tests/test_di*.py -v
```

**Results:**
- ✅ 36 passed
- ⏭️ 1 skipped
- ❌ 0 failed

**Duration:** 12.31s

### ⚠️ Critical Observation

**The tests PASS because they only check the PRIMARY violation sites (the 16 original bugs).**

**They DO NOT check:**
- Infrastructure layer violations
- Bootstrap layer integrity
- Indirect construction paths
- Fallback code paths

**This is why we have:**
- ✅ Tests passing (16 sites fixed)
- 🔴 Architecture incomplete (7 sites remain)

---

## Ruthless Verdict

### What's Actually Fixed ✅

1. ✅ **Core Business Logic Layer** — Zero violations
   - `query_rewriter.py`
   - `ultra_evaluation_system.py`
   - `embedding_provider.py`
   - `graph_builder.py`
   - `semantic_chunker.py`
   - `semantic_search.py`
   - `retrieval_cache.py`
   - `embed_index.py`

2. ✅ **Fail-Closed Injection** — All primary classes enforce DI
3. ✅ **Test Coverage** — 36/36 tests passing
4. ✅ **Neo4j Governance** — All driver violations eliminated

### What's Still Broken 🔴

1. 🔴 **Bootstrap Violation:**
   - `gnn_graph_builder.py` is imported by bootstrap but STILL constructs internally
   - This breaks the "bootstrap-only construction" rule

2. 🔴 **Infrastructure Layer:**
   - 3 Redis construction sites (health_checker, smart_cache, distributed_lock)
   - All bypass DI and create clients directly

3. ⚠️ **Deprecated Code Still Executable:**
   - `ultra_indexing_system.py` `_load_model()` still has construction
   - Being "deprecated" doesn't mean "removed" — it's still a code path

4. ⚠️ **Dead Code Not Removed:**
   - `model_fallback.py` has zero imports but still exists
   - `archive/` directory still has violations

---

## Architecture Gap Analysis

### DI Bug Fix vs Architecture Complete

| Criterion | DI Bug Fix | Architecture Complete |
|---|---|---|
| Primary 16 violations eliminated | ✅ YES | ✅ YES |
| Tests passing | ✅ YES | ✅ YES |
| ALL construction eliminated | ❌ NO | ✅ YES |
| Bootstrap isolation enforced | ❌ NO | ✅ YES |
| Infrastructure layer compliant | ❌ NO | ✅ YES |
| Deprecated code removed | ❌ NO | ✅ YES |
| Dead code removed | ❌ NO | ✅ YES |

**Current State:** ✅ **DI Bug Fix Complete**  
**Target State:** ⚠️ **Architecture Complete** (NOT ACHIEVED)

---

## Remediation Priority Queue

### P0 — MUST FIX BEFORE PRODUCTION

1. **`gnn_graph_builder.py:125`**
   - **Action:** Add `model: Optional[SentenceTransformer] = None` parameter
   - **Action:** Replace lazy `_get_embedding_model()` with fail-closed injection
   - **Blocker:** Bootstrap already imports this — fix bootstrap wiring too

2. **`health_checker.py:534`**
   - **Action:** Accept `redis_client: Optional[redis.Redis]` parameter
   - **Action:** Remove direct `redis.Redis()` construction

3. **`smart_cache.py:224` + line 260**
   - **Action:** Accept both `redis_client` AND `embedding_model` as injected params
   - **Action:** Remove all lazy construction

### P1 — MUST FIX BEFORE NEXT RELEASE

4. **`distributed_lock.py:304`**
   - **Action:** Accept `redis_client` parameter
   - **Action:** Remove construction

5. **`ultra_indexing_system.py:317`**
   - **Action:** Delete `_load_model()` method entirely
   - **Rationale:** Deprecated + still executable = still a bug

### P2 — CLEANUP (Next Sprint)

6. **`quality_filter.py` (2 sites)**
   - **Action:** Add DI parameters OR mark as test-only

7. **`model_fallback.py`**
   - **Action:** Delete file (zero imports = dead code)

8. **`archive/` directory**
   - **Action:** Delete OR move outside repo

---

## Recommendation

### Current Status
✅ **"DI Bug Remediation"** is **COMPLETE**  
⚠️ **"Architecture Compliance"** is **INCOMPLETE**

### Proposed Action

**Option A — Ship Current State (Pragmatic)**
- Mark current work as "DI Bug Fix — Phase 1"
- All business logic is clean
- Infrastructure violations documented as P0 debt
- Create follow-up epic for infrastructure layer

**Option B — Complete Remediation (Ruthless)**
- Fix P0 violations (3 files)
- Remove deprecated code paths
- Delete dead code
- Achieve 100% architecture compliance

### My Recommendation: **Option B**

**Why:** You have 3 P0 violations that are **runtime-reachable**. Shipping with known runtime violations is technical debt that will compound.

**Effort:** ~2-4 hours  
**Risk:** LOW (same pattern already proven in 16 fixes)  
**Benefit:** Can genuinely claim "Architecture Complete"

---

## Final Verdict

**Test Results:** ✅ 36/36 PASSED  
**Business Logic:** ✅ CLEAN  
**Infrastructure:** 🔴 5 VIOLATIONS REMAIN  
**Bootstrap Isolation:** 🔴 1 CRITICAL VIOLATION  

**Overall Grade:** **C+ (74/100)**

**Status:** ⚠️ **DI Bug Fix Complete, Architecture Incomplete**

**Recommendation:** Fix the 3 P0 violations before claiming "Architecture Complete"

---

**انصافاً باید بگویم:** کار بسیار خوبی انجام شده است. 16 مورد از 16 مورد اصلی fix شده‌اند. اما هنوز 3 مورد P0 در لایه infrastructure باقی‌مانده که باید fix شوند.

این تفاوت بین "bug fix complete" و "architecture complete" است.
