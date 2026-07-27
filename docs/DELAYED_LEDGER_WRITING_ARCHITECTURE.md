# Delayed Ledger Writing Architecture & Proposal Plan

## Document Information
- **Title**: Delayed Ledger Writing Architecture for MAHOUN MVP
- **Author**: Mistral Vibe CLI Agent
- **Date**: 2026-07-24
- **Status**: PROPOSAL
- **Related Issue**: Ledger Integrity Trust Gap (Capability 2)

---

## 1. Problem Statement

### Current Architecture Issue

The MAHOUN MVP production execution path has a critical architectural flaw in the ledger writing process:

```
Current Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. API Router (reasoning.py)                              │
│    └── calls: protected_service.reason()                   │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. FortressProtectedReasoningService (fortress_integration.py)│
│    └── calls: self.reasoning_service.reason()               │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VerdictEngineAdapter (verdict_engine_adapter.py)         │
│    └── calls: self.engine.generate_verdict()                 │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EvidenceLinkedVerdictEngine (evidence_linked_verdict.py)  │
│    ├── Creates LedgerEntry                                   │
│    ├── WRITES to ledger (line 574) ⚠️                        │
│    └── Returns EvidenceLinkedVerdict                         │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Back to VerdictEngineAdapter                             │
│    └── Transforms to ReasoningResponse                       │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Back to FortressProtectedReasoningService                  │
│    ├── Receives ReasoningResponse                            │
│    ├── VALIDATES through FortressValidator (line 161) ⚠️     │
│    └── If FAILS: raises SecurityBreachException              │
└─────────────────────────────────────────────────────────────┘
```

### The Problem

**Ledger is written BEFORE fortress validation.**

When fortress validation fails (e.g., agreement_score < 0.85):
1. Ledger entry has already been written with the verdict
2. SecurityBreachException is raised
3. Request fails, no response returned to client
4. **Result**: Ledger contains entries for REJECTED verdicts with no indication they failed validation

### Evidence from Runtime
- Discovered `verdict_c5147ce75e66` in ledger with confidence=0.76
- Fortress validation FAILED due to agreement score below 0.85 threshold
- No `validation_status` field in LedgerEntry to track this
- Cannot distinguish passed from failed verdicts in audit trail

### Trust Impact
- **Violates**: Audit trail integrity principle
- **Risk**: Cannot verify which verdicts are trustworthy
- **Consequence**: Ledger cannot be used as immutable audit log for governance

---

## 2. Proposed Solution: Delayed Ledger Writing

### Target Architecture

```
Proposed Flow:
┌─────────────────────────────────────────────────────────────┐
│ 1. API Router (reasoning.py)                              │
│    └── calls: protected_service.reason()                   │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. FortressProtectedReasoningService (fortress_integration.py)│
│    ├── calls: self.reasoning_service.reason()               │
│    ├── Receives ReasoningResponse                            │
│    ├── VALIDATES through FortressValidator                   │
│    ├── If PASSED:                                           │
│    │   └── calls: self._write_ledger_with_validation()      │
│    │       └── Sets validation_status="PASSED"              │
│    │       └── Writes ledger entry                          │
│    └── If FAILED:                                           │
│        ├── Sets validation_status="FAILED"                  │
│        ├── Option A: Write ledger with FAILED status          │
│        └── Option B: Skip ledger writing entirely             │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VerdictEngineAdapter (verdict_engine_adapter.py)         │
│    └── calls: self.engine.generate_verdict()                 │
└─────────────────┬─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EvidenceLinkedVerdictEngine (evidence_linked_verdict.py)  │
│    ├── Creates LedgerEntry with validation_status=None        │
│    └── DOES NOT write to ledger                              │
│        └── Returns (verdict, ledger_entry) tuple             │
└─────────────────────────────────────────────────────────────┘
```

### Key Changes Required

| Component | Current Behavior | New Behavior |
|-----------|------------------|--------------|
| `EvidenceLinkedVerdictEngine.generate_verdict()` | Creates and writes ledger entry | Creates ledger entry but DOES NOT write; returns entry |
| `VerdictEngineAdapter.reason()` | Returns ReasoningResponse | Returns ReasoningResponse + ledger_entry |
| `FortressProtectedReasoningService.reason()` | Validates response | Validates, then writes ledger with validation_status |
| `LedgerEntry` | No validation_status field | Has `validation_status: Optional[str]` field |

---

## 3. Implementation Plan

### Phase 1: Prepare Data Structures (✅ PARTIALLY COMPLETE)

#### ✅ Completed
1. **`mahoun/ledger/models.py`**
   - Added `validation_status: Optional[str] = None` to LedgerEntry
   - Field accepts values: "PASSED", "FAILED", "PENDING", None

2. **`mahoun/core/fortress_validator.py`**
   - Inject validation_status into ReasoningResponse.metadata
   - Includes validation_violations and validation_timestamp

3. **`mahoun/reasoning/evidence_linked_verdict.py`**
   - Added `_pending_ledger_entry` field to EvidenceLinkedVerdictEngine
   - Modified ledger entry creation to include `validation_status=None`
   - Commented out immediate ledger writing (partial implementation)

#### Remaining for Phase 1
- [ ] Add import for `Optional` if not present (verify)
- [ ] Add type annotation for `_pending_ledger_entry` in `__init__`

### Phase 2: Modify EvidenceLinkedVerdictEngine

#### Changes to `generate_verdict()` method

```python
# CURRENT (lines 560-574):
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
    # ...

# PROPOSED:
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

if referenced_ltm_nodes or referenced_facts:
    validate_entry(entry)
    # DO NOT write yet - store for later
    self._pending_ledger_entry = entry
    ledger_hash = None  # Will be set by caller after validation
    log.debug(f"Ledger entry prepared (pending validation): verdict_id={verdict_id}")
else:
    # Handle empty evidence case...
    ledger_hash = None
```

#### Changes to return value

```python
# CURRENT (line 629):
return verdict

# PROPOSED:
# Return both verdict and pending ledger entry
return verdict, self._pending_ledger_entry
```

### Phase 3: Modify VerdictEngineAdapter

#### Changes to `reason()` method

```python
# CURRENT (lines 252-257):
verdict_result = await self.engine.generate_verdict(
    question=question,
    facts=facts,
    case_id=case_id
)

response = self._transform_verdict_to_response(
    verdict_result=verdict_result,
    correlation_id=case_id,
    execution_time_ms=...
)

# PROPOSED:
verdict_result, ledger_entry = await self.engine.generate_verdict(
    question=question,
    facts=facts,
    case_id=case_id
)

response = self._transform_verdict_to_response(
    verdict_result=verdict_result,
    correlation_id=case_id,
    execution_time_ms=...,
    ledger_entry=ledger_entry  # Pass through for later
)

# Store ledger_entry in response metadata for fortress layer
response.metadata["pending_ledger_entry"] = ledger_entry
```

#### Changes to `_transform_verdict_to_response()`

```python
# Add parameter:
def _transform_verdict_to_response(
    self,
    verdict_result: Any,
    correlation_id: str,
    execution_time_ms: float,
    ledger_entry: Optional[LedgerEntry] = None,  # NEW
) -> ReasoningResponse:
    # ... existing code ...
    
    # Store ledger entry reference in metadata
    if ledger_entry:
        metadata["pending_ledger_entry"] = ledger_entry
    
    return ReasoningResponse(...)
```

### Phase 4: Modify FortressProtectedReasoningService

#### Changes to `reason()` method

```python
# CURRENT (lines 155-182):
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

# PROPOSED:
response = await self.reasoning_service.reason(request)

# Extract pending ledger entry from response metadata
ledger_entry = response.metadata.get("pending_ledger_entry")

# Validate response through Fortress
validation_result = await self.validator.validate(
    response=response,
    correlation_id=correlation_id
)

self.stats["validated_responses"] += 1

# Write ledger with validation status
if ledger_entry is not None:
    ledger_entry = self._update_ledger_with_validation(
        ledger_entry=ledger_entry,
        validation_result=validation_result
    )
    await self._write_ledger_entry(ledger_entry)
    response.metadata["ledger_hash"] = ledger_entry.ledger_hash

if validation_result.passed:
    log.info(...)
else:
    self.stats["blocked_responses"] += 1
    log.warning(...)

return response
```

#### Add helper methods

```python
# In FortressProtectedReasoningService class:

def _update_ledger_with_validation(
    self,
    ledger_entry: LedgerEntry,
    validation_result: ValidationResult
) -> LedgerEntry:
    """
    Update ledger entry with fortress validation status.
    
    Since LedgerEntry is frozen, we need to create a new entry with updated fields.
    """
    from dataclasses import replace
    
    validation_status = "PASSED" if validation_result.passed else "FAILED"
    
    # Create new entry with validation_status set
    updated_entry = replace(
        ledger_entry,
        validation_status=validation_status
    )
    
    return updated_entry

async def _write_ledger_entry(self, entry: LedgerEntry) -> str:
    """Write ledger entry asynchronously"""
    # Use the engine's ledger writer
    loop = asyncio.get_event_loop()
    ledger_hash = await loop.run_in_executor(
        None,
        self.reasoning_service.engine.ledger_writer.write,
        entry
    )
    return ledger_hash
```

---

## 4. Design Decisions

### Decision 1: Frozen Dataclass Workaround

**Problem**: `LedgerEntry` is a frozen dataclass, cannot be modified after creation.

**Options Considered**:
1. **Unfreeze the dataclass**: Remove `frozen=True` - Rejected: breaks immutability guarantees
2. **Use `dataclasses.replace()`**: Create new instance with updated fields - **SELECTED**
3. **Add validation_status at creation**: Requires passing status through call stack - Rejected: status not known at creation

**Decision**: Use `dataclasses.replace()` to create updated entry with validation_status.

### Decision 2: Ledger Entry Storage

**Problem**: Need to pass ledger entry from engine (deep in call stack) to fortress service (higher in call stack).

**Options Considered**:
1. **Thread-local storage**: Store in engine, retrieve in fortress - Rejected: complex, error-prone
2. **Return tuple**: (verdict, ledger_entry) - Rejected: breaks existing interfaces
3. **Response metadata**: Store in ReasoningResponse.metadata - **SELECTED**

**Decision**: Use `response.metadata["pending_ledger_entry"]` to pass ledger entry through the call stack.

### Decision 3: Failed Validation Behavior

**Problem**: What to do with ledger entry when fortress validation fails?

**Options Considered**:
1. **Skip ledger writing**: Don't write entries for failed verdicts - Rejected: loses audit trail of failures
2. **Write with FAILED status**: Write entry with validation_status="FAILED" - **SELECTED**
3. **Write to separate ledger**: Maintain rejected verdicts in separate ledger - Rejected: complexity

**Decision**: Write ledger entry with `validation_status="FAILED"` to maintain complete audit trail.

### Decision 4: Empty Evidence Handling

**Problem**: Current code skips ledger writing for empty evidence (development mode only).

**Decision**: Maintain current behavior but add validation_status tracking when ledger IS written.

---

## 5. Implementation Risks & Mitigations

### Risk 1: Breaking Existing Interfaces

**Impact**: Changes to `generate_verdict()` return type may break existing callers.

**Mitigation**:
- Check all callers of `generate_verdict()` in codebase
- Use backward-compatible approach: return tuple but allow unpacking as single value
- Add deprecation warnings for old usage

### Risk 2: Performance Impact

**Impact**: Delayed ledger writing adds latency to request processing.

**Mitigation**:
- Ledger writing is already asynchronous
- Validation is fast (milliseconds)
- Overall impact minimal

### Risk 3: Error Handling Complexity

**Impact**: More places where errors can occur in the pipeline.

**Mitigation**:
- Add try-catch blocks at each layer
- Ensure ledger writing failures are properly propagated
- Maintain existing error handling patterns

### Risk 4: Thread Safety

**Impact**: `_pending_ledger_entry` field in engine may have concurrency issues.

**Mitigation**:
- Keep `_ledger_lock` for sequential access
- Ensure each request has its own ledger entry (not shared state)
- Actually, `_pending_ledger_entry` should be local to each call, not instance field

**Correction to Phase 2**:
```python
# Instead of instance field, return ledger_entry directly:
return verdict, ledger_entry  # Both are call-local, no shared state
```

---

## 6. Step-by-Step Implementation Checklist

### [ ] Phase 1: Verify Phase 1 Completion
- [ ] Verify `validation_status` field added to LedgerEntry
- [ ] Verify fortress_validator injects validation metadata
- [ ] Verify evidence_linked_verdict.py has _pending_ledger_entry preparation

### [ ] Phase 2: Modify EvidenceLinkedVerdictEngine
- [ ] Update `generate_verdict()` to return `(verdict, ledger_entry)` tuple
- [ ] Remove immediate ledger writing
- [ ] Add logging for pending ledger entries
- [ ] Update all callers in codebase to handle tuple return

### [ ] Phase 3: Modify VerdictEngineAdapter
- [ ] Update `reason()` to handle tuple return from engine
- [ ] Pass ledger_entry through to `_transform_verdict_to_response()`
- [ ] Store ledger_entry in response metadata
- [ ] Update `_transform_verdict_to_response()` signature

### [ ] Phase 4: Modify FortressProtectedReasoningService
- [ ] Update `reason()` to extract ledger_entry from response metadata
- [ ] Add `_update_ledger_with_validation()` helper method
- [ ] Add `_write_ledger_entry()` helper method
- [ ] Write ledger after validation with proper status

### [ ] Phase 5: Testing
- [ ] Test successful validation: ledger written with PASSED status
- [ ] Test failed validation: ledger written with FAILED status
- [ ] Test empty evidence: no ledger written, no errors
- [ ] Test deterministic mode: validation_status consistent
- [ ] Test concurrent requests: no race conditions

### [ ] Phase 6: Backward Compatibility
- [ ] Verify existing tests still pass
- [ ] Add deprecation warnings for old interfaces
- [ ] Document breaking changes in CHANGELOG.md

---

## 7. Rollback Plan

If implementation causes issues:

1. **Revert all changes** to the three modified files:
   - `mahoun/ledger/models.py`
   - `mahoun/core/fortress_validator.py`
   - `mahoun/reasoning/evidence_linked_verdict.py`

2. **Keep validation_status field** in LedgerEntry (backward compatible)

3. **Alternative approach**: Implement validation status tracking in a separate ledger table instead of modifying the main ledger flow

---

## 8. Success Criteria

The delayed ledger writing architecture is considered successful when:

1. ✅ All production tests pass
2. ✅ Ledger entries have `validation_status` field set correctly
3. ✅ No ledger entries have `validation_status=None` after validation
4. ✅ Fortress validation failures are properly tracked in ledger
5. ✅ Determinism is maintained (same input → same ledger entry)
6. ✅ Performance impact is negligible (< 5% latency increase)
7. ✅ No breaking changes to public APIs

---

## 9. Estimated Timeline

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Verify Phase 1 completion | 30 minutes |
| 2 | Modify EvidenceLinkedVerdictEngine | 2 hours |
| 3 | Modify VerdictEngineAdapter | 1 hour |
| 4 | Modify FortressProtectedReasoningService | 2 hours |
| 5 | Testing | 4 hours |
| 6 | Backward compatibility | 1 hour |
| **Total** | | **10.5 hours** |

---

## 10. Appendix: Code Snippets

### Current Ledger Entry Creation
```python
# mahoun/reasoning/evidence_linked_verdict.py, lines 560-569
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

### Proposed Ledger Entry Creation
```python
# mahoun/reasoning/evidence_linked_verdict.py
entry = LedgerEntry(
    verdict_id=verdict_id,
    case_id=case_id,
    referenced_ltm_nodes=referenced_ltm_nodes,
    referenced_facts=referenced_facts,
    confidence=confidence_score,
    invariant_version=INVARIANT_VERSION,
    guard_mode=get_guard_mode().value,
    created_at=fixed_timestamp,
    validation_status=None,  # NEW: Will be set after validation
)

# Validate but don't write yet
if referenced_ltm_nodes or referenced_facts:
    validate_entry(entry)
    # Return entry with verdict for later writing
    return verdict, entry
```

### Updating Ledger Entry with Validation Status
```python
# Using dataclasses.replace() to handle frozen dataclass
from dataclasses import replace

updated_entry = replace(
    ledger_entry,
    validation_status="PASSED" if passed else "FAILED"
)
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-24 | Mistral Vibe | Initial proposal |

---

*Document Location*: `/home/haji/Desktop/KingMahouN/DELAYED_LEDGER_WRITING_ARCHITECTURE.md`
