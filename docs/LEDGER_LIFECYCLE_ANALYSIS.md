# LEDGER LIFECYCLE ANALYSIS

## Document Information
- **Title**: Ledger Lifecycle Analysis - Current vs. Target Architecture
- **Author**: Mistral Vibe CLI Agent (Senior Software Architect)
- **Date**: 2026-07-24
- **Phase**: 1 - Architecture Analysis Only
- **Mission**: MAHOUN Ledger Integrity Trust Gap Resolution
- **Status**: ANALYSIS COMPLETE

---

## EXECUTIVE SUMMARY

### Current State
The MAHOUN MVP has a **critical architectural flaw** in the ledger writing lifecycle:
- Ledger entries are committed **BEFORE** Fortress validation
- Failed validations leave orphaned ledger entries with no validation state
- Ledger cannot distinguish between passed and failed executions
- **Result**: Ledger is NOT a trustworthy execution record

### Target State
Implement **Delayed Ledger Commit**:
- Create pending ledger entry during verdict generation
- DO NOT commit to ledger storage
- Pass pending entry through execution pipeline
- Fortress validation layer commits ledger with validation result
- **Result**: Ledger becomes immutable record of execution truth

---

## 1. CURRENT ARCHITECTURE ANALYSIS

### 1.1 Ledger Entry Creation Location

**File**: `mahoun/reasoning/evidence_linked_verdict.py`
**Method**: `EvidenceLinkedVerdictEngine.generate_verdict()`
**Line**: 560-569

```python
entry = LedgerEntry(
    verdict_id=verdict_id,
    case_id=case_id,
    referenced_ltm_nodes=referenced_ltm_nodes,
    referenced_facts=referenced_facts,
    confidence=confidence_score,
    invariant_version=INVARIANT_VERSION,
    guard_mode=get_guard_mode().value,
    created_at=fixed_timestamp,
)
```

**Key Observation**: Entry created with NO `validation_status` field (field exists but defaults to None).

---

### 1.2 Ledger Write Location

**File**: `mahoun/reasoning/evidence_linked_verdict.py`
**Method**: `_write_ledger_entry_async()`
**Called at**: Line 574 (inside `generate_verdict()`)

```python
async def _write_ledger_entry_async(self, entry: LedgerEntry) -> str:
    """Write ledger entry asynchronously"""
    loop = asyncio.get_event_loop()
    ledger_hash = await loop.run_in_executor(
        None,
        self.ledger_writer.write,
        entry
    )
    return ledger_hash
```

**Invoked from**:
```python
# Line 572-574
if referenced_ltm_nodes or referenced_facts:
    validate_entry(entry)
    ledger_hash = await self._write_ledger_entry_async(entry)
```

**Critical Issue**: Ledger write happens INSIDE `generate_verdict()` BEFORE returning to caller.

---

### 1.3 Fortress Validation Location

**File**: `mahoun/reasoning/fortress_integration.py`
**Method**: `FortressProtectedReasoningService.reason()`
**Lines**: 157-182

```python
async def reason(self, request: Any, correlation_id: Optional[str] = None) -> ReasoningResponse:
    # Step 1: Execute reasoning (calls adapter -> engine.generate_verdict())
    response = await self.reasoning_service.reason(request)  # Line 157
    
    # Step 2: Validate through Fortress (AFTER ledger already written)
    validation_result = await self.validator.validate(
        response=response,
        correlation_id=correlation_id
    )  # Lines 161-164
    
    # Step 3: Return response (ledger already committed at this point)
    return response  # Line 182
```

**Flow Diagram**:
```
FortressProtectedReasoningService.reason()
    ↓
self.reasoning_service.reason()  → VerdictEngineAdapter.reason()
    ↓
self.engine.generate_verdict()    → EvidenceLinkedVerdictEngine.generate_verdict()
    ↓
    ├─ Creates LedgerEntry
    ├─ WRITES to ledger (line 574) ⚠️
    └─ Returns EvidenceLinkedVerdict
    ↓
  Returns to VerdictEngineAdapter
    ↓
  Transforms to ReasoningResponse
    ↓
  Returns to FortressProtectedReasoningService
    ↓
  VALIDATES through FortressValidator (line 161) ⚠️
    ↓
  If FAILED: raises SecurityBreachException
    ↓
  Ledger already written with rejected verdict!
```

---

### 1.4 All Callers of `generate_verdict()`

#### Production Code Callers (non-test):

| Caller | File | Line | Context |
|--------|------|------|---------|
| VerdictEngineAdapter | `mahoun/reasoning/verdict_engine_adapter.py` | 253 | Primary adapter layer |
| generate_verdict_sync | `mahoun/reasoning/evidence_linked_verdict.py` | 664 | Deprecated sync wrapper |

**Only 1 primary production caller**: `VerdictEngineAdapter.reason()` at line 253

#### Call Chain to Fortress:
```
API Router (reasoning.py)
  ↓
FortressProtectedReasoningService.reason() [fortress_integration.py:157]
  ↓
VerdictEngineAdapter.reason() [verdict_engine_adapter.py:215]
  ↓
EvidenceLinkedVerdictEngine.generate_verdict() [evidence_linked_verdict.py:296]
```

---

### 1.5 Ledger Writer Callers

**Primary Writer**: `EvidenceLedgerWriter.write()`
**File**: `mahoun/ledger/writer.py`
**Line**: 433

**Called from**:
- `EvidenceLinkedVerdictEngine._write_ledger_entry_async()` [evidence_linked_verdict.py:1147]
- This is the ONLY production caller of ledger writer

**Writer Types**:
1. `ImmutableLedger` (blockchain-based, recommended)
2. `JSONLLedgerBackend` (legacy, JSONL file)
3. `SQLiteLedgerBackend` (legacy, SQLite database)

---

### 1.6 Existing GovernanceContext Capabilities

**File**: `mahoun/core/governance/governance_context.py`

**GovernanceContext** dataclass contains:
- `context_id`: Unique context identifier
- `correlation_id`: Request correlation ID
- `timestamp`: Context creation timestamp
- `execution_mode`: Current execution mode
- `provenance_tracker`: Tracks proof lineage
- `validator_pipeline`: Runtime validation
- `deterministic_resolver`: Deterministic conflict resolution
- `ontology_enforcer`: Ontology enforcement
- `correlation_lineage`: List of correlation IDs for tracing
- `runtime_attestation`: Runtime environment attestation

**GovernanceContextManager** provides:
- `create_context()`: Create new governance context
- `active_context()`: Get current active context
- `require_context()`: Require active context or raise error

**Current Usage in FortressIntegration**:
```python
# fortress_integration.py:152
ctx = GovernanceContextManager.require_context()
```

**Key Capability**: GovernanceContext enforces that NO reasoning can execute without active context (line 132-134 in fortress_integration.py).

**NOT Used for**: Ledger writing, validation status tracking, execution lifecycle

---

## 2. TARGET ARCHITECTURE

### 2.1 Target Flow

```
Target Lifecycle:
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: REQUEST INITIATION                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ API Router (reasoning.py)                                    ││
│ │   └── calls: protected_service.reason()                   ││
│ └─────────────────┬─────────────────────────────────────────┘│
│                   │                                             │
│                   ▼                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PHASE 2: GOVERNANCE CONTEXT                                  ││
│ │ FortressProtectedReasoningService.reason()                  ││
│ │   ├── Require active GovernanceContext (line 152)            ││
│ │   └── calls: self.reasoning_service.reason()               ││
│ └─────────────────┬─────────────────────────────────────────┘│
│                   │                                             │
│                   ▼                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PHASE 3: VERDICT GENERATION                                   ││
│ │ VerdictEngineAdapter.reason()                                ││
│ │   └── calls: self.engine.generate_verdict()                 ││
│ └─────────────────┬─────────────────────────────────────────┘│
│                   │                                             │
│                   ▼                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PHASE 4: LEDGER ENTRY CREATION (NOT COMMITTED)               ││
│ │ EvidenceLinkedVerdictEngine.generate_verdict()               ││
│ │   ├── Creates LedgerEntry with validation_status=None       ││
│ │   ├── Validates structural integrity (EL-I3)                 ││
│ │   └── Returns VerdictExecutionResult                         ││
│ │       ├── verdict                                            ││
│ │       ├── ledger_entry (NOT written yet)                    ││
│ │       └── execution_metadata                                 ││
│ └─────────────────┬─────────────────────────────────────────┘│
│                   │                                             │
│                   ▼                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PHASE 5: ADAPTER TRANSFORMATION                               ││
│ │ VerdictEngineAdapter._transform_verdict_to_response()        ││
│ │   └── Creates ReasoningResponse with pending_ledger_entry    ││
│ └─────────────────┬─────────────────────────────────────────┘│
│                   │                                             │
│                   ▼                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PHASE 6: FORTRESS VALIDATION & LEDGER COMMIT                 ││
│ │ FortressProtectedReasoningService.reason() (continued)      ││
│ │   ├── Receives ReasoningResponse with pending_ledger_entry   ││
│ │   ├── Validates through FortressValidator                     ││
│ │   ├── If PASSED:                                            ││
│ │   │   └── ledger_entry.validation_status = "PASSED"           ││
│ │   │   └── Commits ledger entry                              ││
│ │   │   └── Returns validated response                         ││
│ │   └── If FAILED:                                            ││
│ │       ├── ledger_entry.validation_status = "FAILED"          ││
│ │       ├── Attaches validation violations to entry           ││
│ │       ├── Commits ledger entry                              ││
│ │       └── Returns response (or raises, depending on mode)    ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Contract Definition

**New File**: `mahoun/contracts/verdict_execution.py`

```python
@dataclass(frozen=True)
class VerdictExecutionResult:
    """
    Contract for delayed ledger commit architecture.
    
    Contains all artifacts of a verdict execution that must be
    atomically committed after fortress validation.
    
    CRITICAL: This is the transport mechanism for pending ledger entries.
    NOT a metadata container - this is a lifecycle entity.
    """
    # Core verdict
    verdict: EvidenceLinkedVerdict
    
    # Pending ledger entry (NOT yet committed)
    ledger_entry: LedgerEntry
    
    # Execution identifiers
    verdict_id: str
    case_id: str
    execution_timestamp: datetime
    
    # Structural validation results (pre-Fortress)
    structural_validation_passed: bool
    structural_violations: list[str]
```

---

## 3. IMPACTED FILES ANALYSIS

### 3.1 Files Requiring Modification

| File | Current Role | Required Change | Impact Level |
|------|--------------|-----------------|--------------|
| `mahoun/contracts/verdict_execution.py` | **NEW** | Create VerdictExecutionResult contract | HIGH |
| `mahoun/reasoning/evidence_linked_verdict.py` | Ledger creation & write | Return VerdictExecutionResult, delay write | **CRITICAL** |
| `mahoun/reasoning/verdict_engine_adapter.py` | Adapter layer | Handle VerdictExecutionResult, pass through | HIGH |
| `mahoun/reasoning/fortress_integration.py` | Fortress validation | Commit ledger after validation | **CRITICAL** |
| `mahoun/ledger/models.py` | LedgerEntry model | Already has validation_status field | NONE (already done) |

### 3.2 Files NOT Requiring Modification

| File | Reason |
|------|--------|
| `mahoun/ledger/writer.py` | Already supports writing LedgerEntry with any fields |
| `mahoun/core/fortress_validator.py` | Validation logic unchanged |
| `mahoun/core/governance/governance_context.py` | Governance context unchanged |
| `api/routers/reasoning.py` | No changes needed |

### 3.3 Backward Compatibility Concerns

**Callers of `generate_verdict()` in tests** (100+ occurrences):
- All expect single return value: `EvidenceLinkedVerdict`
- Changing to return `VerdictExecutionResult` will break all tests

**Mitigation Strategy**:
1. Keep `generate_verdict()` signature unchanged for backward compatibility
2. Add NEW method: `generate_verdict_with_pending_ledger()`
3. Deprecate old method
4. Update primary adapter to use new method
5. Gradually migrate tests

**Alternative (Preferred)**:
- Accept breaking change as necessary for trustworthiness
- Document in migration guide
- Fix all test callers in single commit

---

## 4. RISK ASSESSMENT

### 4.1 High Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking test suite | HIGH | HIGH | Bulk update all test callers; verify with CI |
| Ledger write failures | MEDIUM | HIGH | Maintain existing error handling; add ledger commit retry logic |
| Performance regression | LOW | MEDIUM | Ledger write already async; validation is fast |
| Determinism violation | LOW | CRITICAL | Preserve all ID generation logic; test deterministic mode |
| Race conditions | MEDIUM | HIGH | Maintain `_ledger_lock`; ensure sequential writes |

### 4.2 Medium Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Contract design issues | MEDIUM | MEDIUM | Review with architecture council |
| Incomplete audit trail | LOW | HIGH | Ensure all execution paths commit ledger |
| Metadata pollution | MEDIUM | MEDIUM | DO NOT use response.metadata for lifecycle objects |

### 4.3 Low Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Typo in new field names | LOW | LOW | Code review |
| Documentation gaps | MEDIUM | LOW | Update all relevant docs |

---

## 5. CRITICAL DECISIONS REQUIRED

### 5.1 Decision: Transport Mechanism

**Problem**: Need to pass `LedgerEntry` from `EvidenceLinkedVerdictEngine` (deep) to `FortressProtectedReasoningService` (higher).

**Options**:

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Response metadata | Quick to implement | Abuses metadata semantics; lifecycle object in descriptive field | ❌ REJECTED |
| B. Return tuple from generate_verdict | Explicit, clear ownership | Breaks 100+ test callers | ⚠️ ACCEPTABLE with migration |
| C. New VerdictExecutionResult contract | Clean, type-safe, explicit lifecycle | Requires new file, more code | ✅ **RECOMMENDED** |
| D. Thread-local storage | No signature changes | Global mutable state; error-prone; not thread-safe | ❌ REJECTED |
| E. ExecutionContext extension | Natural fit with existing governance | Complex; may require governance changes | ⚠️ ALTERNATIVE |

**Decision**: ✅ **Option C - New VerdictExecutionResult contract**

**Rationale**:
- Explicit lifecycle management
- Type-safe transport
- Clear ownership semantics
- Extensible for future needs
- Follows MAHOUN pattern of explicit contracts

---

### 5.2 Decision: Failed Validation Handling

**Problem**: What to do when Fortress validation fails?

**Options**:

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| A. Skip ledger commit | Clean ledger; only successful executions | Loses audit trail of failures | ❌ REJECTED |
| B. Commit with FAILED status | Complete audit trail; legally relevant | Ledger contains failures | ✅ **RECOMMENDED** |
| C. Separate rejected ledger | Clean main ledger; complete history | Complexity; two ledgers to maintain | ⚠️ ALTERNATIVE |

**Decision**: ✅ **Option B - Commit with FAILED status**

**Rationale**:
- Legal requirement: failed validations are legally relevant execution events
- Audit requirement: complete execution history must be preserved
- Trust requirement: external observers must be able to verify rejection reasons
- Principle: "A failed validation is also a legally relevant execution event and must not disappear"

---

### 5.3 Decision: Field Ownership (validation_status location)

**Problem**: Where does `validation_status` belong semantically?

**Options**:

| Option | Field Name | Location | Rationale |
|--------|------------|----------|-----------|
| A | `verdict.validation_status` | EvidenceLinkedVerdict | Status is property of the verdict itself | ❌ Verdict shouldn't know about validation |
| B | `ledger_entry.validation_status` | LedgerEntry | Status describes ledger commit state | ✅ **RECOMMENDED** |
| C | `execution.validation_status` | ExecutionContext | Status is execution-level property | ⚠️ Requires new context |

**Decision**: ✅ **Option B - `ledger_entry.validation_status`**

**Rationale**:
- Ledger entry represents the atomic unit of execution history
- Validation status is a property of the execution record, not the verdict content
- Ledger is the source of truth for execution history
- Aligns with principle: "The ledger MUST record both successful and failed executions"

**Already Implemented**: Field exists in `LedgerEntry` (line 21 of models.py)

---

### 5.4 Decision: ID Generation Timing

**Problem**: When to generate verdict_id and case_id?

**Current**: Generated in `generate_verdict()` before ledger write (lines 519-537)

**Options**:

| Option | Timing | Rationale |
|--------|--------|-----------|
| A | Keep current timing | IDs needed for ledger entry creation; no change required | ✅ **RECOMMENDED** |
| B | Delay until after validation | Ensures IDs only for valid executions | ❌ Breaks determinism; IDs needed for ledger entry |

**Decision**: ✅ **Option A - Keep current timing**

**Rationale**:
- IDs are deterministic based on input, not validation result
- Ledger entry needs IDs at creation time
- Changing ID generation timing breaks existing behavior
- Principle: "Preserve determinism guarantees"

---

### 5.5 Decision: Existing validation_status Field

**Problem**: `validation_status` already exists in `LedgerEntry` (line 21 of models.py). How was it added?

**Finding**: This field was added in a previous session but NOT yet used.

**Decision**: ✅ **Keep and use existing field**

**Rationale**:
- No architectural change needed to models.py
- Field is already Optional[str] with default None
- Accepts "PASSED", "FAILED", None values
- Already backward compatible

---

## 6. ARCHITECTURAL DIAGRAMS

### 6.1 Current Lifecycle Sequence Diagram

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│   API Router  │     │ VerdictEngineAdapter │     │ EvidenceLinked       │
│               │     │                      │     │ VerdictEngine         │
└──────┬───────┘     └──────────┬───────────┘     └──────────┬───────────┘
       │                        │                           │
       │ 1. reason() request    │                           │
       │───────────────────────>│                           │
       │                        │ 2. reason() request       │
       │                        │───────────────────────>│
       │                        │                           │
       │                        │                           │ 3. generate_verdict()
       │                        │                           │
       │                        │                           │   │
       │                        │                           │   ├─ 3a. Create LedgerEntry
       │                        │                           │   ├─ 3b. Extract evidence refs
       │                        │                           │   ├─ 3c. Generate IDs
       │                        │                           │   │
       │                        │                           │   ▼
       │                        │                           │ 4. WRITES LEDGER ⚠️
       │                        │                           │   (line 574)
       │                        │                           │
       │                        │                           │ 5. Create Verdict
       │                        │                           │
       │                        │◄────────────────────── 6. Return Verdict
       │                        │
       │                        │ 7. Transform to ReasoningResponse
       │                        │
       │◄─────────────────────── 8. Return ReasoningResponse
       │
       │                        │                           │
       ▼                        ▼                           ▼
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│   (Client)   │     │ FortressProtected    │     │   (Ledger Storage)   │
│               │     │ ReasoningService      │     │                       │
└──────────────┘     └──────────┬───────────┘     └──────────────────────┘
                              │
                              │ 9. reason() continued
                              │
                              │   │
                              │   ├─ 9a. Validate response (line 161)
                              │   │
                              │   ▼
                              │ 10. If FAILED: raise SecurityBreachException
                              │
                              │   ⚠️  PROBLEM: Ledger already written at step 4!
                              │
                              ▼
                       11. Return response (or exception)
```

### 6.2 Target Lifecycle Sequence Diagram

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│   API Router  │     │ VerdictEngineAdapter │     │ EvidenceLinked       │
│               │     │                      │     │ VerdictEngine         │
└──────┬───────┘     └──────────┬───────────┘     └──────────┬───────────┘
       │                        │                           │
       │ 1. reason() request    │                           │
       │───────────────────────>│                           │
       │                        │ 2. reason() request       │
       │                        │───────────────────────>│
       │                        │                           │
       │                        │                           │ 3. generate_verdict()
       │                        │                           │
       │                        │                           │   │
       │                        │                           │   ├─ 3a. Create LedgerEntry
       │                        │                           │   ├─ 3b. Extract evidence refs
       │                        │                           │   ├─ 3c. Generate IDs
       │                        │                           │   │
       │                        │                           │   ▼
       │                        │                           │ 4. Validate structural integrity
       │                        │                           │
       │                        │                           │ 5. Return VerdictExecutionResult
       │                        │                           │   (NOT written yet!)
       │                        │◄──────────────────────
       │                        │
       │                        │ 6. Transform to ReasoningResponse
       │                        │   (with pending_ledger_entry)
       │                        │
       │◄─────────────────────── 7. Return ReasoningResponse
       │                           (with VerdictExecutionResult)
       │
       ▼
┌──────────────┐
│   (Client)   │
└──────────────┘
       │
       ▼
┌──────────────────────┐     ┌──────────────────────┐
│ FortressProtected    │     │   (Ledger Storage)   │
│ ReasoningService      │     │                       │
└──────────┬───────────┘     └──────────────────────┘
           │
           │ 8. reason() continued
           │
           │   │
           │   ├─ 8a. Extract pending_ledger_entry from response
           │   │
           │   ├─ 8b. Validate response (line 161)
           │   │
           │   ▼
           │ 9. If PASSED:
           │   │   ├─ 9a. Set validation_status = "PASSED"
           │   │   └─ 9b. COMMIT ledger entry
           │   │
           │ 10. If FAILED:
           │    │   ├─ 10a. Set validation_status = "FAILED"
           │    │   ├─ 10b. Attach validation violations
           │    │   └─ 10c. COMMIT ledger entry
           │
           ▼
    11. Return response (ledger committed with correct status)
```

---

## 7. FILE-BY-FILE CHANGE SPECIFICATION

### 7.1 NEW FILE: `mahoun/contracts/verdict_execution.py`

**Purpose**: Define explicit contract for delayed ledger commit

**Content**:
```python
"""
MAHOUN Verdict Execution Contract
==================================
Contract for delayed ledger commit architecture.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mahoun.ledger.models import LedgerEntry
    from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdict

@dataclass(frozen=True)
class VerdictExecutionResult:
    """
    Immutable result of verdict execution containing all artifacts
    that must be atomically committed after fortress validation.
    
    This contract ensures that:
    1. Ledger entry is created but NOT committed during generation
    2. All execution artifacts are preserved for fortress validation
    3. Commit decision is made AFTER validation, not before
    """
    verdict: "EvidenceLinkedVerdict"
    ledger_entry: "LedgerEntry"
    verdict_id: str
    case_id: str
    execution_timestamp: datetime
    structural_validation_passed: bool = True
    structural_violations: list[str] = None
    
    def __post_init__(self):
        """Validate contract invariants."""
        if self.ledger_entry.verdict_id != self.verdict_id:
            raise ValueError("verdict_id mismatch between verdict and ledger entry")
        if self.ledger_entry.case_id != self.case_id:
            raise ValueError("case_id mismatch between verdict and ledger entry")
```

---

### 7.2 MODIFY: `mahoun/reasoning/evidence_linked_verdict.py`

**Changes**:

1. **Import** (line 1-30):
   ```python
   from mahoun.contracts.verdict_execution import VerdictExecutionResult
   ```

2. **Method signature** (line 296):
   ```python
   # CURRENT:
   async def generate_verdict(
       self,
       question: str,
       facts: list[Any],
       case_id: str | None = None,
   ) -> EvidenceLinkedVerdict:
   
   # TARGET:
   async def generate_verdict(
       self,
       question: str,
       facts: list[Any],
       case_id: str | None = None,
   ) -> VerdictExecutionResult:
   ```

3. **Ledger creation** (lines 560-574):
   ```python
   # CURRENT:
   entry = LedgerEntry(
       verdict_id=verdict_id,
       case_id=case_id,
       referenced_ltm_nodes=referenced_ltm_nodes,
       referenced_facts=referenced_facts,
       confidence=confidence_score,
       invariant_version=INVARIANT_VERSION,
       guard_mode=get_guard_mode().value,
       created_at=fixed_timestamp,
   )
   
   if referenced_ltm_nodes or referenced_facts:
       validate_entry(entry)
       ledger_hash = await self._write_ledger_entry_async(entry)
   
   # TARGET:
   entry = LedgerEntry(
       verdict_id=verdict_id,
       case_id=case_id,
       referenced_ltm_nodes=referenced_ltm_nodes,
       referenced_facts=referenced_facts,
       confidence=confidence_score,
       invariant_version=INVARIANT_VERSION,
       guard_mode=get_guard_mode().value,
       created_at=fixed_timestamp,
       validation_status=None,  # Will be set after fortress validation
   )
   
   # Validate but DO NOT write
   structural_validation_passed = True
   structural_violations = []
   
   if referenced_ltm_nodes or referenced_facts:
       try:
           validate_entry(entry)
       except Exception as e:
           structural_validation_passed = False
           structural_violations = [str(e)]
   else:
       # Handle empty evidence
       from mahoun.core.environment import is_production
       if is_production():
           raise RuntimeError("EL-I3 VIOLATION: ...")
       structural_validation_passed = False
       structural_violations = ["EL-I3: No evidence references"]
   ```

4. **Return value** (line 629):
   ```python
   # CURRENT:
   return verdict
   
   # TARGET:
   return VerdictExecutionResult(
       verdict=verdict,
       ledger_entry=entry,
       verdict_id=verdict_id,
       case_id=case_id,
       execution_timestamp=fixed_timestamp,
       structural_validation_passed=structural_validation_passed,
       structural_violations=structural_violations,
   )
   ```

5. **Remove ledger write** (lines 572-577):
   - Remove: `ledger_hash = await self._write_ledger_entry_async(entry)`
   - Remove: `log.info(f"Ledger entry written successfully: ...")`
   - Ledger hash no longer set in verdict (will be set after commit)

---

### 7.3 MODIFY: `mahoun/reasoning/verdict_engine_adapter.py`

**Changes**:

1. **Import** (line 1-70):
   ```python
   from mahoun.contracts.verdict_execution import VerdictExecutionResult
   ```

2. **Method signature** (line 215):
   ```python
   # No change to external signature
   async def reason(self, request: Any, correlation_id: Optional[str] = None) -> ReasoningResponse:
   ```

3. **Call to engine** (lines 253-257):
   ```python
   # CURRENT:
   verdict_result = await self.engine.generate_verdict(
       question=question,
       facts=facts,
       case_id=case_id
   )
   
   response = self._transform_verdict_to_response(
       verdict_result=verdict_result,
       correlation_id=case_id,
       execution_time_ms=(time.time() - start_time) * 1000,
   )
   
   # TARGET:
   execution_result = await self.engine.generate_verdict(
       question=question,
       facts=facts,
       case_id=case_id
   )
   
   # Extract pending ledger entry from execution result
   pending_ledger_entry = execution_result.ledger_entry
   
   response = self._transform_verdict_to_response(
       verdict_result=execution_result.verdict,
       correlation_id=case_id,
       execution_time_ms=(time.time() - start_time) * 1000,
       pending_ledger_entry=pending_ledger_entry,
   )
   ```

4. **Transform method** (line 320):
   ```python
   # CURRENT:
   def _transform_verdict_to_response(
       self,
       verdict_result: Any,
       correlation_id: str,
       execution_time_ms: float,
   ) -> ReasoningResponse:
   
   # TARGET:
   def _transform_verdict_to_response(
       self,
       verdict_result: Any,
       correlation_id: str,
       execution_time_ms: float,
       pending_ledger_entry: Optional[LedgerEntry] = None,
   ) -> ReasoningResponse:
       # ... existing code ...
       
       # Attach pending ledger entry to response
       # NOTE: This is a LIFECYCLE object, not metadata
       # We use a dedicated field, NOT response.metadata
       if pending_ledger_entry:
           response._pending_ledger_entry = pending_ledger_entry
       
       return ReasoningResponse(...)
   ```

5. **Response class extension** (if needed):
   ```python
   # In unified_reasoning_service.py, ReasoningResponse class:
   # Add field for pending ledger entry (lifecycle object)
   pending_ledger_entry: Optional[LedgerEntry] = None
   ```

---

### 7.4 MODIFY: `mahoun/reasoning/fortress_integration.py`

**Changes**:

1. **Import** (line 1-50):
   ```python
   from dataclasses import replace
   from mahoun.ledger.models import LedgerEntry
   ```

2. **Method modification** (lines 154-182):
   ```python
   # CURRENT:
   try:
       response = await self.reasoning_service.reason(request)
       
       validation_result = await self.validator.validate(
           response=response,
           correlation_id=correlation_id
       )
       
       self.stats["validated_responses"] += 1
       
       if validation_result.passed:
           log.info(...)
       else:
           self.stats["blocked_responses"] += 1
           log.warning(...)
       
       return response
   
   # TARGET:
   try:
       response = await self.reasoning_service.reason(request)
       
       # Extract pending ledger entry from response
       pending_ledger_entry = getattr(response, '_pending_ledger_entry', None)
       
       # Validate response through Fortress
       validation_result = await self.validator.validate(
           response=response,
           correlation_id=correlation_id
       )
       
       self.stats["validated_responses"] += 1
       
       # Commit ledger with validation status
       if pending_ledger_entry is not None:
           ledger_entry = self._apply_validation_to_ledger_entry(
               ledger_entry=pending_ledger_entry,
               validation_result=validation_result
           )
           await self._commit_ledger_entry(ledger_entry)
           
           # Store hash in response for audit
           response.ledger_hash = ledger_entry.ledger_hash
       
       if validation_result.passed:
           log.info(...)
       else:
           self.stats["blocked_responses"] += 1
           log.warning(...)
       
       return response
   ```

3. **Helper methods** (add to class):
   ```python
   def _apply_validation_to_ledger_entry(
       self,
       ledger_entry: LedgerEntry,
       validation_result: ValidationResult
   ) -> LedgerEntry:
       """
       Apply fortress validation result to ledger entry.
       
       Uses dataclasses.replace() to handle frozen LedgerEntry.
       """
       validation_status = "PASSED" if validation_result.passed else "FAILED"
       
       # Create updated entry with validation status
       updated_entry = replace(
           ledger_entry,
           validation_status=validation_status
       )
       
       # Store validation details for audit
       # NOTE: These could be added as additional fields if needed
       
       return updated_entry
   
   async def _commit_ledger_entry(self, entry: LedgerEntry) -> str:
       """
       Commit ledger entry to storage.
       
       This is the FINAL commit point after all validations.
       """
       # Get the ledger writer from the reasoning service
       if hasattr(self.reasoning_service, 'engine') and hasattr(self.reasoning_service.engine, 'ledger_writer'):
           ledger_writer = self.reasoning_service.engine.ledger_writer
       else:
           raise RuntimeError("Cannot access ledger writer for commit")
       
       # Write entry (same async pattern as before)
       loop = asyncio.get_event_loop()
       ledger_hash = await loop.run_in_executor(
           None,
           ledger_writer.write,
           entry
       )
       
       log.info(
           f"Ledger entry committed: verdict_id={entry.verdict_id}, "
           f"status={entry.validation_status}, hash={ledger_hash[:16]}..."
       )
       
       return ledger_hash
   ```

---

## 8. BACKWARD COMPATIBILITY STRATEGY

### 8.1 Problem
- 100+ test files call `generate_verdict()` expecting `EvidenceLinkedVerdict` return
- Changing return type breaks all existing tests

### 8.2 Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Breaking change | Update all callers at once | Clean, but massive change | ⚠️ |
| B | Dual methods | Keep old method, add new method | Gradual migration | ✅ |
| C | Wrapper pattern | New method wraps old, extracts result | Backward compatible | ✅ **RECOMMENDED** |

### 8.3 Recommended Approach: Wrapper Pattern

```python
# In evidence_linked_verdict.py:

async def generate_verdict(
    self,
    question: str,
    facts: list[Any],
    case_id: str | None = None,
) -> EvidenceLinkedVerdict:
    """
    Generate verdict with evidence-linked reasoning.
    
    DEPRECATED: This method writes ledger immediately.
    Use generate_verdict_v2() for delayed ledger commit.
    """
    # Call new implementation
    result = await self._generate_verdict_internal(question, facts, case_id)
    
    # For backward compatibility: write ledger immediately and return verdict
    if result.structural_validation_passed:
        ledger_hash = await self._write_ledger_entry_async(result.ledger_entry)
        result.verdict.ledger_hash = ledger_hash
    
    return result.verdict

async def _generate_verdict_internal(
    self,
    question: str,
    facts: list[Any],
    case_id: str | None = None,
) -> VerdictExecutionResult:
    """Internal implementation with delayed ledger commit."""
    # ... full implementation from Section 7.2 ...
    pass

# NEW: Explicit delayed commit method
async def generate_verdict_with_pending_ledger(
    self,
    question: str,
    facts: list[Any],
    case_id: str | None = None,
) -> VerdictExecutionResult:
    """
    Generate verdict with pending ledger entry (NOT committed).
    
    This is the NEW contract-compliant method.
    Caller is responsible for committing ledger after validation.
    """
    return await self._generate_verdict_internal(question, facts, case_id)
```

---

## 9. TESTING STRATEGY

### 9.1 Unit Tests

| Test | Description | Input | Expected |
|------|-------------|-------|----------|
| UT-1 | Successful validation | Valid request | Ledger committed with PASSED |
| UT-2 | Failed validation | Low confidence request | Ledger committed with FAILED |
| UT-3 | Empty evidence (dev) | No evidence | No ledger commit, warning logged |
| UT-4 | Empty evidence (prod) | No evidence | RuntimeError raised |
| UT-5 | Ledger write failure | Corrupted backend | Exception propagated |

### 9.2 Integration Tests

| Test | Description | Scope | Expected |
|------|-------------|-------|----------|
| IT-1 | Full pipeline success | API → Ledger | PASSED status, valid hash |
| IT-2 | Full pipeline failure | API → Ledger | FAILED status, valid hash |
| IT-3 | Concurrent requests | Multi-request | Sequential writes, no conflicts |
| IT-4 | Governance context | With/without ctx | Context required, no bypass |

### 9.3 Determinism Tests

| Test | Description | Runs | Expected |
|------|-------------|------|----------|
| DT-1 | Identical requests | 3 | Same verdict_id, case_id, ledger entry |
| DT-2 | Deterministic mode | 3 | validation_status consistent |
| DT-3 | Hour bucket rollover | Cross-hour | Different verdict_id, same case_id |

### 9.4 Regression Tests

| Test | Description | Coverage | Expected |
|------|-------------|----------|----------|
| RT-1 | Existing test suite | All tests | All pass (with wrapper) |
| RT-2 | Breaking change path | New tests | New behavior verified |

---

## 10. MIGRATION PATH

### Phase 1: Preparation (This Document) ✅
- [x] Analyze current architecture
- [x] Identify impacted files
- [x] Define target architecture
- [x] Document risks and decisions

### Phase 2: Contract Implementation
- [ ] Create `mahoun/contracts/verdict_execution.py`
- [ ] Add VerdictExecutionResult dataclass
- [ ] Add validation invariants

### Phase 3: Core Implementation
- [ ] Modify `evidence_linked_verdict.py`
- [ ] Modify `verdict_engine_adapter.py`
- [ ] Modify `fortress_integration.py`

### Phase 4: Backward Compatibility
- [ ] Implement wrapper pattern
- [ ] Update all production callers
- [ ] Add deprecation warnings

### Phase 5: Testing
- [ ] Create unit tests (Section 9.1)
- [ ] Create integration tests (Section 9.2)
- [ ] Create determinism tests (Section 9.3)
- [ ] Run regression tests (Section 9.4)

### Phase 6: Deployment
- [ ] Update CHANGELOG.md
- [ ] Document breaking changes
- [ ] Create migration guide
- [ ] Deploy to staging
- [ ] Deploy to production

---

## 11. SUCCESS CRITERIA

The ledger integrity fix is considered successful when:

1. ✅ **Architectural**: Ledger is written AFTER fortress validation
2. ✅ **Data Integrity**: Every ledger entry has `validation_status` set
3. ✅ **Audit Trail**: Both PASSED and FAILED executions are recorded
4. ✅ **Determinism**: Same input produces same ledger entry
5. ✅ **Trustworthiness**: External observers can verify execution history
6. ✅ **Backward Compatibility**: Existing production code continues to work
7. ✅ **Test Coverage**: All new functionality has automated tests
8. ✅ **Performance**: No significant latency regression

---

## 12. ANSWERS TO MISSION QUESTIONS

### Q1: Current ledger creation location
**A**: `mahoun/reasoning/evidence_linked_verdict.py`, line 560-569, inside `EvidenceLinkedVerdictEngine.generate_verdict()` method

### Q2: Current ledger write location
**A**: `mahoun/reasoning/evidence_linked_verdict.py`, line 574, called via `_write_ledger_entry_async()` which invokes `self.ledger_writer.write(entry)` at line 1147

### Q3: Current Fortress validation location
**A**: `mahoun/reasoning/fortress_integration.py`, lines 161-164, inside `FortressProtectedReasoningService.reason()` method, AFTER the ledger has already been written

### Q4: All callers of `generate_verdict()`
**A**: Production callers:
- `mahoun/reasoning/verdict_engine_adapter.py:253` - Primary adapter
- `mahoun/reasoning/evidence_linked_verdict.py:664` - Deprecated sync wrapper

Test callers: 100+ test files (not listed, will need updating)

### Q5: All callers of ledger writer
**A**: 
- `mahoun/reasoning/evidence_linked_verdict.py:1147` - `_write_ledger_entry_async()` (only production caller)

### Q6: Existing ExecutionContext/GovernanceContext capabilities
**A**: GovernanceContext exists with:
- Correlation lineage tracking
- Proof tracking activation
- Governance scope injection
- Runtime attestation
- Currently used to REQUIRE active context before reasoning
- NOT currently used for ledger lifecycle management

---

## 13. DOCUMENT HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | Mistral Vibe | Initial architecture analysis |

---

**Document Location**: `/home/haji/Desktop/KingMahouN/LEDGER_LIFECYCLE_ANALYSIS.md`

**Next Phase**: Phase 2 - Implement Minimal Safe Change (awaiting approval of this analysis)
