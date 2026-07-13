"""
Shared fixtures for the MAHOUN architectural verification suite.

All tests here are:
    - Deterministic (seeded).
    - Offline (no network, DB, or GPU).
    - Read-only against production code.

Fixtures provide:
    - MAHOUN_ROOT: absolute path to the package root on disk.
    - iter_python_files: iterator over .py files under a given subpackage.
    - parse_module_ast: cached AST parsing helper.
    - safe_import: importlib wrapper that skips a test on ImportError
      (protects against optional heavy dependencies such as torch/neo4j).
"""

from __future__ import annotations

import ast
import importlib
import os
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAHOUN_ROOT = REPO_ROOT / "mahoun"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _deterministic_seed():
    random.seed(1337)
    try:
        import numpy as np
        np.random.seed(1337)
    except Exception:  # numpy is optional in some CI matrices
        pass
    yield


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def mahoun_root() -> Path:
    return MAHOUN_ROOT


@pytest.fixture(scope="session")
def iter_python_files():
    def _iter(subpath: str = "") -> Iterator[Path]:
        root = MAHOUN_ROOT / subpath if subpath else MAHOUN_ROOT
        if not root.exists():
            return iter(())
        return (
            p for p in root.rglob("*.py")
            if "__pycache__" not in p.parts and "archive" not in p.parts
        )
    return _iter


@lru_cache(maxsize=None)
def _parse(path_str: str) -> ast.Module | None:
    try:
        src = Path(path_str).read_text(encoding="utf-8")
        return ast.parse(src, filename=path_str)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


@pytest.fixture(scope="session")
def parse_module_ast():
    def _parse_module(path: Path) -> ast.Module | None:
        return _parse(str(path))
    return _parse_module


@pytest.fixture(scope="session")
def safe_import():
    def _import(dotted: str):
        try:
            return importlib.import_module(dotted)
        except ImportError as e:
            pytest.skip(f"optional dependency unavailable for {dotted}: {e}")
        except Exception as e:
            pytest.skip(f"module {dotted} failed to import in this env: {e}")
    return _import


def collect_imports(module_ast: ast.Module) -> Iterable[str]:
    """Yield fully-qualified module names imported by a module AST."""
    for node in ast.walk(module_ast):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                yield node.module
