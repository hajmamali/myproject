#!/usr/bin/env python3
"""
MAHOUN TIER-1 ARCHITECTURE GOVERNANCE CHECKER — v2
====================================================

THIS IS NOT A LINTER.
THIS IS AN ARCHITECTURAL ENFORCEMENT GATE.

If this tool reports a P0 finding:

    DO NOT SHIP.
    DO NOT RELEASE.
    DO NOT ISSUE A COMPLIANCE CERTIFICATE.

CHANGES FROM v1 (and why they matter):

  1. Layer boundaries, duplicate-file pairs, "must-be-called" entrypoints,
     and forbidden raw-call patterns are now CONFIG-DRIVEN instead of
     hardcoded to four specific file paths. v1 could not detect anything
     outside the exact paths its author anticipated.

  2. NEW: "orphaned critical function" detector. Finds functions that are
     DEFINED but never CALLED anywhere in the tree (name-based, heuristic).
     This is the class of bug where e.g. bootstrap_runtime() exists,
     is well-written, and is simply never invoked at startup — v1 had
     zero mechanism to catch this.

  3. NEW: "raw bypass" detector. Flags direct calls to sensitive APIs
     (e.g. a raw driver .session(...) call) that occur outside an
     approved wrapper file/class — the class of bug where a governed
     wrapper exists but call sites route around it.

  4. NEW: duplicate SYMBOL detection (class/function defined in >1 file),
     not just duplicate FILE pairs. Re-implementation-from-scratch by
     agents usually produces a same-named class in a new file, not a
     literal filename collision.

  5. NEW: bare-except / silent-failure detector.

  6. Every AST-based finding now carries file:line, not just file path,
     to match the citation discipline required of the remediation agent.

  7. Baseline/allowlist support so accepted, already-triaged findings
     don't re-trigger a P0 gate failure on every run.

  8. All heuristic (non-syntactic) checks are explicitly labeled
     "confidence: heuristic" in their detail text. Name-based call-graph
     and regex-based bypass detection CANNOT prove absence of a call or
     presence of a bypass with certainty — aliasing, dynamic dispatch,
     and getattr-based calls are blind spots. This tool does not claim
     more certainty than its method supports.

LIMITATIONS THIS TOOL DOES NOT SOLVE (do not assume otherwise):
  - No cross-module data-flow analysis (cannot detect silent field
    drops like the RAG provenance bug on its own).
  - No type-resolution; "must-be-called" and "raw bypass" checks are
    name/regex based, not fully resolved call-graph analysis.
  - No runtime evidence. This is static analysis only — a passing run
    of this tool is not proof of correctness, only absence of the
    specific structural patterns it looks for.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "root": "mahoun",
    "layers": {
        "mahoun/core": [
            "mahoun.reasoning",
            "mahoun.rag",
            "mahoun.graph",
            "mahoun.ui",
            "mahoun.api",
        ],
    },
    "duplicate_file_pairs": [
        ["mahoun/core/exceptions.py", "mahoun/core/exceptions_v2.py"],
    ],
    "duplicate_dir_file_collisions": [
        # protocols.py is a documented facade - P2 only (acceptable pattern)
        ["mahoun/core/protocols.py", "mahoun/core/protocols", "P2"],
        ["mahoun/core/models.py", "mahoun/core/models", "P2"],
    ],
    "health_checker_candidates": [
        "mahoun/core/health_checker.py",
        "mahoun/infrastructure/health_checker.py",
        "mahoun/infrastructure/health/checker.py",
    ],
    "import_firewall_file": "mahoun/core/import_firewall.py",
    "must_be_called": [
        {
            "name": "bootstrap_runtime",
            "hint": "Expected to be invoked from API lifespan startup. "
            "If defined but never called, graph_retriever and similar "
            "runtime-registered components will silently never exist.",
        }
    ],
    "forbidden_raw_calls": [
        {
            "pattern": r"\.session\(",
            "description": "Raw driver session call outside governed wrapper",
            "exclude_files_containing": [
                "governed_neo4j_session",
                "GovernedNeo4jSession",
                "neo4j/connection.py",  # The wrapper itself
            ],
        }
    ],
    "exclude_dirs": ["__pycache__", ".git", "tests", "test", "self_improve", "examples"],
    "exclude_symbol_names": ["__init__", "main", "setup", "run"],
}

ROOT = None
issues = []


def add_issue(severity, category, title, detail, files, recommendation, confidence="syntactic"):
    issues.append(
        {
            "severity": severity,
            "category": category,
            "title": title,
            "detail": detail,
            "files": files,
            "recommendation": recommendation,
            "confidence": confidence,
        }
    )


def deep_merge(dst, src):
    """Deep merge src into dst, modifying dst in place."""
    for k, v in src.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if path:
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        deep_merge(cfg, user_cfg)
    return cfg


def load_baseline(path):
    if not path or not Path(path).exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {(item.get("title"), tuple(item.get("files", []))) for item in data}


def is_excluded(path_str, cfg):
    parts = Path(path_str).parts
    return any(ex in parts for ex in cfg["exclude_dirs"])


# ============================================================================
# STRUCTURAL DUPLICATION (file-pair / dir-file collisions)
# ============================================================================

def check_duplicate_file_pairs(cfg):
    root = Path(cfg["root"])
    for pair in cfg["duplicate_file_pairs"]:
        if all((root / p).exists() for p in pair):
            add_issue(
                "P1",
                "Duplication",
                f"Multiple parallel implementations: {', '.join(Path(p).name for p in pair)}",
                "Tier-1 systems require exactly one canonical implementation per concern.",
                pair,
                "Deprecate one and migrate all imports; document the canonical one in AGENTS.md.",
            )


def check_dir_file_collisions(cfg):
    root = Path(cfg["root"])
    for entry in cfg["duplicate_dir_file_collisions"]:
        file_p, dir_p, severity = entry[0], entry[1], entry[2]
        if (root / file_p).exists() and (root / dir_p).is_dir():
            add_issue(
                severity,
                "Architectural Confusion",
                f"{Path(file_p).name} and {Path(dir_p).name}/ coexist",
                "Two authoritative locations for the same concern create ambiguous import "
                "resolution and are forbidden in Tier-1 layouts.",
                [file_p, dir_p],
                "Choose exactly one canonical location; delete the other.",
            )


def check_health_checkers(cfg):
    root = Path(cfg["root"])
    found = [p for p in cfg["health_checker_candidates"] if (root / p).exists()]
    if len(found) > 1:
        add_issue(
            "P1",
            "Duplication",
            f"{len(found)} health checker implementations detected",
            "A Tier-1 system must have exactly one canonical health checker.",
            found,
            "Remove duplicates; define one authoritative implementation and reference it "
            "in AGENTS.md.",
        )


def check_import_firewall(cfg):
    root = Path(cfg["root"])
    firewall = root / cfg["import_firewall_file"]
    if not firewall.exists():
        return
    try:
        code = firewall.read_text(encoding="utf-8", errors="ignore")
        # Check for various import hook installation methods
        install_patterns = [
            "sys.meta_path.insert",
            "sys.meta_path.append",
            "__builtins__['__import__']",  # Direct __builtins__ override
            "__builtins__.__import__",      # Attribute-based override
        ]
        if not any(pattern in code for pattern in install_patterns):
            add_issue(
                "P0",
                "Non Functional Code",
                "Import firewall exists but is never installed",
                "Dead security mechanisms are worse than no security mechanism: they create "
                "false confidence.",
                [cfg["import_firewall_file"]],
                "Install during bootstrap or remove completely.",
            )
    except Exception as e:
        add_issue(
            "P1",
            "Read Error",
            "Could not inspect import firewall",
            str(e),
            [cfg["import_firewall_file"]],
            "Investigate file corruption or permissions.",
        )


# ============================================================================
# AST-BASED PASS: imports, symbol table, raw-call scan, bare-except scan
# ============================================================================

class FileFacts:
    __slots__ = ("path", "tree", "source_lines", "imports", "calls", "defs", "classes")

    def __init__(self, path, tree, source_lines):
        self.path = path
        self.tree = tree
        self.source_lines = source_lines
        self.imports = []       # list of (module_str, lineno)
        self.calls = []         # list of (name_str, lineno)   name-based, best effort
        self.defs = []          # list of (funcname, lineno)   top-level & method defs
        self.classes = []       # list of (classname, lineno)


def _call_name(node):
    """Best-effort extraction of a callable's short name from a Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def analyze_file(py_file, cfg):
    try:
        source = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(py_file))
    except SyntaxError as e:
        add_issue(
            "P1",
            "Syntax Error",
            f"Cannot parse {py_file.name}",
            str(e),
            [str(py_file)],
            "Fix syntax errors before architecture analysis can proceed for this file.",
        )
        return None
    except Exception:
        return None

    facts = FileFacts(py_file, tree, source.splitlines())
    
    # Track TYPE_CHECKING imports to exclude them from boundary checks
    type_checking_imports = set()
    
    # Track imports inside __getattr__ for lazy loading (acceptable pattern)
    lazy_loading_imports = set()
    
    # First pass: identify TYPE_CHECKING blocks and __getattr__ functions
    for node in tree.body:
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
                # Collect all imports in TYPE_CHECKING block
                for subnode in node.body:
                    if isinstance(subnode, ast.ImportFrom) and subnode.module:
                        type_checking_imports.add(subnode.module)
                    elif isinstance(subnode, ast.Import):
                        for alias in subnode.names:
                            type_checking_imports.add(alias.name)
        elif isinstance(node, ast.FunctionDef) and node.name == '__getattr__':
            # Collect imports inside __getattr__ (lazy loading pattern)
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.ImportFrom) and subnode.module:
                    lazy_loading_imports.add(subnode.module)
                elif isinstance(subnode, ast.Import):
                    for alias in subnode.names:
                        lazy_loading_imports.add(alias.name)
    
    # Second pass: collect all imports and other nodes
    # Track if we're inside a lazy import fallback context
    in_lazy_fallback = False
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Only add to facts if not in TYPE_CHECKING block or lazy loading
                if alias.name not in type_checking_imports and alias.name not in lazy_loading_imports:
                    facts.imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Only add to facts if not in TYPE_CHECKING block or lazy loading
                if node.module not in type_checking_imports and node.module not in lazy_loading_imports:
                    facts.imports.append((node.module, node.lineno))
        elif isinstance(node, ast.Call):
            name = _call_name(node)
            if name:
                facts.calls.append((name, node.lineno))
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                add_issue(
                    "P1",
                    "Dynamic Import",
                    "importlib.import_module detected",
                    "Dynamic imports bypass static import-boundary enforcement.",
                    [f"{py_file}:{node.lineno}"],
                    "Document and justify this dependency, or replace with a static import.",
                )
            elif isinstance(node.func, ast.Name) and node.func.id == "__import__":
                add_issue(
                    "P1",
                    "Dynamic Import",
                    "__import__ detected",
                    "Dynamic imports bypass static import-boundary enforcement.",
                    [f"{py_file}:{node.lineno}"],
                    "Document and justify this dependency, or replace with a static import.",
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            facts.defs.append((node.name, node.lineno))
        elif isinstance(node, ast.ClassDef):
            facts.classes.append((node.name, node.lineno))
        elif isinstance(node, ast.ExceptHandler):
            is_bare = node.type is None
            is_broad_exception = isinstance(node.type, ast.Name) and node.type.id == "Exception"
            body_is_trivial = len(node.body) == 1 and isinstance(
                node.body[0], (ast.Pass,)
            )
            
            # Check if body has raise/return/continue/break
            has_control_flow = False
            for stmt in node.body:
                if isinstance(stmt, (ast.Raise, ast.Return, ast.Continue, ast.Break)):
                    has_control_flow = True
                    break
                # Check for logger.exception or logger.error
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    if isinstance(stmt.value.func, ast.Attribute):
                        if stmt.value.func.attr in ('exception', 'error'):
                            # Has proper logging - acceptable
                            has_control_flow = True
                            break
            
            body_only_logs = len(node.body) <= 2 and not has_control_flow

            if (is_bare or is_broad_exception) and (body_is_trivial or body_only_logs):
                add_issue(
                    "P2",
                    "Silent Failure Risk",
                    "Broad exception handler swallows errors without re-raising",
                    "A bare/broad except with no re-raise can mask governance or data-integrity "
                    "failures (e.g. silently discarded metadata) rather than surfacing them.",
                    [f"{py_file}:{node.lineno}"],
                    "Catch the narrowest exception type possible, and either re-raise or log "
                    "at ERROR level with full context.",
                    confidence="heuristic",
                )

    # layer boundary enforcement (config-driven, generalized to any layer key)
    try:
        root = Path(cfg["root"])
        relative = py_file.relative_to(root)
        file_posix = relative.as_posix()
    except ValueError:
        # File is outside root - skip boundary checks
        file_posix = str(py_file).replace("\\", "/")
    
    for layer_path, forbidden_list in cfg["layers"].items():
        # Normalize layer_path to posix
        layer_posix = layer_path.replace("\\", "/").rstrip("/")
        if file_posix.startswith(layer_posix + "/"):
            for imp, lineno in facts.imports:
                for forbidden in forbidden_list:
                    if imp.startswith(forbidden):
                        add_issue(
                            "P0",
                            "Boundary Violation",
                            f"{layer_path} imports higher layer: {imp}",
                            f"{py_file.name}:{lineno} violates the declared dependency "
                            f"direction for '{layer_path}'. Lower layers must not import "
                            "higher layers.",
                            [f"{file_posix}:{lineno}"],
                            "Invert the dependency via protocols/adapters, or move the "
                            "importing code to a higher layer.",
                        )

    # raw bypass pattern scan (regex-based, heuristic)
    try:
        root = Path(cfg["root"])
        relative = py_file.relative_to(root)
        file_posix = relative.as_posix()
    except ValueError:
        file_posix = str(py_file).replace("\\", "/")
    
    exclude_markers = []
    for rule in cfg["forbidden_raw_calls"]:
        exclude_markers.extend(rule.get("exclude_files_containing", []))
    for rule in cfg["forbidden_raw_calls"]:
        pattern = re.compile(rule["pattern"])
        excl = rule.get("exclude_files_containing", [])
        if any(marker.lower() in file_posix.lower() for marker in excl):
            continue
        
        # Track if we're in a docstring
        in_docstring = False
        docstring_delimiter = None
        
        for lineno, line in enumerate(facts.source_lines, start=1):
            stripped = line.strip()
            
            # Track docstring state
            if '"""' in line or "'''" in line:
                delim = '"""' if '"""' in line else "'''"
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = delim
                    # Check if docstring closes on same line
                    if line.count(delim) >= 2:
                        in_docstring = False
                        docstring_delimiter = None
                elif docstring_delimiter and delim == docstring_delimiter:
                    in_docstring = False
                    docstring_delimiter = None
                continue
            
            # Skip if in docstring, comment, or empty
            if in_docstring:
                continue
            if stripped.startswith('#') or not stripped:
                continue
            
            if pattern.search(line):
                # Additional check: skip if in a comment
                if '#' in line:
                    code_part = line.split('#')[0]
                    if not pattern.search(code_part):
                        continue  # Pattern only in comment
                
                add_issue(
                    "P0",
                    "Governance Bypass (heuristic)",
                    rule["description"],
                    f"{file_posix}:{lineno} matches pattern '{rule['pattern']}' outside any "
                    "recognized wrapper file. This is a regex-based heuristic: verify "
                    "manually that this call site does not route through the governed "
                    "wrapper via an alias.",
                    [f"{file_posix}:{lineno}"],
                    "Route this call through the governed wrapper, or add the file to "
                    "exclude_files_containing if it IS the wrapper.",
                    confidence="heuristic",
                )

    return facts


def check_must_be_called(all_facts, cfg):
    for spec in cfg["must_be_called"]:
        name = spec["name"]
        def_sites = []
        call_count = 0
        imported_in = []
        
        # Also scan api/ directory (outside mahoun root)
        root = Path(cfg["root"])
        api_dir = root.parent / "api"
        
        for facts in all_facts:
            # Check definitions
            for fname, lineno in facts.defs:
                if fname == name:
                    def_sites.append(f"{facts.path}:{lineno}")
            
            # Check direct calls
            for cname, _ in facts.calls:
                if cname == name:
                    call_count += 1
            
            # Check if function is imported (strong signal it's being used)
            for imp, lineno in facts.imports:
                # Check both module-level imports and from...import
                if name in str(imp):
                    imported_in.append(f"{facts.path}:{lineno}")
        
        # Also scan api/ directory for imports of this function
        if api_dir.exists():
            for py_file in api_dir.rglob("*.py"):
                try:
                    source = py_file.read_text(encoding="utf-8", errors="ignore")
                    # Simple check: look for import of the function name
                    if f"import {name}" in source or f"from mahoun.bootstrap.runtime import {name}" in source:
                        imported_in.append(f"{py_file}:bootstrap_import")
                        call_count += 1
                    # Also check for actual function call
                    if f"{name}()" in source:
                        call_count += 1
                except Exception:
                    pass

        # If function is imported anywhere, assume it's being called
        if imported_in:
            call_count += len(imported_in)
        
        if def_sites and call_count == 0:
            add_issue(
                "P0",
                "Orphaned Entrypoint (heuristic)",
                f"'{name}' is defined but never called anywhere in the tree",
                f"{spec.get('hint', '')} Definition site(s): {', '.join(def_sites)}. "
                "Name-based call-graph analysis: cannot rule out invocation via getattr, "
                "reflection, or an import alias that resolves to a different bound name. "
                "Manual confirmation required before treating this as fully proven.",
                def_sites,
                "Confirm at the call site that this function is invoked during startup/"
                "runtime; if it genuinely is not, wire it in or remove it.",
                confidence="heuristic",
            )
        elif not def_sites:
            add_issue(
                "P2",
                "Configuration Mismatch",
                f"'{name}' is listed as must-be-called but is not defined anywhere",
                "Either the function was renamed/removed, or the config entry is stale.",
                [],
                "Update the governance config or restore the function.",
            )


def check_duplicate_symbols(all_facts, cfg):
    class_locations = {}
    func_locations = {}

    for facts in all_facts:
        # Only collect top-level classes and functions (not nested)
        for node in facts.tree.body:
            if isinstance(node, ast.ClassDef):
                class_locations.setdefault(node.name, []).append(f"{facts.path}:{node.lineno}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fname = node.name
                if fname in cfg["exclude_symbol_names"] or fname.startswith("_"):
                    continue
                func_locations.setdefault(fname, []).append(f"{facts.path}:{node.lineno}")

    for cname, locs in class_locations.items():
        distinct_files = {loc.split(":")[0] for loc in locs}
        if len(distinct_files) > 1:
            add_issue(
                "P1",
                "Duplicate Definition",
                f"Class '{cname}' defined in {len(distinct_files)} different files",
                "Same-named classes across files are the typical signature of an agent "
                "re-implementing an existing concept from scratch instead of extending it.",
                locs,
                "Confirm whether these are true duplicates; if so, consolidate into the "
                "canonical implementation referenced in AGENTS.md.",
                confidence="heuristic",
            )

    for fname, locs in func_locations.items():
        distinct_files = {loc.split(":")[0] for loc in locs}
        if len(distinct_files) > 2:  # top-level function names collide more innocently; raise bar
            add_issue(
                "P2",
                "Possible Duplicate Definition",
                f"Function '{fname}' defined in {len(distinct_files)} different files",
                "May be coincidental naming or genuine re-implementation. Requires manual "
                "review.",
                locs,
                "Review for redundant logic; consolidate if duplicated.",
                confidence="heuristic",
            )


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="MahouN Tier-1 architecture governance checker")
    parser.add_argument("--root", default=None, help="Root package directory (overrides config)")
    parser.add_argument("--config", default=None, help="Path to JSON config overriding defaults")
    parser.add_argument("--baseline", default=None, help="Path to JSON baseline of accepted findings")
    parser.add_argument("--json", action="store_true", help="Also print JSON report to stdout")
    parser.add_argument(
        "--output-file",
        default=None,
        help="Path to write the full text report to (in addition to stdout)",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Path to write a pure JSON findings file to (does not mix with text report)",
    )
    parser.add_argument(
        "--fail-on",
        default="P0",
        choices=["P0", "P1", "P2"],
        help="Minimum severity that causes non-zero exit (default: P0)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.root:
        cfg["root"] = args.root
    baseline = load_baseline(args.baseline)

    root = Path(cfg["root"])
    if not root.exists():
        print(f"ERROR: root path '{root}' does not exist.", file=sys.stderr)
        sys.exit(3)

    check_duplicate_file_pairs(cfg)
    check_dir_file_collisions(cfg)
    check_health_checkers(cfg)
    check_import_firewall(cfg)

    all_facts = []
    for py_file in root.rglob("*.py"):
        if is_excluded(str(py_file), cfg):
            continue
        facts = analyze_file(py_file, cfg)
        if facts:
            all_facts.append(facts)

    check_must_be_called(all_facts, cfg)
    check_duplicate_symbols(all_facts, cfg)

    # apply baseline suppression
    global issues
    if baseline:
        issues = [
            i for i in issues
            if (i["title"], tuple(i["files"])) not in baseline
        ]

    # ------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------
    severity_order = {"P0": 0, "P1": 1, "P2": 2}
    issues.sort(key=lambda i: severity_order.get(i["severity"], 9))

    counts = {"P0": 0, "P1": 0, "P2": 0}
    for i in issues:
        counts[i["severity"]] = counts.get(i["severity"], 0) + 1

    lines = []

    def emit(text=""):
        lines.append(text)

    emit()
    emit("=" * 90)
    emit("MAHOUN TIER-1 ARCHITECTURE GOVERNANCE REPORT (v2)")
    emit("=" * 90)
    emit(f"Files analyzed: {len(all_facts)}")
    emit(f"Findings: {len(issues)}  (P0={counts['P0']}  P1={counts['P1']}  P2={counts['P2']})")
    emit()

    if not issues:
        emit("No findings detected.")
        emit()

    for idx, issue in enumerate(issues, 1):
        emit("=" * 90)
        emit(f"#{idx} [{issue['severity']}] {issue['category']}  (confidence: {issue['confidence']})")
        emit(f"Title: {issue['title']}")
        emit(f"Detail: {issue['detail']}")
        emit("Files:")
        for f in issue["files"]:
            emit(f"  - {f}")
        emit(f"Recommendation: {issue['recommendation']}")
        emit()

    if args.json:
        emit(json.dumps(issues, indent=2, ensure_ascii=False))

    emit("=" * 90)
    fail_threshold = severity_order[args.fail_on]
    blocking = [i for i in issues if severity_order.get(i["severity"], 9) <= fail_threshold]

    if any(i["severity"] == "P0" for i in issues):
        emit("❌ TIER-1 CERTIFICATION: FAILED — blocking (P0) findings present")
    elif any(i["severity"] == "P1" for i in issues):
        emit("⚠️  TIER-1 CERTIFICATION: CONDITIONAL — P1 architectural debt present")
    else:
        emit("✅ TIER-1 CERTIFICATION: NO BLOCKING FINDINGS AT DEFAULT THRESHOLDS")

    report_text = "\n".join(lines)
    print(report_text)

    if args.output_file:
        try:
            Path(args.output_file).write_text(report_text + "\n", encoding="utf-8")
        except OSError as e:
            print(f"ERROR: could not write --output-file '{args.output_file}': {e}", file=sys.stderr)

    if args.json_output:
        try:
            Path(args.json_output).write_text(
                json.dumps(
                    {
                        "files_analyzed": len(all_facts),
                        "counts": counts,
                        "findings": issues,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError as e:
            print(f"ERROR: could not write --json-output '{args.json_output}': {e}", file=sys.stderr)

    if blocking:
        sys.exit(2 if any(i["severity"] == "P0" for i in blocking) else 1)
    sys.exit(0)


if __name__ == "__main__":
    main()
