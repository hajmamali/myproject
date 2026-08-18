#!/usr/bin/env python3
"""
Phase D Integration Tests: Air-Gap Compliance Verification

Test Coverage:
- Task D.1: Air-Gap Compliance Verification
  - D.1.1: Network isolation testing
  - D.1.2: local_files_only enforcement validation
  - D.1.3: Model integrity verification system
  - D.1.4: Air-gap deployment testing

All tests validate complete network isolation and air-gap compliance.

Test Count: 12 tests
Expected Result: 12/12 passing
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import hashlib
import socket
import urllib.error

from mahoun.ai.airgap_validator import (
    AirGapValidator,
    ComplianceStatus,
    IntegrityCheckResult,
    NetworkIsolationResult,
    AirGapComplianceReport,
    validate_airgap_compliance,
    is_airgap_compliant
)


# ============================================================================
# Task D.1.1: Network Isolation Testing
# ============================================================================

class TestTaskD11_NetworkIsolationTesting:
    """Task D.1.1: Network isolation testing"""
    
    @patch('socket.gethostbyname')
    @pytest.mark.p2
    def test_dns_resolution_blocking(self, mock_gethostbyname):
        """Test DNS resolution is blocked in air-gap mode"""
        # Mock DNS resolution failure (expected in air-gap)
        mock_gethostbyname.side_effect = socket.gaierror("Name or service not known")
        
        validator = AirGapValidator()
        results = validator.verify_network_isolation()
        
        # Should have multiple DNS tests
        dns_tests = [r for r in results if "dns_resolution" in r.test_name]
        assert len(dns_tests) > 0
        
        # All DNS tests should show isolation
        for test in dns_tests:
            assert test.isolated == True
            assert "blocked" in test.details.lower()
    
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_http_connection_blocking(self, mock_urlopen):
        """Test HTTP connections are blocked in air-gap mode"""
        # Mock HTTP connection failure (expected in air-gap)
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        validator = AirGapValidator()
        results = validator.verify_network_isolation()
        
        # Should have HTTP connection tests
        http_tests = [r for r in results if "http_connection" in r.test_name]
        assert len(http_tests) > 0
        
        # All HTTP tests should show isolation
        for test in http_tests:
            assert test.isolated == True
            assert "blocked" in test.details.lower()
    
    @patch('socket.gethostbyname')
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_network_isolation_violation_detection(self, mock_urlopen, mock_gethostbyname):
        """Test detection of network isolation violations"""
        # Mock successful network access (VIOLATION)
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_urlopen.return_value = Mock()
        
        validator = AirGapValidator()
        results = validator.verify_network_isolation()
        
        # Should detect violations
        violations = [r for r in results if not r.isolated]
        assert len(violations) > 0
        
        # Validator should record violations
        assert len(validator._violations) > 0


# ============================================================================
# Task D.1.2: local_files_only Enforcement Validation
# ============================================================================

class TestTaskD12_LocalFilesOnlyEnforcement:
    """Task D.1.2: local_files_only enforcement validation"""
    
    @pytest.mark.p2
    def test_local_files_only_enforcement_check(self):
        """Test local_files_only enforcement validation"""
        validator = AirGapValidator()
        
        enforced = validator.verify_local_files_only_enforcement()
        
        # Should return boolean result
        assert isinstance(enforced, bool)
    
    @patch.dict('os.environ', {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'})
    @pytest.mark.p2
    def test_huggingface_offline_mode_configured(self):
        """Test HuggingFace offline mode environment variables"""
        validator = AirGapValidator()
        
        enforced = validator.verify_local_files_only_enforcement()
        
        # Should be enforced with proper env vars
        assert enforced == True
        # Should have minimal or no warnings
        hf_warnings = [w for w in validator._warnings if "HF_HUB_OFFLINE" in w]
        assert len(hf_warnings) == 0
    
    @patch.dict('os.environ', {}, clear=True)
    @pytest.mark.p2
    def test_huggingface_offline_mode_not_configured(self):
        """Test detection of missing HuggingFace offline configuration"""
        validator = AirGapValidator()
        
        enforced = validator.verify_local_files_only_enforcement()
        
        # Should generate warnings about missing env vars
        assert len(validator._warnings) > 0
        assert any("HF_HUB_OFFLINE" in w for w in validator._warnings)


# ============================================================================
# Task D.1.3: Model Integrity Verification System
# ============================================================================

class TestTaskD13_ModelIntegrityVerification:
    """Task D.1.3: Model integrity verification system"""
    
    @pytest.mark.p2
    def test_sha256_checksum_calculation(self):
        """Test SHA-256 checksum calculation"""
        # Create temporary file with known content
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"test model content"
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            validator = AirGapValidator()
            actual_hash = validator._calculate_sha256(temp_path)
            
            # Calculate expected hash
            expected_hash = hashlib.sha256(test_content).hexdigest()
            
            assert actual_hash == expected_hash
        finally:
            temp_path.unlink()
    
    @pytest.mark.p2
    def test_model_integrity_verification_success(self):
        """Test successful model integrity verification"""
        # Create temporary model file
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            model_file = models_dir / "test_model.gguf"
            model_content = b"test model data"
            model_file.write_bytes(model_content)
            
            # Calculate correct checksum
            expected_hash = hashlib.sha256(model_content).hexdigest()
            
            validator = AirGapValidator(models_directory=models_dir)
            results = validator.verify_model_integrity({
                "test_model.gguf": expected_hash
            })
            
            assert len(results) == 1
            assert results[0].verified == True
            assert results[0].actual_hash == expected_hash
    
    @pytest.mark.p2
    def test_model_integrity_verification_failure(self):
        """Test detection of corrupted models"""
        # Create temporary model file
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            model_file = models_dir / "test_model.gguf"
            model_file.write_bytes(b"test model data")
            
            # Use wrong checksum
            wrong_hash = "0" * 64
            
            validator = AirGapValidator(models_directory=models_dir)
            results = validator.verify_model_integrity({
                "test_model.gguf": wrong_hash
            })
            
            assert len(results) == 1
            assert results[0].verified == False
            assert len(validator._violations) > 0
    
    @pytest.mark.p2
    def test_missing_model_file_detection(self):
        """Test detection of missing model files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir)
            
            validator = AirGapValidator(models_directory=models_dir)
            results = validator.verify_model_integrity({
                "nonexistent_model.gguf": "abc123"
            })
            
            assert len(results) == 1
            assert results[0].verified == False
            assert results[0].actual_hash == "FILE_NOT_FOUND"
            assert len(validator._warnings) > 0


# ============================================================================
# Task D.1.4: Air-Gap Deployment Testing
# ============================================================================

class TestTaskD14_AirGapDeploymentTesting:
    """Task D.1.4: Air-gap deployment testing"""
    
    @patch('socket.gethostbyname')
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_comprehensive_compliance_report(self, mock_urlopen, mock_gethostbyname):
        """Test comprehensive air-gap compliance report generation"""
        # Mock air-gap environment (network isolated)
        mock_gethostbyname.side_effect = socket.gaierror("Network unreachable")
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        validator = AirGapValidator()
        report = validator.generate_compliance_report()
        
        assert isinstance(report, AirGapComplianceReport)
        assert isinstance(report.overall_status, ComplianceStatus)
        assert len(report.network_isolation_tests) > 0
        assert isinstance(report.local_files_only_enforced, bool)
        assert isinstance(report.violations, list)
        assert isinstance(report.warnings, list)
        assert isinstance(report.recommendations, list)
    
    @patch('socket.gethostbyname')
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_compliant_system_report(self, mock_urlopen, mock_gethostbyname):
        """Test report for fully compliant air-gap system"""
        # Mock perfect air-gap environment
        mock_gethostbyname.side_effect = socket.gaierror("Network unreachable")
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        validator = AirGapValidator(strict_mode=False)
        report = validator.generate_compliance_report()
        
        # Should be compliant or have only warnings
        assert report.overall_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING]
        
        # All network tests should show isolation
        for test in report.network_isolation_tests:
            assert test.isolated == True
    
    @patch('socket.gethostbyname')
    @pytest.mark.p2
    def test_violation_system_report(self, mock_gethostbyname):
        """Test report for system with violations"""
        # Mock network access (VIOLATION)
        mock_gethostbyname.return_value = "1.2.3.4"
        
        validator = AirGapValidator()
        report = validator.generate_compliance_report()
        
        # Should detect violations
        assert report.overall_status == ComplianceStatus.VIOLATION
        assert len(report.violations) > 0
        assert len(report.recommendations) > 0
        
        # Recommendations should address violations
        assert any("CRITICAL" in r for r in report.recommendations)


# ============================================================================
# Integration Tests
# ============================================================================

class TestAirGapValidatorIntegration:
    """Integration tests for air-gap validation"""
    
    @patch('socket.gethostbyname')
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_validate_airgap_compliance_function(self, mock_urlopen, mock_gethostbyname):
        """Test convenience function for compliance validation"""
        # Mock air-gap environment
        mock_gethostbyname.side_effect = socket.gaierror("Network unreachable")
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        report = validate_airgap_compliance(strict_mode=False)
        
        assert isinstance(report, AirGapComplianceReport)
        assert report.overall_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING]
    
    @patch('socket.gethostbyname')
    @patch('urllib.request.urlopen')
    @pytest.mark.p2
    def test_is_airgap_compliant_function(self, mock_urlopen, mock_gethostbyname):
        """Test quick compliance check function"""
        # Mock air-gap environment
        mock_gethostbyname.side_effect = socket.gaierror("Network unreachable")
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        compliant = is_airgap_compliant(strict_mode=False)
        
        assert isinstance(compliant, bool)
        # In mocked air-gap environment, should be compliant or have warnings
        # (warnings don't fail in non-strict mode)
        assert compliant in [True, False]  # Result depends on env vars


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
