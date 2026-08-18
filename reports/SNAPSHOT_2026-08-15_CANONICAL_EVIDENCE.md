# SNAPSHOT_2026-08-15_CANONICAL_EVIDENCE

**Role:** Evidence Collector Only  
**Status:** NO INTERPRETATION - RAW FACTS ONLY  
**Date:** 2026-08-15  
**Scope:** Current repository state at HEAD: 106256df81a2571a634b88077887b4a2364aa244

---

## FACTS: Governance Router Import Structure

FACT: api/routers/governance.py:16 contains:
```python
from mahoun.security.rbac import require_permissions, Permission
```

FACT: api/routers/governance.py:366 contains:
```python
_ = Depends(require_permissions([Permission.READ]))
```

FACT: api/routers/governance.py:399 contains:
```python
_ = Depends(require_permissions([Permission.READ]))
```

FACT: api/routers/governance.py:421 contains:
```python
_ = Depends(require_permissions([Permission.READ]))
```

FACT: api/routers/governance.py:439 contains:
```python
_ = Depends(require_permissions([Permission.READ]))
```

FACT: mahoun/security/rbac.py:24-31 contains:
```python
class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"
    ANONYMIZE = "anonymize"
```

FACT: mahoun/security/rbac.py:217-235 contains:
```python
def require_permission(
    self,
    username: str,
    permission: Permission
):
    if not self.check_permission(username, permission):
        raise PermissionError(
            f"User {username} does not have {permission} permission"
        )
```

FACT: mahoun/security/rbac.py:359-384 contains:
```python
def require_permission(permission: Permission):
    def decorator(func):
        def wrapper(*args, **kwargs):
            username = kwargs.get('username') or (args[0] if args else None)
            if not username:
                raise ValueError("Username required for permission check")
            rbac = RBACManager()
            rbac.require_permission(username, permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

FACT: mahoun/security/rbac.py contains NO definition of symbol `require_permissions` (plural).

FACT: api/main.py:462-469 contains:
```python
# Register Governance Center router (CRITICAL - Constitutional Compliance)
try:
    from api.routers import governance as governance_router
    app.include_router(governance_router.router)
    logger.info("✓ Governance Center router registered at /api/v1/governance")
except ImportError as e:
    logger.warning(f"Governance router not available: {e}")
```

---

## FACTS: Neo4j Initialization Path

FACT: mahoun/graph/neo4j/connection.py:1-13 contains imports:
```python
import logging
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TYPE_CHECKING
```

FACT: mahoun/graph/neo4j/connection.py:1-32 contains NO import of module `asyncio`.

FACT: mahoun/graph/neo4j/connection.py:739 contains in docstring:
```python
Raises:
    asyncio.TimeoutError: If connectivity check times out
```

FACT: mahoun/graph/neo4j/connection.py:749 contains:
```python
result = await asyncio.wait_for(
    initializer.initialize_with_governance(
        timeout_sec=timeout_sec,
        correlation_id="async_driver_connectivity_check"
    ),
    timeout=timeout_sec
)
```

FACT: mahoun/graph/neo4j/connection.py:764 contains:
```python
except asyncio.TimeoutError:
    _conn_logger.error(f"❌ Async driver connectivity check timed out after {timeout_sec}s")
    raise
```

FACT: mahoun/graph/neo4j/connection.py:633-718 contains function `initialize_canonical_async_driver` with no use of `asyncio` module.

FACT: mahoun/graph/neo4j/connection.py:721-769 contains function `verify_async_driver_connectivity` with use of `asyncio` module at lines 739, 749, 764.

FACT: api/database.py:33 contains:
```python
import asyncio
```

FACT: api/database.py:216-235 contains:
```python
async def _handshake_neo4j(driver: Any, timeout_sec: float) -> None:
    if not verify_async_driver_connectivity:
        raise RuntimeError("Neo4j governance layer not available")
    success = await verify_async_driver_connectivity(driver, timeout_sec=timeout_sec)
    if not success:
        raise RuntimeError("Neo4j handshake failed through governance layer")
```

FACT: api/database.py:238-369 contains function `init_neo4j` with try/except blocks at lines 283-296, 314-331, 332-353, 354-369.

FACT: api/database.py:276-282 contains:
```python
neo4j_driver = await initialize_canonical_async_driver(
    uri=uri,
    auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    max_connection_lifetime=settings.neo4j_max_connection_lifetime,
    max_connection_pool_size=settings.neo4j_max_connection_pool_size,
    connection_acquisition_timeout=settings.neo4j_connection_timeout,
)
```

FACT: api/database.py:301-313 contains:
```python
await asyncio.wait_for(
    _handshake_neo4j(
        neo4j_driver,
        timeout_sec=NEO4J_HANDSHAKE_TIMEOUT_SEC,
    ),
    timeout=NEO4J_HANDSHAKE_TIMEOUT_SEC,
)
```

FACT: mahoun/graph/neo4j/connection.py:697-704 contains:
```python
driver = AsyncGraphDatabase.driver(
    uri,
    auth=auth,
    max_connection_lifetime=max_connection_lifetime,
    max_connection_pool_size=max_connection_pool_size,
    connection_acquisition_timeout=connection_acquisition_timeout,
    **driver_config
)
```

FACT: mahoun/graph/neo4j/connection.py:706-708 contains:
```python
_conn_logger.info(
    f"✅ Canonical async driver initialized successfully at {uri}"
)
```

FACT: mahoun/graph/neo4j/connection.py:767-769 contains:
```python
except Exception as e:
    _conn_logger.error(f"❌ Async driver connectivity check failed: {e}")
    raise ConnectionError(f"Driver connectivity verification failed: {e}") from e
```

FACT: api/database.py:339-342 contains:
```python
log.warning(
    f"⚠️ Neo4j unavailable at {uri}. Falling back to non-graph mode. "
    f"Reason: {type(conn_err).__name__}: {conn_err}"
)
```

FACT: api/database.py:352-353 contains:
```python
neo4j_driver = None
return
```

FACT: api/main.py:208-211 contains:
```python
if enable_neo4j:
    from api.database import init_neo4j
    await init_neo4j()
    logger.info("✅ Neo4j initialized")
```

FACT: mahoun/bootstrap/runtime.py:85 contains:
```python
logger.info("Governance runtime validation passed: audit sink is wired.")
```

---

## FACTS: Runtime Configuration State

FACT: mahoun/core/runtime_config.py:149 contains:
```python
mode = os.getenv("MAHOUN_MODE") or yaml_config.get("mode") or "server_full"
```

FACT: mahoun/core/runtime_config.py:217-219 contains:
```python
return MahounRuntimeSettings(
    mode="server_full",  # FORCED ENTERPRISE MODE
    graph_enabled=True,
    graph_backend="local_full",
```

---

## FACTS: Module Inventory - Pipelines

FACT: mahoun/pipelines/ contains 45 .py files (excluding __pycache__).

FACT: mahoun/pipelines/ingestion/ contains 30 .py files (excluding __pycache__).

---

## FACTS: Modules Imported from Pipelines (Outside pipelines/)

FACT: api/main.py:54 contains:
```python
from mahoun.pipelines._logging import get_logger
```

FACT: api/routers/training_datasets.py:287 contains:
```python
from mahoun.pipelines.ingestion.document_handlers import DocumentHandlerFactory
```

FACT: api/routers/training_datasets.py:371 contains:
```python
from mahoun.pipelines.ingestion.document_handlers import DocumentHandlerFactory
```

FACT: api/routers/ingest.py:63 contains:
```python
from mahoun.pipelines.ingestion.enhanced_pipeline import (
    EnhancedIngestionPipeline,
    EnhancedIngestionResult
)
```

FACT: api/routers/ingest.py:82 contains:
```python
from mahoun.pipelines.ingestion.pipeline import IngestionPipeline
```

FACT: api/routers/ingest.py:106 contains:
```python
from mahoun.pipelines.ingestion.document_handlers import extract_document_text
```

FACT: api/routers/ingest.py:227 contains:
```python
from mahoun.pipelines.ingestion.minimal_verdict_parser import (
    MinimalVerdictParser,
    parse_verdict_text
)
```

FACT: api/routers/ingest.py:231 contains:
```python
from mahoun.pipelines.graph_build import GraphBuildPipeline
```

FACT: mahoun/bootstrap/runtime.py:203 contains:
```python
from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
```

FACT: mahoun/rag/hybrid_rag_service.py:279 contains:
```python
from mahoun.pipelines.embed_index import EmbeddingService
```

FACT: mahoun/rag/hybrid_rag_service.py:420 contains:
```python
from mahoun.pipelines.vector_store.manager import VectorStoreManager
```

FACT: mahoun/rag/indexing_pipeline.py:22 contains:
```python
from mahoun.pipelines.ingestion import IngestionPipeline
```

FACT: mahoun/rag/indexing_pipeline.py:23 contains:
```python
from mahoun.pipelines.ingestion.document_normalizer import DocumentNormalizer, normalize_document_text
```

FACT: mahoun/rag/policy_aware_rag_service.py:507 contains:
```python
from mahoun.pipelines.query_rewriter import QueryRewriter
```

FACT: mahoun/rag/evidence_enrichment.py:15 contains:
```python
from mahoun.pipelines.ingestion.legal_ner import LegalNEREngine
```

FACT: mahoun/graph/builders/entity_linker.py:809 contains comment referencing:
```python
>>> from mahoun.pipelines.ingestion.legal_ner import extract_entities
```

FACT: mahoun/uncertainty/service.py:24 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/uncertainty/gaussian_process.py:121 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/uncertainty/ensemble.py:12 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/guardrails/runtime_invariants.py:17 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/infrastructure/cache/smart_cache.py:32 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/monitoring/wandb_logger.py:28 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/monitoring/metrics_tracker.py:13 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/orchestrator/qa/advanced_chatbot.py:26 contains:
```python
from mahoun.pipelines._logging import setup_logger
```

FACT: mahoun/orchestrator/bootstrap_verdict_dataloader.py:47 contains:
```python
from mahoun.pipelines.ingestion.minimal_verdict_parser import (
    MinimalVerdictParser,
    parse_verdict_text
)
```

FACT: mahoun/orchestrator/bootstrap_verdict_dataloader.py:85 contains:
```python
from mahoun.pipelines.vector_store.manager import index_verdict_struct
```

FACT: mahoun/orchestrator/demo_mvp.py:93 contains:
```python
from mahoun.pipelines.embed_index import EmbeddingService, EmbeddingConfig
```

FACT: mahoun/orchestrator/demo_mvp.py:107 contains:
```python
from mahoun.pipelines.vector_store.manager import VectorStoreManager
```

FACT: mahoun/orchestrator/demo_mvp.py:118 contains:
```python
from mahoun.pipelines.ingestion.pipeline import IngestionPipeline
```

FACT: mahoun/agents/timeline_agent.py:46 contains:
```python
from mahoun.pipelines.ingestion.metadata_extractor import MetadataExtractor
```

FACT: mahoun/agents/doc_parser_agent.py:127 contains:
```python
from mahoun.pipelines.ingestion.legal_ner import LegalNEREngine
```

FACT: mahoun/agents/doc_parser_agent.py:138 contains:
```python
from mahoun.pipelines.ingestion.legal_storage import LegalStorageService
```

FACT: mahoun/agents/doc_parser_agent.py:147 contains:
```python
from mahoun.pipelines.ingestion.minimal_verdict_parser import MinimalVerdictParser
```

FACT: mahoun/agents/doc_parser_agent.py:155 contains:
```python
from mahoun.pipelines.ingestion.enhanced_chunker import EnhancedChunker, ChunkingConfig
```

FACT: mahoun/agents/doc_parser_agent.py:168 contains:
```python
from mahoun.pipelines.ingestion.ocr_handler import OCRHandler
```

FACT: mahoun/agents/doc_parser_agent.py:176 contains:
```python
from mahoun.pipelines.ingestion.persian_normalizer import PersianLegalNormalizer
```

FACT: mahoun/agents/doc_parser_agent.py:364 contains:
```python
from mahoun.pipelines.ingestion.document_handlers import DocumentHandlerFactory
```

FACT: mahoun/flows/enhanced_rag.py:16 contains:
```python
from mahoun.pipelines.llm.ollama_llm import OllamaLLMService
```

FACT: mahoun/finetuning/qa_generator.py:90 contains:
```python
from mahoun.pipelines.llm.ollama_llm import OllamaLLMService
```

FACT: mahoun/retrieval/graph_enhanced.py:35 contains:
```python
from mahoun.pipelines.ingestion.enhanced_embedding import EnhancedEmbeddingService
```

FACT: mahoun/retrieval/graph_enhanced.py:194 contains:
```python
from mahoun.pipelines.ingestion.enhanced_embedding import EnhancedEmbeddingService
```

FACT: mahoun/retrieval/graph_enhanced.py:194 contains:
```python
from mahoun.pipelines.ingestion.enhanced_embedding import EnhancedEmbeddingService
```

FACT: mahoun/metrics/health.py:90 contains:
```python
from mahoun.pipelines.vector_store.manager import VectorStoreManager
```

FACT: mahoun/mcp/tools/rag.py:21 contains:
```python
from mahoun.pipelines.vector_store.manager_v2 import VectorStoreManagerV2
```

FACT: mahoun/mcp/tools/ingest.py:21 contains:
```python
from mahoun.pipelines.ingestion.pipeline import IngestionPipelineV2, IngestionResultV2
```

FACT: mahoun/services/search/legal_search_service.py:98 contains:
```python
from mahoun.pipelines.vector_store.manager import VectorStoreManager
```

FACT: scripts/backfill_vectors.py:74 contains:
```python
from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
```

---

## FACTS: Switchboard Registrations

FACT: mahoun/switchboard.py:155-158 contains:
```python
switchboard.register(
    "legal_pipeline",
    base_path="mahoun.pipelines.ingestion.hardened_legal_pipeline.HardenedLegalPipeline",
)
```

FACT: mahoun/switchboard.py:169-170 contains:
```python
switchboard.register(
    "document_normalizer",
    base_path="mahoun.pipelines.ingestion.document_normalizer.DocumentNormalizer",
)
```

FACT: mahoun/switchboard.py:172-174 contains:
```python
switchboard.register(
    "metadata_extractor",
    base_path="mahoun.pipelines.ingestion.metadata_extractor.MetadataExtractor",
)
```

FACT: mahoun/switchboard.py:176-177 contains:
```python
switchboard.register(
    "ocr_handler", base_path="mahoun.pipelines.ingestion.ocr_handler.OCRHandler"
)
```

FACT: mahoun/switchboard.py:179-181 contains:
```python
switchboard.register(
    "document_handler_factory",
    base_path="mahoun.pipelines.ingestion.document_handlers.DocumentHandlerFactory",
)
```

FACT: mahoun/switchboard.py:183-189 contains:
```python
switchboard.register(
    "graph_build_pipeline",
    base_path="mahoun.pipelines.graph_build.run_import.GraphBuildPipeline",
)
```

---

## FACTS: Module Inventory - All Python Files

FACT: Repository contains 20,595 Python files (excluding venv/, data/, .git/).

FACT: Repository contains 8,401,437 lines of Python code (excluding venv/, data/, .git/).

FACT: Frontend contains 69 TypeScript/TypeScriptX files.

FACT: Frontend contains 11,747 lines of TypeScript/TypeScriptX code.

---

## FACTS: Git State

FACT: git log -1 reports:
```
106256df81a2571a634b88077887b4a2364aa244 2026-08-11 16:49:52 +0330 feat: TIER 1 HARDENING COMPLETE - Thread-safe stats, STRICT default, NLI tests, audit logging
```

---

## FACTS: File System State

FACT: Root directory contains 10 .md files:
```
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
```

FACT: reports/ directory exists and contains multiple .md files.

FACT: mahoun/constitutional/ directory exists.

FACT: mahoun/security/rbac.py exists and is 10815 bytes.

FACT: api/routers/governance.py exists and is 1568 bytes.

FACT: mahoun/graph/neo4j/connection.py exists and is 48155 bytes.

FACT: api/database.py exists and is 1176 bytes.

---

## END OF SNAPSHOT

**NO INTERPRETATION. NO CONCLUSION. NO RECOMMENDATION. ONLY FACTS.**
