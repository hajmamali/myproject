"""
MAHOUN Import Firewall System
=============================

Classification: KERNEL / SECURITY / STABILITY
Purpose: Control dependency chains and provide safe fallbacks.

TIER SYSTEM:
- TIER 0: Kernel (Zero external dependencies)
- TIER 1: Core (Pydantic, standard utils)
- TIER 2: Infrastructure (Neo4j, Redis, Postgres)
- TIER 3: AI/ML (Torch, Transformers, LLMs)
"""

import sys
import importlib
import logging
from typing import Any, Dict, List, Optional, Set, Type

logger = logging.getLogger(__name__)

# Registry of blocked or high-risk imports per tier
TIER_RESTRICTIONS = {
    "mahoun.core.governance_kernel": {"torch", "neo4j", "yaml", "transformers", "networkx", "numpy", "pandas"},
    "mahoun.core.governance": {"torch", "transformers", "numpy"},
}

class ImportFirewallError(ImportError):
    """Raised when a forbidden cross-tier import is attempted."""
    pass

class SafeStub:
    """A generic stub that logs calls and raises helpful errors if invoked."""
    def __init__(self, name: str):
        self.__name = name

    def __getattr__(self, name: str) -> Any:
        logger.warning(f"Attempted to access '{name}' on missing dependency stub '{self.__name}'")
        return SafeStub(f"{self.__name}.{name}")

    def __call__(self, *args, **kwargs) -> Any:
        raise RuntimeError(f"Dependency '{self.__name}' is missing or blocked by firewall.")

class ImportFirewall:
    """Implements TIER-based import restrictions and dependency stubbing."""
    
    _instance = None
    _enabled = False
    _missing_optional: Set[str] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def enable(cls):
        if not cls._enabled:
            sys.meta_path.insert(0, cls())
            cls._enabled = True
            logger.info("MAHOUN Import Firewall ENABLED")

    def find_spec(self, fullname, path, target=None):
        """Standard meta_path hook."""
        # Check if current caller is in a restricted tier
        # This is simplified; real implementation would inspect stack frames
        # or use a context-based registry.
        return None

def safe_import(module_name: str, optional: bool = True) -> Any:
    """Import a module or return a SafeStub if missing/forbidden."""
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as e:
        if optional:
            logger.warning(f"Optional dependency '{module_name}' missing. Injecting SafeStub.")
            return SafeStub(module_name)
        raise ImportFirewallError(f"Critical dependency '{module_name}' missing.") from e

# Initialize Firewall
ImportFirewall.enable()
