# Gate 1 — Semantic Integrity Policy

## 1. Purpose

Gate 1 enforces **semantic intent**, not structural correctness.

While Gate 0 guarantees that the codebase is structurally sound (no `pass` stubs, no `TODO/FIXME`, no `NotImplementedError` in critical paths, and no hardcoded secrets), Gate 1 focuses on:

- Making `None` returns **intentional and explicit**
- Avoiding **silent exception swallowing**
- Ensuring **predicate functions** behave as strict booleans
- Requiring **clear documentation** when `None` is part of the contract

> **Policy Statement (Authoritative)**  
> Gate 1 enforces semantic intent, not perfection.  
> Optional returns are allowed only when explicit and intentional.

## 2. Scope

### Included Paths

Gate 1 analyzes only internal core logic:

- `mahoun/core/**`
- `mahoun/domain/**`
- `mahoun/orchestrator/**`

### Explicitly Excluded

Gate 1 **does not** analyze:

- `api/**` — API boundary semantics are already enforced by Gate 0
- `tests/**` — tests are free to use flexible patterns for verification
- `ci/**` — CI scripts are treated as infrastructure, not domain logic

This keeps Gate 1 focused on the **core semantic layer** of the platform.

## 3. Difference from Gate 0

- **Gate 0 — Structural Integrity (BLOCKING)**  
  - Enforces:  
    - No `pass` stubs in critical paths  
    - No `TODO/FIXME/XXX` markers  
    - No `NotImplementedError` stubs  
    - No `return None` in API boundaries (core is WARNING-only)  
    - No hardcoded secrets  
  - Scope: Structural, safety, and hygiene.

- **Gate 1 — Semantic Integrity (REPORT-ONLY in v1.1)**  
  - Enforces:
    - Optional-aware `None` returns
    - No silent exception swallowing via `return None`
    - Predicate functions behaving as strict booleans
    - Docstring clarity for `None`-capable functions  
  - Scope: **Intent and contracts**, not raw structure.

Gate 1 is layered **on top of** Gate 0 and does **not** weaken or replace it.

## 4. Rule Summary

Gate 1 is implemented as an AST-based semantic checker in:

- `ci/second_step/gate_1_semantic.py`

The rules below are enforced on `mahoun/core`, `mahoun/domain`, and `mahoun/orchestrator`.

### Rule 1 — Optional Return Contract

If a function contains `return None`, at least one of the following must hold:

1. The return annotation explicitly allows `None`, for example:
   - `-> Optional[T]`
   - `-> Union[T, None]`
   - `-> T | None`
   - `-> None` (functions that only ever return `None`)

2. The function name conventionally implies an Optional-like result:
   - Name starts with: `get_`, `find_`, `resolve_`, `load_`, `fetch_`

3. The docstring explicitly mentions that `None` can be returned:
   - e.g., `Returns None if the item is not found.`
   - e.g., `May return None when configuration is missing.`

If none of the above conditions hold and `return None` is present, Gate 1 reports:

- `ERROR: SEMANTIC_VIOLATION — None returned without explicit Optional contract`

### Rule 2 — Silent Exception Prohibition

The following pattern is **forbidden** in `core/domain/orchestrator` code:

```python
except Exception:
    return None
```

This is treated as a **silent exception** and reported as:

- `ERROR: SILENT_EXCEPTION — Silent exception: 'except Exception' followed by 'return None'.`

Allowed patterns include:

```python
except KnownError:
    return None
```

or

```python
except Exception as e:
    logger.debug("...", exc_info=True)
    return None
```

The goal is to avoid silently discarding exceptions without any trace, while still allowing graceful degradation with explicit logging or explicit error types.

### Rule 3 — Predicate Functions (Bool vs Optional Confusion)

Functions that:

- Have a name starting with `is_`, `has_`, or `should_`  
  **OR**
- Have a boolean return annotation (e.g., `-> bool`)

**MUST NOT** return `None`.

Any `return None` inside such functions is reported as:

- `ERROR: PREDICATE_RETURNS_NONE — Predicate function returns None (must be strictly bool).`

This prevents the classic confusion where a caller expects `True/False` but receives `None`.

### Rule 4 — Docstring Intent Clarity

If `return None` is allowed by contract (i.e., Rule 1 passes), the docstring must clearly explain when or why `None` is returned.

Examples of acceptable docstrings:

- `Returns None if the user does not exist.`
- `Returns None when the configuration key is missing.`

If a function may validly return `None` but the docstring does **not** mention `None` at all, Gate 1 reports:

- `WARNING: DOCSTRING_NONE_CLARITY — Function can return None but docstring does not explain when/why.`

This is advisory in v1.1 and intended to improve clarity over time.

## 5. Severity Model

Gate 1 distinguishes between **ERROR** and **WARNING** severity:

| Rule/Condition                   | Severity |
|----------------------------------|----------|
| Missing Optional contract        | ERROR    |
| Silent exception (`except Exception: return None`) | ERROR |
| Predicate function returns None  | ERROR    |
| Missing docstring clarity for allowed `None` | WARNING |

- **ERROR**: Semantically dangerous or ambiguous patterns that should eventually become blocking.
- **WARNING**: Clarity and documentation issues that should be improved but do not immediately break correctness.

## 6. Versioning & CI Behavior

### v1.1 — Report-Only Mode

In version **v1.1**:

- `ci/second_step/gate_1_semantic.py`:
  - Scans relevant paths
  - Prints grouped **ERROR** and **WARNING** findings per file
  - Always exits with **code 0** (non-blocking)
- Gate 1 serves as a **semantic observability layer**, not a gatekeeper.

This allows the team to:

- Understand semantic risks
- Triage findings
- Incrementally improve contracts and docstrings

without blocking day-to-day development.

### v1.2 — Blocking on ERROR

In **v1.2** (or a future agreed release), Gate 1 may be escalated to:

- **Blocking on ERROR**, while WARNINGs remain advisory:
  - Any `ERROR` finding will cause a non-zero exit code.
  - WARNINGs will continue to be printed but will not block CI.

The transition from v1.1 to v1.2 should be:

- Announced to the team
- Supported by prior cleanup of existing errors
- Documented clearly in CI release notes

## 7. Integration in CI Pipeline

Recommended execution order:

1. `ci/first_step/gate_0_integrity.sh`  
   - Structural integrity (BLOCKING)

2. `ci/second_step/gate_1_semantic.py`  
   - Semantic integrity (REPORT-ONLY in v1.1)

3. Subsequent gates:
   - Lint, typing, reality, determinism, artifacts, etc.

Gate 1 is explicitly designed to:

- Be **separable** from Gate 0
- Focus only on **semantic intent and Optional-awareness**
- Avoid over-policing or forcing hacks in core code

## 8. Final Policy Statement

> Gate 1 enforces semantic intent, not perfection.  
> Optional returns are allowed only when explicit and intentional.  
>  
> Gate 0 ensures the codebase is structurally sound.  
> Gate 1 ensures that `None` and exceptions are used with clear, explicit contracts.
