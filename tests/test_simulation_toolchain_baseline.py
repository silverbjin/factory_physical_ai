from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_simulation_toolchain_baseline.py"
SPEC = importlib.util.spec_from_file_location("verify_simulation_toolchain_baseline", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT}")
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


def _result(command: Sequence[str], stdout: str = "", *, returncode: int = 0) -> dict[str, Any]:
    return {
        "command": list(command),
        "timeout_seconds": 5,
        "available": True,
        "returncode": returncode,
        "timed_out": False,
        "duration_seconds": 0.001,
        "stdout": stdout,
        "stderr": "" if returncode == 0 else "probe failed",
        "process_group_cleanup_complete": True,
    }


def _copy_predecessors(destination_root: Path) -> None:
    for relative in baseline.PRESERVED_ACCEPTED_PATHS:
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


class ReadyRunner:
    def __init__(self, *, mujoco_available: bool = True) -> None:
        self.commands: list[list[str]] = []
        self.mujoco_available = mujoco_available

    def __call__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float,
        cwd: Path,
        env: dict[str, str],
    ) -> dict[str, Any]:
        del timeout_seconds, cwd, env
        command = list(command)
        self.commands.append(command)
        if command[-1:] == ["--help"]:
            return _result(command, "ros2 help")
        if command[-3:] == ["pkg", "prefix", "rclpy"]:
            return _result(command, "/opt/ros/jazzy")
        if "importlib.metadata" in " ".join(command) and "rclpy" in " ".join(command):
            return _result(
                command,
                json.dumps(
                    {
                        "version": "7.1.11",
                        "module_path": "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py",
                    }
                ),
            )
        if len(command) >= 4 and command[-3:-1] == ["pkg", "executables"]:
            pairs = (*baseline.ROS_GZ_ENTRY_POINTS, *baseline.NAV2_ENTRY_POINTS)
            requested_package = command[-1]
            return _result(
                command,
                "\n".join(
                    f"{package} {executable}"
                    for package, executable in pairs
                    if package == requested_package
                ),
            )
        if command[-2:] == ["sim", "--version"]:
            return _result(command, "Gazebo Sim, version 8.11.0")
        if "--iterations" in command:
            return _result(command)
        if "import mujoco" in " ".join(command):
            if not self.mujoco_available:
                return _result(command, returncode=1)
            return _result(
                command,
                json.dumps(
                    {
                        "version": "3.3.5",
                        "model_loaded": True,
                        "steps": 1,
                        "time_before": 0.0,
                        "time_after": 0.002,
                        "nq": 7,
                        "nv": 6,
                        "viewer_used": False,
                        "rendering_requested": False,
                    }
                ),
            )
        if "pytest" in command:
            return _result(command, "tests passed")
        raise AssertionError(f"unexpected command: {command}")


class SimulationToolchainBaselineTests(unittest.TestCase):
    def evaluate(self, runner: ReadyRunner) -> dict[str, Any]:
        return baseline.evaluate_baseline(
            ROOT,
            git_root=ROOT,
            runner=runner,
            environ={"ROS_DISTRO": "jazzy"},
            which=lambda name: f"/opt/ros/jazzy/bin/{name}",
            generation_timestamp="2026-09-16T00:00:00Z",
            pre_implementation_clean=True,
        )

    def test_current_predecessor_chain_is_exact_and_accepted(self) -> None:
        result = baseline.validate_predecessors(ROOT, git_root=ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(check["status"] == "PASS" for check in result["checks"]))
        decisions = {item["task_id"]: item.get("task_specific_decision") for item in result["bindings"]}
        self.assertEqual(decisions["TASK-SIM-C01"], "SIM_CONTRACT_GAPS_RESOLVED")
        self.assertEqual(decisions["TASK-SIM-001"], "SIM_CONTRACT_PROFILE_READY")
        self.assertEqual(decisions["TASK-SIM-002"], "SIM_SMOKE_READY")
        self.assertEqual(decisions["TASK-SIM-GATE"], "SIM_GO")

    def test_toolchain_probes_run_only_after_predecessors_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            _copy_predecessors(temporary_root)
            acceptance_path = temporary_root / baseline.ACCEPTANCE_PATHS["TASK-SIM-001"]
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["review_decision"] = "REJECT"
            acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")

            def forbidden_runner(*args: Any, **kwargs: Any) -> dict[str, Any]:
                raise AssertionError(f"toolchain probe ran: {args}, {kwargs}")

            result = baseline.evaluate_baseline(
                temporary_root,
                git_root=ROOT,
                runner=forbidden_runner,
                environ={"ROS_DISTRO": "jazzy"},
            )
        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_BLOCKED")
        self.assertEqual(result["runtime"]["probe_order"], "SKIPPED_DUE_TO_PREDECESSOR_FAILURE")

    def test_unrelated_existing_reviewed_commit_fails_predecessor_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            _copy_predecessors(temporary_root)
            acceptance_path = temporary_root / baseline.ACCEPTANCE_PATHS["TASK-SIM-GATE"]
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["reviewed_commit"] = "ce41227020357d95f14dfd2986f102ccc063c5f9"
            acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")
            result = baseline.validate_predecessors(temporary_root, git_root=ROOT)

        checks = {item["check_id"]: item["status"] for item in result["checks"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(checks["TASK-SIM-GATE:reviewed_commit"], "FAIL")

    def test_regression_mutation_of_accepted_artifact_fails_closed(self) -> None:
        class MutatingRunner(ReadyRunner):
            def __call__(
                self,
                command: Sequence[str],
                *,
                timeout_seconds: float,
                cwd: Path,
                env: dict[str, str],
            ) -> dict[str, Any]:
                if "pytest" in command:
                    target = cwd / "results/simulation/SIM-GATE_readiness.json"
                    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                return super().__call__(
                    command, timeout_seconds=timeout_seconds, cwd=cwd, env=env
                )

        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            _copy_predecessors(temporary_root)
            result = baseline.evaluate_baseline(
                temporary_root,
                git_root=ROOT,
                runner=MutatingRunner(),
                environ={"ROS_DISTRO": "jazzy"},
                which=lambda name: f"/opt/ros/jazzy/bin/{name}",
                generation_timestamp="2026-09-16T00:00:00Z",
            )

        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_BLOCKED")
        self.assertIn("accepted_evidence_preservation", result["blockers"])
        self.assertTrue(result["deterministic_regression"]["accepted_evidence_modified"])
        self.assertEqual(result["accepted_artifact_preservation"]["status"], "FAIL")

    def test_ready_result_requires_every_runtime_and_bounded_smoke(self) -> None:
        result = self.evaluate(ReadyRunner())
        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_READY")
        self.assertEqual(result["blockers"], [])
        for name in ("ros2", "gazebo", "ros_gz", "nav2", "mujoco"):
            self.assertEqual(result["runtime"][name]["status"], "PASS")
        self.assertTrue(result["runtime"]["gazebo"]["headless_smoke"]["process_group_cleanup_complete"])
        self.assertEqual(result["runtime"]["gazebo"]["smoke_mode"], "server_only_headless")
        self.assertFalse(result["runtime"]["gazebo"]["navigation_mission_executed"])
        self.assertTrue(result["runtime"]["mujoco"]["step_result"]["time_after"] > 0)

    def test_missing_mujoco_fails_closed_without_guessing_version(self) -> None:
        result = self.evaluate(ReadyRunner(mujoco_available=False))
        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_BLOCKED")
        self.assertIn("mujoco_headless_step", result["blockers"])
        self.assertIsNone(result["runtime"]["mujoco"]["version"])
        self.assertIsNone(result["authority_policy"]["mujoco_version"])
        self.assertFalse(result["downstream_eligibility"]["eligible_after_independent_acceptance"])

    def test_wrong_ros_distribution_fails_closed(self) -> None:
        runner = ReadyRunner()
        result = baseline.evaluate_baseline(
            ROOT,
            git_root=ROOT,
            runner=runner,
            environ={"ROS_DISTRO": "humble"},
            which=lambda name: f"/opt/ros/humble/bin/{name}",
            generation_timestamp="2026-09-16T00:00:00Z",
        )
        self.assertEqual(result["runtime"]["ros2"]["status"], "FAIL")
        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_BLOCKED")

    def test_humble_executable_cannot_pass_with_jazzy_environment_label(self) -> None:
        runner = ReadyRunner()
        result = baseline.evaluate_baseline(
            ROOT,
            git_root=ROOT,
            runner=runner,
            environ={"ROS_DISTRO": "jazzy"},
            which=lambda name: f"/opt/ros/humble/bin/{name}",
            generation_timestamp="2026-09-16T00:00:00Z",
        )
        self.assertEqual(result["runtime"]["ros2"]["status"], "FAIL")
        self.assertFalse(result["runtime"]["ros2"]["identity_matches"])
        self.assertEqual(result["task_specific_result"], "SIM_BASELINE_BLOCKED")

    def test_authority_and_fidelity_are_frozen_exactly(self) -> None:
        result = self.evaluate(ReadyRunner())
        for key, value in baseline.AUTHORITY_POLICY.items():
            self.assertEqual(result["authority_policy"][key], value)
        self.assertEqual(result["fidelity_policy"]["levels"], list(baseline.FIDELITY_LEVELS))
        self.assertFalse(result["authority_policy"]["simulation_evidence_is_physical_evidence"])
        self.assertFalse(result["authority_policy"]["physical_target_frozen"])
        self.assertEqual(
            result["validation_commands"]["focused"][-3:],
            [
                "tests/test_simulation_toolchain_baseline.py",
                "tests/test_simulation_execution_contract.py",
                "tests/test_simulation_smoke.py",
            ],
        )

    def test_nav2_and_ros_gz_surface_is_exact(self) -> None:
        result = self.evaluate(ReadyRunner())
        ros_gz = {(item["package"], item["executable"]) for item in result["runtime"]["ros_gz"]["entry_points"]}
        nav2 = {(item["package"], item["executable"]) for item in result["runtime"]["nav2"]["entry_points"]}
        self.assertEqual(ros_gz, set(baseline.ROS_GZ_ENTRY_POINTS))
        self.assertEqual(nav2, set(baseline.NAV2_ENTRY_POINTS))

    def test_payload_and_source_bindings_are_self_consistent(self) -> None:
        result = self.evaluate(ReadyRunner())
        self.assertEqual(result["payload_sha256"], baseline.canonical_payload_sha256(result))
        self.assertTrue(all(item["exists"] for item in result["source_bindings"]))
        for item in result["source_bindings"]:
            digest = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
            self.assertEqual(item["sha256"], digest)

    def test_report_matches_result_and_non_authorization(self) -> None:
        result = self.evaluate(ReadyRunner(mujoco_available=False))
        report = baseline.render_report(result)
        self.assertIn("`SIM_BASELINE_BLOCKED`", report)
        self.assertIn("`dual_world_cosimulation = prohibited_v1`", report)
        self.assertIn("mujoco_headless_step", report)
        self.assertIn("requires independent acceptance", report)

    def test_canonical_evidence_and_report_match_live_files(self) -> None:
        evidence_path = ROOT / "results/simulation/SIM-003_baseline.json"
        report_path = ROOT / "docs/simulation/simulation_baseline_v1.md"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["payload_sha256"], baseline.canonical_payload_sha256(evidence))
        self.assertEqual(report_path.read_text(encoding="utf-8"), baseline.render_report(evidence))
        self.assertEqual(evidence["predecessors"]["status"], "PASS")
        self.assertIn(evidence["task_specific_result"], {baseline.READY, baseline.BLOCKED})
        self.assertFalse(evidence["downstream_eligibility"]["task_sim_004_eligible_now"])
        self.assertFalse(evidence["downstream_eligibility"]["task_sim_005_eligible_now"])

    def test_accepted_predecessor_artifacts_remain_unchanged(self) -> None:
        expected = {
            "results/reviews/SIM-GATE_acceptance.json": "31195148a649b142abae43fe91bc017744827615de1c3a1f662763262a0ced5a",
            "results/simulation/SIM-GATE_readiness.json": "82c837e519c37799cb5a88af14470d2b74ba5d75913e811eac752f8e80f8b312",
            "results/reviews/SIM-C01_acceptance.json": "1aee7a19f24cf52da3a2c0b232872420aafe7f1e644ed5fb1a493a025c5ee2d5",
            "results/reviews/SIM-001_acceptance.json": "bf1fe8df30a73339fcdd90a5bbc3d0cf5963a0a02d538102e732054e175f5e53",
            "results/reviews/SIM-002_acceptance.json": "07ee8867208498719b1a5bed04fb7572a881e2e470b6d218648aaecaf5d02951",
            "docs/contracts/simulation_execution_contract_v1.md": "0451e9abae4cee911d9468d11e68b8bbb0e3aff1a1a2d9cf104ed64264d28caa",
            "docs/contracts/schemas/simulation_execution_contract_v1.schema.json": "112b1e2e0d1fefb03d7b353e8ed4d875b025fe342380d5ba1cbf050bcc7d944a",
        }
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
