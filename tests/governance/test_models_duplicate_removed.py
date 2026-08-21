"""Regression test: mahoun/core/models.py standalone file must remain absent."""

from pathlib import Path

def test_models_duplicate_removed():
    """Duplicate models file must not be reintroduced; package is canonical."""
    assert not Path("mahoun/core/models.py").exists()
