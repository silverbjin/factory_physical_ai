from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "verify_training_resource_readiness.py"
SPEC = importlib.util.spec_from_file_location("verify_training_resource_readiness", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCRIPT_PATH}")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)
ORIGINAL_PATH_READ_TEXT = Path.read_text


def _delayed_disk_usage(_path: Path) -> Any:
    time.sleep(0.5)
    return (100, 50, 50)


def _delayed_path_is_dir(_path: Path) -> bool:
    time.sleep(0.5)
    return True


def _delayed_path_is_file(_path: Path) -> bool:
    time.sleep(0.5)
    return True


def _delayed_path_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
    time.sleep(0.5)
    return ORIGINAL_PATH_READ_TEXT(path, *args, **kwargs)


class TrainingResourceReadinessTests(unittest.TestCase):
    def local_resources(self) -> dict[str, Any]:
        return {
            "host": {
                "provenance": "MEASURED",
                "platform": "synthetic-test-host",
                "machine": "x86_64",
                "logical_cpu_count": 8,
            },
            "gpu": {
                "provenance": "MEASURED",
                "available": True,
                "name": "synthetic RTX 2060 Max-Q fixture",
                "memory_total_mib": 6144,
                "memory_free_mib": 5000,
                "compute_capability": "7.5",
            },
            "torch_cuda": {
                "provenance": "MEASURED",
                "available": True,
                "python": "3.12.3",
                "torch": "2.10.0+cu130",
                "torchvision": "0.25.0+cu130",
                "cuda_runtime": "13.0",
                "cuda_available": True,
                "device_count": 1,
                "model_loaded": False,
                "training_executed": False,
                "optimizer_updates_executed": False,
                "hyperparameter_search_executed": False,
            },
            "ram": {
                "provenance": "MEASURED",
                "total_bytes": 16_000_000_000,
                "available_bytes": 8_000_000_000,
            },
            "repository_filesystem": {
                "provenance": "MEASURED",
                "path": "/synthetic",
                "total_bytes": 100_000_000_000,
                "free_bytes": 80_000_000_000,
            },
            "cache_filesystem": {
                "provenance": "MEASURED",
                "path": "/synthetic",
                "total_bytes": 100_000_000_000,
                "free_bytes": 80_000_000_000,
            },
            "environment_footprint": {
                "provenance": "MEASURED",
                "path": "/synthetic/.venv-vla",
                "bytes": 1_000_000,
            },
            "environment_path": {
                "value": "/synthetic/.venv-vla",
                "provenance": "DOCUMENTED",
            },
            "huggingface_cache_path": {
                "value": "/synthetic/.cache/huggingface",
                "provenance": "DOCUMENTED",
                "exists": False,
                "created_by_task": False,
            },
        }

    def valid_hybrid_plan(self) -> dict[str, Any]:
        plan = verifier.unresolved_plan(REPOSITORY_ROOT)
        plan["execution_mode"] = {
            "value": "HYBRID_TRAINING",
            "provenance": "DECLARED_INPUT",
            "source_reference": "fixture://execution-mode",
            "local_role": "LOCAL_DEVELOPMENT_CONFIGURATION_VALIDATION_ONLY",
            "training_role": "REMOTE_PRIMARY_RESOURCE_TRAINS",
        }
        plan["primary_resource"] = {
            "identified": True,
            "resource_id": "remote-gpu-fixture-01",
            "provider_or_owner": "synthetic-test-provider",
            "compute_kind": verifier.CUDA_GPU_RESOURCE,
            "availability": "AVAILABLE",
            "availability_provenance": "DECLARED_INPUT",
            "availability_source_reference": "fixture://resource-availability",
            "resource_class": "synthetic remote GPU fixture",
            "vram_bytes": 24 * 1024 * 1024 * 1024,
            "vram_provenance": "DOCUMENTED",
            "vram_source_reference": "fixture://resource-class",
            "required_vram_bytes": 16 * 1024 * 1024 * 1024,
            "required_vram_provenance": "DOCUMENTED",
            "required_vram_source_reference": "fixture://workload-vram-requirement",
            "workload_config_reference": "fixture://training-configuration",
            "provenance": "DECLARED_INPUT",
            "source_reference": "fixture://resource-identity",
            "compatibility": "COMPATIBLE",
            "compatibility_provenance": "DOCUMENTED",
            "compatibility_source_reference": "fixture://runtime-compatibility",
            "detail": "synthetic test fixture only",
        }
        plan["storage"].update(
            {
                "readiness": "STORAGE_READY",
                "provenance": "DECLARED_INPUT",
                "source_reference": "fixture://storage-plan",
                "dataset_size_bytes": 1_000_000,
                "dataset_size_provenance": "DECLARED_INPUT",
                "dataset_size_source_reference": "fixture://dataset-size",
                "checkpoint_size_bytes": 2_000_000,
                "checkpoint_size_provenance": "DECLARED_INPUT",
                "checkpoint_size_source_reference": "fixture://checkpoint-size",
                "model_cache_size_bytes": 1_000_000,
                "model_cache_size_provenance": "DOCUMENTED",
                "model_cache_size_source_reference": "fixture://model-cache-size",
                "temporary_space_bytes": 6_000_000,
                "temporary_space_provenance": "DECLARED_INPUT",
                "temporary_space_source_reference": "fixture://temporary-space",
                "required_capacity_bytes": 10_000_000,
                "required_capacity_provenance": "DERIVED",
                "required_capacity_source_reference": "fixture://capacity-calculation",
                "capacity_formula": verifier.STORAGE_FORMULA,
                "available_capacity_bytes": 80_000_000_000,
                "available_capacity_provenance": "MEASURED",
                "available_capacity_source_reference": "fixture://disk-measurement",
                "artifact_movement_strategy": "copy by checksum-verified artifact transfer",
                "checkpoint_retention_strategy": "retain approved best and final checkpoints",
                "temporary_space_strategy": "use bounded scratch storage and clean after verification",
            }
        )
        plan["budget"] = {
            "policy": "APPROVED_NUMERIC_BUDGET_CEILING",
            "provenance": "DECLARED_INPUT",
            "source_reference": "fixture://budget-approval",
            "applies_to_resource_id": "remote-gpu-fixture-01",
            "feasibility": "WITHIN_POLICY",
            "currency": "TEST",
            "resource_unit": "GPU-hour",
            "estimation_date": "2026-09-04",
            "approved_ceiling": 10.0,
            "approved_ceiling_provenance": "DECLARED_INPUT",
            "approved_ceiling_source_reference": "fixture://budget-ceiling",
            "unit_price": 2.0,
            "unit_price_provenance": "DOCUMENTED",
            "unit_price_source_reference": "fixture://unit-price",
            "estimated_training_hours": 4.0,
            "estimated_training_hours_provenance": "DECLARED_INPUT",
            "estimated_training_hours_source_reference": "fixture://hours",
            "estimated_compute_cost": 8.0,
            "estimated_compute_cost_provenance": "DERIVED",
            "estimated_compute_cost_source_reference": "fixture://cost-formula",
            "cost_inputs": [
                {
                    "name": "unit_price",
                    "value": 2.0,
                    "provenance": "DOCUMENTED",
                    "source_reference": "fixture://unit-price",
                },
                {
                    "name": "estimated_training_hours",
                    "value": 4.0,
                    "provenance": "DECLARED_INPUT",
                    "source_reference": "fixture://hours",
                },
                {
                    "name": "estimated_compute_cost",
                    "value": 8.0,
                    "provenance": "DERIVED",
                    "source_reference": "fixture://cost-formula",
                },
            ],
            "cost_formula": verifier.COST_FORMULA,
            "calculation_performed": True,
            "detail": "synthetic test fixture only",
        }
        plan["fallback"] = {
            "required": True,
            "defined": True,
            "availability": "AVAILABLE",
            "strategy_id": "fallback-remote-gpu",
            "resource_id": "remote-gpu-fixture-02",
            "provider_or_owner": "synthetic-test-provider",
            "compute_kind": verifier.CUDA_GPU_RESOURCE,
            "resource_class": "synthetic alternate GPU fixture",
            "resource": "synthetic fallback GPU fixture",
            "vram_bytes": 24 * 1024 * 1024 * 1024,
            "vram_provenance": "DOCUMENTED",
            "vram_source_reference": "fixture://fallback-vram",
            "required_vram_bytes": 16 * 1024 * 1024 * 1024,
            "required_vram_provenance": "DOCUMENTED",
            "required_vram_source_reference": "fixture://workload-vram-requirement",
            "workload_config_reference": "fixture://training-configuration",
            "provenance": "DECLARED_INPUT",
            "source_reference": "fixture://fallback-identity",
            "availability_provenance": "DECLARED_INPUT",
            "availability_source_reference": "fixture://fallback-availability",
            "compatibility": "COMPATIBLE",
            "compatibility_provenance": "DOCUMENTED",
            "compatibility_source_reference": "fixture://fallback-runtime",
            "not_required_rule": None,
            "not_required_source_reference": None,
            "storage_strategy_reference": "fixture://fallback-artifact-movement",
            "storage_strategy_provenance": "DOCUMENTED",
            "storage_strategy_source_reference": "fixture://fallback-storage-plan",
            "stop_condition": "stop if fallback is unavailable or outside policy",
            "detail": "synthetic test fixture only",
        }
        plan["fallback"]["budget"] = deepcopy(plan["budget"])
        plan["fallback"]["budget"].update(
            {
                "source_reference": "fixture://fallback-budget-approval",
                "applies_to_resource_id": "remote-gpu-fixture-02",
            }
        )
        return plan

    def evidence(self, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        return verifier.build_evidence(
            REPOSITORY_ROOT,
            self.local_resources(),
            plan or self.valid_hybrid_plan(),
            generated_at="2026-09-04T00:00:00Z",
        )

    @staticmethod
    def rebind(evidence: dict[str, Any]) -> None:
        evidence["content_binding"]["evidence_payload_sha256"] = (
            verifier._evidence_payload_sha256(evidence)
        )

    @staticmethod
    def refresh(evidence: dict[str, Any]) -> None:
        evidence["checks"] = verifier._checks_from_material(evidence)
        evidence["training_resource_decision"] = verifier.decide_readiness(evidence["checks"])
        evidence["unresolved_blockers"] = verifier._blockers(evidence["checks"])
        TrainingResourceReadinessTests.rebind(evidence)

    def test_valid_hybrid_resource_evidence_is_ready(self) -> None:
        evidence = self.evidence()

        self.assertEqual(evidence["training_resource_decision"], verifier.READY)
        self.assertEqual(verifier.validate_evidence(evidence), [])
        self.assertTrue(all(item["mandatory"] for item in evidence["checks"]))
        self.assertTrue(all(item["status"] == "PASS" for item in evidence["checks"]))
        self.assertTrue(
            all(item["provenance"] != "NOT_VERIFIED" for item in evidence["checks"])
        )
        self.assertEqual(
            evidence["resource_plan"]["local_training"]["classification"],
            "TRAINING_NOT_VERIFIED",
        )

    def test_canonical_unresolved_plan_is_blocked_but_structurally_valid(self) -> None:
        evidence = self.evidence(verifier.unresolved_plan(REPOSITORY_ROOT))

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(verifier.validate_evidence(evidence), [])
        blocker_ids = {item["check_id"] for item in evidence["unresolved_blockers"]}
        self.assertTrue(
            {"C08", "C09", "C10", "C11", "C12", "C14", "C15"}
            <= blocker_ids
        )

    def test_missing_execution_mode_fails_closed(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["execution_mode"].pop("value")
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("invalid training execution mode" in error for error in errors))

    def test_unsupported_local_training_claim_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["local_training"]["classification"] = "TRAINING_VERIFIED"
        evidence["resource_plan"]["local_training"]["model_specific_evidence"] = {
            "available": False,
            "authorized_by_task": False,
            "provenance": "NOT_VERIFIED",
            "detail": "CUDA/import/free VRAM only",
        }
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("unsupported local-training claim" in error for error in errors))
        self.assertEqual(evidence["checks"][16]["status"], "BLOCKED")

    def test_missing_required_resource_blocks_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["primary_resource"]["identified"] = False
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(verifier.validate_evidence(evidence), [])
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")

    def test_missing_budget_policy_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["budget"].pop("policy")
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("missing or invalid budget policy" in error for error in errors))
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)

    def test_malformed_numeric_budget_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["budget"]["approved_ceiling"] = "ten"
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("malformed numeric budget" in error for error in errors))

    def test_cost_outside_policy_blocks_ready(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget["unit_price"] = 2.5025
        budget["cost_inputs"][0]["value"] = 2.5025
        budget["estimated_compute_cost"] = 10.01
        budget["cost_inputs"][2]["value"] = 10.01
        budget["feasibility"] = "OUTSIDE_POLICY"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(verifier.validate_evidence(evidence), [])
        self.assertEqual(evidence["checks"][13]["status"], "BLOCKED")

    def test_exactly_at_budget_ceiling_is_within_policy(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget["unit_price"] = 2.5
        budget["cost_inputs"][0]["value"] = 2.5
        budget["estimated_compute_cost"] = budget["approved_ceiling"]
        budget["cost_inputs"][2]["value"] = budget["approved_ceiling"]
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.READY)
        self.assertEqual(verifier.validate_evidence(evidence), [])

    def test_zero_incremental_local_budget_cannot_bypass_unverified_local_fit(self) -> None:
        plan = self.valid_hybrid_plan()
        plan["local_training"] = {
            "classification": "TRAINING_VERIFIED",
            "provenance": "DOCUMENTED",
            "model_specific_evidence": {
                "available": True,
                "authorized_by_task": True,
                "provenance": "DOCUMENTED",
                "detail": "synthetic authorized model-specific fixture",
            },
            "role": "synthetic local training fixture",
        }
        plan["execution_mode"] = {"value": "LOCAL_TRAINING", "provenance": "DOCUMENTED"}
        plan["primary_resource"]["resource_class"] = "synthetic verified local fixture"
        plan["budget"] = {
            "policy": "LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET",
            "provenance": "DOCUMENTED",
            "source_reference": "fixture://local-zero-policy",
            "applies_to_resource_id": "remote-gpu-fixture-01",
            "feasibility": "WITHIN_POLICY",
            "currency": None,
            "approved_ceiling": 0,
            "unit_price": 0,
            "estimated_training_hours": None,
            "estimated_compute_cost": 0,
            "cost_inputs": [],
            "calculation_performed": False,
            "detail": "synthetic zero-incremental-cost fixture",
        }
        evidence = self.evidence(plan)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("unsupported local-training claim" in error for error in errors))
        self.assertEqual(evidence["checks"][16]["status"], "BLOCKED")

    def test_local_mode_with_unverified_or_unsuitable_classification_cannot_be_ready(self) -> None:
        for classification in ("TRAINING_NOT_VERIFIED", "TRAINING_UNSUITABLE"):
            with self.subTest(classification=classification):
                plan = self.valid_hybrid_plan()
                plan["local_training"]["classification"] = classification
                plan["execution_mode"] = {
                    "value": "LOCAL_TRAINING",
                    "provenance": "DOCUMENTED",
                    "source_reference": "fixture://local-mode",
                    "local_role": "LOCAL_PRIMARY_RESOURCE_TRAINS",
                    "training_role": "LOCAL_PRIMARY_RESOURCE_TRAINS",
                }
                evidence = self.evidence(plan)

                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )
                self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")

    def test_local_ready_requires_complete_model_specific_fixture(self) -> None:
        plan = self.valid_hybrid_plan()
        plan["local_training"] = {
            "classification": "TRAINING_VERIFIED",
            "provenance": "DOCUMENTED",
            "source_reference": "fixture://authorized-local-fit-evidence",
            "model_specific_evidence": {
                "available": True,
                "authorized_by_task": True,
                "provenance": "DOCUMENTED",
                "source_reference": "fixture://bounded-model-memory-evidence",
                "configuration_reference": "fixture://training-configuration",
                "peak_vram_bytes": 4 * 1024 * 1024 * 1024,
                "detail": "synthetic authorized model-specific fixture only",
            },
            "role": "synthetic local training fixture",
        }
        plan["execution_mode"] = {
            "value": "LOCAL_TRAINING",
            "provenance": "DOCUMENTED",
            "source_reference": "fixture://local-mode",
            "local_role": "LOCAL_PRIMARY_RESOURCE_TRAINS",
            "training_role": "LOCAL_PRIMARY_RESOURCE_TRAINS",
        }
        plan["primary_resource"].update(
            {
                "resource_id": "LOCAL_ACCEPTED_P0_005_GPU",
                "provider_or_owner": "local-test-owner",
                "compute_kind": verifier.CUDA_GPU_RESOURCE,
                "resource_class": "synthetic local GPU fixture",
                "vram_bytes": 6 * 1024 * 1024 * 1024,
                "source_reference": "fixture://local-resource",
                "availability_source_reference": "fixture://local-availability",
                "vram_source_reference": "fixture://local-vram",
                "required_vram_bytes": 4 * 1024 * 1024 * 1024,
                "required_vram_provenance": "DOCUMENTED",
                "required_vram_source_reference": "fixture://bounded-model-memory-evidence",
                "workload_config_reference": "fixture://training-configuration",
                "compatibility_source_reference": "fixture://local-runtime",
            }
        )
        plan["budget"].update(
            {
                "policy": "LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET",
                "provenance": "DOCUMENTED",
                "source_reference": "fixture://local-zero-policy",
                "applies_to_resource_id": "LOCAL_ACCEPTED_P0_005_GPU",
                "feasibility": "WITHIN_POLICY",
                "estimated_compute_cost": 0,
                "calculation_performed": False,
            }
        )
        evidence = self.evidence(plan)

        self.assertEqual(evidence["training_resource_decision"], verifier.READY)
        self.assertEqual(verifier.validate_evidence(evidence), [])

    def test_missing_fallback_blocks_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["fallback"]["defined"] = False
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][14]["status"], "BLOCKED")

    def test_unknown_compatibility_blocks_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["primary_resource"]["compatibility"] = "NOT_VERIFIED"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][9]["status"], "BLOCKED")

    def test_invalid_provenance_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["primary_resource"]["provenance"] = "ASSUMED"
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("invalid provenance" in error for error in errors))

    def test_mandatory_check_demotion_cannot_create_ready(self) -> None:
        evidence = self.evidence()
        evidence["checks"][0]["mandatory"] = False
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(verifier.decide_readiness(evidence["checks"]), verifier.BLOCKED)
        self.assertTrue(any("C01 must remain mandatory" in error for error in errors))
        self.assertTrue(any("checks do not match material facts" in error for error in errors))

    def test_blocker_list_mismatch_is_rejected(self) -> None:
        evidence = self.evidence(verifier.unresolved_plan(REPOSITORY_ROOT))
        evidence["unresolved_blockers"] = []
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("unresolved_blockers must exactly match" in error for error in errors))

    def test_manipulated_ready_artifact_is_rejected(self) -> None:
        evidence = self.evidence(verifier.unresolved_plan(REPOSITORY_ROOT))
        evidence["training_resource_decision"] = verifier.READY
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("aggregate decision" in error for error in errors))
        self.assertTrue(any("TRAINING_RESOURCE_READY requires" in error for error in errors))

    def test_zero_or_invalid_storage_blocks_characterization(self) -> None:
        evidence = self.evidence()
        evidence["local_resources"]["repository_filesystem"]["free_bytes"] = 0
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][5]["status"], "BLOCKED")

    def test_missing_numeric_cost_estimate_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["budget"]["estimated_compute_cost"] = None
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("malformed numeric budget" in error for error in errors))

    def test_unavailable_remote_resource_blocks_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["primary_resource"]["availability"] = "NOT_VERIFIED"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")

    def test_rehashed_coordinated_material_manipulation_cannot_create_ready(self) -> None:
        evidence = self.evidence(verifier.unresolved_plan(REPOSITORY_ROOT))
        plan = evidence["resource_plan"]
        plan["execution_mode"] = {
            "value": "HYBRID_TRAINING",
            "provenance": "NOT_VERIFIED",
            "source_reference": None,
        }
        plan["primary_resource"].update(
            {
                "identified": True,
                "availability": "AVAILABLE",
                "resource_id": None,
                "resource_class": None,
                "provenance": "NOT_VERIFIED",
                "compatibility": "COMPATIBLE",
            }
        )
        plan["storage"]["readiness"] = "STORAGE_NOT_VERIFIED"
        plan["budget"].update(
            {
                "policy": "EXISTING_PREPAID_RESOURCE",
                "provenance": "NOT_VERIFIED",
                "source_reference": None,
                "feasibility": "WITHIN_POLICY",
            }
        )
        plan["fallback"].update(
            {
                "defined": True,
                "availability": "AVAILABLE",
                "resource": None,
                "provenance": "NOT_VERIFIED",
            }
        )
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(evidence["unresolved_blockers"])
        self.assertTrue(verifier.validate_evidence(evidence))

        for check in evidence["checks"]:
            check["mandatory"] = True
            check["status"] = "PASS"
        evidence["unresolved_blockers"] = []
        evidence["training_resource_decision"] = verifier.READY
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("checks do not match material facts" in error for error in errors))
        self.assertTrue(any("aggregate decision" in error for error in errors))

    def test_placeholder_like_primary_identity_blocks_rehashed_ready(self) -> None:
        evidence = self.evidence()
        primary = evidence["resource_plan"]["primary_resource"]
        primary["resource_id"] = "unknown resource"
        primary["resource_class"] = "unresolved resource"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")
        self.assertTrue(verifier.validate_evidence(evidence))

    def test_hybrid_mode_requires_explicit_role_split(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["execution_mode"]["training_role"] = None
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][7]["status"], "BLOCKED")

    def test_prepaid_budget_must_apply_to_primary_resource(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget.update(
            {
                "policy": "EXISTING_PREPAID_RESOURCE",
                "provenance": "DOCUMENTED",
                "source_reference": "fixture://prepaid-policy",
                "applies_to_resource_id": "different-resource",
                "feasibility": "WITHIN_POLICY",
                "prepaid_resource_id": "different-resource",
                "prepaid_resource_reference": "fixture://different-resource",
                "prepaid_resource_provenance": "DOCUMENTED",
                "remaining_quota": 10,
                "quota_unit": "GPU-hours",
                "quota_provenance": "DOCUMENTED",
                "quota_source_reference": "fixture://different-quota",
                "calculation_performed": False,
            }
        )
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("selected primary resource" in error for error in errors))

    def test_fallback_not_required_assertion_without_proof_blocks_ready(self) -> None:
        evidence = self.evidence()
        fallback = evidence["resource_plan"]["fallback"]
        fallback.update(
            {
                "required": False,
                "defined": False,
                "availability": "NOT_VERIFIED",
                "resource": None,
                "resource_id": None,
                "provider_or_owner": None,
                "resource_class": None,
                "provenance": "DOCUMENTED",
                "source_reference": None,
                "availability_provenance": "NOT_VERIFIED",
                "availability_source_reference": None,
                "compatibility": "NOT_VERIFIED",
                "compatibility_provenance": "NOT_VERIFIED",
                "compatibility_source_reference": None,
                "not_required_rule": verifier.FALLBACK_NOT_REQUIRED_RULE,
                "not_required_source_reference": "fixture://assertion-only",
            }
        )
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][14]["status"], "BLOCKED")

    def test_fallback_must_be_distinct_from_primary_resource(self) -> None:
        evidence = self.evidence()
        fallback = evidence["resource_plan"]["fallback"]
        fallback["resource_id"] = evidence["resource_plan"]["primary_resource"][
            "resource_id"
        ]
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][14]["status"], "BLOCKED")

    def test_measured_planning_estimates_cannot_be_upgraded_to_ready(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget["estimated_training_hours_provenance"] = "MEASURED"
        budget["cost_inputs"][1]["provenance"] = "MEASURED"
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(
            any("estimated_training_hours lacks" in error for error in errors)
        )

    def test_additional_placeholder_spellings_block_material_identity(self) -> None:
        for placeholder in ("N/A", "not applicable", "TBC resource"):
            with self.subTest(placeholder=placeholder):
                evidence = self.evidence()
                evidence["resource_plan"]["primary_resource"]["resource_id"] = (
                    placeholder
                )
                self.refresh(evidence)

                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )

    def test_contradictory_training_activity_fields_block_rehashed_ready(self) -> None:
        cases = (
            ("generation", "training_executed"),
            ("torch_cuda", "training_executed"),
            ("torch_cuda", "optimizer_updates_executed"),
        )
        for section, field in cases:
            with self.subTest(section=section, field=field):
                evidence = self.evidence()
                target = (
                    evidence["generation"]
                    if section == "generation"
                    else evidence["local_resources"][section]
                )
                target[field] = True
                self.refresh(evidence)

                errors = verifier.validate_evidence(evidence)
                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )
                self.assertEqual(evidence["checks"][17]["status"], "BLOCKED")
                self.assertTrue(any("training activity fields" in error for error in errors))

    def test_zero_planned_artifact_sizes_block_storage_ready(self) -> None:
        evidence = self.evidence()
        storage = evidence["resource_plan"]["storage"]
        storage["dataset_size_bytes"] = 0
        storage["checkpoint_size_bytes"] = 0
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][10]["status"], "BLOCKED")
        self.assertEqual(
            verifier.validate_evidence(
                evidence,
                repository_root=REPOSITORY_ROOT,
                verify_bound_files=True,
            ),
            [],
        )

    def test_storage_required_capacity_is_recomputed_from_components(self) -> None:
        evidence = self.evidence()
        storage = evidence["resource_plan"]["storage"]
        storage["dataset_size_bytes"] = 70_000_000_000
        storage["checkpoint_size_bytes"] = 70_000_000_000
        storage["required_capacity_bytes"] = 10_000_000
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][10]["status"], "BLOCKED")
        self.assertEqual(
            verifier.validate_evidence(
                evidence,
                repository_root=REPOSITORY_ROOT,
                verify_bound_files=True,
            ),
            [],
        )

    def test_primary_vram_must_cover_evidenced_workload_requirement(self) -> None:
        evidence = self.evidence()
        primary = evidence["resource_plan"]["primary_resource"]
        primary["vram_bytes"] = 1
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")
        self.assertEqual(
            verifier.validate_evidence(
                evidence,
                repository_root=REPOSITORY_ROOT,
                verify_bound_files=True,
            ),
            [],
        )

    def test_fallback_requires_compute_storage_and_budget_material(self) -> None:
        mutations = (
            lambda fallback: fallback.update(vram_bytes=1),
            lambda fallback: fallback.update(storage_strategy_reference=None),
            lambda fallback: fallback.pop("budget"),
            lambda fallback: fallback["budget"].update(
                estimated_compute_cost=1
            ),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                evidence = self.evidence()
                mutate(evidence["resource_plan"]["fallback"])
                self.refresh(evidence)

                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )
                self.assertEqual(evidence["checks"][14]["status"], "BLOCKED")
                self.assertEqual(
                    verifier.validate_evidence(
                        evidence,
                        repository_root=REPOSITORY_ROOT,
                        verify_bound_files=True,
                    ),
                    [],
                )

    def test_prepaid_quota_must_cover_evidenced_required_usage(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget.update(
            {
                "policy": "EXISTING_PREPAID_RESOURCE",
                "provenance": "DOCUMENTED",
                "source_reference": "fixture://prepaid-policy",
                "applies_to_resource_id": "remote-gpu-fixture-01",
                "feasibility": "WITHIN_POLICY",
                "prepaid_resource_id": "remote-gpu-fixture-01",
                "prepaid_resource_reference": "fixture://prepaid-resource",
                "prepaid_resource_provenance": "DOCUMENTED",
                "remaining_quota": 1e-300,
                "quota_unit": "GPU-hours",
                "quota_provenance": "DOCUMENTED",
                "quota_source_reference": "fixture://remaining-quota",
                "required_quota": 4.0,
                "required_quota_unit": "GPU-hours",
                "required_quota_provenance": "DECLARED_INPUT",
                "required_quota_source_reference": "fixture://required-hours",
                "approved_ceiling": None,
                "unit_price": None,
                "estimated_training_hours": None,
                "estimated_compute_cost": None,
                "cost_inputs": [],
                "cost_formula": None,
                "calculation_performed": False,
            }
        )
        self.refresh(evidence)

        errors = verifier.validate_evidence(
            evidence,
            repository_root=REPOSITORY_ROOT,
            verify_bound_files=True,
        )
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("below evidenced required usage" in error for error in errors))

        budget["remaining_quota"] = 4.0
        self.refresh(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.READY)
        self.assertEqual(
            verifier.validate_evidence(
                evidence,
                repository_root=REPOSITORY_ROOT,
                verify_bound_files=True,
            ),
            [],
        )

    def test_missing_runtime_no_training_fields_fail_closed(self) -> None:
        for field in (
            "training_executed",
            "optimizer_updates_executed",
            "hyperparameter_search_executed",
        ):
            with self.subTest(field=field):
                evidence = self.evidence()
                evidence["local_resources"]["torch_cuda"].pop(field)
                self.refresh(evidence)

                errors = verifier.validate_evidence(
                    evidence,
                    repository_root=REPOSITORY_ROOT,
                    verify_bound_files=True,
                )
                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )
                self.assertEqual(evidence["checks"][17]["status"], "BLOCKED")
                self.assertTrue(any("training activity fields" in error for error in errors))

    def test_hybrid_not_verified_primary_evidence_blocks_ready(self) -> None:
        evidence = self.evidence()
        primary = evidence["resource_plan"]["primary_resource"]
        primary["provenance"] = "NOT_VERIFIED"
        primary["source_reference"] = None
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")

    def test_available_primary_without_identity_or_class_blocks_ready(self) -> None:
        evidence = self.evidence()
        primary = evidence["resource_plan"]["primary_resource"]
        primary["resource_id"] = None
        primary["resource_class"] = "placeholder"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][8]["status"], "BLOCKED")

    def test_storage_not_verified_cannot_support_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["storage"]["readiness"] = "STORAGE_NOT_VERIFIED"
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][10]["status"], "BLOCKED")

    def test_prepaid_policy_without_concrete_evidence_is_rejected(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget.update(
            {
                "policy": "EXISTING_PREPAID_RESOURCE",
                "source_reference": "fixture://prepaid-policy",
                "feasibility": "WITHIN_POLICY",
                "prepaid_resource_id": None,
                "prepaid_resource_reference": None,
                "prepaid_resource_provenance": "NOT_VERIFIED",
                "remaining_quota": None,
                "quota_unit": None,
                "quota_provenance": "NOT_VERIFIED",
                "quota_source_reference": None,
                "calculation_performed": False,
            }
        )
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("prepaid budget lacks concrete" in error for error in errors))

    def test_fallback_available_with_null_resource_blocks_ready(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["fallback"]["resource"] = None
        evidence["resource_plan"]["fallback"]["resource_id"] = None
        self.refresh(evidence)

        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][14]["status"], "BLOCKED")

    def test_inconsistent_cost_arithmetic_is_rejected_after_rehash(self) -> None:
        evidence = self.evidence()
        budget = evidence["resource_plan"]["budget"]
        budget["approved_ceiling"] = 20_000
        budget["cost_inputs"][0]["value"] = 100
        budget["unit_price"] = 100
        budget["cost_inputs"][1]["value"] = 100
        budget["estimated_training_hours"] = 100
        budget["cost_inputs"][2]["value"] = 1
        budget["estimated_compute_cost"] = 1
        self.refresh(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertTrue(any("inconsistent cost arithmetic" in error for error in errors))

    def test_non_finite_negative_and_missing_cost_values_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), -1, None):
            with self.subTest(value=value):
                evidence = self.evidence()
                budget = evidence["resource_plan"]["budget"]
                budget["unit_price"] = value
                budget["cost_inputs"][0]["value"] = value
                self.refresh(evidence)

                errors = verifier.validate_evidence(evidence)
                self.assertEqual(
                    evidence["training_resource_decision"], verifier.BLOCKED
                )
                self.assertTrue(any("malformed numeric budget" in error for error in errors))

    def test_material_failure_with_rewritten_checks_and_empty_blockers_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["resource_plan"]["primary_resource"]["resource_id"] = None
        evidence["checks"] = [
            {
                "id": check_id,
                "area": area,
                "mandatory": True,
                "status": "PASS",
                "provenance": "DOCUMENTED",
                "detail": "tampered",
            }
            for check_id, area in verifier.EXPECTED_CHECKS
        ]
        evidence["unresolved_blockers"] = []
        evidence["training_resource_decision"] = verifier.READY
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("checks do not match material facts" in error for error in errors))
        self.assertTrue(any("aggregate decision" in error for error in errors))

    def test_check_identity_order_and_uniqueness_are_enforced(self) -> None:
        evidence = self.evidence()
        evidence["checks"][1] = deepcopy(evidence["checks"][0])
        self.rebind(evidence)

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("check identity/order mismatch" in error for error in errors))
        self.assertTrue(any("check identities must be unique" in error for error in errors))

    def test_payload_tampering_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["local_resources"]["gpu"]["memory_total_mib"] = 99_999

        errors = verifier.validate_evidence(evidence)
        self.assertTrue(any("evidence payload hash mismatch" in error for error in errors))

    def test_predecessor_and_source_hashes_verify(self) -> None:
        evidence = self.evidence()

        self.assertEqual(
            verifier.validate_evidence(
                evidence,
                repository_root=REPOSITORY_ROOT,
                verify_bound_files=True,
            ),
            [],
        )

    def test_rehashed_predecessor_fact_mismatch_is_rejected(self) -> None:
        evidence = self.evidence()
        predecessor = evidence["predecessors"]["p0_005"]
        predecessor["expected_sha256"] = "0" * 64
        predecessor["actual_sha256"] = "0" * 64
        predecessor["hash_match"] = True
        self.refresh(evidence)

        errors = verifier.validate_evidence(
            evidence,
            repository_root=REPOSITORY_ROOT,
            verify_bound_files=True,
        )
        self.assertTrue(any("p0_005 predecessor facts" in error for error in errors))

    def test_decision_requires_exact_complete_mandatory_check_set(self) -> None:
        checks = [
            {
                "id": check_id,
                "area": area,
                "mandatory": True,
                "status": "PASS",
            }
            for check_id, area in verifier.EXPECTED_CHECKS
        ]
        self.assertEqual(verifier.decide_readiness(checks), verifier.READY)
        self.assertEqual(verifier.decide_readiness(checks[:-1]), verifier.BLOCKED)
        checks[0]["mandatory"] = False
        self.assertEqual(verifier.decide_readiness(checks), verifier.BLOCKED)

    def test_delayed_disk_usage_terminates_and_fails_closed(self) -> None:
        children_before = {child.pid for child in multiprocessing.active_children()}
        started = time.monotonic()
        with mock.patch.object(verifier.shutil, "disk_usage", _delayed_disk_usage):
            result = verifier._filesystem(REPOSITORY_ROOT, timeout_seconds=0.03)
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.75)
        self.assertEqual(result["provenance"], "NOT_VERIFIED")
        self.assertTrue(result["timed_out"])
        local = self.local_resources()
        local["repository_filesystem"] = result
        evidence = verifier.build_evidence(
            REPOSITORY_ROOT,
            local,
            self.valid_hybrid_plan(),
            generated_at="2026-09-04T00:00:00Z",
        )
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][5]["status"], "BLOCKED")
        self.assertEqual(
            {child.pid for child in multiprocessing.active_children()}, children_before
        )

    def test_delayed_is_dir_terminates_environment_probe(self) -> None:
        started = time.monotonic()
        with mock.patch.object(Path, "is_dir", _delayed_path_is_dir):
            result = verifier._environment_footprint(
                REPOSITORY_ROOT, metadata_timeout_seconds=0.03
            )
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.75)
        self.assertEqual(result["provenance"], "NOT_VERIFIED")
        self.assertTrue(result["timed_out"])

    def test_delayed_is_file_terminates_interpreter_probe(self) -> None:
        started = time.monotonic()
        with mock.patch.object(Path, "is_file", _delayed_path_is_file):
            result = verifier._torch_probe(
                REPOSITORY_ROOT, metadata_timeout_seconds=0.03
            )
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.75)
        self.assertEqual(result["provenance"], "NOT_VERIFIED")
        self.assertTrue(result["timed_out"])

    def test_delayed_meminfo_read_terminates_and_blocks_ram_check(self) -> None:
        children_before = {child.pid for child in multiprocessing.active_children()}
        started = time.monotonic()
        with mock.patch.object(Path, "read_text", _delayed_path_read_text):
            result = verifier._memory(timeout_seconds=0.03)
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.75)
        self.assertEqual(result["provenance"], "NOT_VERIFIED")
        self.assertTrue(result["timed_out"])
        local = self.local_resources()
        local["ram"] = result
        evidence = verifier.build_evidence(
            REPOSITORY_ROOT,
            local,
            self.valid_hybrid_plan(),
            generated_at="2026-09-04T00:00:00Z",
        )
        self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
        self.assertEqual(evidence["checks"][4]["status"], "BLOCKED")
        self.assertEqual(
            {child.pid for child in multiprocessing.active_children()}, children_before
        )

    def test_blocking_json_and_hash_reads_terminate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fifo = Path(temporary_directory) / "blocked-input"
            os.mkfifo(fifo)

            started = time.monotonic()
            self.assertEqual(verifier._json(fifo, timeout_seconds=0.03), {})
            json_elapsed = time.monotonic() - started

            started = time.monotonic()
            self.assertIsNone(verifier._sha256(fifo, timeout_seconds=0.03))
            hash_elapsed = time.monotonic() - started

        self.assertLess(json_elapsed, 0.75)
        self.assertLess(hash_elapsed, 0.75)

    def test_delayed_executable_discovery_terminates_conservatively(self) -> None:
        started = time.monotonic()
        with mock.patch.object(verifier.shutil, "which", lambda _name: time.sleep(0.5)):
            result = verifier._nvidia(metadata_timeout_seconds=0.03)
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.75)
        self.assertEqual(result["provenance"], "NOT_VERIFIED")
        self.assertTrue(result["timed_out"])


class TrainingResourceReadinessCliTests(unittest.TestCase):
    def test_cli_writes_atomic_blocked_evidence_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "evidence.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
                cwd=REPOSITORY_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )

            self.assertEqual(completed.returncode, 2, completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["training_resource_decision"], verifier.BLOCKED)
            self.assertEqual(
                evidence["resource_plan"]["local_training"]["classification"],
                "TRAINING_NOT_VERIFIED",
            )
            self.assertFalse(evidence["scope_safety"]["training_executed"])
            self.assertFalse(evidence["task_w1_001_authorized"])
            self.assertTrue(evidence["p0_004r_required"])
            self.assertFalse(list(output.parent.glob(f".{output.name}.*.tmp")))


if __name__ == "__main__":
    unittest.main()
