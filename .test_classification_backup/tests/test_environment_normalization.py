import pytest
pytest.importorskip("pydantic_settings")
"""
Test environment enum normalization and alias handling.

This ensures backward compatibility with 'development' alias
while enforcing canonical 'dev' in runtime.
"""

import pytest
from mahoun.core.config import Environment


def test_environment_normalize_dev_aliases():
    """Test that 'dev' and 'development' normalize to DEV."""
    assert Environment.normalize("dev") == Environment.DEV
    assert Environment.normalize("development") == Environment.DEV
    assert Environment.normalize("DEV") == Environment.DEV
    assert Environment.normalize("DEVELOPMENT") == Environment.DEV


def test_environment_normalize_prod_aliases():
    """Test that 'prod' and 'production' normalize to PROD."""
    assert Environment.normalize("prod") == Environment.PROD
    assert Environment.normalize("production") == Environment.PROD
    assert Environment.normalize("PROD") == Environment.PROD
    assert Environment.normalize("PRODUCTION") == Environment.PROD


def test_environment_normalize_exact_values():
    """Test exact enum values are preserved."""
    assert Environment.normalize("staging") == Environment.STAGING
    assert Environment.normalize("test") == Environment.TEST


def test_environment_normalize_invalid_raises():
    """Test invalid environment values raise ValueError."""
    with pytest.raises(ValueError):
        Environment.normalize("invalid")
    
    with pytest.raises(ValueError):
        Environment.normalize("local")


def test_environment_production_check():
    """Test production environment detection."""
    assert Environment.PROD.is_production()
    assert Environment.PRODUCTION.is_production()
    assert Environment.STAGING.is_production()
    
    assert not Environment.DEV.is_production()
    assert not Environment.DEVELOPMENT.is_production()
    assert not Environment.TEST.is_production()
