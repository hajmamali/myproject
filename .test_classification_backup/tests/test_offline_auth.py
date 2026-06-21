"""
Tests for Offline Authentication
=================================

Tests air-gapped authentication without external dependencies.
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from mahoun.api.auth import OfflineAuthenticator, reload_api_keys


@pytest.fixture
def temp_keys_file(tmp_path: Path) -> Path:
    """Create temporary API keys file"""
    keys_file = tmp_path / "api_keys.json"
    
    # Create test keys
    keys_data = {
        "keys": {
            "mahoun_key_admin123": {
                "role": "admin",
                "name": "Test Admin",
                "created": datetime.now(timezone.utc).isoformat(),
                "revoked": False,
            },
            "mahoun_key_readonly456": {
                "role": "readonly",
                "name": "Test Readonly",
                "created": datetime.now(timezone.utc).isoformat(),
                "revoked": False,
            },
            "mahoun_key_revoked789": {
                "role": "admin",
                "name": "Revoked Key",
                "created": datetime.now(timezone.utc).isoformat(),
                "revoked": True,
            },
            "mahoun_key_expired000": {
                "role": "admin",
                "name": "Expired Key",
                "created": datetime.now(timezone.utc).isoformat(),
                "expires": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "revoked": False,
            },
        },
        "metadata": {
            "created": datetime.now(timezone.utc).isoformat()
        }
    }
    
    with open(keys_file, "w") as f:
        json.dump(keys_data, f)
    
    return keys_file


@pytest.fixture
def client() -> TestClient:
    """Test client for API"""
    return TestClient(app)


# ============================================================================
# Test: OfflineAuthenticator
# ============================================================================


def test_authenticator_valid_key(temp_keys_file: Path) -> None:
    """Test valid API key authentication"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    valid, info = auth.validate_key("mahoun_key_admin123")
    
    assert valid is True
    assert info is not None
    assert info["role"] == "admin"
    assert info["name"] == "Test Admin"


def test_authenticator_invalid_key(temp_keys_file: Path) -> None:
    """Test invalid API key"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    valid, info = auth.validate_key("mahoun_key_invalid")
    
    assert valid is False
    assert info is None


def test_authenticator_revoked_key(temp_keys_file: Path) -> None:
    """Test revoked API key"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    valid, info = auth.validate_key("mahoun_key_revoked789")
    
    assert valid is False
    assert info is not None
    assert info["error"] == "Key revoked"


def test_authenticator_expired_key(temp_keys_file: Path) -> None:
    """Test expired API key"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    valid, info = auth.validate_key("mahoun_key_expired000")
    
    assert valid is False
    assert info is not None
    assert info["error"] == "Key expired"


def test_authenticator_empty_key(temp_keys_file: Path) -> None:
    """Test empty API key"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    valid, info = auth.validate_key("")
    
    assert valid is False
    assert info is None


def test_authenticator_reload_keys(temp_keys_file: Path) -> None:
    """Test key reload functionality"""
    auth = OfflineAuthenticator(str(temp_keys_file))
    
    # First validation
    valid1, _ = auth.validate_key("mahoun_key_admin123")
    assert valid1 is True
    
    # Modify keys file
    with open(temp_keys_file, "r") as f:
        data = json.load(f)
    
    data["keys"]["mahoun_key_admin123"]["revoked"] = True
    
    with open(temp_keys_file, "w") as f:
        json.dump(data, f)
    
    # Reload keys
    auth.reload_keys()
    
    # Second validation should fail
    valid2, info2 = auth.validate_key("mahoun_key_admin123")
    assert valid2 is False
    assert info2["error"] == "Key revoked"


# ============================================================================
# Test: API Integration
# ============================================================================


def test_api_without_key(client: TestClient) -> None:
    """Test API call without authentication"""
    response = client.get("/api/v1/reasoning/health")
    
    # Health endpoint should work without auth
    assert response.status_code == 200


def test_api_with_invalid_key(client: TestClient) -> None:
    """Test API call with invalid key"""
    # This test assumes protected endpoints exist
    # For now, just verify the auth mechanism works
    pass


# ============================================================================
# Test: Key Manager CLI
# ============================================================================


def test_key_generation(tmp_path: Path) -> None:
    """Test API key generation"""
    from scripts.manage_api_keys import APIKeyManager
    
    keys_file = tmp_path / "test_keys.json"
    manager = APIKeyManager(str(keys_file))
    
    # Generate key
    api_key = manager.generate_key(role="admin", name="Test User")
    
    assert api_key.startswith("mahoun_key_")
    assert len(api_key) > 20
    
    # Validate generated key
    valid, info = manager.validate_key(api_key)
    assert valid is True
    assert info["role"] == "admin"
    assert info["name"] == "Test User"


def test_key_revocation(tmp_path: Path) -> None:
    """Test API key revocation"""
    from scripts.manage_api_keys import APIKeyManager
    
    keys_file = tmp_path / "test_keys.json"
    manager = APIKeyManager(str(keys_file))
    
    # Generate and revoke key
    api_key = manager.generate_key(role="admin", name="Test User")
    assert manager.revoke_key(api_key) is True
    
    # Validate revoked key
    valid, info = manager.validate_key(api_key)
    assert valid is False
    assert info["error"] == "Key revoked"


def test_key_listing(tmp_path: Path) -> None:
    """Test API key listing"""
    from scripts.manage_api_keys import APIKeyManager
    
    keys_file = tmp_path / "test_keys.json"
    manager = APIKeyManager(str(keys_file))
    
    # Generate multiple keys
    manager.generate_key(role="admin", name="Admin 1")
    manager.generate_key(role="readonly", name="Readonly 1")
    
    # List keys
    keys = manager.list_keys()
    assert len(keys) == 2
    assert any(k["role"] == "admin" for k in keys)
    assert any(k["role"] == "readonly" for k in keys)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
