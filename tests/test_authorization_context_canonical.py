"""
Identity regression test for the single _authorized_write_ctx ContextVar.

This complements tests/test_authorization_state_singleton.py by exercising
the in-canonical-module guard `assert_no_duplicate_contextvar()` directly
with a forged second ContextVar injected into a consumer module's
namespace. It proves the guard FIRES (RuntimeError) when a duplicate
appears, so a future regression that accidentally reintroduces a
local `_authorized_write_ctx` redefinition in `kernel.py` or
`mutation_boundary.py` will fail loudly at runtime rather than silently
split-braining.

Together with tests/test_authorization_state_singleton.py.p0 tests this
closes the "duplicate ContextVar detection" ratchet for Issue 3 of the
remediation pass (consolidating the four authorization-boundary
implementations down to ONE canonical ContextVar).
"""

import contextvars

import pytest


def test_canonical_contextvar_identity_across_consumers():
    """kernel, mutation_boundary (and the shim) must share ONE ContextVar."""
    from mahoun.core.governance_kernel.kernel import _authorized_write_ctx as k
    from mahoun.core.governance.mutation_boundary import _authorized_write_ctx as m
    from mahoun.core.governance.authorization_state import _authorized_write_ctx as s
    from mahoun.core.governance_kernel.authorization_state import (
        _authorized_write_ctx as canonical,
    )

    assert k is canonical, "kernel.py uses a non-canonical ContextVar"
    assert m is canonical, "mutation_boundary.py uses a non-canonical ContextVar"
    assert s is canonical, "authorization_state shim lost the canonical ref"
    assert k is m, "kernel and mutation_boundary split-brain on auth state"


def test_duplicate_contextvar_guard_fires_for_kernel():
    """If kernel.py redefines _authorized_write_ctx the guard raises."""
    import mahoun.core.governance_kernel.authorization_state as canonical_mod
    import mahoun.core.governance_kernel.kernel as kernel_mod

    forged = contextvars.ContextVar("forged_kernel_ctx", default=False)
    original = getattr(kernel_mod, "_authorized_write_ctx", None)
    kernel_mod._authorized_write_ctx = forged
    try:
        with pytest.raises(RuntimeError, match="DUPLICATE _authorized_write_ctx"):
            canonical_mod._assert_no_duplicate_contextvar()
    finally:
        if original is not None:
            kernel_mod._authorized_write_ctx = original
        else:
            del kernel_mod._authorized_write_ctx
    # guard now passes again
    canonical_mod._assert_no_duplicate_contextvar()


def test_duplicate_contextvar_guard_fires_for_mutation_boundary():
    """If mutation_boundary.py redefines _authorized_write_ctx the guard raises."""
    import mahoun.core.governance_kernel.authorization_state as canonical_mod
    import mahoun.core.governance.mutation_boundary as mb_mod

    forged = contextvars.ContextVar("forged_mb_ctx", default=False)
    original = mb_mod._authorized_write_ctx
    mb_mod._authorized_write_ctx = forged
    try:
        with pytest.raises(RuntimeError, match="DUPLICATE _authorized_write_ctx"):
            canonical_mod._assert_no_duplicate_contextvar()
    finally:
        mb_mod._authorized_write_ctx = original
    canonical_mod._assert_no_duplicate_contextvar()


def test_governance_boundary_roundtrip_after_consolidation():
    """End-to-end: set auth in the canonical module → boundary sees True."""
    from mahoun.core.governance_kernel.authorization_state import (
        set_authorized,
        reset_authorized,
        is_authorized,
    )
    from mahoun.core.governance.mutation_boundary import _is_authorized

    assert is_authorized() is False
    assert _is_authorized() is False, "boundary sees auth True when canonical is False"
    token = set_authorized(True)
    try:
        assert is_authorized() is True
        assert _is_authorized() is True, (
            "boundary split-brain: canonical set True but boundary still False"
        )
    finally:
        reset_authorized(token)
    assert is_authorized() is False
    assert _is_authorized() is False
