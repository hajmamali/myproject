# MAHOUN Governance Enforcement Layer

## MANDATORY AI AGENT CONSTITUTIONAL BOOTSTRAP

All AI agents working on MAHOUN MUST perform the following initialization before any analysis, planning, coding, modification, refactoring, testing, or architectural decision.

## Step 1 — Constitutional Loading

The agent MUST read and understand:

`/home/haji/Desktop/KingMahouN/mahoun/constitutional/constitution/CONSTITUTION.md`

This document is the root authority for MAHOUN development governance.

No repository action is authorized before constitutional loading is completed.

## Step 2 — Authority Hierarchy

The following authority hierarchy MUST be respected:

1. Constitutional documents
2. Workflow definitions
3. Agent role instructions
4. Repository implementation details
5. Local tooling and IDE metadata

Lower-level instructions MUST NEVER override higher-level authority.

## Step 3 — Source of Truth

The directory:

`/home/haji/Desktop/KingMahouN/mahoun/constitutional/`

is the single authoritative governance source for:

- Architecture decisions
- Governance boundaries
- Security rules
- API evolution policies
- Workflow execution rules
- Agent behavior constraints

## Step 4 — Forbidden Assumptions

Agents MUST NOT consider the following as architectural authority:

- `.ai/`
- `.cursor/`
- `.vscode/`
- IDE-generated instructions
- Client-specific metadata
- Generated files
- Temporary agent memory
- Previous agent assumptions

These sources may be consulted only when explicitly referenced by constitutional documents.

## Step 5 — Conflict Resolution

If any conflict exists between:

- Agent instructions
- IDE instructions
- Client configuration
- Generated metadata
- Existing implementation

the constitutional documents ALWAYS take precedence.

## Step 6 — Architectural Changes

Before performing any of the following actions, the agent MUST consult relevant constitutional documents:

- Creating new modules
- Moving files
- Changing public APIs
- Modifying governance logic
- Altering contracts/schema
- Changing workflow behavior
- Refactoring core architecture

## Step 7 — Fail Closed Rule

If constitutional documents cannot be accessed, are missing, ambiguous, or contradictory:

The agent MUST NOT proceed with architectural changes.

The agent MUST:

1. Report the conflict.
2. Identify the missing authority source.
3. Request clarification.

Silent assumption is prohibited.

## Final Rule

MAHOUN is governed by constitutional architecture.

Agents are execution units, not architectural authorities.

No agent, model, IDE, plugin, or client configuration may redefine MAHOUN architecture outside the constitutional process.

## Overview

This directory contains the **Police** (Tier-1) - Governance Enforcement Tools that protect the **Constitution** (Tier-0 Kernel).

### Architectural Principle

```
Tier-0 Kernel (Constitution) - mahoun/core/governance_kernel/
    |
    | (read-only inspection only)
    v
Tier-1 Governance Tools (Police) - mahoun/governance/
    |
    v
CI / Audit / Security Layer
```

**The kernel CANNOT depend on the police that protects it.**

## Directory Structure

```
mahoun/governance/
├── __init__.py                 # Governance module exports
├── kernel_guard.py             # Kernel integrity protection
├── architecture_guard.py        # Architecture boundary enforcement
├── api_guard.py                # Public API protection
└── README.md                   # This file
```

## Tools

### 1. Kernel Guard (`kernel_guard.py`)
**Purpose:** Protect Tier-0 kernel from unauthorized modifications

**Features:**
- SHA256 fingerprint calculation for protected files
- Lock file generation and verification
- Kernel change authorization tracking
- Attestation generation and verification
- Manifest validation

**Usage:**
```bash
# Verify kernel integrity
python -m mahoun.governance.kernel_guard --verify

# Update lock file (after authorized changes)
python -m mahoun.governance.kernel_guard --update

# Authorize a kernel change
python -m mahoun.governance.kernel_guard --authorize-change \
    --version 1.1.0 \
    --reason "Security fix for CVE-2026-XXXX" \
    --approved-by "security-team"

# Generate attestation
python -m mahoun.governance.kernel_guard --generate-attestation

# Verify attestation
python -m mahoun.governance.kernel_guard --verify-attestation

# Validate manifest structure
python -m mahoun.governance.kernel_guard --validate-manifest
```

### 2. Architecture Guard (`architecture_guard.py`)
**Purpose:** Enforce architecture boundaries and detect violations

**Features:**
- AST-based import analysis (not just grep)
- Per-tier forbidden import checking
- Layer violation detection (Tier-0 importing from higher tiers)
- Governance bypass pattern detection
- Duplicate symbol detection
- Context-aware checking (skips comments, docstrings, governance tools)

**Usage:**
```bash
# Full architecture verification
python -m mahoun.governance.architecture_guard --verify

# Check specific violations
python -m mahoun.governance.architecture_guard --check-imports
python -m mahoun.governance.architecture_guard --check-layers
python -m mahoun.governance.architecture_guard --check-bypass
python -m mahoun.governance.architecture_guard --check-duplicates

# Check a specific file
python -m mahoun.governance.architecture_guard --check-file mahoun/core/some_file.py
```

### 3. API Guard (`api_guard.py`)
**Purpose:** Protect public APIs from unauthorized changes

**Features:**
- API extraction from source code and imported modules
- Snapshot generation and storage
- Drift detection (missing, new, signature-changed members)
- Critical interface verification
- Module path to import path conversion

**Usage:**
```bash
# Generate API snapshot
python -m mahoun.governance.api_guard --update

# Verify API against snapshot
python -m mahoun.governance.api_guard --verify

# Check critical interfaces only
python -m mahoun.governance.api_guard --check-critical

# Check a specific module
python -m mahoun.governance.api_guard --check-module mahoun.core.governance_kernel.kernel
```

## Constitution Files

The **Constitution** (source of truth) is stored in the `constitution/` directory:

```
constitution/
├── kernel.manifest.yaml       # Main manifest (source of truth)
├── kernel.lock                 # SHA256 fingerprints of Tier-0 files
├── kernel_changes.yaml         # Authorized kernel modifications
├── kernel.attestation.json     # Signed kernel state attestation
└── api.snapshot.json           # Public API snapshot
```

## Makefile Targets

Quick access via Makefile:

```bash
# Verify everything
make governance-verify

# Individual checks
make kernel-verify           # Verify kernel integrity
make architecture-verify    # Verify architecture boundaries
make api-verify              # Verify API compatibility
make manifest-validate       # Validate manifest structure
make attestation-verify      # Verify kernel attestation

# Update operations (require authorization)
make kernel-update           # Update kernel lock
make api-update              # Update API snapshot
```

## CI/CD Integration

The GitHub Actions workflow `.github/workflows/kernel-governance.yml` runs automatically on:
- Push to `main`, `develop`, `release/*` branches
- Pull requests to these branches

**Jobs:**
1. `kernel-integrity` - Verify kernel files haven't been modified without authorization
2. `architecture-enforcement` - Verify no forbidden imports or layer violations
3. `api-compatibility` - Verify public API hasn't changed without authorization
4. `governance-tests` - Run governance-specific test suite
5. `security-validation` - Additional security checks

**Branch Protection:**
- main branch requires all 5 jobs to pass before merge
- Protected branches cannot be force-pushed
- Status checks must pass

## Configuration

All configuration is in `constitution/kernel.manifest.yaml`:

```yaml
kernel:
  name: "mahoun_governance_kernel"
  version: "1.0.0"
  description: "Immutable Constitutional Kernel"
  strict_mode: true

tiers:
  tier_0:
    description: "The Constitution"
    protected_files:
      - "mahoun/core/governance_kernel/__init__.py"
      - "mahoun/core/governance_kernel/kernel.py"
    forbidden_imports:
      - "mahoun.governance"
      - "neo4j"
      - "sqlalchemy"
      # ... etc
  
  tier_1:
    description: "The Police"
    protected_files:
      - "mahoun/governance/__init__.py"
      - "mahoun/governance/kernel_guard.py"
      # ... etc
    forbidden_imports:
      - "mahoun.api"
      - "mahoun.pipelines"
      # ... etc

boundaries:
  forbidden_imports:
    tier_0:
      - "mahoun.governance"
      - "neo4j"
      # ... etc

  tier_boundary_violations:
    tier_0_cannot_import:
      - "tier_1"
      - "tier_2"

  layer_violations:
    forbidden_layers_for_tier_0:
      - "api"
      - "infrastructure"
      - "pipelines"

detection:
  governance_bypass:
    enabled: true
    patterns:
      - "raw_session ="
      - "bypass_governance("
      # ... etc
  
  duplicate_symbols:
    enabled: true
    forbidden_duplicates:
      - "policy_engine"
      - "governance_controller"
      # ... etc

kernel_change_policy:
  require_version_bump: true
  require_approval_label:
    - "kernel-change"
  authorized_approvers:
    - "security-team"
    - "architecture-team"
    - "maintainer"
```

## Dependency Direction

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEPENDENCY DIRECTION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Tier-0 (Constitution)                                         │
│       mahoun/core/governance_kernel/                         │
│       ├── __init__.py                                           │
│       └── kernel.py                                             │
│       (stdlib only, zero dependencies)                         │
│                                                                 │
│              ↓ (read-only inspection)                          │
│              │                                                  │
│  ┌─────────────────────┐                                      │
│  │ Tier-1 (Police)      │                                      │
│  │ mahoun/governance/  │                                      │
│  │ ├── kernel_guard.py │ ←─────────── Can import Tier-0      │
│  │ ├── architecture_guard.py                              │
│  │ └── api_guard.py                                         │
│  └─────────────────────┘                                      │
│              ↓                                                  │
│  ┌─────────────────────┐                                      │
│  │ Constitution Files   │                                      │
│  │ constitution/        │                                      │
│  │ ├── kernel.manifest.yaml ←── Source of Truth              │
│  │ ├── kernel.lock                                     │
│  │ ├── kernel_changes.yaml                             │
│  │ └── api.snapshot.json                               │
│  └─────────────────────┘                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

KEY PRINCIPLE: The kernel CANNOT depend on the police that protects it.
NO CIRCULAR DEPENDENCIES
```

## Tests

Test suite is in `tests/governance/`:

- `test_kernel_guard.py` - Kernel integrity tests
- `test_architecture_guard.py` - Architecture boundary tests
- `test_api_guard.py` - API protection tests

Run tests:
```bash
# Run all governance tests
pytest tests/governance/ -v

# Run specific test file
pytest tests/governance/test_kernel_guard.py -v

# Run with coverage
pytest tests/governance/ -v --cov=mahoun/governance
```

## Security Notes

### Fail-Closed Design
- All enforcement fails closed (exit code 1)
- If manifest is missing, exit 1
- If lock file is missing, exit 1
- If verification fails, exit 1
- Default to STRICT mode if not initialized

### No Bypass
- Governance tools CANNOT be disabled in CI
- Runtime bypass requires cryptographic authorization
- All checks are mandatory in protected branches

### Immutability
- Tier-0 files are protected by SHA256 hashes
- Kernel changes require explicit authorization
- Change records are immutable once created

## Quick Start

### For Developers

1. **Verify your changes:**
   ```bash
   make kernel-verify
   make architecture-verify
   ```

2. **If modifying Tier-0:**
   ```bash
   # Get authorization
   python -m mahoun.governance.kernel_guard --authorize-change \
       --version 1.1.0 \
       --reason "Your reason here" \
       --approved-by "security-team"
   
   # Update lock
   make kernel-update
   
   # Commit both code AND change record
   git add mahoun/core/governance_kernel/ constitution/
   git commit -m "Your message"
   ```

### For Maintainers

1. **Full verification:**
   ```bash
   make governance-verify
   ```

2. **Check attestation:**
   ```bash
   make attestation-verify
   ```

3. **View authorized changes:**
   ```bash
   cat constitution/kernel_changes.yaml
   ```

## Troubleshooting

### "Kernel integrity violation" error
**Cause:** Protected Tier-0 files have been modified without authorization

**Solution:**
1. If the change is intentional, authorize it:
   ```bash
   python -m mahoun.governance.kernel_guard --authorize-change \
       --version NEW_VERSION \
       --reason "Your reason" \
       --approved-by "your-name"
   ```
2. Update the lock:
   ```bash
   make kernel-update
   ```

### "Architecture violation" error
**Cause:** Forbidden import or layer violation detected

**Solution:**
1. Check which file has the violation
2. Remove the forbidden import or move the code to the correct tier
3. If the import should be allowed, update `constitution/kernel.manifest.yaml`

### "API drift detected" error
**Cause:** Public API has changed without updating the snapshot

**Solution:**
1. If the API change is intentional, update the snapshot:
   ```bash
   make api-update
   ```
2. If the API change is unintentional, revert the change

### "Manifest validation failed" error
**Cause:** `constitution/kernel.manifest.yaml` is missing required sections

**Solution:**
1. Check the error message for missing sections
2. Restore or fix the manifest file

## Documentation

- Full implementation report: `GOVERNANCE_IMPLEMENTATION_REPORT.md`
- Constitution manifest: `constitution/kernel.manifest.yaml`
- This file: `mahoun/governance/README.md`

## License

This code is part of the MAHOUN platform and follows the same licensing terms.

## Support

For questions or issues:
1. Check the implementation report
2. Review the manifest configuration
3. Run `make governance-verify` for full diagnostics
4. Open an issue with the error message
