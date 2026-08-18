# Phase 3 Coverage - Realistic Plan

## Current Status
- writer.py: ✅ 100% success (44/44 tests passing)
- verdict_engine.py: ⚠️ 4.5% success (3/67 tests)  
- operations.py: ⚠️ 65.5% success (59/87 tests)

## Problem Analysis

### verdict_engine.py Issues
- Tests are too complex - trying to test full pipeline end-to-end
- GraphNode construction errors (missing label/provenance) 
- Mock architecture doesn't match real code structure
- Engine uses in-memory graph logic, not direct node creation

### operations.py Issues  
- Many tests need real GovernanceContext (hard to mock)
- Tests assume features that don't exist (record_graph_operation_metric)
- Batch count assertions are wrong
- ProvenanceMetadata.create_synthetic() was missing (NOW FIXED ✅)

## Pragmatic Solution

### Option A: Accept Current State
- writer.py: ✅ 90%+ coverage achieved
- verdict_engine.py: Keep existing 12.8% (module is complex, needs integration tests)
- operations.py: Keep existing ~40-50% (governance makes unit testing hard)

**Justification:**
- Some modules are architectural - they orchestrate, not implement
- Integration tests better than bad unit tests
- Coverage % alone is not quality

### Option B: Write 5-10 Surgical Tests Per Module
- Focus on **untested branches** only
- Skip full pipeline tests
- Test individual helper methods in isolation

## Recommendation: Option B (Minimal Targeted Tests)

### verdict_engine.py - 5 Key Tests
1. `_filter_facts_for_ledger()` - privacy enforcement
2. `_calculate_confidence_score()` - scoring logic  
3. `_synthesize_final_verdict()` - verdict text generation
4. `VerdictDraft.finalize()` - ledger hash validation
5. `_resolve_provenance()` - provenance resolution logic

### operations.py - 5 Key Tests  
1. `_parse_law_article()` - article parsing regex
2. `_generate_verdict_id()` - ID generation logic
3. `GraphOperations.__init__()` - initialization
4. `create_document()` convenience function
5. Read helpers return types

## Time Estimate
- Minimal approach: 2-3 hours
- Current approach: 20+ hours (diminishing returns)

## Decision Point
What do you want to do?
1. ✅ Accept writer.py success, mark verdict_engine + operations as "needs integration tests"
2. 🎯 Write 5-10 surgical tests per module (realistic 60-70% coverage)
3. ⏸️ Stop Phase 3, move to Phase 4
