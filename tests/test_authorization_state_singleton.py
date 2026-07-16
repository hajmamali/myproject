"""
Authorization State Singleton Tests
=====================================

Enforces Invariant: There exists exactly ONE _authorized_write_ctx object.
kernel._authorized_write_ctx is mutation_boundary._authorized_write_ctx is True.

If this test fails, a duplicate ContextVar has been introduced and
authorization state can diverge — which is a governance violation.
"""

import pytest


@pytest.mark.p2
@pytest.mark.p0
def test_single_authorization_contextvar():
    """A is B is C — all three references point to the same object."""
    from mahoun.core.governance.authorization_state import _authorized_write_ctx as canonical
    from mahoun.core.governance_kernel import kernel
    from mahoun.core.governance import mutation_boundary

    assert kernel._authorized_write_ctx is canonical, (
        "kernel._authorized_write_ctx is NOT the canonical ContextVar. "
        "Duplicate authorization state detected."
    )
    assert mutation_boundary._authorized_write_ctx is canonical, (
        "mutation_boundary._authorized_write_ctx is NOT the canonical ContextVar. "
        "Duplicate authorization state detected."
    )
    assert kernel._authorized_write_ctx is mutation_boundary._authorized_write_ctx, (
        "kernel and mutation_boundary use different ContextVar objects. "
        "Authorization split-brain confirmed."
    )


@pytest.mark.p2
@pytest.mark.p0
def test_authorization_state_roundtrip_kernel_to_boundary():
    """Set via kernel helpers, read via mutation_boundary — must agree."""
    from mahoun.core.governance_kernel.kernel import (
        set_governance_authority,
        reset_governance_authority,
    )
    from mahoun.core.governance.mutation_boundary import _is_authorized

    assert not _is_authorized(), "Baseline: should be False"

    token = set_governance_authority(True)
    try:
        assert _is_authorized() is True, (
            "Set via kernel, boundary still reads False — split-brain."
        )
    finally:
        reset_governance_authority(token)

    assert not _is_authorized(), "After reset: should be False"


@pytest.mark.p2
@pytest.mark.p0
def test_authorization_state_roundtrip_boundary_to_kernel():
    """Set via authorization_state directly, read via kernel — must agree."""
    from mahoun.core.governance.authorization_state import set_authorized, reset_authorized
    from mahoun.core.governance_kernel.kernel import is_governance_authorized

    assert not is_governance_authorized(), "Baseline: should be False"

    token = set_authorized(True)
    try:
        assert is_governance_authorized() is True, (
            "Set via authorization_state, kernel still reads False — split-brain."
        )
    finally:
        reset_authorized(token)

    assert not is_governance_authorized(), "After reset: should be False"


@pytest.mark.p2
@pytest.mark.p0
def test_no_mutation_without_authorization():
    """MutationAuthorizationBoundary.inspect blocks mutation when unauthorized."""
    from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
    from mahoun.core.governance.violations import GovernanceViolationError

    with pytest.raises(GovernanceViolationError):
        MutationAuthorizationBoundary.inspect("MERGE (n:Test {id: $id})")


@pytest.mark.p2
@pytest.mark.p0
def test_mutation_passes_when_authorized():
    """MutationAuthorizationBoundary.inspect allows mutation when ctx_B is set."""
    from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
    from mahoun.core.governance.authorization_state import set_authorized, reset_authorized

    token = set_authorized(True)
    try:
        # Must NOT raise
        MutationAuthorizationBoundary.inspect("MERGE (n:Test {id: $id})")
    finally:
        reset_authorized(token)
