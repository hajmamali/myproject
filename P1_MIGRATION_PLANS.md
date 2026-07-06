# P1 Duplicate Consolidation — Migration Plans

**Generated:** /home/haji/Desktop/KingMahouN

این سند شامل migration plan برای top 20 duplicate definitions است.

---

## Migration Plan: Entity

**Canonical Location:** `mahoun/graph/builders/entity_extractor.py:51`
**Score:** 7.30/10.0

### Why This is Canonical:
- Location Score: 7.0/10 (domain)
- Completeness: 10.0/10 (LOC=56, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/nlp/ultra_persian_legal_nlp.py:75` (score=5.50)
- `mahoun/pipelines/ingestion/legal_ner.py:55` (score=5.30)
- `mahoun/graph/ultra_relation_extractor.py:54` (score=4.90)
- `mahoun/rag/evidence_enrichment.py:49` (score=4.30)
- `mahoun/ultra_systems/graph/ultra_relation_extractor.py:54` (score=4.10)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.graph.builders.entity_extractor import Entity
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ValidationResult

**Canonical Location:** `mahoun/core/fortress_validator.py:231`
**Score:** 7.70/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 10.0/10 (LOC=23, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/reasoning/neural_validation.py:53` (score=7.30)
- `mahoun/preproduction/models.py:73` (score=6.10)
- `mahoun/graph/ingestion/validators.py:21` (score=6.10)
- `mahoun/core/policy_deployment.py:139` (score=5.60)
- `mahoun/pipelines/ingestion/validation_quality.py:24` (score=5.30)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.fortress_validator import ValidationResult
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ReasoningMode

**Canonical Location:** `mahoun/reasoning/unified_reasoning_service.py:89`
**Score:** 6.10/10.0

### Why This is Canonical:
- Location Score: 7.0/10 (domain)
- Completeness: 6.0/10 (LOC=6, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/reasoning/reasoning_chain.py:50` (score=5.20)
- `mahoun/reasoning/symbolic_reasoner.py:48` (score=5.20)
- `mahoun/agents/contract_agent.py:40` (score=4.40)
- `mahoun/orchestrator/runtime_profile.py:34` (score=4.00)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.reasoning.unified_reasoning_service import ReasoningMode
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: HealthStatus

**Canonical Location:** `mahoun/core/protocols/ai_runtime.py:73`
**Score:** 7.10/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 8.0/10 (LOC=20, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/infrastructure/health/models.py:11` (score=5.70)
- `mahoun/infrastructure/health_checker.py:24` (score=4.80)
- `mahoun/ai/health.py:54` (score=4.00)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.protocols.ai_runtime import HealthStatus
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ModelNotFoundError

**Canonical Location:** `mahoun/core/exceptions.py:144`
**Score:** 6.00/10.0

### Why This is Canonical:
- Location Score: 9.0/10 (core)
- Completeness: 3.0/10 (LOC=2, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/protocols/ai_runtime.py:300` (score=5.60)
- `mahoun/core/exceptions_v2.py:237` (score=5.50)
- `mahoun/embeddings/local_service.py:60` (score=4.00)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.exceptions import ModelNotFoundError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ViolationSeverity

**Canonical Location:** `mahoun/core/fortress_validator.py:88`
**Score:** 6.50/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 6.0/10 (LOC=6, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/governance/violations.py:55` (score=4.90)
- `mahoun/core/governance_kernel/kernel.py:42` (score=3.10)
- `mahoun/agents/archive/dispute_agent_ultra.py:37` (score=2.50)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.fortress_validator import ViolationSeverity
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ValidationError

**Canonical Location:** `mahoun/core/config_validator.py:27`
**Score:** 6.50/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 6.0/10 (LOC=6, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/exceptions.py:163` (score=6.00)
- `mahoun/core/exceptions_v2.py:259` (score=5.50)
- `mahoun/ledger/validators.py:28` (score=4.00)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.config_validator import ValidationError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ReasoningStep

**Canonical Location:** `mahoun/reasoning/reasoning_recorder.py:99`
**Score:** 7.30/10.0

### Why This is Canonical:
- Location Score: 7.0/10 (domain)
- Completeness: 10.0/10 (LOC=28, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/models.py:83` (score=7.30)
- `mahoun/agents/contract_agent.py:221` (score=5.30)
- `mahoun/reasoning/ultra_reasoning_service.py:50` (score=4.60)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.reasoning.reasoning_recorder import ReasoningStep
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ReasoningResult

**Canonical Location:** `mahoun/core/models.py:105`
**Score:** 8.50/10.0

### Why This is Canonical:
- Location Score: 10.0/10 (core)
- Completeness: 10.0/10 (LOC=38, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/reasoning/symbolic_reasoner.py:95` (score=7.30)
- `mahoun/reasoning/reasoning_chain.py:70` (score=6.70)
- `mahoun/reasoning/ultra_reasoning_service.py:73` (score=5.20)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.models import ReasoningResult
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: UncertaintyEstimate

**Canonical Location:** `mahoun/core/protocols/advanced_protocols.py:28`
**Score:** 7.70/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 10.0/10 (LOC=44, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/models.py:151` (score=7.30)
- `mahoun/uncertainty/service.py:44` (score=6.10)
- `mahoun/uncertainty/gaussian_process.py:228` (score=6.10)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.protocols.advanced_protocols import UncertaintyEstimate
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: LedgerWriteError

**Canonical Location:** `mahoun/core/exceptions.py:77`
**Score:** 6.00/10.0

### Why This is Canonical:
- Location Score: 9.0/10 (core)
- Completeness: 3.0/10 (LOC=2, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/api/errors.py:153` (score=5.50)
- `mahoun/core/exceptions_v2.py:159` (score=5.50)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.exceptions import LedgerWriteError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: CircuitBreaker

**Canonical Location:** `mahoun/agents/base_agent.py:116`
**Score:** 6.50/10.0

### Why This is Canonical:
- Location Score: 5.0/10 (domain)
- Completeness: 10.0/10 (LOC=38, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/llm/router.py:250` (score=6.10)
- `mahoun/orchestrator/orchestrator.py:137` (score=6.10)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.agents.base_agent import CircuitBreaker
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: LLMRouterError

**Canonical Location:** `mahoun/core/exceptions.py:139`
**Score:** 6.00/10.0

### Why This is Canonical:
- Location Score: 9.0/10 (core)
- Completeness: 3.0/10 (LOC=2, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/exceptions_v2.py:231` (score=5.50)
- `mahoun/llm/router.py:1325` (score=4.00)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.exceptions import LLMRouterError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: SecurityBreachException

**Canonical Location:** `mahoun/core/fortress_validator.py:126`
**Score:** 7.70/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 10.0/10 (LOC=36, docstring=✓, types=✓)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/exceptions.py:306` (score=6.90)
- `mahoun/core/exceptions_v2.py:77` (score=6.40)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.fortress_validator import SecurityBreachException
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: SerializationError

**Canonical Location:** `mahoun/core/exceptions.py:58`
**Score:** 6.00/10.0

### Why This is Canonical:
- Location Score: 9.0/10 (core)
- Completeness: 3.0/10 (LOC=2, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/serialization.py:21` (score=5.60)
- `mahoun/core/exceptions_v2.py:343` (score=5.50)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.exceptions import SerializationError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ConfigurationError

**Canonical Location:** `mahoun/core/exceptions.py:120`
**Score:** 6.00/10.0

### Why This is Canonical:
- Location Score: 9.0/10 (core)
- Completeness: 3.0/10 (LOC=2, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/core/config_validator.py:36` (score=5.60)
- `mahoun/core/exceptions_v2.py:209` (score=5.50)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.exceptions import ConfigurationError
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: LegalDocType

**Canonical Location:** `mahoun/core/models.py:33`
**Score:** 7.30/10.0

### Why This is Canonical:
- Location Score: 10.0/10 (core)
- Completeness: 6.0/10 (LOC=9, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/graph/ingestion/document_classifier.py:204` (score=6.10)
- `mahoun/graph/ultra_legal_data_pipeline.py:43` (score=3.10)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.models import LegalDocType
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: QueryType

**Canonical Location:** `mahoun/core/protocols/legacy_protocols.py:17`
**Score:** 6.50/10.0

### Why This is Canonical:
- Location Score: 8.0/10 (core)
- Completeness: 6.0/10 (LOC=8, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/rag/query_router.py:26` (score=6.10)
- `mahoun/core/governance_kernel/kernel.py:29` (score=3.10)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.core.protocols.legacy_protocols import QueryType
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: RetrievalResult

**Canonical Location:** `mahoun/rag/hybrid_rag_service.py:39`
**Score:** 6.10/10.0

### Why This is Canonical:
- Location Score: 7.0/10 (domain)
- Completeness: 6.0/10 (LOC=7, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/pipelines/retrieve_rag.py:80` (score=5.30)
- `mahoun/flows/enhanced_rag.py:23` (score=4.90)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.rag.hybrid_rag_service import RetrievalResult
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---

## Migration Plan: ThreatLevel

**Canonical Location:** `mahoun/guardrails/adversarial_detector.py:71`
**Score:** 4.90/10.0

### Why This is Canonical:
- Location Score: 4.0/10 (domain)
- Completeness: 6.0/10 (LOC=6, docstring=✓, types=✗)
- Usage: 5.0/10
- Quality: 5.0/10

### Duplicates to Remove:

- `mahoun/security/prompt_defense.py:24` (score=4.90)
- `mahoun/security/behavioral_monitor.py:66` (score=4.90)

### Migration Steps:

1. Verify canonical implementation has all features from duplicates
2. Update all imports to point to canonical location:
   ```python
   from mahoun.guardrails.adversarial_detector import ThreatLevel
   ```
3. Add deprecation warnings to duplicate locations
4. Remove duplicates after migration period

---
