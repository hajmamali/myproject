# CRITICAL DI GOVERNANCE REMEDIATION — MANIFEST

**Objective:** Eliminate ALL runtime construction of external service clients (SentenceTransformer, OpenAI, CrossEncoder, Redis, QdrantClient) from business logic modules. Enforce fail-closed dependency injection with zero tolerance for hidden construction.

**Risk Level:** HIGH (P0 Governance Violation)
- Violates architectural boundaries
- Breaks testability
- Prevents deterministic execution
- Blocks composition control

**Scope:**
- **IN:** All files flagged by `test_di_bug_condition.py`
- **IN:** Production code only (mahoun/ and api/)
- **OUT:** Test fixtures, bootstrap/, composition root
- **OUT:** Steering docs, CI gates

**Touched Files:**
1. `mahoun/pipelines/query_rewriter.py` — OpenAI construction removal
2. `mahoun/rag/ultra_evaluation_system.py` — SentenceTransformer construction removal
3. `mahoun/graph/retriever/embedding_provider.py` — SentenceTransformer construction removal
4. `mahoun/graph/gnn/graph_builder.py` — SentenceTransformer construction removal
5. `mahoun/graph/gnn/semantic_chunker.py` — SentenceTransformer construction removal
6. `mahoun/graph/semantic_search.py` — SentenceTransformer construction removal
7. `mahoun/pipelines/retrieval_cache.py` — SentenceTransformer construction removal
8. `mahoun/pipelines/embed_index.py` — SentenceTransformer construction removal
9. `mahoun/rag/ultra_indexing_system.py` — Redis + Qdrant construction removal
10. `mahoun/graph/reranker/cross_encoder.py` — CrossEncoder construction removal

**Plan (Steps):**

### Phase 1: Module-Level Import Removal (query_rewriter.py)
1. Remove `from openai import OpenAI` module-level import (line ~14)
2. Move OpenAI import inside TYPE_CHECKING guard
3. Replace lazy fallback with fail-closed ValueError
4. Verify `client: Optional[OpenAI]` parameter exists
5. **Acceptance:** No module-level OpenAI import

### Phase 2: SentenceTransformer Sites (7 files)
6. **ultra_evaluation_system.py** — SemanticSimilarityCalculator:
   - Add `model: Optional[SentenceTransformer] = None` parameter
   - Replace lazy construction with fail-closed ValueError
7. **embedding_provider.py** — EmbeddingProvider:
   - Add `model: Optional[SentenceTransformer] = None` parameter
   - Replace lazy construction with fail-closed ValueError
8. **graph_builder.py** — LegalGraphBuilder:
   - Add `model: Optional[SentenceTransformer] = None` parameter
   - Replace lazy construction with fail-closed ValueError
9. **semantic_chunker.py** — SemanticChunker:
   - Add `embed_model_instance: Optional[SentenceTransformer] = None` parameter
   - Replace lazy construction with fail-closed ValueError
10. **semantic_search.py** — PersianSemanticSearch:
    - Add `model_instance: Optional[SentenceTransformer] = None` parameter
    - Replace lazy construction with fail-closed ValueError
11. **retrieval_cache.py** — SemanticCache:
    - Add `embed_model: Optional[SentenceTransformer] = None` parameter
    - Replace lazy construction with fail-closed ValueError
12. **embed_index.py** — AdvancedEmbedder:
    - Add `model: Optional[SentenceTransformer] = None` parameter
    - Replace lazy construction with fail-closed ValueError

### Phase 3: Infrastructure Sites (ultra_indexing_system.py)
13. **EmbeddingGenerator:**
    - Add `cache: Optional[redis.Redis] = None` parameter
    - Replace lazy Redis construction with fail-closed ValueError
14. **VectorIndex:**
    - Add `qdrant_client: Optional[QdrantClient] = None` parameter
    - Replace lazy Qdrant construction with fail-closed ValueError

### Phase 4: CrossEncoder Site
15. **cross_encoder.py:**
    - Add `model: Optional[CrossEncoder] = None` parameter
    - Replace eager construction with fail-closed ValueError

### Phase 5: Verification
16. Run `pytest tests/test_di_bug_condition.py -v`
17. Verify ALL tests PASS (zero violations)
18. Run global search for forbidden patterns
19. Verify zero construction sites outside composition root

**Acceptance Criteria:**
- [ ] `test_di_bug_condition.py::TestClassC_HiddenConstruction` — ALL PASS
- [ ] `test_di_bug_condition.py::TestIsBugConditionProperty` — ALL PASS (16/16)
- [ ] Global grep: `SentenceTransformer(` — zero hits outside bootstrap/
- [ ] Global grep: `OpenAI(` — zero hits outside bootstrap/
- [ ] Global grep: `redis.Redis(` — zero hits outside bootstrap/
- [ ] Global grep: `QdrantClient(` — zero hits outside bootstrap/
- [ ] Global grep: `CrossEncoder(` — zero hits outside bootstrap/
- [ ] No module-level `from openai import OpenAI` outside TYPE_CHECKING

**Tests to Run:**
```bash
# Activate venv
source /home/haji/Desktop/KingMahouN/venv/bin/activate

# Run DI bug condition test
pytest tests/test_di_bug_condition.py -v --tb=short

# Run DI refactor module tests
pytest tests/test_di_refactor_modules.py -v --tb=short

# Expected: ALL PASS, zero violations
```

**Rollback Plan:**
- Git revert commit
- All changes are additive (parameter injection)
- Zero breaking changes to existing callers
- Fail-closed errors are explicit and auditable

**Risks & Mitigations:**
- **Risk:** Existing code may not inject dependencies
  - **Mitigation:** Fail-closed ValueError with remediation guidance
- **Risk:** Backward compatibility break
  - **Mitigation:** All existing parameters preserved, new parameters are Optional with None default
- **Risk:** Tests may fail due to missing injection
  - **Mitigation:** Test fixtures already mock dependencies; no test changes needed

**Next Actions (Post-Remediation):**
1. Update bootstrap/runtime.py to inject all clients
2. Create LLM provider abstraction (remove direct OpenAI dependency)
3. Create embedding provider registry
4. Create reranker provider registry
5. Update CI gate to enforce zero construction violations
