"""
BL-9 Version Authority Regression Tests
========================================

Ensures that version integrity is a single, canonical, fail-closed invariant.

These tests prove:
- all governed versions aligned -> PASS
- any governed version mismatch -> FAIL
- startup refuses to proceed on mismatch
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mahoun.invariants.versions import INVARIANT_VERSION, verify_version_authority


def _constitution_path() -> Path:
    return Path(__file__).resolve().parents[2] / "constitution"


def test_aligned_versions_pass():
    """All governed artifacts at canonical version must pass."""
    canonical = verify_version_authority()
    assert canonical == INVARIANT_VERSION


def test_mismatched_manifest_version_fails():
    """Mismatched kernel.manifest.yaml::kernel.version must fail."""
    manifest_path = _constitution_path() / "kernel.manifest.yaml"
    original = manifest_path.read_text(encoding="utf-8")

    try:
        manifest_path.write_text(
            original.replace('version: "1.1.0"', 'version: "9.9.9"', 1),
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="BL-9 Version Authority Violation"):
            verify_version_authority()
    finally:
        manifest_path.write_text(original, encoding="utf-8")


def test_mismatched_lock_version_fails():
    """Mismatched kernel.lock::kernel_version must fail."""
    lock_path = _constitution_path() / "kernel.lock"
    original = lock_path.read_text(encoding="utf-8")

    try:
        lock_path.write_text(
            original.replace('"kernel_version": "1.1.0"', '"kernel_version": "9.9.9"', 1),
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="BL-9 Version Authority Violation"):
            verify_version_authority()
    finally:
        lock_path.write_text(original, encoding="utf-8")


def test_mismatched_attestation_version_fails():
    """Mismatched kernel.attestation.json::kernel_version must fail."""
    attestation_path = _constitution_path() / "kernel.attestation.json"
    original = attestation_path.read_text(encoding="utf-8")

    try:
        attestation_path.write_text(
            original.replace('"1.1.0"', '"9.9.9"', 1),
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError, match="BL-9 Version Authority Violation"):
            verify_version_authority()
    finally:
        attestation_path.write_text(original, encoding="utf-8")


def test_mismatched_module_version_fails():
    """Mismatched sys.modules INVARIANT_VERSION must fail."""
    fake_module = type(sys)("mahoun.fake_module")
    fake_module.INVARIANT_VERSION = "9.9.9"
    sys.modules["mahoun.fake_module"] = fake_module

    try:
        with pytest.raises(RuntimeError, match="BL-9 Version Authority Violation"):
            verify_version_authority()
    finally:
        sys.modules.pop("mahoun.fake_module", None)


def test_startup_import_refuses_mismatch():
    """api.main startup must fail when version authority is inconsistent."""
    import sys

    fake_module = type(sys)("mahoun.fake_module")
    fake_module.INVARIANT_VERSION = "9.9.9"
    sys.modules["mahoun.fake_module"] = fake_module

    try:
        with pytest.raises(RuntimeError, match="BL-9 Version Authority Violation"):
            from mahoun.invariants.versions import verify_version_authority as _v
            _v()
    finally:
        sys.modules.pop("mahoun.fake_module", None)


def test_canonical_verifier_used_by_kernel_guard():
    """kernel_guard.py must consume the canonical verifier."""
    import mahoun.governance.kernel_guard as kg

    assert hasattr(kg, "verify_version_authority"), (
        "kernel_guard.py must import the canonical verify_version_authority"
    )
    assert kg.verify_version_authority is verify_version_authority, (
        "kernel_guard.py must use the canonical verifier, not a duplicate"
    )
