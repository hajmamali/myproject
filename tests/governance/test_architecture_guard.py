"""
MAHOUN Architecture Guard Tests
================================

Test suite for architecture_guard.py - Architecture Boundary Enforcement

Tests prove:
- Forbidden imports fail detection
- Tier boundary violations fail detection
- Governance bypass detection works
- Duplicate symbol detection works
"""

import os
import ast
import tempfile
import shutil

import pytest

# Test fixtures
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def setup_test_modules():
    """Set up temporary test modules."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test module structure
    modules = {
        "tier0_module.py": """
# This is a Tier-0 module
import sys
import json

def allowed_function():
    pass
""",
        "tier1_module.py": """
# This is a Tier-1 module
import os

def another_function():
    pass
""",
        "forbidden_module.py": """
# This module should not be imported by Tier-0
import some_external_lib

def forbidden_function():
    pass
""",
        "governance_bypass.py": """
# This module attempts to bypass governance
import raw_session

def bypass_governance():
    pass
"""
    }
    
    for filename, content in modules.items():
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
    
    yield {"temp_dir": temp_dir, "modules": modules}
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_manifest():
    """Create a test manifest."""
    manifest = {
        "kernel": {
            "name": "test_kernel",
            "version": "1.0.0"
        },
        "tiers": {
            "tier_0": {
                "description": "Test Tier 0",
                "protected_files": ["tier0_module.py"],
                "forbidden_imports": ["forbidden_module", "raw_session", "some_external_lib"]
            },
            "tier_1": {
                "description": "Test Tier 1",
                "protected_files": ["tier1_module.py"]
            }
        },
        "boundaries": {
            "forbidden_imports": {
                "tier_0": [
                    "forbidden_module",
                    "raw_session",
                    "some_external_lib",
                    "neo4j",
                    "sqlalchemy"
                ]
            },
            "tier_boundary_violations": {
                "tier_0_cannot_import": ["tier_1", "tier_2"]
            },
            "layer_violations": {
                "forbidden_layers_for_tier_0": ["api", "infrastructure"]
            }
        },
        "detection": {
            "governance_bypass": {
                "enabled": True,
                "patterns": ["raw.*session", "bypass.*governance"],
                "detect_raw_sessions": True,
                "detect_direct_database_access": True
            },
            "duplicate_symbols": {
                "enabled": True,
                "forbidden_duplicates": ["policy_engine", "governance_controller"]
            }
        }
    }
    
    return manifest


class TestImportExtraction:
    """Tests for import extraction from AST."""
    
    def test_extract_imports_from_ast(self):
        """Test extracting imports from AST."""
        from mahoun.governance.architecture_guard import extract_imports_from_ast
        
        source = """
import os
import sys
from datetime import datetime
from typing import List, Dict
import json as js
        """
        
        tree = ast.parse(source)
        imports = extract_imports_from_ast(tree, "test.py")
        
        assert "os" in imports
        assert "sys" in imports
        assert "datetime.datetime" in imports or "datetime" in imports
        assert "typing.List" in imports or "List" in imports
        assert "json" in imports or "js" in imports
    
    def test_extract_defined_symbols(self):
        """Test extracting defined symbols from AST."""
        from mahoun.governance.architecture_guard import extract_defined_symbols
        
        source = """
TEST_CONSTANT = 42

class TestClass:
    def method(self):
        pass

def test_function():
    pass
        """
        
        tree = ast.parse(source)
        symbols = extract_defined_symbols(tree)
        
        assert "TEST_CONSTANT" in symbols
        assert "TestClass" in symbols
        assert "method" in symbols
        assert "test_function" in symbols


class TestForbiddenImports:
    """Tests for forbidden import detection."""
    
    def test_detect_forbidden_import(self, test_manifest, setup_test_modules):
        """Test detection of forbidden imports."""
        from mahoun.governance.architecture_guard import check_forbidden_imports
        
        test_info = setup_test_modules
        
        # Create a file with forbidden import
        forbidden_file = os.path.join(test_info["temp_dir"], "test_forbidden.py")
        with open(forbidden_file, "w") as f:
            f.write("import forbidden_module\n")
        
        # This should detect the forbidden import
        # Use absolute path since check_forbidden_imports uses ROOT_DIR
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(forbidden_file, AG_ROOT_DIR)
        violations = check_forbidden_imports(abs_filepath, test_manifest)
        
        assert len(violations) > 0
        assert any("forbidden_module" in v for v in violations)
    
    def test_detect_prefix_forbidden_import(self, test_manifest, setup_test_modules):
        """Test detection of imports with forbidden prefix."""
        from mahoun.governance.architecture_guard import check_forbidden_imports
        
        test_info = setup_test_modules
        
        # Create a file with neo4j import
        neo4j_file = os.path.join(test_info["temp_dir"], "test_neo4j.py")
        with open(neo4j_file, "w") as f:
            f.write("from neo4j.driver import Driver\n")
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(neo4j_file, AG_ROOT_DIR)
        violations = check_forbidden_imports(abs_filepath, test_manifest)
        
        assert len(violations) > 0
        assert any("neo4j" in v for v in violations)
    
    def test_no_violations_for_allowed_imports(self, test_manifest, setup_test_modules):
        """Test that allowed imports don't trigger violations."""
        from mahoun.governance.architecture_guard import check_forbidden_imports
        
        test_info = setup_test_modules
        
        # Create a file with only allowed imports
        allowed_file = os.path.join(test_info["temp_dir"], "test_allowed.py")
        with open(allowed_file, "w") as f:
            f.write("import os\nimport sys\nimport json\n")
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(allowed_file, AG_ROOT_DIR)
        violations = check_forbidden_imports(abs_filepath, test_manifest)
        
        assert len(violations) == 0


class TestLayerViolations:
    """Tests for layer violation detection."""
    
    def test_detect_layer_violation(self, test_manifest, setup_test_modules):
        """Test detection of layer violations."""
        from mahoun.governance.architecture_guard import check_layer_violations
        
        test_info = setup_test_modules
        
        # Create a Tier-0 file that imports from forbidden layer
        layer_violation_file = os.path.join(test_info["temp_dir"], "test_layer.py")
        with open(layer_violation_file, "w") as f:
            f.write("from mahoun.api import some_function\n")
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(layer_violation_file, AG_ROOT_DIR)
        
        # Add our test file to the manifest so it gets checked
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = [abs_filepath]
        
        violations = check_layer_violations(abs_filepath, manifest)
        
        # Should detect the api import as a layer violation
        assert any("LAYER_VIOLATION" in v or "layer" in v.lower() for v in violations)
    
    def test_detect_tier_boundary_violation(self, test_manifest, setup_test_modules):
        """Test detection of tier boundary violations."""
        from mahoun.governance.architecture_guard import check_layer_violations
        
        test_info = setup_test_modules
        
        # Create a Tier-0 file that imports from tier_1
        boundary_violation_file = os.path.join(test_info["temp_dir"], "test_boundary.py")
        with open(boundary_violation_file, "w") as f:
            f.write("from mahoun.governance import something\n")
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(boundary_violation_file, AG_ROOT_DIR)
        
        # Modify manifest for this test
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = [abs_filepath]
        manifest["boundaries"]["tier_boundary_violations"]["tier_0_cannot_import"] = ["governance"]
        
        violations = check_layer_violations(abs_filepath, manifest)
        
        # Should detect the governance import
        assert len(violations) > 0


class TestGovernanceBypass:
    """Tests for governance bypass detection."""
    
    def test_detect_raw_session_pattern(self, test_manifest, setup_test_modules):
        """Test detection of raw session patterns."""
        from mahoun.governance.architecture_guard import check_governance_bypass
        
        test_info = setup_test_modules
        
        # Create a file with raw session creation
        session_file = os.path.join(test_info["temp_dir"], "test_session.py")
        with open(session_file, "w") as f:
            f.write("""
session = Session()
result = engine.connect()
            """)
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(session_file, AG_ROOT_DIR)
        violations = check_governance_bypass(abs_filepath, test_manifest)
        
        assert len(violations) > 0
        assert any("SESSION" in v or "session" in v.lower() for v in violations)
    
    def test_detect_bypass_pattern(self, test_manifest, setup_test_modules):
        """Test detection of bypass patterns."""
        from mahoun.governance.architecture_guard import check_governance_bypass
        
        test_info = setup_test_modules
        
        # Create a file with bypass pattern
        bypass_file = os.path.join(test_info["temp_dir"], "test_bypass.py")
        with open(bypass_file, "w") as f:
            f.write("""
def bypass_governance_check():
    pass

def disable_enforcement():
    pass
            """)
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(bypass_file, AG_ROOT_DIR)
        violations = check_governance_bypass(abs_filepath, test_manifest)
        
        assert len(violations) > 0
    
    def test_detect_direct_db_access(self, test_manifest, setup_test_modules):
        """Test detection of direct database access."""
        from mahoun.governance.architecture_guard import check_governance_bypass
        
        test_info = setup_test_modules
        
        # Create a file with direct DB access
        db_file = os.path.join(test_info["temp_dir"], "test_db.py")
        with open(db_file, "w") as f:
            f.write("""
connection.execute("SELECT * FROM table")
session.raw("INSERT INTO table VALUES (1)")
            """)
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath = os.path.relpath(db_file, AG_ROOT_DIR)
        violations = check_governance_bypass(abs_filepath, test_manifest)
        
        assert len(violations) > 0


class TestDuplicateSymbols:
    """Tests for duplicate symbol detection."""
    
    def test_detect_duplicate_symbol(self, test_manifest, setup_test_modules):
        """Test detection of duplicate symbols."""
        from mahoun.governance.architecture_guard import check_duplicate_symbols
        
        test_info = setup_test_modules
        
        # Create first file with a symbol
        file1 = os.path.join(test_info["temp_dir"], "test_dup1.py")
        with open(file1, "w") as f:
            f.write("""
class policy_engine:
    pass
            """)
        
        # Create second file with same symbol
        file2 = os.path.join(test_info["temp_dir"], "test_dup2.py")
        with open(file2, "w") as f:
            f.write("""
class policy_engine:
    pass
            """)
        
        from mahoun.governance.architecture_guard import ROOT_DIR as AG_ROOT_DIR
        abs_filepath1 = os.path.relpath(file1, AG_ROOT_DIR)
        abs_filepath2 = os.path.relpath(file2, AG_ROOT_DIR)
        
        # Add files to manifest
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = [abs_filepath1, abs_filepath2]
        manifest["detection"]["duplicate_symbols"]["forbidden_duplicates"] = ["policy_engine"]
        
        # Process first file to populate all_symbols
        all_symbols = {}
        check_duplicate_symbols(abs_filepath1, manifest, all_symbols)
        
        # Now check second file
        violations = check_duplicate_symbols(abs_filepath2, manifest, all_symbols)
        
        # Should detect the duplicate
        assert len(violations) > 0
        assert any("policy_engine" in v for v in violations)


class TestArchitectureGuardCLI:
    """Tests for architecture guard CLI commands."""
    
    @pytest.mark.skip(reason="Requires real file structure - TODO: Fix path resolution")
    def test_verify_architecture_success(self, test_manifest, setup_test_modules):
        """Test that architecture verification succeeds for valid code."""
        from mahoun.governance.architecture_guard import verify_architecture
        
        test_info = setup_test_modules
        
        # Create a valid Tier-0 file
        valid_file = os.path.join(test_info["temp_dir"], "valid_module.py")
        with open(valid_file, "w") as f:
            f.write("import os\nimport sys\n")
        
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = ["valid_module.py"]
        
        # This should succeed
        result = verify_architecture(manifest)
        assert result is True
    
    @pytest.mark.skip(reason="Requires real file structure - TODO: Fix path resolution")
    def test_verify_architecture_detects_violations(self, test_manifest, setup_test_modules):
        """Test that architecture verification detects violations."""
        from mahoun.governance.architecture_guard import verify_architecture
        
        test_info = setup_test_modules
        
        # Create an invalid Tier-0 file
        invalid_file = os.path.join(test_info["temp_dir"], "invalid_module.py")
        with open(invalid_file, "w") as f:
            f.write("import forbidden_module\n")
        
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = ["invalid_module.py"]
        
        # This should fail
        with pytest.raises(SystemExit) as exc_info:
            verify_architecture(manifest)
        assert exc_info.value.code == 1


class TestModulePathConversion:
    """Tests for module path conversion."""
    
    def test_get_file_path_module(self):
        """Test converting file path to module path."""
        from mahoun.governance.architecture_guard import get_file_path_module
        
        # Test various path formats
        assert get_file_path_module("mahoun/core/module.py") == "mahoun.core.module"
        assert get_file_path_module("mahoun/core/module.py") == "mahoun.core.module"
        assert get_file_path_module("./mahoun/core/module.py") == "mahoun.core.module"


class TestManifestLoading:
    """Tests for manifest loading in architecture guard."""
    
    def test_load_manifest_success(self):
        """Test loading a valid manifest."""
        from mahoun.governance.architecture_guard import load_manifest
        
        manifest = load_manifest()
        assert "kernel" in manifest
        assert "tiers" in manifest
        assert "boundaries" in manifest
    
    def test_load_manifest_file_not_found(self, monkeypatch):
        """Test loading manifest when file doesn't exist."""
        from mahoun.governance import architecture_guard
        
        # Temporarily change MANIFEST_PATH
        original_path = architecture_guard.MANIFEST_PATH
        architecture_guard.MANIFEST_PATH = "/nonexistent/path/manifest.yaml"
        
        try:
            with pytest.raises(SystemExit) as exc_info:
                architecture_guard.load_manifest()
            assert exc_info.value.code == 1
        finally:
            architecture_guard.MANIFEST_PATH = original_path


class TestErrorHandling:
    """Tests for error handling in architecture guard."""
    
    def test_architecture_guard_error_hierarchy(self):
        """Test error class hierarchy."""
        from mahoun.governance.architecture_guard import (
            ArchitectureGuardError,
            ForbiddenImportError,
            LayerViolationError,
            GovernanceBypassError,
            DuplicateSymbolError
        )
        
        assert issubclass(ForbiddenImportError, ArchitectureGuardError)
        assert issubclass(LayerViolationError, ArchitectureGuardError)
        assert issubclass(GovernanceBypassError, ArchitectureGuardError)
        assert issubclass(DuplicateSymbolError, ArchitectureGuardError)


# Integration tests
class TestIntegration:
    """Integration tests for architecture guard functionality."""
    
    @pytest.mark.skip(reason="Requires real file structure - TODO: Fix path resolution")
    def test_check_specific_file(self, test_manifest, setup_test_modules):
        """Test checking a specific file."""
        pass
    
    @pytest.mark.skip(reason="Requires real file structure - TODO: Fix path resolution")
    def test_full_architecture_verification_with_valid_code(self, test_manifest, setup_test_modules):
        """Test full verification with valid code."""
        from mahoun.governance.architecture_guard import verify_architecture
        
        test_info = setup_test_modules
        
        # Create a valid Tier-0 file
        valid_file = os.path.join(test_info["temp_dir"], "valid_tier0.py")
        with open(valid_file, "w") as f:
            f.write("import os\nimport sys\n")
        
        # Create a valid Tier-1 file
        valid_tier1 = os.path.join(test_info["temp_dir"], "valid_tier1.py")
        with open(valid_tier1, "w") as f:
            f.write("import json\nimport yaml\n")
        
        manifest = test_manifest.copy()
        manifest["tiers"]["tier_0"]["protected_files"] = ["valid_tier0.py"]
        manifest["tiers"]["tier_1"]["protected_files"] = ["valid_tier1.py"]
        
        result = verify_architecture(manifest)
        assert result is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
