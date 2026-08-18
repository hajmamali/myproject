"""
Hardening and governance regression tests for the HealthChecker surface.

These tests intentionally focus on the production path:

* ``mahoun.infrastructure.health_checker.HealthChecker``
* ``mahoun.core.health_cache.CachedHealthChecker``
* ``api/routers/health_v2.py``

They exist to lock three invariants:

1. Public surface stays backward-compatible.
2. ``check_all()`` keeps the required response contract.
3. Cache wrappers / v2 routes do not bypass the canonical
   ``app.state``-inspection path.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

from mahoun.core.health_cache import CachedHealthChecker
from mahoun.infrastructure.health_checker import HealthChecker


ROOT = pathlib.Path(__file__).resolve().parents[2]
HC_PATH = ROOT / "mahoun" / "infrastructure" / "health_checker.py"
HC_CACHE_PATH = ROOT / "mahoun" / "core" / "health_cache.py"
HEALTH_V2_PATH = ROOT / "api" / "routers" / "health_v2.py"


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), str(path))


def _get_async_fn(tree: ast.Module, name: str) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Async function {name!r} not found in {tree}")


def _get_class_method(
    tree: ast.Module,
    class_name: str,
    method_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                    return item
            raise AssertionError(f"Method {method_name!r} not found in class {class_name!r}")
    raise AssertionError(f"Class {class_name!r} not found")


def test_healthchecker_public_surface_preserved() -> None:
    """No-arg construction and the public async surface must remain available."""
    checker = HealthChecker()

    assert hasattr(checker, "check_health")
    assert hasattr(checker, "check_all")
    assert hasattr(checker, "check_ollama")
    assert hasattr(checker, "check_vector_store")
    assert hasattr(checker, "check_graph")
    assert hasattr(checker, "check_reasoning")
    assert hasattr(checker, "check_agents")
    assert hasattr(checker, "check_refactored_modules")
    assert hasattr(checker, "check_databases")

    signature = inspect.signature(HealthChecker.__init__)
    params = signature.parameters
    assert params["app_state"].default is None
    assert params["switchboard_registry"].default is None


def test_cached_healthchecker_signature_extends_without_breaking_ctor() -> None:
    """Cache wrapper must stay backward-compatible while carrying app_state."""
    signature = inspect.signature(CachedHealthChecker.__init__)
    params = signature.parameters

    assert list(params) == [
        "self",
        "cache_ttl",
        "app_state",
        "switchboard_registry",
    ]
    assert params["cache_ttl"].default == 30.0
    assert params["app_state"].default is None
    assert params["switchboard_registry"].default is None

    checker = CachedHealthChecker()
    assert checker.app_state is None
    assert hasattr(checker, "cache")


def test_cached_healthchecker_forwards_canonical_lookup_context() -> None:
    """The cache wrapper must forward app_state/switchboard to HealthChecker."""
    tree = _parse(HC_CACHE_PATH)
    ctor = _get_class_method(tree, "CachedHealthChecker", "__init__")
    src = ast.unparse(ctor)

    assert "super().__init__(app_state=app_state, switchboard_registry=switchboard_registry)" in src


def test_check_all_contract_shape_is_statically_preserved() -> None:
    """Lock the response contract keys even before runtime mocking kicks in."""
    tree = _parse(HC_PATH)
    body = _get_async_fn(tree, "check_all")
    src = ast.unparse(body)
    normalized = src.replace('"', "'")

    for key in (
        "'status'",
        "'core'",
        "'graph'",
        "'agents'",
        "'components'",
        "'import_safe'",
        "'uptime_sec'",
        "'count'",
        "'reason'",
    ):
        assert key in normalized, f"missing contract key/token: {key}"


def test_health_v2_detailed_route_uses_request_app_state() -> None:
    """Detailed v2 route must preserve the no-re-instantiation path."""
    tree = _parse(HEALTH_V2_PATH)
    fn = _get_async_fn(tree, "detailed_health_check")
    src = ast.unparse(fn)
    arg_names = [arg.arg for arg in fn.args.args]

    assert "request" in arg_names
    assert "CachedHealthChecker(cache_ttl=cache_ttl, app_state=request.app.state)" in src


def test_health_v2_component_route_uses_request_app_state() -> None:
    """Component v2 route must preserve the no-re-instantiation path."""
    tree = _parse(HEALTH_V2_PATH)
    fn = _get_async_fn(tree, "component_health_check")
    src = ast.unparse(fn)
    arg_names = [arg.arg for arg in fn.args.args]

    assert "request" in arg_names
    assert "CachedHealthChecker(cache_ttl=cache_ttl, app_state=request.app.state)" in src
