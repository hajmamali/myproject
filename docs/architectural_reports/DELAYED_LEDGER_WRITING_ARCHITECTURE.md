# MAHOUN Delayed Ledger Writing Architecture

## Executive Summary

The current MAHOUN execution flow has a **critical trust gap**: LedgerEntry is written to immutable storage BEFORE Fortress validation completes. This violates the fundamental principle that the ledger must be the immutable source of execution truth.

### Current Problem (TRUST GAP)

```
Request ↓
Reasoning ↓
Verdict generated ↓
LedgerEntry created and COMMITTED ❌ ↓
Fortress validation ↓
PASS / FAIL
```

**Risk**: A rejected verdict can exist in the ledger without clear validation state. The ledger becomes a storage location, not a trustworthy execution record.

---

## Target Architecture (TRUST PRESERVED)

```
Request ↓
Execution Context ↓
Reasoning ↓
Verdict Generated ↓
Pending Ledger Event created ↓
Fortress Validation ↓
Validation Result attached ↓
Ledger Commit ✓
```

**Guarantee**: The ledger records BOTH successful AND failed executions with their validation state. Nothing disappears from audit history.

---

## Implementation Plan

### Phase 1: Architecture Analysis (COMPLETED)

**Findings**:
1. Ledger creation occurs in `EvidenceLinkedVerdictEngine.generate_verdict()`
2. Ledger write is immediate (no pending state)
3. Fortress validation occurs AFTER ledger commit
4. No mechanism exists to record failed validations in ledger

**Impacted Files**:
- `mahoun/reasoning/evidence_linked_verdict.py` (primary)
- `mahoun/reasoning/verdict_engine_adapter.py` (secondary)
- `mahoun/reasoning/fortress_integration.py` (tertiary)
- `mahoun/ledger/writer.py` (ledger commit logic)
- `mahoun/ledger/models.py` (LedgerEntry model)
- `api/routers/reasoning.py` (API integration)

### Phase 2: Minimal Safe Change (IN PROGRESS)

#### 1. VerdictExecutionResult Contract

**Location**: `mahoun/contracts/verdict_execution.py`

```python
@dataclass(frozen=True)
class VerdictExecutionResult:
    """
    Explicit contract for execution lifecycle artifacts.
    
    RULE 3: No hidden transport - all execution artifacts travel through
    this contract, NOT through metadata or thread locals.
    """
    verdict: EvidenceLinkedVerdict
    ledger_entry: LedgerEntry  # Pending, not yet committed
    execution_id: str
    correlation_id: str
    case_id: str
    proof: Proof
    validation_status: Optional[ValidationStatus] = None
    validation_violations: List[GovernanceViolation] = field(default_factory=list)
```

**Why This Contract?**
- Prevents lifecycle leakage into metadata
- Explicit ownership of execution artifacts
- Immutable (frozen=True) - cannot be modified after creation
- Contains all artifacts needed for ledger commit

#### 2. EvidenceLinkedVerdictEngine Changes

**Current Behavior** (VIOLATES RULE 1):
```python
def generate_verdict(self, question: str, facts: list) -> EvidenceLinkedVerdict:
    # ... reasoning ...
    verdict = EvidenceLinkedVerdict(...)
    
    # ❌ WRONG: Commits ledger BEFORE validation
    ledger_entry = LedgerEntry(verdict=verdict, ...)
    self.ledger_writer.commit(ledger_entry)
    
    return verdict
```

**Required Behavior** (COMPLIES WITH RULE 1-2):
```python
def generate_verdict(self, question: str, facts: list) -> VerdictExecutionResult:
    # ... reasoning ...
    verdict = EvidenceLinkedVerdict(...)
    
    # ✓ CORRECT: Creates ledger entry but DOES NOT commit
    ledger_entry = LedgerEntry(
        verdict=verdict,
        status=ExecutionStatus.PENDING,
        execution_id=execution_id,
        correlation_id=correlation_id,
        case_id=case_id
    )
    
    # ✓ CORRECT: Creates proof
    proof = self.proof_system.generate_proof(
        verdict=verdict,
        evidence_refs=verdict.evidence_references,  # RULE 5: Real evidence
        execution_id=execution_id
    )
    
    # ✓ CORRECT: Returns execution result (no ledger commit)
    return VerdictExecutionResult(
        verdict=verdict,
        ledger_entry=ledger_entry,
        execution_id=execution_id,
        correlation_id=correlation_id,
        case_id=case_id,
        proof=proof,
        validation_status=None,  # Not yet validated
        validation_violations=[]
    )
```

#### 3. FortressProtectedReasoningService Changes

**New Responsibility** (RULE 6): Final ledger commit

```python
class FortressProtectedReasoningService:
    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        # Receive execution result from adapter
        execution_result = await self.reasoning_service.reason(request)
        
        # RULE 4: Proof generation is OWNED by execution pipeline
        # (already done in EvidenceLinkedVerdictEngine)
        
        # RULE 11: Failed validation MUST also create ledger history
        try:
            # Run Fortress validation
            validation_result = self.fortress_validator.validate(
                request=request,
                verdict=execution_result.verdict,
                proof=execution_result.proof
            )
            
            # PASSED path
            execution_result.ledger_entry.validation_status = ValidationStatus.PASSED
            execution_result.validation_status = ValidationStatus.PASSED
            
        except GovernanceViolationError as e:
            # FAILED path - MUST preserve audit trail
            execution_result.ledger_entry.validation_status = ValidationStatus.FAILED
            execution_result.ledger_entry.validation_violations = e.violation
            execution_result.validation_status = ValidationStatus.FAILED
            execution_result.validation_violations = [e.violation]
        
        # RULE 7: Ledger becomes source of truth
        # Commit ledger with validation status
        self.ledger_commit_service.commit(execution_result.ledger_entry)
        
        # Return response with all execution artifacts
        return execution_result
```

#### 4. VerdictEngineAdapter Changes

**Purpose**: Transform between VerdictExecutionResult and ReasoningResponse

```python
def create_verdict_engine_adapter(engine: EvidenceLinkedVerdictEngine):
    class Adapter:
        async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
            # Call engine with new signature
            execution_result = await engine.generate_verdict(
                question=request.question,
                facts=request.facts,
                correlation_id=request.correlation_id,
                case_id=request.case_id
            )
            
            # Transform to ReasoningResponse
            # RULE 9: API Router is transport only - no execution assembly
            return ReasoningResponse(
                verdict=execution_result.verdict,
                proof=execution_result.proof,
                ledger_entry=execution_result.ledger_entry,
                metadata={
                    "execution_id": execution_result.execution_id,
                    "correlation_id": execution_result.correlation_id,
                    "case_id": execution_result.case_id,
                    "validation_status": execution_result.validation_status,
                    "fortress_validated": execution_result.validation_status == ValidationStatus.PASSED
                }
            )
    
    return Adapter()
```

#### 5. LedgerEntry Model Enhancement

**RULE 6**: Validation status belongs to execution history

```python
class LedgerEntry:
    # Existing fields...
    
    # NEW: Validation status (RULE 6)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_violations: List[GovernanceViolation] = field(default_factory=list)
    validation_timestamp: Optional[str] = None
    validator_version: Optional[str] = None
    
    # NEW: Execution correlation (RULE 7)
    execution_id: str
    correlation_id: str
    case_id: str
```

**Decision**: `validation_status` belongs to **LedgerEntry**, not Verdict or Execution.
- Reasoning: The ledger is the source of truth for execution history
- The verdict itself is immutable (its content doesn't change)
- The execution status (passed/failed) is part of the ledger event

#### 6. LedgerCommitService Changes

**RULE 8**: Explicit dependency injection (no object graph walking)

```python
class LedgerCommitService:
    """
    Dedicated service for committing ledger entries.
    
    RULE 8: Fortress must NOT discover LedgerWriter by walking object graphs.
    Instead: Inject explicitly.
    """
    
    def __init__(self, ledger_writer: EvidenceLedgerWriter, strict_mode: bool = True):
        self.ledger_writer = ledger_writer
        self.strict_mode = strict_mode
    
    def commit(self, ledger_entry: LedgerEntry) -> None:
        """
        Commit a ledger entry to immutable storage.
        
        RULE 10: Execution is atomic - if commit fails, execution fails.
        """
        if self.strict_mode:
            # Validate ledger entry before commit
            self._validate_ledger_entry(ledger_entry)
        
        self.ledger_writer.write(ledger_entry)
    
    def _validate_ledger_entry(self, entry: LedgerEntry) -> None:
        """Ensure ledger entry has all required fields."""
        if not entry.execution_id:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.AUDIT_FAILURE,
                    severity=ViolationSeverity.CRITICAL,
                    message="Ledger entry missing execution_id",
                    details={"entry": str(entry)},
                    source="LedgerCommitService"
                )
            )
```

---

## Critical Invariants (RULES 1-15)

### RULE 1: Ledger NEVER written before Fortress validation
✓ **Enforced**: LedgerEntry created in PENDING state, committed only after Fortress

### RULE 2: Delayed Ledger Commit
✓ **Enforced**: EvidenceLinkedVerdictEngine creates but does NOT commit

### RULE 3: No hidden transport
✓ **Enforced**: VerdictExecutionResult contract owns all execution artifacts

### RULE 4: Proof generation ownership
✓ **Enforced**: Proof generated in EvidenceLinkedVerdictEngine, not Router

### RULE 5: Evidence binding
✓ **Enforced**: ProofSystem receives actual EvidenceReference objects, not empty refs

### RULE 6: Validation result ownership
✓ **Enforced**: LedgerEntry records validation_status, violations, timestamp

### RULE 7: Ledger as source of truth
✓ **Enforced**: LedgerEntry contains all fields needed for reconstruction

### RULE 8: Dependency Direction
✓ **Enforced**: LedgerCommitService injected explicitly, no graph walking

### RULE 9: No lifecycle leakage into API
✓ **Enforced**: API Router is transport only

### RULE 10: Execution Atomicity
✓ **Enforced**: Commit happens only once, after all validations

### RULE 11: Audit completeness
✓ **Enforced**: FAILED executions also create ledger entries

### RULE 12: Determinism
✓ **Preserved**: case_id, verdict_id, evidence ordering unchanged

### RULE 13: Backward Compatibility
⚠️ **Partial**: Public API preserved where possible, but trustworthiness takes priority

### RULE 14: Governance
✓ **Enforced**: Every execution inside GovernanceContext

### RULE 15: EL-I8 Completion
✓ **Target**: Evidence → Inference → Proof → Fortress → Ledger (all links present)

---

## Migration Strategy

### Step 1: Create New Contracts
- Add `VerdictExecutionResult` to `mahoun/contracts/verdict_execution.py`
- Add `ValidationStatus` enum
- Add `LedgerCommitService` class

### Step 2: Update Core Engine
- Modify `EvidenceLinkedVerdictEngine.generate_verdict()` to return `VerdictExecutionResult`
- Ensure proof generation uses real evidence references
- Create ledger entry but DO NOT commit

### Step 3: Update Adapter Layer
- Modify `create_verdict_engine_adapter()` to handle new return type
- Transform `VerdictExecutionResult` to `ReasoningResponse`

### Step 4: Update Fortress Integration
- Modify `FortressProtectedReasoningService.reason()` to:
  - Receive `VerdictExecutionResult` from adapter
  - Run validation
  - Attach validation result to ledger_entry
  - Commit ledger via `LedgerCommitService`

### Step 5: Update Ledger Model
- Add validation fields to `LedgerEntry`
- Ensure immutability

### Step 6: Update API Router
- Inject `LedgerCommitService` via dependency injection
- Ensure router remains transport only

### Step 7: Testing
- All existing tests must pass (except those that test the OLD broken behavior)
- New tests for:
  - Successful verdict with delayed commit
  - Failed validation with ledger recording
  - Determinism across multiple runs
  - Case evolution with multiple verdicts
  - Ledger reconstruction

---

## Trust Guarantees After Implementation

### ✓ Reproducibility
- Same case_id + evidence + execution config = same verdict_id
- Evidence selection deterministic
- Reasoning path deterministic

### ✓ Verifiability
- Every ledger entry has validation_status
- Proof includes real evidence references
- Merkle root represents actual evidence

### ✓ Traceability
- Ledger entry references execution_id, correlation_id, case_id
- Can reconstruct: Case → Evidence → Reasoning → Validation → Verdict

### ✓ Auditability
- Failed executions recorded in ledger
- Validation violations preserved
- Immutability guaranteed

---

## Risk Assessment

### High Risk (Must Mitigate)
1. **Backward Compatibility**: Existing code that calls `generate_verdict()` expects `EvidenceLinkedVerdict`, not `VerdictExecutionResult`
   - **Mitigation**: Create adapter layer for backward compatibility
   
2. **Performance**: Delayed commit may increase latency
   - **Mitigation**: Ledger commit is async, minimal impact
   
3. **Memory**: Holding execution artifacts in memory until commit
   - **Mitigation**: Artifacts are small (verdict, proof, metadata)

### Medium Risk (Acceptable)
1. **Test Updates**: Many tests expect immediate ledger write
   - **Mitigation**: Update tests to verify delayed commit behavior
   
2. **Error Handling**: New failure modes (validation after ledger creation)
   - **Mitigation**: Comprehensive error handling in all new code

### Low Risk (Minimal)
1. **Code Complexity**: More classes and contracts
   - **Mitigation**: Clear documentation, explicit ownership

---

## Rollback Plan

If implementation causes critical regressions:
1. Revert to old `generate_verdict()` signature with immediate commit
2. Add feature flag to toggle delayed commit on/off
3. Gradual migration path for dependent systems

---

## Success Criteria

The implementation is **ACCEPTED** only if:

1. ✓ No execution path where Ledger is committed before Fortress validation
2. ✓ No execution path where Proof is detached from Evidence
3. ✓ No execution path where Validation disappears from Ledger
4. ✓ No execution path where Router owns execution logic
5. ✓ Single execution ownership
6. ✓ Explicit contracts
7. ✓ Immutable audit trail
8. ✓ Dependency inversion
9. ✓ Atomic execution
10. ✓ Full reconstructability

**Any shortcut to make tests pass is REJECTED**. Architecture integrity > backward compatibility.

---

## Architecture Decision Record (ADR)

### Decision: Delayed Ledger Commit with Explicit Execution Contract

**Status**: PROPOSED  
**Date**: 2026-07-25  
**Context**: MAHOUN Phase 2 - Trust Architecture Migration  

**Decision**: 
- Introduce `VerdictExecutionResult` contract for explicit execution artifact ownership
- Delay ledger commit until after Fortress validation
- Record both PASSED and FAILED executions in ledger
- Inject `LedgerCommitService` explicitly (no object graph walking)

**Alternatives Considered**:
1. **Keep immediate commit**: Rejected - violates trust principles
2. **Two-phase commit**: Rejected - adds complexity without clear benefit
3. **Event sourcing**: Rejected - too much architectural change

**Consequences**:
- **Positive**: Trustworthy execution records, audit completeness
- **Negative**: Requires updating dependent code, test changes needed

**Author**: MAHOUN Architecture Team  
**Approved**: Pending runtime verification

---

## Next Steps

1. **Implement VerdictExecutionResult contract** (Priority: CRITICAL)
2. **Update EvidenceLinkedVerdictEngine** (Priority: CRITICAL)
3. **Create LedgerCommitService** (Priority: CRITICAL)
4. **Update FortressProtectedReasoningService** (Priority: CRITICAL)
5. **Update LedgerEntry model** (Priority: HIGH)
6. **Write automated tests** (Priority: HIGH)
7. **Run gate_9_governance.sh** (Priority: HIGH)
8. **Produce final verification report** (Priority: MEDIUM)

---

*Document generated as part of MAHOUN Phase 2 - Trust Architecture Migration*
*Classification: ARCHITECTURE / CRITICAL / NON-NEGOTIABLE*
