"""
P0/P1 Tests: Audit Sink Fail-Closed Constitutional Fix
=======================================================

Tests that verify:
1. P0: _append_governance_audit raises GovernanceViolationError when sink is None
2. P0: _append_governance_audit raises GovernanceViolationError when sink.append() fails
3. P0: _append_governance_audit succeeds when sink is properly wired
4. P1: validate_governance_runtime() raises RuntimeError when sink is missing
5. P1: validate_governance_runtime() succeeds when sink is configured

These are CONSTITUTIONAL tests — they verify kernel-level governance invariants.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from mahoun.core.governance.mutation_boundary import (
    _append_governance_audit,
    get_audit_sink,
    set_audit_sink,
    unset_audit_sink,
)
from mahoun.core.governance.violations import GovernanceViolationError, ViolationCategory
from mahoun.bootstrap.runtime import validate_governance_runtime


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_audit_sink():
    """Ensure audit sink is unset before and after each test."""
    original = get_audit_sink()
    unset_audit_sink()
    yield
    # Restore original state
    if original is not None:
        set_audit_sink(original)
    else:
        unset_audit_sink()


def _make_null_sink():
    """Create a no-op audit sink that records appends."""
    sink = MagicMock()
    sink.append = MagicMock(return_value=None)
    return sink


def _make_failing_sink(error_msg: str = "Disk full"):
    """Create a sink that always fails on append."""
    sink = MagicMock()
    sink.append = MagicMock(side_effect=OSError(error_msg))
    return sink


# ---------------------------------------------------------------------------
# P0 Tests: _append_governance_audit fail-closed
# ---------------------------------------------------------------------------

class TestAuditSinkFailClosed:
    """P0: _append_governance_audit must raise when sink is not wired."""

    @pytest.mark.p2
    def test_missing_sink_raises_governance_violation(self):
        """P0: Audit append with no sink wired must raise GovernanceViolationError."""
        assert get_audit_sink() is None, "Precondition: sink must be None"

        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"operation": "test", "entity": "test-node"})

        violation = exc_info.value.violation
        assert violation.category == ViolationCategory.AUDIT_FAILURE
        assert "AUDIT SINK NOT WIRED" in violation.message
        assert "set_audit_sink" in violation.message or "set_audit_sink" in str(violation.details)

    @pytest.mark.p2
    def test_missing_sink_error_is_actionable(self):
        """P0: Error message must contain actionable hint for operators."""
        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"operation": "test"})

        # The error must be actionable — not just "error occurred"
        error_text = str(exc_info.value)
        assert any(hint in error_text for hint in [
            "set_audit_sink",
            "validate_governance_runtime",
            "bootstrap",
        ]), f"Error message must contain actionable hint, got: {error_text}"

    @pytest.mark.p2
    def test_configured_sink_succeeds(self):
        """P0: Audit append with properly wired sink must succeed."""
        sink = _make_null_sink()
        set_audit_sink(sink)

        entry = {"operation": "write_node", "entity_id": "node-123", "label": "Law"}
        # Must not raise
        _append_governance_audit(entry)

        sink.append.assert_called_once_with(entry)

    @pytest.mark.p2
    def test_configured_sink_receives_full_entry(self):
        """P0: Sink must receive the exact audit entry provided."""
        sink = _make_null_sink()
        set_audit_sink(sink)

        entry = {
            "timestamp": "2026-07-15T00:00:00Z",
            "correlation_id": "corr-test-123",
            "actor_id": "test-actor",
            "operation": "write_node",
            "label": "Statute",
            "entity_id": "statute-001",
        }
        _append_governance_audit(entry)

        sink.append.assert_called_once()
        called_entry = sink.append.call_args[0][0]
        assert called_entry == entry

    @pytest.mark.p2
    def test_failing_sink_raises_governance_violation(self):
        """P0: Sink append failure must raise GovernanceViolationError (fail-closed)."""
        sink = _make_failing_sink("Disk quota exceeded")
        set_audit_sink(sink)

        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"operation": "test"})

        violation = exc_info.value.violation
        assert violation.category == ViolationCategory.AUDIT_FAILURE
        assert "FAILED" in violation.message or "failed" in violation.message.lower()

    @pytest.mark.p2
    def test_failing_sink_preserves_original_exception(self):
        """P0: GovernanceViolationError must chain from the original sink error."""
        original_error = OSError("Storage backend unavailable")
        sink = MagicMock()
        sink.append = MagicMock(side_effect=original_error)
        set_audit_sink(sink)

        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"operation": "test"})

        # Exception must be chained
        assert exc_info.value.__cause__ is original_error

    @pytest.mark.p2
    def test_unset_sink_after_set_raises_again(self):
        """P0: After unset_audit_sink(), append must raise again (regression guard)."""
        sink = _make_null_sink()
        set_audit_sink(sink)
        unset_audit_sink()

        with pytest.raises(GovernanceViolationError):
            _append_governance_audit({"operation": "test"})

    @pytest.mark.p2
    def test_multiple_appends_with_wired_sink(self):
        """P0: Multiple appends with a single wired sink must all succeed."""
        sink = _make_null_sink()
        set_audit_sink(sink)

        entries = [
            {"operation": "write_node", "entity_id": f"node-{i}"}
            for i in range(10)
        ]
        for entry in entries:
            _append_governance_audit(entry)

        assert sink.append.call_count == 10


# ---------------------------------------------------------------------------
# P1 Tests: validate_governance_runtime()
# ---------------------------------------------------------------------------

class TestValidateGovernanceRuntime:
    """P1: validate_governance_runtime() must catch missing sink at startup."""

    @pytest.mark.p2
    def test_missing_sink_fails_validation(self):
        """P1: validate_governance_runtime() must raise RuntimeError when sink is None."""
        assert get_audit_sink() is None, "Precondition: sink must be None"

        with pytest.raises(RuntimeError) as exc_info:
            validate_governance_runtime()

        error_msg = str(exc_info.value)
        assert "Audit sink missing" in error_msg or "audit sink" in error_msg.lower()

    @pytest.mark.p2
    def test_configured_sink_passes_validation(self):
        """P1: validate_governance_runtime() must pass when sink is properly wired."""
        sink = _make_null_sink()
        set_audit_sink(sink)

        # Must not raise
        validate_governance_runtime()

    @pytest.mark.p2
    def test_validation_error_is_runtime_error_not_governance_error(self):
        """P1: Startup validation must raise RuntimeError (not GovernanceViolationError).
        
        RuntimeError is appropriate for startup misconfiguration; 
        GovernanceViolationError is for runtime governance violations.
        """
        with pytest.raises(RuntimeError):
            validate_governance_runtime()

        # Explicitly verify it's NOT a GovernanceViolationError
        try:
            validate_governance_runtime()
        except GovernanceViolationError:
            pytest.fail(
                "validate_governance_runtime() raised GovernanceViolationError "
                "but should raise RuntimeError for startup misconfiguration"
            )
        except RuntimeError:
            pass  # Expected

    @pytest.mark.p2
    def test_validation_message_is_actionable(self):
        """P1: RuntimeError message must tell operator what to do."""
        with pytest.raises(RuntimeError) as exc_info:
            validate_governance_runtime()

        msg = str(exc_info.value)
        assert len(msg) > 20, "Error message must not be empty/trivial"
        # Must contain actionable guidance
        assert any(word in msg.lower() for word in [
            "audit", "sink", "set_audit_sink", "bootstrap", "missing", "wire"
        ]), f"Error message must be actionable, got: {msg}"

    @pytest.mark.p2
    def test_validation_passes_with_any_compliant_sink(self):
        """P1: Any object satisfying AuditSinkProtocol must pass validation."""
        class MinimalSink:
            def append(self, entry: dict) -> None:
                pass

        set_audit_sink(MinimalSink())
        validate_governance_runtime()  # Must not raise


# ---------------------------------------------------------------------------
# Integration: Audit sink interaction with GovernanceViolationError category
# ---------------------------------------------------------------------------

class TestAuditSinkViolationCategory:
    """Verify the correct ViolationCategory is used for audit failures."""

    @pytest.mark.p2
    def test_no_sink_uses_audit_failure_category(self):
        """Missing sink must use AUDIT_FAILURE category (not ARCHITECTURE_BOUNDARY)."""
        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"op": "test"})

        assert exc_info.value.violation.category == ViolationCategory.AUDIT_FAILURE

    @pytest.mark.p2
    def test_sink_failure_uses_audit_failure_category(self):
        """Sink append failure must use AUDIT_FAILURE category."""
        sink = _make_failing_sink()
        set_audit_sink(sink)

        with pytest.raises(GovernanceViolationError) as exc_info:
            _append_governance_audit({"op": "test"})

        assert exc_info.value.violation.category == ViolationCategory.AUDIT_FAILURE
