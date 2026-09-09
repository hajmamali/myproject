"""Canonical pre-extraction execution gate for specialized ingestion."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator


class IngestionExecutionDenied(PermissionError):
    """Raised when ingestion starts without a canonical execution context."""


@dataclass(frozen=True, slots=True)
class IngestionExecutionRequest:
    """Identity and contract metadata required before extraction begins."""

    source: str
    author_id: str
    correlation_id: str
    adapter_name: str
    contract_version: str = "1"


@dataclass(frozen=True, slots=True)
class IngestionExecutionPermit:
    """Immutable permit held for the lifetime of one ingestion execution."""

    request: IngestionExecutionRequest


_active_permit: ContextVar[IngestionExecutionPermit | None] = ContextVar(
    "mahoun_ingestion_execution_permit",
    default=None,
)


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise IngestionExecutionDenied(
            f"ingestion execution requires a non-empty {field_name}"
        )


def _validate_request(request: IngestionExecutionRequest) -> None:
    for field_name in (
        "source",
        "author_id",
        "correlation_id",
        "adapter_name",
        "contract_version",
    ):
        _require_text(getattr(request, field_name), field_name)


class IngestionExecutionGate:
    """Single canonical gate that must be entered before extraction."""

    @staticmethod
    @contextmanager
    def enter(
        request: IngestionExecutionRequest,
    ) -> Iterator[IngestionExecutionPermit]:
        _validate_request(request)
        if _active_permit.get() is not None:
            raise IngestionExecutionDenied(
                "nested ingestion execution contexts are not allowed"
            )

        permit = IngestionExecutionPermit(request=request)
        token: Token[IngestionExecutionPermit | None] = _active_permit.set(
            permit
        )
        try:
            yield permit
        finally:
            _active_permit.reset(token)

    @staticmethod
    def require_active() -> IngestionExecutionPermit:
        permit = _active_permit.get()
        if permit is None:
            raise IngestionExecutionDenied(
                "No Gate -> No Extraction -> No Ingestion"
            )
        return permit
