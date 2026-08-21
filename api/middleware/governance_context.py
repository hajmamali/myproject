"""
Governance Context Middleware
==============================

FastAPI middleware that creates and injects GovernanceContext at API boundary.

ARCHITECTURE PRINCIPLE:
- GovernanceContext is created ONCE at API entry point
- Injected into request.state for downstream access
- Services receive context (never create it)
- Prevents God Object anti-pattern

This middleware ensures:
1. Every request has a governance context before processing
2. Context is propagated to all services via request.state
3. No service creates its own governance context
4. Full audit trail from API to storage

Part of: Phase 5 - Architecture Integration Mission
Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

import logging
import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from mahoun.core.governance.governance_context import GovernanceContextManager

logger = logging.getLogger(__name__)


class GovernanceContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that creates GovernanceContext at API boundary.

    CRITICAL ARCHITECTURE ROLE:
    - This is the ONLY place where GovernanceContext is created for API requests
    - All services downstream RECEIVE the context, never create it
    - Prevents RAG services from becoming God Objects
    - Ensures governance scope is active before any operation

    Flow:
        HTTP Request
            │
            ▼
        GovernanceContextMiddleware (creates context)
            │
            ▼
        request.state.governance_context (injected)
            │
            ▼
        Router → Container → Services (receive context)
    """

    # Paths that don't require governance context (health checks, metrics, docs)
    SKIP_PATH_PREFIXES = (
        "/health",
        "/metrics",
        "/system/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
    )

    # Execution mode based on environment
    DEFAULT_EXECUTION_MODE = "STRICT"

    def __init__(self, app, execution_mode: Optional[str] = None):
        """
        Initialize Governance Context Middleware.

        Args:
            app: FastAPI application
            execution_mode: Execution mode (STRICT, AUDIT, etc.). Defaults to STRICT.
        """
        super().__init__(app)
        self.execution_mode = execution_mode or self.DEFAULT_EXECUTION_MODE
        logger.info(f"GovernanceContextMiddleware initialized with mode: {self.execution_mode}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with governance context injection.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Skip governance context for certain paths
        if request.url.path.startswith(self.SKIP_PATH_PREFIXES):
            return await call_next(request)

        try:
            # Extract request metadata for governance context
            correlation_id = self._extract_correlation_id(request)
            actor_id = self._extract_actor_id(request)

            # v5.1 Integrity Closure (BL-6): activate the governance context on the
            # GovernanceContextManager ContextVar for the duration of the request so
            # that downstream enforcement (GovernedNeo4jSession.require_context / the
            # mutation boundary) actually sees it. Previously the context was only
            # stashed in request.state, making this middleware window-dressing rather
            # than the real enforcement point.
            async with GovernanceContextManager.active_context(
                correlation_id=correlation_id,
                execution_mode=self.execution_mode,
                actor_id=actor_id,
            ) as governance_context:
                # Inject into request.state for backward-compatible downstream access
                request.state.governance_context = governance_context

                logger.debug(
                    f"Governance context created: {governance_context.context_id} "
                    f"for {request.method} {request.url.path}"
                )

                # Process request with governance context
                response = await call_next(request)

                # Log successful processing
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(
                    f"Request processed with governance: {request.method} {request.url.path} "
                    f"({duration_ms:.2f}ms)"
                )

                return response

        except Exception as e:
            # Log governance context creation failure
            logger.error(
                f"Governance context creation failed: {request.method} {request.url.path}",
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "governance_context_error",
                    "message": "Failed to create governance context for request",
                    "path": request.url.path,
                },
            )

    def _extract_correlation_id(self, request: Request) -> str:
        """
        Extract or generate correlation ID from request.

        Priority:
        1. X-Correlation-ID header
        2. X-Request-ID header
        3. Generate new correlation ID

        Args:
            request: HTTP request

        Returns:
            Correlation ID string
        """
        # Check for existing correlation ID header
        correlation_id = request.headers.get("X-Correlation-ID")
        if correlation_id:
            return correlation_id

        # Check for request ID header
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            return request_id

        # Generate new correlation ID (will be created by GovernanceContextManager)
        return None

    def _extract_actor_id(self, request: Request) -> Optional[str]:
        """
        Extract actor ID from request for audit trail.

        Priority:
        1. X-User-ID header (if authenticated)
        2. X-API-Key-ID header (if API key auth)
        3. None (anonymous/unauthenticated)

        Args:
            request: HTTP request

        Returns:
            Actor ID string or None
        """
        # Check for authenticated user ID
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        # Check for API key ID
        api_key_id = request.headers.get("X-API-Key-ID")
        if api_key_id:
            return f"api-key:{api_key_id}"

        # No actor ID (anonymous)
        return None


def get_governance_context(request: Request):
    """
    Convenience function to extract governance context from request.

    Args:
        request: HTTP request with governance context

    Returns:
        GovernanceContext instance

    Raises:
        RuntimeError: If governance context not found in request
    """
    if not hasattr(request.state, "governance_context"):
        raise RuntimeError(
            "GovernanceContext not found in request.state. "
            "Ensure GovernanceContextMiddleware is registered."
        )

    return request.state.governance_context
