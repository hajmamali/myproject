# SNAPSHOT_2026-08-15_evidence-collection

---

## 1. Repository identity

Command:
```bash
git log -1 --format="%H %ai %s"
```

Output:

106256df81a2571a634b88077887b4a2364aa244 2026-08-11 16:49:52 +0330 feat: TIER 1 HARDENING COMPLETE - Thread-safe stats, STRICT default, NLI tests, audit logging

---

## 2. Python file count + LOC

Command:
```bash
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -not -path "./data/*" | wc -l
```

Output:

20595

Command:
```bash
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -not -path "./data/*" -exec cat {} \; 2>/dev/null | wc -l
```

Output:

8401437

---

## 3. Frontend TS/TSX LOC

Command:
```bash
find frontend/src -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l
```

Output:

69

Command:
```bash
find frontend/src -name "*.ts" -o -name "*.tsx" 2>/dev/null | xargs cat 2>/dev/null | wc -l
```

Output:

11747

---

## 4. Syntax

Command:
```bash
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -not -path "./data/*" 2>/dev/null | head -5 | xargs python3 -m py_compile 2>&1
```

Output:



---

## 5. Tests

Command:
```bash
python3 -m pytest --collect-only -q 2>&1 | tail -5
```

Output:

STRESS TEST SUITE COMPLETE
Exit Status: 3
======================================================================

============= 3326 tests collected, 63 errors in 63.19s (0:01:03) ==============

---

## 6. Governance

### 6-A. GovernanceContext

Command:
```bash
grep -rn "class GovernanceContext" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./tests/preproduction/test_security_validator.py:43:        "class GovernanceContext:\n    pass\n"
./tests/preproduction/test_security_validator.py:174:        canonical_output = f"{sample_workspace}/mahoun/core/governance/governance_context.py:1:class GovernanceContext:\n"
./tests/preproduction/test_security_validator.py:178:            if "class GovernanceContext" in args[0]:
./tests/preproduction/test_security_validator.py:200:            f"{sample_workspace}/mahoun/core/governance/governance_context.py:1:class GovernanceContext:\n"
./tests/preproduction/test_security_validator.py:201:            f"{sample_workspace}/mahoun/ledger/write_gate.py:50:class GovernanceContext:\n"
./api/middleware/governance_context.py:37:class GovernanceContextMiddleware(BaseHTTPMiddleware):
./.test_classification_backup/tests/preproduction/test_security_validator.py:43:        "class GovernanceContext:\n    pass\n"
./.test_classification_backup/tests/preproduction/test_security_validator.py:165:        canonical_output = f"{sample_workspace}/mahoun/core/governance/governance_context.py:1:class GovernanceContext:\n"
./.test_classification_backup/tests/preproduction/test_security_validator.py:169:            if "class GovernanceContext" in args[0]:
./.test_classification_backup/tests/preproduction/test_security_validator.py:190:            f"{sample_workspace}/mahoun/core/governance/governance_context.py:1:class GovernanceContext:\n"
./.test_classification_backup/tests/preproduction/test_security_validator.py:191:            f"{sample_workspace}/mahoun/ledger/write_gate.py:50:class GovernanceContext:\n"
./mahoun/core/governance/governance_context.py:55:class GovernanceContext:
./mahoun/core/governance/governance_context.py:227:class GovernanceContextManager:

---

### 6-B. MutationAuthorizationBoundary

Command:
```bash
grep -rn "class MutationAuthorizationBoundary" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./mahoun/core/governance/mutation_boundary.py:350:class MutationAuthorizationBoundary:
./.kilo/worktrees/gleaming-magician/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.kilo/worktrees/economic-isthmus/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.kilo/worktrees/tulip-education/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.kilo/worktrees/mud-koala/mahoun/core/governance_kernel/__init__.py:112:class MutationAuthorizationBoundary:
./.kilo/worktrees/mud-koala/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.kilo/worktrees/sun-wildebeest/mahoun/core/governance_kernel/__init__.py:61:class MutationAuthorizationBoundary:
./.kilo/worktrees/sun-wildebeest/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.kilo/worktrees/shimmering-piccolo/mahoun/core/governance_kernel/__init__.py:112:class MutationAuthorizationBoundary:
./.kilo/worktrees/shimmering-piccolo/mahoun/core/governance/mutation_boundary.py:283:class MutationAuthorizationBoundary:
./.worktrees/task/you-are-not-performing-a-git-merge-651ef3/mahoun/core/governance/mutation_boundary.py:307:class MutationAuthorizationBoundary:

---

### 6-C. GraphDatabase.driver

Command:
```bash
grep -rn "GraphDatabase.driver(" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./tests/preproduction/test_security_validator.py:49:        "from neo4j import GraphDatabase\ndriver = GraphDatabase.driver('bolt://localhost')\n"
./tests/preproduction/test_security_validator.py:143:        violation_output = f"{sample_workspace}/mahoun/pipelines/bad_code.py:42:driver = GraphDatabase.driver('bolt://localhost')\n"
./tests/preproduction/test_security_validator.py:159:        allowed_output = f"{sample_workspace}/mahoun/graph/neo4j/connection.py:10:driver = GraphDatabase.driver('bolt://localhost')\n"
./tests/preproduction/test_security_validator.py:377:        neo4j_violation = f"{sample_workspace}/mahoun/bad.py:1:GraphDatabase.driver('bolt://localhost')\n"
./tests/test_di_bug_condition.py:168:        mahoun/infrastructure/health/integrity_probe.py must NOT call GraphDatabase.driver(.
./tests/test_di_bug_condition.py:172:        pattern = "GraphDatabase.driver("
./tests/test_di_bug_condition.py:175:            f"VIOLATION in {path}: GraphDatabase.driver() outside allowlist at lines {lines}. "
./tests/test_di_bug_condition.py:182:        mahoun/infrastructure/health/checker.py must NOT call AsyncGraphDatabase.driver(.
./tests/test_di_bug_condition.py:186:        pattern = "AsyncGraphDatabase.driver("
./tests/test_di_bug_condition.py:189:            f"VIOLATION in {path}: AsyncGraphDatabase.driver() outside allowlist at lines {lines}. "
./tests/test_di_bug_condition.py:210:        Global scan: GraphDatabase.driver( must not appear outside the allowlist.
./tests/test_di_bug_condition.py:210:        Global scan: GraphDatabase.driver( must not appear outside the allowlist.
./tests/test_di_bug_condition.py:220:                if "GraphDatabase.driver(" in line:
./tests/test_di_bug_condition.py:223:            f"VIOLATION: GraphDatabase.driver() found outside allowlist:\n"
./tests/test_di_bug_condition.py:445:         "GraphDatabase.driver(",
./tests/test_di_bug_condition.py:449:         "AsyncGraphDatabase.driver(",
./tests/governance/test_api_database_firewall.py:29:driver = GraphDatabase.driver('bolt://localhost')
./tests/governance/test_api_database_firewall.py:43:        """Firewall MUST detect 'AsyncGraphDatabase.driver()'"""

---

### 6-D. AsyncGraphDatabase.driver

Command:
```bash
grep -rn "AsyncGraphDatabase.driver(" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./tests/test_di_bug_condition.py:182:        mahoun/infrastructure/health/checker.py must NOT call AsyncGraphDatabase.driver(.
./tests/test_di_bug_condition.py:186:        pattern = "AsyncGraphDatabase.driver("
./tests/test_di_bug_condition.py:189:            f"VIOLATION in {path}: AsyncGraphDatabase.driver() outside allowlist at lines {lines}. "
./tests/test_di_bug_condition.py:230:        Global scan: AsyncGraphDatabase.driver( must not appear outside the allowlist.
./tests/test_di_bug_condition.py:240:                if "AsyncGraphDatabase.driver(" in line:
./tests/test_di_bug_condition.py:243:            f"VIOLATION: AsyncGraphDatabase.driver() found outside allowlist:\n"
./tests/test_di_bug_condition.py:449:         "AsyncGraphDatabase.driver(",
./tests/governance/test_api_database_firewall.py:43:        """Firewall MUST detect 'AsyncGraphDatabase.driver()'"""
./tests/governance/test_api_database_firewall.py:48:    driver = AsyncGraphDatabase.driver('bolt://localhost', auth=('neo4j', 'pass'))
./tests/governance/test_api_database_firewall.py:57:        assert len(violations) >= 1, "Must detect AsyncGraphDatabase.driver()"
./tests/governance/test_api_database_firewall.py:217:            if 'AsyncGraphDatabase.driver(' in line:
./tests/governance/test_api_database_firewall.py:219:                    f"Line {i}: Direct AsyncGraphDatabase.driver() detected: {line.strip()}\n"
./tests/governance/test_api_database_firewall.py:306:            assert 'AsyncGraphDatabase.driver(' not in source, \
./tests/governance/test_api_database_firewall.py:320:        # Search for AsyncGraphDatabase.driver() calls outside canonical location
./tests/governance/test_api_database_firewall.py:343:                if 'AsyncGraphDatabase.driver(' in source:
./tests/governance/test_api_database_firewall.py:344:                    violations.append((str(py_file.relative_to(workspace)), 'AsyncGraphDatabase.driver()'))
./tests/governance/test_unified_health_governance.py:689:        """``AGENTS.md`` 1-A: exactly one ``AsyncGraphDatabase.driver()``
./tests/governance/test_unified_health_governance.py:722:            f"AGENTS.md 1-A violation: AsyncGraphDatabase.driver() "
./tests/test_di_refactor_modules.py:201:        assert 'AsyncGraphDatabase.driver(' not in source, "Must NOT create AsyncGraphDatabase.driver"
./tests/test_di_refactor_modules.py:344:        assert 'AsyncGraphDatabase.driver(' not in source, "Must NOT create AsyncGraphDatabase.driver"

---

### 6-E. authorized ContextVar

Command:
```bash
grep -rn "_authorized_write_ctx" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./tests/test_authorization_state_singleton.py:5:Enforces Invariant: There exists exactly ONE _authorized_write_ctx object.
./tests/test_authorization_state_singleton.py:6:kernel._authorized_write_ctx is mutation_boundary._authorized_write_ctx is True.
./tests/test_authorization_state_singleton.py:19:    from mahoun.core.governance.authorization_state import _authorized_write_ctx as canonical
./tests/test_authorization_state_singleton.py:23:    assert kernel._authorized_write_ctx is canonical, (
./tests/test_authorization_state_singleton.py:24:        "kernel._authorized_write_ctx is NOT the canonical ContextVar. "
./tests/test_authorization_state_singleton.py:27:    assert mutation_boundary._authorized_write_ctx is canonical, (
./tests/test_authorization_state_singleton.py:28:        "mutation_boundary._authorized_write_ctx is NOT the canonical ContextVar. "
./tests/test_authorization_state_singleton.py:31:    assert kernel._authorized_write_ctx is mutation_boundary._authorized_write_ctx, (
./tests/stress/test_kernel_ownership.py:74:            _authorized_write_ctx,
./tests/preproduction/test_security_validator.py:46:        "_authorized_write_ctx = ContextVar('auth')\n"
./tests/preproduction/test_security_validator.py:180:            elif "_authorized_write_ctx" in args[0]:
./tests/preproduction/test_security_validator.py:181:                authz_output = f"{sample_workspace}/mahoun/core/governance/authorization_state.py:1:_authorized_write_ctx = ContextVar('auth')\n"
./tests/preproduction/test_security_validator.py:192:        assert len(info_findings) >= 2  # One for GovernanceContext, one for _authorized_write_ctx
./tests/preproduction/test_security_validator.py:417:                elif "_authorized_write_ctx" in command:
./tests/preproduction/test_security_validator.py:420:                        stdout=f"{sample_workspace}/mahoun/core/governance/authorization_state.py:1:_authorized_write_ctx = ContextVar('auth')\n"
./tests/test_authorization_context_canonical.py:2:Identity regression test for the single _authorized_write_ctx ContextVar.
./tests/test_authorization_context_canonical.py:9:local `_authorized_write_ctx` redefinition in `kernel.py` or
./tests/test_authorization_context_canonical.py:26:    from mahoun.core.governance_kernel.kernel import _authorized_write_ctx as k
./tests/test_authorization_context_canonical.py:27:    from mahoun.core.governance.mutation_boundary import _authorized_write_ctx as m
./tests/test_authorization_context_canonical.py:28:    from mahoun.core.governance.authorization_state import _authorized_write_ctx as s

---

### 6-F. GovernanceContextMiddleware

Command:
```bash
grep -rn "GovernanceContextMiddleware" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./tests/governance/test_api_governance_middleware_wiring.py:2:Tests for GovernanceContextMiddleware API Wiring
./tests/governance/test_api_governance_middleware_wiring.py:6:Purpose: Verify GovernanceContextMiddleware is registered on the real FastAPI
./tests/governance/test_api_governance_middleware_wiring.py:15:from api.middleware.governance_context import GovernanceContextMiddleware, get_governance_context
./tests/governance/test_api_governance_middleware_wiring.py:25:class TestGovernanceContextMiddlewareWiring:
./tests/governance/test_api_governance_middleware_wiring.py:26:    """Verify GovernanceContextMiddleware wiring on the real FastAPI app."""
./tests/governance/test_api_governance_middleware_wiring.py:29:        """Verify GovernanceContextMiddleware exists in app.user_middleware or middleware stack."""
./tests/governance/test_api_governance_middleware_wiring.py:31:        assert GovernanceContextMiddleware in middleware_classes, (
./tests/governance/test_api_governance_middleware_wiring.py:32:            "GovernanceContextMiddleware is NOT registered in api.main app.user_middleware!"
./tests/governance/test_api_governance_middleware_wiring.py:38:        populated by GovernanceContextMiddleware, and do NOT fail with
./tests/integration/test_governed_rag_integration.py:6:- GovernanceContextMiddleware 
./tests/integration/test_governed_rag_integration.py:22:from api.middleware.governance_context import GovernanceContextMiddleware, get_governance_context
./tests/integration/test_governed_rag_integration.py:39:    app.add_middleware(GovernanceContextMiddleware, execution_mode="STRICT")
./tests/integration/test_governed_rag_integration.py:81:class TestGovernanceContextMiddleware:
./tests/integration/test_governed_rag_integration.py:118:        from api.middleware.governance_context import GovernanceContextMiddleware
./tests/integration/test_governed_rag_integration.py:120:        middleware = GovernanceContextMiddleware(None)
./tests/integration/test_governed_rag_integration.py:195:        from api.middleware.governance_context import GovernanceContextMiddleware
./tests/integration/test_governed_rag_integration.py:197:        middleware = GovernanceContextMiddleware(None)
./tests/integration/test_phase5_simple.py:16:from api.middleware.governance_context import GovernanceContextMiddleware, get_governance_context
./tests/integration/test_phase5_simple.py:25:    middleware = GovernanceContextMiddleware(None)
./tests/integration/test_phase5_simple.py:35:    middleware = GovernanceContextMiddleware(None)

---

## 7. Core boundaries

### 7-A. core imports

Command:
```bash
find mahoun/core -name "*.py" -not -path "./.git/*" | head -30 2>/dev/null
```

Output:

mahoun/core/dependency_validator.py
mahoun/core/singleton.py
mahoun/core/policy_deployment.py
mahoun/core/rollback_orchestrator.py
mahoun/core/settings.py
mahoun/core/secrets.py
mahoun/core/query_executor.py
mahoun/core/health_cache.py
mahoun/core/governance_lock.py
mahoun/core/protocols.py
mahoun/core/unified_governance.py
mahoun/core/governance_kernel/kernel.py
mahoun/core/governance_kernel/__init__.py
mahoun/core/governance_kernel/authorization_state.py
mahoun/core/environment.py
mahoun/core/policy_resolver.py
mahoun/core/health_checker.py
mahoun/core/fortress_validator.py
mahoun/core/config.py
mahoun/core/exceptions.py
mahoun/core/models/reasoning.py
mahoun/core/models/__init__.py
mahoun/core/models/project_model/manager.py
mahoun/core/models/project_model/detectors/registry.py
mahoun/core/models/project_model/detectors/engine.py
mahoun/core/models/project_model/detectors/duplicate_detector.py
mahoun/core/models/project_model/detectors/boundary_detector.py
mahoun/core/models/project_model/detectors/orphaned_detector.py
mahoun/core/models/project_model/detectors/base.py
mahoun/core/models/project_model/index.py

---

### 7-B. core_manifest.yaml

Command:
```bash
wc -l core_manifest.yaml 2>&1
```

Output:

582 core_manifest.yaml

---

### 7-C. non_core_manifest.yaml

Command:
```bash
wc -l non_core_manifest.yaml 2>&1
```

Output:

683 non_core_manifest.yaml

---

## 8. Duplication

### 8-A. models.py / models/

Command:
```bash
find . -name "models.py" -not -path "./.git/*" -not -path "./venv/*" -not -path "./data/*" 2>/dev/null | head -20
```

Output:

./mahoun/infrastructure/health/models.py
./mahoun/infrastructure/models.py
./mahoun/core/models.py
./mahoun/preproduction/models.py
./mahoun/audit/models.py
./mahoun/ai/models.py
./mahoun/graph/batch/models.py
./mahoun/graph/neo4j/models.py
./mahoun/ledger/models.py

---

### 8-B. models/ directories

Command:
```bash
find . -type d -name "models" -not -path "./.git/*" -not -path "./venv/*" -not -path "./data/*" 2>/dev/null | head -20
```

Output:

./api/models
./mahoun/core/models
./scripts/models

---

### 8-C. LegalDocument

Command:
```bash
grep -rn "class LegalDocument" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./mahoun/core/models/reasoning.py:36:class LegalDocument(BaseModel):
./mahoun/core/models.py:45:class LegalDocument(BaseModel):
./mahoun/schemas/legal_aware_schema.py:45:class LegalDocumentType(str, Enum):
./mahoun/schemas/contracts/core_contracts.py:83:class LegalDocumentInput(BaseModel):
./mahoun/schemas/contracts/core_contracts.py:112:class LegalDocumentOutput(BaseModel):
./mahoun/graph/ingestion/parsers.py:428:class LegalDocumentParser(BaseParser):
./mahoun/graph/ingestion/validators.py:249:class LegalDocumentValidator(BaseValidator):

---

### 8-D. LegalEntity

Command:
```bash
grep -rn "class LegalEntity" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./mahoun/nlp/ultra_persian_legal_nlp.py:263:class LegalEntityExtractor:
./mahoun/core/models/reasoning.py:58:class LegalEntity(BaseModel):
./mahoun/core/models/entity.py:1091:class LegalEntity(Entity):
./mahoun/core/models.py:67:class LegalEntity(BaseModel):
./mahoun/schemas/contracts/core_contracts.py:128:class LegalEntityInput(BaseModel):
./mahoun/schemas/contracts/core_contracts.py:157:class LegalEntityOutput(BaseModel):
./mahoun/finetuning/data_augmentation.py:59:class LegalEntityExtractor:

---

### 8-E. ReasoningStep

Command:
```bash
grep -rn "class ReasoningStep" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./api/models/core.py:308:class ReasoningStep(BaseModel):
./mahoun/core/models/reasoning.py:74:class ReasoningStep(BaseModel):
./mahoun/core/models.py:83:class ReasoningStep(BaseModel):
./mahoun/reasoning/reasoning_recorder_ultra.py:77:class ReasoningStepRecord:
./mahoun/reasoning/ultra_reasoning_service.py:50:class ReasoningStep:
./mahoun/reasoning/reasoning_recorder.py:26:class ReasoningStep:
./mahoun/agents/contract_agent.py:221:class ReasoningStep:
./mahoun/schemas/contracts/reasoning_contracts.py:308:class ReasoningStepContract(BaseModel):

---

### 8-F. ReasoningResult

Command:
```bash
grep -rn "class ReasoningResult" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/"
```

Output:

./mahoun/core/models/reasoning.py:96:class ReasoningResult(BaseModel):
./mahoun/core/models.py:105:class ReasoningResult(BaseModel):
./mahoun/reasoning/ultra_reasoning_service.py:73:class ReasoningResult:
./mahoun/reasoning/reasoning_chain.py:101:class ReasoningResult:
./mahoun/reasoning/symbolic_reasoner.py:95:class ReasoningResult:
./mahoun/schemas/contracts/core_contracts.py:172:class ReasoningResultContract(BaseModel):

---

## 9. RAG / NLI / OCR wiring

### 9-A. retrieval_provenance / RAGEvidenceNode

Command:
```bash
grep -rn "retrieval_provenance" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | head -20
```

Output:

./tests/ledger/test_rag_provenance_gaps_1_3.py:30:    def test_retrieval_provenance_field_exists(self):
./tests/ledger/test_rag_provenance_gaps_1_3.py:31:        """EvidencePackage should have retrieval_provenance field"""
./tests/ledger/test_rag_provenance_gaps_1_3.py:39:        # Should have retrieval_provenance field (defaults to empty list)
./tests/ledger/test_rag_provenance_gaps_1_3.py:40:        assert hasattr(package, "retrieval_provenance")
./tests/ledger/test_rag_provenance_gaps_1_3.py:41:        assert package.retrieval_provenance == []
./tests/ledger/test_rag_provenance_gaps_1_3.py:57:    def test_retrieval_provenance_can_be_provided(self):
./tests/ledger/test_rag_provenance_gaps_1_3.py:58:        """EvidencePackage should accept retrieval_provenance"""
./tests/ledger/test_rag_provenance_gaps_1_3.py:75:            retrieval_provenance=rag_provenance,
./tests/ledger/test_rag_provenance_gaps_1_3.py:78:        assert package.retrieval_provenance == rag_provenance
./tests/ledger/test_rag_provenance_gaps_1_3.py:82:        """Old code without retrieval_provenance should still work"""
./tests/ledger/test_rag_provenance_gaps_1_3.py:89:            # Note: NOT providing retrieval_provenance
./tests/ledger/test_rag_provenance_gaps_1_3.py:93:        assert package.retrieval_provenance == []
./tests/ledger/test_rag_provenance_gaps_1_3.py:99:    """Tests for retrieval_provenance validation logic"""
./tests/ledger/test_rag_provenance_gaps_1_3.py:102:    def test_valid_retrieval_provenance_accepted(self):
./tests/ledger/test_rag_provenance_gaps_1_3.py:103:        """Valid retrieval_provenance should pass validation"""
./tests/ledger/test_rag_provenance_gaps_1_3.py:121:            retrieval_provenance=rag_provenance,
./tests/ledger/test_rag_provenance_gaps_1_3.py:145:            retrieval_provenance=rag_provenance,
./tests/ledger/test_rag_provenance_gaps_1_3.py:154:    def test_empty_retrieval_provenance_accepted(self):
./tests/ledger/test_rag_provenance_gaps_1_3.py:155:        """Empty retrieval_provenance list should be valid"""
./tests/ledger/test_rag_provenance_gaps_1_3

---

Command:
```bash
grep -rn "RAGEvidenceNode" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | head -20
```

Output:

./tests/ai_runtime/test_governance_compliance_d24.py:339:        # AIRuntimeManager -> RAGEvidenceNode -> ProvenanceMetadata -> EvidenceLedger
./tests/reasoning/test_rag_provenance_integration.py:7:- RAGEvidenceNode (evidence wrapping)
./tests/reasoning/test_rag_provenance_integration.py:97:    # Test RAGEvidenceNode creation with all fields.
./tests/reasoning/test_rag_provenance_integration.py:99:    Verifies that RAGEvidenceNode can be created with proper validation.
./tests/reasoning/test_rag_provenance_integration.py:101:    from mahoun.reasoning.rag_evidence import RAGEvidenceNode, RAGSource, SourceAuthority
./tests/reasoning/test_rag_provenance_integration.py:103:    node = RAGEvidenceNode(
./tests/reasoning/test_rag_provenance_integration.py:138:    from mahoun.reasoning.rag_evidence import RAGEvidenceNode, RAGSource, SourceAuthority
./tests/reasoning/test_rag_provenance_integration.py:144:        0: RAGEvidenceNode(
./tests/reasoning/test_rag_provenance_integration.py:154:        1: RAGEvidenceNode(
./tests/test_rag_evidence.py:2:Tests for RAGEvidenceNode — audit-grade RAG provenance wrapper.
./tests/test_rag_evidence.py:16:    RAGEvidenceNode,
./tests/test_rag_evidence.py:57:        node = RAGEvidenceNode(**_make_kwargs())
./tests/test_rag_evidence.py:67:        n1 = RAGEvidenceNode(**_make_kwargs())
./tests/test_rag_evidence.py:68:        n2 = RAGEvidenceNode(**_make_kwargs())
./tests/test_rag_evidence.py:74:        node = RAGEvidenceNode(**_make_kwargs())

---

### 9-B. NLI verifier usage

Command:
```bash
grep -rn "NLI.*verify\|verify.*NLI\|nli_verifier\|NLIVerifier" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | head -30
```

Output:

./tests/regression/test_nli_verification_hardcore.py:42:            # from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier as NLIVerifier
./tests/regression/test_nli_verification_hardcore.py:43:            self._nli_verifier = NLIVerifier(threshold=self.config.nli_threshold)
./tests/regression/test_nli_verification_hardcore.py:46:            from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier
./tests/regression/test_nli_verification_hardcore.py:47:            self._nli_verifier = UltraNLIVerifier(threshold=self.config.nli_threshold)
./tests/regression/test_nli_verification_hardcore.py:69:        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in init_section, \
./tests/regression/test_nli_verification_hardcore.py:70:            "Active UltraNLIVerifier import not found in initialization"
./tests/regression/test_nli_verification_hardcore.py:77:            if stripped.startswith("from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier"):
./tests/regression/test_nli_verification_hardcore.py:82:            "UltraNLIVerifier import line is commented out or missing"
./tests/regression/test_nli_verification_hardcore.py:84:        # The instantiation MUST use UltraNLIVerifier (not NLIVerifier)
./tests/regression/test_nli_verification_hardcore.py:85:        assert "UltraNLIVerifier(threshold=" in init_section, \
./tests/regression/test_nli_verification_hardcore.py:86:            "Instantiation with UltraNLIVerifier not found"
./tests/regression/test_nli_verification_hardcore.py:88:        # The instantiation MUST NOT use NLIVerifier (the old broken name) without Ultra prefix
./tests/regression/test_nli_verification_hardcore.py:89:        # Check that we don't have standalone NLIVerifier (which would be the broken import)
./tests/regression/test_nli_verification_hardcore.py:90:        assert "self._nli_verifier = NLIVerifier(" not in source, \
./tests/regression/test_nli_verification_hardcore.py:93:            if line.startswith("self._nli_verifier = NLIVerifier("):
./tests/regression/test_nli_verification_hardcore.py:94:        assert False, f"Found broken NLIVerifier instantiation: {line}"
./tests/regression/test_nli_verification_hardcore.py:102:            NameError: name 'NLIVerifier' is not defined
./tests/regression/test_nli_verification_hardcore.py:115:    These tests verify that the NLI verification code is not just present somewhere,
./tests/regression/test_nli_verification_hardcore.py:140:        nli_pos = content.find("UltraNLIVerifier")
./tests/regression/test_nli_verification_hardcore.py:145:        assert nli_pos > 0, "UltraNLIVerifier not found"
./tests/regression/test_nli_verification_hardcore.py:211:        nli_section_start = content.find("nli_result: UltraNLIResult = nli_verifier.verify")
./tests/regression/test_nli_verification_hardcore.py:294:        Verify that if UltraNLIVerifier cannot be imported, production mode raises ImportError.
./tests/regression/test_nli_verification_hardcore.py:323:                "Production doesn't raise ImportError when UltraNLIVerifier is missing"
./tests/regression/test_round7_hardcore.py:56:class TestNLIVerifierHardCore:
./tests/regression/test_round7_hardcore.py:65:        CRITICAL: Verify reasoning_chain.py has ACTIVE import of UltraNLIVerifier.
./tests/regression/test_round7_hardcore.py:72:        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in source
./tests/regression/test_round7_hardcore.py:75:        assert "# from mahoun.guardrails.ultra_nli_verifier import" not in source
./tests/regression/test_round7_hardcore.py:78:        assert "self._nli_verifier = UltraNLIVerifier" in source
./tests/regression/test_round7_hardcore.py:89:        # Must import UltraNLIVerifier
./tests/regression/test_round7_hardcore.py:90:        assert "from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier" in source

---

### 9-C. OCR usage

Command:
```bash
grep -rn "OCR\|paddleocr\|PaddleOCR" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | grep -v "test" | head -30
```

Output:

./api/routers/mahoun.py:205:    Supports: PDF, DOCX, TXT, Images (with OCR)
./mahoun/infrastructure/config.py:56:class OCRSettings(BaseSettings):
./mahoun/infrastructure/config.py:57:    """OCR configuration."""
./mahoun/infrastructure/config.py:59:        default="paddle", env="MAHOUN_OCR_DEFAULT_ENGINE"
./mahoun/infrastructure/config.py:61:    languages: str = Field(default="fa", env="MAHOUN_OCR_LANGUAGES")
./mahoun/infrastructure/config.py:63:        default=True, env="MAHOUN_OCR_USE_POST_PROCESSING"
./mahoun/infrastructure/config.py:66:    model_config = SettingsConfigDict(env_prefix="MAHOUN_OCR_")
./mahoun/infrastructure/config.py:113:    ocr: OCRSettings = OCRSettings()
./mahoun/infrastructure/config.py:152:def get_ocr_settings() -> OCRSettings:
./mahoun/core/exceptions.py:170:    """Security constraint violation (e.g., OCR confidence too low)."""
./mahoun/switchboard.py:176:        "ocr_handler", base_path="mahoun.pipelines.ingestion.ocr_handler.OCRHandler"
./mahoun/pipelines/ingestion/ocr_post_processor.py:2:OCR Post-Processor for MAHOUN Platform
./mahoun/pipelines/ingestion/ocr_post_processor.py:5:Enterprise-grade post-processing pipeline for OCR output with:
./mahoun/pipelines/ingestion/ocr_post_processor.py:12:This module improves OCR accuracy by 10-20% through intelligent correction
./mahoun/pipelines/ingestion/ocr_post_processor.py:63:    """Configuration for OCR post-processing"""
./mahoun/pipelines/ingestion/ocr_post_processor.py:262:    Corrects common OCR errors in legal terminology.
./mahoun/pipelines/ingestion/ocr_post_processor.py:349:    Validates OCR output quality using statistical analysis.
./mahoun/pipelines/ingestion/ocr_post_processor.py:353:    - High non-text character ratio (OCR artifacts)
./mahoun/pipelines/ingestion/ocr_post_processor.py:446:class OCRPostProcessor:
./mahoun/pipelines/ingestion/ocr_post_processor.py:448:    Enterprise-grade OCR post-processor.
./mahoun/pipelines/ingestion/ocr_post_processor.py:470:        logger.info("OCRPostProcessor initialized")
./mahoun/pipelines/ingestion/ocr_post_processor.py:477:        if os.getenv('OCR_MIN_LINE_CONFIDENCE'):
./mahoun/pipelines/ingestion/ocr_post_processor.py:478:            self.config.min_line_confidence = float(os.getenv('OCR_MIN_LINE_CONFIDENCE'))
./mahoun/pipelines/ingestion/ocr_post_processor.py:481:        if os.getenv('OCR_NORMALIZE_PERSIAN'):
./mahoun/pipelines/ingestion/ocr_post_processor.py:482:            self.config.normalize_persian = os.getenv('OCR_NORMALIZE_PERSIAN').lower() == 'true'
./mahoun/pipelines/ingestion/ocr_post_processor.py:485:        if os.getenv('OCR_ENABLE_LEGAL_CORRECTION'):
./mahoun/pipelines/ingestion/ocr_post_processor.py:486:            self.config.enable_legal_correction = os.getenv('OCR_ENABLE_LEGAL_CORRECTION').lower() == 'true'
./mahoun/pipelines/ingestion/ocr_post_processor.py:489:        if os.getenv('OCR_ENABLE_STATISTICAL_VALIDATION'):
./mahoun/pipelines/ingestion/ocr_post_processor.py:490:            self.config.enable_statistical_validation = os.getenv('OCR_ENABLE_STATISTICAL_VALIDATION').lower() == 'true'
./mahoun/pipelines/ingestion/ocr_post_processor.py:499:        Process OCR output with corrections and validation.

---

## 10. Determinism

Command:
```bash
grep -rn "uuid4()" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | grep -v "test" | head -30
```

Output:

./api/routers/training_datasets.py:269:            doc_id = f"doc_{uuid4().hex[:8]}"
./api/routers/training_datasets.py:362:            doc_id = f"doc_{uuid4().hex[:8]}"
./api/routers/training_datasets.py:363:        job_id = f"job_{uuid4().hex[:12]}"
./api/routers/reasoning.py:411:            user_case_id = request.case_id or str(uuid.uuid4())
./api/routers/reasoning.py:459:        verdict_id = verdict.metadata.get("verdict_id", str(uuid.uuid4()))
./api/routers/finetuning.py:205:    job_id = str(uuid.uuid4())
./api/routers/ingest.py:114:        "doc_id": str(uuid.uuid4()),
./api/routers/ingest.py:158:    record_id = str(uuid.uuid4())  # Primary key for the database record
./api/routers/ingest.py:159:    doc_id = str(uuid.uuid4())  # Document identifier
./api/routers/mahoun.py:216:        file_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"
./api/routers/mahoun.py:358:        claim_id = str(uuid.uuid4())
./api/routers/mahoun.py:470:        report_id = str(uuid.uuid4())
./api/routers/mahoun.py:531:        report_id = str(uuid.uuid4())
./api/routers/chat.py:79:            conversation_id = str(uuid.uuid4())
./mahoun/llm/provider_protocol.py:208:        correlation_id = correlation_id or f"openai-{uuid.uuid4().hex[:8]}"
./mahoun/concurrency/distributed_lock.py:90:        self.lock_id = str(uuid.uuid4())
./mahoun/infrastructure/workers/outbox_worker.py:121:        correlation_id = str(event['correlation_id']) if event['correlation_id'] else f"outbox-{uuid.uuid4()}"
./mahoun/core/policy_deployment.py:502:        deployment_id = f"deploy-{uuid4().hex[:12]}"
./mahoun/core/rollback_orchestrator.py:434:            snapshot_id=f"snap-{uuid4().hex[:12]}"
./mahoun/core/rollback_orchestrator.py:468:        rollback_id = f"rollback-{uuid4().hex[:12]}"
./mahoun/core/governance_kernel/kernel.py:185:                validation_id=str(uuid.uuid4()),
./mahoun/core/governance_kernel/kernel.py:196:        validation_id=str(uuid.uuid4()),
./mahoun/core/governance_kernel/kernel.py:206:            validation_id=str(uuid.uuid4()),
./mahoun/core/fortress_validator.py:690:        return f"fortress-{uuid.uuid4().hex[:12]}"
./mahoun/core/governance/governance_context.py:166:        child_id = child_correlation_id or f"{self.correlation_id}-{uuid.uuid4().hex[:8]}"
./mahoun/core/governance/governance_context.py:169:            context_id=f"{self.context_id}-child-{uuid.uuid4().hex[:8]}",
./mahoun/core/governance/governance_context.py:334:        ctx_id = f"ctx-{uuid.uuid4().hex[:16]}"
./mahoun/core/governance/governance_context.py:335:        corr_id = correlation_id or f"req-{uuid.uuid4().hex[:16]}"
./mahoun/services/legal_migration_service.py:157:        migration_id = str(uuid.uuid4())
./mahoun/services/legal_migration_service.py:1399:                "audit_id": str(uuid.uuid4()),

---

## 11. Ledger

### 11-A. Ledger classes

Command:
```bash
grep -rn "class.*Ledger\|class EvidenceLedgerWriter\|class ImmutableLedger" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | grep -v "test"
```

Output:

./api/routers/reasoning.py:185:class LedgerQueryRequest(BaseModel):
./api/routers/reasoning.py:195:class LedgerQueryResponse(ProofCarryingResponse):
./mahoun/bootstrap/executors/critical_infrastructure.py:301:class ImmutableLedgerExecutor(BootstrapPhaseExecutor):
./mahoun/api/errors.py:153:class LedgerWriteError(MAHOUNAPIError):
./mahoun/core/config.py:105:class LedgerBackend(str, Enum):
./mahoun/core/exceptions.py:63:class LedgerError(MahounError):
./mahoun/core/exceptions.py:68:class LedgerWriteError(LedgerError):
./mahoun/core/exceptions.py:73:class LedgerIntegrityError(LedgerError):
./mahoun/reasoning/ledger_commit_service.py:41:class LedgerCommitResult:
./mahoun/reasoning/ledger_commit_service.py:59:class LedgerCommitService:
./mahoun/contracts/verdict_execution.py:465:class PendingLedgerCommit:
./mahoun/contracts/__init__.py:65:    >>> class LedgerIntegrityContract(GovernanceContract):
./mahoun/schemas/contracts/ledger_contracts.py:30:class LedgerEntryContract(BaseModel):
./mahoun/schemas/contracts/ledger_contracts.py:144:class WriteLedgerInput(BaseModel):
./mahoun/schemas/contracts/ledger_contracts.py:158:class WriteLedgerOutput(BaseModel):
./mahoun/schemas/contracts/ledger_contracts.py:219:class WriteLedgerError(BaseModel):
./mahoun/schemas/contracts/ledger_contracts.py:378:class LedgerBackendConfig(BaseModel):
./mahoun/security/signing.py:325:class LedgerSigning:
./mahoun/ledger/write_gate.py:106:class LedgerWriteGate:
./mahoun/ledger/write_gate.py:539:class LedgerWriteContext:
./mahoun/ledger/async_writer.py:39:class AsyncLedgerWriter:
./mahoun/ledger/storage.py:57:class FileLedgerWriter(EvidenceLedgerWriter):
./mahoun/ledger/storage.py:136:class NoOpLedgerWriter(EvidenceLedgerWriter):
./mahoun/ledger/blockchain.py:36:class ImmutableLedger:
./mahoun/ledger/models.py:23:class LedgerEntry:
./mahoun/ledger/writer.py:33:class LedgerBackend(ABC):
./mahoun/ledger/writer.py:57:class JSONLLedgerBackend(LedgerBackend):
./mahoun/ledger/writer.py:148:class SQLiteLedgerBackend(LedgerBackend):
./mahoun/ledger/writer.py:281:class NoOpLedgerBackend(LedgerBackend):
./mahoun/ledger/writer.py:346:class EvidenceLedgerWriter:

---

### 11-B. EvidenceLedgerWriter, ImmutableLedger, hash / previous_hash / actor_id / correlation_id / timestamp

Command:
```bash
grep -rn "hash.*previous_hash\|previous_hash.*hash\|actor_id\|correlation_id\|timestamp" --include="*.py" mahoun/ledger/ 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | head -40
```

Output:

mahoun/ledger/write_gate.py:64:    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
mahoun/ledger/write_gate.py:75:            "timestamp": self.timestamp.isoformat(),
mahoun/ledger/async_writer.py:356:                "timestamp": datetime.now(timezone.utc).isoformat(),
mahoun/ledger/storage.py:90:            timestamp = entry.created_at or datetime.now(UTC)
mahoun/ledger/storage.py:99:                "created_at": timestamp.isoformat(),
mahoun/ledger/storage.py:103:            timestamp = datetime.now(UTC)
mahoun/ledger/storage.py:109:                "ts": timestamp.isoformat(),
mahoun/ledger/blockchain.py:112:            timestamp=datetime.now(timezone.utc),
mahoun/ledger/guards.py:52:    - Temporal markers: _deletion_timestamp, _redaction_timestamp
mahoun/ledger/guards.py:93:        OR (n._deletion_timestamp IS NOT NULL 
mahoun/ledger/guards.py:94:            AND datetime(n._deletion_timestamp) <= datetime())
mahoun/ledger/guards.py:95:        OR (n._redaction_timestamp IS NOT NULL 
mahoun/ledger/guards.py:96:            AND datetime(n._deletion_timestamp) <= datetime())
mahoun/ledger/guards.py:109:           n._deletion_timestamp as deleted_at,
mahoun/ledger/models.py:31:    - Execution metadata (execution_id, correlation_id)
mahoun/ledger/models.py:70:    correlation_id: Optional[str] = None
mahoun/ledger/models.py:77:    validation_timestamp: Optional[datetime] = None
mahoun/ledger/models.py:109:    datetime_fields = ['created_at', 'validation_timestamp', 'execution_timestamp']
mahoun/ledger/block.py:31:    - timestamp: When block was created
mahoun/ledger/block.py:44:    timestamp: datetime
mahoun/ledger/block.py:63:            Hash includes: index, timestamp, data, prev_hash
mahoun/ledger/block.py:69:            "timestamp": self.timestamp.isoformat(),
mahoun/ledger/block.py:116:            "timestamp": self.timestamp.isoformat(),
mahoun/ledger/block.py:133:        # Parse timestamp
mahoun/ledger/block.py:134:    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
mahoun/ledger/block.py:145:        block = cls(index=data["index"], timestamp=timestamp, data=ledger_data, prev_hash=data["prev_hash"])
mahoun/ledger/block.py:174:    Uses fixed timestamp so identical empty chains produce identical genesis hashes.
mahoun/ledger/block.py:183:        timestamp=mahoun_epoch,
mahoun/ledger/block.py:216:    block1 = Block(index=1, timestamp=datetime.now(UTC), data=entry, prev_hash=genesis.hash)

---

## 12. Runtime

### 12-A. Dockerfiles

Command:
```bash
find . -name "Dockerfile*" -o -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null | grep -v ".git/" | grep -v "data/" | grep -v "venv/" | head -20
```

Output:

./frontend/Dockerfile
./frontend/Dockerfile.dev
./Dockerfile.backend.optimized
./Dockerfile.kernel
./docker-compose.kernel.yml
./Dockerfile
./docker-compose.yml
./docker-compose.backend.yml
./Dockerfile.backend

---

### 12-B. docker-compose configuration

Command:
```bash
ls -la docker-compose.yml docker-compose.backend.yml docker-compose.kernel.yml 2>&1
```

Output:

-rw-rw-r-- 1 haji haji 6250 Jul 17 15:47 docker-compose.yml
-rw-rw-r-- 1 haji haji 8536 Jul 17 15:47 docker-compose.backend.yml
-rw-rw-r-- 1748016 Jul 17 15:47 docker-compose.kernel.yml

---

## 13. Frontend

### 13-A. File locations and line counts

Command:
```bash
ls -la frontend/src/components/AIChat.tsx frontend/src/components/LegalSearchPage.tsx frontend/src/pages/GovernanceCenter.tsx frontend/src/pages/KnowledgeGraphCenter.tsx 2>&1
```

Output:

-rw-rw-r-- 1 haji haji 1568 Aug 11 02:21 frontend/src/components/AIChat.tsx
-rw-rw-r-- 1 haji haji 9490 Aug 11 02:35 frontend/src/components/LegalSearchPage.tsx
-rw-rw-r-- 1 haji haji 1568 Aug 11 02:21 frontend/src/components/LegalSearchPage.tsx
-rw-rw-r-- 1 haji haji 9490 Aug 11 02:35 frontend/src/pages/GovernanceCenter.tsx
-rw-rw-r-- 1 haji haji 11747 Aug 11 02:20 frontend/src/pages/KnowledgeGraphCenter.tsx

---

Command:
```bash
wc -l frontend/src/components/AIChat.tsx frontend/src/components/LegalSearchPage.tsx frontend/src/pages/GovernanceCenter.tsx frontend/src/pages/KnowledgeGraphCenter.tsx 2>&1
```

Output:

    51 frontend/src/components/AIChat.tsx
  257 frontend/src/components/LegalSearchPage.tsx
  217 frontend/src/pages/GovernanceCenter.tsx
  309 frontend/src/pages/KnowledgeGraphCenter.tsx
  834 total

---

### 13-B. Real API calls, mock/simulation/hardcoded/TODO/FIXME markers

Command:
```bash
grep -n "mock\|simulation\|hardcoded\|TODO\|FIXME\|setTimeout\|fetch\|await.*Client" frontend/src/components/AIChat.tsx frontend/src/components/LegalSearchPage.tsx frontend/src/pages/GovernanceCenter.tsx frontend/src/pages/KnowledgeGraphCenter.tsx 2>/dev/null | head -50
```

Output:

frontend/src/pages/GovernanceCenter.tsx:34:    fetchGovernanceHealth();
frontend/src/pages/GovernanceCenter.tsx:35:    const interval = setInterval(fetchGovernanceHealth, 30000); // Refresh every 30s
frontend/src/pages/GovernanceCenter.tsx:39:  const fetchGovernanceHealth = async () => {
frontend/src/pages/GovernanceCenter.tsx:41:      const response = await fetch('/api/v1/governance/health');
frontend/src/pages/GovernanceCenter.tsx:42:      if (!response.ok) throw new Error('Failed to fetch governance health');
frontend/src/pages/KnowledgeGraphCenter.tsx:44:      const response = await fetch('/api/v1/graph/query', {
frontend/src/pages/KnowledgeGraphCenter.tsx:66:      const response = await fetch('/api/v1/graph/expand', {
frontend/src/pages/KnowledgeGraphCenter.tsx:93:      const response = await fetch('/api/v1/graph/explain-path', {

---

## 14. CI

### 14-A. ci scripts

Command:
```bash
ls -la ci/ 2>&1 | head -20
```

Output:

total 244
drwxrwxr-x 10 haji haji   4096 Aug 13 18:39 .
drwxxr-xr-x 62 haji haji  12288 Aug 15 19:55 ..
-rw-rw-r-- 1 haji haji 191880 Jul 17 05:07 coverage_baseline.json
-drwxr-xxr-x 3 haji haji   4096 Aug 13 18:43 enforcement
-drwxr-xxr-x 2 hahi haji   4096 Aug 10 02:28 first_step
-rwxrwxr-- 1 haji haji    597 Jul 30 06:30 gate_md_count.sh
-rwxr-xxr-x 3 hahi haji   4096 Aug 13 18:33 gates
-drwxr-xxr-x 3 hahi haji   4096 Aug 14 06:13 mypy
-rw-rw-r-- 1 hahi haji 1554 Jun 24 15:25 schema_baseline.json
-drwxr-xxr-x 3 hahi haji   4096 Aug 14 06:13 scripts
-drwxr-xxr-x 3 hahi haji   4096 Aug 14 06:13 security

---

### 14-B. pre-commit

Command:
```bash
ls -la .pre-commit-config.yaml 2>&1
```

Output:

-rw-rw-r-- 1 haji haji 1176 Aug 10 02:31 .pre-commit-config.yaml

---

### 14-C. GitHub/GitLab workflows

Command:
```bash
ls -la .github/workflows/ 2>&1 | head -20
```

Output:

total 20
drwxrwxr-x 2 haji haji 12248 Aug 15 19:55 .
drwxr-xxr-x 3 hahi haji 12288 Aug 15 19:55 ..
-rw-rw-r-- 1 haji hahi 12241 Aug 10 02:34 kernel-governance.yml

---

## 15. Constitutional state

### 15-A. Constitutional file SHA256 hashes

Command:
```bash
sha256sum mahoun/constitutional/constitution/CONSTITUTION.md mahoun/constitutional/README.md AGENTS.md 2>&1
```

Output:

099effb9fe95f1181ae5aa52533fde10aa736baa15c032b79b310c113acd9c7a  mahoun/constitutional/constitution/CONSTITUTION.md
bb68301f4356d13463561471cf38ad035a8375b84761d25796bda52747ec35ed  mahoun/constitutional/README.md
ac25d26c056e4c781aa1e0f034407d5bb6abb4162a113d58dc7c324887f585cf  AGENTS.md

---

### 15-B. AGENTS.md content

Command:
```bash
head -5 AGENTS.md 2>&1
```

Output:

# MahouN — Canonical Component Map
### Classification: MANDATORY PRE-READ / SUBORDINATE TO CONSTITUTIONAL AUTHORITY

---

## 16. Dependency direction

Command:
```bash
grep -rn "from mahoun.core\|import mahoun.core" --include="*.py" . 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__" | grep -v "venv/" | grep -v "data/" | grep -v "test" | head -40
```

Output:

./api/middleware/validation.py:20:from mahoun.core.exceptions import ValidationError
./api/middleware/validation.py:21:from mahoun.core.validation import StringSanitizer
./api/middleware/governance_context.py:32:from mahoun.core.governance.governance_context import GovernanceContextManager
./api/main.py:26:from mahoun.core.exceptions import (
./api/main.py:53:from mahoun.core.settings import load_security_settings
./api/main.py:101:        from mahoun.core.config_validator import validate_runtime_config
./api/main.py:102:        from mahoun.core.runtime_config import get_runtime_settings
./api/main.py:131:            from mahoun.core.config_validator import validate_runtime_config
./api/main.py:154:        from mahoun.core.governance.mutation_boundary import set_audit_sink
./api/main.py:580:    from mahoun.core.environment import is_production, is_staging
./api/database.py:376:        from mahoun.core.governance.authorization_state import set_authorized, reset_authorized
./api/routers/training_datasets.py:38:from mahoun.core.validation import SafeString, StringSanitizer
./api/routers/system.py:43:    from mahoun.core.runtime_config import get_runtime_settings
./api/routers/system.py:216:    from mahoun.core.runtime_config import get_runtime_settings
./api/routers/system.py:227:    from mahoun.core.runtime_config import get_runtime_settings
./api/routers/system.py:232:    from mahoun.core.runtime_config import get_runtime_settings
./api/routers/system.py:247:    from mahoun.core.runtime_config import get_runtime_settings
./api/routers/reasoning.py:36:from mahoun.core.governance import (
./api/routers/reasoning.py:39:from mahoun.core.fortress_validator import SecurityBreachException
./api/routers/reasoning.py:40:from mahoun.core.logging import setup_logger
./api/routers/reasoning.py:41:from mahoun.core.runtime_config import (

---

## 17. Root cleanliness

### 17-A. root *.md files

Command:
```bash
ls -1 *.md 2>&1
```

Output:

01_FRONTEND_GATE_REQUIREMENTS.md
AGENTRULES.md
AGENTS.md
BRANCH_ANALYSIS.md
DUPLICATION_AUDIT_REPORT.md
MAHOUN_HARDENING_EXECUTIVE_SUMMARY.md
MERGE_SAFETY_ANALYSIS.md
README.md
TIER1_HARDENING_SUMMARY.md
glmreport.md

---

Command:
```bash
ls -1 *.md 2>&1 | wc -l
```

Output:

10

---

## 18. Live health

Command:
```bash
curl -s --max-time 3 http://localhost:8000/system/health/detailed 2>&1
```

Output:

