#!/usr/bin/env python3
"""
MAHOUN Frontend Readiness Gate
================================

Executable validation script that blocks frontend development until
backend/platform contracts are stable.

Architecture Gate Principle:
- Fail closed: if any check fails, frontend development is blocked
- Every check returns: PASS/FAIL, Evidence, Failure reason, Fix recommendation
- Exit code: 0 = READY, 1 = NOT_READY

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# Repository root detection
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()


@dataclass
class CheckResult:
    """Result of a single readiness check"""
    check_id: str
    name: str
    status: str  # PASS or FAIL
    evidence: List[str]
    problem: Optional[str] = None
    fix: Optional[str] = None


@dataclass
class GateReport:
    """Complete frontend readiness report"""
    timestamp: str
    status: str  # READY or NOT_READY
    checks: List[CheckResult]
    summary: Dict[str, int] = field(default_factory=dict)

    def to_text(self) -> str:
        """Generate human-readable report"""
        lines = []
        lines.append("=" * 80)
        lines.append("MAHOUN Frontend Readiness Gate Report")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {self.timestamp}")
        lines.append(f"Status: {self.status}")
        lines.append("")
        lines.append(f"Summary: {self.summary.get('passed', 0)} passed, {self.summary.get('failed', 0)} failed")
        lines.append("-" * 80)
        
        for check in self.checks:
            status_icon = "[PASS]" if check.status == "PASS" else "[FAIL]"
            lines.append(f"\n{status_icon} {check.name}")
            lines.append(f"  Check ID: {check.check_id}")
            
            if check.evidence:
                lines.append("  Evidence:")
                for evidence in check.evidence:
                    lines.append(f"    - {evidence}")
            
            if check.problem:
                lines.append(f"  Problem: {check.problem}")
            
            if check.fix:
                lines.append(f"  Fix: {check.fix}")
        
        lines.append("\n" + "=" * 80)
        
        if self.status == "READY":
            lines.append("RESULT: Frontend development is CLEARED to proceed.")
        else:
            lines.append("RESULT: Frontend development is BLOCKED.")
            lines.append("Remediate all FAILED checks before proceeding.")
        
        lines.append("=" * 80)
        return "\n".join(lines)


class FrontendReadinessGate:
    """
    Main gate class implementing all readiness checks.
    
    Checks implemented:
    1. Bootstrap Stability
    2. Characterization Tests
    3. API Contract
    4. Backend Boundary
    5. Authentication Contract
    6. Governance Boundary
    7. Error Contract
    8. Observability
    9. Frontend Architecture Declaration
    10. API Client Readiness
    """

    CHECKS = [
        "bootstrap_stability",
        "characterization_tests",
        "api_contract",
        "boundary_enforcement",
        "auth_contract",
        "governance_boundary",
        "error_contract",
        "observability",
        "frontend_architecture",
        "sdk_readiness",
    ]

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or REPO_ROOT
        self.results: List[CheckResult] = []

    def run_all_checks(self) -> GateReport:
        """Run all readiness checks and return report"""
        self.results = []
        
        # Run each check
        self._check_bootstrap_stability()
        self._check_characterization_tests()
        self._check_api_contract()
        self._check_boundary_enforcement()
        self._check_auth_contract()
        self._check_governance_boundary()
        self._check_error_contract()
        self._check_observability()
        self._check_frontend_architecture()
        self._check_sdk_readiness()
        
        # Calculate summary
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        
        status = "READY" if failed == 0 else "NOT_READY"
        
        return GateReport(
            timestamp=datetime.now().isoformat(),
            status=status,
            checks=self.results,
            summary={"passed": passed, "failed": failed}
        )

    def _check_bootstrap_stability(self):
        """CHECK 1: Bootstrap Stability"""
        check_id = "bootstrap_stability"
        name = "Bootstrap Stability"
        
        bootstrap_dir = self.repo_root / "mahoun" / "bootstrap"
        snapshot_file = bootstrap_dir / "BEHAVIOR_SNAPSHOT.md"
        contract_file = bootstrap_dir / "bootstrap_contract.yaml"
        golden_master_dir = bootstrap_dir / "golden_master"
        
        evidence = []
        problems = []
        
        # Check if files exist
        if snapshot_file.exists():
            evidence.append(f"BEHAVIOR_SNAPSHOT.md exists at {snapshot_file}")
        else:
            problems.append("BEHAVIOR_SNAPSHOT.md not found")
        
        if contract_file.exists():
            evidence.append(f"bootstrap_contract.yaml exists at {contract_file}")
        else:
            problems.append("bootstrap_contract.yaml not found")
        
        if golden_master_dir.exists() and any(golden_master_dir.iterdir()):
            evidence.append(f"golden_master directory exists with {len(list(golden_master_dir.iterdir()))} entries")
        else:
            problems.append("golden_master directory missing or empty")
        
        # Check for unauthorized Tier-0 changes
        # Tier-0 files should not be modified without going through proper process
        tier0_files = [
            "manager.py",
            "runtime.py",
            "contract_validator.py",
        ]
        
        tier0_evidence = []
        for tf in tier0_files:
            tf_path = bootstrap_dir / tf
            if tf_path.exists():
                tier0_evidence.append(f"Tier-0 component {tf} exists")
        
        if tier0_evidence:
            evidence.append(f"Tier-0 components present: {', '.join(tier0_evidence)}")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create missing files: BEHAVIOR_SNAPSHOT.md, bootstrap_contract.yaml, and ensure golden_master/ directory has snapshots"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_characterization_tests(self):
        """CHECK 2: Characterization Tests"""
        check_id = "characterization_tests"
        name = "Characterization Tests"
        
        tests_dir = self.repo_root / "tests" / "bootstrap" / "characterization"
        golden_master_dir = self.repo_root / "mahoun" / "bootstrap" / "golden_master"
        
        evidence = []
        problems = []
        
        # Check if test directory exists
        if tests_dir.exists() and tests_dir.is_dir():
            test_files = list(tests_dir.glob("*.py"))
            if test_files:
                evidence.append(f"Characterization tests exist: {len(test_files)} test files")
                evidence.extend([f"  - {tf.name}" for tf in test_files[:5]])
                if len(test_files) > 5:
                    evidence.append(f"  ... and {len(test_files) - 5} more")
            else:
                problems.append("Characterization test directory exists but is empty")
        else:
            problems.append("Characterization tests directory not found at tests/bootstrap/characterization/")
        
        # Check if golden snapshots exist
        # Look in both mahoun/bootstrap/golden_master/ and tests/bootstrap/characterization/golden_master/
        golden_snapshot_dirs = [
            self.repo_root / "mahoun" / "bootstrap" / "golden_master",
            self.repo_root / "tests" / "bootstrap" / "characterization" / "golden_master",
        ]
        
        snapshots_found = False
        for gdir in golden_snapshot_dirs:
            if gdir.exists():
                # Look for snapshot files recursively
                golden_files = list(gdir.rglob("*.json")) + list(gdir.rglob("*.yaml")) + list(gdir.rglob("*.yml"))
                if golden_files:
                    evidence.append(f"Golden snapshots exist: {len(golden_files)} snapshot files in {gdir.relative_to(self.repo_root)}")
                    snapshots_found = True
                    break
        
        if not snapshots_found:
            problems.append("No golden snapshot files found in golden_master directories")
        
        # Try to run pytest on characterization tests
        pytest_ran = False
        pytest_passed = False
        if tests_dir.exists():
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(tests_dir), "--collect-only", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.repo_root
                )
                pytest_ran = True
                if result.returncode == 0:
                    # Count collectable tests
                    import re
                    match = re.search(r'(\d+) test', result.stdout)
                    if match:
                        test_count = match.group(1)
                        evidence.append(f"pytest collected {test_count} tests from characterization suite")
                        pytest_passed = True
                else:
                    problems.append(f"pytest collection failed: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                problems.append("pytest collection timed out")
            except Exception as e:
                problems.append(f"pytest collection error: {str(e)}")
        
        if not pytest_ran:
            problems.append("Could not verify pytest can collect characterization tests")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create characterization tests in tests/bootstrap/characterization/ and golden snapshots in mahoun/bootstrap/golden_master/"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_api_contract(self):
        """CHECK 3: API Contract"""
        check_id = "api_contract"
        name = "API Contract"
        
        api_spec_locations = [
            self.repo_root / "docs" / "api" / "openapi.yaml",
            self.repo_root / "docs" / "api" / "openapi.yml",
            self.repo_root / "docs" / "api" / "reasoning-api.yaml",
            self.repo_root / "openapi.yaml",
            self.repo_root / "openapi.yml",
        ]
        
        evidence = []
        problems = []
        
        # Check for OpenAPI specification
        spec_found = False
        for spec_path in api_spec_locations:
            if spec_path.exists():
                evidence.append(f"OpenAPI specification found at {spec_path.relative_to(self.repo_root)}")
                spec_found = True
                
                # Try to parse and validate the YAML
                try:
                    with open(spec_path) as f:
                        spec_content = yaml.safe_load(f)
                    if spec_content:
                        if "paths" in spec_content:
                            evidence.append(f"  OpenAPI spec contains {len(spec_content['paths'])} paths")
                        if "components" in spec_content:
                            comp = spec_content["components"]
                            if "schemas" in comp:
                                evidence.append(f"  OpenAPI spec contains {len(comp['schemas'])} schemas")
                            if "responses" in comp:
                                evidence.append(f"  OpenAPI spec contains {len(comp['responses'])} response definitions")
                except Exception as e:
                    problems.append(f"OpenAPI spec at {spec_path} is not valid YAML: {str(e)}")
                break
        
        if not spec_found:
            problems.append("OpenAPI specification not found in expected locations")
        
        # Check for API documentation
        api_docs = [
            self.repo_root / "docs" / "api" / "README.md",
            self.repo_root / "docs" / "API.md",
            self.repo_root / "API.md",
        ]
        
        docs_found = False
        for doc_path in api_docs:
            if doc_path.exists():
                evidence.append(f"API documentation found at {doc_path.relative_to(self.repo_root)}")
                docs_found = True
                break
        
        if not docs_found and not spec_found:
            problems.append("No API documentation found")
        
        # Check for request/response schemas
        schema_locations = [
            self.repo_root / "api" / "models",
            self.repo_root / "mahoun" / "api" / "models",
            self.repo_root / "services" / "schemas",
        ]
        
        schemas_found = False
        for schema_dir in schema_locations:
            if schema_dir.exists() and schema_dir.is_dir():
                py_files = list(schema_dir.glob("*.py"))
                if py_files:
                    evidence.append(f"Request/response schemas found in {schema_dir.relative_to(self.repo_root)}: {len(py_files)} files")
                    schemas_found = True
                    break
        
        if not schemas_found and not spec_found:
            problems.append("No request/response schema definitions found")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create OpenAPI specification at docs/api/openapi.yaml with request schemas, response schemas, and error schemas"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_boundary_enforcement(self):
        """CHECK 4: Backend Boundary - Detect forbidden coupling"""
        check_id = "boundary_enforcement"
        name = "Backend Boundary Enforcement"
        
        frontend_dir = self.repo_root / "frontend"
        
        evidence = []
        problems = []
        violations = []
        
        # Only check if frontend directory exists
        if frontend_dir.exists() and frontend_dir.is_dir():
            evidence.append(f"Frontend directory exists at {frontend_dir.relative_to(self.repo_root)}")
            
            # Define forbidden patterns - be precise to avoid false positives
            forbidden_patterns = [
                (r"from['\"]mahoun\.graph", "mahoun.graph imports"),
                (r"from['\"]mahoun\.core\.governance", "direct governance module imports"),
                (r"from['\"]mahoun\.ledger", "direct ledger module imports"),
                (r"from['\"]mahoun\.bootstrap", "direct bootstrap imports (except via API)"),
                (r"from['\"]neo4j", "neo4j module imports"),
                (r"import neo4j", "neo4j package imports"),
                (r"GraphDatabase\.driver\(", "Neo4j driver instantiation"),
            
            ]
            # Search frontend source files for violations
            frontend_src = frontend_dir / "src"
            if frontend_src.exists():
                # Check TypeScript/JavaScript files
                for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
                    for file_path in frontend_src.rglob(ext):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            for pattern, description in forbidden_patterns:
                                import re
                                if re.search(pattern, content, re.IGNORECASE):
                                    violations.append(f"{file_path.relative_to(frontend_dir)} contains {description}")
                        except Exception as e:
                            pass  # Skip files that can't be read
                
                if violations:
                    problems.append(f"Found {len(violations)} boundary violations in frontend code")
                    evidence.extend(violations[:5])  # Show first 5 violations
                    if len(violations) > 5:
                        evidence.append(f"  ... and {len(violations) - 5} more violations")
                else:
                    evidence.append("No forbidden coupling detected in frontend code")
            
            # Check if frontend uses API client abstraction
            api_client_dir = frontend_dir / "src" / "api"
            if api_client_dir.exists():
                client_files = list(api_client_dir.glob("*.ts")) + list(api_client_dir.glob("*.tsx")) + list(api_client_dir.glob("*.js"))
                if client_files:
                    evidence.append(f"API client abstraction found: {len(client_files)} files in {api_client_dir.relative_to(frontend_dir)}")
                else:
                    problems.append("No API client abstraction found in frontend/src/api/")
            else:
                problems.append("No API client directory found at frontend/src/api/")
        else:
            # Frontend directory doesn't exist - this is acceptable
            evidence.append("Frontend directory does not exist (no boundary to check)")
            
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Refactor frontend to use only API contract through client abstraction. Remove direct imports of database, Neo4j, embedding, executor, or internal service modules."
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_auth_contract(self):
        """CHECK 5: Authentication Contract"""
        check_id = "auth_contract"
        name = "Authentication Contract"
        
        auth_doc_locations = [
            self.repo_root / "docs" / "security" / "authentication.md",
            self.repo_root / "docs" / "authentication.md",
            self.repo_root / "docs" / "AUTHENTICATION.md",
            self.repo_root / "AUTHENTICATION.md",
        ]
        
        evidence = []
        problems = []
        
        # Check for authentication documentation
        auth_doc_found = False
        for doc_path in auth_doc_locations:
            if doc_path.exists():
                evidence.append(f"Authentication documentation found at {doc_path.relative_to(self.repo_root)}")
                auth_doc_found = True
                
                # Check if it contains required sections
                try:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    required_sections = [
                        ("identity", "identity model"),
                        ("role", "roles"),
                        ("permission", "permissions"),
                        ("authenticat", "authentication"),
                    ]
                    
                    found_sections = []
                    for keyword, description in required_sections:
                        if keyword in content:
                            found_sections.append(description)
                    
                    if found_sections:
                        evidence.append(f"  Documentation contains: {', '.join(found_sections)}")
                    
                    missing = [desc for keyword, desc in required_sections if keyword not in content]
                    if missing:
                        problems.append(f"Authentication documentation missing sections: {', '.join(missing)}")
                except Exception as e:
                    problems.append(f"Could not read authentication documentation: {str(e)}")
                break
        
        if not auth_doc_found:
            problems.append("Authentication documentation not found in expected locations")
        
        # Check for auth-related code
        auth_code_locations = [
            self.repo_root / "api" / "auth",
            self.repo_root / "mahoun" / "auth",
            self.repo_root / "auth",
        ]
        
        auth_code_found = False
        for auth_dir in auth_code_locations:
            if auth_dir.exists() and auth_dir.is_dir():
                auth_files = list(auth_dir.glob("*.py"))
                if auth_files:
                    evidence.append(f"Authentication code found at {auth_dir.relative_to(self.repo_root)}: {len(auth_files)} files")
                    auth_code_found = True
                    break
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create authentication documentation at docs/security/authentication.md defining identity model, roles, and permissions"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_governance_boundary(self):
        """CHECK 6: Governance Boundary - Validate API responses contain governance metadata"""
        check_id = "governance_boundary"
        name = "Governance Boundary"
        
        evidence = []
        problems = []
        
        # Check middleware for governance context injection
        governance_middleware = self.repo_root / "api" / "middleware" / "governance_context.py"
        if governance_middleware.exists():
            evidence.append(f"Governance context middleware exists at {governance_middleware.relative_to(self.repo_root)}")
            
            # Check for request_id and trace_id handling
            try:
                with open(governance_middleware, 'r') as f:
                    content = f.read()
                
                has_request_id = "request_id" in content.lower() or "request.id" in content.lower()
                has_trace_id = "trace_id" in content.lower() or "correlation_id" in content.lower()
                has_audit = "audit" in content.lower()
                has_provenance = "provenance" in content.lower() or "citation" in content.lower()
                
                if has_request_id:
                    evidence.append("  Middleware handles request_id")
                else:
                    problems.append("Governance middleware does not handle request_id")
                
                if has_trace_id:
                    evidence.append("  Middleware handles trace_id/correlation_id")
                else:
                    problems.append("Governance middleware does not handle trace_id")
                
                if has_audit:
                    evidence.append("  Middleware has audit capability")
                else:
                    problems.append("Governance middleware lacks audit capability")
            except Exception as e:
                problems.append(f"Could not analyze governance middleware: {str(e)}")
        else:
            problems.append("Governance context middleware not found at api/middleware/governance_context.py")
        
        # Check for governance context in API layer
        api_errors = self.repo_root / "mahoun" / "api" / "errors.py"
        if api_errors.exists():
            try:
                with open(api_errors, 'r') as f:
                    content = f.read()
                
                has_error_code = "error_code" in content
                has_trace_id = "trace_id" in content or "request_id" in content
                has_timestamp = "timestamp" in content
                
                if has_error_code:
                    evidence.append("  Error responses include error_code")
                if has_trace_id:
                    evidence.append("  Error responses include trace/request ID")
                if has_timestamp:
                    evidence.append("  Error responses include timestamp")
            except Exception:
                pass
        
        # Check for provenance/citation in reasoning
        reasoning_files = [
            self.repo_root / "mahoun" / "reasoning" / "rag_evidence.py",
            self.repo_root / "mahoun" / "reasoning" / "evidence_linked_verdict.py",
        ]
        
        provenance_found = False
        for rf in reasoning_files:
            if rf.exists():
                try:
                    with open(rf, 'r') as f:
                        content = f.read()
                    if "provenance" in content.lower() or "citation" in content.lower():
                        provenance_found = True
                        evidence.append(f"  Provenance/citation handling in {rf.relative_to(self.repo_root)}")
                        break
                except Exception:
                    pass
        
        if not provenance_found:
            problems.append("No provenance/citation handling found in reasoning modules")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Ensure governance middleware injects request_id, trace_id, and audit references. Add provenance/citation to API responses where applicable."
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_error_contract(self):
        """CHECK 7: Error Contract - Validate unified error format"""
        check_id = "error_contract"
        name = "Error Contract"
        
        evidence = []
        problems = []
        
        required_fields = ["error_code", "message", "trace_id", "timestamp"]
        
        # Check API error definitions
        error_files = [
            self.repo_root / "mahoun" / "api" / "errors.py",
            self.repo_root / "api" / "errors.py",
            self.repo_root / "mahoun" / "core" / "exceptions.py",
        ]
        
        error_contract_found = False
        for ef in error_files:
            if ef.exists():
                try:
                    with open(ef, 'r') as f:
                        content = f.read()
                    
                    # Check for required fields
                    found_fields = []
                    for field in required_fields:
                        if field in content:
                            found_fields.append(field)
                    
                    if len(found_fields) >= 3:  # At least 3 out of 4
                        evidence.append(f"Error contract found at {ef.relative_to(self.repo_root)} with fields: {', '.join(found_fields)}")
                        error_contract_found = True
                        
                        # Check if it's a proper class definition
                        if "class" in content and "Error" in content:
                            evidence.append("  Structured error classes defined")
                        break
                except Exception as e:
                    problems.append(f"Could not read {ef}: {str(e)}")
        
        if not error_contract_found:
            problems.append(f"No error contract found with required fields: {', '.join(required_fields)}")
        
        # Check API router error handling
        router_files = [
            self.repo_root / "api" / "routers" / "reasoning.py",
            self.repo_root / "api" / "routers" / "search.py",
        ]
        
        router_evidence = []
        for rf in router_files:
            if rf.exists():
                try:
                    with open(rf, 'r') as f:
                        content = f.read()
                    if "error" in content.lower() or "exception" in content.lower():
                        router_evidence.append(f"  Error handling in {rf.relative_to(self.repo_root)}")
                except Exception:
                    pass
        
        if router_evidence:
            evidence.extend(router_evidence)
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix=f"Define unified error format with fields: {', '.join(required_fields)} in mahoun/api/errors.py"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_observability(self):
        """CHECK 8: Observability - Validate structured logging, correlation IDs, audit"""
        check_id = "observability"
        name = "Observability"
        
        evidence = []
        problems = []
        
        # Check for structured logging
        logging_files = [
            self.repo_root / "mahoun" / "core" / "logging.py",
            self.repo_root / "core" / "logging.py",
        ]
        
        logging_found = False
        for lf in logging_files:
            if lf.exists():
                try:
                    with open(lf, 'r') as f:
                        content = f.read()
                    
                    has_structured = "structured" in content.lower() or "json" in content.lower()
                    has_formatter = "formatter" in content.lower() or "Format" in content
                    
                    if has_structured or has_formatter:
                        evidence.append(f"Structured logging found at {lf.relative_to(self.repo_root)}")
                        logging_found = True
                        break
                except Exception:
                    pass
        
        # Check for correlation ID handling
        correlation_files = [
            self.repo_root / "api" / "middleware" / "governance_context.py",
            self.repo_root / "mahoun" / "core" / "governance" / "governance_context.py",
        ]
        
        correlation_found = False
        for cf in correlation_files:
            if cf.exists():
                try:
                    with open(cf, 'r') as f:
                        content = f.read()
                    if "correlation" in content.lower() or "trace" in content.lower():
                        evidence.append(f"Correlation ID handling found at {cf.relative_to(self.repo_root)}")
                        correlation_found = True
                        break
                except Exception:
                    pass
        
        # Check for audit capability
        audit_files = [
            self.repo_root / "mahoun" / "ledger",
            self.repo_root / "ledger",
        ]
        
        audit_found = False
        for audit_dir in audit_files:
            if audit_dir.exists() and audit_dir.is_dir():
                audit_files_list = list(audit_dir.glob("*.py"))
                if audit_files_list:
                    evidence.append(f"Audit capability found in {audit_dir.relative_to(self.repo_root)}: {len(audit_files_list)} files")
                    audit_found = True
                    break
        
        if not logging_found:
            problems.append("No structured logging configuration found")
        if not correlation_found:
            problems.append("No correlation ID handling found")
        if not audit_found:
            problems.append("No audit capability found")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Implement structured logging (mahoun/core/logging.py), correlation ID handling in middleware, and audit capability in ledger module"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_frontend_architecture(self):
        """CHECK 9: Frontend Architecture Declaration"""
        check_id = "frontend_architecture"
        name = "Frontend Architecture Declaration"
        
        arch_doc_locations = [
            self.repo_root / "docs" / "frontend" / "architecture.md",
            self.repo_root / "docs" / "FRONTEND_ARCHITECTURE.md",
            self.repo_root / "FRONTEND_ARCHITECTURE.md",
            self.repo_root / "frontend" / "ARCHITECTURE.md",
            self.repo_root / "frontend" / "README.md",
        ]
        
        evidence = []
        problems = []
        
        required_sections = [
            ("framework", "frontend framework"),
            ("client", "API client strategy"),
            ("state", "state management"),
            ("authenticat", "authentication integration"),
            ("component", "component strategy"),
        ]
        
        arch_doc_found = False
        for doc_path in arch_doc_locations:
            if doc_path.exists():
                evidence.append(f"Frontend architecture document found at {doc_path.relative_to(self.repo_root)}")
                
                try:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    found_sections = []
                    for keyword, description in required_sections:
                        if keyword in content:
                            found_sections.append(description)
                    
                    if found_sections:
                        evidence.append(f"  Document defines: {', '.join(found_sections)}")
                    
                    missing = [desc for keyword, desc in required_sections if keyword not in content]
                    if missing:
                        problems.append(f"Frontend architecture document missing sections: {', '.join(missing)}")
                        break
                    
                    arch_doc_found = True
                    break
                except Exception as e:
                    problems.append(f"Could not read frontend architecture document: {str(e)}")
                    break
        
        if not arch_doc_found:
            problems.append("Frontend architecture declaration not found in expected locations")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create frontend architecture document at docs/frontend/architecture.md defining: frontend framework, API client strategy, state management, authentication integration, component strategy"
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))

    def _check_sdk_readiness(self):
        """CHECK 10: API Client Readiness - Validate client abstraction"""
        check_id = "sdk_readiness"
        name = "API Client Readiness"
        
        evidence = []
        problems = []
        
        # Check for client directory
        client_locations = [
            self.repo_root / "clients",
            self.repo_root / "frontend" / "src" / "api",
            self.repo_root / "src" / "api",
            self.repo_root / "mahoun" / "clients",
        ]
        
        client_found = False
        for client_dir in client_locations:
            if client_dir.exists() and client_dir.is_dir():
                client_files = list(client_dir.glob("*.ts")) + list(client_dir.glob("*.tsx")) + \
                              list(client_dir.glob("*.js")) + list(client_dir.glob("*.jsx")) + \
                              list(client_dir.glob("*.py"))
                
                if client_files:
                    evidence.append(f"API client abstraction found at {client_dir.relative_to(self.repo_root)}: {len(client_files)} files")
                    evidence.extend([f"  - {cf.name}" for cf in client_files[:5]])
                    if len(client_files) > 5:
                        evidence.append(f"  ... and {len(client_files) - 5} more")
                    client_found = True
                    break
        
        if not client_found:
            problems.append("No API client abstraction directory found in expected locations")
        else:
            # Verify client uses API contract, not backend internals
            frontend_api = self.repo_root / "frontend" / "src" / "api"
            if frontend_api.exists():
                for client_file in frontend_api.glob("*.ts"):
                    try:
                        with open(client_file, 'r') as f:
                            content = f.read()
                        
                        # Check for good patterns
                        if "fetch" in content and "API_BASE_URL" in content:
                            evidence.append(f"  {client_file.name} uses fetch with API_BASE_URL")
                        
                        # Check for TypeScript types matching API contract
                        if "interface" in content or "type" in content:
                            evidence.append(f"  {client_file.name} defines TypeScript types")
                    except Exception:
                        pass
        
        # Check if frontend consumes through client layer
        frontend_src = self.repo_root / "frontend" / "src"
        if frontend_src.exists():
            # Find files that import from API client
            api_imports = []
            for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
                for file_path in frontend_src.rglob(ext):
                    if "api" in str(file_path.relative_to(frontend_src)):
                        continue  # Skip API files themselves
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        # Check for TypeScript/JS import patterns
                        if 'from' in content and ('api/' in content or './api' in content or '@/' in content):
                            api_imports.append(f"  {file_path.relative_to(frontend_src)}")
                        elif 'import' in content and 'api' in content:
                            # Could be a named import
                            api_imports.append(f"  {file_path.relative_to(frontend_src)}")
                    except Exception:
                        pass
            
            if api_imports:
                evidence.append(f"Components using API client: {len(api_imports)} files")
                evidence.extend(api_imports[:3])
            else:
                problems.append("No components found that consume API through client layer")
        
        if problems:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="FAIL",
                evidence=evidence,
                problem="; ".join(problems),
                fix="Create API client abstraction in clients/ or frontend/src/api/ directory. Ensure all frontend code consumes API through this client layer, not raw backend internals."
            ))
        else:
            self.results.append(CheckResult(
                check_id=check_id,
                name=name,
                status="PASS",
                evidence=evidence,
                problem=None,
                fix=None
            ))


def main():
    """Main entry point for the frontend readiness gate"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MAHOUN Frontend Readiness Gate - Validate backend contracts for frontend development"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root directory (default: auto-detected)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        choices=["text", "json", "yaml"],
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output status and exit code"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Fail on any check failure (default: True)"
    )
    
    args = parser.parse_args()
    
    # Set repo root
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    
    # Run gate
    gate = FrontendReadinessGate(repo_root=repo_root)
    report = gate.run_all_checks()
    
    # Output report
    if args.quiet:
        print(f"Status: {report.status}")
        if report.status == "NOT_READY":
            print(f"Failed checks: {report.summary.get('failed', 0)}")
    else:
        output_format = args.output or "text"
        
        if output_format == "text":
            print(report.to_text())
        elif output_format == "json":
            import json
            report_dict = {
                "timestamp": report.timestamp,
                "status": report.status,
                "summary": report.summary,
                "checks": [
                    {
                        "check_id": c.check_id,
                        "name": c.name,
                        "status": c.status,
                        "evidence": c.evidence,
                        "problem": c.problem,
                        "fix": c.fix
                    }
                    for c in report.checks
                ]
            }
            print(json.dumps(report_dict, indent=2, ensure_ascii=False))
        elif output_format == "yaml":
            report_dict = {
                "timestamp": report.timestamp,
                "status": report.status,
                "summary": report.summary,
                "checks": [
                    {
                        "check_id": c.check_id,
                        "name": c.name,
                        "status": c.status,
                        "evidence": c.evidence,
                        "problem": c.problem,
                        "fix": c.fix
                    }
                    for c in report.checks
                ]
            }
            print(yaml.dump(report_dict, allow_unicode=True, default_flow_style=False))
    
    # Exit with appropriate code
    sys.exit(0 if report.status == "READY" else 1)


if __name__ == "__main__":
    main()
