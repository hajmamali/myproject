"""
Tests for GovernanceContextMiddleware API Wiring
=================================================

Classification: CRITICAL REGRESSION TESTS (Issue 1)
Purpose: Verify GovernanceContextMiddleware is registered on the real FastAPI
app from api.main and properly populates request.state.governance_context
for reasoning endpoints without raising RuntimeError.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.governance_context import GovernanceContextMiddleware, get_governance_context
from mahoun.core.governance.governance_context import GovernanceContextManager


@pytest.fixture
def real_app_client() -> TestClient:
    """TestClient using the REAL app instance from api.main (not a mock/custom app)."""
    return TestClient(app, raise_server_exceptions=True)


class TestGovernanceContextMiddlewareWiring:
    """Verify GovernanceContextMiddleware wiring on the real FastAPI app."""

    def test_middleware_is_registered_in_real_app(self):
        """Verify GovernanceContextMiddleware exists in app.user_middleware or middleware stack."""
        middleware_classes = [m.cls for m in app.user_middleware]
        assert GovernanceContextMiddleware in middleware_classes, (
            "GovernanceContextMiddleware is NOT registered in api.main app.user_middleware!"
        )

    def test_governance_context_populated_on_request(self, real_app_client: TestClient):
        """
        Verify that requests to the real app have request.state.governance_context
        populated by GovernanceContextMiddleware, and do NOT fail with
        'RuntimeError: GovernanceContext not found in request.state'.
        """
        corr_id = "test-corr-wire-real-999"
        actor_id = "test-user-wire-888"

        response = real_app_client.post(
            "/api/v1/reasoning/generate-verdict",
            json={
                "question": "Is notice valid under civil code?",
                "facts": [
                    {"value": "Notice served on 2024-01-10"},
                ],
                "generate_proof": False,
            },
            headers={
                "X-Correlation-ID": corr_id,
                "X-User-ID": actor_id,
            },
        )

        # The endpoint must NOT fail with 500 'GovernanceContext not found'
        # It proceeds to the reasoning engine and returns either 200 (success) or
        # deterministic 403 (Fortress RedLine security check), with correlation_id preserved.
        assert response.status_code in (200, 403), (
            f"Unexpected status {response.status_code}: {response.text}"
        )
        if response.status_code == 403:
            # Confirm the correlation_id from the header was in fact captured into GovernanceContext
            data = response.json()
            assert corr_id in data.get("message", "") or data.get("correlation_id") == corr_id

    def test_skip_paths_bypass_governance_context_gracefully(self, real_app_client: TestClient):
        """Verify skip paths like /health execute normally."""
        response = real_app_client.get("/health")
        assert response.status_code == 200
