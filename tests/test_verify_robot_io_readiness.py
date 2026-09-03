from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "verify_robot_io_readiness.py"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "verify_robot_io_readiness", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load robot I/O readiness verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RobotIoReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = load_verifier()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.dev_root = root / "dev"
        self.dev_root.mkdir()
        self.robot_path = self.dev_root / "ttyACM0"
        self.robot_path.write_text("device fixture", encoding="utf-8")
        self.robot_stable = self.dev_root / "serial" / "by-id" / "usb-test-robot"
        self.robot_stable.parent.mkdir(parents=True)
        self.robot_stable.symlink_to(Path("../..") / self.robot_path.name)
        self.camera_path = self.dev_root / "video0"
        self.camera_path.write_text("camera fixture", encoding="utf-8")
        self.camera_stable = self.dev_root / "v4l" / "by-id" / "usb-test-camera"
        self.camera_stable.parent.mkdir(parents=True)
        self.camera_stable.symlink_to(Path("../..") / self.camera_path.name)
        self.state_path = root / "state.json"
        self.state_path.write_text('{"mode":"idle","joints":[0,0]}', encoding="utf-8")

    def declarations(self) -> dict[str, Any]:
        return {
            "target_hardware": {
                "manufacturer": "Fixture Robotics",
                "model": "Fixture Arm 1",
                "controller": "Fixture Controller",
                "firmware": "1.0-test",
                "connection_type": "USB serial fixture",
                "robot_device_path": str(self.robot_path),
                "stable_device_path": str(self.robot_stable),
                "documentation_refs": ["fixture://robot-interface"],
                "gripper_present": True,
            },
            "interfaces": {
                "state": {
                    "interface": "bounded regular-file fixture snapshot",
                    "documentation_ref": "fixture://state-interface",
                    "observation": {
                        "kind": "regular_file_snapshot",
                        "path": str(self.state_path),
                        "safe_read_only": True,
                    },
                },
                "command": {
                    "interface": "future typed fixture command adapter",
                    "documentation_ref": "fixture://command-interface",
                },
                "gripper": {
                    "interface": "future typed fixture gripper adapter",
                    "documentation_ref": "fixture://gripper-interface",
                },
            },
            "camera": {
                "manufacturer": "Fixture Vision",
                "model": "Fixture Camera 1",
                "device_path": str(self.camera_path),
                "stable_device_path": str(self.camera_stable),
                "width": 640,
                "height": 480,
                "pixel_format": "YUYV",
                "documentation_refs": ["fixture://camera-interface"],
            },
            "workspace": {
                "description": "fixture bounded tabletop cell",
                "joint_or_cartesian_limits": {"joint_1_degrees": [-90, 90]},
                "prohibited_zones": ["outside fixture cell"],
                "initial_pose_assumptions": ["powered off before operator setup"],
                "gripper_constraints": ["fixture object only"],
                "source_kind": "DOCUMENTED",
                "source_refs": ["fixture://workspace-limits"],
                "operator_supervision_required": True,
            },
            "abort": {
                "availability": "DOCUMENTED_ONLY",
                "hardware_estop": "fixture controller E-stop",
                "controller_disable_method": "fixture controller power disable",
                "software_abort_interface": "not used by this task",
                "manual_operator_action": "press E-stop and disable controller power",
                "operator_location": "within immediate reach of E-stop",
                "motion_tested": False,
            },
        }

    @staticmethod
    def successful_camera_probe(
        path: Path, frame_count: int, timeout_seconds: float
    ) -> dict[str, Any]:
        return {
            "status": "PASS",
            "opened": True,
            "frames_requested": frame_count,
            "frames_acquired": frame_count,
            "frames_persisted": 0,
            "width": 640,
            "height": 480,
            "channels": 3,
            "pixel_format": "YUYV",
            "driver_reported_fps": 30.0,
            "acquisition_elapsed_seconds": 0.02,
            "diagnostic_observed_fps": 50.0,
            "timed_out": False,
            "detail": "synthetic fixture camera probe succeeded",
        }

    @staticmethod
    def successful_state_probe(path: Path, timeout_seconds: float) -> dict[str, Any]:
        return {
            "status": "PASS",
            "bytes_read": 32,
            "snapshot_sha256": "a" * 64,
            "timed_out": False,
            "detail": "synthetic fixture state probe succeeded",
        }

    def collect(self, **overrides: Any) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "declarations": self.declarations(),
            "declaration_source": "synthetic test fixture",
            "dev_root": self.dev_root,
            "camera_probe": self.successful_camera_probe,
            "state_probe": self.successful_state_probe,
        }
        arguments.update(overrides)
        return self.verifier.collect_evidence(REPOSITORY_ROOT, **arguments)

    def test_normal_synthetic_device_discovery_path_is_ready(self) -> None:
        evidence = self.collect()

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_READY")
        self.assertEqual(self.verifier.validate_evidence(evidence), [])
        self.assertTrue(all(item["status"] == "PASS" for item in evidence["checks"]))
        self.assertFalse(evidence["safety"]["robot_motion_commanded"])
        self.assertFalse(evidence["command_path"]["executed"])
        self.assertEqual(evidence["camera"]["acquisition"]["frames_persisted"], 0)
        self.assertEqual(evidence["state_path"]["provenance"], "DECLARED_INPUT")
        self.assertEqual(evidence["command_path"]["provenance"], "DECLARED_INPUT")
        self.assertEqual(
            evidence["workspace_safety_boundary"]["provenance"],
            "DECLARED_INPUT",
        )
        self.assertEqual(
            evidence["workspace_safety_boundary"]["declared_source_kind"],
            "DOCUMENTED",
        )

    def test_missing_robot_device_propagates_to_blocked(self) -> None:
        self.robot_path.unlink()

        evidence = self.collect()

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][1]["status"], "BLOCKED")
        self.assertIn("C02", {item["check_id"] for item in evidence["unresolved_blockers"]})

    def test_permission_failure_propagates_to_blocked(self) -> None:
        def deny_robot_write(path: Path, mode: int) -> bool:
            if path == self.robot_path and mode == os.W_OK:
                return False
            return os.access(path, mode)

        evidence = self.collect(access_checker=deny_robot_write)

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][3]["status"], "BLOCKED")
        self.assertFalse(evidence["robot_device"]["permissions_changed"])

    def test_missing_camera_path_propagates_to_blocked(self) -> None:
        self.camera_path.unlink()

        evidence = self.collect()

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][9]["status"], "BLOCKED")
        self.assertFalse(evidence["camera"]["acquisition"]["attempted"])

    def test_bounded_camera_acquisition_failure_propagates(self) -> None:
        def failed_probe(
            path: Path, frame_count: int, timeout_seconds: float
        ) -> dict[str, Any]:
            return {
                "status": "BLOCKED",
                "opened": False,
                "frames_requested": frame_count,
                "frames_acquired": 0,
                "frames_persisted": 0,
                "timed_out": True,
                "detail": "synthetic bounded acquisition timeout",
            }

        evidence = self.collect(camera_probe=failed_probe)

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][10]["status"], "BLOCKED")
        self.assertTrue(evidence["camera"]["acquisition"]["timed_out"])

    def test_partial_camera_success_diagnostic_fails_closed(self) -> None:
        def malformed_probe(
            path: Path, frame_count: int, timeout_seconds: float
        ) -> dict[str, Any]:
            return {
                "status": "PASS",
                "opened": True,
                "frames_requested": frame_count,
                "frames_acquired": 0,
                "frames_persisted": 0,
                "timed_out": False,
                "detail": "synthetic malformed success diagnostic",
            }

        evidence = self.collect(camera_probe=malformed_probe)

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][10]["status"], "BLOCKED")
        self.assertEqual(evidence["checks"][11]["status"], "BLOCKED")

    def test_partial_declaration_fails_closed_without_probe(self) -> None:
        evidence = self.verifier.collect_evidence(
            REPOSITORY_ROOT,
            declarations={"target_hardware": {"manufacturer": "partial"}},
            declaration_source="synthetic partial fixture",
            dev_root=self.dev_root,
            camera_probe=self.successful_camera_probe,
            state_probe=self.successful_state_probe,
        )

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertTrue(evidence["declarations"]["errors"])
        self.assertFalse(evidence["camera"]["acquisition"]["attempted"])
        self.assertFalse(evidence["state_path"]["observation"]["attempted"])

    def test_declared_device_paths_cannot_escape_device_root(self) -> None:
        declarations = self.declarations()
        declarations["target_hardware"]["robot_device_path"] = "/etc/passwd"
        declarations["camera"]["device_path"] = "/etc/passwd"

        evidence = self.verifier.collect_evidence(
            REPOSITORY_ROOT,
            declarations=declarations,
            declaration_source="synthetic unsafe-path fixture",
            dev_root=self.dev_root,
            camera_probe=self.successful_camera_probe,
            state_probe=self.successful_state_probe,
        )

        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertTrue(
            any("must be a ttyUSB*/ttyACM* path" in item for item in evidence["declarations"]["errors"])
        )
        self.assertTrue(
            any("must be a video* path" in item for item in evidence["declarations"]["errors"])
        )
        self.assertIsNone(evidence["robot_device"]["selected_metadata"])
        self.assertFalse(evidence["camera"]["acquisition"]["attempted"])

    def test_device_discovery_timeout_is_bounded_and_blocks_readiness(self) -> None:
        def slow_access(path: Path, mode: int) -> bool:
            time.sleep(2)
            return True

        started = time.monotonic()
        evidence = self.collect(
            access_checker=slow_access,
            device_discovery_timeout_seconds=0.05,
        )
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 1.0)
        self.assertTrue(evidence["device_discovery"]["timed_out"])
        self.assertEqual(evidence["device_discovery"]["status"], "BLOCKED")
        self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
        self.assertEqual(evidence["checks"][1]["status"], "BLOCKED")

    def test_evidence_validation_rejects_aggregate_mismatch(self) -> None:
        evidence = self.collect()
        evidence["checks"][0]["status"] = "BLOCKED"

        errors = self.verifier.validate_evidence(evidence)

        self.assertTrue(
            any("aggregate decision" in error for error in errors), errors
        )

    def test_timeout_helper_is_bounded_and_reports_timeout(self) -> None:
        started = __import__("time").monotonic()
        result = self.verifier._run(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.05,
        )
        elapsed = __import__("time").monotonic() - started

        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["returncode"])
        self.assertLess(elapsed, 1.0)

    def test_decision_requires_at_least_one_mandatory_check_and_all_pass(self) -> None:
        self.assertEqual(self.verifier.decide_readiness([]), "DEVICE_IO_BLOCKED")
        self.assertEqual(
            self.verifier.decide_readiness(
                [
                    {"mandatory": True, "status": "PASS"},
                    {"mandatory": True, "status": "NOT_VERIFIED"},
                ]
            ),
            "DEVICE_IO_BLOCKED",
        )


class RobotIoReadinessCliTests(unittest.TestCase):
    def test_no_declarations_writes_atomic_blocking_evidence_and_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "evidence.json"
            dev_root = Path(temporary_directory) / "empty-dev"
            dev_root.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    str(output),
                    "--dev-root",
                    str(dev_root),
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
            self.assertFalse(evidence["task_w1_001_authorized"])
            self.assertTrue(evidence["p0_004r_required"])
            self.assertFalse(list(output.parent.glob(f".{output.name}.*.tmp")))

    def test_invalid_declaration_json_is_a_blocker_not_verifier_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            declarations = root / "invalid.json"
            declarations.write_text("{invalid", encoding="utf-8")
            output = root / "evidence.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--declarations",
                    str(declarations),
                    "--output",
                    str(output),
                    "--dev-root",
                    str(root),
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["device_io_decision"], "DEVICE_IO_BLOCKED")
            self.assertTrue(evidence["declarations"]["errors"])

    def test_invalid_bounds_return_verifier_error_without_device_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "evidence.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--output",
                    str(output),
                    "--camera-frame-count",
                    "99",
                ],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(completed.returncode, 3)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
