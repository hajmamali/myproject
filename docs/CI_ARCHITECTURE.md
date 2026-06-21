# MAHOUN ENTERPRISE CI/CD GOVERNANCE ARCHITECTURE

## 1. Overview & Philosophy
The MAHOUN CI pipeline is **NOT just a test runner**. It is an **Active Immune System** designed to continuously detect and destroy architectural entropy. Silent fallbacks, non-deterministic behaviors, and governance bypasses are treated as critical production-grade security failures.

## 2. CI Pipeline Matrix (The 6 Phases)

| Phase | Workflow | Purpose | Blocking? |
|-------|----------|---------|-----------|
| 1 | `01-governance-enforcement.yml` | Scans for forbidden patterns, direct `os.getenv` bypasses. | **YES** |
| 2 | `02-determinism-gates.yml` | Runs determinism suite, catching flaky or non-monotonic logic. | **YES** |
| 3 | `03-architecture-compliance.yml`| Analyzes Python AST for layer boundary violations. | **YES** |
| 4 | `04-quality-gates.yml` | Ruff, Black, Mypy, Pytest. Coverage enforcement. | **YES** |
| 5 | `05-security-forensics.yml` | Vulnerability scanning and artifact/evidence generation. | **YES** |
| 6 | `06-performance-stability.yml` | Validates retry-storm and concurrent async stability. | **YES** |

## 3. Failure Classification Matrix

| Failure Type | Example | Resolution Strategy |
|--------------|---------|---------------------|
| **Governance Bypass** | Direct `os.environ["MAHOUN_ENV"]` | Use `mahoun.core.environment.get_current_environment()`. |
| **Silent Fallback** | `except Exception: pass` | Must log the exception or re-raise it. |
| **Layer Violation** | `mahoun.core` imports `api` | Refactor. Core must not know about outer presentation layers. |
| **Determinism Failure** | Hash instability | Sort dictionary keys, use cryptographically seeded randoms. |
| **Concurrency Race** | `test_concurrent_async.py` fails | Ensure immutable contexts or strict locking mechanisms. |

## 4. Artifact Retention Policies

Because MAHOUN operations have high regulatory and audit demands, CI artifacts are retained significantly longer than standard projects:
- **Determinism Evidence**: Retained for **90 days**.
- **Coverage Reports**: Retained for **14 days**.
- **Security & Forensic Manifests**: Retained for **365 days** (Compliance requirement).

## 5. Developer Guidance

1. **NO "Allow Failure":** Determinism workflows will fail your PR if the output hash isn't strictly identical across identical inputs. You cannot bypass this.
2. **Canonical Environment Only:** Never use `os.getenv("MAHOUN_ENV")`. Import `mahoun.core.environment`.
3. **No Muted Exceptions:** If an invariant fails, crash the request gracefully and explicitly. Do not hide it.
4. **Architectural Purity:** A layer can only depend on layers below it. Guardrails and Core are foundational.
