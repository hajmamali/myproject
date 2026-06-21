"""
IMPORT FIREWALL (P0 SECURITY LAYER)
Blocks unsafe dependencies at import time.
"""

from __future__ import annotations

FORBIDDEN_IMPORTS = {
    "yaml",
    "torch",
    "torch_geometric",
    "ultra_graph_builder",
    "fortress_validator",
    "graph_query_service",
    "gnn_graph_builder",
}


def validate_import(module_name: str) -> None:
    """Validate that module import is allowed."""
    base = module_name.split(".")[0]
    
    if base in FORBIDDEN_IMPORTS:
        raise ImportError(
            f"[IMPORT FIREWALL] Blocked unsafe dependency: {module_name}"
        )


def guarded_import(name: str, *args, **kwargs):
    """Guarded import that enforces firewall rules."""
    validate_import(name)
    return _original_import(name, *args, **kwargs)


_original_import = __builtins__.__import__
__builtins__.__import__ = guarded_import


def enable_firewall() -> None:
    """Enable the import firewall."""
    global _original_import
    if __builtins__.__import__ is not guarded_import:
        _original_import = __builtins__.__import__
        __builtins__.__import__ = guarded_import


def disable_firewall() -> None:
    """Disable the import firewall."""
    global _original_import
    if __builtins__.__import__ is guarded_import:
        __builtins__.__import__ = _original_import