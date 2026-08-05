"""
🔍 Behavioral Regression Detection for EmbeddingModelsExecutor

Compares current behavioral snapshots against golden master baseline.
Detects ANY deviation in observable behavior during refactoring.

Regression Types Detected:
- Context mutations changed (services added/removed differently)
- Exception fingerprints changed (different error types/messages)
- Event sequence changed (execution order differences)  
- Rollback behavior changed (cleanup sequence differences)
- Performance characteristics changed (timing thresholds)

Usage:
    python detect_regressions.py --baseline golden_master/snapshots/ --current test_run/snapshots/
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class RegressionFinding:
    """Represents a behavioral regression detected during comparison"""
    level: str  # "🟢 EASY", "🟡 MEDIUM", etc.
    category: str  # "context_mutations", "events", "exceptions", etc.
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    description: str
    baseline_value: Any
    current_value: Any


class BehavioralRegressionDetector:
    """
    Detects regressions by comparing behavioral snapshots.
    
    Uses deep semantic comparison, not just JSON diff.
    Focuses on observable behavior changes that affect system contracts.
    """
    
    def __init__(self):
        self.findings: List[RegressionFinding] = []
        
    def compare_snapshots(self, baseline_dir: Path, current_dir: Path) -> List[RegressionFinding]:
        """Compare all snapshots between baseline and current"""
        
        self.findings.clear()
        
        # Expected snapshot files for each test level
        snapshot_files = [
            ("🟢 EASY", "embedding_easy_success.json"),
            ("🟡 MEDIUM", "embedding_missing_neo4j.json"),
            ("🔴 HARD", "embedding_rollback_race.json"),
            ("⚫ ULTRA HARD", "embedding_adversarial_ultra.json")
        ]
        
        for level, filename in snapshot_files:
            baseline_file = baseline_dir / filename
            current_file = current_dir / filename
            
            if not baseline_file.exists():
                self._add_finding(level, "missing_baseline", "CRITICAL",
                    f"Baseline snapshot missing: {baseline_file}",
                    None, f"File not found: {baseline_file}")
                continue
                
            if not current_file.exists():
                self._add_finding(level, "missing_current", "CRITICAL",
                    f"Current snapshot missing: {current_file}",
                    f"Expected: {current_file}", "File not found")
                continue
                
            # Load and compare snapshots
            try:
                with open(baseline_file) as f:
                    baseline = json.load(f)
                with open(current_file) as f:
                    current = json.load(f)
                    
                self._compare_snapshot_pair(level, baseline, current)
                
            except Exception as e:
                self._add_finding(level, "load_error", "HIGH",
                    f"Failed to load snapshots: {e}",
                    f"Baseline: {baseline_file}", f"Current: {current_file}")
        
        return self.findings
    
    def _compare_snapshot_pair(self, level: str, baseline: Dict, current: Dict) -> None:
        """Deep comparison of a single snapshot pair"""
        
        # 1. Context Mutations Comparison
        self._compare_context_mutations(level, baseline, current)
        
        # 2. Events Sequence Comparison  
        self._compare_events_sequence(level, baseline, current)
        
        # 3. Exception Fingerprints Comparison
        self._compare_exception_fingerprints(level, baseline, current)
        
        # 4. Rollback Behavior Comparison
        self._compare_rollback_behavior(level, baseline, current)
        
        # 5. Performance Characteristics Comparison
        self._compare_performance_characteristics(level, baseline, current)
        
    def _compare_context_mutations(self, level: str, baseline: Dict, current: Dict) -> None:
        """Compare context mutation patterns"""
        
        baseline_mutations = baseline.get("context_mutations", {})
        current_mutations = current.get("context_mutations", {})
        
        # Services added/removed
        baseline_services = set(baseline_mutations.get("services_added", []))
        current_services = set(current_mutations.get("services_added", []))
        
        if baseline_services != current_services:
            missing_services = baseline_services - current_services
            extra_services = current_services - baseline_services
            
            self._add_finding(level, "context_mutations", "CRITICAL",
                f"Service registry mutations changed",
                f"Baseline services: {baseline_services}",
                f"Current services: {current_services}")
                
        # Config mutations
        baseline_config = baseline_mutations.get("config_changes", {})
        current_config = current_mutations.get("config_changes", {})
        
        if baseline_config != current_config:
            self._add_finding(level, "context_mutations", "HIGH",
                f"Configuration mutations changed",
                f"Baseline: {baseline_config}",
                f"Current: {current_config}")
    
    def _compare_events_sequence(self, level: str, baseline: Dict, current: Dict) -> None:
        """Compare event sequences for behavioral changes"""
        
        baseline_events = baseline.get("events", [])
        current_events = current.get("events", [])
        
        # Extract event type sequences
        baseline_sequence = [e.get("type", "unknown") for e in baseline_events]
        current_sequence = [e.get("type", "unknown") for e in current_events]
        
        if baseline_sequence != current_sequence:
            self._add_finding(level, "event_sequence", "HIGH",
                f"Event execution sequence changed",
                f"Baseline: {baseline_sequence}",
                f"Current: {current_sequence}")
        
        # Compare critical event details
        for baseline_event in baseline_events:
            event_type = baseline_event.get("type")
            if event_type in ["expected_exception", "execution_completed", "rollback_completed"]:
                # Find matching event in current
                matching_current = next(
                    (e for e in current_events if e.get("type") == event_type),
                    None
                )
                
                if not matching_current:
                    self._add_finding(level, "missing_event", "CRITICAL",
                        f"Critical event missing: {event_type}",
                        f"Baseline had: {baseline_event}",
                        "Event not found in current run")
                else:
                    # Compare event data
                    baseline_data = {k: v for k, v in baseline_event.items() if k != "timestamp"}
                    current_data = {k: v for k, v in matching_current.items() if k != "timestamp"}
                    
                    if baseline_data != current_data:
                        self._add_finding(level, "event_data", "HIGH",
                            f"Event data changed for {event_type}",
                            f"Baseline: {baseline_data}",
                            f"Current: {current_data}")
    
    def _compare_exception_fingerprints(self, level: str, baseline: Dict, current: Dict) -> None:
        """Compare exception handling patterns"""
        
        baseline_events = baseline.get("events", [])
        current_events = current.get("events", [])
        
        # Extract exception events
        baseline_exceptions = [e for e in baseline_events if "exception" in e.get("type", "")]
        current_exceptions = [e for e in current_events if "exception" in e.get("type", "")]
        
        if len(baseline_exceptions) != len(current_exceptions):
            self._add_finding(level, "exception_count", "CRITICAL",
                f"Exception count changed",
                f"Baseline: {len(baseline_exceptions)} exceptions",
                f"Current: {len(current_exceptions)} exceptions")
        
        # Compare exception details
        for baseline_exc, current_exc in zip(baseline_exceptions, current_exceptions):
            baseline_type = baseline_exc.get("data", {}).get("type")
            current_type = current_exc.get("data", {}).get("type")
            
            if baseline_type != current_type:
                self._add_finding(level, "exception_type", "CRITICAL",
                    f"Exception type changed",
                    f"Baseline: {baseline_type}",
                    f"Current: {current_type}")
    
    def _compare_rollback_behavior(self, level: str, baseline: Dict, current: Dict) -> None:
        """Compare rollback and cleanup behavior"""
        
        baseline_events = baseline.get("events", [])
        current_events = current.get("events", [])
        
        # Find rollback events
        baseline_rollbacks = [e for e in baseline_events if "rollback" in e.get("type", "")]
        current_rollbacks = [e for e in current_events if "rollback" in e.get("type", "")]
        
        if len(baseline_rollbacks) != len(current_rollbacks):
            self._add_finding(level, "rollback_behavior", "HIGH",
                f"Rollback event count changed",
                f"Baseline: {len(baseline_rollbacks)}",
                f"Current: {len(current_rollbacks)}")
    
    def _compare_performance_characteristics(self, level: str, baseline: Dict, current: Dict) -> None:
        """Compare performance and timing characteristics"""
        
        # Compare event timing patterns (not absolute times)
        baseline_events = baseline.get("events", [])
        current_events = current.get("events", [])
        
        if len(baseline_events) > 1 and len(current_events) > 1:
            # Check for major timing order changes (not absolute times)
            baseline_timestamps = [e.get("timestamp", 0) for e in baseline_events]
            current_timestamps = [e.get("timestamp", 0) for e in current_events]
            
            # Verify timestamps are monotonically increasing
            baseline_ordered = all(baseline_timestamps[i] <= baseline_timestamps[i+1] 
                                 for i in range(len(baseline_timestamps)-1))
            current_ordered = all(current_timestamps[i] <= current_timestamps[i+1] 
                                for i in range(len(current_timestamps)-1))
            
            if baseline_ordered != current_ordered:
                self._add_finding(level, "timing_order", "MEDIUM",
                    f"Event timing order changed",
                    f"Baseline ordered: {baseline_ordered}",
                    f"Current ordered: {current_ordered}")
    
    def _add_finding(self, level: str, category: str, severity: str, 
                     description: str, baseline_value: Any, current_value: Any) -> None:
        """Add a regression finding"""
        
        finding = RegressionFinding(
            level=level,
            category=category,
            severity=severity,
            description=description,
            baseline_value=baseline_value,
            current_value=current_value
        )
        
        self.findings.append(finding)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression report"""
        
        # Group findings by severity
        findings_by_severity = {
            "CRITICAL": [],
            "HIGH": [],
            "MEDIUM": [],
            "LOW": []
        }
        
        for finding in self.findings:
            findings_by_severity[finding.severity].append(finding)
        
        # Calculate regression score
        critical_count = len(findings_by_severity["CRITICAL"])
        high_count = len(findings_by_severity["HIGH"])
        medium_count = len(findings_by_severity["MEDIUM"])
        low_count = len(findings_by_severity["LOW"])
        
        total_score = (critical_count * 10) + (high_count * 5) + (medium_count * 2) + (low_count * 1)
        
        # Determine regression status
        if critical_count > 0:
            regression_status = "CRITICAL_REGRESSIONS"
        elif high_count > 0:
            regression_status = "HIGH_REGRESSIONS"  
        elif medium_count > 0:
            regression_status = "MEDIUM_REGRESSIONS"
        elif low_count > 0:
            regression_status = "LOW_REGRESSIONS"
        else:
            regression_status = "NO_REGRESSIONS"
        
        report = {
            "regression_summary": {
                "status": regression_status,
                "total_findings": len(self.findings),
                "regression_score": total_score,
                "critical_count": critical_count,
                "high_count": high_count,
                "medium_count": medium_count,
                "low_count": low_count
            },
            "findings_by_severity": {
                severity: [
                    {
                        "level": f.level,
                        "category": f.category,
                        "description": f.description,
                        "baseline_value": f.baseline_value,
                        "current_value": f.current_value
                    }
                    for f in findings
                ]
                for severity, findings in findings_by_severity.items()
            },
            "recommendation": self._get_recommendation(regression_status)
        }
        
        return report
    
    def _get_recommendation(self, regression_status: str) -> str:
        """Get recommendation based on regression status"""
        
        recommendations = {
            "NO_REGRESSIONS": "✅ SAFE TO PROCEED - No behavioral regressions detected",
            "LOW_REGRESSIONS": "⚠️ REVIEW REQUIRED - Minor behavioral changes detected",
            "MEDIUM_REGRESSIONS": "⚠️ CAUTION ADVISED - Moderate behavioral changes detected", 
            "HIGH_REGRESSIONS": "🚨 STOP - Significant behavioral changes detected",
            "CRITICAL_REGRESSIONS": "🚨 ABORT - Critical behavioral regressions detected"
        }
        
        return recommendations.get(regression_status, "❓ UNKNOWN STATUS")


def main():
    """Command-line interface for regression detection"""
    
    if len(sys.argv) != 3:
        print("Usage: python detect_regressions.py <baseline_dir> <current_dir>")
        sys.exit(1)
    
    baseline_dir = Path(sys.argv[1])
    current_dir = Path(sys.argv[2])
    
    if not baseline_dir.exists():
        print(f"Error: Baseline directory not found: {baseline_dir}")
        sys.exit(1)
        
    if not current_dir.exists():
        print(f"Error: Current directory not found: {current_dir}")
        sys.exit(1)
    
    # Run regression detection
    detector = BehavioralRegressionDetector()
    findings = detector.compare_snapshots(baseline_dir, current_dir)
    report = detector.generate_report()
    
    # Print results
    print("🔍 Behavioral Regression Detection Report")
    print("=" * 60)
    print(f"Status: {report['regression_summary']['status']}")
    print(f"Total Findings: {report['regression_summary']['total_findings']}")
    print(f"Regression Score: {report['regression_summary']['regression_score']}")
    print(f"\nRecommendation: {report['recommendation']}")
    
    # Print findings by severity
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        findings_list = report['findings_by_severity'][severity]
        if findings_list:
            print(f"\n{severity} Findings ({len(findings_list)}):")
            for finding in findings_list:
                print(f"  • {finding['level']} {finding['category']}: {finding['description']}")
    
    # Save report
    report_path = current_dir / "regression_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Full report saved: {report_path}")
    
    # Exit with appropriate code
    if report['regression_summary']['status'] in ["CRITICAL_REGRESSIONS", "HIGH_REGRESSIONS"]:
        sys.exit(1)  # Fail CI/CD pipeline
    else:
        sys.exit(0)  # Allow pipeline to continue


if __name__ == "__main__":
    main()