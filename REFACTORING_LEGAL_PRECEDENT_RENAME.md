# REFACTORING: LegalPrecedent.case_id → precedent_id

**Classification**: SEMANTIC CLARIFICATION / FIELD RENAME  
**Date**: 2025-01-09  
**Status**: IN PROGRESS  
**Parent**: Investigation 3 (Case Identity Semantic Audit)

---

## OBJECTIVE

Rename `LegalPrecedent.case_id` to `precedent_id` to eliminate semantic confusion with internal MahouN case identities.

**Rationale**:
- `LegalPrecedent.case_id` = External legal case reference (PUBLIC)
- `Ledger.case_id` = Internal MahouN case (PRIVATE)
- Same field name, different meanings → **Semantic conflict**

**Solution**: Rename to `precedent_id` for clarity.

---

## AFFECTED FILES

Based on Investigation 3 findings, the following files require updates:

### Core Definition
1. `mahoun/reasoning/knowledge_graph.py:57` — LegalPrecedent dataclass
2. `mahoun/reasoning/knowledge_graph.py:215` — Neo4j write query
3. `mahoun/reasoning/knowledge_graph.py:540-580` — add_precedent method

### Usage Sites
4. `demos/financial_aml.py:82` — Demo usage
5. `test_knowledge_graph_updated.py:21` — Test usage
6. `scripts/load_knowledge_graph_parallel.py:144,232` — Parallel loader

### Tests (Will be updated after main code)
- Various test files referencing LegalPrecedent

---

## REFACTORING PLAN

### Phase 1: Update Core Definition
- [x] `mahoun/reasoning/knowledge_graph.py` — LegalPrecedent dataclass
- [x] `mahoun/reasoning/knowledge_graph.py` — Neo4j MERGE query
- [x] `mahoun/reasoning/knowledge_graph.py` — add_precedent method

### Phase 2: Update Usage Sites
- [x] `mahoun/reasoning/reasoning_engine.py` — add_precedent wrapper
- [x] `demos/financial_aml.py`
- [x] `test_knowledge_graph_updated.py`
- [x] `scripts/load_knowledge_graph_parallel.py`

### Phase 3: Update Tests
- [x] `tests/governance/test_p0_hardening.py`
- [x] `tests/test_knowledge_graph_properties.py`
- [x] `tests/test_evidence_linked_verdict_system.py`
- [x] `tests/test_mega_stress.py`

### Phase 4: Verify
- [x] Import test: PASSED
- [x] Instance creation: PASSED
- [x] No remaining case_id references in LegalPrecedent

---

## IMPLEMENTATION

Starting with core definition...
