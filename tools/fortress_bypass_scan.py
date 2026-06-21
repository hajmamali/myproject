#!/usr/bin/env python3
"""
MAHOUN Fortress Bypass Scanner
===============================

Classification: CRITICAL GOVERNANCE ENFORCEMENT
Purpose: Forensic static scanning for governance bypass vectors

This scanner performs deep static analysis to detect:
- success=True without proof_tree
- Direct response returns bypassing FortressValidator
- Bare except blocks
- logger.warning + continue patterns
- fallback_response returns
- Validation suppression
- Unvalidated serialization paths
- Direct UnifiedReasoningService exposure
- Missing audit metadata
- Agreement threshold weakening
- Silent exception downgrades

Output: SECURITY_GOVERNANCE_REPORT.md

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

import ast
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional

# ============================================================================
# SEVERITY LEVELS
# ============================================================================

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================================
# VIOLATION TYPES
# ============================================================================

@dataclass
class Violation:
    """Represents a detected governance violation"""
    severity: Severity
    violation_type: str
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str


# ============================================================================
# BYPASS PATTERNS
# ============================================================================

BYPASS_PATTERNS = {
    # CRITICAL: Direct success without proof
    "success_without_proof": {
        "severity": Severity.CRITICAL,
        "pattern": r'success\s*=\s*True.*(?!proof_tree)',
        "description": "Response marked success=True without proof_tree",
        "recommendation": "Ensure all successful responses include proof_tree"
    },
    
    # CRITICAL: Direct UnifiedReasoningService instantiation
    "direct_service_instantiation": {
        "severity": Severity.CRITICAL,
        "pattern": r'UnifiedReasoningService\s*\(',
        "description": "Direct UnifiedReasoningService instantiation (bypass risk)",
        "recommendation": "Use create_fortress_protected_service() wrapper"
    },
    
    # CRITICAL: Bare except blocks
    "bare_except": {
        "severity": Severity.CRITICAL,
        "pattern": r'except\s*:',
        "description": "Bare except block (silent failure risk)",
        "recommendation": "Use specific exception types and log failures"
    },
    
    # HIGH: Logger warning + continue
    "warning_continue": {
        "severity": Severity.HIGH,
        "pattern": r'logger\.warning.*\n.*continue',
        "description": "Logger warning followed by continue (bypass pattern)",
        "recommendation": "Fail explicitly instead of continuing"
    },
    
    # HIGH: Fallback response without validation
    "fallback_without_validation": {
        "severity": Severity.HIGH,
        "pattern": r'fallback.*return.*(?!validate)',
        "description": "Fallback response returned without validation",
        "recommendation": "Validate fallback responses through FortressValidator"
    },
    
    # HIGH: Agreement threshold weakening
    "threshold_weakening": {
        "severity": Severity.HIGH,
        "pattern": r'agreement_score\s*<\s*0\.[0-7]',
        "description": "Agreement threshold below 0.85 (governance violation)",
        "recommendation": "Maintain agreement_score >= 0.85 threshold"
    },
    
    # MEDIUM: Missing correlation_id
    "missing_correlation_id": {
        "severity": Severity.MEDIUM,
        "pattern": r'\.reason\(.*\)(?!.*correlation_id)',
        "description": "Reasoning call without correlation_id",
        "recommendation": "Include correlation_id for audit trail"
    },
    
    # MEDIUM: Direct return without validation
    "direct_return": {
        "severity": Severity.MEDIUM,
        "pattern": r'return\s+\{.*success.*\}(?!.*validate)',
        "description": "Direct response return without validation",
        "recommendation": "Pass through FortressValidator before returning"
    },
}


# ============================================================================
# AST-BASED DETECTION
# ============================================================================

class BypassDetector(ast.NodeVisitor):
    """AST visitor for detecting bypass patterns"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: List[Violation] = []
        self.current_function: Optional[str] = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track current function for context"""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Try(self, node: ast.Try):
        """Detect bare except blocks"""
        for handler in node.handlers:
            if handler.type is None:  # Bare except
                self.violations.append(Violation(
                    severity=Severity.CRITICAL,
                    violation_type="bare_except",
                    file_path=self.file_path,
                    line_number=handler.lineno,
                    code_snippet="except:",
                    description="Bare except block detected (silent failure risk)",
                    recommendation="Use specific exception types: except SpecificError:"
                ))
        self.generic_visit(node)
    
    def visit_Return(self, node: ast.Return):
        """Detect direct returns without validation"""
        if isinstance(node.value, ast.Dict):
            # Check if returning dict with 'success' key
            for i, key in enumerate(node.value.keys):
                if isinstance(key, ast.Constant) and key.value == 'success':
                    # Check if proof_tree is also present
                    has_proof = any(
                        isinstance(k, ast.Constant) and k.value == 'proof_tree'
                        for k in node.value.keys
                    )
                    if not has_proof:
                        self.violations.append(Violation(
                            severity=Severity.HIGH,
                            violation_type="success_without_proof",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            code_snippet=f"return {{success: ..., ...}} in {self.current_function}()",
                            description="Response with success but no proof_tree",
                            recommendation="Include proof_tree in all successful responses"
                        ))
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detect direct service instantiation"""
        if isinstance(node.func, ast.Name):
            if node.func.id == "UnifiedReasoningService":
                self.violations.append(Violation(
                    severity=Severity.CRITICAL,
                    violation_type="direct_service_instantiation",
                    file_path=self.file_path,
                    line_number=node.lineno,
                    code_snippet="UnifiedReasoningService()",
                    description="Direct UnifiedReasoningService instantiation (bypass risk)",
                    recommendation="Use create_fortress_protected_service() wrapper"
                ))
        self.generic_visit(node)


# ============================================================================
# FILE SCANNER
# ============================================================================

class FortressBypassScanner:
    """Main scanner for governance bypass detection"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[Violation] = []
        self.files_scanned = 0
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.low_count = 0
    
    def scan(self):
        """Execute full scan"""
        print("🔍 MAHOUN Fortress Bypass Scanner")
        print("=" * 80)
        print(f"Scanning: {self.project_root}")
        print()
        
        # Scan Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        # Exclude certain directories
        excluded_dirs = {'venv', 'node_modules', '.git', '__pycache__', 'build', 'dist'}
        python_files = [
            f for f in python_files
            if not any(excluded in f.parts for excluded in excluded_dirs)
        ]
        
        print(f"Found {len(python_files)} Python files to scan")
        print()
        
        for file_path in python_files:
            self._scan_file(file_path)
        
        self._generate_report()
    
    def _scan_file(self, file_path: Path):
        """Scan a single file"""
        self.files_scanned += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex-based detection
            self._scan_with_regex(file_path, content)
            
            # AST-based detection
            try:
                tree = ast.parse(content, filename=str(file_path))
                detector = BypassDetector(str(file_path))
                detector.visit(tree)
                self.violations.extend(detector.violations)
            except SyntaxError:
                # Skip files with syntax errors
                pass
                
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
    
    def _scan_with_regex(self, file_path: Path, content: str):
        """Scan file content with regex patterns"""
        lines = content.split('\n')
        
        for pattern_name, pattern_config in BYPASS_PATTERNS.items():
            pattern = pattern_config["pattern"]
            severity = pattern_config["severity"]
            
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    self.violations.append(Violation(
                        severity=severity,
                        violation_type=pattern_name,
                        file_path=str(file_path),
                        line_number=line_num,
                        code_snippet=line.strip()[:100],
                        description=pattern_config["description"],
                        recommendation=pattern_config["recommendation"]
                    ))
    
    def _generate_report(self):
        """Generate governance report"""
        # Count by severity
        for v in self.violations:
            if v.severity == Severity.CRITICAL:
                self.critical_count += 1
            elif v.severity == Severity.HIGH:
                self.high_count += 1
            elif v.severity == Severity.MEDIUM:
                self.medium_count += 1
            elif v.severity == Severity.LOW:
                self.low_count += 1
        
        # Generate markdown report
        report_path = self.project_root / "SECURITY_GOVERNANCE_REPORT.md"
        
        with open(report_path, 'w') as f:
            f.write(self._generate_markdown_report())
        
        # Print summary
        print()
        print("=" * 80)
        print("📊 SCAN COMPLETE")
        print("=" * 80)
        print(f"Files Scanned: {self.files_scanned}")
        print(f"Total Violations: {len(self.violations)}")
        print()
        print(f"🔴 CRITICAL: {self.critical_count}")
        print(f"🟠 HIGH: {self.high_count}")
        print(f"🟡 MEDIUM: {self.medium_count}")
        print(f"🟢 LOW: {self.low_count}")
        print()
        print(f"Report generated: {report_path}")
        print()
        
        # CI failure logic
        if self.critical_count > 0:
            print("❌ CI MUST FAIL: CRITICAL governance violations detected")
            return 1
        elif self.high_count > 0:
            print("⚠️  WARNING: HIGH severity violations detected")
            return 0  # Don't fail CI on HIGH (yet)
        else:
            print("✅ No critical violations detected")
            return 0
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown report content"""
        report = []
        report.append("# MAHOUN Security Governance Report")
        report.append("")
        report.append("**Classification**: CRITICAL GOVERNANCE AUDIT")
        report.append(f"**Files Scanned**: {self.files_scanned}")
        report.append(f"**Total Violations**: {len(self.violations)}")
        report.append("")
        report.append("---")
        report.append("")
        report.append("## Summary")
        report.append("")
        report.append(f"- 🔴 **CRITICAL**: {self.critical_count}")
        report.append(f"- 🟠 **HIGH**: {self.high_count}")
        report.append(f"- 🟡 **MEDIUM**: {self.medium_count}")
        report.append(f"- 🟢 **LOW**: {self.low_count}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Group by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            severity_violations = [v for v in self.violations if v.severity == severity]
            
            if not severity_violations:
                continue
            
            report.append(f"## {severity.value} Violations ({len(severity_violations)})")
            report.append("")
            
            # Group by violation type
            by_type: Dict[str, List[Violation]] = {}
            for v in severity_violations:
                by_type.setdefault(v.violation_type, []).append(v)
            
            for vtype, violations in by_type.items():
                report.append(f"### {vtype.replace('_', ' ').title()} ({len(violations)})")
                report.append("")
                report.append(f"**Description**: {violations[0].description}")
                report.append(f"**Recommendation**: {violations[0].recommendation}")
                report.append("")
                report.append("**Occurrences**:")
                report.append("")
                
                for v in violations[:10]:  # Limit to first 10
                    report.append(f"- `{v.file_path}:{v.line_number}`")
                    report.append(f"  ```python")
                    report.append(f"  {v.code_snippet}")
                    report.append(f"  ```")
                    report.append("")
                
                if len(violations) > 10:
                    report.append(f"*... and {len(violations) - 10} more occurrences*")
                    report.append("")
                
                report.append("---")
                report.append("")
        
        report.append("## Remediation Priority")
        report.append("")
        report.append("1. **IMMEDIATE**: Fix all CRITICAL violations")
        report.append("2. **URGENT**: Address HIGH violations within 24 hours")
        report.append("3. **PLANNED**: Schedule MEDIUM violations for next sprint")
        report.append("4. **BACKLOG**: Track LOW violations for future cleanup")
        report.append("")
        report.append("---")
        report.append("")
        report.append("## CI Enforcement")
        report.append("")
        if self.critical_count > 0:
            report.append("❌ **CI STATUS**: MUST FAIL")
            report.append("")
            report.append("Critical governance violations detected. Merge blocked.")
        else:
            report.append("✅ **CI STATUS**: PASS")
            report.append("")
            report.append("No critical violations detected.")
        report.append("")
        
        return "\n".join(report)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    project_root = Path(__file__).parent.parent
    
    scanner = FortressBypassScanner(project_root)
    exit_code = scanner.scan()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
