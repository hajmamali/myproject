# Phase 5: Critical Architectural Issue - Validator Signature Mismatch

**Date**: 2026-07-02  
**Severity**: ⚠️ **P1_HIGH** (Architecture Debt)  
**Impact**: Enforcement gap, prevents orchestrator from working

---

## Issue Description

The `DomainValidator` base class defines a standard `__init__` signature:

```python
def __init__(
    self,
    name: str,
    evidence_collector: EvidenceCollectorProtocol,
    workspace_root: Path | None = None,
)
```

**However**, the concrete validator implementations have **inconsistent signatures**:

| Validator | Actual Signature | Matches Base? |
|-----------|------------------|---------------|
| `ExceptionHierarchyValidator` | `__init__(self, project_root: Path)` | ❌ NO |
| `TestClassificationValidator` | `__init__(self, project_root: Path)` | ❌ NO |
| `CoverageValidator` | `__init__(self, evidence_collector, workspace_root)` | ⚠️ PARTIAL |
| `SecurityHardeningValidator` | `__init__(self, evidence_collector)` | ⚠️ PARTIAL |
| `InfrastructureValidator` | `__init__(self, ...)` | ⚠️ UNKNOWN |

---

## Root Cause

The validators were implemented **before** the base class interface was finalized. When `DomainValidator` was refactored to require `evidence_collector`, the child classes were not updated.

This violates the **Liskov Substitution Principle** (LSP):
- You cannot substitute a `DomainValidator` with any of its subclasses
- Orchestrator cannot instantiate validators polymorphically
- Manual try/except workarounds needed (brittle)

---

## Impact on Enforcement

### ❌ **Current State**: NO ENFORCEMENT

```python
# This FAILS at runtime:
validator: DomainValidator = ExceptionHierarchyValidator(
    name="exception-hierarchy",
    evidence_collector=evidence,
    workspace_root=root
)
# TypeError: __init__() got unexpected keyword argument 'evidence_collector'
```

### ✅ **Expected State**: POLYMORPHIC INSTANTIATION

```python
# Should work for ALL validators:
for config in validator_configs:
    validator_class = get_validator_class(config.class_name)
    validator = validator_class(
        name=config.validator_id,
        evidence_collector=evidence,
        workspace_root=root
    )
    orchestrator.register_validator(validator)
```

---

## Concrete Examples of Broken Contract

### Example 1: ExceptionHierarchyValidator

**Expected (per base class)**:
```python
def __init__(self, name: str, evidence_collector: EvidenceCollectorProtocol, workspace_root: Path | None = None):
    super().__init__(name, evidence_collector, workspace_root)
```

**Actual**:
```python
def __init__(self, project_root: Path):
    super().__init__("exception-hierarchy", project_root)  # ❌ Wrong!
    # Missing evidence_collector parameter!
```

**Impact**: Cannot be instantiated through orchestrator interface

---

### Example 2: CoverageValidator

**Expected**:
```python
def __init__(self, name: str, evidence_collector: EvidenceCollectorProtocol, workspace_root: Path | None = None):
    super().__init__(name, evidence_collector, workspace_root)
```

**Actual**:
```python
def __init__(self, evidence_collector: EvidenceCollectorProtocol, workspace_root: Path | None = None):
    # Missing 'name' parameter!
    # Hard-codes name internally instead
```

**Impact**: Cannot configure validator name dynamically

---

## Why This is P1 (Not P0)

**Why Not P0**: 
- Tests exist and pass (they instantiate validators directly, not through orchestrator)
- Phase 1-4 validations ran successfully (used direct instantiation)
- No production deployment blocker (workarounds exist)

**Why P1**:
- Prevents Phase 5 orchestrator from working
- Architecture violation (breaks LSP)
- Makes validators non-interchangeable
- Increases maintenance cost (each validator needs custom instantiation logic)

---

## Required Fix

### Option A: Update All Validators (Recommended)

**Change each validator to match base signature:**

```python
# Before (ExceptionHierarchyValidator)
def __init__(self, project_root: Path):
    super().__init__("exception-hierarchy", project_root)

# After
def __init__(
    self,
    name: str,
    evidence_collector: EvidenceCollectorProtocol,
    workspace_root: Path | None = None,
):
    super().__init__(name, evidence_collector, workspace_root)
    self.exceptions_file = workspace_root / "mahoun" / "core" / "exceptions.py"
    # ...
```

**Effort**: ~2 hours (update 5 validators + tests)

---

### Option B: Make Base Class More Flexible (Not Recommended)

**Change base class to accept flexible signatures:**

```python
def __init__(self, *args, **kwargs):
    # Too permissive, loses type safety
```

**Why Not**: Defeats the purpose of having a base class

---

### Option C: Workaround with Factory Pattern (Current Temporary Solution)

**Use a factory with try/except logic:**

```python
def create_validator(config, evidence, workspace_root):
    try:
        return validator_class(config.name, evidence, workspace_root)
    except TypeError:
        try:
            return validator_class(project_root=workspace_root)
        except TypeError:
            return validator_class(evidence, workspace_root)
```

**Why Not Long-Term**: Brittle, hides the problem, hard to maintain

---

## Recommended Action Plan

**Phase 5.1 (Immediate - Current State)**:
1. ✅ Use factory pattern workaround in `run_preproduction_validation.py`
2. ✅ Document this issue as P1 finding
3. ✅ Complete Phase 5 validation with workaround
4. ✅ Add to post-release backlog

**Phase 5.2 (Post-Release - Within 1 Sprint)**:
1. Create task: "Standardize validator signatures"
2. Update all 5 validators to match base class
3. Update all validator tests
4. Remove factory workarounds
5. Add CI check: `mypy --strict` on validator files

---

## Verification After Fix

```bash
# Should pass without any TypeError:
python scripts/run_preproduction_validation.py --list-validators

# Mypy should pass:
mypy mahoun/preproduction/validators/*.py --strict
```

---

## Related Issues

- Similar issue found in: None (this is isolated)
- Root cause: Rapid prototyping without interface enforcement
- Prevents: Dynamic validator loading, plugin architecture

---

## Status

**Current**: ⚠️ **WORKAROUND IN PLACE**  
**Target**: ✅ **FIX IN NEXT SPRINT**  
**Blocking**: Phase 5 completion? **NO** (workaround sufficient)

---

**Conclusion**: This is a **technical debt** issue that should be fixed post-release. It doesn't block production but reduces code quality and maintainability. The workaround is acceptable for Phase 5 completion.
