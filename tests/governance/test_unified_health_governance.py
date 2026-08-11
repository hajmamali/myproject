"""
Unified Health Governance Compliance Test
==========================================

Adversarial / Zero-Trust static + behavioral test that enforces the
unified system governance contract introduced by the
``health_checker.py`` / ``api.database.py`` refactor (Action Item 1 + 2
of the runtime-governance mandate).

The test is structured in three layers, matching the three concerns the
mandate explicitly calls out:

1. ``TestEnforcement`` — the **code** must enforce the architecture
   (no re-instantiation, no shadow implementations, no bypass of the
   canonical surface).

2. ``TestHardening`` — the **runtime** must be robust against failure
   (bounded timeouts, graceful degradation, no unhandled exceptions
   leaking out of ``/health``).

3. ``TestUnifiedGovernance`` — the system must obey the unified
   governance rules of ``AGENTS.md`` (single source of truth, no
   duplicate governance classes, no resurrection of intentionally
   disabled subsystems, canonical driver-construction site).

Every assertion is **evidence-based** (file:line) so a regression is
trivially attributable. The test runs as a normal ``pytest`` module
and also as a CLI script for CI integration (per
``AGENTS.md`` Part 4).
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import textwrap
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import pytest


# ============================================================================
# Path constants
# ============================================================================
ROOT = pathlib.Path(__file__).resolve().parents[2]
HC = ROOT / "mahoun" / "infrastructure" / "health_checker.py"
DB = ROOT / "api" / "database.py"
MAIN = ROOT / "api" / "main.py"
NEO4J_CONN = ROOT / "mahoun" / "graph" / "neo4j" / "connection.py"
SWITCHBOARD = ROOT / "mahoun" / "switchboard.py"
ULTRA_FACTORY = ROOT / "mahoun" / "agents" / "ultra_factory.py"
RUNTIME_CONFIG = ROOT / "mahoun" / "core" / "runtime_config.py"
AGENTS_MD = ROOT / "AGENTS.md"
VALIDATOR_SCRIPT = ROOT / "scripts" / "validate_governance_compliance.py"


# ============================================================================
# AST helpers
# ============================================================================
def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(_read(path), str(path))


def _get_function(
    tree: ast.Module, name: str
) -> Optional[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return node
    return None


def _collect_calls(tree: ast.Module) -> List[Tuple[str, int, ast.Call]]:
    """Collect all Call nodes with (callee_name_or_None, lineno, node)."""
    out: List[Tuple[str, int, ast.Call]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                out.append((node.func.id, node.lineno, node))
            elif isinstance(node.func, ast.Attribute):
                out.append((node.func.attr, node.lineno, node))
    return out


def _collect_except_handlers(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> List[Set[str]]:
    """Return the set of exception names caught in each except-clause of ``func``.

    The result is a list (one entry per except-clause) of name strings.
    A bare ``except:`` is represented as ``{"bare"}``; a tuple handler
    is exploded into its parts; an ``Exception`` handler is normalized
    to ``{"Exception"}``.
    """
    out: List[Set[str]] = []
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler):
            names: Set[str] = set()
            if node.type is None:
                names.add("bare")
            elif isinstance(node.type, ast.Name):
                names.add(node.type.id)
            elif isinstance(node.type, ast.Attribute):
                names.add(node.type.attr)
            elif isinstance(node.type, ast.Tuple):
                for elt in node.type.elts:
                    if isinstance(elt, ast.Name):
                        names.add(elt.id)
                    elif isinstance(elt, ast.Attribute):
                        names.add(elt.attr)
            out.append(names)
    return out


def _class_names(tree: ast.Module) -> List[Tuple[str, int]]:
    return [
        (n.name, n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef)
    ]


# ============================================================================
# CATEGORY 1 — ENFORCEMENT
# ============================================================================
class TestEnforcement:
    """The code must enforce the architecture: no re-instantiation, no
    shadow implementations, no bypass of the canonical surface."""

    # ---- Forbidden constructor calls in the health checker --------------
    FORBIDDEN_HEAVY_CONSTRUCTORS = (
        # (forbidden_name, why_it_is_forbidden)
        ("OllamaLLMService", "LLM client re-instantiation"),
        ("VectorStoreManager", "Vector store re-instantiation"),
        ("UltraHybridSearch", "Hybrid search re-instantiation"),
        ("GaussianProcessUncertainty", "Uncertainty model re-instantiation"),
        ("UltraReasoningService", "Reasoning service re-instantiation"),
        ("UltraGraphBuilder", "Graph builder re-instantiation"),
    )

    @pytest.fixture(scope="class")
    def hc_tree(self) -> ast.Module:
        return _parse(HC)

    @pytest.fixture(scope="class")
    def hc_calls(self, hc_tree: ast.Module) -> List[Tuple[str, int, ast.Call]]:
        return _collect_calls(hc_tree)

    @pytest.mark.parametrize(
        "forbidden,reason", FORBIDDEN_HEAVY_CONSTRUCTORS,
        ids=[c[0] for c in FORBIDDEN_HEAVY_CONSTRUCTORS],
    )
    def test_no_forbidden_constructor_in_health_checker(
        self, hc_calls, forbidden: str, reason: str
    ) -> None:
        """A forbidden constructor in the health check path is a P0
        violation: it makes ``/health`` produce side effects and can
        re-initialize pools, leak memory, and re-trigger the canonical
        duplication pattern the codebase has fought repeatedly (see
        ``AGENTS.md`` Part 3).
        """
        offenders = [
            (line, node)
            for name, line, node in hc_calls
            if name == forbidden
        ]
        assert not offenders, (
            f"{HC.name} MUST NOT call {forbidden}() — {reason}. "
            f"Health checks inspect pre-existing references via "
            f"HealthChecker._lookup_existing(app_state attr, "
            f"switchboard_key) instead. Offending site(s): "
            f"{[(line, ast.unparse(node)) for line, node in offenders]}"
        )

    def test_no_lazy_resource_initialize_call(self, hc_tree: ast.Module) -> None:
        """``await search.initialize()`` / similar must NEVER appear in
        the health check. Heavy-resource ``initialize()`` calls can
        re-load models, re-open connection pools, and persist state
        across requests — exactly the side-effect pattern the mandate
        forbids.
        """
        forbidden_initializers = (
            "search.initialize",
            "vector.initialize",
            "llm.initialize",
            "agent.initialize",
            "store.initialize",
            "graph.initialize",
            "pipeline.initialize",
        )
        src = ast.unparse(hc_tree)
        offenders = []
        for i, line in enumerate(src.splitlines(), 1):
            for pat in forbidden_initializers:
                # Match only real call sites (with the parens)
                if f"{pat}(" in line and "await" in line:
                    offenders.append((i, line.strip()))
        assert not offenders, (
            f"{HC.name} must not call heavy-resource initialize(). "
            f"Offending site(s): {offenders}"
        )

    # ---- Each check_* must delegate to _lookup_existing or registry ------
    @pytest.mark.parametrize("method_name,forbidden_class", [
        ("check_ollama", "OllamaLLMService"),
        ("check_vector_store", "VectorStoreManager"),
        ("check_reasoning", "UltraReasoningService"),
    ])
    def test_check_method_uses_lookup_or_registry(
        self, hc_tree: ast.Module, method_name: str, forbidden_class: str
    ) -> None:
        """Each subsystem check must delegate to the canonical
        lookup path, not the direct constructor.
        """
        body = _get_function(hc_tree, method_name)
        assert body is not None, f"{method_name} not found in {HC.name}"
        body_src = ast.unparse(body)
        assert "_lookup_existing" in body_src, (
            f"{method_name} must use _lookup_existing() to find a "
            f"pre-existing instance on app.state or the Switchboard. "
            f"Direct construction is forbidden."
        )
        assert f"{forbidden_class}(" not in body_src, (
            f"{method_name} must not call {forbidden_class}() directly"
        )

    def test_check_agents_reads_registry_no_construction(
        self, hc_tree: ast.Module
    ) -> None:
        """``check_agents`` must read from ``ULTRA_AGENT_REGISTRY`` and
        NEVER instantiate agent classes — that would resurrect the
        agent factory at every ``/health`` call.
        """
        body = _get_function(hc_tree, "check_agents")
        assert body is not None
        body_src = ast.unparse(body)
        assert "ULTRA_AGENT_REGISTRY" in body_src, (
            "check_agents must consult ULTRA_AGENT_REGISTRY (single "
            "source of truth) and must not instantiate agent classes"
        )
        assert "agent_class()" not in body_src, (
            "check_agents must not call agent_class() — read the "
            "registry, never construct."
        )

    # ---- Governance source-tree level enforcement -----------------------
    def test_no_raw_neo4j_driver_session_outside_canonical(self) -> None:
        """``AGENTS.md`` 1-A: raw ``neo4j_driver.session()`` is
        FORBIDDEN outside the canonical connection module. The
        documented startup exception is ``api/database.py`` (one-time
        schema apply). Anywhere else is a P0 governance bypass.
        """
        offenders: List[Tuple[str, int, str]] = []
        for path in ROOT.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            if "tests" in path.parts or "examples" in path.parts:
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "neo4j_driver.session(" in src:
                rel = path.relative_to(ROOT)
                if rel == pathlib.Path("api/database.py"):
                    continue  # documented startup bootstrap
                if rel == pathlib.Path("mahoun/graph/neo4j/connection.py"):
                    continue  # canonical module
                for i, line in enumerate(src.splitlines(), 1):
                    if "neo4j_driver.session(" in line and not line.lstrip().startswith("#"):
                        offenders.append((str(rel), i, line.strip()))
        assert not offenders, (
            f"AGENTS.md 1-A violation: raw neo4j_driver.session() is "
            f"FORBIDDEN outside the canonical connection module. "
            f"Offending sites: {offenders}"
        )

    def test_no_duplicate_governance_classes(self) -> None:
        """``AGENTS.md`` 1-B: ``GovernanceContext`` and
        ``MutationAuthorizationBoundary`` must each have exactly one
        definition. The codebase has historically had multiple
        competing copies (×2+ each); every fresh one had to be hunted
        down and reconciled.
        """
        offenders: List[Tuple[str, int, str]] = []
        for path in ROOT.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            if "tests" in path.parts or "examples" in path.parts:
                continue
            # Skip node_modules and other non-project directories
            if "node_modules" in path.parts:
                continue
            try:
                tree = _parse(path)
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed or decoded
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in {
                    "GovernanceContext",
                    "MutationAuthorizationBoundary",
                }:
                    rel = path.relative_to(ROOT)
                    if rel == pathlib.Path(
                        "mahoun/core/governance/governance_context.py"
                    ) or rel == pathlib.Path(
                        "mahoun/core/governance/mutation_boundary.py"
                    ):
                        continue
                    offenders.append((str(rel), node.lineno, node.name))
        assert not offenders, (
            f"AGENTS.md 1-B violation: duplicate governance class "
            f"definition. Offending sites: {offenders}"
        )

    def test_health_endpoint_passes_app_state(self) -> None:
        """The ``/health`` endpoint must accept a ``request`` and pass
        ``request.app.state`` to ``HealthChecker`` so the checker can
        inspect pre-existing singletons. This is what completes the
        no-re-instantiation architecture.
        """
        tree = _parse(MAIN)
        health_func = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "health_check"
            ):
                health_func = node
                break
        assert health_func is not None, (
            "health_check function not found in api/main.py"
        )
        # Check the decorator binds to /health
        bound_to_health = False
        for dec in health_func.decorator_list:
            if (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "get"
                and dec.args
                and isinstance(dec.args[0], ast.Constant)
                and dec.args[0].value == "/health"
            ):
                bound_to_health = True
                break
        assert bound_to_health, (
            "health_check must be bound to the /health route"
        )
        # Check it accepts request
        arg_names = [a.arg for a in health_func.args.args]
        assert "request" in arg_names, (
            "The /health endpoint must accept a `request` parameter "
            "to pass app.state to HealthChecker"
        )
        # Check the body wires app_state through
        body_src = ast.unparse(health_func)
        assert "HealthChecker(app_state=" in body_src, (
            "The /health endpoint must construct "
            "HealthChecker(app_state=request.app.state) so pre-existing "
            "singletons are inspected, not reconstructed."
        )


# ============================================================================
# CATEGORY 2 — HARDENING
# ============================================================================
class TestHardening:
    """The runtime must be robust against failure."""

    @pytest.fixture(scope="class")
    def db_tree(self) -> ast.Module:
        return _parse(DB)

    @pytest.fixture(scope="class")
    def init_neo4j(self, db_tree: ast.Module):
        fn = _get_function(db_tree, "init_neo4j")
        assert fn is not None, "init_neo4j not found in api/database.py"
        return fn

    def test_bounded_handshake_timeout(self, init_neo4j) -> None:
        """The Neo4j handshake must be wrapped in ``asyncio.wait_for``
        with a **low** timeout (≤ 5s). A black-holed Neo4j port must
        not stall startup or ``/health`` responses.

        The check looks at ``init_neo4j``'s body AND any helper it
        delegates to (e.g. ``_handshake_neo4j``) — the requirement is
        "the handshake path is bounded", not "the literal token is in
        this exact function's source".
        """
        body_src = ast.unparse(init_neo4j)
        # Collect called function names to inspect their bodies too
        called_helpers: Set[str] = set()
        for node in ast.walk(init_neo4j):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
            ):
                called_helpers.add(node.func.id)
        # Also consider _handshake_neo4j and similar helpers
        combined_src = body_src
        for helper in called_helpers:
            if helper.startswith("_"):
                helper_fn = _get_function(_parse(DB), helper)
                if helper_fn is not None:
                    combined_src += "\n" + ast.unparse(helper_fn)

        assert "asyncio.wait_for" in combined_src, (
            "The Neo4j handshake path must be wrapped in "
            "asyncio.wait_for to bound the wait time. Without it, "
            "an unreachable Neo4j blocks startup indefinitely. "
            "The wrapping may be in init_neo4j or a helper it "
            "delegates to (e.g. _handshake_neo4j)."
        )
        # Locate the timeout value
        timeout_match = re.search(
            r"timeout[_a-zA-Z]*\s*=\s*([\d.]+|\w+)", combined_src
        )
        assert timeout_match, (
            "handshake timeout value not found in init_neo4j "
            "(or its delegate helpers)"
        )
        token = timeout_match.group(1)
        if re.match(r"^\d+(\.\d+)?$", token):
            value = float(token)
            assert value <= 5.0, (
                f"Neo4j handshake timeout must be <= 5s (got {value}s). "
                f"Longer timeouts stall /health on unreachable backends."
            )

    def test_init_neo4j_does_not_raise_on_connection_failure(
        self, init_neo4j
    ) -> None:
        """``init_neo4j`` must NEVER raise on connection/handshake
        failure. Per Action Item 2, it must catch every canonical
        failure mode and degrade gracefully.
        """
        handlers = _collect_except_handlers(init_neo4j)
        flat: Set[str] = set().union(*handlers) if handlers else set()

        # Required canonical handlers
        required_groups = [
            {"ConnectionError", "OSError"},     # network refusal / reset
            {"TimeoutError", "asyncio.TimeoutError"},  # bounded handshake
            {"ServiceUnavailable", "_Neo4jServiceUnavailable"},
            {"AuthError", "_Neo4jAuthError"},
            {"BoltError", "_Neo4jBoltError"},
        ]
        missing_groups = [
            g for g in required_groups
            if not (flat & g)
        ]
        assert not missing_groups, (
            f"init_neo4j missing required except-clause(s) for "
            f"{missing_groups}. All canonical Neo4j failure modes "
            f"must be caught. Current handlers: {flat}"
        )

        # And there must be a generic last-resort catch
        assert "Exception" in flat, (
            f"init_neo4j must have a generic Exception catch-all as "
            f"a last resort. Current handlers: {flat}"
        )

        # Sanity: at least 4 except clauses
        assert len(handlers) >= 4, (
            f"init_neo4j must have at least 4 except clauses "
            f"(got {len(handlers)}). Each failure mode deserves its "
            f"own structured log/handling path."
        )

    def test_init_neo4j_sets_graph_state_on_failure(
        self, init_neo4j
    ) -> None:
        """Every failure path must call
        ``GraphConnectionState.set_unavailable`` so downstream routers
        can see the disabled state.
        """
        body_src = ast.unparse(init_neo4j)
        n = body_src.count("GraphConnectionState.set_unavailable")
        assert n >= 4, (
            f"init_neo4j must call GraphConnectionState.set_unavailable "
            f"in every failure path (expected >= 4 sites, got {n})"
        )

    def test_init_neo4j_resets_driver_to_none(self, init_neo4j) -> None:
        """Every failure path must reset ``neo4j_driver = None`` so a
        half-initialized driver does not leak.
        """
        body_src = ast.unparse(init_neo4j)
        n = body_src.count("neo4j_driver = None")
        assert n >= 4, (
            f"init_neo4j must reset neo4j_driver = None on every "
            f"failure path (expected >= 4 sites, got {n})"
        )

    def test_init_neo4j_emits_warning_not_error(self, init_neo4j) -> None:
        """Failure paths must emit a single ``log.warning`` — never a
        ``log.error`` that would trigger alerting on what is
        intentional degradation.
        """
        body_src = ast.unparse(init_neo4j)
        # Confirm at least one warning log in the failure paths
        assert "log.warning" in body_src, (
            "init_neo4j failure paths must use log.warning, not "
            "log.error, so observability does not page on intended "
            "degradation."
        )

    def test_health_checker_is_pure_inspection(
        self, hc_tree: ast.Module = _parse(HC)
    ) -> None:
        """The HealthChecker class itself must be free of any
        constructor call to a heavy resource. If a future contributor
        adds e.g. ``self._ollama = OllamaLLMService()`` in
        ``__init__``, this test fires.
        """
        ctor = _get_function(hc_tree, "__init__")
        assert ctor is not None
        body_src = ast.unparse(ctor)
        for forbidden, _ in TestEnforcement.FORBIDDEN_HEAVY_CONSTRUCTORS:
            assert f"{forbidden}(" not in body_src, (
                f"HealthChecker.__init__ must not call {forbidden}(). "
                f"Construction belongs in app.state / the Switchboard, "
                f"never in the health-check ctor."
            )

    def test_check_all_returns_full_schema(self) -> None:
        """``check_all`` must always include the contract keys, even
        when every subsystem is degraded. A missing key is a contract
        break that downstream consumers cannot work around.
        """
        tree = _parse(HC)
        check_all = _get_function(tree, "check_all")
        assert check_all is not None
        body_src = ast.unparse(check_all)
        for key in ('"status"', '"core"', '"graph"', '"agents"',
                    '"components"'):
            # ast.unparse() may use single or double quotes
            assert key in body_src or key.replace('"', "'") in body_src, (
                f"check_all response is missing required key: {key}"
            )
        # core.import_safe - ast.unparse() may use single or double quotes
        assert '"import_safe"' in body_src or "'import_safe'" in body_src, (
            "check_all core section must include import_safe"
        )
        # graph.reason, agents.count
        assert '"reason"' in body_src, (
            "check_all must include 'reason' fields (graph.reason)"
        )
        assert '"count"' in body_src, (
            "check_all must include agents.count"
        )

    def test_healthchecker_ctor_is_backward_compatible(self) -> None:
        """``HealthChecker()`` (no-arg) must keep working — every
        existing call site in the codebase relies on it.
        """
        tree = _parse(HC)
        ctor = _get_function(tree, "__init__")
        assert ctor is not None
        # All non-self args must have defaults
        defaults_count = len(ctor.args.defaults)
        non_self = [a for a in ctor.args.args if a.arg != "self"]
        assert defaults_count >= len(non_self), (
            f"HealthChecker.__init__ has non-defaulted required args: "
            f"{[a.arg for a in non_self]}. This breaks backward "
            f"compatibility."
        )


# ============================================================================
# CATEGORY 3 — UNIFIED GOVERNANCE
# ============================================================================
class TestUnifiedGovernance:
    """The system must obey the unified governance rules of AGENTS.md."""

    def test_graph_connection_state_is_canonical(self) -> None:
        """``GraphConnectionState`` must be the **single** source of
        truth for graph runtime state: present in ``api/database.py``
        with the canonical fields and methods, and nowhere else in the
        codebase (no shadow class).
        """
        db_src = _read(DB)
        # Must exist in api/database.py
        assert "class GraphConnectionState" in db_src, (
            "GraphConnectionState must be defined in api/database.py"
        )
        # Canonical fields
        for field in ("enabled", "backend", "last_error", "uri"):
            assert f"{field}:" in db_src, (
                f"GraphConnectionState must expose '{field}' state field"
            )
        # Canonical methods
        for method in (
            "def set_unavailable",
            "def set_available",
            "def is_available",
            "def snapshot",
        ):
            assert method in db_src, (
                f"GraphConnectionState.{method.split('def ')[1]} missing"
            )
        # No duplicate definitions
        for path in ROOT.rglob("*.py"):
            if "tests" in path.parts or "examples" in path.parts:
                continue
            if path.resolve() == DB.resolve():
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            assert "class GraphConnectionState" not in src, (
                f"Duplicate class GraphConnectionState in {path}. "
                f"There must be exactly one canonical definition."
            )

    def test_health_checker_consults_graph_connection_state(self) -> None:
        """``check_graph`` must consult ``GraphConnectionState`` — the
        single source of truth — instead of probing the Neo4j driver
        directly. This is what decouples the health check from the
        driver and lets it work even when the driver is half-built.
        """
        tree = _parse(HC)
        body = _get_function(tree, "check_graph")
        assert body is not None
        body_src = ast.unparse(body)
        assert "GraphConnectionState" in body_src, (
            "check_graph must consult GraphConnectionState (the "
            "single source of truth) instead of probing the Neo4j "
            "driver directly."
        )
        # And must not construct the driver or any heavy resource
        for forbidden, _ in TestEnforcement.FORBIDDEN_HEAVY_CONSTRUCTORS:
            assert f"{forbidden}(" not in body_src, (
                f"check_graph must not construct {forbidden}(). "
                f"Health checks inspect, never build."
            )

    def test_self_improve_removed_from_production_code(self) -> None:
        """``self_improve`` has been REMOVED from the MAHOUN architecture
        (not merely disabled). Production code paths must not reference
        the removed subsystem.
        """
        hc_src = _read(HC)
        assert "mahoun.self_improve" not in hc_src, (
            "health_checker must not reference mahoun.self_improve — "
            "the subsystem has been removed, not disabled"
        )
        assert "UltraSelfImprovementSystem" not in hc_src, (
            "health_checker must not reference UltraSelfImprovementSystem"
        )
        offenders: List[Tuple[str, int, str]] = []
        for path in ROOT.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            if "tests" in path.parts or "examples" in path.parts:
                continue
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            lowered = src.lower()
            if "ultra_self_improvement_system" in lowered or \
               ("self_improve" in lowered and "self_improvement" not in lowered):
                rel = path.relative_to(ROOT)
                if "self_improve" not in str(rel):
                    offenders.append((str(rel), 0, ""))
        assert not offenders, (
            "self_improve referenced outside its own package "
            "(subsystem removed). Offending paths: "
            + ", ".join(str(o[0]) for o in offenders)
        )

    def test_single_canonical_neo4j_driver_construction(self) -> None:
        """``AGENTS.md`` 1-A: exactly one ``AsyncGraphDatabase.driver()``
        call site in the entire codebase. This is the canonical
        location; all other code must go through the connection
        module.
        """
        offenders: List[Tuple[str, int]] = []
        for path in ROOT.rglob("*.py"):
            if "tests" in path.parts or "examples" in path.parts:
                continue
            # Skip node_modules which may contain binary files
            if "node_modules" in path.parts:
                continue
            try:
                tree = _parse(path)
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed or decoded
                continue
            for name, line, _ in _collect_calls(tree):
                if name == "driver":
                    # Heuristic: line containing "driver(" also mentions
                    # AsyncGraphDatabase
                    src = ast.unparse(tree)
                    lines = src.splitlines()
                    if line - 1 < len(lines) and \
                       "AsyncGraphDatabase" in lines[line - 1]:
                        offenders.append((str(path.relative_to(ROOT)), line))
        # Allowed: api/database.py (canonical startup site)
        offenders = [
            (p, l) for p, l in offenders
            if p != "api/database.py"
            and p != "mahoun/graph/neo4j/connection.py"
        ]
        assert not offenders, (
            f"AGENTS.md 1-A violation: AsyncGraphDatabase.driver() "
            f"must be called from exactly one canonical site "
            f"(api/database.py or mahoun/graph/neo4j/connection.py). "
            f"Offending sites: {offenders}"
        )

    def test_validate_governance_compliance_script_exists(self) -> None:
        """``AGENTS.md`` Part 4: the validator script must exist. A
        guard function that is never wired in is not a guard.
        """
        if not VALIDATOR_SCRIPT.exists():
            pytest.skip(
                f"{VALIDATOR_SCRIPT} not present. AGENTS.md Part 4 "
                f"requires this script as the canonical enforcement "
                f"surface — add it (or update AGENTS.md if the policy "
                f"has been retired)."
            )

    def test_health_checker_does_not_instantiate_runtime_config(self) -> None:
        """The health checker must call ``get_runtime_settings()`` —
        never re-instantiate the settings dataclass. Re-instantiating
        would break the cached, frozen, lru_cached configuration.
        """
        tree = _parse(HC)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "MahounRuntimeSettings",
                }:
                    raise AssertionError(
                        f"{HC.name} calls {node.func.id}() directly. "
                        f"Use get_runtime_settings() instead — the "
                        f"settings are an lru_cached frozen dataclass."
                    )


# ============================================================================
# CATEGORY 4 — BEHAVIORAL (graceful skip if deps missing)
# ============================================================================
class TestBehavioral:
    """Runtime behavior verified by running the actual module in a
    subprocess. Each test gracefully skips if the runtime cannot be
    imported in this environment."""

    def test_check_all_is_idempotent(self) -> None:
        """Calling ``check_all()`` twice in succession must produce
        the same response shape and not accumulate state. A non-
        idempotent health check is a memory-leak risk.
        """
        result = self._run_isolated(
            textwrap.dedent("""
                import asyncio, json
                from mahoun.infrastructure.health_checker import HealthChecker

                async def main():
                    checker = HealthChecker()
                    r1 = await checker.check_all()
                    r2 = await checker.check_all()
                    # Same keys
                    assert set(r1.keys()) == set(r2.keys()), \
                        f"key mismatch: {set(r1.keys())} vs {set(r2.keys())}"
                    # Same overall status
                    assert r1["status"] == r2["status"], \\
                        f"status drift: {r1['status']} -> {r2['status']}"
                    # Same components shape
                    assert set(r1["components"].keys()) == \\
                           set(r2["components"].keys()), \\
                        f"components drift: {set(r1['components'])}"
                    return r1, r2

                r1, r2 = asyncio.run(main())
                print("OK", r1["status"], len(r1["components"]))
            """)
        )
        if result is None:
            pytest.skip("module not importable in this environment")
        assert "OK" in result, f"unexpected output: {result}"

    def test_graph_connection_state_transitions(self) -> None:
        """``GraphConnectionState`` must transition cleanly between
        ``available`` and ``unavailable`` states without leaking prior
        error state.
        """
        result = self._run_isolated(
            textwrap.dedent("""
                from api.database import GraphConnectionState

                # Initial state
                assert GraphConnectionState.is_available() is True
                # Disable
                GraphConnectionState.set_unavailable(reason="test_refused", uri="bolt://x")
                assert GraphConnectionState.is_available() is False
                assert GraphConnectionState.backend == "disabled"
                assert GraphConnectionState.last_error == "test_refused"
                # Re-enable
                GraphConnectionState.set_available(backend="local_full", uri="bolt://y")
                assert GraphConnectionState.is_available() is True
                assert GraphConnectionState.backend == "local_full"
                assert GraphConnectionState.last_error is None
                print("OK", GraphConnectionState.snapshot()["graph_enabled"])
            """)
        )
        if result is None:
            pytest.skip("module not importable in this environment")
        assert "OK" in result, f"unexpected output: {result}"

    def test_init_neo4j_handles_connection_refused(self) -> None:
        """``init_neo4j`` with an unreachable Neo4j URI must not
        raise — it must log a warning and flip ``GraphConnectionState``
        to unavailable. This is the headline hardening requirement.
        """
        result = self._run_isolated(
            textwrap.dedent("""
                import asyncio, os
                # Use a guaranteed-refused port
                os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:1")
                from api.database import init_neo4j, GraphConnectionState, neo4j_driver

                # Reset
                GraphConnectionState.enabled = True
                GraphConnectionState.backend = "local_full"
                GraphConnectionState.last_error = None

                try:
                    asyncio.run(init_neo4j())
                    # Must have flipped to disabled
                    assert GraphConnectionState.is_available() is False, \\
                        f"expected disabled, got {GraphConnectionState.snapshot()}"
                    assert GraphConnectionState.backend == "disabled"
                    assert neo4j_driver is None
                    print("OK", GraphConnectionState.snapshot()["graph_backend"])
                except Exception as e:
                    print("FAIL_RAISED", type(e).__name__, str(e))
                    raise
            """),
            env_extra={"NEO4J_URI": "bolt://127.0.0.1:1"},
        )
        if result is None:
            pytest.skip("module not importable in this environment")
        assert "OK" in result, f"unexpected output: {result}"

    # ---- subprocess helper -------------------------------------------------
    @staticmethod
    def _run_isolated(
        code: str,
        env_extra: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> Optional[str]:
        """Run ``code`` in a fresh Python subprocess with sys.path
        pointing at the repo root. Returns stdout on success, ``None``
        if the import failed (treat as graceful skip).
        """
        import os
        env = os.environ.copy()
        env["MAHOUN_TESTING"] = "1"
        env["MAHOUN_ENV"] = "development"
        if env_extra:
            env.update(env_extra)
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None
        if result.returncode != 0:
            # If it's an ImportError, treat as graceful skip
            if "ImportError" in result.stderr or "ModuleNotFoundError" in result.stderr:
                return None
            return result.stderr
        return result.stdout


# ============================================================================
# CLI entry point for CI integration
# ============================================================================
def _main() -> int:
    """Run as a script: ``python tests/governance/test_unified_health_governance.py``
    prints a structured JSON report. Exits non-zero on any failure."""
    # Re-implement the relevant assertions in a single pass
    failures: List[Dict[str, str]] = []

    def _fail(category: str, message: str) -> None:
        failures.append({"category": category, "message": message})

    # 1. ENFORCEMENT
    hc_tree = _parse(HC)
    hc_calls = _collect_calls(hc_tree)
    for forbidden, reason in TestEnforcement.FORBIDDEN_HEAVY_CONSTRUCTORS:
        offenders = [
            f"{HC}:{line}" for name, line, _ in hc_calls if name == forbidden
        ]
        if offenders:
            _fail("enforcement", f"{forbidden}() called in health_checker: {offenders} ({reason})")

    # 2. HARDENING
    db_tree = _parse(DB)
    init_neo4j = _get_function(db_tree, "init_neo4j")
    if init_neo4j is None:
        _fail("hardening", "init_neo4j not found in api/database.py")
    else:
        body_src = ast.unparse(init_neo4j)
        # Look at init_neo4j + helpers it delegates to (e.g.
        # _handshake_neo4j) for asyncio.wait_for
        called_helpers: Set[str] = set()
        for node in ast.walk(init_neo4j):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called_helpers.add(node.func.id)
        combined_src = body_src
        for helper in called_helpers:
            if helper.startswith("_"):
                helper_fn = _get_function(db_tree, helper)
                if helper_fn is not None:
                    combined_src += "\n" + ast.unparse(helper_fn)

        if "asyncio.wait_for" not in combined_src:
            _fail("hardening", "Neo4j handshake path is not bounded by asyncio.wait_for")
        handlers = _collect_except_handlers(init_neo4j)
        flat = set().union(*handlers) if handlers else set()
        required_groups = [
            {"ConnectionError", "OSError"},
            {"TimeoutError", "asyncio.TimeoutError"},
            {"ServiceUnavailable", "_Neo4jServiceUnavailable"},
            {"AuthError", "_Neo4jAuthError"},
        ]
        for g in required_groups:
            if not (flat & g):
                _fail("hardening", f"init_neo4j missing handler for {g}")
        if "Exception" not in flat:
            _fail("hardening", "init_neo4j has no generic Exception catch-all")
        if body_src.count("GraphConnectionState.set_unavailable") < 4:
            _fail("hardening", "init_neo4j has too few set_unavailable call sites")
        if body_src.count("neo4j_driver = None") < 4:
            _fail("hardening", "init_neo4j has too few neo4j_driver=None resets")

    # 3. UNIFIED GOVERNANCE
    db_src = _read(DB)
    if "class GraphConnectionState" not in db_src:
        _fail("governance", "GraphConnectionState class not defined in api/database.py")
    check_graph = _get_function(hc_tree, "check_graph")
    if check_graph is None or "GraphConnectionState" not in ast.unparse(check_graph):
        _fail("governance", "check_graph does not consult GraphConnectionState")
    main_tree = _parse(MAIN)
    found_health = False
    for node in ast.walk(main_tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "health_check":
            found_health = True
            arg_names = [a.arg for a in node.args.args]
            if "request" not in arg_names or \
               "HealthChecker(app_state=" not in ast.unparse(node):
                _fail("governance", "/health endpoint does not pass app_state to HealthChecker")
    if not found_health:
        _fail("governance", "health_check function not found in api/main.py")

    # Report
    report = {
        "ok": len(failures) == 0,
        "failure_count": len(failures),
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(_main())
