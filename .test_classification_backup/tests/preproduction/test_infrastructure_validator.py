"""
Tests for Infrastructure Validator
==================================

Test suite for Docker image optimization and security validation.
"""

import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mahoun.preproduction.validators.infrastructure_validator import (
    InfrastructureValidator,
    DockerImageMetrics,
    SecurityVulnerability,
    ImageOptimizationRecommendation,
)
from mahoun.preproduction.models import ValidationStatus, FindingSeverity


@pytest.fixture
def mock_evidence_collector():
    """Mock evidence collector."""
    collector = Mock()
    collector.collect_file_lines = Mock(return_value={})
    collector.collect_ast_analysis = Mock(return_value={})
    collector.collect_command_output = Mock(return_value={})
    return collector


@pytest.fixture
def sample_workspace(tmp_path):
    """Create sample workspace."""
    # Create Dockerfiles
    (tmp_path / "Dockerfile.backend").write_text(
        "FROM python:3.12-slim\nCOPY . .\nRUN pip install -e .\n"
    )
    (tmp_path / "Dockerfile.api").write_text(
        "FROM python:3.12\nCOPY mahoun/ /app/mahoun/\nCOPY api/ /app/api/\n"
    )
    
    return tmp_path


class TestDockerImageMetrics:
    """Test DockerImageMetrics dataclass."""
    
    def test_image_metrics_creation(self):
        """Test creating image metrics."""
        metrics = DockerImageMetrics(
            image_name="mahoun/backend",
            tag="latest",
            size_mb=1200.5,
            layers=10,
        )
        
        assert metrics.full_name == "mahoun/backend:latest"
        assert metrics.size_mb == 1200.5
    
    def test_full_name_property(self):
        """Test full_name property."""
        metrics = DockerImageMetrics(
            image_name="test/image",
            tag="v1.0",
            size_mb=100.0,
        )
        
        assert metrics.full_name == "test/image:v1.0"


class TestSecurityVulnerability:
    """Test SecurityVulnerability dataclass."""
    
    def test_vulnerability_creation(self):
        """Test creating vulnerability."""
        vuln = SecurityVulnerability(
            cve_id="CVE-2024-1234",
            severity="CRITICAL",
            package="openssl",
            installed_version="1.0.0",
            fixed_version="1.0.1",
            description="Buffer overflow in SSL",
            cvss_score=9.8,
        )
        
        assert vuln.cve_id == "CVE-2024-1234"
        assert vuln.severity == "CRITICAL"


class TestInfrastructureValidator:
    """Test InfrastructureValidator."""
    
    def test_initialization(self, mock_evidence_collector, tmp_path):
        """Test validator initialization."""
        validator = InfrastructureValidator(
            evidence_collector=mock_evidence_collector,
            workspace_root=tmp_path
        )
        
        assert validator.name == "infrastructure-validator"
        assert validator.workspace_root == tmp_path
        assert validator.dockerignore_path == tmp_path / ".dockerignore"
    
    def test_dependencies(self, mock_evidence_collector, tmp_path):
        """Test validator has no dependencies."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        deps = validator.get_dependencies()
        
        assert deps == []
    
    def test_target_sizes_constants(self):
        """Test target sizes are properly defined."""
        targets = InfrastructureValidator.TARGET_SIZES
        
        assert "mahoun/backend" in targets
        assert targets["mahoun/backend"] == 400
        assert targets["mahoun/api"] == 350
        assert targets["mahoun/kernel"] == 200
    
    def test_required_dockerignore_patterns(self):
        """Test required .dockerignore patterns."""
        patterns = InfrastructureValidator.REQUIRED_DOCKERIGNORE_PATTERNS
        
        assert ".git" in patterns
        assert "__pycache__" in patterns
        assert "*.pyc" in patterns
        assert "tests/" in patterns
    
    def test_dockerignore_missing(self, mock_evidence_collector, tmp_path):
        """Test detection of missing .dockerignore."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._check_dockerignore()
        
        # Should have P0 finding
        p0_findings = [f for f in findings if f.severity == FindingSeverity.P0_CRITICAL]
        assert len(p0_findings) > 0
        assert "missing" in p0_findings[0].message.lower()
    
    def test_dockerignore_complete(self, mock_evidence_collector, tmp_path):
        """Test complete .dockerignore passes."""
        # Create complete .dockerignore
        dockerignore = tmp_path / ".dockerignore"
        dockerignore.write_text("\n".join(InfrastructureValidator.REQUIRED_DOCKERIGNORE_PATTERNS))
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._check_dockerignore()
        
        # Should have INFO finding
        info_findings = [f for f in findings if f.severity == FindingSeverity.INFO]
        assert len(info_findings) > 0
        assert "all critical patterns" in info_findings[0].message.lower()
    
    def test_dockerignore_incomplete(self, mock_evidence_collector, tmp_path):
        """Test incomplete .dockerignore detected."""
        # Create partial .dockerignore
        dockerignore = tmp_path / ".dockerignore"
        dockerignore.write_text(".git\n__pycache__\n")  # Missing other patterns
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._check_dockerignore()
        
        # Should have P1 finding
        p1_findings = [f for f in findings if f.severity == FindingSeverity.P1_HIGH]
        assert len(p1_findings) > 0
        assert "missing" in p1_findings[0].message.lower()
    
    def test_parse_size_to_mb_gb(self, mock_evidence_collector, tmp_path):
        """Test parsing GB size to MB."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        
        size_mb = validator._parse_size_to_mb("1.2GB")
        assert size_mb == 1228.8  # 1.2 * 1024
    
    def test_parse_size_to_mb_mb(self, mock_evidence_collector, tmp_path):
        """Test parsing MB size."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        
        size_mb = validator._parse_size_to_mb("450MB")
        assert size_mb == 450.0
    
    def test_parse_size_to_mb_kb(self, mock_evidence_collector, tmp_path):
        """Test parsing KB size to MB."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        
        size_mb = validator._parse_size_to_mb("2048KB")
        assert size_mb == 2.0  # 2048 / 1024
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_measure_image_sizes(self, mock_run, mock_evidence_collector, tmp_path):
        """Test measuring Docker image sizes."""
        # Mock docker images command output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="mahoun/backend:latest\t1.2GB\nmahoun/api:v1.0\t890MB\n",
            stderr=""
        )
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        images = validator._measure_image_sizes()
        
        assert len(images) == 2
        assert images[0].image_name == "mahoun/backend"
        assert images[0].size_mb > 1000  # ~1228 MB
        assert images[1].image_name == "mahoun/api"
        assert images[1].size_mb == 890.0
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_measure_image_sizes_no_images(self, mock_run, mock_evidence_collector, tmp_path):
        """Test when no mahoun images found."""
        # Mock docker returning other images only
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="postgres:14\t200MB\nredis:7\t100MB\n",
            stderr=""
        )
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        images = validator._measure_image_sizes()
        
        assert len(images) == 0
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_measure_image_sizes_docker_not_found(self, mock_run, mock_evidence_collector, tmp_path):
        """Test handling when Docker not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        images = validator._measure_image_sizes()
        
        assert len(images) == 0
        # Should have added finding
        assert len(validator.findings) > 0
    
    def test_analyze_image_sizes_no_images(self, mock_evidence_collector, tmp_path):
        """Test analyzing when no images."""
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._analyze_image_sizes([])
        
        # Should have P2 finding
        p2_findings = [f for f in findings if f.severity == FindingSeverity.P2_MEDIUM]
        assert len(p2_findings) > 0
        assert "no" in p2_findings[0].message.lower()
    
    def test_analyze_image_sizes_within_target(self, mock_evidence_collector, tmp_path):
        """Test analysis when images within target."""
        images = [
            DockerImageMetrics("mahoun/backend", "latest", 350.0),  # Target: 400
            DockerImageMetrics("mahoun/api", "latest", 300.0),      # Target: 350
        ]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._analyze_image_sizes(images)
        
        # Should have INFO finding
        info_findings = [f for f in findings if f.severity == FindingSeverity.INFO]
        assert len(info_findings) > 0
        assert "within target" in info_findings[0].message.lower()
    
    def test_analyze_image_sizes_oversized(self, mock_evidence_collector, tmp_path):
        """Test analysis when images oversized."""
        images = [
            DockerImageMetrics("mahoun/backend", "latest", 1200.0),  # Target: 400, excess: 800
            DockerImageMetrics("mahoun/api", "latest", 890.0),       # Target: 350, excess: 540
        ]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._analyze_image_sizes(images)
        
        # Should have P1 finding
        p1_findings = [f for f in findings if f.severity == FindingSeverity.P1_HIGH]
        assert len(p1_findings) > 0
        assert "exceed target" in p1_findings[0].message.lower()
    
    def test_analyze_dockerfiles_single_stage(self, mock_evidence_collector, sample_workspace):
        """Test analyzing single-stage Dockerfile."""
        validator = InfrastructureValidator(mock_evidence_collector, sample_workspace)
        findings = validator._analyze_dockerfiles()
        
        # Should detect missing multi-stage
        multistage_findings = [
            f for f in findings 
            if "multi-stage" in f.message.lower()
        ]
        assert len(multistage_findings) > 0
        assert multistage_findings[0].severity == FindingSeverity.P1_HIGH
    
    def test_analyze_dockerfiles_copy_dot_dot(self, mock_evidence_collector, sample_workspace):
        """Test detection of COPY . . anti-pattern."""
        validator = InfrastructureValidator(mock_evidence_collector, sample_workspace)
        findings = validator._analyze_dockerfiles()
        
        # Should detect COPY . . in Dockerfile.backend
        copy_findings = [
            f for f in findings 
            if "copy . ." in f.message.lower()
        ]
        assert len(copy_findings) > 0
    
    def test_analyze_dockerfiles_multistage(self, mock_evidence_collector, tmp_path):
        """Test analyzing multi-stage Dockerfile."""
        # Create multi-stage Dockerfile
        (tmp_path / "Dockerfile.backend").write_text(
            "FROM python:3.12 AS builder\n"
            "RUN pip install build\n"
            "FROM python:3.12-slim\n"
            "COPY --from=builder /app /app\n"
        )
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._analyze_dockerfiles()
        
        # Should NOT flag multi-stage issue
        multistage_findings = [
            f for f in findings 
            if "multi-stage" in f.message.lower() and f.severity == FindingSeverity.P1_HIGH
        ]
        assert len(multistage_findings) == 0
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_security_scan_trivy_not_installed(self, mock_run, mock_evidence_collector, tmp_path):
        """Test security scan when Trivy not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        images = [DockerImageMetrics("mahoun/backend", "latest", 400.0)]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._run_security_scan(images)
        
        # Should have P3 finding about Trivy
        p3_findings = [f for f in findings if f.severity == FindingSeverity.P3_LOW]
        assert len(p3_findings) > 0
        assert "trivy" in p3_findings[0].message.lower()
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_security_scan_with_vulnerabilities(self, mock_run, mock_evidence_collector, tmp_path):
        """Test security scan finding vulnerabilities."""
        # Mock trivy --version
        # Mock trivy image scan
        trivy_output = {
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-1234",
                            "Severity": "CRITICAL",
                            "PkgName": "openssl",
                            "InstalledVersion": "1.0.0",
                            "FixedVersion": "1.0.1",
                            "Description": "Critical security issue",
                        },
                        {
                            "VulnerabilityID": "CVE-2024-5678",
                            "Severity": "HIGH",
                            "PkgName": "curl",
                            "InstalledVersion": "7.0.0",
                            "FixedVersion": "7.0.1",
                            "Description": "High severity issue",
                        },
                    ]
                }
            ]
        }
        
        def mock_run_side_effect(*args, **kwargs):
            if "--version" in args[0]:
                return MagicMock(returncode=0)
            else:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(trivy_output),
                    stderr=""
                )
        
        mock_run.side_effect = mock_run_side_effect
        
        images = [DockerImageMetrics("mahoun/backend", "latest", 400.0)]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._run_security_scan(images)
        
        # Should have P0 finding for CRITICAL vulns
        p0_findings = [f for f in findings if f.severity == FindingSeverity.P0_CRITICAL]
        assert len(p0_findings) > 0
        assert "critical" in p0_findings[0].message.lower()
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_security_scan_clean(self, mock_run, mock_evidence_collector, tmp_path):
        """Test security scan with no vulnerabilities."""
        trivy_output = {"Results": []}
        
        def mock_run_side_effect(*args, **kwargs):
            if "--version" in args[0]:
                return MagicMock(returncode=0)
            else:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps(trivy_output),
                    stderr=""
                )
        
        mock_run.side_effect = mock_run_side_effect
        
        images = [DockerImageMetrics("mahoun/backend", "latest", 400.0)]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        findings = validator._run_security_scan(images)
        
        # Should have INFO finding
        info_findings = [f for f in findings if f.severity == FindingSeverity.INFO]
        assert len(info_findings) > 0
    
    def test_generate_optimizations_oversized_image(self, mock_evidence_collector, tmp_path):
        """Test generating optimizations for oversized image."""
        images = [DockerImageMetrics("mahoun/backend", "latest", 1200.0)]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        recs = validator._generate_optimizations(images, [], [])
        
        # Should have size optimization recommendation
        size_recs = [r for r in recs if r.category == "size"]
        assert len(size_recs) > 0
    
    def test_generate_optimizations_missing_dockerignore(self, mock_evidence_collector, tmp_path):
        """Test generating optimizations for missing .dockerignore."""
        from mahoun.preproduction.models import Finding
        
        dockerignore_findings = [
            Finding(
                severity=FindingSeverity.P0_CRITICAL,
                message=".dockerignore missing",
                evidence={}
            )
        ]
        
        validator = InfrastructureValidator(mock_evidence_collector, tmp_path)
        recs = validator._generate_optimizations([], dockerignore_findings, [])
        
        # Should have build optimization recommendation
        build_recs = [r for r in recs if r.category == "build"]
        assert len(build_recs) > 0
    
    @patch("mahoun.preproduction.validators.infrastructure_validator.subprocess.run")
    def test_full_validation_workflow(self, mock_run, mock_evidence_collector, sample_workspace):
        """Test full validation workflow."""
        # Create .dockerignore
        (sample_workspace / ".dockerignore").write_text(
            "\n".join(InfrastructureValidator.REQUIRED_DOCKERIGNORE_PATTERNS)
        )
        
        # Mock Docker commands
        def mock_run_side_effect(*args, **kwargs):
            if "docker" in args[0] and "images" in args[0]:
                return MagicMock(
                    returncode=0,
                    stdout="mahoun/backend:latest\t450MB\n",
                    stderr=""
                )
            elif "trivy" in args[0] and "--version" in args[0]:
                raise FileNotFoundError()  # Trivy not installed
            return MagicMock(returncode=1, stdout="", stderr="")
        
        mock_run.side_effect = mock_run_side_effect
        
        validator = InfrastructureValidator(mock_evidence_collector, sample_workspace)
        result = validator.validate()
        
        assert result.validator_id == "infrastructure-validator"
        assert result.status in (ValidationStatus.PASS, ValidationStatus.WARNING, ValidationStatus.FAIL)
        assert "dockerignore_exists" in result.evidence
        assert "image_metrics" in result.evidence


class TestImageOptimizationRecommendation:
    """Test ImageOptimizationRecommendation dataclass."""
    
    def test_recommendation_creation(self):
        """Test creating optimization recommendation."""
        rec = ImageOptimizationRecommendation(
            category="size",
            priority=FindingSeverity.P1_HIGH,
            current_value="1200MB",
            target_value="400MB",
            estimated_improvement="66% reduction",
            action="Implement multi-stage build",
        )
        
        assert rec.category == "size"
        assert rec.priority == FindingSeverity.P1_HIGH
        assert rec.estimated_improvement == "66% reduction"
