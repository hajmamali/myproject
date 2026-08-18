"""
DI Bug Condition Exploration Test
==================================
Property 1: Bug Condition — DI Violation Sites

This test performs a static scan of the codebase to assert that all 16 known
DI violation sites have been ELIMINATED. On UNFIXED code, this test FAILS —
that failure is the SUCCESS condition proving the violations exist.

After all fix tasks are applied, this test must PASS (zero violations found).

Violation classes:
  Class A — Neo4j session bypass (self.neo4j.session() / self.driver.session())
  Class B — Driver creation outside allowlist (GraphDatabase.driver / AsyncGraphDatabase.driver / Neo4jConnection())
  Class C — Hidden infrastructure construction (SentenceTransformer / redis.Redis / QdrantClient / OpenAI)

ALLOWLIST (files permitted to create Neo4j drivers):
  - mahoun/graph/neo4j/connection.py
  - mahoun/graph/neo4j/schema.py
  - api/database.py
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent

ALLOWLIST = {
    "mahoun/graph/neo4j/connection.py",
    "mahoun/graph/neo4j/schema.py",
    "api/database.py",
}


def _rel(path: Path) -> str:
    """Return path relative to project root using forward slashes."""
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def file_lines(rel_path: str) -> List[str]:
    """Read file and return list of lines (1-indexed: lines[0] = line 1)."""
    full = PROJECT_ROOT / rel_path
    if not full.exists():
        return []
    return full.read_text(encoding="utf-8").splitlines()


def line_contains(rel_path: str, lineno: int, pattern: str) -> bool:
    """Return True if the given 1-based line number contains the pattern."""
    lines = file_lines(rel_path)
    if lineno < 1 or lineno > len(lines):
        return False
    return pattern in lines[lineno - 1]


def file_contains(rel_path: str, pattern: str) -> bool:
    """Return True if any line in the file contains the pattern."""
    return any(pattern in line for line in file_lines(rel_path))


def find_pattern_lines(rel_path: str, pattern: str) -> List[int]:
    """Return list of 1-based line numbers where pattern appears."""
    return [
        i + 1
        for i, line in enumerate(file_lines(rel_path))
        if pattern in line
    ]


def isBugCondition(module_path: str, pattern: str) -> bool:
    """
    FUNCTION isBugCondition(X)
      INPUT: module_path (relative), pattern (construction type string)
      OUTPUT: boolean — True if this is a violation site

    A site is a violation if:
      - The pattern appears in the file
      - The file is NOT on the allowlist
    """
    if module_path in ALLOWLIST:
        return False
    return file_contains(module_path, pattern)


# ---------------------------------------------------------------------------
# Class A — Neo4j Session Bypass (P0)
# ---------------------------------------------------------------------------

class TestClassA_SessionBypass:
    """Assert that raw .session() calls are gone from all P0 sites."""

    @pytest.mark.p2
    def test_graph_enhanced_no_raw_session(self):
        """
        mahoun/retrieval/graph_enhanced.py must NOT call self.neo4j.session().
        Violation confirmed at line 89.
        """
        path = "mahoun/retrieval/graph_enhanced.py"
        pattern = "self.neo4j.session()"
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: raw session bypass found at lines {lines}. "
            f"Replace with self.connection.governed_session(...)."
        )

    @pytest.mark.p2
    def test_graph_vector_sync_no_raw_session_inject(self):
        """
        mahoun/pipelines/sync/graph_vector_sync.py must NOT call self.neo4j.session()
        in _inject_neo4j_embedding (was line 85).
        """
        path = "mahoun/pipelines/sync/graph_vector_sync.py"
        pattern = "self.neo4j.session()"
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: raw session bypass found at lines {lines}. "
            f"Replace with self.connection.governed_session(...)."
        )

    @pytest.mark.p2
    def test_graph_vector_sync_no_raw_session_backfill(self):
        """
        mahoun/pipelines/sync/graph_vector_sync.py must NOT call self.neo4j.session()
        in backfill_graph_vectors (was line 111).
        """
        path = "mahoun/pipelines/sync/graph_vector_sync.py"
        # Same pattern — covered by test above, but we verify both occurrences were removed
        pattern = "self.neo4j.session()"
        lines = find_pattern_lines(path, pattern)
        # Both line 85 and 111 must be gone
        assert len(lines) == 0, (
            f"VIOLATION in {path}: {len(lines)} raw session bypass(es) remain at lines {lines}."
        )

    @pytest.mark.p2
    def test_legal_cypher_queries_no_raw_session(self):
        """
        mahoun/graph/legal_cypher_queries.py must NOT call self.driver.session().
        Violation confirmed at line 694.
        """
        path = "mahoun/graph/legal_cypher_queries.py"
        pattern = "self.driver.session()"
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: raw driver.session() found at lines {lines}. "
            f"Replace with self.connection.governed_session(...)."
        )


# ---------------------------------------------------------------------------
# Class B — Driver Creation Outside Allowlist (P0)
# ---------------------------------------------------------------------------

class TestClassB_DriverCreation:
    """Assert that no driver creation occurs outside the allowlist."""

    @pytest.mark.p2
    def test_integrity_probe_no_graphdatabase_driver(self):
        """
        mahoun/infrastructure/health/integrity_probe.py must NOT call GraphDatabase.driver(.
        Violation confirmed at line 51.
        """
        path = "mahoun/infrastructure/health/integrity_probe.py"
        pattern = "GraphDatabase.driver("
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: GraphDatabase.driver() outside allowlist at lines {lines}. "
            f"Replace with get_connection().ping()."
        )

    @pytest.mark.p2
    def test_checker_no_asyncgraphdatabase_driver(self):
        """
        mahoun/infrastructure/health/checker.py must NOT call AsyncGraphDatabase.driver(.
        Violation confirmed at line 157.
        """
        path = "mahoun/infrastructure/health/checker.py"
        pattern = "AsyncGraphDatabase.driver("
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: AsyncGraphDatabase.driver() outside allowlist at lines {lines}. "
            f"Replace with get_connection().ping() via executor."
        )

    @pytest.mark.p2
    def test_run_optimizer_job_no_direct_neo4j_connection(self):
        """
        mahoun/graph/optimizer/run_optimizer_job.py must NOT directly instantiate Neo4jConnection(.
        Violation confirmed at line 231.
        """
        path = "mahoun/graph/optimizer/run_optimizer_job.py"
        pattern = "Neo4jConnection("
        lines = find_pattern_lines(path, pattern)
        assert lines == [], (
            f"VIOLATION in {path}: Direct Neo4jConnection() instantiation at lines {lines}. "
            f"Replace with get_connection()."
        )

    @pytest.mark.p2
    def test_no_graphdatabase_driver_outside_allowlist_globally(self):
        """
        Global scan: GraphDatabase.driver( must not appear outside the allowlist.
        """
        violations: List[Tuple[str, int]] = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            rel = _rel(py_file)
            if rel in ALLOWLIST:
                continue
            if any(skip in rel for skip in ("__pycache__", ".git", "venv", "node_modules", "archived_modules", ".worktrees")):
                continue
            for i, line in enumerate(py_file.read_text(encoding="utf-8", errors="ignore").splitlines()):
                if "GraphDatabase.driver(" in line:
                    violations.append((rel, i + 1))
        assert violations == [], (
            f"VIOLATION: GraphDatabase.driver() found outside allowlist:\n"
            + "\n".join(f"  {f}:{ln}" for f, ln in violations)
        )

    @pytest.mark.p2
    def test_no_asyncgraphdatabase_driver_outside_allowlist_globally(self):
        """
        Global scan: AsyncGraphDatabase.driver( must not appear outside the allowlist.
        """
        violations: List[Tuple[str, int]] = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            rel = _rel(py_file)
            if rel in ALLOWLIST:
                continue
            if any(skip in rel for skip in ("__pycache__", ".git", "venv", "node_modules", "archived_modules", ".worktrees")):
                continue
            for i, line in enumerate(py_file.read_text(encoding="utf-8", errors="ignore").splitlines()):
                if "AsyncGraphDatabase.driver(" in line:
                    violations.append((rel, i + 1))
        assert violations == [], (
            f"VIOLATION: AsyncGraphDatabase.driver() found outside allowlist:\n"
            + "\n".join(f"  {f}:{ln}" for f, ln in violations)
        )


# ---------------------------------------------------------------------------
# Class C — Hidden Infrastructure Construction (P1)
# ---------------------------------------------------------------------------

class TestClassC_HiddenConstruction:
    """Assert that hidden infrastructure construction is eliminated from all P1 sites."""

    # --- SentenceTransformer sites (7 files) ---

    @pytest.mark.p2
    def test_embedding_provider_no_hidden_sentence_transformer(self):
        """
        mahoun/graph/retriever/embedding_provider.py must NOT construct SentenceTransformer(
        in __init__ without injection guard. Violation at line 69.
        """
        path = "mahoun/graph/retriever/embedding_provider.py"
        # After fix: SentenceTransformer( may only appear inside a fallback/lazy path
        # guarded by `if model is None:` or similar. The eager construction in __init__
        # without an injection check is the violation.
        # We assert the file accepts an injected model parameter.
        content = "\n".join(file_lines(path))
        assert "model: Optional[SentenceTransformer]" in content or \
               "model=None" in content, (
            f"VIOLATION in {path}: No injectable model parameter found. "
            f"Add `model: Optional[SentenceTransformer] = None` to __init__."
        )

    @pytest.mark.p2
    def test_graph_builder_no_hidden_sentence_transformer(self):
        """
        mahoun/graph/gnn/graph_builder.py must accept injected SentenceTransformer.
        Violation at line 83.
        """
        path = "mahoun/graph/gnn/graph_builder.py"
        content = "\n".join(file_lines(path))
        assert "model: Optional[SentenceTransformer]" in content or \
               "model=None" in content, (
            f"VIOLATION in {path}: No injectable model parameter found."
        )

    @pytest.mark.p2
    def test_semantic_chunker_no_hidden_sentence_transformer(self):
        """
        mahoun/graph/gnn/semantic_chunker.py must accept injected SentenceTransformer.
        Violation at line 161.
        """
        path = "mahoun/graph/gnn/semantic_chunker.py"
        content = "\n".join(file_lines(path))
        assert "embed_model_instance" in content or \
               "embed_model=None" in content or \
               "Optional[SentenceTransformer]" in content, (
            f"VIOLATION in {path}: No injectable embed_model_instance parameter found."
        )

    @pytest.mark.p2
    def test_semantic_search_no_hidden_sentence_transformer(self):
        """
        mahoun/graph/semantic_search.py must accept injected SentenceTransformer.
        Violation at line 149.
        """
        path = "mahoun/graph/semantic_search.py"
        content = "\n".join(file_lines(path))
        assert "model_instance" in content or \
               "Optional[SentenceTransformer]" in content, (
            f"VIOLATION in {path}: No injectable model_instance parameter found."
        )

    @pytest.mark.p2
    def test_retrieval_cache_no_hidden_sentence_transformer(self):
        """
        mahoun/pipelines/retrieval_cache.py must accept injected SentenceTransformer.
        Violation at line 123.
        """
        path = "mahoun/pipelines/retrieval_cache.py"
        content = "\n".join(file_lines(path))
        assert "embed_model" in content and (
            "Optional[SentenceTransformer]" in content or "embed_model=None" in content
        ), (
            f"VIOLATION in {path}: No injectable embed_model parameter found."
        )

    @pytest.mark.p2
    def test_embed_index_no_hidden_sentence_transformer(self):
        """
        mahoun/pipelines/embed_index.py AdvancedEmbedder must accept injected SentenceTransformer.
        Violation at line 122.
        """
        path = "mahoun/pipelines/embed_index.py"
        content = "\n".join(file_lines(path))
        assert "model: Optional[SentenceTransformer]" in content or \
               "model=None" in content, (
            f"VIOLATION in {path}: No injectable model parameter found in AdvancedEmbedder."
        )

    @pytest.mark.p2
    def test_ultra_evaluation_no_hidden_sentence_transformer(self):
        """
        mahoun/rag/ultra_evaluation_system.py SemanticSimilarityCalculator must accept
        injected SentenceTransformer. Violation at line 279.
        """
        path = "mahoun/rag/ultra_evaluation_system.py"
        content = "\n".join(file_lines(path))
        assert "model: Optional[SentenceTransformer]" in content or \
               "model=None" in content, (
            f"VIOLATION in {path}: No injectable model parameter found in SemanticSimilarityCalculator."
        )

    # --- redis.Redis and QdrantClient (ultra_indexing_system.py) ---

    @pytest.mark.p2
    def test_ultra_indexing_embedding_generator_no_hidden_redis(self):
        """
        mahoun/rag/ultra_indexing_system.py EmbeddingGenerator must accept injected redis.Redis.
        Violation at line 274.
        """
        path = "mahoun/rag/ultra_indexing_system.py"
        content = "\n".join(file_lines(path))
        assert "cache: Optional" in content or \
               "cache=None" in content, (
            f"VIOLATION in {path}: No injectable cache parameter found in EmbeddingGenerator."
        )

    @pytest.mark.p2
    def test_ultra_indexing_vector_index_no_hidden_qdrant(self):
        """
        mahoun/rag/ultra_indexing_system.py VectorIndex must accept injected QdrantClient.
        Violation at line 579.
        """
        path = "mahoun/rag/ultra_indexing_system.py"
        content = "\n".join(file_lines(path))
        assert "qdrant_client: Optional" in content or \
               "qdrant_client=None" in content, (
            f"VIOLATION in {path}: No injectable qdrant_client parameter found in VectorIndex."
        )

    # --- OpenAI client (query_rewriter.py) ---

    @pytest.mark.p2
    def test_query_rewriter_no_module_level_openai_import(self):
        """
        mahoun/pipelines/query_rewriter.py must NOT have module-level `from openai import OpenAI`.
        Violation at line 14.
        """
        path = "mahoun/pipelines/query_rewriter.py"
        lines = file_lines(path)
        # Module-level means outside any function/class (no leading whitespace)
        module_level_violations = [
            i + 1
            for i, line in enumerate(lines)
            if re.match(r'^from openai import OpenAI', line.strip()) and
               not line.startswith("    ") and
               not line.startswith("\t")
        ]
        assert module_level_violations == [], (
            f"VIOLATION in {path}: module-level `from openai import OpenAI` at lines "
            f"{module_level_violations}. Move inside __init__ under try/except ImportError."
        )

    @pytest.mark.p2
    def test_query_rewriter_accepts_injected_client(self):
        """
        mahoun/pipelines/query_rewriter.py LLMQueryRewriter must accept injected OpenAI client.
        """
        path = "mahoun/pipelines/query_rewriter.py"
        content = "\n".join(file_lines(path))
        assert "client: Optional" in content or \
               "client=None" in content, (
            f"VIOLATION in {path}: No injectable client parameter found in LLMQueryRewriter."
        )


# ---------------------------------------------------------------------------
# isBugCondition property test — all 16 sites must return True on unfixed code
# ---------------------------------------------------------------------------

class TestIsBugConditionProperty:
    """
    Verify that isBugCondition() returns True for all 16 confirmed violation sites.
    On unfixed code, all 16 must be detectable.
    After fixes, all 16 must return False (patterns eliminated).
    """

    VIOLATION_INVENTORY = [
        # (module_path, pattern, description)
        ("mahoun/retrieval/graph_enhanced.py",
         "self.neo4j.session()",
         "Class A: raw session bypass in GraphEnhancedRetriever"),

        ("mahoun/pipelines/sync/graph_vector_sync.py",
         "self.neo4j.session()",
         "Class A: raw session bypass in GraphVectorSync._inject_neo4j_embedding"),

        ("mahoun/graph/legal_cypher_queries.py",
         "self.driver.session()",
         "Class A: raw session bypass in LegalQueryExecutor"),

        ("mahoun/infrastructure/health/integrity_probe.py",
         "GraphDatabase.driver(",
         "Class B: driver creation outside allowlist in integrity_probe"),

        ("mahoun/infrastructure/health/checker.py",
         "AsyncGraphDatabase.driver(",
         "Class B: async driver creation outside allowlist in checker"),

        ("mahoun/graph/optimizer/run_optimizer_job.py",
         "Neo4jConnection(",
         "Class B: direct Neo4jConnection() instantiation in run_optimizer_job"),

        ("mahoun/graph/retriever/embedding_provider.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in EmbeddingProvider"),

        ("mahoun/graph/gnn/graph_builder.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in LegalGraphBuilder"),

        ("mahoun/graph/gnn/semantic_chunker.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in SemanticChunker"),

        ("mahoun/graph/semantic_search.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in PersianSemanticSearch"),

        ("mahoun/pipelines/retrieval_cache.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in SemanticCache"),

        ("mahoun/pipelines/embed_index.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in AdvancedEmbedder"),

        ("mahoun/rag/ultra_evaluation_system.py",
         "SentenceTransformer(",
         "Class C: hidden SentenceTransformer in SemanticSimilarityCalculator"),

        ("mahoun/rag/ultra_indexing_system.py",
         "redis.Redis(",
         "Class C: hidden redis.Redis in EmbeddingGenerator"),

        ("mahoun/rag/ultra_indexing_system.py",
         "QdrantClient(",
         "Class C: hidden QdrantClient in VectorIndex"),

        ("mahoun/pipelines/query_rewriter.py",
         "from openai import OpenAI",
         "Class C: hidden OpenAI import in query_rewriter"),
    ]

    @pytest.mark.parametrize("module_path,pattern,description", VIOLATION_INVENTORY)
    @pytest.mark.p2
    def test_violation_site_is_detectable(self, module_path, pattern, description):
        """
        Each violation site must be detectable by isBugCondition().
        On UNFIXED code: isBugCondition() returns True (violation present).
        After fix: isBugCondition() returns False (violation eliminated).

        This test FAILS on unfixed code — that failure IS the proof the bug exists.
        """
        result = isBugCondition(module_path, pattern)
        assert not result, (
            f"BUG CONFIRMED — {description}\n"
            f"  File: {module_path}\n"
            f"  Pattern: {pattern!r}\n"
            f"  isBugCondition() returned True — violation still present.\n"
            f"  Lines: {find_pattern_lines(module_path, pattern)}"
        )
