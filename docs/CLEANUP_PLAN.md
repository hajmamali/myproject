# MAHOUN Repository Cleanup Plan

## Objective
Remove unrealistic marketing claims and organize repository structure for production readiness.

## Phase 1: Move Standalone Scripts to Proper Directories ✓ (In Progress)

### Files to Move from Root:
- [x] `alpha_test.sh` → `scripts/testing/`
- [x] `migrate_containers.sh` → `scripts/deployment/`
- [x] `orchestrator.py` → `scripts/orchestration/` (if used) OR delete if orphaned
- [x] `governance-kernel-contract-v1.yaml` → `docs/api/`
- [x] `mahoun_filelock.py` → Check if used, move to `mahoun/utils/` or delete

### Configuration Files (Keep in Root):
- ✓ `.env*` files
- ✓ `docker-compose*.yml` files
- ✓ `Dockerfile.*` files
- ✓ `Makefile*` files
- ✓ `pyproject.toml`, `requirements*.txt`
- ✓ Core manifest files

## Phase 2: Remove "Zero-Hallucination" Claims

### Critical Files to Update:

1. **API Layer:**
   - `api/routers/reasoning.py` - Remove "zero-hallucination guarantee" from docstrings
   - `api/main.py` - Tone down configuration validation comments

2. **Documentation:**
   - `.env.backend.example` - Update guard mode description
   - `docker-compose.backend.yml` - Remove "zero-hallucination" references
   - `Makefile.backend` - Update header

3. **Tests:**
   - Update test docstrings to use "hallucination reduction" instead of "zero-hallucination guarantee"
   - Files: `test_blockchain_ledger.py`, `test_guard_enforcement.py`, `test_semantic_contradiction.py`, etc.

4. **Examples/Demos:**
   - `demos/healthcare_compliance.py` - Change "Zero Hallucination" to "Evidence-Grounded Reasoning"
   - `examples/legal_aware_usage_examples.py` - Update claims

### Realistic Replacements:

| Old (Hype) | New (Realistic) |
|------------|-----------------|
| "zero-hallucination guarantee" | "evidence-grounded reasoning with hallucination reduction" |
| "100% groundedness guarantee" | "high-confidence evidence-linked reasoning" |
| "CRITICAL for zero-hallucination" | "CRITICAL for evidence integrity" |
| "Zero Hallucination" | "Evidence-Grounded" |

## Phase 3: Rename "Ultra/Quantum/Hyper" Files (Low Priority)

### Files with Marketing Names:
- `mahoun/graph/ultra_graph_builder.py` → `graph_builder.py` (canonical already exists?)
- `mahoun/graph/ultra_graph_query_service.py` → Check if duplicate
- `mahoun/rag/ultra_evaluation_system.py` → `rag_evaluation_system.py`
- `mahoun/rag/ultra_indexing_system.py` → `indexing_system.py`
- `mahoun/guardrails/ultra_nli_verifier.py` → `nli_verifier.py`
- `mahoun/reasoning/ultra_reasoning_service.py` → Check usage

**NOTE:** Only rename if they're not causing import errors. This is cosmetic and low priority.

## Phase 4: Update README.md with Realistic Description

### Current Claims to Revise:
- Tone down "proprietary audit-grade platform"
- Remove any "zero-hallucination" promises
- Be honest about:
  - LLM limitations
  - What governance actually provides (risk reduction, not elimination)
  - Appropriate use cases (regulated industries)

### New Structure:
1. What MAHOUN Actually Is
2. Core Capabilities (evidence-based, not absolute guarantees)
3. Architecture Highlights
4. Appropriate Use Cases
5. Known Limitations

## Phase 5: Organize docs/ Directory

```
docs/
├── api/              # API specs, contracts
├── architecture/     # Architecture docs
├── deployment/       # Deployment guides
├── reports/          # ✓ Already moved commit reports here
└── governance/       # Governance documentation
```

## Execution Order:
1. ✓ Move scripts from root (Phase 1)
2. Update zero-hallucination claims in critical files (Phase 2)
3. Update README.md with realistic description (Phase 4)
4. Rename ultra/quantum files (Phase 3) - Optional
5. Final verification and documentation update

## Success Criteria:
- [ ] No unrealistic "zero-hallucination guarantee" claims in user-facing docs
- [ ] Root directory contains only essential config/build files
- [ ] All scripts organized in proper subdirectories
- [ ] README.md provides honest, realistic project description
- [ ] No file naming that suggests capabilities beyond reality
