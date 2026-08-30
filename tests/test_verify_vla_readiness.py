from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "verify_vla_readiness.py"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_vla_readiness", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load VLA readiness verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GateDecisionTests(unittest.TestCase):
    def test_blocking_failure_produces_no_go(self) -> None:
        verifier = load_verifier()

        status, authorized = verifier.decide_gate(
            [
                {"status": "PASS", "blocking": True},
                {"status": "FAIL", "blocking": True},
                {"status": "PASS", "blocking": False},
            ]
        )

        self.assertEqual(status, "NO_GO")
        self.assertFalse(authorized)

    def test_go_requires_every_blocking_check_to_pass(self) -> None:
        verifier = load_verifier()

        status, authorized = verifier.decide_gate(
            [
                {"status": "PASS", "blocking": True},
                {"status": "PASS", "blocking": True},
                {"status": "DEFERRED", "blocking": False},
            ]
        )

        self.assertEqual(status, "GO")
        self.assertTrue(authorized)


class VerificationScriptTests(unittest.TestCase):
    def test_safe_run_writes_required_evidence_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "readiness.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    str(output),
                    "--skip-camera-capture",
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            for field in (
                "task",
                "status",
                "host",
                "python",
                "gpu",
                "lerobot",
                "smolvla",
                "robot",
                "camera",
                "teleoperation",
                "dataset_pipeline",
                "service_boundary",
                "checks",
                "blockers",
                "deferred_checks",
                "next_task_authorized",
            ):
                self.assertIn(field, evidence)
            self.assertEqual(evidence["task"], "TASK-P0-004")
            self.assertIn(evidence["status"], {"GO", "CONDITIONAL_GO", "NO_GO"})
            self.assertFalse(evidence["safety"]["robot_commands_sent"])
            self.assertFalse(evidence["safety"]["training_started"])
            self.assertFalse(evidence["safety"]["dataset_v1_collected"])


if __name__ == "__main__":
    unittest.main()
