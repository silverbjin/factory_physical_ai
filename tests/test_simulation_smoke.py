from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import simulation_runtime.smoke as smoke  # noqa: E402
from simulation_runtime import ContractViolation, canonical_sha256, run_smoke_suite, validate_contract_message  # noqa: E402


class SimulationSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = run_smoke_suite()
        self.scenarios = {scenario["scenario_id"]: scenario for scenario in self.result["scenarios"]}

    def test_all_four_mandatory_scenarios_pass(self) -> None:
        self.assertEqual(set(self.scenarios), {"S01", "S02", "S03", "S04"})
        self.assertTrue(all(scenario["status"] == "PASS" for scenario in self.scenarios.values()))

    def test_success_path_covers_frozen_boundaries_and_requires_verification_pass(self) -> None:
        success = self.scenarios["S01"]
        self.assertEqual(
            success["operations"],
            ["mission.execute", "navigation.execute", "vla.execute", "verification.verify"],
        )
        self.assertEqual(success["final_mission_status"], "completed")
        self.assertEqual(success["verification_verdict"], "pass")

    def test_failure_path_is_explicit_non_success(self) -> None:
        failure = self.scenarios["S02"]
        self.assertEqual(failure["observed_status"], "failed")
        self.assertEqual(failure["observed_result"], "failure")
        self.assertEqual(failure["error_category"], "EXECUTION_FAILED")

    def test_timeout_is_bounded_pending_unknown_without_sleep(self) -> None:
        timeout = self.scenarios["S03"]
        self.assertEqual(timeout["observed_status"], "unknown")
        self.assertEqual(timeout["observed_result"], "pending")
        self.assertEqual(timeout["error_category"], "MODEL_TIMEOUT")
        self.assertTrue(timeout["virtual_no_result_at_bound"])
        self.assertEqual(timeout["execution_bound_ms"], 1_000)
        self.assertFalse(self.result["boundedness"]["sleep_used"])

    def test_unknown_requires_authoritative_reconciliation_before_resolved_success(self) -> None:
        reconciliation = self.scenarios["S04"]
        self.assertEqual(reconciliation["state_sequence"], ["unknown", "reconciling", "reconciled"])
        self.assertEqual(reconciliation["resolved_status"], "succeeded")
        self.assertFalse(reconciliation["direct_unknown_to_succeeded"])
        self.assertTrue(reconciliation["authoritative_evidence_required"])
        with self.assertRaises(ContractViolation):
            validate_contract_message(
                {"record_type": "action_transition", "from_status": "unknown", "to_status": "succeeded"}
            )

    def test_reconciliation_rejects_mismatched_observed_resolution(self) -> None:
        action_id = "a37c1c93-e697-48a8-bc94-065842841f3c"
        status_request = smoke._common_request(  # noqa: SLF001 - reconciliation negative test
            "action_status.get", "49a449fa-226d-4b72-ad9d-108810c29f5c"
        )
        status_request["action_id"] = action_id
        status_result = smoke._common_result(  # noqa: SLF001 - reconciliation negative test
            "action_status.get", status_request["request_id"]
        )
        evidence_refs = [smoke._evidence_ref("mismatch-probe")]  # noqa: SLF001
        status_result.update(
            {
                "action_id": action_id,
                "status": "succeeded",
                "result": "success",
                "observed_at": smoke.TIMESTAMP,
                "observed_status": "succeeded",
                "evidence_refs": evidence_refs,
            }
        )
        reconciliation = {
            "record_type": "reconciliation_record",
            "schema_version": "1.0",
            "mission_id": smoke.MISSION_ID,
            "action_id": action_id,
            "status_request_id": status_request["request_id"],
            "status_result_request_id": status_result["request_id"],
            "from_status": "unknown",
            "phase": "reconciling",
            "status": "reconciled",
            "resolved_status": "failed",
            "observed_at": smoke.TIMESTAMP,
            "component_version": smoke.COMPONENT_VERSION,
            "evidence_refs": evidence_refs,
            "error": smoke._error("EXECUTION_FAILED"),  # noqa: SLF001
        }
        with self.assertRaisesRegex(ContractViolation, "resolved_status mismatch"):
            smoke._validate_reconciliation(status_request, status_result, reconciliation)  # noqa: SLF001

    def test_repeated_runs_are_byte_equivalent_after_canonicalization(self) -> None:
        first = run_smoke_suite()
        second = run_smoke_suite()
        self.assertEqual(first, second)
        self.assertEqual(canonical_sha256(first), canonical_sha256(second))

    def test_contract_validation_fails_closed_for_unknown_field_and_bad_deadline(self) -> None:
        request = smoke._navigation_request(  # noqa: SLF001 - contract-negative test
            "a96caacf-efbc-438a-8cb6-e6977fb861c2",
            "bbbaea65-b803-47d7-b11c-bc6517ca7259",
        )
        unknown = deepcopy(request)
        unknown["raw_pose"] = {"x": 1.0, "y": 2.0}
        with self.assertRaises(ContractViolation):
            validate_contract_message(unknown)
        bad_deadline = deepcopy(request)
        bad_deadline["deadline_at"] = bad_deadline["timestamp"]
        with self.assertRaisesRegex(ContractViolation, "deadline_at must be later"):
            validate_contract_message(bad_deadline)

    def test_fixture_tampering_fails_closed(self) -> None:
        manifest = smoke._manifest()  # noqa: SLF001 - fixture-integrity negative test
        request = smoke._verification_request(  # noqa: SLF001 - fixture-integrity negative test
            "112e4e10-b61c-441c-b356-1751049fd625",
            "18f70897-9cea-4792-b82a-1d1c80909bb7",
            manifest,
        )
        manifest["fixtures"][0]["observation"]["location_id"] = "tampered-location"
        with self.assertRaisesRegex(ContractViolation, "fixture content hash mismatch"):
            smoke._deterministic_verdict(request, manifest)  # noqa: SLF001

        timestamp_mismatch = smoke._manifest()  # noqa: SLF001
        timestamp_request = smoke._verification_request(  # noqa: SLF001
            "112e4e10-b61c-441c-b356-1751049fd625",
            "18f70897-9cea-4792-b82a-1d1c80909bb7",
            timestamp_mismatch,
        )
        timestamp_request["observation_refs"][0]["timestamp"] = "2026-09-13T00:00:01Z"
        with self.assertRaisesRegex(ContractViolation, "timestamp mismatch"):
            smoke._deterministic_verdict(timestamp_request, timestamp_mismatch)  # noqa: SLF001

    def test_runtime_has_no_external_or_physical_dependency(self) -> None:
        isolation = self.result["isolation"]
        self.assertTrue(all(value is False for value in isolation.values()))
        cleanup = self.result["process_cleanup"]
        self.assertEqual(cleanup["child_processes_started"], 0)
        self.assertEqual(cleanup["background_workers_started"], 0)
        self.assertEqual(cleanup["temporary_files_created"], 0)
        self.assertTrue(cleanup["cleanup_complete"])

        source_path = ROOT / "src/simulation_runtime/smoke.py"
        source = source_path.read_text(encoding="utf-8")
        imports: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse({"socket", "subprocess", "serial"} & imports)
        self.assertNotIn("/dev/tty", source)
        self.assertNotIn("/dev/video", source)

    def test_cli_completes_within_bound_and_emits_same_result(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "scripts/run_simulation_smoke.py"],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout), self.result)


if __name__ == "__main__":
    unittest.main()
