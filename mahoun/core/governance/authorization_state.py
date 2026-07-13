"""
Canonical Authorization State
==============================

Classification: KERNEL / CONSTITUTIONAL / SINGLE SOURCE OF TRUTH

This module is the ONE canonical definition of the mutation authorization
ContextVar. Both kernel.py and mutation_boundary.py import from here.

Invariant: There exists exactly one _authorized_write_ctx object in the
           entire process. Any module that needs to read or write mutation
           authorization state MUST import from this module.

A is B == True is enforced by tests/test_authorization_state_singleton.py
and by the CI gate in scripts/validate_governance_compliance.py.
"""

from contextvars import ContextVar, Token

# Single authoritative ContextVar for mutation authorization.
# Name kept as "authorized_write" (not "_authorized_write_ctx") to avoid
# confusion with the module-level names in legacy callers.
_authorized_write_ctx: ContextVar[bool] = ContextVar(
    "authorized_write",
    default=False,
)


def is_authorized() -> bool:
    """Return True only when executing inside GovernedNeo4jSession."""
    return _authorized_write_ctx.get()


def set_authorized(state: bool) -> Token:
    """Set authorization state and return token for reset."""
    return _authorized_write_ctx.set(state)


def reset_authorized(token: Token) -> None:
    """Reset authorization state to previous value via token."""
    _authorized_write_ctx.reset(token)
