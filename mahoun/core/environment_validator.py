"""
Production Environment Validator
=================================

Validates that all required environment variables are set correctly
for production deployment. Implements fail-fast principle.

Usage:
    from mahoun.core.environment_validator import validate_production_environment
    
    # At application startup
    validate_production_environment()
"""

import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EnvironmentLevel(str, Enum):
    """Environment level criticality"""
    REQUIRED = "required"        # Must be set in production
    RECOMMENDED = "recommended"  # Should be set
    OPTIONAL = "optional"        # Nice to have


class ValidationSeverity(str, Enum):
    """Validation failure severity"""
    CRITICAL = "critical"  # Block startup
    WARNING = "warning"    # Log warning
    INFO = "info"         # Informational


@dataclass
class EnvironmentVariable:
    """Environment variable definition"""
    name: str
    level: EnvironmentLevel
    expected_values: Optional[List[str]] = None
    default: Optional[str] = None
    description: str = ""
    validation_fn: Optional[callable] = None


@dataclass
class ValidationResult:
    """Result of environment validation"""
    passed: bool
    severity: ValidationSeverity
    variable: str
    message: str
    current_value: Optional[str] = None
    expected: Optional[List[str]] = None


# ============================================================================
# Environment Variable Definitions
# ============================================================================

REQUIRED_PRODUCTION_VARS = [
    EnvironmentVariable(
        name="MAHOUN_ENVIRONMENT",
        level=EnvironmentLevel.REQUIRED,
        expected_values=["production", "prod"],
        description="Must be set to 'production' for production deployment"
    ),
    EnvironmentVariable(
        name="MAHOUN_EXECUTION_MODE",
        level=EnvironmentLevel.REQUIRED,
        expected_values=["full"],
        default="minimal",
        description="Execution mode (full for production with 16GB+ RAM)"
    ),
    EnvironmentVariable(
        name="MAHOUN_GUARD_MODE",
        level=EnvironmentLevel.REQUIRED,
        expected_values=["STRICT", "strict"],
        description="Governance enforcement mode (STRICT for production)"
    ),
]

RECOMMENDED_PRODUCTION_VARS = [
    EnvironmentVariable(
        name="NEO4J_URI",
        level=EnvironmentLevel.RECOMMENDED,
        description="Neo4j database URI"
    ),
    EnvironmentVariable(
        name="NEO4J_USER",
        level=EnvironmentLevel.RECOMMENDED,
        description="Neo4j username"
    ),
    EnvironmentVariable(
        name="NEO4J_PASSWORD",
        level=EnvironmentLevel.RECOMMENDED,
        description="Neo4j password"
    ),
    EnvironmentVariable(
        name="CUDA_VISIBLE_DEVICES",
        level=EnvironmentLevel.RECOMMENDED,
        description="GPU device(s) to use"
    ),
]

OPTIONAL_PRODUCTION_VARS = [
    EnvironmentVariable(
        name="MAHOUN_LOG_LEVEL",
        level=EnvironmentLevel.OPTIONAL,
        expected_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        description="Logging level"
    ),
    EnvironmentVariable(
        name="MAHOUN_MAX_WORKERS",
        level=EnvironmentLevel.OPTIONAL,
        description="Maximum number of worker processes"
    ),
]


# ============================================================================
# Validation Functions
# ============================================================================

def validate_environment_variable(var: EnvironmentVariable) -> ValidationResult:
    """
    Validate a single environment variable.
    
    Args:
        var: Environment variable definition
    
    Returns:
        ValidationResult
    """
    current_value = os.getenv(var.name)
    
    # Check if variable is set
    if current_value is None:
        if var.level == EnvironmentLevel.REQUIRED:
            return ValidationResult(
                passed=False,
                severity=ValidationSeverity.CRITICAL,
                variable=var.name,
                message=f"CRITICAL: {var.name} is REQUIRED but not set. {var.description}",
                expected=var.expected_values
            )
        elif var.level == EnvironmentLevel.RECOMMENDED:
            return ValidationResult(
                passed=False,
                severity=ValidationSeverity.WARNING,
                variable=var.name,
                message=f"WARNING: {var.name} is not set. {var.description}",
                expected=var.expected_values
            )
        else:
            return ValidationResult(
                passed=True,
                severity=ValidationSeverity.INFO,
                variable=var.name,
                message=f"INFO: {var.name} not set (optional)",
                current_value=var.default
            )
    
    # Check if value is in expected values
    if var.expected_values and current_value not in var.expected_values:
        severity = ValidationSeverity.CRITICAL if var.level == EnvironmentLevel.REQUIRED else ValidationSeverity.WARNING
        return ValidationResult(
            passed=False,
            severity=severity,
            variable=var.name,
            message=f"{severity.value.upper()}: {var.name}='{current_value}' is not valid. Expected: {var.expected_values}",
            current_value=current_value,
            expected=var.expected_values
        )
    
    # Custom validation function
    if var.validation_fn:
        try:
            is_valid, error_msg = var.validation_fn(current_value)
            if not is_valid:
                severity = ValidationSeverity.CRITICAL if var.level == EnvironmentLevel.REQUIRED else ValidationSeverity.WARNING
                return ValidationResult(
                    passed=False,
                    severity=severity,
                    variable=var.name,
                    message=f"{severity.value.upper()}: {var.name} validation failed: {error_msg}",
                    current_value=current_value
                )
        except Exception as e:
            return ValidationResult(
                passed=False,
                severity=ValidationSeverity.WARNING,
                variable=var.name,
                message=f"WARNING: {var.name} validation function failed: {e}",
                current_value=current_value
            )
    
    # Success
    return ValidationResult(
        passed=True,
        severity=ValidationSeverity.INFO,
        variable=var.name,
        message=f"✓ {var.name}='{current_value}'",
        current_value=current_value
    )


def validate_production_environment(
    fail_fast: bool = True,
    log_results: bool = True
) -> tuple[bool, List[ValidationResult]]:
    """
    Validate all production environment variables.
    
    Args:
        fail_fast: Exit immediately on critical failure
        log_results: Log validation results
    
    Returns:
        Tuple of (success, results_list)
    
    Raises:
        SystemExit: If critical validation fails and fail_fast=True
    """
    all_vars = REQUIRED_PRODUCTION_VARS + RECOMMENDED_PRODUCTION_VARS + OPTIONAL_PRODUCTION_VARS
    results: List[ValidationResult] = []
    
    critical_failures = 0
    warnings = 0
    
    if log_results:
        logger.info("=" * 80)
        logger.info("🔍 Production Environment Validation")
        logger.info("=" * 80)
    
    # Validate each variable
    for var in all_vars:
        result = validate_environment_variable(var)
        results.append(result)
        
        if log_results:
            if result.severity == ValidationSeverity.CRITICAL:
                logger.critical(result.message)
                critical_failures += 1
            elif result.severity == ValidationSeverity.WARNING:
                logger.warning(result.message)
                warnings += 1
            else:
                logger.info(result.message)
    
    # Summary
    if log_results:
        logger.info("=" * 80)
        logger.info(f"Validation Summary: {len(results)} variables checked")
        logger.info(f"  ✓ Passed: {len([r for r in results if r.passed])}")
        logger.info(f"  ✗ Critical Failures: {critical_failures}")
        logger.info(f"  ⚠ Warnings: {warnings}")
        logger.info("=" * 80)
    
    # Fail fast on critical errors
    if critical_failures > 0:
        error_msg = (
            f"\n{'='*80}\n"
            f"❌ PRODUCTION ENVIRONMENT VALIDATION FAILED\n"
            f"{'='*80}\n"
            f"Critical failures: {critical_failures}\n\n"
            f"Required environment variables:\n"
        )
        
        for result in results:
            if result.severity == ValidationSeverity.CRITICAL:
                error_msg += f"  • {result.variable}: {result.message}\n"
        
        error_msg += f"\n{'='*80}\n"
        error_msg += "Fix these issues before starting in production mode.\n"
        error_msg += f"{'='*80}\n"
        
        if fail_fast:
            logger.critical(error_msg)
            sys.exit(1)
        else:
            logger.error(error_msg)
            return False, results
    
    if log_results:
        logger.info("✅ Production environment validation PASSED")
    
    return True, results


def get_environment_template() -> str:
    """
    Generate a template .env file for production.
    
    Returns:
        Template content as string
    """
    template = [
        "# MahouN Production Environment Variables",
        "# =========================================",
        "",
        "# REQUIRED: Core Settings",
        "# ------------------------",
    ]
    
    for var in REQUIRED_PRODUCTION_VARS:
        template.append(f"# {var.description}")
        if var.expected_values:
            template.append(f"# Expected: {', '.join(var.expected_values)}")
        if var.default:
            template.append(f"{var.name}={var.default}")
        else:
            template.append(f"{var.name}=")
        template.append("")
    
    template.append("# RECOMMENDED: Database & Infrastructure")
    template.append("# ---------------------------------------")
    
    for var in RECOMMENDED_PRODUCTION_VARS:
        template.append(f"# {var.description}")
        template.append(f"{var.name}=")
        template.append("")
    
    template.append("# OPTIONAL: Fine-tuning")
    template.append("# ----------------------")
    
    for var in OPTIONAL_PRODUCTION_VARS:
        template.append(f"# {var.description}")
        if var.expected_values:
            template.append(f"# Options: {', '.join(var.expected_values)}")
        if var.default:
            template.append(f"{var.name}={var.default}")
        else:
            template.append(f"# {var.name}=")
        template.append("")
    
    return "\n".join(template)


def generate_environment_report() -> Dict[str, Any]:
    """
    Generate a detailed environment report.
    
    Returns:
        Dictionary with environment details
    """
    success, results = validate_production_environment(
        fail_fast=False,
        log_results=False
    )
    
    return {
        "success": success,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "total_variables": len(results),
        "passed": len([r for r in results if r.passed]),
        "critical_failures": len([r for r in results if r.severity == ValidationSeverity.CRITICAL]),
        "warnings": len([r for r in results if r.severity == ValidationSeverity.WARNING]),
        "results": [
            {
                "variable": r.variable,
                "passed": r.passed,
                "severity": r.severity.value,
                "message": r.message,
                "current_value": r.current_value if r.severity != ValidationSeverity.CRITICAL else "***",
            }
            for r in results
        ]
    }


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate production environment")
    parser.add_argument("--template", action="store_true", help="Generate .env template")
    parser.add_argument("--report", action="store_true", help="Generate JSON report")
    parser.add_argument("--no-fail-fast", action="store_true", help="Don't exit on critical errors")
    
    args = parser.parse_args()
    
    if args.template:
        print(get_environment_template())
        sys.exit(0)
    
    if args.report:
        import json
        report = generate_environment_report()
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["success"] else 1)
    
    # Normal validation
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    validate_production_environment(fail_fast=not args.no_fail_fast)
