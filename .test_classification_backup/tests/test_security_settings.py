import pytest

from mahoun.core.settings import load_security_settings


def test_dev_defaults(monkeypatch):
    monkeypatch.setenv("MAHOUN_ENV", "dev")
    monkeypatch.delenv("MAHOUN_API_KEY", raising=False)
    monkeypatch.delenv("MAHOUN_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("MAHOUN_ALLOWED_HOSTS", raising=False)

    settings = load_security_settings()
    assert "localhost" in settings.allowed_hosts
    assert settings.api_key is None


def test_prod_requires_api_key(monkeypatch):
    monkeypatch.setenv("MAHOUN_ENV", "prod")
    monkeypatch.delenv("MAHOUN_API_KEY", raising=False)
    monkeypatch.setenv("MAHOUN_ALLOWED_ORIGINS", "https://example.com")
    monkeypatch.setenv("MAHOUN_ALLOWED_HOSTS", "example.com")

    with pytest.raises(RuntimeError):
        load_security_settings()


def test_prod_requires_origins_and_hosts(monkeypatch):
    monkeypatch.setenv("MAHOUN_ENV", "prod")
    monkeypatch.setenv("MAHOUN_API_KEY", "secret")
    monkeypatch.delenv("MAHOUN_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("MAHOUN_ALLOWED_HOSTS", raising=False)

    with pytest.raises(RuntimeError, match="MAHOUN_ALLOWED_ORIGINS is required"):
        load_security_settings()

    monkeypatch.setenv("MAHOUN_ALLOWED_ORIGINS", "https://example.com")
    with pytest.raises(RuntimeError, match="MAHOUN_ALLOWED_HOSTS is required"):
        load_security_settings()
