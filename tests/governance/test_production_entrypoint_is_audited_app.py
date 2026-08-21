"""
v5.1 Integrity Closure — BL-1 deploy-time enforcement.

This test exists to make the "Certification Surface == Execution Surface"
invariant CI-enforced. The production container MUST run the exact same
governed application that the test suite imports (api.main:app). A regression
that reintroduces a divergent, locally-defined FastAPI app in the container
entrypoint (the historical start-api.py divergence) must fail this test.

It does NOT require building the container: it statically asserts that the
container entrypoint targets api.main:app AND that api.main:app is actually
the governed application (GovernanceContextMiddleware installed).
"""

import os

import pytest


def _repo_root() -> str:
    # tests/governance/ -> repo root (3 levels up)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def _user_middleware_classes(app):
    # FastAPI stores Starlette Middleware objects in app.user_middleware;
    # the real class is on the `.cls` attribute.
    return {getattr(mw, "cls", type(mw)) for mw in getattr(app, "user_middleware", [])}


def test_api_main_is_the_governed_application():
    """api.main:app must be importable and install GovernanceContextMiddleware."""
    from api.main import app
    from api.middleware.governance_context import GovernanceContextMiddleware

    classes = _user_middleware_classes(app)
    assert GovernanceContextMiddleware in classes, (
        "api.main does not install GovernanceContextMiddleware — the audited "
        "application is not governed. BL-1 regression."
    )


def test_dockerfile_entrypoint_targets_api_main():
    """The production container entrypoint must run api.main:app, not a divergent app."""
    dockerfile = os.path.join(_repo_root(), "Dockerfile.api")
    assert os.path.exists(dockerfile), "Dockerfile.api missing"

    with open(dockerfile, "r", encoding="utf-8") as fh:
        content = fh.read()

    assert "api.main:app" in content, (
        "Dockerfile.api does not target 'api.main:app'. Production would run a "
        "divergent application (Certification Surface != Execution Surface). BL-1."
    )

    # The historical divergence used uvicorn.run("start-api:app", ...).
    assert 'uvicorn.run("start-api:app"' not in content, (
        "Dockerfile.api still launches the locally-defined 'start-api:app' instead "
        "of the canonical governed application. BL-1 regression."
    )
