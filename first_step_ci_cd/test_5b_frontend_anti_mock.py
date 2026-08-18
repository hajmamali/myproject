"""
Test 5b: Frontend Anti-Mock / Fabrication Detection
====================================================
Self-test for gate_4b_frontend_antimock.sh (Phase B, Round 10).

Two fixtures, two assertions — mandatory per Round 10 spec:
  - POSITIVE: a file with the exact AIChat.tsx fabrication pattern
    (hardcoded multi-line Persian string, `setTimeout` fake streaming,
    hardcoded `confidence: 0.95`, `citations: [...]`, and the comment
    `// Simulate streaming response (replace with actual API call)`).
    The gate MUST flag this.
  - NEGATIVE / false-positive guard: a file that imports from `../api/`
    AND makes a real `await` call (the canonical LegalSearchPage.tsx pattern).
    The gate MUST NOT flag or warn on this. A check without this guard
    drifts toward over-flagging (ignored) or under-flagging (over-suppressed).

The test points the shell script at a temp frontend tree via the
MAHOUN_FRONTEND_SRC env override (no production paths are touched).
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GATE_SCRIPT = PROJECT_ROOT / "ci" / "first_step" / "gate_4b_frontend_antimock.sh"

# ---------------------------------------------------------------------------
# Fixtures: the exact AIChat.tsx fabrication pattern + a clean canonical file
# ---------------------------------------------------------------------------

FABRICATION_COMPONENT = textwrap.dedent(
    """\
    import { useState } from "react";

    export default function FakeChat() {
      const [messages, setMessages] = useState([]);
      const handleSend = async () => {
        // Simulate streaming response (replace with actual API call)
        const response = "بر اساس ماده ۲۱۹ قانون آیین دادرسی مدنی، دادگاه می‌تواند مهلت مناسبی بدهد.";
        let currentText = "";
        for (let i = 0; i < response.length; i++) {
          await new Promise((resolve) => setTimeout(resolve, 20));
          currentText += response[i];
          setMessages((p) => [...p, currentText]);
        }
        setMessages((p) => [...p, {
          confidence: 0.95,
          citations: [{ text: "placeholder", source: "hardcoded fake response" }],
        }]);
      };
      return null;
    }
    """
)

# Canonical clean pattern: real API import + real awaited call.
# Matches the LegalSearchPage.tsx wiring referenced in AGENTS.md.
CLEAN_COMPONENT = textwrap.dedent(
    """\
    import { useState, useCallback } from "react";
    import { searchVerdicts } from "../api/client";

    export default function CleanSearchPage() {
      const [results, setResults] = useState([]);
      const handleSearch = useCallback(async (query: string) => {
        const trimmed = query.trim();
        if (!trimmed) return;
        const response = await searchVerdicts({ query: trimmed, limit: 10 });
        setResults(response.results);
      }, []);
      return null;
    }
    """
)


@pytest.fixture
def temp_frontend(tmp_path: Path) -> Path:
    """Create a throwaway frontend/src tree for the gate to scan."""
    src = tmp_path / "frontend" / "src"
    (src / "components").mkdir(parents=True)
    (src / "pages").mkdir(parents=True)
    return src


def _run_gate(frontend_src: Path) -> subprocess.CompletedProcess:
    """Run gate_4b pointed at the given frontend root; capture output."""
    env = os.environ.copy()
    env["MAHOUN_FRONTEND_SRC"] = str(frontend_src)
    return subprocess.run(
        ["bash", str(GATE_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Positive: the AIChat.tsx fabrication pattern MUST be detected
# ---------------------------------------------------------------------------

class TestFrontendFabricationDetected:
    def test_fabrication_component_is_flagged(self, temp_frontend: Path):
        (temp_frontend / "components" / "FakeChat.tsx").write_text(
            FABRICATION_COMPONENT, encoding="utf-8"
        )
        proc = _run_gate(temp_frontend.parent)
        # At least one hard B1 violation (the "Simulate streaming" comment,
        # "replace with actual API call", "placeholder/hardcoded/fake response"
        # near confidence:/citations:).
        assert proc.returncode != 0, (
            "gate_4b PASSED on a known fabrication fixture — the check is dead.\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        out = proc.stdout + proc.stderr
        # Must surface the fabrication marker, not just a B2 warning.
        assert "B1:" in out or "fabrication marker" in out.lower(), (
            "gate_4b failed but not via B1 marker detection — wrong failure mode:\n"
            f"{out}"
        )


# ---------------------------------------------------------------------------
# MANDATORY false-positive guard: clean canonical wiring MUST NOT be flagged
# ---------------------------------------------------------------------------

class TestFrontendCleanNotFlagged:
    def test_clean_api_call_not_warned(self, temp_frontend: Path):
        (temp_frontend / "pages" / "CleanSearchPage.tsx").write_text(
            CLEAN_COMPONENT, encoding="utf-8"
        )
        proc = _run_gate(temp_frontend.parent)
        out = proc.stdout + proc.stderr
        assert proc.returncode == 0, (
            "gate_4b FAILED on a clean canonical component (false positive):\n"
            f"{out}"
        )
        # And there must be no B2 warning for it — it imports from ../api AND
        # calls await searchVerdicts(...).
        assert "CleanSearchPage" not in out or "B2:" not in out, (
            "gate_4b raised a B2 warning on a component that DOES make a real "
            "API call — the heuristic is broken (over-flagging).\n"
            f"{out}"
        )

    def test_suppression_marker_requires_reason(self, temp_frontend: Path):
        # A file that would otherwise be a B1 violation gets a bare
        # suppression marker (no reason) — this must itself fail the gate.
        bad = FABRICATION_COMPONENT.replace(
            "import { useState } from \"react\";",
            "import { useState } from \"react\";\n// fabrication-check-ok:",
        )
        (temp_frontend / "components" / "SuppressedNoReason.tsx").write_text(
            bad, encoding="utf-8"
        )
        proc = _run_gate(temp_frontend.parent)
        out = proc.stdout + proc.stderr
        assert proc.returncode != 0, (
            "gate_4b accepted a suppression marker with no reason — B3 is dead:\n"
            f"{out}"
        )
        assert "NO_REASON" in out or "suppression" in out.lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
