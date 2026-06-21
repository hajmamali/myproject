"""
Core Dependency Validator
========================

Validates that core modules maintain minimal external dependencies.
This is part of the architectural purity enforcement for the governance kernel.

ENFORCEMENT:
- Core modules should be dependency-free where possible
- External dependencies must be justified and documented
- Production deployments get stricter validation
"""

import os
import sys
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# Allowed external dependencies for core modules
CORE_ALLOWED_DEPENDENCIES = {
    "mahoun.core": {
        # Standard library only
        "os", "sys", "logging", "typing", "dataclasses", "enum", 
        "datetime", "hashlib", "hmac", "secrets", "contextvars",
        "contextlib", "functools", "threading", "asyncio", "json",
        
        # Minimal external (documented exceptions)
        "pydantic",  # For data validation - TODO: replace with custom solution
        "yaml",      # For config files - TODO: replace with json
    },
    "mahoun.core.governance": {
        # Everything from mahoun.core plus governance-specific
        "os", "sys", "logging", "typing", "dataclasses", "enum",
        "datetime", "hashlib", "hmac", "secrets", "contextvars", 
        "contextlib", "functools", "threading", "asyncio", "json",
        "pydantic", "yaml"
    }
}

def get_module_dependencies(module_name: str) -> Set[str]:
    """
    Get all dependencies for a loaded module.
    
    Args:
        module_name: Name of the module to analyze
        
    Returns:
        Set of dependency module names
    """
    if module_name not in sys.modules:
        return set()
    
    module = sys.modules[module_name]
    dependencies = set()
    
    # Get direct imports from module dict
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if hasattr(attr, '__module__'):
            dep_module = attr.__module__
            if dep_module and not dep_module.startswith(module_name):
                # Extract top-level module name
                top_level = dep_module.split('.')[0]
                dependencies.add(top_level)
    
    return dependencies

def validate_core_dependencies() -> List[str]:
    """
    Validate that core modules don't have unauthorized dependencies.
    
    Returns:
        List of violation messages (empty if all good)
    """
    violations = []
    
    for module_pattern, allowed_deps in CORE_ALLOWED_DEPENDENCIES.items():
        # Find all loaded modules matching the pattern
        matching_modules = [
            mod_name for mod_name in sys.modules.keys() 
            if mod_name.startswith(module_pattern)
        ]
        
        for module_name in matching_modules:
            actual_deps = get_module_dependencies(module_name)
            
            # Filter out standard library, internal Python modules, and allowed dependencies
            internal_modules = {'_frozen_importlib', '_frozen_importlib_external', 'builtins', '_io', '_warnings'}
            unauthorized_deps = actual_deps - allowed_deps - internal_modules
            
            if unauthorized_deps:
                violations.append(
                    f"DEPENDENCY VIOLATION: {module_name} has unauthorized dependencies: "
                    f"{sorted(unauthorized_deps)}"
                )
    
    return violations

def check_core_purity(fail_fast: bool = None) -> bool:
    """
    Check core module dependency purity.
    
    Args:
        fail_fast: If True, raise on violations. If None, use environment setting.
        
    Returns:
        True if all dependencies are authorized
        
    Raises:
        ImportError: If fail_fast=True and violations found
    """
    if fail_fast is None:
        # Default to fail-fast in production
        env = os.getenv("MAHOUN_ENV", "development").lower()
        fail_fast = env in ("production", "prod", "staging")
    
    violations = validate_core_dependencies()
    
    if violations:
        error_msg = "CORE DEPENDENCY VIOLATIONS:\n" + "\n".join(violations)
        
        if fail_fast:
            logger.error(error_msg)
            raise ImportError(error_msg)
        else:
            logger.warning(f"WARNING: {error_msg}")
            return False
    
    logger.info("✅ Core module dependencies validated - all authorized")
    return True

# Auto-check in production
env = os.getenv("MAHOUN_ENV", "development").lower()
if env in ("production", "prod"):
    # Delay check until after import phase
    import atexit
    def delayed_check():
        try:
            check_core_purity(fail_fast=True)
        except Exception as e:
            logger.error(f"Core dependency check failed: {e}")
    
    atexit.register(delayed_check)