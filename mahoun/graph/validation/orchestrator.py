"""
Validation Orchestrator — Unified Validation Pipeline
=====================================================

Enterprise-grade orchestration layer:
- Coordinates quality + integrity checks
- Generates comprehensive reports
- Integrates with monitoring/alerting
- Audit trail to immutable ledger
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from mahoun.graph.validation.quality_validator import (
    GraphQualityValidator,
    ValidationReport,
    QualityLevel,
)
from mahoun.graph.validation.integrity_checker import IntegrityChecker
from mahoun.core.governance.governance_context import GovernanceContext

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Validation execution configuration"""
    run_quality_checks: bool = True
    run_integrity_checks: bool = True
    fail_on_critical: bool = True
    generate_report: bool = True
    export_to_file: Optional[str] = None


class ValidationOrchestrator:
    """
    Unified validation orchestration
    
    Coordinates:
    - GraphQualityValidator (data quality)
    - IntegrityChecker (structural integrity)
    - Report generation
    - Monitoring integration
    """
    
    def __init__(
        self,
        governance_context: GovernanceContext,
        config: Optional[ValidationConfig] = None
    ):
        self.governance_context = governance_context
        self.config = config or ValidationConfig()
        self.quality_validator = GraphQualityValidator(governance_context)
        self.integrity_checker = IntegrityChecker(governance_context)
    
    def validate_graph(self) -> Dict:
        """
        Run comprehensive validation pipeline
        
        Returns:
            Unified validation report
        """
        logger.info(
            "Starting orchestrated validation",
            extra={
                "correlation_id": self.governance_context.correlation_id,
                "actor_id": self.governance_context.actor_id,
            }
        )
        
        start_time = datetime.now()
        results = {
            'timestamp': datetime.now().isoformat(),
            'correlation_id': self.governance_context.correlation_id,
            'actor_id': self.governance_context.actor_id,
        }
        
        # Phase 1: Quality validation
        if self.config.run_quality_checks:
            logger.info("Phase 1: Running quality validation")
            quality_report = self.quality_validator.validate_all()
            results['quality'] = {
                'quality_score': quality_report.quality_score,
                'quality_level': quality_report.quality_level.value,
                'total_issues': quality_report.total_issues,
                'has_critical_issues': quality_report.has_critical_issues(),
                'is_production_ready': quality_report.is_production_ready(),
                'issues_by_severity': quality_report.issues_by_severity,
                'issues_by_type': quality_report.issues_by_type,
            }
        
        # Phase 2: Integrity validation
        if self.config.run_integrity_checks:
            logger.info("Phase 2: Running integrity validation")
            integrity_report = self.integrity_checker.validate_all()
            results['integrity'] = {
                'total_violations': integrity_report['total_violations'],
                'has_critical_violations': integrity_report['has_critical_violations'],
                'checks': integrity_report['checks'],
            }
        
        # Calculate overall status
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = round(duration, 3)
        
        # Determine overall pass/fail
        has_critical = False
        if self.config.run_quality_checks:
            has_critical = has_critical or results['quality']['has_critical_issues']
        if self.config.run_integrity_checks:
            has_critical = has_critical or results['integrity']['has_critical_violations']
        
        results['validation_passed'] = not has_critical if self.config.fail_on_critical else True
        results['has_critical_issues'] = has_critical
        
        # Generate report
        if self.config.generate_report:
            results['report_text'] = self._generate_report_text(results)
            
            if self.config.export_to_file:
                self._export_report(results['report_text'], self.config.export_to_file)
        
        logger.info(
            f"Validation complete: {'PASSED' if results['validation_passed'] else 'FAILED'}",
            extra={
                "correlation_id": self.governance_context.correlation_id,
                "validation_passed": results['validation_passed'],
                "duration_seconds": duration,
            }
        )
        
        return results
    
    def _generate_report_text(self, results: Dict) -> str:
        """Generate human-readable report"""
        lines = []
        lines.append("=" * 80)
        lines.append("MAHOUN KNOWLEDGE GRAPH VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {results['timestamp']}")
        lines.append(f"Correlation ID: {results['correlation_id']}")
        lines.append(f"Actor: {results['actor_id']}")
        lines.append(f"Duration: {results['duration_seconds']:.3f}s")
        lines.append(f"Overall Status: {'✅ PASSED' if results['validation_passed'] else '❌ FAILED'}")
        lines.append("")
        
        # Quality section
        if 'quality' in results:
            quality = results['quality']
            lines.append("-" * 80)
            lines.append("DATA QUALITY VALIDATION")
            lines.append("-" * 80)
            lines.append(f"Quality Score: {quality['quality_score']}/100")
            lines.append(f"Quality Level: {quality['quality_level'].upper()}")
            lines.append(f"Total Issues: {quality['total_issues']}")
            lines.append(f"Production Ready: {'✅ YES' if quality['is_production_ready'] else '❌ NO'}")
            lines.append("")
            lines.append("Issues by Severity:")
            for severity, count in quality['issues_by_severity'].items():
                lines.append(f"  {severity.upper()}: {count}")
            lines.append("")
        
        # Integrity section
        if 'integrity' in results:
            integrity = results['integrity']
            lines.append("-" * 80)
            lines.append("STRUCTURAL INTEGRITY VALIDATION")
            lines.append("-" * 80)
            lines.append(f"Total Violations: {integrity['total_violations']}")
            lines.append(f"Critical Violations: {'❌ YES' if integrity['has_critical_violations'] else '✅ NO'}")
            lines.append("")
            lines.append("Integrity Checks:")
            for check_name, check_result in integrity['checks'].items():
                status = "❌ FAILED" if check_result.get('has_violations') else "✅ PASSED"
                lines.append(f"  {check_name}: {status}")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _export_report(self, report_text: str, file_path: str):
        """Export report to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(
                f"Report exported to {file_path}",
                extra={"correlation_id": self.governance_context.correlation_id}
            )
        except Exception as e:
            logger.error(
                f"Failed to export report: {e}",
                extra={"correlation_id": self.governance_context.correlation_id}
            )


# ============================================================================
# Convenience Functions
# ============================================================================

def run_validation(
    governance_context: GovernanceContext,
    export_file: Optional[str] = None
) -> Dict:
    """
    Quick validation function
    
    Args:
        governance_context: Governance context
        export_file: Optional file path for report export
    
    Returns:
        Validation results
    """
    config = ValidationConfig(export_to_file=export_file)
    orchestrator = ValidationOrchestrator(governance_context, config)
    return orchestrator.validate_graph()


def print_validation_report(governance_context: GovernanceContext):
    """Print validation report to console"""
    results = run_validation(governance_context)
    if 'report_text' in results:
        print(results['report_text'])
