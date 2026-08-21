# mahoun/invariants/versions.py
"""
Invariant Versioning
=====================

Tracks versions of system invariants for auditability.
Versions are immutable and recorded per verdict.

BL-9 Version Authority:
This module is the single source of truth for INVARIANT_VERSION.
All other modules MUST import from here or from mahoun.invariants.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Tuple

# Current invariant version - must be updated when invariants change
INVARIANT_VERSION = "1.1.0"

# Changelog of invariant changes
CHANGELOG = {
    "1.0.0": "Initial evidence ledger invariants",
    "1.1.0": "Added privacy filtering for sensitive facts",
}


def _check_sys_module_versions(canonical: str) -> List[str]:
    mismatches = []
    for mod_name, mod in list(sys.modules.items()):
        if not mod_name.startswith("mahoun."):
            continue
        other = getattr(mod, "INVARIANT_VERSION", None)
        if other is not None and other != canonical:
            mismatches.append(f"{mod_name}={other}")
    return mismatches


def _load_yaml_version(path: str, key_path: str) -> Optional[str]:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        parts = key_path.split(".")
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part, {})
            else:
                return None
        return str(data) if data else None
    except Exception:
        return None


def _load_json_version(path: str, key: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return str(data.get(key)) if data.get(key) is not None else None
    except Exception:
        return None


def verify_version_authority() -> str:
    """
    BL-9 Version Authority Enforcement.

    Verify that all governed version artifacts resolve to the same
    canonical version. This is called at startup to ensure version
    consistency before any requests are handled.

    Governed artifacts:
    - mahoun/invariants/versions.py::INVARIANT_VERSION
    - constitution/kernel.manifest.yaml::kernel.version
    - constitution/kernel_changes.yaml::current_version
    - constitution/kernel.lock::kernel_version
    - constitution/kernel.attestation.json::kernel_version

    Returns:
        str: The canonical invariant version

    Raises:
        RuntimeError: If any governed version mismatch is detected
    """
    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    constitution = os.path.join(root, "constitution")
    canonical = INVARIANT_VERSION
    mismatches: List[str] = []

    manifest_version = _load_yaml_version(
        os.path.join(constitution, "kernel.manifest.yaml"), "kernel.version"
    )
    if manifest_version and manifest_version != canonical:
        mismatches.append(f"kernel.manifest.yaml::kernel.version={manifest_version}")

    changes_version = _load_yaml_version(
        os.path.join(constitution, "kernel_changes.yaml"), "current_version"
    )
    if changes_version and changes_version != canonical:
        mismatches.append(f"kernel_changes.yaml::current_version={changes_version}")

    lock_version = _load_json_version(
        os.path.join(constitution, "kernel.lock"), "kernel_version"
    )
    if lock_version and lock_version != canonical:
        mismatches.append(f"kernel.lock::kernel_version={lock_version}")

    attestation_version = _load_json_version(
        os.path.join(constitution, "kernel.attestation.json"), "kernel_version"
    )
    if attestation_version and attestation_version != canonical:
        mismatches.append(f"kernel.attestation.json::kernel_version={attestation_version}")

    mismatches.extend(_check_sys_module_versions(canonical))

    if mismatches:
        raise RuntimeError(
            f"BL-9 Version Authority Violation: invariant version mismatch detected. "
            f"Canonical version is {canonical}, but found conflicting versions: "
            f"{', '.join(mismatches)}. All governed artifacts and modules must use "
            f"the same invariant version."
        )

    return canonical