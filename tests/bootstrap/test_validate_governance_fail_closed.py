"""Test fail-closed enforcement in bootstrap_runtime()"""
import pytest
from unittest.mock import patch
from mahoun.bootstrap.runtime import bootstrap_runtime, clear_registry, validate_governance_runtime

class TestFailClosed:
    def test_bootstrap_fails_when_audit_sink_missing(self):
        """bootstrap_runtime() must raise RuntimeError when audit sink missing"""
        clear_registry()
        with patch('mahoun.core.governance.mutation_boundary.get_audit_sink', return_value=None):
            with pytest.raises(RuntimeError, match='Governance runtime invalid'):
                bootstrap_runtime()
        clear_registry()

    def test_validate_governance_fails_when_audit_sink_missing(self):
        """validate_governance_runtime() must raise RuntimeError when audit sink missing"""
        with patch('mahoun.core.governance.mutation_boundary.get_audit_sink', return_value=None):
            with pytest.raises(RuntimeError, match='Governance runtime invalid'):
                validate_governance_runtime()
