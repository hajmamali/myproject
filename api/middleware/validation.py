"""
Input Validation Middleware
============================
FastAPI middleware for automatic input validation and sanitization.

This middleware:
- Validates all incoming requests
- Sanitizes string inputs
- Logs validation failures
- Returns clear error messages
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mahoun.core.exceptions import ValidationError
from mahoun.core.validation import StringSanitizer

logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input validation and sanitization.

    Applied to all API requests to ensure security.
    """

    # Path prefixes that skip validation (health checks, metrics, docs)
    SKIP_PATH_PREFIXES = (
        "/health",
        "/metrics",
        "/system/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    )

    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with validation.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        start_time = time.time()

        # Skip validation for certain path prefixes
        if request.url.path.startswith(self.SKIP_PATH_PREFIXES):
            return await call_next(request)

        try:
            # Validate request
            await self._validate_request(request)

            # Process request
            response = await call_next(request)

            # Log successful request
            duration_ms = (time.time() - start_time) * 1000
            logger.debug(
                f"Request validated: {request.method} {request.url.path} "
                f"({duration_ms:.2f}ms)"
            )

            return response

        except ValidationError as e:
            # Log validation failure
            logger.warning(
                f"Validation failed: {request.method} {request.url.path} - {e}"
            )

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "validation_error",
                    "message": str(e),
                    "path": request.url.path,
                },
            )

        except Exception as e:
            # Log unexpected error
            logger.error(
                f"Validation middleware error: {request.method} {request.url.path}",
                exc_info=True,
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "internal_error",
                    "message": "Request validation failed",
                },
            )

    async def _validate_request(self, request: Request) -> None:
        """
        Validate incoming request.

        Args:
            request: HTTP request to validate

        Raises:
            ValidationError: If validation fails
        """
        # Validate headers
        self._validate_headers(request)

        # Validate query parameters
        self._validate_query_params(request)

        # Validate path parameters
        self._validate_path_params(request)

        # Validate body size (if applicable)
        if request.method in ("POST", "PUT", "PATCH"):
            await self._validate_body_size(request)

    def _validate_headers(self, request: Request) -> None:
        """
        Validate request headers.

        Args:
            request: HTTP request

        Raises:
            ValidationError: If headers are invalid
        """
        # Check Content-Type for POST/PUT/PATCH
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")

            # Must have content-type
            if not content_type:
                raise ValidationError("Missing Content-Type header")

            # Check for valid content types
            valid_types = [
                "application/json",
                "multipart/form-data",
                "application/x-www-form-urlencoded",
            ]

            if not any(ct in content_type.lower() for ct in valid_types):
                raise ValidationError(f"Unsupported Content-Type: {content_type}")

        # Validate User-Agent (optional but recommended)
        user_agent = request.headers.get("user-agent", "")
        if user_agent:
            # Check for suspicious patterns
            if StringSanitizer.check_command_injection(user_agent):
                raise ValidationError("Invalid User-Agent header")

    def _validate_query_params(self, request: Request) -> None:
        """
        Validate query parameters.

        Args:
            request: HTTP request

        Raises:
            ValidationError: If query params are invalid
        """
        # Limit number of query parameters
        if len(request.query_params) > 50:
            raise ValidationError("Too many query parameters (max: 50)")

        # Validate each parameter
        for key, value in request.query_params.items():
            # Check key length
            if len(key) > 100:
                raise ValidationError(f"Query parameter key too long: {key}")

            # Check value length
            if len(value) > 1000:
                raise ValidationError(f"Query parameter value too long: {key}")

            # Check for injection patterns
            if StringSanitizer.check_sql_injection(value):
                raise ValidationError(f"Invalid query parameter: {key}")

            if StringSanitizer.check_command_injection(value):
                raise ValidationError(f"Invalid query parameter: {key}")

    def _validate_path_params(self, request: Request) -> None:
        """
        Validate path parameters.

        Args:
            request: HTTP request

        Raises:
            ValidationError: If path params are invalid
        """
        path = request.url.path

        # Check for path traversal
        if StringSanitizer.check_path_traversal(path):
            raise ValidationError("Invalid path: path traversal detected")

        # Check path length
        if len(path) > 500:
            raise ValidationError("Path too long")

        # Check for null bytes
        if "\x00" in path:
            raise ValidationError("Invalid path: null byte detected")

    async def _validate_body_size(self, request: Request) -> None:
        """
        Validate request body size.

        Args:
            request: HTTP request

        Raises:
            ValidationError: If body is too large
        """
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_BODY_SIZE:
                    raise ValidationError(
                        f"Request body too large: {size} bytes "
                        f"(max: {self.MAX_BODY_SIZE})"
                    )
            except ValueError:
                raise ValidationError("Invalid Content-Length header")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.

    Prevents abuse by limiting requests per IP.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}  # IP -> [(timestamp, count)]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.window_seconds}s",
                },
            )

        # Process request
        return await call_next(request)

    def _check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if client is within rate limit.

        Args:
            client_ip: Client IP address

        Returns:
            True if within limit, False otherwise
        """
        current_time = time.time()

        # Clean old entries
        if client_ip in self._requests:
            self._requests[client_ip] = [
                (ts, count)
                for ts, count in self._requests[client_ip]
                if current_time - ts < self.window_seconds
            ]

        # Count requests in current window
        if client_ip not in self._requests:
            self._requests[client_ip] = []

        request_count = sum(count for _, count in self._requests[client_ip])

        # Check limit
        if request_count >= self.max_requests:
            return False

        # Add current request
        self._requests[client_ip].append((current_time, 1))

        return True
