#!/usr/bin/env python3
"""
Performance Regression Gate for MAHOUN Platform

Measures:
1. pytest -q wall-clock duration
2. Docker Compose health check duration
3. /system/health endpoint response time

Usage:
    python scripts/ci/perf_gate.py --mode=check     # Check against baseline
    python scripts/ci/perf_gate.py --mode=update    # Update baseline
    python scripts/ci/perf_gate.py --mode=measure   # Just measure, no check

Baseline: reports/ci_perf_baseline.json
Regression threshold: 20% (configurable)
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


BASELINE_FILE = Path(__file__).parent.parent.parent / "reports" / "ci_perf_baseline.json"
REGRESSION_THRESHOLD = 0.20


def measure_pytest_duration() -> tuple[Optional[float], int]:
    """
    Returns (duration, returncode).
    """
    start = time.time()
    result = subprocess.run(
        ["./venv/bin/python", "-m", "pytest", "-q", "--tb=no", "-x"],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        timeout=300
    )
    duration = time.time() - start
    
    return (round(duration, 2), result.returncode)


def measure_health_endpoint() -> Optional[float]:
    try:
        import urllib.request
        start = time.time()
        req = urllib.request.Request("http://localhost:8000/system/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
        duration = time.time() - start
        return round(duration, 3)
    except Exception as e:
        print(f"⚠️  Health endpoint unreachable: {e}")
        return None


def measure_docker_health() -> Optional[float]:
    try:
        start = time.time()
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=mahoun", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("⚠️  Docker not available")
            return None
        
        lines = result.stdout.strip().split('\n')
        healthy_count = sum(1 for line in lines if 'healthy' in line.lower())
        
        duration = time.time() - start
        
        if healthy_count == 0:
            print("⚠️  No healthy containers detected")
            return None
            
        return round(duration, 3)
    except Exception as e:
        print(f"⚠️  Docker health check failed: {e}")
        return None


def load_baseline() -> Optional[Dict]:
    if not BASELINE_FILE.exists():
        return None
    
    try:
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load baseline: {e}")
        return None


def save_baseline(metrics: Dict):
    """Save baseline, omitting any None values."""
    clean_metrics = {k: v for k, v in metrics.items() if v is not None}
    
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w') as f:
        json.dump(clean_metrics, f, indent=2)
    print(f"✅ Baseline saved to {BASELINE_FILE}")
    print(f"   Metrics: {list(clean_metrics.keys())}")


def check_regression(current: Dict, baseline: Dict) -> bool:
    print("\n=== Performance Gate Check ===\n")
    print(f"{'Metric':<30} {'Current':<12} {'Baseline':<12} {'Delta':<10} {'Status'}")
    print("-" * 80)
    
    failed = False
    
    for metric, current_val in current.items():
        if current_val is None:
            print(f"{metric:<30} {'N/A':<12} {'N/A':<12} {'N/A':<10} ⚠️  SKIP")
            continue
        
        baseline_val = baseline.get(metric)
        if baseline_val is None:
            print(f"{metric:<30} {current_val:<12.2f} {'N/A':<12} {'N/A':<10} ⚠️  NEW")
            continue
        
        delta_pct = ((current_val - baseline_val) / baseline_val) * 100
        delta_str = f"{delta_pct:+.1f}%"
        
        if delta_pct > (REGRESSION_THRESHOLD * 100):
            status = "❌ FAIL"
            failed = True
        elif delta_pct > 10:
            status = "⚠️  WARN"
        else:
            status = "✅ PASS"
        
        print(f"{metric:<30} {current_val:<12.2f} {baseline_val:<12.2f} {delta_str:<10} {status}")
    
    print("-" * 80)
    
    if failed:
        print(f"\n❌ Performance regression detected (threshold: {REGRESSION_THRESHOLD * 100:.0f}%)")
        print("   To update baseline: python scripts/ci/perf_gate.py --mode=update")
        return False
    else:
        print("\n✅ No performance regression detected")
        return True


def main():
    parser = argparse.ArgumentParser(description="Performance regression gate")
    parser.add_argument(
        "--mode",
        choices=["check", "update", "measure"],
        default="check",
        help="check=verify against baseline, update=update baseline, measure=just measure"
    )
    args = parser.parse_args()
    
    print("🔬 Measuring performance metrics...\n")
    
    pytest_duration, pytest_returncode = measure_pytest_duration()
    
    if pytest_returncode == 5:
        print("NO TESTS COLLECTED")
        if args.mode == "check":
            print("   This is not valid for gate check - failing gate")
    elif pytest_returncode != 0:
        print(f"❌ pytest failed with exit code {pytest_returncode}")
    
    pytest_passed = pytest_returncode == 0 if args.mode == "check" else pytest_returncode in (0, 5)
    
    metrics = {
        "pytest_duration_sec": pytest_duration,
        "docker_health_check_sec": measure_docker_health(),
        "health_endpoint_response_sec": measure_health_endpoint()
    }
    
    print(f"\nMeasured metrics:")
    for key, val in metrics.items():
        val_str = f"{val:.3f}" if val is not None else "N/A"
        print(f"  {key}: {val_str}")
    
    if not pytest_passed:
        print("\n❌ pytest failed - gate cannot pass with failing tests")
        if args.mode == "check":
            return 1
    
    if args.mode == "measure":
        return 0
    
    if args.mode == "update":
        if pytest_returncode != 0:
            print("❌ Cannot update baseline when pytest fails or no tests collected")
            return 1
        save_baseline(metrics)
        return 0
    
    baseline = load_baseline()
    
    if baseline is None:
        print("\n⚠️  No baseline found. Generating initial baseline...")
        if not pytest_passed:
            print("❌ Cannot create baseline when pytest fails")
            return 1
        save_baseline(metrics)
        print("\n✅ Initial baseline created. Run in 'check' mode next time.")
        return 0
    
    if not pytest_passed:
        return 1
    
    passed = check_regression(metrics, baseline)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
