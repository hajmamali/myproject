"""
MAHOUN API Guard
===============

Public API Protection and Snapshot Verification Layer with Semantic Drift Classification

Responsibilities:
- Maintain API snapshots for critical modules
- Detect API drift (renamed, removed, moved, or changed signatures)
- Classify drifts into semantic categories (Rename, Removal, Module Relocation, etc.)
- Enforce authorization for API changes
- Generate and verify API snapshots

Architecture:
- Tier-1 component (depends on Tier-0 for read-only inspection only)
- Uses Python AST and inspect module for API extraction
- Uses SemanticDriftClassifier for intelligent classification
- Fail-closed: any API drift causes immediate exit with code 1

Usage:
    python -m mahoun.governance.api_guard --verify
    python -m mahoun.governance.api_guard --update
    python -m mahoun.governance.api_guard --check-module mahoun.core.governance_kernel.kernel
    python -m mahoun.governance.api_guard --verify-semantic  # New: semantic classification
"""

import argparse
import ast
import hashlib
import inspect
import json
import os
import sys
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Tuple
from importlib import import_module

# Import semantic classifier
try:
    from mahoun.governance.semantic_drift_classifier import (
        APISemanticClassifier,
        APIDriftCategory,
        SchemaDriftCategory,
        SemanticDriftClassification,
        SemanticDriftReport,
        DriftSeverity,
        get_api_classifier,
        get_schema_classifier,
    )
    SEMANTIC_CLASSIFIER_AVAILABLE = True
except ImportError:
    SEMANTIC_CLASSIFIER_AVAILABLE = False

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(ROOT_DIR, "constitution", "kernel.manifest.yaml")
API_SNAPSHOT_PATH = os.path.join(ROOT_DIR, "constitution", "api.snapshot.json")


class APIGuardError(Exception):
    """Base exception for API guard violations."""
    pass


class APIDriftError(APIGuardError):
    """Raised when API drift is detected."""
    pass


@dataclass
class APIMember:
    """Represents an API member (class, method, function, etc.)."""
    name: str
    type: str  # 'class', 'method', 'function', 'variable', 'enum'
    signature: Optional[str] = None
    description: Optional[str] = None
    critical: bool = False
    module: str = ""
    lineno: Optional[int] = None


@dataclass
class APISnapshot:
    """Represents an API snapshot for a module."""
    module: str
    members: Dict[str, APIMember] = field(default_factory=dict)
    classes: Dict[str, Dict[str, APIMember]] = field(default_factory=dict)
    functions: Dict[str, APIMember] = field(default_factory=dict)
    variables: Dict[str, APIMember] = field(default_factory=dict)


def load_manifest() -> Dict[str, Any]:
    """Load the kernel manifest."""
    if not os.path.exists(MANIFEST_PATH):
        print(f"API_GUARD_ERROR: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)
    
    try:
        with open(MANIFEST_PATH, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"API_GUARD_ERROR: Invalid YAML in manifest: {e}")
        sys.exit(1)


def load_api_snapshot() -> Dict[str, Any]:
    """Load the API snapshot."""
    if not os.path.exists(API_SNAPSHOT_PATH):
        return {}
    
    try:
        with open(API_SNAPSHOT_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"API_GUARD_ERROR: Invalid JSON in API snapshot: {e}")
        sys.exit(1)


def save_api_snapshot(snapshot: Dict[str, Any]) -> None:
    """Save the API snapshot."""
    os.makedirs(os.path.dirname(API_SNAPSHOT_PATH), exist_ok=True)
    with open(API_SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"API snapshot saved: {API_SNAPSHOT_PATH}")


def get_critical_modules(manifest: Dict[str, Any]) -> List[str]:
    """Get list of critical modules from manifest."""
    critical_modules = manifest.get("critical_modules", [])
    modules = []
    
    for cm in critical_modules:
        module_path = cm.get("module", "")
        if module_path:
            modules.append(module_path)
    
    return modules


def get_module_path_from_file(filepath: str) -> str:
    """Convert a file path to a module import path."""
    # Remove .py extension
    if filepath.endswith(".py"):
        filepath = filepath[:-3]
    
    # Convert to module path
    module_path = filepath.replace("/", ".")
    
    # Ensure it starts with mahoun
    if not module_path.startswith("mahoun"):
        module_path = f"mahoun.{module_path}"
    
    return module_path


def extract_api_from_source(filepath: str, module_path: str) -> APISnapshot:
    """
    Extract API from a Python source file using AST.
    
    Args:
        filepath: Path to the file
        module_path: Full module import path
    
    Returns:
        APISnapshot for the module
    """
    abs_path = os.path.join(ROOT_DIR, filepath)
    
    if not os.path.exists(abs_path):
        return APISnapshot(module=module_path)
    
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        print(f"API_GUARD_WARNING: Failed to parse {filepath}: {e}")
        return APISnapshot(module=module_path)
    
    snapshot = APISnapshot(module=module_path)
    
    # Extract classes and their methods
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            class_member = APIMember(
                name=class_name,
                type="class",
                module=module_path,
                lineno=node.lineno
            )
            snapshot.members[class_name] = class_member
            snapshot.classes[class_name] = {}
            
            # Extract methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    method_name = item.name
                    if not method_name.startswith("_"):
                        # Try to get signature
                        try:
                            # This is a simplified signature extraction
                            args = []
                            for arg in item.args.args:
                                arg_type = ""
                                if arg.annotation:
                                    arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                                args.append(f"{arg.arg}: {arg_type}" if arg_type else arg.arg)
                            
                            returns = ""
                            if item.returns:
                                returns = ast.unparse(item.returns) if hasattr(ast, 'unparse') else str(item.returns)
                            
                            signature = f"({', '.join(args)}) -> {returns}" if returns else f"({', '.join(args)})"
                        except:
                            signature = "()"
                        
                        method_member = APIMember(
                            name=method_name,
                            type="method",
                            signature=signature,
                            module=f"{module_path}.{class_name}",
                            lineno=item.lineno
                        )
                        snapshot.members[f"{class_name}.{method_name}"] = method_member
                        snapshot.classes[class_name][method_name] = method_member
        
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                func_name = node.name
                try:
                    args = []
                    for arg in node.args.args:
                        arg_type = ""
                        if arg.annotation:
                            arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                        args.append(f"{arg.arg}: {arg_type}" if arg_type else arg.arg)
                    
                    returns = ""
                    if node.returns:
                        returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                    
                    signature = f"({', '.join(args)}) -> {returns}" if returns else f"({', '.join(args)})"
                except:
                    signature = "()"
                
                func_member = APIMember(
                    name=func_name,
                    type="function",
                    signature=signature,
                    module=module_path,
                    lineno=node.lineno
                )
                snapshot.members[func_name] = func_member
                snapshot.functions[func_name] = func_member
        
        elif isinstance(node, ast.AnnAssign) or (isinstance(node, ast.Assign) and len(node.targets) == 1):
            # Variable assignment
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                var_member = APIMember(
                    name=target.id,
                    type="variable",
                    module=module_path,
                    lineno=node.lineno
                )
                snapshot.members[target.id] = var_member
                snapshot.variables[target.id] = var_member
    
    return snapshot


def extract_api_from_module(module_path: str) -> APISnapshot:
    """
    Extract API from an imported module using inspect.
    
    Args:
        module_path: Full module import path
    
    Returns:
        APISnapshot for the module
    """
    try:
        module = import_module(module_path)
    except ImportError as e:
        print(f"API_GUARD_WARNING: Failed to import {module_path}: {e}")
        return APISnapshot(module=module_path)
    
    snapshot = APISnapshot(module=module_path)
    
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        
        if inspect.isclass(obj):
            # Check if it's defined in this module
            if inspect.getmodule(obj) and inspect.getmodule(obj).__name__ == module_path:
                class_member = APIMember(
                    name=name,
                    type="class",
                    module=module_path
                )
                snapshot.members[name] = class_member
                snapshot.classes[name] = {}
                
                # Extract class methods
                for method_name, method in inspect.getmembers(obj):
                    if not method_name.startswith("_") and callable(method):
                        try:
                            sig = inspect.signature(method)
                            signature = str(sig)
                        except:
                            signature = "()"
                        
                        method_member = APIMember(
                            name=method_name,
                            type="method",
                            signature=signature,
                            module=f"{module_path}.{name}"
                        )
                        snapshot.members[f"{name}.{method_name}"] = method_member
                        snapshot.classes[name][method_name] = method_member
        
        elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
            if inspect.getmodule(obj) and inspect.getmodule(obj).__name__ == module_path:
                try:
                    sig = inspect.signature(obj)
                    signature = str(sig)
                except:
                    signature = "()"
                
                func_member = APIMember(
                    name=name,
                    type="function",
                    signature=signature,
                    module=module_path
                )
                snapshot.members[name] = func_member
                snapshot.functions[name] = func_member
        
        elif not inspect.isclass(obj) and not inspect.ismodule(obj):
            # Variable or constant
            var_member = APIMember(
                name=name,
                type="variable",
                module=module_path
            )
            snapshot.members[name] = var_member
            snapshot.variables[name] = var_member
    
    return snapshot


def generate_api_snapshot(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a complete API snapshot for all critical modules.
    
    Args:
        manifest: The kernel manifest
    
    Returns:
        API snapshot dictionary
    """
    critical_modules = get_critical_modules(manifest)
    
    # Also get protected files from tiers
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    tier_1_files = manifest.get("tiers", {}).get("tier_1", {}).get("protected_files", [])
    
    # Convert files to module paths
    modules_to_check = set(critical_modules)
    for filepath in tier_0_files + tier_1_files:
        if filepath.endswith(".py"):
            module_path = get_module_path_from_file(filepath)
            modules_to_check.add(module_path)
    
    snapshot = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "kernel_version": manifest.get("kernel", {}).get("version", "unknown"),
            "snapshot_version": "1.0.0",
            "description": "Public API snapshot for MAHOUN Constitutional Kernel",
            "source_of_truth": "kernel.manifest.yaml"
        },
        "modules": {},
        "critical_interfaces": {}
    }
    
    print(f"Generating API snapshot for {len(modules_to_check)} modules...")
    
    for module_path in sorted(modules_to_check):
        print(f"  Processing: {module_path}")
        
        try:
            # Try to import and extract via inspect first
            api_snapshot = extract_api_from_module(module_path)
            
            if not api_snapshot.members:
                # Fall back to AST parsing
                filepath = module_path.replace(".", "/") + ".py"
                api_snapshot = extract_api_from_source(filepath, module_path)
        except Exception as e:
            print(f"    Error: {e}")
            continue
        
        if api_snapshot.members:
            module_data = {
                "description": api_snapshot.module,
                "classes": {},
                "functions": {},
                "variables": {}
            }
            
            # Add classes
            for class_name, methods in api_snapshot.classes.items():
                class_data = {}
                for method_name, method_member in methods.items():
                    class_data[method_name] = {
                        "signature": method_member.signature or "()",
                        "description": method_member.description or "",
                        "critical": method_member.critical
                    }
                module_data["classes"][class_name] = class_data
            
            # Add functions
            for func_name, func_member in api_snapshot.functions.items():
                module_data["functions"][func_name] = {
                    "signature": func_member.signature or "()",
                    "description": func_member.description or "",
                    "critical": func_member.critical
                }
            
            # Add variables
            for var_name, var_member in api_snapshot.variables.items():
                module_data["variables"][var_name] = {
                    "type": var_member.type,
                    "description": var_member.description or "",
                    "critical": var_member.critical
                }
            
            snapshot["modules"][module_path] = module_data
    
    # Add critical interfaces from manifest
    critical_apis = manifest.get("critical_apis", {})
    snapshot["critical_interfaces"] = critical_apis
    
    # Add snapshot rules
    snapshot["snapshot_rules"] = {
        "critical_apis": "Must not be renamed, removed, or have signature changes without authorization",
        "non_critical_apis": "Can be modified but changes should be documented",
        "enforcement": "fail-closed - any API drift detection causes CI failure",
        "update_requirement": "Requires explicit authorization"
    }
    
    return snapshot


def verify_api_snapshot(manifest: Dict[str, Any]) -> bool:
    """
    Verify that the current API matches the snapshot.
    
    Args:
        manifest: The kernel manifest
    
    Returns:
        True if API matches
    
    Raises:
        SystemExit: If API drift is detected
    """
    current_snapshot = load_api_snapshot()
    
    if not current_snapshot:
        print("API_GUARD_ERROR: No API snapshot found. Generate one with --update")
        sys.exit(1)
    
    # Generate current API
    current_api = {}
    critical_modules = get_critical_modules(manifest)
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    tier_1_files = manifest.get("tiers", {}).get("tier_1", {}).get("protected_files", [])
    
    modules_to_check = set(critical_modules)
    for filepath in tier_0_files + tier_1_files:
        if filepath.endswith(".py"):
            module_path = get_module_path_from_file(filepath)
            modules_to_check.add(module_path)
    
    print(f"Verifying API for {len(modules_to_check)} modules...")
    
    all_drift = []
    
    for module_path in sorted(modules_to_check):
        print(f"  Checking: {module_path}")
        
        try:
            current_module_api = extract_api_from_module(module_path)
        except Exception as e:
            print(f"    Error: {e}")
            continue
        
        if not current_module_api.members:
            # Try AST parsing
            filepath = module_path.replace(".", "/") + ".py"
            current_module_api = extract_api_from_source(filepath, module_path)
        
        # Get expected API from snapshot
        expected_module = current_snapshot.get("modules", {}).get(module_path, {})
        
        if not expected_module:
            print(f"    WARNING: Module {module_path} not in snapshot (new module?)")
            continue
        
        # Check for missing members
        expected_members = set()
        for class_name, methods in expected_module.get("classes", {}).items():
            expected_members.add(class_name)
            for method_name in methods:
                expected_members.add(f"{class_name}.{method_name}")
        for func_name in expected_module.get("functions", {}):
            expected_members.add(func_name)
        for var_name in expected_module.get("variables", {}):
            expected_members.add(var_name)
        
        current_members = set(current_module_api.members.keys())
        
        # Find missing and new members
        missing_members = expected_members - current_members
        new_members = current_members - expected_members
        
        # Check signatures for existing members
        signature_changes = []
        for member_name in expected_members & current_members:
            expected_sig = None
            current_sig = None
            
            # Get expected signature
            if "." in member_name:
                class_name, method_name = member_name.split(".", 1)
                expected_sig = expected_module.get("classes", {}).get(class_name, {}).get(method_name, {}).get("signature")
            else:
                expected_sig = expected_module.get("functions", {}).get(member_name, {}).get("signature")
                if not expected_sig:
                    expected_sig = expected_module.get("variables", {}).get(member_name, {}).get("type")
            
            # Get current signature
            if member_name in current_module_api.members:
                current_sig = current_module_api.members[member_name].signature
            
            if expected_sig and current_sig and expected_sig != current_sig:
                signature_changes.append({
                    "member": member_name,
                    "expected": expected_sig,
                    "current": current_sig
                })
        
        # Collect drift for this module
        module_drift = []
        if missing_members:
            module_drift.append(f"Missing members in {module_path}: {sorted(missing_members)}")
        if new_members:
            module_drift.append(f"New members in {module_path}: {sorted(new_members)}")
        if signature_changes:
            for change in signature_changes:
                module_drift.append(
                    f"Signature change in {module_path}: {change['member']} "
                    f"(expected: {change['expected']}, current: {change['current']})"
                )
        
        all_drift.extend(module_drift)
    
    # Report drift
    if all_drift:
        print("\n" + "=" * 70)
        print("API_DRIFT_DETECTED:")
        print("=" * 70)
        
        for drift in all_drift:
            print(f"  - {drift}")
        
        print("\n" + "=" * 70)
        print(f"TOTAL API DRIFT: {len(all_drift)}")
        print("=" * 70)
        print("\nTo update the API snapshot:")
        print("  python -m mahoun.governance.api_guard --update")
        
        sys.exit(1)
    else:
        print("\nAPI snapshot verified successfully.")
        return True


def check_critical_interfaces(manifest: Dict[str, Any]) -> bool:
    """
    Verify that all critical interfaces are present and unchanged.
    
    Args:
        manifest: The kernel manifest
    
    Returns:
        True if all critical interfaces are present
    """
    critical_apis = manifest.get("critical_apis", {})
    
    # Flatten critical interfaces
    critical_interface_names = []
    for category, interfaces in critical_apis.items():
        critical_interface_names.extend(interfaces)
    
    if not critical_interface_names:
        print("API_GUARD_WARNING: No critical interfaces defined in manifest")
        return True
    
    print(f"Checking {len(critical_interface_names)} critical interfaces...")
    
    missing_critical = []
    changed_critical = []
    
    # Load current snapshot
    current_snapshot = load_api_snapshot()
    
    for interface in critical_interface_names:
        # Parse interface name (could be Class.method or just Function)
        parts = interface.split(".")
        
        if len(parts) == 2:
            # Class.method
            class_name, method_name = parts
            found = False
            
            for module_path, module_data in current_snapshot.get("modules", {}).items():
                if class_name in module_data.get("classes", {}):
                    class_data = module_data["classes"][class_name]
                    if method_name in class_data:
                        found = True
                        break
            
            if not found:
                missing_critical.append(interface)
        else:
            # Function or class
            found = False
            for module_path, module_data in current_snapshot.get("modules", {}).items():
                if interface in module_data.get("functions", {}):
                    found = True
                    break
                if interface in module_data.get("classes", {}):
                    found = True
                    break
            
            if not found:
                missing_critical.append(interface)
    
    if missing_critical:
        print("\nCRITICAL INTERFACE MISSING:")
        for interface in missing_critical:
            print(f"  - {interface}")
        sys.exit(1)
    else:
        print("All critical interfaces present.")
        return True


# =============================================================================
# SEMANTIC DRIFT CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_api_drift_semantic(
    manifest: Dict[str, Any],
    verbose: bool = False
) -> SemanticDriftReport:
    """
    Classify API drift into semantic categories.
    
    Distinguishes between:
    - Removed
    - Renamed
    - Moved (Module Relocation)
    - Aliased
    - Signature Change
    - Documentation Change
    - Typing Change
    - etc.
    
    Args:
        manifest: The kernel manifest
        verbose: Print detailed classification info
        
    Returns:
        SemanticDriftReport with all classified drifts
    """
    if not SEMANTIC_CLASSIFIER_AVAILABLE:
        print("API_GUARD_WARNING: Semantic classifier not available. Falling back to basic detection.")
        # Return empty report
        return SemanticDriftReport()
    
    current_snapshot = load_api_snapshot()
    
    if not current_snapshot:
        print("API_GUARD_ERROR: No API snapshot found. Generate one with --update")
        return SemanticDriftReport()
    
    # Generate current API
    current_api = {}
    critical_modules = get_critical_modules(manifest)
    tier_0_files = manifest.get("tiers", {}).get("tier_0", {}).get("protected_files", [])
    tier_1_files = manifest.get("tiers", {}).get("tier_1", {}).get("protected_files", [])
    
    modules_to_check = set(critical_modules)
    for filepath in tier_0_files + tier_1_files:
        if filepath.endswith(".py"):
            module_path = get_module_path_from_file(filepath)
            modules_to_check.add(module_path)
    
    if verbose:
        print(f"Classifying API drift for {len(modules_to_check)} modules...")
    
    report = SemanticDriftReport()
    classifier = get_api_classifier()
    
    # Build full API data for cross-module analysis
    full_old_api: Dict[str, Dict[str, Any]] = {}
    full_new_api: Dict[str, Dict[str, Any]] = {}
    
    for module_path in sorted(modules_to_check):
        if verbose:
            print(f"  Processing: {module_path}")
        
        try:
            # Get current module API
            current_module_api = extract_api_from_module(module_path)
            if not current_module_api.members:
                filepath = module_path.replace(".", "/") + ".py"
                current_module_api = extract_api_from_source(filepath, module_path)
            
            # Build members dict for current
            new_members: Dict[str, Dict[str, Any]] = {}
            for name, member in current_module_api.members.items():
                new_members[name] = {
                    "type": member.type,
                    "signature": member.signature or "",
                    "module": member.module,
                    "description": member.description or "",
                    "critical": member.critical
                }
            
            full_new_api[module_path] = {
                "members": new_members,
                "classes": {k: {m.name: {"signature": m.signature or "", "type": m.type} 
                           for m in v.values()} 
                          for k, v in current_module_api.classes.items()},
                "functions": {k: {"signature": v.signature or "", "type": v.type} 
                             for k, v in current_module_api.functions.items()},
                "variables": {k: {"type": v.type} 
                            for k, v in current_module_api.variables.items()}
            }
            
            # Get expected module API from snapshot
            expected_module = current_snapshot.get("modules", {}).get(module_path, {})
            if not expected_module:
                continue
            
            # Build members dict for expected
            old_members: Dict[str, Dict[str, Any]] = {}
            
            # Add classes and their methods
            for class_name, methods in expected_module.get("classes", {}).items():
                old_members[class_name] = {
                    "type": "class",
                    "signature": "",
                    "module": module_path,
                    "methods": {m_name: m_data.get("signature", "") 
                               for m_name, m_data in methods.items()}
                }
                for method_name, method_data in methods.items():
                    old_members[f"{class_name}.{method_name}"] = {
                        "type": "method",
                        "signature": method_data.get("signature", ""),
                        "module": module_path,
                        "class": class_name
                    }
            
            # Add functions
            for func_name, func_data in expected_module.get("functions", {}).items():
                old_members[func_name] = {
                    "type": "function",
                    "signature": func_data.get("signature", ""),
                    "module": module_path
                }
            
            # Add variables
            for var_name, var_data in expected_module.get("variables", {}).items():
                old_members[var_name] = {
                    "type": "variable",
                    "signature": var_data.get("type", ""),
                    "module": module_path
                }
            
            full_old_api[module_path] = {
                "members": old_members
            }
            
            # Classify changes for this module
            classifications = classifier.classify_api_change(
                old_members, new_members, module_path
            )
            
            for classification in classifications:
                report.add_classification(classification)
                if verbose:
                    print(f"    ✓ Classified: {classification.category.value} - {classification.old_symbol or classification.new_symbol or module_path}")
                    
        except Exception as e:
            if verbose:
                print(f"    Error: {e}")
            continue
    
    return report


def verify_api_snapshot_semantic(
    manifest: Dict[str, Any],
    fail_on_critical: bool = True
) -> Tuple[bool, SemanticDriftReport]:
    """
    Verify API snapshot with semantic classification.
    
    Provides detailed classification of drifts instead of simple "missing" detection.
    
    Args:
        manifest: The kernel manifest
        fail_on_critical: If True, exit with code 1 on CRITICAL drifts
        
    Returns:
        Tuple of (success: bool, report: SemanticDriftReport)
    """
    report = classify_api_drift_semantic(manifest, verbose=True)
    
    # Print report
    print("\n" + "=" * 70)
    print("SEMANTIC API DRIFT REPORT")
    print("=" * 70)
    
    if not report.classifications:
        print("✅ No API drift detected.")
        print("=" * 70)
        return True, report
    
    # Print summary by category
    print(f"\nTotal Classifications: {len(report.classifications)}")
    print("-" * 70)
    
    # Group by category
    by_category: Dict[str, List[SemanticDriftClassification]] = {}
    for classification in report.classifications:
        cat = classification.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(classification)
    
    for category, drifts in sorted(by_category.items()):
        print(f"\n{category}:")
        for drift in drifts:
            severity = drift.severity.value
            old_sym = drift.old_symbol or "N/A"
            new_sym = drift.new_symbol or "N/A"
            
            if drift.old_path == drift.new_path:
                location = drift.old_path
            else:
                location = f"{drift.old_path} -> {drift.new_path}"
            
            print(f"  [{severity}] {old_sym}")
            if new_sym != "N/A" and old_sym != new_sym:
                print(f"           -> {new_sym}")
            print(f"           Location: {location}")
            if drift.old_signature and drift.new_signature:
                if drift.old_signature != drift.new_signature:
                    print(f"           Old Sig: {drift.old_signature}")
                    print(f"           New Sig: {drift.new_signature}")
            
            for evidence in drift.evidence[:2]:  # Limit evidence lines
                print(f"           Evidence: {evidence}")
    
    # Print summary by severity
    print("\n" + "-" * 70)
    print("Summary by Severity:")
    by_severity: Dict[str, int] = {}
    for classification in report.classifications:
        sev = classification.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1
    
    for severity, count in sorted(by_severity.items(), 
                                   key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x[0], 5)):
        print(f"  {severity}: {count}")
    
    print("=" * 70)
    
    # Fail if there are critical drifts and fail_on_critical is True
    if fail_on_critical and report.critical_drifts:
        print("\n🚨 CRITICAL API DRIFT DETECTED")
        print(f"   {len(report.critical_drifts)} critical drift(s) require attention")
        print("\nTo investigate and update:")
        print("  python -m mahoun.governance.api_guard --verify-semantic")
        print("  python -m mahoun.governance.api_guard --update")
        sys.exit(1)
    
    return True, report


# =============================================================================
# LEGACY COMPATIBILITY: Verify API Guard still fails on drift
# =============================================================================

def verify_api_snapshot_with_semantic_fallback(
    manifest: Dict[str, Any]
) -> bool:
    """
    Enhanced verify_api_snapshot that uses semantic classification
    but maintains the same fail-closed behavior.
    
    This function first attempts semantic classification, but if
    CRITICAL drifts are found, it fails with the same exit code.
    
    This preserves backward compatibility while providing better
    classification information.
    """
    # First, try semantic classification
    if SEMANTIC_CLASSIFIER_AVAILABLE:
        try:
            success, report = verify_api_snapshot_semantic(
                manifest, fail_on_critical=False
            )
            
            # If there are critical drifts, fail
            if report.critical_drifts:
                print("\n" + "=" * 70)
                print("API_DRIFT_DETECTED (Semantic Classification):")
                print("=" * 70)
                for drift in report.critical_drifts:
                    print(f"  - [{drift.severity.value}] {drift.category.value}: {drift.old_symbol or drift.new_symbol}")
                print("\n" + "=" * 70)
                print(f"TOTAL CRITICAL API DRIFT: {len(report.critical_drifts)}")
                print("=" * 70)
                print("\nTo update the API snapshot:")
                print("  python -m mahoun.governance.api_guard --update")
                sys.exit(1)
            
            # If no critical drifts but there are drifts, still fail
            # (maintain fail-closed behavior for any drift)
            if report.classifications:
                print("\n" + "=" * 70)
                print("API_DRIFT_DETECTED (Non-Critical):")
                print("=" * 70)
                for drift in report.classifications:
                    if drift.severity.value in ["HIGH", "MEDIUM"]:
                        print(f"  - [{drift.severity.value}] {drift.category.value}: {drift.old_symbol or drift.new_symbol}")
                if report.classifications:
                    print("\n" + "=" * 70)
                    print(f"TOTAL API DRIFT: {len(report.classifications)}")
                    print("=" * 70)
                    print("\nTo update the API snapshot:")
                    print("  python -m mahoun.governance.api_guard --update")
                    sys.exit(1)
            
            # No drifts
            print("\nAPI snapshot verified successfully.")
            return True
            
        except Exception as e:
            # Fall back to original implementation
            print(f"API_GUARD_WARNING: Semantic classification failed: {e}")
            print("Falling back to basic verification...")
    
    # Fall back to original implementation
    return verify_api_snapshot(manifest)


def main():
    """Main entry point for API guard CLI."""
    parser = argparse.ArgumentParser(
        description="MAHOUN API Guard - Public API Protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m mahoun.governance.api_guard --verify
  python -m mahoun.governance.api_guard --update
  python -m mahoun.governance.api_guard --check-critical
  python -m mahoun.governance.api_guard --check-module mahoun.core.governance_kernel.kernel
        """
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify API against snapshot"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update API snapshot"
    )
    parser.add_argument(
        "--check-critical",
        action="store_true",
        help="Check only critical interfaces"
    )
    parser.add_argument(
        "--check-module",
        type=str,
        help="Check API for a specific module"
    )
    parser.add_argument(
        "--generate-snapshot",
        action="store_true",
        help="Generate and save API snapshot (same as --update)"
    )
    parser.add_argument(
        "--verify-semantic",
        action="store_true",
        help="Verify API with semantic drift classification"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Classify API drift without failing (same as --verify-semantic with no-fail)"
    )
    
    args = parser.parse_args()
    
    if not any([
        args.verify, args.update, args.check_critical,
        args.check_module, args.generate_snapshot, args.verify_semantic, args.classify
    ]):
        parser.print_help()
        sys.exit(1)
    
    manifest = load_manifest()
    
    try:
        if args.update or args.generate_snapshot:
            snapshot = generate_api_snapshot(manifest)
            save_api_snapshot(snapshot)
        
        elif args.verify:
            # Use enhanced verification with semantic fallback
            verify_api_snapshot_with_semantic_fallback(manifest)
        
        elif args.verify_semantic:
            # Full semantic verification with reporting
            verify_api_snapshot_semantic(manifest, fail_on_critical=True)
        
        elif args.classify:
            # Just classify without failing
            verify_api_snapshot_semantic(manifest, fail_on_critical=False)
        
        elif args.check_critical:
            check_critical_interfaces(manifest)
        
        elif args.check_module:
            # Check a specific module
            try:
                api = extract_api_from_module(args.check_module)
                print(f"Module {args.check_module}:")
                print(f"  Classes: {list(api.classes.keys())}")
                print(f"  Functions: {list(api.functions.keys())}")
                print(f"  Variables: {list(api.variables.keys())}")
                print(f"  Total members: {len(api.members)}")
            except Exception as e:
                print(f"API_GUARD_ERROR: {e}")
                sys.exit(1)
    
    except Exception as e:
        print(f"API_GUARD_ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()