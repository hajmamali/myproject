"""
API Database Firewall Regression Tests
========================================

Tests that verify the governance firewall prevents bypass attempts.
These tests ensure that the refactored architecture remains secure.

Classification: P0 - CRITICAL GOVERNANCE
"""

import pytest
import tempfile
from pathlib import Path
from ci.enforcement.api_database_firewall import (
    DatabaseAccessFirewall,
    scan_file,
    ViolationSeverity,
)


class TestAPIFirewallDetection:
    """Test that firewall correctly detects violations"""
    
    def test_detects_direct_neo4j_import(self):
        """Firewall MUST detect 'from neo4j import GraphDatabase'"""
        code = """
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost')
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        assert len(violations) >= 1, "Must detect direct neo4j import"
        assert any(v.severity == ViolationSeverity.P0_CRITICAL for v in violations)
        assert any('neo4j import' in v.message.lower() for v in violations)
    
    def test_detects_async_driver_instantiation(self):
        """Firewall MUST detect 'AsyncGraphDatabase.driver()'"""
        code = """
from neo4j import AsyncGraphDatabase

async def init():
    driver = AsyncGraphDatabase.driver('bolt://localhost', auth=('neo4j', 'pass'))
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        assert len(violations) >= 1, "Must detect AsyncGraphDatabase.driver()"
        assert any(v.severity == ViolationSeverity.P0_CRITICAL for v in violations)
    
    def test_detects_sync_driver_instantiation(self):
        """Firewall MUST detect 'GraphDatabase.driver()'"""
        code = """
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost', auth=('neo4j', 'pass'))
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        assert len(violations) >= 1, "Must detect GraphDatabase.driver()"
        p0_violations = [v for v in violations if v.severity == ViolationSeverity.P0_CRITICAL]
        assert len(p0_violations) >= 1, "Driver instantiation must be P0"
    
    def test_allows_canonical_import(self):
        """Firewall MUST allow imports from canonical layer"""
        code = """
from mahoun.graph.neo4j.connection import (
    get_connection,
    initialize_canonical_async_driver,
)

async def init():
    driver = await initialize_canonical_async_driver('bolt://localhost', ('neo4j', 'pass'))
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        # Should have no P0 violations
        p0_violations = [v for v in violations if v.severity == ViolationSeverity.P0_CRITICAL]
        assert len(p0_violations) == 0, "Canonical imports must be allowed"
    
    def test_detects_raw_session_without_exemption(self):
        """Firewall MUST flag raw driver.session() without exemption"""
        code = """
async def bad_code(neo4j_driver):
    async with neo4j_driver.session() as session:
        await session.run("CREATE (n:BadNode)")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        # Should detect raw session access
        session_violations = [v for v in violations if 'session' in v.message.lower()]
        assert len(session_violations) >= 1, "Must detect raw session access"
    
    def test_allows_bootstrap_exemption(self):
        """Firewall MUST allow documented BOOTSTRAP EXEMPTION"""
        code = """
async def init_schema(neo4j_driver):
    # BOOTSTRAP EXEMPTION: Schema initialization before governance layer exists
    async with neo4j_driver.session() as session:
        await session.run("CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.id)")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        # Should have no violations due to exemption comment
        session_violations = [v for v in violations if 'session' in v.message.lower()]
        assert len(session_violations) == 0, "BOOTSTRAP EXEMPTION must be honored"


class TestCanonicalAsyncDriver:
    """Test the canonical async driver initialization"""
    
    @pytest.mark.asyncio
    async def test_canonical_driver_exists(self):
        """Verify initialize_canonical_async_driver exists and is importable"""
        try:
            from mahoun.graph.neo4j.connection import initialize_canonical_async_driver
            assert callable(initialize_canonical_async_driver)
        except ImportError as e:
            pytest.fail(f"Cannot import canonical async driver: {e}")
    
    @pytest.mark.asyncio
    async def test_exception_reexports_exist(self):
        """Verify Neo4j exceptions are re-exported from canonical layer"""
        try:
            from mahoun.graph.neo4j.connection import (
                Neo4jServiceUnavailable,
                Neo4jAuthError,
                Neo4jBoltError,
            )
            # Should be exception types
            assert issubclass(Neo4jServiceUnavailable, Exception)
            assert issubclass(Neo4jAuthError, Exception)
            assert issubclass(Neo4jBoltError, Exception)
        except ImportError as e:
            pytest.fail(f"Exception re-exports missing: {e}")


class TestAPIDatabaseCompliance:
    """Test that api/database.py is governance compliant"""
    
    def test_api_database_no_direct_import(self):
        """api/database.py MUST NOT import neo4j directly"""
        api_database = Path(__file__).parent.parent.parent / "api" / "database.py"
        
        if not api_database.exists():
            pytest.skip("api/database.py not found")
        
        source = api_database.read_text()
        
        # Check for direct neo4j imports (excluding re-exports in comments)
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Check for forbidden patterns
            if 'from neo4j import' in line and 'AsyncGraphDatabase' in line:
                # This is only allowed if it's importing from connection layer
                if 'mahoun.graph.neo4j.connection' not in source[:source.index(line)]:
                    pytest.fail(
                        f"Line {i}: Direct neo4j import detected: {line.strip()}\n"
                        f"Must import from mahoun.graph.neo4j.connection instead"
                    )
    
    def test_api_database_uses_canonical_driver(self):
        """api/database.py MUST use initialize_canonical_async_driver"""
        api_database = Path(__file__).parent.parent.parent / "api" / "database.py"
        
        if not api_database.exists():
            pytest.skip("api/database.py not found")
        
        source = api_database.read_text()
        
        # Must import from canonical layer
        assert 'from mahoun.graph.neo4j.connection import' in source, \
            "Must import from canonical connection layer"
        
        assert 'initialize_canonical_async_driver' in source, \
            "Must use initialize_canonical_async_driver()"
        
        # Must NOT directly instantiate AsyncGraphDatabase
        lines = source.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('#'):
                continue
            
            if 'AsyncGraphDatabase.driver(' in line:
                pytest.fail(
                    f"Line {i}: Direct AsyncGraphDatabase.driver() detected: {line.strip()}\n"
                    f"This violates AGENTS.md Section 1-A"
                )


class TestGovernanceBypassPrevention:
    """Test that common bypass vectors are blocked"""
    
    def test_cannot_import_neo4j_driver_from_api_database(self):
        """Code MUST NOT be able to import neo4j_driver from api.database"""
        # This test verifies the global variable is not exposed for import
        
        code = """
from api.database import neo4j_driver

# Try to bypass governance
async with neo4j_driver.session() as session:
    await session.run("CREATE (n:Bypass)")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        # Should detect this as CRITICAL violation
        critical_violations = [v for v in violations if v.severity == ViolationSeverity.P0_CRITICAL]
        assert len(critical_violations) >= 1, "Must block neo4j_driver import"
    
    def test_firewall_catches_module_attribute_access(self):
        """Firewall MUST detect api.database.neo4j_driver access"""
        code = """
import api.database

# Try to access global driver directly
driver = api.database.neo4j_driver
session = driver.session()
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            
            violations = scan_file(Path(f.name))
        
        # Should flag this attempt
        assert len(violations) >= 1, "Must detect module attribute access to driver"


class TestRegressionScenarios:
    """Test specific regression scenarios from past incidents"""
    
    def test_infrastructure_health_checker_compliance(self):
        """Regression: mahoun/infrastructure/health modules must use canonical layer"""
        health_dir = Path(__file__).parent.parent.parent / "mahoun" / "infrastructure" / "health"
        
        if not health_dir.exists():
            pytest.skip("Health directory not found")
        
        for py_file in health_dir.glob("*.py"):
            if py_file.name.startswith('test_'):
                continue
            
            violations = scan_file(py_file)
            p0_violations = [v for v in violations if v.severity == ViolationSeverity.P0_CRITICAL]
            
            assert len(p0_violations) == 0, \
                f"{py_file.name} has P0 violations: {[v.message for v in p0_violations]}"
    
    def test_routers_use_get_connection(self):
        """Regression: All routers must use get_connection(), not direct driver"""
        routers_dir = Path(__file__).parent.parent.parent / "api" / "routers"
        
        if not routers_dir.exists():
            pytest.skip("Routers directory not found")
        
        for router_file in routers_dir.glob("*.py"):
            if router_file.name == '__init__.py':
                continue
            
            source = router_file.read_text()
            
            # Should not contain direct driver access
            assert 'neo4j_driver.session()' not in source, \
                f"{router_file.name} has direct driver.session() call"
            
            assert 'AsyncGraphDatabase.driver(' not in source, \
                f"{router_file.name} instantiates driver directly"
            
            assert 'GraphDatabase.driver(' not in source, \
                f"{router_file.name} instantiates driver directly"


@pytest.mark.governance
@pytest.mark.p0
class TestConstitutionalCompliance:
    """Verify compliance with constitutional mandates"""
    
    def test_single_canonical_driver_location(self):
        """CONSTITUTION.md Section 7: Single source of truth"""
        # Search for AsyncGraphDatabase.driver() calls outside canonical location
        
        workspace = Path(__file__).parent.parent.parent
        violations = []
        
        canonical_locations = [
            'mahoun/graph/neo4j/connection.py',
        ]
        
        for py_file in workspace.rglob('*.py'):
            # Skip tests, virtual env, and git worktrees
            if any(skip in str(py_file) for skip in ['test', 'venv', '.pyc', '.kilo/worktrees']):
                continue
            
            # Check if this is canonical location
            is_canonical = any(canonical in str(py_file) for canonical in canonical_locations)
            
            if is_canonical:
                continue
            
            try:
                source = py_file.read_text(encoding='utf-8', errors='ignore')
                
                if 'AsyncGraphDatabase.driver(' in source:
                    violations.append((str(py_file.relative_to(workspace)), 'AsyncGraphDatabase.driver()'))
                
                if 'GraphDatabase.driver(' in source and 'connection.py' not in str(py_file):
                    violations.append((str(py_file.relative_to(workspace)), 'GraphDatabase.driver()'))
            
            except Exception:
                continue
        
        assert len(violations) == 0, \
            f"Driver instantiation found outside canonical location:\n" + \
            "\n".join(f"  {file}: {pattern}" for file, pattern in violations)
    
    def test_agents_md_section_1a_compliance(self):
        """AGENTS.md Section 1-A: Neo4j Connection canonical location"""
        # Verify that connection.py contains the canonical driver initialization
        
        connection_file = Path(__file__).parent.parent.parent / "mahoun" / "graph" / "neo4j" / "connection.py"
        
        assert connection_file.exists(), "Canonical connection.py must exist"
        
        source = connection_file.read_text()
        
        # Must contain async driver factory
        assert 'def initialize_canonical_async_driver' in source or \
               'async def initialize_canonical_async_driver' in source, \
            "Must contain initialize_canonical_async_driver function"
        
        # Must document its canonical status
        assert 'CANONICAL' in source.upper() or 'AGENTS.MD' in source.upper(), \
            "Must document canonical status per AGENTS.md"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
