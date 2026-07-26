"""
Pytest configuration for API integration tests.
This file provides fixtures and patches for tests that need to bypass
production middleware like TrustedHostMiddleware.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="session", autouse=True)
def patch_trusted_host_middleware():
    """
    Patch TrustedHostMiddleware to allow all hosts during testing.
    This is needed because TestClient doesn't send proper host headers.
    """
    import starlette.middleware.trustedhost as trustedhost_module
    
    # Patch the __call__ method to always allow
    original_call = trustedhost_module.TrustedHostMiddleware.__call__
    
    def patched_call(self, request):
        # Skip host validation for tests
        return request
    
    with patch.object(trustedhost_module.TrustedHostMiddleware, '__call__', patched_call):
        yield
