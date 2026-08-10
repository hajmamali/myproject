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


class authorize_write:
    """
    Context manager for temporarily authorizing write operations.
    
    Usage:
        with authorize_write():
            # Write operations are authorized here
            session.run("CREATE (n:Node)")
        # Authorization automatically cleared after exit
    """
    
    def __init__(self):
        self.token: Token[bool] | None = None
    
    def __enter__(self):
        self.token = set_authorized(True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            reset_authorized(self.token)
        return False


__all__ = [
    "_authorized_write_ctx",
    "is_authorized",
    "set_authorized",
    "reset_authorized",
    "authorize_write",
    "_assert_no_duplicate_contextvar",
]
