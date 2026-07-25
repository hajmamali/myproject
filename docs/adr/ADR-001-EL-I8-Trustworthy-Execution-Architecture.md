# ADR-001: EL-I8 Trustworthy Execution Architecture

## Status
**ACCEPTED** - Implementation Complete, Verification Pending

## Context

The MAHOUN Legal AI system had a **critical trust gap** in its execution lifecycle: the ledger was being written **BEFORE** Fortress validation. This meant that:

1. Unverified verdicts could exist in the immutable ledger
2. There was no record of whether validation passed or failed
3. The ledger could not answer: "Given a verdict_id, was it validated or rejected?"
4. Proof generation was happening in the wrong layer (router instead of execution pipeline)
5. Proof was not cryptographically bound to evidence (evidence_refs was empty list)

This violated the fundamental principle that a legal AI system must have **trustworthy, auditable, and verifiable** execution records.

### Problem Statement

The system's execution flow was:
```
Request → Verdict Engine (WRITE LEDGER HERE) → Adapter → Fortress Validation → Response (Generate Proof)
```

**Issues:**
- ❌ Ledger written before validation (trust gap)
- ❌ Proof generated in router (wrong layer)
- ❌ Proof not bound to evidence (evidence_refs=[])
- ❌ No validation status in ledger
- ❌ Router owning execution logic

### Desired State

The system needed:
```
Request → Verdict Engine (CREATE artifacts) → Adapter → Fortress Validation → COMMIT LEDGER → Response
```

With:
- ✅ Ledger committed AFTER validation
- ✅ Proof generated in execution pipeline
- ✅ Proof bound to actual evidence
- ✅ Validation status recorded in ledger
- ✅ Router as transport only
- ✅ Explicit contracts for artifact transport

---

## Decision

### Implement Delayed Ledger Commit Architecture

We decided to implement a **Delayed Ledger Commit** architecture where:

1. **EvidenceLinkedVerdictEngine** creates all execution artifacts (verdict, proof, pending ledger entry) but **DOES NOT** commit the ledger
2. **VerdictExecutionResult** contract transports all artifacts explicitly (no hidden state)
3. **FortressProtectedReasoningService** validates the response, then **commits the ledger with validation results**
4. **API Router** becomes transport-only (no execution logic)
5. **LedgerEntry** model enhanced to store validation status and proof hashes

### New Component: VerdictExecutionResult Contract

```python
@dataclass(frozen=True)
class VerdictExecutionResult:
    # Required
    verdict: EvidenceLinkedVerdict
    ledger_entry: LedgerEntry  # PENDING - not committed
    execution_id: str
    correlation_id: str
    execution_timestamp: datetime
    
    # Optional
    proof: CryptographicProof | None
    validation_passed: bool | None
    validation_violations: list | None
    validation_timestamp: datetime | None
    fortress_version: str | None
    reasoning_depth: int = 0
    evidence_count: int = 0
    agreement_score: float | None = None
```

### New Component: LedgerCommitService

Dedicated service for committing ledger entries **AFTER** validation. Explicitly injected (not discovered via object graphs).

```python
class LedgerCommitService:
    def __init__(self, ledger_writer: EvidenceLedgerWriter, strict_mode: bool = True):
        self.ledger_writer = ledger_writer
        self.strict_mode = strict_mode
    
    async def commit_execution(
        self,
        execution_result: VerdictExecutionResult,
        validation_passed: bool,
        validation_violations: list | None,
        validation_timestamp: datetime | None,
        fortress_version: str | None
    ) -> LedgerCommitResult:
        # Updates ledger entry with validation results
        # Commits to immutable storage
        # Returns commit result
```

---

## Architectural Changes

### Before (BROKEN)

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────────┐
│   API Router    │────▶│ VerdictEngine        │────▶│ WRITE LEDGER           │
│                 │     │                     │     │ (Before validation!)    │
└─────────────────┘     └─────────────────────┘     └──────────┬───────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────────┐
│   (continue)     │     │ VerdictEngineAdapter  │     │ CREATE VERDICT          │
│   API Router    │◀────│                     │◀────│                         │
└─────────────────┘     └─────────────────────┘     └─────────────────────────┘
                                                           │
                                                           ▼
                                                    ┌─────────────────────────┐
                                                    │ Fortress Validation       │
                                                    │ (AFTER ledger write!)     │
                                                    └─────────────────────────┘
                                                           │
                                                           ▼
                                                    ┌─────────────────────────┐
                                                    │ GENERATE PROOF            │
                                                    │ (In router - wrong!)     │
                                                    └─────────────────────────┘
```

### After (TRUSTWORTHY)

```
┌─────────────────┐
│   API Router    │
│   (Transport)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  EvidenceLinkedVerdictEngine                                   │
│  - Generate verdict from question + facts                        │
│  - Build graph, detect contradictions, resolve                  │
│  - Generate proof with evidence_refs (NOT [])                    │
│  - Create LedgerEntry (PENDING - NOT committed)                 │
│  - Return VerdictExecutionResult                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  VerdictEngineAdapter                                          │
│  - Transform VerdictExecutionResult to ReasoningResponse        │
│  - Store execution_result in metadata for Fortress              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  FortressProtectedReasoningService                             │
│  - Execute reasoning_service.reason()                           │
│  - Extract execution_result from response                       │
│  - Validate through FortressValidator                           │
│  - **COMMIT LEDGER AFTER VALIDATION** (NEW!)                  │
│    - Update ledger_entry with validation results                │
│    - Commit via LedgerCommitService                             │
│    - Handles both PASSED and FAILED                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                 Return Response to Client
```

---

## Consequences

### Positive

1. **Trustworthy Ledger**: Every ledger entry now records validation status (PASSED/FAILED)
2. **Evidence-Proof Binding**: Proof is cryptographically bound to actual evidence (not empty)
3. **Separation of Concerns**: Each layer has a single responsibility
4. **Explicit Contracts**: No hidden transport mechanisms (RULE 3)
5. **Atomic Execution**: All steps succeed or fail together (RULE 10)
6. **Complete Audit Trail**: Ledger can reconstruct complete execution (RULE 7)

### Negative

1. **Backward Compatibility**: Old code expecting `EvidenceLinkedVerdict` return type will break
2. **Complexity**: Additional abstraction layer (VerdictExecutionResult)
3. **Migration Effort**: Existing tests and callers need updates

### Neutral

1. **Performance**: Proof generation moved from router to engine (same work, different location)
2. **Memory**: Pending ledger entries held in memory until commit (minimal impact)

---

## Alternatives Considered

### Alternative 1: Minimal Change - Just Move Ledger Write

**Rejected** because:
- Would still violate RULE 3 (no hidden transport)
- Proof would still be in router
- Evidence would still not be bound to proof
- Only fixes one of five issues

### Alternative 2: Event-Based Architecture

**Rejected** because:
- Too complex for current needs
- Would require major refactoring
- Over-engineered for the problem
- Violates RULE 13 (minimal changes)

### Alternative 3: Decorator-Based Ledger Commit

**Rejected** because:
- Hidden transport (violates RULE 3)
- Not explicit enough
- Harder to test and debug

---

## Verification

### Tests Created

1. **test_el_i8_implementation.py** - Runtime verification of all components
2. Manual verification of file compilation
3. Verification of all architectural rules

### Verification Checklist

- [x] All files compile without errors
- [x] VerdictExecutionResult contract works
- [x] LedgerEntry has new fields
- [x] LedgerCommitService can be instantiated
- [x] Fortress accepts ledger_commit_service
- [x] Router no longer generates proofs
- [ ] Runtime execution test (requires full environment)
- [ ] Proof contains evidence references (requires runtime)
- [ ] Ledger commit happens after validation (requires runtime)

---

## Compliance Matrix

| Rule | Status | Implementation |
|------|--------|----------------|
| RULE 1 | ✅ | Ledger written AFTER Fortress validation |
| RULE 2 | ✅ | Delayed ledger commit |
| RULE 3 | ✅ | VerdictExecutionResult explicit contract |
| RULE 4 | ✅ | Proof generated in engine |
| RULE 5 | ✅ | evidence_refs passed to proof_system |
| RULE 6 | ✅ | validation_status in LedgerEntry |
| RULE 7 | ✅ | Ledger has all execution data |
| RULE 8 | ✅ | LedgerCommitService explicitly injected |
| RULE 9 | ✅ | Router is transport-only |
| RULE 10 | ✅ | Atomic execution |
| RULE 11 | ✅ | Both PASSED and FAILED recorded |
| RULE 12 | ✅ | Determinism preserved |
| RULE 13 | ⚠️ | Partial backward compatibility |
| RULE 14 | ✅ | Governance context maintained |
| RULE 15 | ✅ | EL-I8 chain complete |

---

## Related Documents

- [LEDGER_LIFECYCLE_ANALYSIS.md](../LEDGER_LIFECYCLE_ANALYSIS.md) - Architecture analysis
- [EL_I8_ARCHITECTURE_AUDIT_REPORT.md](../EL_I8_ARCHITECTURE_AUDIT_REPORT.md) - Pre-implementation audit
- [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) - Implementation tracking
- [Migration Report](ADR-001-MIGRATION-REPORT.md) - Migration details
- [Risk Report](ADR-001-RISK-REPORT.md) - Risk assessment
- [Test Report](ADR-001-TEST-REPORT.md) - Test results

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-07-24 | MAHOUN Platform Governance Council | Initial ADR created |
| 2026-07-24 | Implementation Team | Implementation completed |

---

## Decision Record Metadata

- **ADR Number**: ADR-001
- **Title**: EL-I8 Trustworthy Execution Architecture
- **Status**: ACCEPTED
- **Deciders**: MAHOUN Platform Governance Council
- **Date**: 2026-07-24
- **Supersedes**: None
- **Superseded By**: None
