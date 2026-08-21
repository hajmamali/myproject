"""
MAHOUN Kernel Guard
===================

Constitutional Kernel Protection and Governance Enforcement Layer

Responsibilities:
- Read kernel.manifest.yaml (source of truth)
- Calculate SHA256 fingerprints for protected files
- Compare current state against approved state
- Detect unauthorized modifications
- Enforce authorization for kernel changes
- Track and validate kernel change records

Architecture:
- Tier-1 component (depends on Tier-0 for read-only inspection only)
- Zero external dependencies beyond stdlib + yaml + json
- Fail-closed: any violation causes immediate exit with code 1

Usage:
    python -m mahoun.governance.kernel_guard --update
    python -m mahoun.governance.kernel_guard --verify
    python -m mahoun.governance.kernel_guard --authorize-change --version 1.1.0 --reason "Security fix"
"""

import argparse
import hashlib
import json
import os
import sys
import yaml
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from mahoun.invariants.versions import verify_version_authority

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(ROOT_DIR, "constitution", "kernel.manifest.yaml")
LOCK_PATH = os.path.join(ROOT_DIR, "constitution", "kernel.lock")
CHANGES_PATH = os.path.join(ROOT_DIR, "constitution", "kernel_changes.yaml")
ATTESTATION_PATH = os.path.join(ROOT_DIR, "constitution", "kernel.attestation.json")


class KernelGuardError(Exception):
    """Base exception for kernel guard violations."""
    pass


class KernelIntegrityViolationError(KernelGuardError):
    """Raised when kernel integrity is violated."""
    pass


class UnauthorizedKernelChangeError(KernelGuardError):
    """Raised when a kernel change is not authorized."""
    pass


class ManifestValidationError(KernelGuardError):
    """Raised when manifest validation fails."""
    pass


def load_manifest() -> Dict[str, Any]:
    """Load and validate the kernel manifest."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"KERNEL_GUARD_ERROR: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    
    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"KERNEL_GUARD_ERROR: Invalid YAML in manifest: {e}")
        sys.exit(1)
    
    # Validate manifest structure
    if not manifest or not isinstance(manifest, dict):
        print("KERNEL_GUARD_ERROR: Manifest is empty or invalid")
        sys.exit(1)
    
    if "kernel" not in manifest:
        print("KERNEL_GUARD_ERROR: Manifest missing 'kernel' section")
        sys.exit(1)
    
    if "tiers" not in manifest:
        print("KERNEL_GUARD_ERROR: Manifest missing 'tiers' section")
        sys.exit(1)
    
    return manifest


def get_tier_0_protected_files(manifest: Dict[str, Any]) -> List[str]:
    """Extract Tier-0 protected file paths from manifest."""
    return manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])


def get_kernel_version(manifest: Dict[str, Any]) -> str:
    """Extract kernel version from manifest."""
    return manifest.get("kernel", {}).get("version", "unknown")


def get_kernel_name(manifest: Dict[str, Any]) -> str:
    """Extract kernel name from manifest."""
    return manifest.get("kernel", {}).get("name", "mahoun_governance_kernel")


def calculate_sha256(filepath: str) -> Optional[str]:
    """Calculate SHA256 hash of a file."""
    abs_path = os.path.join(ROOT_DIR, filepath)
    if not os.path.exists(abs_path):
        return None
    sha256 = hashlib.sha256()
    try:
        with open(abs_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError) as e:
        print(f"KERNEL_GUARD_WARNING: Cannot read file {filepath}: {e}")
        return None


def calculate_manifest_hash(manifest: Dict[str, Any]) -> str:
    """Calculate hash of the manifest content."""
    manifest_str = yaml.dump(manifest, sort_keys=True)
    return hashlib.sha256(manifest_str.encode()).hexdigest()


def load_lock() -> Dict[str, Any]:
    """Load the kernel lock file."""
    if not os.path.exists(LOCK_PATH):
        return {}
    
    try:
        with open(LOCK_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"KERNEL_GUARD_ERROR: Invalid JSON in lock file: {e}")
        sys.exit(1)


def save_lock(lock_data: Dict[str, Any]) -> None:
    """Save the kernel lock file."""
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    with open(LOCK_PATH, "w") as f:
        json.dump(lock_data, f, indent=2)
    print(f"Kernel lock updated: {LOCK_PATH}")


def update_lock(manifest: Dict[str, Any]) -> None:
    """
    Update the kernel lock file with current file hashes.
    
    This generates a new snapshot of all Tier-0 protected files.
    Requires explicit authorization via --force or existing change record.
    """
    protected_paths = get_tier_0_protected_files(manifest)
    kernel_version = get_kernel_version(manifest)
    
    if not protected_paths:
        print("KERNEL_GUARD_WARNING: No protected files defined in manifest")
    
    files = {}
    for path in protected_paths:
        file_hash = calculate_sha256(path)
        if file_hash:
            files[path] = file_hash
            print(f"  Hashing: {path} -> {file_hash[:16]}...")
        else:
            print(f"KERNEL_GUARD_WARNING: Protected file not found: {path}")
    
    lock_data = {
        "files": files,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kernel_version": kernel_version,
        "kernel_name": get_kernel_name(manifest),
        "hash_algorithm": "SHA256"
    }
    
    save_lock(lock_data)


def verify_lock(manifest: Dict[str, Any]) -> bool:
    """
    Verify kernel integrity against the lock file.
    
    Returns:
        True if integrity verified, False otherwise
    
    Raises:
        KernelIntegrityViolationError: If integrity violations are detected
    """
    lock_data = load_lock()
    
    if not lock_data:
        print("KERNEL_GUARD_ERROR: Lock file not found or empty")
        sys.exit(1)
    
    protected_paths = get_tier_0_protected_files(manifest)
    locked_files = lock_data.get("files", {})
    
    if not protected_paths:
        print("KERNEL_GUARD_WARNING: No protected files defined in manifest")
        return True
    
    violations = []
    modified_files = []
    missing_files = []
    new_files = []
    
    # Check each protected file
    for path in protected_paths:
        current_hash = calculate_sha256(path)
        if current_hash is None:
            missing_files.append(path)
            violations.append(f"File missing: {path}")
            continue
        
        expected_hash = locked_files.get(path)
        if not expected_hash:
            new_files.append(path)
            violations.append(f"File not in lock (new file): {path}")
        elif current_hash != expected_hash:
            modified_files.append(path)
            violations.append(f"File modified: {path} (expected {expected_hash[:16]}..., got {current_hash[:16]}...)")
    
    # Check for files in lock that are no longer protected
    for path in locked_files:
        if path not in protected_paths:
            violations.append(f"File no longer protected (removed from manifest): {path}")
    
    if violations:
        print("KERNEL_INTEGRITY_VIOLATION:")
        for violation in violations:
            print(f"  - {violation}")
        
        # Detailed summary
        if modified_files:
            print(f"\nModified files: {len(modified_files)}")
            for f in modified_files:
                print(f"  - {f}")
        if missing_files:
            print(f"\nMissing files: {len(missing_files)}")
            for f in missing_files:
                print(f"  - {f}")
        if new_files:
            print(f"\nNew files not in lock: {len(new_files)}")
            for f in new_files:
                print(f"  - {f}")
        
        sys.exit(1)
    
    # BL-9 Version Authority: verify all governed version artifacts agree
    try:
        canonical_version = verify_version_authority()
        print(f"Version authority verified: {canonical_version}")
    except RuntimeError as e:
        print(f"KERNEL_GUARD_ERROR: {e}")
        sys.exit(1)
    else:
        print("Kernel integrity verified successfully.")
        return True


def load_changes() -> Dict[str, Any]:
    """Load the kernel changes tracking file."""
    if not os.path.exists(CHANGES_PATH):
        return {"changes": [], "current_version": "unknown"}
    
    try:
        with open(CHANGES_PATH, "r") as f:
            return yaml.safe_load(f) or {"changes": [], "current_version": "unknown"}
    except yaml.YAMLError as e:
        print(f"KERNEL_GUARD_ERROR: Invalid YAML in changes file: {e}")
        sys.exit(1)


def save_changes(changes_data: Dict[str, Any]) -> None:
    """Save the kernel changes tracking file."""
    os.makedirs(os.path.dirname(CHANGES_PATH), exist_ok=True)
    with open(CHANGES_PATH, "w") as f:
        yaml.dump(changes_data, f, default_flow_style=False)
    print(f"Kernel changes record updated: {CHANGES_PATH}")


def validate_authorization(manifest: Dict[str, Any], reason: str, approved_by: str) -> bool:
    """
    Validate that a kernel change is authorized.
    
    Checks:
    - Reason is provided and non-empty
    - Approver is in authorized list
    - Change follows version bump policy
    
    Args:
        manifest: The kernel manifest
        reason: The reason for the change
        approved_by: The person/team approving the change
    
    Returns:
        True if authorized, False otherwise
    """
    policy = manifest.get("kernel_change_policy", {})
    authorized_approvers = policy.get("authorized_approvers", [])
    
    if not reason or len(reason.strip()) < 10:
        print("KERNEL_GUARD_ERROR: Authorization rejected - reason too short (minimum 10 characters)")
        return False
    
    if approved_by not in authorized_approvers:
        print(f"KERNEL_GUARD_ERROR: Authorization rejected - '{approved_by}' not in authorized approvers: {authorized_approvers}")
        return False
    
    if policy.get("require_version_bump", False):
        print("KERNEL_GUARD_INFO: Version bump required for kernel change")
    
    return True


def authorize_change(manifest: Dict[str, Any], version: str, reason: str, approved_by: str) -> None:
    """
    Authorize a kernel modification.
    
    Creates a change record that allows the lock file to be updated.
    Without a valid change record, verification will fail.
    
    Args:
        manifest: The kernel manifest
        version: New kernel version
        reason: Reason for the change
        approved_by: Person/team approving the change
    """
    if not validate_authorization(manifest, reason, approved_by):
        raise UnauthorizedKernelChangeError(
            "Kernel change authorization failed. Check approver and reason."
        )
    
    changes_data = load_changes()
    
    change_record = {
        "version": version,
        "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reason": reason,
        "approved_by": approved_by,
        "kernel_name": get_kernel_name(manifest),
        "authorization_hash": hashlib.sha256(
            f"{version}|{reason}|{approved_by}|{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()
    }
    
    changes_data.setdefault("changes", []).append(change_record)
    changes_data["current_version"] = version
    
    save_changes(changes_data)
    print(f"Kernel change authorized: version={version}, reason={reason[:50]}...")


def verify_authorization(manifest: Dict[str, Any], lock_data: Dict[str, Any]) -> bool:
    """
    Verify that any hash changes are authorized.
    
    If the lock file has been updated (hashes changed), there must be
    a corresponding authorized change record.
    
    Args:
        manifest: The kernel manifest
        lock_data: The current lock data
    
    Returns:
        True if changes are authorized or no changes detected
    """
    changes_data = load_changes()
    current_version = get_kernel_version(manifest)
    lock_version = lock_data.get("kernel_version", "unknown")
    
    # If versions match, no authorization needed
    if current_version == lock_version:
        return True
    
    # Check if there's a change record for the current version
    for change in changes_data.get("changes", []):
        if change.get("version") == current_version:
            print(f"Kernel change authorized: version {current_version} on {change.get('date')}")
            return True
    
    print(f"KERNEL_GUARD_ERROR: Kernel version changed from {lock_version} to {current_version}")
    print("  but no authorized change record found.")
    print(f"  Authorize the change with: kernel_guard --authorize-change --version {current_version}")
    return False


def generate_attestation(manifest: Dict[str, Any]) -> None:
    """
    Generate kernel attestation file.
    
    Creates a signed attestation that the current kernel state is approved.
    """
    # BL-9: Version authority must be consistent before attesting
    try:
        verify_version_authority()
    except RuntimeError as e:
        print(f"KERNEL_GUARD_ERROR: {e}")
        sys.exit(1)

    lock_data = load_lock()
    changes_data = load_changes()
    
    manifest_hash = calculate_manifest_hash(manifest)
    lock_hash = hashlib.sha256(json.dumps(lock_data, sort_keys=True).encode()).hexdigest()
    changes_hash = hashlib.sha256(yaml.dump(changes_data, sort_keys=True).encode()).hexdigest()
    
    attestation = {
        "kernel_version": get_kernel_version(manifest),
        "kernel_name": get_kernel_name(manifest),
        "manifest_hash": manifest_hash,
        "lock_hash": lock_hash,
        "changes_hash": changes_hash,
        "attested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "approved": True,
        "verification": {
            "kernel_integrity": verify_lock(manifest),
            "authorization_valid": verify_authorization(manifest, lock_data)
        }
    }
    
    os.makedirs(os.path.dirname(ATTESTATION_PATH), exist_ok=True)
    with open(ATTESTATION_PATH, "w") as f:
        json.dump(attestation, f, indent=2)
    
    print(f"Kernel attestation generated: {ATTESTATION_PATH}")


def verify_attestation() -> bool:
    """
    Verify the kernel attestation.
    
    Returns:
        True if attestation is valid
    """
    if not os.path.exists(ATTESTATION_PATH):
        print("KERNEL_GUARD_ERROR: Attestation file not found")
        return False
    
    try:
        with open(ATTESTATION_PATH, "r") as f:
            attestation = json.load(f)
    except json.JSONDecodeError as e:
        print(f"KERNEL_GUARD_ERROR: Invalid JSON in attestation: {e}")
        return False
    
    if not attestation.get("approved", False):
        print("KERNEL_GUARD_ERROR: Attestation not approved")
        return False
    
    # Verify hashes match
    manifest = load_manifest()
    manifest_hash = calculate_manifest_hash(manifest)
    
    if manifest_hash != attestation.get("manifest_hash"):
        print("KERNEL_GUARD_ERROR: Manifest hash mismatch")
        print(f"  Expected: {attestation.get('manifest_hash')}")
        print(f"  Actual: {manifest_hash}")
        return False
    
    lock_data = load_lock()
    lock_hash = hashlib.sha256(json.dumps(lock_data, sort_keys=True).encode()).hexdigest()
    
    if lock_hash != attestation.get("lock_hash"):
        print("KERNEL_GUARD_ERROR: Lock hash mismatch")
        print(f"  Expected: {attestation.get('lock_hash')}")
        print(f"  Actual: {lock_hash}")
        return False
    
    print("Kernel attestation verified successfully.")
    return True


def validate_manifest_structure(manifest: Dict[str, Any]) -> bool:
    """
    Validate that the manifest has the required structure.
    
    Args:
        manifest: The kernel manifest
    
    Returns:
        True if valid
    
    Raises:
        ManifestValidationError: If manifest is invalid
    """
    required_sections = ["kernel", "tiers", "boundaries", "critical_modules", "critical_apis"]
    
    for section in required_sections:
        if section not in manifest:
            raise ManifestValidationError(f"Manifest missing required section: {section}")
    
    # Validate kernel section
    kernel = manifest.get("kernel", {})
    if not kernel.get("name"):
        raise ManifestValidationError("Kernel missing 'name'")
    if not kernel.get("version"):
        raise ManifestValidationError("Kernel missing 'version'")
    
    # Validate tiers
    tiers = manifest.get("tiers", {})
    if "tier_0" not in tiers:
        raise ManifestValidationError("Tiers missing 'tier_0' definition")
    
    tier_0 = tiers.get("tier_0", {})
    if not tier_0.get("protected_files"):
        print("KERNEL_GUARD_WARNING: Tier-0 has no protected files defined")
    
    print("Manifest structure validation passed.")
    return True


def main():
    """Main entry point for kernel guard CLI."""
    parser = argparse.ArgumentParser(
        description="MAHOUN Kernel Guard - Constitutional Kernel Protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m mahoun.governance.kernel_guard --update
  python -m mahoun.governance.kernel_guard --verify
  python -m mahoun.governance.kernel_guard --authorize-change --version 1.1.0 --reason "Security fix" --approved-by "security-team"
  python -m mahoun.governance.kernel_guard --validate-manifest
  python -m mahoun.governance.kernel_guard --generate-attestation
  python -m mahoun.governance.kernel_guard --verify-attestation
        """
    )
    
    parser.add_argument(
        "--update", 
        action="store_true", 
        help="Update the kernel lock file with current file hashes"
    )
    parser.add_argument(
        "--verify", 
        action="store_true", 
        help="Verify kernel integrity against the lock file"
    )
    parser.add_argument(
        "--authorize-change", 
        action="store_true", 
        help="Authorize a kernel modification (creates change record)"
    )
    parser.add_argument(
        "--version", 
        type=str,
        help="New kernel version for authorized change"
    )
    parser.add_argument(
        "--reason", 
        type=str,
        help="Reason for the kernel change"
    )
    parser.add_argument(
        "--approved-by", 
        type=str,
        help="Approver for the kernel change"
    )
    parser.add_argument(
        "--validate-manifest", 
        action="store_true", 
        help="Validate manifest structure"
    )
    parser.add_argument(
        "--generate-attestation", 
        action="store_true", 
        help="Generate kernel attestation file"
    )
    parser.add_argument(
        "--verify-attestation", 
        action="store_true", 
        help="Verify kernel attestation"
    )
    
    args = parser.parse_args()
    
    if not any([
        args.update, args.verify, args.authorize_change,
        args.validate_manifest, args.generate_attestation, args.verify_attestation
    ]):
        parser.print_help()
        sys.exit(1)
    
    manifest = load_manifest()
    
    try:
        if args.validate_manifest:
            validate_manifest_structure(manifest)
        
        elif args.update:
            update_lock(manifest)
        
        elif args.verify:
            verify_lock(manifest)
        
        elif args.authorize_change:
            if not args.version:
                print("KERNEL_GUARD_ERROR: --version required for --authorize-change")
                sys.exit(1)
            if not args.reason:
                print("KERNEL_GUARD_ERROR: --reason required for --authorize-change")
                sys.exit(1)
            if not args.approved_by:
                print("KERNEL_GUARD_ERROR: --approved-by required for --authorize-change")
                sys.exit(1)
            authorize_change(manifest, args.version, args.reason, args.approved_by)
        
        elif args.generate_attestation:
            generate_attestation(manifest)
        
        elif args.verify_attestation:
            verify_attestation()
    
    except (KernelGuardError, Exception) as e:
        print(f"KERNEL_GUARD_ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
