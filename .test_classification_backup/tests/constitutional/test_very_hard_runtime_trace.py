import json
import subprocess
import sys
from pathlib import Path


@pytest.mark.p2
def test_runtime_trace_script_emits_structured_live_path_report():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "runtime_trace.py"

    completed = subprocess.run(
        [sys.executable, str(script_path), "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode in {0, 1}, completed.stderr
    assert completed.stdout.strip(), completed.stderr

    payload = json.loads(completed.stdout)
    steps = {step["name"]: step for step in payload["steps"]}

    assert {"api", "kernel", "retrieval", "graph", "reasoning", "audit", "system_health"} <= set(steps)
    assert "missing_routes" in steps["api"]["details"]
    assert steps["kernel"]["details"]["correlation_id"] == "runtime-trace"
    assert "status" in steps["system_health"]["details"]


@pytest.mark.p2
def test_runtime_trace_reports_no_missing_critical_routes():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "runtime_trace.py"

    completed = subprocess.run(
        [sys.executable, str(script_path), "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    api_step = next(step for step in payload["steps"] if step["name"] == "api")

    assert api_step["details"]["missing_routes"] == {}
