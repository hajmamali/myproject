#!/usr/bin/env python3
"""
MAHOUN Advanced Architecture Compliance Tool
Classification: CRITICAL / CI-GATING
Purpose: Enforces layering integrity and dependency bounds based strictly on core_manifest.yaml.
"""

import ast
import sys
import yaml
from pathlib import Path

def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        print(f"Manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def check_file_imports(file_path: Path, forbidden_list: list, module_name: str) -> list:
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # e.g., import mahoun.agents
                    if alias.name.startswith("mahoun."):
                        submodule = alias.name.split(".")[1]
                        if submodule in forbidden_list:
                            violations.append(f"Line {node.lineno}: {module_name} cannot import from forbidden non-core module '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("mahoun."):
                    submodule = node.module.split(".")[1]
                    if submodule in forbidden_list:
                        violations.append(f"Line {node.lineno}: {module_name} cannot import from forbidden non-core module '{node.module}'")
    except SyntaxError as e:
        print(f"Syntax error parsing {file_path}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        
    return violations

def main():
    print("🏗️  MAHOUN Advanced Architecture Compliance Scanner starting...")
    root_dir = Path.cwd()
    core_manifest_path = root_dir / "core_manifest.yaml"
    
    try:
        manifest = load_manifest(core_manifest_path)
    except Exception as e:
        print(f"Failed to load yaml manifest: {e}. Ensure PyYAML is installed.", file=sys.stderr)
        sys.exit(1)
        
    core_modules = manifest.get("core_modules", {})
    all_violations = []
    
    for mod_name, mod_data in core_modules.items():
        mod_path_str = mod_data.get("path")
        forbidden = mod_data.get("forbidden_dependencies", [])
        adapter_files = mod_data.get("adapter_files", [])
        
        if not mod_path_str or not forbidden:
            continue
            
        mod_path = root_dir / mod_path_str
        if not mod_path.exists() or not mod_path.is_dir():
            continue
            
        # Scan all python files in this core module
        for py_file in mod_path.rglob("*.py"):
            rel_file_name = py_file.name
            
            # Exclude adapter files which are allowed to break boundaries via DI
            if rel_file_name in adapter_files:
                continue
                
            file_violations = check_file_imports(py_file, forbidden, py_file.relative_to(root_dir))
            for v in file_violations:
                all_violations.append(f"❌ ARCHITECTURE VIOLATION in {py_file.relative_to(root_dir)}: {v}")

    if all_violations:
        for v in all_violations:
            print(v, file=sys.stderr)
        print("-" * 50)
        print(f"🚨 FAILED: Found {len(all_violations)} architecture compliance violations.", file=sys.stderr)
        sys.exit(1)
        
    print("✅ Advanced Architecture compliance verified against core_manifest.yaml. Layer boundaries are intact.")
    sys.exit(0)

if __name__ == "__main__":
    main()
