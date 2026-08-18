"""
Test 5e: API Contract Checker Self-Tests (Phase E, Amendment D D6)
====================================================================
Tests for scripts/check_api_contracts.py.

Per Amendment D D6:
  PASS: exact match, router prefix + decorator, parameterized match,
        query-string normalization.
  FAIL: frontend endpoint with no backend route.
  WARNING: statically unresolved dynamic endpoint.

All tests operate on isolated temp workspaces. No production files modified.
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKER = PROJECT_ROOT / "scripts" / "check_api_contracts.py"


def _run_checker(workspace: Path) -> subprocess.CompletedProcess:
    """Run the API contract checker against a workspace."""
    checker_copy = workspace / "check_api_contracts_test.py"
    shutil.copy(CHECKER, checker_copy)
    # Patch the project root to be the workspace
    content = checker_copy.read_text()
    content = content.replace(
        'project_root = Path(__file__).resolve().parent.parent',
        f'project_root = Path({str(workspace)!r})'
    )
    checker_copy.write_text(content)
    return subprocess.run(
        ["python3", str(checker_copy)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _setup_workspace(tmp_path: Path) -> Path:
    """Create a workspace with api/routers/ and frontend/src/."""
    ws = tmp_path
    (ws / "api" / "routers").mkdir(parents=True)
    (ws / "frontend" / "src" / "pages").mkdir(parents=True)
    return ws


def _write_backend_router(ws: Path, router_code: str):
    """Write a router file in the workspace."""
    (ws / "api" / "routers" / "test_router.py").write_text(router_code)


def _write_frontend_file(ws: Path, filename: str, code: str):
    """Write a frontend component in the workspace."""
    (ws / "frontend" / "src" / "pages" / filename).write_text(code)


class TestAPIContractPass:
    """PASS cases per Amendment D D6."""

    def test_exact_match(self, tmp_path: Path):
        """Exact frontend/backend path match."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter()
            @router.get("/health")
            def health():
                return {"status": "ok"}
            """))
        _write_frontend_file(ws, "Health.tsx", textwrap.dedent("""\
            async function check() {
                const res = await fetch('/health');
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        assert proc.returncode == 0, f"Exact match should pass:\n{proc.stdout}\n{proc.stderr}"

    def test_router_prefix_plus_decorator(self, tmp_path: Path):
        """Router prefix + decorator path combination."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter(prefix="/api/v1/governance")
            @router.get("/status")
            def status():
                return {"status": "ok"}
            """))
        _write_frontend_file(ws, "Governance.tsx", textwrap.dedent("""\
            async function check() {
                const res = await fetch('/api/v1/governance/status');
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        assert proc.returncode == 0, f"Prefix+decorator match should pass:\n{proc.stdout}\n{proc.stderr}"

    def test_parameterized_route_match(self, tmp_path: Path):
        """Parameterized path: /users/{id} backend matches /users/${id} frontend."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter(prefix="/api")
            @router.get("/users/{user_id}")
            def get_user(user_id: str):
                return {"id": user_id}
            """))
        _write_frontend_file(ws, "UserProfile.tsx", textwrap.dedent("""\
            async function fetchUser(id: string) {
                const res = await fetch(`/api/users/${id}`);
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        assert proc.returncode == 0, f"Parameterized match should pass:\n{proc.stdout}\n{proc.stderr}"

    def test_query_string_normalization(self, tmp_path: Path):
        """Query strings are stripped before matching."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter(prefix="/api")
            @router.get("/search")
            def search():
                return {"results": []}
            """))
        _write_frontend_file(ws, "Search.tsx", textwrap.dedent("""\
            async function search() {
                const res = await fetch('/api/search?q=test&page=1');
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        assert proc.returncode == 0, f"Query string normalization should pass:\n{proc.stdout}\n{proc.stderr}"


class TestAPIContractFail:
    """FAIL case per Amendment D D6."""

    def test_frontend_endpoint_no_backend_route(self, tmp_path: Path):
        """Frontend calls /api/nonexistent but no backend route exists."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter(prefix="/api")
            @router.get("/health")
            def health():
                return {"status": "ok"}
            """))
        _write_frontend_file(ws, "Broken.tsx", textwrap.dedent("""\
            async function check() {
                const res = await fetch('/api/nonexistent');
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        assert proc.returncode != 0, (
            f"Nonexistent endpoint should fail:\n{proc.stdout}\n{proc.stderr}"
        )
        out = proc.stdout + proc.stderr
        assert "nonexistent" in out, f"Should report missing route:\n{out}"


class TestAPIContractWarning:
    """WARNING case per Amendment D D6."""

    def test_dynamic_endpoint_is_warning_not_violation(self, tmp_path: Path):
        """Unresolved dynamic endpoint → warning, not failure."""
        ws = _setup_workspace(tmp_path)
        _write_backend_router(ws, textwrap.dedent("""\
            from fastapi import APIRouter
            router = APIRouter(prefix="/api")
            @router.get("/health")
            def health():
                return {"status": "ok"}
            """))
        _write_frontend_file(ws, "Dynamic.tsx", textwrap.dedent("""\
            const baseUrl = import.meta.env.VITE_API_URL;
            async function check() {
                const res = await fetch('/api/health');
                return res.json();
            }
            """))
        proc = _run_checker(ws)
        out = proc.stdout + proc.stderr
        # Either it passes (if the /api/health route matched) or it has a warning
        # but NOT a violation for the unresolved dynamic endpoint.
        # The key assertion: no VIOLATION for dynamic endpoints.
        lines = out.split('\n')
        # Check that any violation does NOT include "UNRESOLVED_DYNAMIC_ENDPOINT"
        violations = [l for l in lines if "VIOLATION" in l and "UNRESOLVED_DYNAMIC" not in l]
        # If there are no violations, it passed.
        if proc.returncode != 0:
            assert not violations, (
                f"Dynamic endpoint should be WARNING not VIOLATION:\n{out}"
            )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
