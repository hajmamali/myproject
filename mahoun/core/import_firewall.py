"""
MAHOUN Import Firewall - Runtime Enforcement
===========================================

Prevents forbidden imports at runtime in production environments.
This is a runtime safety net in addition to CI checks.

ENFORCEMENT LEVELS:
- DEVELOPMENT: Warnings only
- STAGING: Block dangerous imports 
- PRODUCTION: Block ALL forbidden imports, fail-fast
"""

import os
import sys
import logging
from typing import Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)

class ImportRiskLevel(Enum):
    """Risk levels for imports"""
    SAFE = "safe"           # Always allowed
    RISKY = "risky"         # Allowed in dev, blocked in prod
    FORBIDDEN = "forbidden" # Always blocked

# Production-forbidden imports 
FORBIDDEN_IMPORTS = {
    # Direct Neo4j access (must go through governed connection)
    "neo4j": ImportRiskLevel.FORBIDDEN,
    "neo4j.GraphDatabase": ImportRiskLevel.FORBIDDEN,
    
    # Runtime evaluation (code injection risks)
    "eval": ImportRiskLevel.FORBIDDEN,
    "exec": ImportRiskLevel.FORBIDDEN,
    
    # Unsafe subprocess usage
    "subprocess": ImportRiskLevel.RISKY,
    
    # Development-only tools
    "pdb": ImportRiskLevel.RISKY,
    "ipdb": ImportRiskLevel.RISKY,
    "pudb": ImportRiskLevel.RISKY,
}

def get_environment() -> str:
    """Get current runtime environment"""
    return os.getenv("MAHOUN_ENV", "development").lower()

def is_production_environment() -> bool:
    """Check if we're in a production environment"""
    env = get_environment()
    return env in ("production", "prod", "staging", "stage")

def check_import_allowed(module_name: str, import_context: str = "") -> bool:
    """
    Check if an import is allowed in current environment.
    
    Args:
        module_name: Name of the module being imported
        import_context: Context of the import (file, function, etc.)
        
    Returns:
        True if import is allowed, False otherwise
        
    Raises:
        ImportError: In production if forbidden import is attempted
    """
    env = get_environment()
    is_prod = is_production_environment()
    
    # Check against forbidden imports
    risk_level = FORBIDDEN_IMPORTS.get(module_name, ImportRiskLevel.SAFE)
    
    if risk_level == ImportRiskLevel.FORBIDDEN:
        error_msg = (
            f"FORBIDDEN IMPORT BLOCKED: '{module_name}' is constitutionally forbidden. "
            f"Environment: {env}, Context: {import_context}"
        )
        
        if is_prod:
            logger.error(error_msg)
            raise ImportError(error_msg)
        else:
            logger.warning(f"WARNING: {error_msg} (would be blocked in production)")
            return True
    
    elif risk_level == ImportRiskLevel.RISKY and is_prod:
        error_msg = (
            f"RISKY IMPORT BLOCKED: '{module_name}' is not allowed in production. "
            f"Environment: {env}, Context: {import_context}"
        )
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    return True

# Install import hook for runtime enforcement
class MahounImportHook:
    """Import hook to enforce governance at import time"""
    
    def __init__(self):
        # Handle both dict and module builtins safely
        self.original_import = None
        
        if isinstance(__builtins__, dict):
            self.original_import = __builtins__.get('__import__')
        else:
            self.original_import = getattr(__builtins__, '__import__', None)
        
        # Fallback to builtins module if needed
        if self.original_import is None:
            import builtins
            self.original_import = builtins.__import__
        
    def install(self):
        """Install the import hook"""
        if is_production_environment():
            if isinstance(__builtins__, dict):
                __builtins__['__import__'] = self.governed_import
            else:
                __builtins__.__import__ = self.governed_import
            logger.info("🔒 MAHOUN Import Firewall ACTIVE (production mode)")
        else:
            logger.info("🔓 MAHOUN Import Firewall in warning mode (development)")
    
    def governed_import(self, name, globals_=None, locals_=None, fromlist=(), level=0):
        """Governed import wrapper"""
        # Avoid recursion for standard library imports
        # Build a comprehensive standard library list to prevent recursion
        stdlib_modules = {
            'inspect', 'sys', 'os', 'logging', 'pathlib', 'builtins', 'collections',
            'typing', 'dataclasses', 'enum', 'functools', 'itertools', 'operator',
            'warnings', 'weakref', 'contextlib', 'abc', 'atexit', 'io', 'traceback',
            'threading', 'time', 'datetime', 'hashlib', 'json', 'pickle', 're',
            'string', 'struct', 'tempfile', 'uuid', 'urllib', 'email'
        }
        
        # Always allow standard library and private modules 
        if name in stdlib_modules or name.startswith('_'):
            return self.original_import(name, globals_, locals_, fromlist, level)
        
        # Get calling context safely without recursion
        import_context = "unknown"
        try:
            # Use sys._getframe instead of inspect to avoid import recursion
            frame = sys._getframe(1)
            if frame and frame.f_code:
                import_context = f"file:{frame.f_code.co_filename}"
        except:
            import_context = "unknown"
        
        # Check if import is allowed
        check_import_allowed(name, import_context)
        
        # Perform the actual import
        return self.original_import(name, globals_, locals_, fromlist, level)

# Global import hook instance
_import_hook = MahounImportHook()

def install_import_firewall():
    """Install the import firewall globally"""
    _import_hook.install()

def check_neo4j_import_violation():
    """
    Specific check for Neo4j import violations.
    Called by CI and runtime checks.
    """
    if is_production_environment():
        # Check if neo4j is already imported
        if 'neo4j' in sys.modules:
            raise ImportError(
                "GOVERNANCE VIOLATION: neo4j module already imported in production. "
                "All graph operations must go through mahoun.graph.neo4j.connection.get_connection()"
            )

# Auto-install only when explicitly requested, not by default
# if is_production_environment():
#     install_import_firewall()