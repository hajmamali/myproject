"""
Tests for Exception Hierarchy Validator
========================================

Comprehensive test suite for ExceptionHierarchyValidator with 100% coverage goal.
"""

import ast
import tempfile
from pathlib import Path

import pytest

from mahoun.preproduction.models import FindingSeverity, ValidationStatus
from mahoun.preproduction.validators.exception_validator import (
    ExceptionClass,
    ExceptionHierarchyAnalyzer,
    ExceptionHierarchyValidator,
)


class TestExceptionHierarchyAnalyzer:
    """Test AST analysis of exception classes."""
    
    def test_extracts_basic_exception(self):
        """Should extract basic exception metadata."""
        code = """
class MyError(Exception):
    '''My custom error.'''
    pass
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        assert len(analyzer.exceptions) == 1
        exc = analyzer.exceptions[0]
        assert exc.name == "MyError"
        assert "Exception" in exc.bases
        assert exc.docstring == "My custom error."
        assert exc.is_root
    
    def test_extracts_status_code(self):
        """Should detect status_code class attribute."""
        code = """
class APIError(Exception):
    status_code: int = 400
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        exc = analyzer.exceptions[0]
        assert exc.has_status_code
        assert exc.status_code_value == 400
    
    def test_extracts_to_dict_method(self):
        """Should detect to_dict() method."""
        code = """
class MyError(Exception):
    def to_dict(self):
        return {"error": "test"}
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        exc = analyzer.exceptions[0]
        assert exc.has_to_dict
        assert exc.to_dict_signature == "()"
    
    def test_extracts_to_dict_with_args(self):
        """Should extract to_dict() signature with arguments."""
        code = """
class MyError(Exception):
    def to_dict(self, include_trace: bool = False):
        return {"error": "test"}
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        exc = analyzer.exceptions[0]
        assert exc.has_to_dict
        assert "include_trace" in exc.to_dict_signature
    
    def test_detects_inheritance_chain(self):
        """Should extract inheritance relationships."""
        code = """
class BaseError(Exception):
    pass

class ChildError(BaseError):
    pass

class GrandchildError(ChildError):
    pass
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        assert len(analyzer.exceptions) == 3
        
        base = next(e for e in analyzer.exceptions if e.name == "BaseError")
        assert base.is_root
        
        child = next(e for e in analyzer.exceptions if e.name == "ChildError")
        assert "BaseError" in child.bases
        assert not child.is_root
        
        grandchild = next(e for e in analyzer.exceptions if e.name == "GrandchildError")
        assert "ChildError" in grandchild.bases
    
    def test_ignores_non_exceptions(self):
        """Should not extract non-exception classes."""
        code = """
class MyClass:
    pass

class MyService:
    def do_something(self):
        pass
"""
        tree = ast.parse(code)
        analyzer = ExceptionHierarchyAnalyzer()
        analyzer.visit(tree)
        
        assert len(analyzer.exceptions) == 0


class TestExceptionHierarchyValidator:
    """Test full validation logic."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project structure."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        
        # Create mahoun/core directory
        core_dir = project_root / "mahoun" / "core"
        core_dir.mkdir(parents=True)
        
        # Create api directory
        api_dir = project_root / "api"
        api_dir.mkdir()
        
        return project_root
    
    def test_detects_duplicate_roots(self, temp_project):
        """Should detect multiple root exception classes."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    pass

class BaseMahounError(Exception):
    pass

class ChildError(MahounError):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        assert result.status == ValidationStatus.FAIL
        blocker_findings = [f for f in result.findings if f.severity == FindingSeverity.P0_CRITICAL]
        assert len(blocker_findings) > 0
        assert "Multiple root exception classes" in blocker_findings[0].message
        assert "MahounError" in blocker_findings[0].message
        assert "BaseMahounError" in blocker_findings[0].message
    
    def test_single_root_passes(self, temp_project):
        """Should pass with single root exception."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    status_code: int = 400
    
    def to_dict(self):
        return {}

class ChildError(MahounError):
    pass

class GrandchildError(ChildError):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        # Should not have P0 findings for duplicate roots
        blocker_findings = [
            f for f in result.findings 
            if f.severity == FindingSeverity.P0_CRITICAL and "Multiple root" in f.message
        ]
        assert len(blocker_findings) == 0
    
    def test_detects_inconsistent_to_dict_signatures(self, temp_project):
        """Should detect inconsistent to_dict() signatures."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    def to_dict(self):
        return {}

class ErrorA(MahounError):
    def to_dict(self, verbose: bool = False):
        return {}

class ErrorB(MahounError):
    def to_dict(self, include_trace: bool = False):
        return {}
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        # Should detect inconsistent signatures
        signature_findings = [
            f for f in result.findings 
            if "to_dict() signatures" in f.message
        ]
        assert len(signature_findings) > 0
        assert signature_findings[0].severity == FindingSeverity.P1_HIGH
    
    def test_detects_missing_status_codes_in_api_exceptions(self, temp_project):
        """Should detect API-facing exceptions without status_code."""
        # Create exceptions without status_code
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    pass

class APIError(MahounError):
    pass

class ValidationError(MahounError):
    pass
""")
        
        # Create API router that uses these exceptions
        router_file = temp_project / "api" / "routers.py"
        router_file.write_text("""
from mahoun.core.exceptions import APIError, ValidationError

def my_handler():
    raise APIError("test")

def my_validator():
    raise ValidationError("invalid")
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        # Should detect missing status codes
        status_findings = [
            f for f in result.findings 
            if "missing status_code" in f.message
        ]
        assert len(status_findings) > 0
        assert status_findings[0].severity == FindingSeverity.P1_HIGH
    
    def test_detects_circular_inheritance(self, temp_project):
        """Should detect circular inheritance chains."""
        # Note: This is a synthetic test - Python won't actually allow this at runtime
        # But validator should detect it in AST
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        
        # We can't create actual circular inheritance, but we can test the detection logic
        # by mocking the graph
        validator = ExceptionHierarchyValidator(temp_project)
        
        # Create mock exceptions with circular references
        exc_a = ExceptionClass(name="ErrorA", bases=["ErrorB"], lineno=1, col_offset=0)
        exc_b = ExceptionClass(name="ErrorB", bases=["ErrorC"], lineno=2, col_offset=0)
        exc_c = ExceptionClass(name="ErrorC", bases=["ErrorA"], lineno=3, col_offset=0)
        
        exceptions = [exc_a, exc_b, exc_c]
        findings = validator._detect_circular_inheritance(exceptions)
        
        assert len(findings) > 0
        assert findings[0].severity == FindingSeverity.P0_CRITICAL
        assert "Circular inheritance" in findings[0].message
    
    def test_detects_bad_naming_conventions(self, temp_project):
        """Should detect exceptions not ending with Error or Exception."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounFailure(Exception):
    pass

class BadThing(Exception):
    pass

class GoodError(Exception):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        # Should detect naming violations
        naming_findings = [
            f for f in result.findings 
            if "naming convention" in f.message
        ]
        assert len(naming_findings) > 0
        assert naming_findings[0].severity == FindingSeverity.P3_LOW
    
    def test_generates_migration_plan(self, temp_project):
        """Should generate migration plan for fixing issues."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    pass

class BaseMahounError(Exception):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        assert "migration_plan" in result.evidence
        plan = result.evidence["migration_plan"]
        assert "steps" in plan
        assert len(plan["steps"]) > 0
        assert plan["priority"] == "P0_BLOCKER"
    
    def test_caches_ast_parsing(self, temp_project):
        """Should cache AST parsing results."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        
        # First parse
        exceptions1 = validator._parse_exception_hierarchy()
        cache_key1 = validator._ast_cache[0] if validator._ast_cache else None
        
        # Second parse (should use cache)
        exceptions2 = validator._parse_exception_hierarchy()
        cache_key2 = validator._ast_cache[0] if validator._ast_cache else None
        
        assert cache_key1 == cache_key2
        assert exceptions1 == exceptions2
    
    def test_invalidates_cache_on_content_change(self, temp_project):
        """Should invalidate cache when file content changes."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        
        # First parse
        exceptions1 = validator._parse_exception_hierarchy()
        cache_key1 = validator._ast_cache[0] if validator._ast_cache else None
        
        # Modify file
        exceptions_file.write_text("""
class MahounError(Exception):
    pass

class NewError(MahounError):
    pass
""")
        
        # Second parse (should re-parse)
        exceptions2 = validator._parse_exception_hierarchy()
        cache_key2 = validator._ast_cache[0] if validator._ast_cache else None
        
        assert cache_key1 != cache_key2
        assert len(exceptions2) > len(exceptions1)
    
    def test_reports_metadata(self, temp_project):
        """Should report comprehensive metadata."""
        exceptions_file = temp_project / "mahoun" / "core" / "exceptions.py"
        exceptions_file.write_text("""
class MahounError(Exception):
    status_code: int = 400
    def to_dict(self):
        return {}

class ErrorA(MahounError):
    status_code: int = 404

class ErrorB(MahounError):
    def to_dict(self):
        return {}

class ErrorC(MahounError):
    pass
""")
        
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        assert result.evidence["total_exceptions"] == 4
        assert result.evidence["root_exceptions"] == 1
        assert result.evidence["with_status_code"] >= 2
        assert result.evidence["with_to_dict"] >= 2
    
    def test_handles_missing_exceptions_file(self, temp_project):
        """Should handle missing exceptions.py gracefully."""
        # Don't create exceptions.py
        validator = ExceptionHierarchyValidator(temp_project)
        result = validator.validate()
        
        # Should complete without crashing
        assert result.evidence["total_exceptions"] == 0


class TestExceptionClass:
    """Test ExceptionClass dataclass."""
    
    def test_is_root_detection(self):
        """Should correctly identify root exceptions."""
        root = ExceptionClass(name="MyError", bases=["Exception"], lineno=1, col_offset=0)
        assert root.is_root
        
        child = ExceptionClass(name="ChildError", bases=["MyError"], lineno=2, col_offset=0)
        assert not child.is_root
    
    def test_full_location(self):
        """Should format location string."""
        exc = ExceptionClass(name="MyError", bases=[], lineno=42, col_offset=8)
        assert exc.full_location == "line 42, col 8"


class TestIntegrationWithRealExceptions:
    """Integration tests with actual exceptions.py file."""
    
    def test_real_exceptions_file(self):
        """Should successfully parse real exceptions.py."""
        # This test runs against the actual project exceptions file
        project_root = Path(__file__).parent.parent.parent
        
        validator = ExceptionHierarchyValidator(project_root)
        result = validator.validate()
        
        # Should detect the known duplicate roots issue
        assert result.evidence["total_exceptions"] > 0
        
        # Should detect MahounError and BaseMahounError
        root_count = result.evidence["root_exceptions"]
        assert root_count >= 2  # Known issue: duplicate roots exist
        
        # Should have findings about duplicate roots
        duplicate_root_findings = [
            f for f in result.findings 
            if f.severity == FindingSeverity.P0_CRITICAL and "Multiple root" in f.message
        ]
        assert len(duplicate_root_findings) > 0
