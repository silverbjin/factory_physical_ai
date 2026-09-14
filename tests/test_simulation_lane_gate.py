from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import simulation_runtime.smoke as accepted_runtime  # noqa: E402

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
        paths.add(gate.SIM_002_RUNTIME_INIT_PATH)
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

    def _clone_review_git(self) -> Path:
        review_git = self.root / "review-git"
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(review_git)],
            check=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "config", "user.name", "SIM Gate Regression"],
            cwd=review_git,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "sim-gate-regression@example.invalid"],
            cwd=review_git,
            check=True,
        )
        return review_git

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

    def test_rehashed_unreviewed_runtime_operation_marker_fails_provenance_closed(self) -> None:
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
        self.assertEqual(result["material_predicates"]["C18"]["status"], "PASS")
        self.assertFalse(result["simulation_lane_authorization_effective"])

    def test_combined_review_commit_rewrite_and_concatenated_operation_fails_closed(self) -> None:
        review_git = self._clone_review_git()

        runtime_relative = "src/simulation_runtime/smoke.py"
        attack = '\nDIRECT_ACTUATOR_OPERATION = "actuator" + ".execute"\n'
        for base in (self.root, review_git):
            runtime_path = base / runtime_relative
            runtime_path.write_text(runtime_path.read_text(encoding="utf-8") + attack, encoding="utf-8")
        subprocess.run(["git", "add", runtime_relative], cwd=review_git, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "unreviewed runtime mutation"],
            cwd=review_git,
            check=True,
        )
        mutated_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=review_git,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        acceptance = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
        original_reviewed_commit = acceptance["reviewed_commit"]
        acceptance["reviewed_commit"] = mutated_commit
        acceptance["runtime_module_sha256"] = _sha(self.root, runtime_relative)
        _write_json(self.root, "results/reviews/SIM-002_acceptance.json", acceptance)

        result = gate.evaluate_simulation_lane_gate(
            self.root,
            git_root=review_git,
            generation_timestamp="2026-09-14T00:00:00Z",
            generation_git_head=mutated_commit,
            pre_implementation_clean=True,
        )

        review_text = (self.root / gate.SIM_002_REVIEW_RECORD_PATH).read_text(encoding="utf-8")
        self.assertIn(original_reviewed_commit, review_text)
        self.assertNotIn(mutated_commit, review_text)
        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")
        self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "PASS")

    def test_b04_review_record_and_acceptance_rewrite_remains_bound_to_historical_anchor(self) -> None:
        review_git = self._clone_review_git()
        runtime_relative = "src/simulation_runtime/smoke.py"
        attack = '\nUNREVIEWED_RUNTIME_REVISION = "different commit"\n'
        for base in (self.root, review_git):
            runtime_path = base / runtime_relative
            runtime_path.write_text(runtime_path.read_text(encoding="utf-8") + attack, encoding="utf-8")
        subprocess.run(["git", "add", runtime_relative], cwd=review_git, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "-m", "unreviewed SIM-002 runtime revision"],
            cwd=review_git,
            check=True,
        )
        mutated_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=review_git,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        acceptance_path = "results/reviews/SIM-002_acceptance.json"
        acceptance = _read_json(self.root, acceptance_path)
        original_reviewed_commit = acceptance["reviewed_commit"]
        review_path = self.root / gate.SIM_002_REVIEW_RECORD_PATH
        review_path.write_text(
            review_path.read_text(encoding="utf-8").replace(
                original_reviewed_commit, mutated_commit
            ),
            encoding="utf-8",
        )
        acceptance["reviewed_commit"] = mutated_commit
        acceptance["runtime_module_sha256"] = _sha(self.root, runtime_relative)
        acceptance["review_record_sha256"] = _sha(
            self.root, gate.SIM_002_REVIEW_RECORD_PATH
        )
        _write_json(self.root, acceptance_path, acceptance)

        result = gate.evaluate_simulation_lane_gate(
            self.root,
            git_root=review_git,
            generation_timestamp="2026-09-14T00:00:00Z",
            generation_git_head=mutated_commit,
            pre_implementation_clean=True,
        )

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["sim_002"]["reviewed_commit"], original_reviewed_commit)
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")
        self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")

    def test_current_review_record_modified_after_anchor_fails_closed(self) -> None:
        review_path = self.root / gate.SIM_002_REVIEW_RECORD_PATH
        review_path.write_text(review_path.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")
        acceptance = _read_json(self.root, gate.SIM_002_ACCEPTANCE_PATH)
        acceptance["review_record_sha256"] = _sha(self.root, gate.SIM_002_REVIEW_RECORD_PATH)
        _write_json(self.root, gate.SIM_002_ACCEPTANCE_PATH, acceptance)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")

    def test_acceptance_review_record_sha_rewrite_fails_closed(self) -> None:
        def mutate() -> None:
            acceptance = _read_json(self.root, gate.SIM_002_ACCEPTANCE_PATH)
            acceptance["review_record_sha256"] = "0" * 64
            _write_json(self.root, gate.SIM_002_ACCEPTANCE_PATH, acceptance)

        self.assert_no_go(mutate, "C06")

    def test_canonical_review_path_substitution_fails_closed(self) -> None:
        substitute = "docs/task_history/TASK-SIM-002/substitute_review.md"
        destination = self.root / substitute
        destination.write_bytes((self.root / gate.SIM_002_REVIEW_RECORD_PATH).read_bytes())
        acceptance = _read_json(self.root, gate.SIM_002_ACCEPTANCE_PATH)
        acceptance["review_record_path"] = substitute
        acceptance["review_record_sha256"] = _sha(self.root, substitute)
        _write_json(self.root, gate.SIM_002_ACCEPTANCE_PATH, acceptance)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")

    def test_missing_or_ambiguous_review_anchor_fails_closed(self) -> None:
        scenarios = ([], ["1" * 40, "2" * 40])
        for introductions in scenarios:
            with self.subTest(introductions=introductions):
                with mock.patch.object(
                    gate,
                    "_git_path_introduction_commits",
                    return_value=introductions,
                ):
                    result = self.evaluate()
                self.assertEqual(result["gate_result"], "SIM_NO_GO")
                self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")

    def test_reviewed_implementation_must_precede_review_anchor(self) -> None:
        with mock.patch.object(gate, "_git_is_strict_ancestor", return_value=False):
            result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")

    def test_acceptance_introduction_must_follow_review_anchor(self) -> None:
        with mock.patch.object(
            gate,
            "_git_is_strict_ancestor",
            side_effect=(True, False),
        ):
            result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C06"]["status"], "FAIL")

    def test_acceptance_reviewed_commit_rewrite_fails_closed(self) -> None:
        def mutate() -> None:
            acceptance = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
            acceptance["reviewed_commit"] = "0" * 40
            _write_json(self.root, "results/reviews/SIM-002_acceptance.json", acceptance)

        self.assert_no_go(mutate, "C06")

    def test_sim_002_canonical_path_substitutions_fail_closed(self) -> None:
        acceptance_path = "results/reviews/SIM-002_acceptance.json"
        original_acceptance = _read_json(self.root, acceptance_path)
        for path_key, sha_key, canonical in gate.EXPECTED_SIM_002_REVIEWED_ARTIFACTS:
            with self.subTest(path_key=path_key):
                substitute = f"substitutes/{Path(canonical).name}"
                destination = self.root / substitute
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((self.root / canonical).read_bytes())
                acceptance = json.loads(json.dumps(original_acceptance))
                acceptance[path_key] = substitute
                acceptance[sha_key] = _sha(self.root, substitute)
                _write_json(self.root, acceptance_path, acceptance)

                result = self.evaluate()

                self.assertEqual(result["gate_result"], "SIM_NO_GO")
                self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")
        _write_json(self.root, acceptance_path, original_acceptance)

    def test_sim_002_git_blob_mismatches_fail_closed_after_current_rehash(self) -> None:
        acceptance_path = "results/reviews/SIM-002_acceptance.json"
        original_acceptance = _read_json(self.root, acceptance_path)
        for _, sha_key, canonical in gate.EXPECTED_SIM_002_REVIEWED_ARTIFACTS:
            with self.subTest(canonical=canonical):
                artifact = self.root / canonical
                original_bytes = artifact.read_bytes()
                artifact.write_bytes(original_bytes + b"\n")
                acceptance = json.loads(json.dumps(original_acceptance))
                acceptance[sha_key] = _sha(self.root, canonical)
                _write_json(self.root, acceptance_path, acceptance)

                result = self.evaluate()

                self.assertEqual(result["gate_result"], "SIM_NO_GO")
                self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")
                artifact.write_bytes(original_bytes)
        _write_json(self.root, acceptance_path, original_acceptance)

    def test_public_request_validator_rejects_direct_unknown_and_dynamic_operations(self) -> None:
        schema = _read_json(self.root, gate.EXECUTION_SCHEMA_PATH)
        self.assertEqual(gate._schema_operation_surface(schema), gate.EXPECTED_OPERATIONS)
        for operation in gate.EXPECTED_OPERATIONS:
            with self.subTest(allowed=operation):
                self.assertTrue(gate._request_operation_is_allowed(schema, {"operation": operation}))
        dynamically_supplied = "dynamic" + ".execute"
        for operation in ("actuator.execute", "joint.execute", "arbitrary.unknown", dynamically_supplied):
            with self.subTest(rejected=operation):
                self.assertFalse(gate._request_operation_is_allowed(schema, {"operation": operation}))
                request = accepted_runtime._navigation_request(  # noqa: SLF001
                    "a96caacf-efbc-438a-8cb6-e6977fb861c2",
                    "bbbaea65-b803-47d7-b11c-bc6517ca7259",
                )
                request = deepcopy(request)
                request["operation"] = operation
                with self.assertRaises(accepted_runtime.ContractViolation):
                    accepted_runtime.validate_contract_message(request)

    def test_runtime_operation_registry_with_sixth_operation_returns_sim_no_go(self) -> None:
        schema = _read_json(self.root, gate.EXECUTION_SCHEMA_PATH)
        schema["$defs"]["Operation"]["enum"].append("actuator.execute")
        _write_json(self.root, gate.EXECUTION_SCHEMA_PATH, schema)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "FAIL")

    def test_runtime_operation_registry_missing_frozen_operation_returns_sim_no_go(self) -> None:
        schema = _read_json(self.root, gate.EXECUTION_SCHEMA_PATH)
        schema["$defs"]["Operation"]["enum"].remove("verification.verify")
        _write_json(self.root, gate.EXECUTION_SCHEMA_PATH, schema)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "FAIL")

    def test_alternate_schema_operation_branch_returns_sim_no_go(self) -> None:
        schema = _read_json(self.root, gate.EXECUTION_SCHEMA_PATH)
        schema["$defs"]["ActuatorExecuteRequest"] = {
            "type": "object",
            "required": ["operation"],
            "properties": {"operation": {"const": "actuator.execute"}},
            "additionalProperties": False,
        }
        schema["oneOf"].append({"$ref": "#/$defs/ActuatorExecuteRequest"})
        _write_json(self.root, gate.EXECUTION_SCHEMA_PATH, schema)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "FAIL")

    def test_alternate_public_dispatcher_returns_sim_no_go(self) -> None:
        runtime_relative = "src/simulation_runtime/smoke.py"
        runtime_path = self.root / runtime_relative
        runtime_path.write_text(
            runtime_path.read_text(encoding="utf-8")
            + "\ndef dispatch_operation(operation: str) -> str:\n    return operation\n",
            encoding="utf-8",
        )
        acceptance = _read_json(self.root, "results/reviews/SIM-002_acceptance.json")
        acceptance["runtime_module_sha256"] = _sha(self.root, runtime_relative)
        _write_json(self.root, "results/reviews/SIM-002_acceptance.json", acceptance)

        result = self.evaluate()

        self.assertEqual(result["gate_result"], "SIM_NO_GO")
        self.assertEqual(result["material_predicates"]["C08"]["status"], "FAIL")
        self.assertEqual(result["material_predicates"]["C18"]["status"], "FAIL")

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
