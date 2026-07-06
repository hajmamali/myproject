from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any


class GovernanceConfig:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = self._deep_merge({}, values or {})

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = GovernanceConfig._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    @classmethod
    def from_path(cls, path: Path) -> "GovernanceConfig":
        values: dict[str, Any] = {}
        if path.exists():
            import json

            values = json.loads(path.read_text())
        return cls(values)

    @classmethod
    def from_env(cls) -> "GovernanceConfig":
        values: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith("GOVERNANCE_"):
                values[key.lower().replace("governance_", "")]=value
        return cls(values)

    def get(self, key: str, default: Any = None) -> Any:
        current: Any = self.values
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current
