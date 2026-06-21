"""
Tests for GovernanceLock
========================

Classification: CRITICAL SECURITY TESTS
Purpose: Verify GovernanceLock immutable governance enforcement

Test Coverage:
- Mode immutability
- Forensic logging
- Fail-closed behavior
- Cryptographic authorization
- Immutability verification
- Integration with existing code
"""

from datetime import UTC, datetime

import pytest

from mahoun.core.governance_lock import (
    GovernanceLock,
    GovernanceMode,
    SecurityError,
    check_governance_integrity,
    should_enforce_proof_carrying_contract,
)

# ============================================================================
# TESTS: Mode Immutability
# ============================================================================


class TestModeImmutability:
    """Tests that governance mode cannot be changed after initialization"""

    def test_initialization_sets_mode(self, reset_governance_lock):
        """Initialization should set the governance mode"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        assert GovernanceLock.get_mode() == GovernanceMode.STRICT
        assert GovernanceLock._initialized is True

    def test_second_initialization_raises_error(self, reset_governance_lock):
        """Second initialization attempt should raise RuntimeError"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        error_msg = str(exc_info.value)
        assert "already initialized" in error_msg.lower()
        assert "STRICT" in error_msg
        assert "AUDIT" in error_msg
        assert "change attempts" in error_msg.lower()

    def test_change_attempts_counter_increments(self, reset_governance_lock):
        """Change attempts counter should increment on each bypass attempt"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # First bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert GovernanceLock._change_attempts == 1

        # Second bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert GovernanceLock._change_attempts == 2

    def test_mode_cannot_be_changed_to_disabled(self, reset_governance_lock):
        """Mode cannot be changed to DISABLED after initialization"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert "already initialized" in str(exc_info.value).lower()

    def test_mode_cannot_be_changed_to_audit(self, reset_governance_lock):
        """Mode cannot be changed to AUDIT after initialization"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert "already initialized" in str(exc_info.value).lower()


# ============================================================================
# TESTS: Forensic Logging
# ============================================================================


class TestForensicLogging:
    """Tests that bypass attempts are logged with full forensic context"""

    def test_bypass_attempt_logs_mode_change(self, reset_governance_lock, capsys):
        """Bypass attempt should log current and requested modes"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        captured = capsys.readouterr()
        log_output = captured.out

        assert "CRITICAL" in log_output
        assert "Bypass attempt" in log_output
        assert "STRICT" in log_output
        assert "AUDIT" in log_output

    def test_bypass_attempt_logs_timestamp(self, reset_governance_lock, capsys):
        """Bypass attempt should log timestamp"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        captured = capsys.readouterr()
        log_output = captured.out

        assert "T" in log_output  # ISO 8601 date-time separator
        assert ":" in log_output  # Time separator

    def test_audit_metadata_contains_bypass_attempts(self, reset_governance_lock):
        """Audit metadata should contain detailed bypass attempt information"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make multiple bypass attempts
        for _ in range(3):
            with pytest.raises(RuntimeError):
                GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        metadata = GovernanceLock.get_audit_metadata()

        assert metadata["change_attempts"] == 3
        assert "bypass_attempts" in metadata
        assert len(metadata["bypass_attempts"]) == 3

        for attempt in metadata["bypass_attempts"]:
            assert "attempt_number" in attempt
            assert "timestamp" in attempt
            assert "blocked" in attempt
            assert attempt["blocked"] is True


# ============================================================================
# TESTS: Fail-Closed Behavior
# ============================================================================


class TestFailClosed:
    """Tests that system fails-closed when governance is not initialized"""

    def test_uninitialized_default_to_strict(self, reset_governance_lock):
        """Uninitialized lock should default to STRICT mode"""
        GovernanceLock._reset()

        mode = GovernanceLock.get_mode()

        assert mode == GovernanceMode.STRICT

    def test_uninitialized_enforcement_enabled(self, reset_governance_lock):
        """Uninitialized lock should have enforcement enabled (fail-closed)"""
        GovernanceLock._reset()

        enforcement_enabled = GovernanceLock.is_enforcement_enabled()

        assert enforcement_enabled is True

    def test_check_governance_integrity_uninitialized(self, reset_governance_lock):
        """Integrity check on uninitialized lock should indicate issue"""
        GovernanceLock._reset()

        metadata = GovernanceLock.get_audit_metadata()

        assert metadata["initialized"] is False
        assert metadata["mode"] == "UNINITIALIZED"
        assert metadata["integrity_verified"] is False


# ============================================================================
# TESTS: Cryptographic Authorization
# ============================================================================


class TestDisabledModeAuthorization:
    """Tests that DISABLED mode requires cryptographic authorization"""

    def test_disabled_mode_without_token_raises_error(self, reset_governance_lock):
        """DISABLED mode without token should raise SecurityError"""
        GovernanceLock._reset()

        with pytest.raises(SecurityError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED)

        assert "authorization" in str(exc_info.value).lower()

    def test_disabled_mode_with_valid_token_succeeds(self, reset_governance_lock):
        """DISABLED mode with valid token should succeed"""
        GovernanceLock._reset()

        # Generate valid token for today
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        expected_input = f"MAHOUN_DEV_OVERRIDE_{today}"
        import hashlib

        valid_token = hashlib.sha256(expected_input.encode()).hexdigest()

        GovernanceLock.initialize(mode=GovernanceMode.DISABLED, authorization_token=valid_token)

        assert GovernanceLock.get_mode() == GovernanceMode.DISABLED

    def test_disabled_mode_with_invalid_token_raises_error(self, reset_governance_lock):
        """DISABLED mode with invalid token should raise SecurityError"""
        GovernanceLock._reset()

        with pytest.raises(SecurityError) as exc_info:
            GovernanceLock.initialize(mode=GovernanceMode.DISABLED, authorization_token="invalid_token")

        assert "authorization" in str(exc_info.value).lower()


# ============================================================================
# TESTS: Immutability Verification
# ============================================================================


class TestImmutabilityVerification:
    """Tests for verify_immutable method"""

    def test_verify_immutable_on_valid_lock(self, reset_governance_lock):
        """verify_immutable should return True on valid lock"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        assert GovernanceLock.verify_immutable() is True

    def test_verify_immutable_after_bypass_attempt(self, reset_governance_lock):
        """verify_immutable should return False after bypass attempt"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make a bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert GovernanceLock.verify_immutable() is False

    def test_verify_immutable_after_reset(self, reset_governance_lock):
        """verify_immutable should return False after reset"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        GovernanceLock._reset()

        assert GovernanceLock.verify_immutable() is False


# ============================================================================
# TESTS: Integration with Existing Code
# ============================================================================


class TestIntegration:
    """Tests for integration with existing code"""

    def test_check_governance_integrity_with_bypass_attempts(self, reset_governance_lock):
        """check_governance_integrity should include bypass attempts in alert"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Make a bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        metadata = check_governance_integrity()

        assert "alert" in metadata
        assert "bypass attempts" in metadata.get("alert", "").lower()
        assert "bypass_attempts" in metadata

    def test_should_enforce_proof_carrying_contract_fails_closed(self, reset_governance_lock):
        """should_enforce_proof_carrying_contract should fail-closed"""
        # Reset to uninitialized state
        GovernanceLock._reset()

        # Should enforce (fail-closed)
        assert should_enforce_proof_carrying_contract() is True

        # Initialize and verify
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        assert should_enforce_proof_carrying_contract() is True

        # Make bypass attempt
        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        # Should still enforce (fail-closed on compromised lock)
        assert should_enforce_proof_carrying_contract() is True


# ============================================================================
# TESTS: Performance
# ============================================================================


class TestPerformance:
    """Tests for GovernanceLock performance"""

    def test_initialization_performance(self, reset_governance_lock):
        """Initialization should complete quickly"""
        import time

        start = time.time()
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        elapsed = time.time() - start

        assert elapsed < 0.01  # < 10ms

    def test_mode_check_performance(self, reset_governance_lock):
        """Mode check should complete quickly"""
        import time

        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        start = time.time()
        for _ in range(1000):
            GovernanceLock.get_mode()
        elapsed = time.time() - start

        assert elapsed < 0.1  # < 100ms for 1000 checks


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases"""

    def test_same_mode_reinitialization_raises_error(self, reset_governance_lock):
        """Reinitialization with same mode should still raise error"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        with pytest.raises(RuntimeError):
            GovernanceLock.initialize(mode=GovernanceMode.STRICT)

    def test_multiple_concurrent_initialization_attempts(self, reset_governance_lock):
        """Multiple concurrent initialization attempts should all fail"""
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)

        # Try multiple times
        for _ in range(10):
            with pytest.raises(RuntimeError):
                GovernanceLock.initialize(mode=GovernanceMode.AUDIT)

        assert GovernanceLock._change_attempts == 10
