from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_simulation_lane_gate.py"
SPEC = importlib.util.spec_from_file_location("verify_simulation_lane_gate", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT}")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _write_json(root: Path, relative: str, value: dict[str, Any]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def _resign_payload(value: dict[str, Any]) -> None:
    value["payload_sha256"] = gate.canonical_payload_sha256(value)


class SimulationLaneGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._copy_gate_inputs()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _copy_gate_inputs(self) -> None:
        paths = set(gate.REQUIRED_CONTEXT_PATHS)
        for relative in (
            "results/simulation/SIM-001_contract_profile.json",
            "results/simulation/SIM-002_smoke_runtime.json",
        ):
            evidence = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            paths.update(binding["path"] for binding in evidence["source_bindings"])
        for relative in (
            "results/reviews/SIM-001_acceptance.json",
            "results/reviews/SIM-002_acceptance.json",
        ):
            acceptance = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            paths.update(
                value
                for key, value in acceptance.items()
                if key.endswith("_path") and isinstance(value, str)
            )
        for relative in paths:
            source = ROOT / relative
            if source.is_file():
                destination = self.root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)

    def evaluate(self) -> dict[str, Any]:
        return gate.evaluate_simulation_lane_gate(
            self.root,
            git_root=ROOT,
            generation_timestamp="2026-09-14T00:00:00Z",
            generation_git_head="6503618c83a51714a4ad948f58917832e8bbc4e2",
            pre_implementation_clean=True,
        )

    def assert_no_go(self, mutation: Callable[[], None], failed_check: str) -> None:
        mutation()
        result = self.evaluate()
        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"][failed_check]["status"], "FAIL")
        self.assertFalse(result["authorization_snapshot"]["simulation_lane_authorized"])
        self.assertFalse(result["simulation_lane_authorization_effective"])

    def _update_sim_002_acceptance_for_evidence(self, evidence: dict[str, Any]) -> None:
        _resign_payload(evidence)
        _write_json(self.root, "results/simulation/SIM-002_smoke_runtime.json", evidence)
        acceptance = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
        acceptance["evidence_sha256"] = _sha(
            self.root, "results/simulation/SIM-002_smoke_runtime.json"
        )
        acceptance["evidence_payload_sha256"] = evidence["payload_sha256"]
        _write_json(self.root, "results/reviews/SIM-002_acceptance.json", acceptance)

    def test_canonical_state_reconstructs_sim_go_without_authorizing_lane(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["gate_result"], "SIM_GO")
        self.assertEqual(set(result["material_predicates"]), {f"C{i:02d}" for i in range(1, 21)})
        self.assertTrue(all(item["status"] == "PASS" for item in result["material_predicates"].values()))
        self.assertEqual(result["unresolved_blockers"], [])
        self.assertEqual(result["independent_acceptance"], "PENDING")
        self.assertFalse(result["simulation_lane_authorization_effective"])
        expected = {
            "simulation_lane_authorized": False,
            "task_w1_001_authorized": False,
            "task_w1_002_authorized": False,
            "dataset_v1_authorized": False,
            "fine_tuning_authorized": False,
            "physical_motion_authorized": False,
            "physical_gripper_authorized": False,
            "physical_teleop_authorized": False,
            "physical_dataset_collection_authorized": False,
            "hardware_target_frozen": False,
        }
        self.assertEqual(result["authorization_snapshot"], expected)
        self.assertEqual(result["payload_sha256"], gate.canonical_payload_sha256(result))

    def test_sim_001_accept_plus_blocked_fails_closed(self) -> None:
        def mutate() -> None:
            value = _read_json(self.root, "results/reviews/SIM-001_acceptance.json")
            value["task_specific_decision"] = "SIM_CONTRACT_PROFILE_BLOCKED"
            _write_json(self.root, "results/reviews/SIM-001_acceptance.json", value)

        self.assert_no_go(mutate, "C04")

    def test_sim_001_ready_without_independent_acceptance_fails_closed(self) -> None:
        self.assert_no_go(
            lambda: (self.root / "results/reviews/SIM-001_acceptance.json").unlink(),
            "C03",
        )

    def test_sim_001_acceptance_pointing_to_stale_evidence_fails_closed(self) -> None:
        def mutate() -> None:
            path = self.root / "results/simulation/SIM-001_contract_profile.json"
            path.write_bytes(path.read_bytes() + b"\n")

        self.assert_no_go(mutate, "C05")

    def test_sim_001_profile_hash_mismatch_fails_closed(self) -> None:
        def mutate() -> None:
            path = self.root / "docs/simulation/simulation_contract_profile_v1.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")

        self.assert_no_go(mutate, "C05")

    def test_sim_002_accept_plus_blocked_fails_closed(self) -> None:
        def mutate() -> None:
            value = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
            value["task_specific_decision"] = "SIM_SMOKE_BLOCKED"
            _write_json(self.root, "results/reviews/SIM-002_acceptance.json", value)

        self.assert_no_go(mutate, "C07")

    def test_sim_002_ready_without_independent_acceptance_fails_closed(self) -> None:
        self.assert_no_go(
            lambda: (self.root / "results/reviews/SIM-002_acceptance.json").unlink(),
            "C06",
        )

    def test_sim_002_acceptance_pointing_to_stale_evidence_fails_closed(self) -> None:
        def mutate() -> None:
            path = self.root / "results/simulation/SIM-002_smoke_runtime.json"
            path.write_bytes(path.read_bytes() + b"\n")

        self.assert_no_go(mutate, "C08")

    def test_sim_002_bound_to_different_sim_001_revision_fails_closed(self) -> None:
        def mutate() -> None:
            evidence = _read_json(self.root, "results/simulation/SIM-002_smoke_runtime.json")
            evidence["sim_001_binding"]["acceptance_sha256"] = "0" * 64
            self._update_sim_002_acceptance_for_evidence(evidence)

        self.assert_no_go(mutate, "C09")

    def test_self_reported_acceptance_without_artifact_fails_closed(self) -> None:
        def mutate() -> None:
            evidence = _read_json(self.root, "results/simulation/SIM-002_smoke_runtime.json")
            evidence["accepted"] = True
            _resign_payload(evidence)
            _write_json(self.root, "results/simulation/SIM-002_smoke_runtime.json", evidence)
            (self.root / "results/reviews/SIM-002_acceptance.json").unlink()

        self.assert_no_go(mutate, "C06")

    def test_p0_week_authorization_mutation_fails_closed(self) -> None:
        def mutate() -> None:
            value = _read_json(self.root, "results/phase0/P0-004R_vla_readiness.json")
            value["authorization"]["task_w1_001"] = True
            _write_json(self.root, "results/phase0/P0-004R_vla_readiness.json", value)

        self.assert_no_go(mutate, "C14")

    def test_missing_p0_authorization_source_fails_closed(self) -> None:
        self.assert_no_go(
            lambda: (self.root / "results/phase0/P0-004R_vla_readiness.json").unlink(),
            "C19",
        )

    def test_dataset_v1_aliasing_fails_closed_even_with_resigned_evidence(self) -> None:
        def mutate() -> None:
            evidence = _read_json(self.root, "results/simulation/SIM-002_smoke_runtime.json")
            evidence["dataset_v1_created"] = True
            self._update_sim_002_acceptance_for_evidence(evidence)

        self.assert_no_go(mutate, "C15")

    def test_physical_motion_authorization_true_fails_closed_even_with_resigned_evidence(self) -> None:
        def mutate() -> None:
            evidence = _read_json(self.root, "results/simulation/SIM-002_smoke_runtime.json")
            evidence["authorization_snapshot"]["physical_motion_authorized"] = True
            self._update_sim_002_acceptance_for_evidence(evidence)

        self.assert_no_go(mutate, "C13")

    def test_direct_actuator_contract_detected(self) -> None:
        def mutate() -> None:
            evidence = _read_json(self.root, "results/simulation/SIM-001_contract_profile.json")
            evidence["direct_actuator_contract_introduced"] = True
            _resign_payload(evidence)
            _write_json(self.root, "results/simulation/SIM-001_contract_profile.json", evidence)

        self.assert_no_go(mutate, "C18")

    def test_rehashed_unreviewed_runtime_with_direct_actuator_operation_fails_closed(self) -> None:
        runtime_relative = "src/simulation_runtime/smoke.py"
        runtime_path = self.root / runtime_relative
        runtime_path.write_text(
            runtime_path.read_text(encoding="utf-8")
            + '\nDIRECT_ACTUATOR_OPERATION = "actuator.execute"\n',
            encoding="utf-8",
        )
        acceptance = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
        acceptance["runtime_module_sha256"] = _sha(self.root, runtime_relative)
        _write_json(self.root, "results/reviews/SIM-002_acceptance.json", acceptance)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "FAIL")
        self.assertFalse(result["simulation_lane_authorization_effective"])

    def test_unknown_logical_operation_is_not_allowlisted(self) -> None:
        runtime = (self.root / "src/simulation_runtime/smoke.py").read_text(encoding="utf-8")
        self.assertTrue(gate._runtime_operations_are_allowlisted(runtime))
        self.assertFalse(
            gate._runtime_operations_are_allowlisted(
                runtime + '\nUNREVIEWED_OPERATION = "controller.dispatch"\n'
            )
        )

    def test_malformed_p0_authorizations_emit_only_conservative_booleans(self) -> None:
        malformed_values = ("false", 0, None)
        source_keys = (
            "task_w1_001",
            "task_w1_002",
            "dataset_v1",
            "smolvla_fine_tuning",
            "physical_motion",
        )
        snapshot_keys = (
            "task_w1_001_authorized",
            "task_w1_002_authorized",
            "dataset_v1_authorized",
            "fine_tuning_authorized",
            "physical_motion_authorized",
        )
        original = _read_json(self.root, "results/phase0/P0-004R_vla_readiness.json")

        for malformed in malformed_values:
            for source_key in source_keys:
                with self.subTest(source_key=source_key, malformed=malformed):
                    value = json.loads(json.dumps(original))
                    value["authorization"][source_key] = malformed
                    _write_json(self.root, "results/phase0/P0-004R_vla_readiness.json", value)
                    result = self.evaluate()
                    self.assertEqual(result["gate_result"], "SIM_NO_GO")
                    self.assertEqual(result["material_predicates"]["C19"]["status"], "FAIL")
                    self.assertTrue(
                        all(
                            isinstance(result["authorization_snapshot"][key], bool)
                            for key in snapshot_keys
                        )
                    )
                    self.assertFalse(result["authorization_snapshot"][snapshot_keys[source_keys.index(source_key)]])

    def test_forged_sim_go_with_valid_payload_does_not_override_failure(self) -> None:
        def mutate() -> None:
            forged = {
                "task_id": "TASK-SIM-GATE",
                "gate_result": "SIM_GO",
                "material_predicates": {"self_reported": True},
            }
            _resign_payload(forged)
            _write_json(self.root, "results/simulation/SIM-GATE_readiness.json", forged)
            (self.root / "results/reviews/SIM-002_acceptance.json").unlink()

        self.assert_no_go(mutate, "C06")


if __name__ == "__main__":
    unittest.main()
