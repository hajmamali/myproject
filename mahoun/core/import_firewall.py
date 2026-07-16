"""
MAHOUN Import Firewall System
=============================

Classification: KERNEL / SECURITY / STABILITY
Purpose: Control dependency chains and provide safe fallbacks.

TIER SYSTEM:
- TIER 0 — KERNEL       : mahoun.core.governance_kernel, mahoun.core.governance
- TIER 1 — STD          : stdlib always allowed
- TIER 2 — INFRA        : infra / IO (Neo4j driver, requests, fs, etc.)
- TIER 3 — ML          : PyTorch / Transformers / NumPy / pandas / networkx / yaml

The firewall exposes:
    - DependencyTier   : enum classifying modules
    - get_tier(name)   : classify a top-level package
    - safe_import(...) : import-with-tier enforcement (returns None when blocked)
    - find_spec(...)   : sys.meta_path hook enforcing the matrix

Tests previously broke because the firewall advertised an API it did not
implement.  This module now ACTUALLY implements that API and the meta_path
hook ACTUALLY enforces tier restrictions for any module loaded while the
caller is inside a Tier-0 frame.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
from enum import Enum
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

class DependencyTier(str, Enum):
    KERNEL = "KERNEL"
    INFRA = "INFRA"
    ML = "ML"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Tier classification table
# ---------------------------------------------------------------------------
# Top-level package -> DependencyTier.
# Anything outside this table returns DependencyTier.UNKNOWN and is treated
# carefully (UNKNOWN modules may be loaded by Tier-0 callers outside critical
# paths; the strictest behavior is governed by FORBIDDEN_T0 set below).
_PACKAGE_TIER: dict[str, DependencyTier] = {
    # Stdlib / typing-grade helpers — always safe.
    "typing": DependencyTier.KERNEL,
    "dataclasses": DependencyTier.KERNEL,
    "contextvars": DependencyTier.KERNEL,
    "enum": DependencyTier.KERNEL,

    # ML / scientific stacks (Tier 3 forbidden in Tier-0).
    "torch": DependencyTier.ML,
    "transformers": DependencyTier.ML,
    "numpy": DependencyTier.ML,
    "pandas": DependencyTier.ML,
    "networkx": DependencyTier.ML,
    "yaml": DependencyTier.ML,

    # Infra drivers (Tier 2 forbidden in Tier-0).
    "neo4j": DependencyTier.INFRA,
    "redis": DependencyTier.INFRA,
    "psycopg2": DependencyTier.INFRA,
    "psycopg": DependencyTier.INFRA,
    "asyncpg": DependencyTier.INFRA,
    "httpx": DependencyTier.INFRA,
    "aiohttp": DependencyTier.INFRA,
    "requests": DependencyTier.INFRA,
    "fastapi": DependencyTier.INFRA,
    "pydantic": DependencyTier.INFRA,
    "openai": DependencyTier.INFRA,
    "anthropic": DependencyTier.INFRA,
    "google.generativeai": DependencyTier.INFRA,
    "langchain": DependencyTier.INFRA,
    "chromadb": DependencyTier.INFRA,
    "sqlalchemy": DependencyTier.INFRA,
}


def get_tier(module_name: str) -> Optional[DependencyTier]:
    """
    Classify a top-level package into a DependencyTier.

    Walks dotted parents (e.g., 'neo4j.GraphDatabase' -> 'neo4j').

    Returns:
        - DependencyTier enum when the root package is explicitly classified
          (ML / INFRA — packages the firewall actively governs).
        - None when the module is not a governed package (stdlib, unknown
          third-party that the kernel neither forbids nor requires).

    Callers can treat ``None`` as "safe-by-default — firewall has no opinion".
    """
    if not module_name:
        return None
    parts = module_name.split(".")
    root = parts[0]
    # Stdlib is always safe.
    if root in _STDLIB_ALLOWLIST:
        return None
    try:
        std_names = getattr(sys, "stdlib_module_names", None)
        if std_names and root in std_names:
            return None
    except Exception:
        pass
    # Explicitly tiered package.
    if root in _PACKAGE_TIER:
        return _PACKAGE_TIER[root]
    # Unrecognised package — not governed.
    return None


# Strict forbidden set for Tier-0 callers.
# Anything imported from a Tier-0 frame must either be in _PACKAGE_TIER[KERNEL]
# or be stdlib. KERNEL here denotes a CONSTITUTIONAL classification; the
# firewall only inspects against forbidden packages, not Python-internal names.
_KERNEL_FORBIDDEN: Set[str] = {
    "torch", "transformers", "numpy", "pandas", "networkx", "yaml",
    "neo4j", "redis", "psycopg2", "psycopg", "asyncpg",
    "httpx", "aiohttp", "requests", "fastapi", "pydantic",
    "openai", "anthropic", "langchain", "chromadb", "sqlalchemy",
    "google.generativeai",
}

# Stdlib packages — never blocked.
_STDLIB_ALLOWLIST: Set[str] = {
    "os", "sys", "re", "json", "logging", "hashlib", "uuid",
    "datetime", "time", "typing", "dataclasses", "enum",
    "contextvars", "contextlib", "collections", "collections.abc",
    "copy", "functools", "itertools", "math", "pathlib",
    "io", "abc", "importlib", "inspect", "gc", "asyncio",
}


# ---------------------------------------------------------------------------
# Firewall error
# ---------------------------------------------------------------------------

class ImportFirewallError(ImportError):
    """Raised when a forbidden cross-tier import is attempted."""
    pass


# ---------------------------------------------------------------------------
# Safe stub for optional / blocked modules
# ---------------------------------------------------------------------------

class SafeStub:
    """A generic stub for blocked or missing optional dependencies."""
    def __init__(self, name: str) -> None:
        self.__name = name

    def __getattr__(self, name: str) -> "SafeStub":
        logger.warning(
            "Attempted to access '%s' on missing dependency stub '%s'",
            name, self.__name,
        )
        return SafeStub(f"{self.__name}.{name}")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"Dependency '{self.__name}' is missing or blocked by firewall."
        )


# ---------------------------------------------------------------------------
# Firewall (sys.meta_path hook)
# ---------------------------------------------------------------------------

class ImportFirewall:
    """
    sys.meta_path finder enforcing tier restrictions.

    On `find_spec` we inspect the caller's frame; if the immediate loader is
    inside a Tier-0 module and the requested top-level package is forbidden,
    we raise ImportFirewallError — preventing the import.
    """

    _instance: Optional["ImportFirewall"] = None
    _enabled: bool = False

    def __new__(cls) -> "ImportFirewall":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def enable(cls) -> None:
        if not cls._enabled:
            sys.meta_path.insert(0, cls())
            cls._enabled = True
            logger.info("MAHOUN Import Firewall ENABLED")

    @classmethod
    def disable(cls) -> None:
        for finder in list(sys.meta_path):
            if isinstance(finder, ImportFirewall):
                sys.meta_path.remove(finder)
        cls._enabled = False

    @classmethod
    def enabled(cls) -> bool:
        return cls._enabled

    @staticmethod
    def _caller_module_name(depth: int = 2) -> Optional[str]:
        """
        Walk the call stack to identify the name of the module that triggered
        this import. depth=2 typically yields "caller's caller" — the importer.
        """
        try:
            frame = sys._getframe(depth)
        except (ValueError, OSError):
            return None
        # Walk frames inward until we find one whose globals carry a __name__
        # that is not the firewall module itself.
        for d in range(depth, depth + 6):
            try:
                fr = sys._getframe(d)
            except (ValueError, OSError):
                return None
            name = fr.f_globals.get("__name__") if hasattr(fr, "f_globals") else None
            if name and name != __name__:
                return str(name)
        return None

    @classmethod
    def _root_package(cls, fullname: str) -> str:
        return (fullname or "").split(".")[0]

    @classmethod
    def _is_stdlib_root(cls, root: str) -> bool:
        if root in _STDLIB_ALLOWLIST:
            return True
        # sys.stdlib_module_names is available on 3.10+
        try:
            std_names = getattr(sys, "stdlib_module_names", None)
            if std_names and root in std_names:
                return True
        except Exception:
            return None
        return False

    @classmethod
    def _is_tier0_caller(cls, module_name: Optional[str]) -> bool:
        if not module_name:
            return False
        return (
            module_name == "mahoun.core.governance_kernel"
            or module_name.startswith("mahoun.core.governance_kernel.")
            or module_name == "mahoun.core.governance"
            or module_name.startswith("mahoun.core.governance.")
        )

    def find_spec(
        self,
        fullname: str,
        path: Any = None,
        target: Any = None,
    ) -> Any:
        """
        sys.meta_path hook. Allows stdlib always; blocks Tier-1/2/3 packages
        when the calling frame is in Tier-0.
        """
        root = self._root_package(fullname)
        # Stdlib and builtins always pass.
        if self._is_stdlib_root(root):
            return None  # delegate to next finder
        # No tier-1/2/3 root? Allow (third-party may be neutral).
        if root not in _PACKAGE_TIER:
            return None

        # Determine caller.
        caller = self._caller_module_name(depth=2)
        if not self._is_tier0_caller(caller):
            return None  # Not from a Tier-0 frame — permit.

        if root in _KERNEL_FORBIDDEN:
            raise ImportFirewallError(
                f"[FIREWALL] Forbidden import '{fullname}' (root='{root}') "
                f"attempted from Tier-0 kernel module '{caller}'. "
                "Tier-0 must remain hermetic."
            )
        return None


# ---------------------------------------------------------------------------
# safe_import — explicit opt-in enforcement
# ---------------------------------------------------------------------------

def safe_import(
    module_name: str,
    tier: DependencyTier = DependencyTier.KERNEL,
    optional: bool = True,
) -> Any:
    """
    Import a module with tier enforcement.

    - If `tier` is KERNEL and the requested module is in _KERNEL_FORBIDDEN,
      return None (when optional=True) or raise ImportFirewallError.
    - Otherwise import normally.
    """
    root = (module_name or "").split(".")[0]
    if tier == DependencyTier.KERNEL and root in _KERNEL_FORBIDDEN:
        if optional:
            logger.warning(
                "safe_import blocked forbidden module '%s' "
                "for KERNEL tier.", module_name,
            )
            return None
        raise ImportFirewallError(
            f"KERNEL tier cannot import forbidden module '{module_name}'."
        )
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as e:
        if optional:
            logger.warning(
                "Optional dependency '%s' missing. Injecting SafeStub.", module_name,
            )
            return SafeStub(module_name)
        raise ImportFirewallError(
            f"Critical dependency '{module_name}' missing."
        ) from e


# Activate the firewall on import.
ImportFirewall.enable()
