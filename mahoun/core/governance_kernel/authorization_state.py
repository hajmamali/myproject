"""
Constitutional Tier-0 Authorization State
==========================================

Classification: KERNEL / TIER-0 / SINGLE SOURCE OF TRUTH

This module is the CANONICAL OWNER of the _authorized_write_ctx ContextVar.
It lives in governance_kernel (Tier-0) so the dependency boundary is correct:
  - governance_kernel (Tier-0) owns the primitive
  - governance/authorization_state.py is a re-export shim (Tier-1)

STDLIB ONLY — no external imports permitted per kernel.manifest.yaml §tier_0.

Every module that needs to read or write mutation authorization state MUST
ultimately resolve to this single object. Identity invariant:

    governance_kernel.authorization_state._authorized_write_ctx
        is
    governance.authorization_state._authorized_write_ctx
        is
    governance.mutation_boundary._authorized_write_ctx
        is
    governance_kernel.kernel._authorized_write_ctx

All four are the same Python object. Any divergence is caught by
_assert_no_duplicate_contextvar() which scans sys.modules at runtime.
"""

from __future__ import annotations

import sys
from contextvars import ContextVar, Token
from contextlib import contextmanager
from typing import Generator

# ============================================================================
# THE ONE CANONICAL ContextVar — defined EXACTLY ONCE in the entire process
# ============================================================================

_authorized_write_ctx: ContextVar[bool] = ContextVar(
    "_authorized_write_ctx", default=False
)


# ============================================================================
# PUBLIC API
# ============================================================================

def is_authorized() -> bool:
    """Return True if the current context has an active write authorization."""
    return _authorized_write_ctx.get()


def set_authorized(state: bool) -> "Token[bool]":
    """Set the authorization state; returns a Token for reset."""
    return _authorized_write_ctx.set(state)


def reset_authorized(token: "Token[bool]") -> None:
    """Reset authorization state to what it was before set_authorized()."""
    _authorized_write_ctx.reset(token)


@contextmanager
def authorize_write() -> "Generator[None, None, None]":
    """
    Context manager for temporarily authorizing write operations.

    Usage:
        with authorize_write():
            session.run("CREATE (n:Node)")
        # Authorization automatically cleared after exit
    """
    token = set_authorized(True)
    try:
        yield
    finally:
        reset_authorized(token)


# ============================================================================
# DUPLICATE-GUARD — fail fast if a second ContextVar appears anywhere
# ============================================================================

def _assert_no_duplicate_contextvar() -> None:
    """
    Scan sys.modules and raise RuntimeError if any mahoun module exposes a
    different _authorized_write_ctx object.

    This guard prevents the historical 4-implementation split-brain problem
    from recurring silently. It is invoked by the identity regression tests
    (tests/test_authorization_context_canonical.py,
     tests/test_authorization_state_singleton.py).

    A guard that is never called is not a guard — ensure the tests that call
    this function run in default CI.
    
    NOTE: Only checks mahoun.* modules to avoid false positives from
    third-party libraries (e.g., torch.ops) that may coincidentally have
    attributes with the same name.
    """
    for mod_name, mod in list(sys.modules.items()):
        # Only check mahoun modules (ignore third-party like torch, pytest, etc.)
        if not mod_name.startswith("mahoun."):
            continue
        other = getattr(mod, "_authorized_write_ctx", None)
        if other is not None and other is not _authorized_write_ctx:
            raise RuntimeError(
                f"DUPLICATE _authorized_write_ctx ContextVar detected in "
                f"mahoun module '{mod_name}'. Only "
                f"mahoun.core.governance_kernel.authorization_state may "
                f"define this symbol. All other modules must import it."
            )


# ============================================================================
# __all__
# ============================================================================

__all__ = [
    "_authorized_write_ctx",
    "is_authorized",
    "set_authorized",
    "reset_authorized",
    "authorize_write",
    "_assert_no_duplicate_contextvar",
]
