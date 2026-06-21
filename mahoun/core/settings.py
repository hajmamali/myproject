import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SecuritySettings:
    env: str
    api_key: str | None
    allowed_origins: list[str]
    allowed_hosts: list[str]


def _csv(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def load_security_settings() -> SecuritySettings:
    from mahoun.core.environment import get_current_environment
    env_context = get_current_environment()
    
    if env_context.is_production():
        env = "prod"
    elif env_context.is_staging():
        env = "staging"
    else:
        env = "dev"

    api_key = os.getenv("MAHOUN_API_KEY")
    allowed_origins = _csv("MAHOUN_ALLOWED_ORIGINS")
    allowed_hosts = _csv("MAHOUN_ALLOWED_HOSTS")

    if env == "dev":
        if not allowed_origins:
            allowed_origins = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        if not allowed_hosts:
            allowed_hosts = ["localhost", "127.0.0.1"]
    else:
        if not api_key:
            raise RuntimeError("MAHOUN_API_KEY is required in staging/prod")
        if not allowed_origins:
            raise RuntimeError("MAHOUN_ALLOWED_ORIGINS is required in staging/prod")
        if not allowed_hosts:
            raise RuntimeError("MAHOUN_ALLOWED_HOSTS is required in staging/prod")

    return SecuritySettings(
        env=env,
        api_key=api_key,
        allowed_origins=allowed_origins,
        allowed_hosts=allowed_hosts,
    )
