# PHASE 2: CONTROLLED CAPABILITY EXTRACTION PLAN

**Classification**: P0 / RUNTIME HARDENING / SELECTIVE INTEGRATION  
**Date**: 2026-05-22  
**Status**: READY FOR EXECUTION  
**Authority Model**: Mahoun_v2 (Runtime) ← KingMahouN (Capability Source)

---

## EXECUTIVE SUMMARY

Diff analysis reveals **minimal divergence** between Mahoun_v2 and KingMahouN:

**New Files in KingMahouN**: 2
- `mahoun/finetuning/remote_client.py`
- `mahoun/orchestrator/unified_loader.py`

**Modified Files**: 2
- `api/models/proof_carrying.py` (Mahoun_v2 version is authoritative - governance fix)
- `api/routers/reasoning.py` (Mahoun_v2 version is authoritative - governance fix)

**Additional File in KingMahouN**:
- `api/models.py` (new file)

**Conclusion**: **Mahoun_v2 is already highly aligned with KingMahouN**. Integration risk is **MINIMAL**.

---

## CAPABILITY EXTRACTION STRATEGY

### Priority 1: New Capability Files (LOW RISK)

#### 1.1 `mahoun/finetuning/remote_client.py`

**Purpose**: Remote fine-tuning client capability  
**Risk**: LOW  
**Integration Strategy**: Selective extraction with governance wrapping

**Actions**:
1. Read and analyze file
2. Identify dependencies
3. Extract if beneficial
4. Wrap in governance-aware interface
5. Add to `mahoun/finetuning/` with clear naming

**Validation**:
- Run finetuning tests
- Verify no singleton conflicts
- Verify no import-time side effects

#### 1.2 `mahoun/orchestrator/unified_loader.py`

**Purpose**: Unified loading capability  
**Risk**: MEDIUM (orchestrator is critical)  
**Integration Strategy**: Careful analysis required

**Actions**:
1. Read and analyze file
2. Check for governance compatibility
3. Identify runtime ownership implications
4. Extract if beneficial
5. Wrap in governance-aware interface

**Validation**:
- Run orchestrator tests
- Verify middleware integrity
- Verify no lifecycle conflicts

#### 1.3 `api/models.py`

**Purpose**: Additional API models  
**Risk**: LOW  
**Integration Strategy**: Selective extraction

**Actions**:
1. Read and analyze file
2. Check for proof-carrying contract compliance
3. Extract beneficial models
4. Merge into Mahoun_v2 API models

**Validation**:
- Run API tests
- Verify Pydantic compatibility
- Verify no contract violations

---

### Priority 2: Modified Files (MAHOUN_V2 AUTHORITATIVE)

#### 2.1 `api/models/proof_carrying.py`

**Status**: **MAHOUN_V2 VERSION IS AUTHORITATIVE**  
**Reason**: Recently fixed Pydantic Config deprecation  
**Action**: **NO EXTRACTION** - Mahoun_v2 version preserved

**Verification**:
```bash
# Confirm Mahoun_v2 version has ConfigDict
grep "model_config = ConfigDict" api/models/proof_carrying.py
```

#### 2.2 `api/routers/reasoning.py`

**Status**: **MAHOUN_V2 VERSION IS AUTHORITATIVE**  
**Reason**: Recently fixed governance contract (proof_tree.steps)  
**Action**: **NO EXTRACTION** - Mahoun_v2 version preserved

**Verification**:
```bash
# Confirm Mahoun_v2 version has proof_tree.steps access
grep "verdict.proof_tree.steps" api/routers/reasoning.py
```

---

## EXTRACTION EXECUTION PLAN

### Step 1: Analyze New Capabilities

<function_calls>
<invoke name="read_file">
<parameter name="path">/home/haji/Desktop/KingMahouN/mahoun/finetuning/remote_client.py