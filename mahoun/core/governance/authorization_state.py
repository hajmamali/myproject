"""
Canonical Authorization State
=============================

Classification: KERNEL / CONSTITUTIONAL / SINGLE SOURCE OF TRUTH

This module defines the single canonical _authorized_write_ctx ContextVar.
Any module that needs to read or write mutation authorization state MUST import from this module.
"""

from contextvars import ContextVar, Token
import sys

_authorized_write_ctx: ContextVar[bool] = ContextVar(
    "_authorized_write_ctx", default=False
)

def is_authorized() -> bool:
    return _authorized_write_ctx.get()

def set_authorized(state: bool) -> Token[bool]:
    return _authorized_write_ctx.set(state)

def reset_authorized(token: Token[bool]) -> None:
    _authorized_write_ctx.reset(token)

def _assert_no_duplicate_contextvar() -> None:
    """Fail fast if a second _authorized_write_ctx ContextVar is alive."""
    # Check sys.modules for any other module defining it
    for name, mod in list(sys.modules.items()):
        if mod is getattr(sys.modules.get(__name__), "__module__", None):
            continue
        other = getattr(mod, "_authorized_write_ctx", None)
        if other is not None and other is not _authorized_write_ctx:
            raise RuntimeError(f"DUPLICATE _authorized_write_ctx ContextVar detected in {name}")

__all__ = [
    "_authorized_write_ctx",
    "is_authorized",
    "set_authorized",
    "reset_authorized",
    "_assert_no_duplicate_contextvar",
]
