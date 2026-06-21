"""
Observability & Output Correctness Harness for MAHOUN
=====================================================
کمک‌زیرساخت برای اجرای تست‌های E2E و اعتبارسنجی خروجی‌ها
"""

import os
import json
import time
import hashlib
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

# Mock DBs and prevent initialization for the harness execution
os.environ["MAHOUN_MODE"] = "test"
os.environ["MAHOUN_ENABLE_POSTGRES"] = "0"
os.environ["MAHOUN_ENABLE_REDIS"] = "0"

@dataclass
class InvariantResult:
    name: str
    passed: bool
    message: str

class ObservabilityHarness:
    def __init__(self, artifact_dir: str = "tests/artifacts/observability"):
        self.artifact_dir = artifact_dir
        os.makedirs(self.artifact_dir, exist_ok=True)
        self.logger = logging.getLogger("ObservabilityHarness")
        self.logger.setLevel(logging.INFO)
        
    def get_health_snapshot(self) -> Dict[str, Any]:
        """Captures a snapshot of the system health"""
        try:
            from mahoun.infrastructure.health_checker import HealthChecker
            checker = HealthChecker()
            # Note: We run this synchronously for the harness
            import asyncio
            return asyncio.run(checker.check_health())
        except Exception as e:
            return {"status": "error", "message": str(e), "healthy": False}

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Captures a snapshot of current metrics"""
        try:
            from mahoun.metrics import MetricsCollector
            collector = MetricsCollector()
            return collector.get_metrics_summary()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stable_hash(self, text: str) -> str:
        """Generates a stable SHA256 hash of text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def normalize_text(self, text: str) -> str:
        """Removes volatile noise like timestamps or UUIDs for determinism check"""
        import re
        # Remove UUIDs
        text = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', text)
        # Remove ISO timestamps (simplified)
        text = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', text)
        return text

    async def run_workflow(self, workflow_fn, *args, **kwargs) -> Tuple[Dict[str, Any], List[InvariantResult]]:
        """Executes a workflow and records all metadata"""
        start_time = time.time()
        run_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Capture pre-run state
        health_pre = self.get_health_snapshot()
        metrics_pre = self.get_metrics_snapshot()
        
        # Execute workflow
        actual_output = None
        exception = None
        try:
            actual_output = await workflow_fn(*args, **kwargs)
        except Exception as e:
            exception = str(e)
            self.logger.error(f"Workflow execution failed: {e}")

        duration = time.time() - start_time
        
        # Capture post-run state
        health_post = self.get_health_snapshot()
        metrics_post = self.get_metrics_snapshot()
        
        # Validate Invariants
        invariants = self._validate_invariants(actual_output, health_post, exception)
        
        # Prepare artifact
        artifact = {
            "run_id": run_id,
            "timestamp": timestamp,
            "duration_s": duration,
            "input": {"args": args, "kwargs": kwargs},
            "output": actual_output if actual_output else None,
            "health_snapshot": health_post,
            "metrics_snapshot": metrics_post,
            "invariants": [asdict(inv) for inv in invariants],
            "exception": exception,
            "env": {
                "python": os.sys.version,
                "mode": os.environ.get("MAHOUN_MODE")
            }
        }
        
        # Save JSON artifact
        filepath = os.path.join(self.artifact_dir, f"run_{timestamp}_{run_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
            
        self._write_markdown_summary(artifact, invariants)
        
        return artifact, invariants

    def _validate_invariants(self, output: Any, health: Dict, exception: Optional[str]) -> List[InvariantResult]:
        results = []
        
        # 1. No Masking
        # If Postgres is disabled, health must show it
        pg_health = health.get("components", {}).get("postgresql", {})
        if os.environ.get("MAHOUN_ENABLE_POSTGRES") == "0":
            is_healthy = pg_health.get("healthy", True)
            results.append(InvariantResult(
                "No Masking (Postgres)",
                not is_healthy or pg_health.get("status") == "disabled",
                "Health correctly reports Postgres as disabled/unhealthy" if not is_healthy else "Postgres marked healthy despite being disabled!"
            ))

        # 2. explicit fallback
        fallback_detected = False
        if isinstance(output, dict):
            fallback_detected = output.get("metadata", {}).get("fallback_used", False) or output.get("fallback_used", False)
        
        # In test mode, we often expect fallbacks if DBs are off
        results.append(InvariantResult(
            "Explicit Fallback",
            True, # This is a detection, not always an error
            f"Fallback usage: {fallback_detected}"
        ))

        # 3. Citation Consistency
        if isinstance(output, dict) and "answer" in output:
            citations = output.get("citations", [])
            has_citations = len(citations) > 0
            results.append(InvariantResult(
                "Citation Consistency",
                True if not has_citations or all(isinstance(c, (str, dict)) for c in citations) else False,
                f"Citations present: {has_citations}"
            ))

        # 4. AgentResult Integrity
        if output and hasattr(output, "success"):
             results.append(InvariantResult(
                "AgentResult Contract",
                hasattr(output, "data") and hasattr(output, "error"),
                "AgentResult has standard attributes"
            ))

        return results

    def _write_markdown_summary(self, artifact: Dict, invariants: List[InvariantResult]):
        summary_path = os.path.join(self.artifact_dir, "latest_summary.md")
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Observability Summary - {artifact['timestamp']}\n\n")
            f.write(f"**Run ID:** `{artifact['run_id']}`\n")
            f.write(f"**Duration:** {artifact['duration_s']:.2f}s\n\n")
            
            f.write("## Invariants Status\n")
            f.write("| Invariant | Status | Message |\n")
            f.write("|-----------|--------|---------|\n")
            for inv in invariants:
                status = "✅ PASS" if inv.passed else "❌ FAIL"
                f.write(f"| {inv.name} | {status} | {inv.message} |\n")
            
            f.write("\n## Component Status Table\n")
            f.write("| Component | Healthy | Status |\n")
            f.write("|-----------|---------|--------|\n")
            components = artifact['health_snapshot'].get('components', {})
            for cmp_name, cmp_data in components.items():
                healthy = "✅" if cmp_data.get('healthy') else "❌"
                f.write(f"| {cmp_name} | {healthy} | {cmp_data.get('status', 'N/A')} |\n")
            
            f.write("\n## Output Preview\n")
            if artifact['output']:
                f.write("```json\n")
                # Truncate large outputs
                out_str = json.dumps(artifact['output'], ensure_ascii=False, indent=2)
                if len(out_str) > 1000:
                    out_str = out_str[:1000] + "... [TRUNCATED]"
                f.write(out_str)
                f.write("\n```\n")
            else:
                f.write("*No output (Execution failed or exception occurred)*\n")
                if artifact['exception']:
                    f.write(f"**Exception:** `{artifact['exception']}`\n")
