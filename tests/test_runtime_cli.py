from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from agent_runtime.contracts import TOOLS


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "run_runtime.py"


class RuntimeCliTests(unittest.TestCase):
    def test_task_envelope_runs_through_normal_cli_and_remains_inconclusive_without_sources(self):
        tool_input = dict(
            TOOLS["validation.verifyClaim"]["examples"]["validInput"],
            dataType="study_result",
            claim="Fixture sintética por CLI.",
            candidateReferences=[],
        )
        request = {
            "task": {
                "contractVersion": "1.0.0",
                "objective": "Verificar uma afirmação sintética sobre estudo",
                "stages": [{"id": "claim", "tool": "validation.verifyClaim", "input": tool_input}],
            }
        }
        completed = subprocess.run(
            [sys.executable, str(CLI)],
            input=json.dumps(request, ensure_ascii=True),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertTrue(result["missingDependencies"])

    def test_existing_single_tool_envelope_stays_compatible(self):
        tool_input = TOOLS["validation.verifyClaim"]["examples"]["validInput"]
        completed = subprocess.run(
            [sys.executable, str(CLI)],
            input=json.dumps({"tool": "validation.verifyClaim", "input": tool_input}),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["verdict"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
