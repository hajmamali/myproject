"""
Authorization State — Re-export Shim (Tier-1 compatibility layer)
=================================================================

Classification: TIER-1 / RE-EXPORT SHIM / DO NOT REDEFINE

The CANONICAL OWNER of _authorized_write_ctx is:
    mahoun.core.governance_kernel.authorization_state  (Tier-0)

This module is a pure re-export shim that preserves backward compatibility
for all existing Tier-1/Tier-2 importers. It MUST NOT redefine the ContextVar
— the identity invariant requires exactly one object in the process:

    governance_kernel.authorization_state._authorized_write_ctx
        is
    governance.authorization_state._authorized_write_ctx  <- this module

Any importer of this module gets the same object as an importer of
governance_kernel.authorization_state. This is enforced at test time by
tests/test_authorization_context_canonical.py and
tests/test_authorization_state_singleton.py.

Change record: kernel_changes.yaml v1.1.0 (approved: architecture-team)
Migration documented: glmreport.md Section F, Section K Phase 1
"""

from mahoun.core.governance_kernel.authorization_state import (
    _authorized_write_ctx,
    is_authorized,
    set_authorized,
    reset_authorized,
    authorize_write,
    _assert_no_duplicate_contextvar,
)

# Canonical alias
is_governance_authorized = is_authorized

__all__ = [
    "_authorized_write_ctx",
    "is_authorized",
    "is_governance_authorized",
    "set_authorized",
    "reset_authorized",
    "authorize_write",
    "_assert_no_duplicate_contextvar",
]

