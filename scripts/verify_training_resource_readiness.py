#!/usr/bin/env python3
"""Verify TASK-P0-007 training-resource readiness without training or procurement.

The canonical run measures host resources and reads the accepted predecessor
artifacts.  It never loads model weights, creates an optimizer, processes a
training dataset, contacts a cloud provider, or provisions compute.  Resource
planning inputs that are not evidenced fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import platform
import queue as queue_module
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


TASK_ID = "TASK-P0-007"
SCHEMA_VERSION = "1.0"
VERIFIER_VERSION = "1.3.0"
READY = "TRAINING_RESOURCE_READY"
BLOCKED = "TRAINING_RESOURCE_BLOCKED"

EXPECTED_P0_005_SHA256 = (
    "aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae"
)
EXPECTED_P0_006_SHA256 = (
    "486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506"
)
EXPECTED_RUNTIME = {
    "python": "3.12.3",
    "lerobot": "0.4.4",
    "torch": "2.10.0+cu130",
    "torchvision": "0.25.0+cu130",
}
PROVENANCE = {
    "MEASURED",
    "DECLARED_INPUT",
    "DERIVED",
    "DOCUMENTED",
    "NOT_VERIFIED",
}
CHECK_STATUSES = {"PASS", "BLOCKED", "NOT_VERIFIED"}
LOCAL_TRAINING_CLASSIFICATIONS = {
    "TRAINING_VERIFIED",
    "TRAINING_NOT_VERIFIED",
    "TRAINING_UNSUITABLE",
}
EXECUTION_MODES = {
    "LOCAL_TRAINING",
    "REMOTE_TRAINING",
    "HYBRID_TRAINING",
    "UNRESOLVED",
}
BUDGET_POLICIES = {
    "LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET",
    "APPROVED_NUMERIC_BUDGET_CEILING",
    "EXISTING_PREPAID_RESOURCE",
    "UNRESOLVED",
}
BUDGET_FEASIBILITY = {"WITHIN_POLICY", "OUTSIDE_POLICY", "NOT_VERIFIED"}
EXPECTED_CHECKS = (
    ("C01", "Accepted VLA runtime preserved"),
    ("C02", "Local GPU identity measured"),
    ("C03", "Local VRAM measured"),
    ("C04", "CUDA execution remains available"),
    ("C05", "Host RAM characterized"),
    ("C06", "Storage capacity characterized"),
    ("C07", "Local training role explicitly classified"),
    ("C08", "Training execution mode selected"),
    ("C09", "Primary training resource identified"),
    ("C10", "Software/runtime compatibility documented"),
    ("C11", "Model/dataset/checkpoint storage strategy defined"),
    ("C12", "Budget policy defined"),
    ("C13", "Cost inputs provenance validated when applicable"),
    ("C14", "Primary-path budget feasibility classified"),
    ("C15", "Fallback compute strategy defined"),
    ("C16", "Reproduction strategy documented"),
    ("C17", "Unsupported training-fit claims rejected"),
    ("C18", "No actual fine-tuning/training executed"),
    ("C19", "No downstream task leakage"),
    ("C20", "Final readiness decision and authorization consistent"),
)
BOUND_SOURCE_PATHS = (
    "scripts/verify_training_resource_readiness.py",
    "tests/test_verify_training_resource_readiness.py",
    "docs/vla/training_compute_readiness_v1.md",
    "plans/vla_training_compute_budget_plan.md",
    "plans/vla_training_resource_risks.md",
)
MAX_DIAGNOSTIC_BYTES = 4096
MAX_JSON_BYTES = 2 * 1024 * 1024
DEFAULT_METADATA_TIMEOUT_SECONDS = 2.0
RESULT_QUEUE_TIMEOUT_SECONDS = 0.5
SUFFICIENT_PROVENANCE = PROVENANCE - {"NOT_VERIFIED"}
PLACEHOLDER_TEXT = {
    "",
    "n/a",
    "na",
    "none",
    "not applicable",
    "not verified",
    "not_verified",
    "null",
    "placeholder",
    "tbd",
    "unknown",
    "unresolved",
}
FALLBACK_NOT_REQUIRED_RULE = (
    "PRIMARY_RESOURCE_HAS_DOCUMENTED_REDUNDANCY_AND_POLICY_ACCEPTS_NO_SEPARATE_FALLBACK"
)
COST_FORMULA = "unit_price * estimated_training_hours"
STORAGE_FORMULA = (
    "dataset_size_bytes + checkpoint_size_bytes + model_cache_size_bytes + "
    "temporary_space_bytes"
)
CUDA_GPU_RESOURCE = "NVIDIA_CUDA_GPU"
IDENTITY_PROVENANCE = {"MEASURED", "DECLARED_INPUT", "DOCUMENTED"}
COMPATIBILITY_PROVENANCE = {"MEASURED", "DOCUMENTED"}
CAPACITY_PROVENANCE = {"MEASURED", "DECLARED_INPUT", "DOCUMENTED"}
PLAN_SELECTION_PROVENANCE = {"DECLARED_INPUT", "DOCUMENTED"}
PLANNED_SIZE_PROVENANCE = {"DECLARED_INPUT", "DOCUMENTED"}
DERIVED_CAPACITY_PROVENANCE = {"DECLARED_INPUT", "DERIVED", "DOCUMENTED"}
EXECUTION_ROLE_PAIRS = {
    "LOCAL_TRAINING": (
        "LOCAL_PRIMARY_RESOURCE_TRAINS",
        "LOCAL_PRIMARY_RESOURCE_TRAINS",
    ),
    "REMOTE_TRAINING": (
        "LOCAL_NON_TRAINING_SUPPORT_ONLY",
        "REMOTE_PRIMARY_RESOURCE_TRAINS",
    ),
    "HYBRID_TRAINING": (
        "LOCAL_DEVELOPMENT_CONFIGURATION_VALIDATION_ONLY",
        "REMOTE_PRIMARY_RESOURCE_TRAINS",
    ),
}


def _bounded(value: str, limit: int = MAX_DIAGNOSTIC_BYTES) -> str:
    return value.strip()[:limit]


def _run(
    command: Sequence[str],
    *,
    timeout_seconds: float = 10.0,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    output_limit: int = MAX_DIAGNOSTIC_BYTES,
) -> dict[str, Any]:
    """Run a bounded, non-interactive diagnostic command."""

    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=cwd,
            env=dict(env) if env is not None else None,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "available": True,
            "returncode": None,
            "timed_out": True,
            "output": _bounded(str(exc), output_limit),
        }
    except OSError as exc:
        return {
            "available": False,
            "returncode": None,
            "timed_out": False,
            "output": _bounded(f"{type(exc).__name__}: {exc}", output_limit),
        }

    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}" if output else completed.stderr
    return {
        "available": True,
        "returncode": completed.returncode,
        "timed_out": False,
        "output": _bounded(output, output_limit),
    }


def _sha256(
    path: Path, timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS
) -> str | None:
    helper = (
        "import hashlib,sys\n"
        "digest=hashlib.sha256()\n"
        "with open(sys.argv[1],'rb') as handle:\n"
        "    while True:\n"
        "        chunk=handle.read(1048576)\n"
        "        if not chunk:\n"
        "            break\n"
        "        digest.update(chunk)\n"
        "print(digest.hexdigest())\n"
    )
    result = _run(
        [sys.executable, "-I", "-c", helper, str(path)],
        timeout_seconds=timeout_seconds,
    )
    digest = result.get("output")
    if (
        result.get("returncode") != 0
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        return None
    return digest


def _json(
    path: Path, timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS
) -> dict[str, Any]:
    helper = (
        "import json,sys; limit=int(sys.argv[2]); "
        "f=open(sys.argv[1],'rb'); raw=f.read(limit+1); f.close(); "
        "assert len(raw)<=limit, 'JSON input exceeds bound'; "
        "value=json.loads(raw.decode('utf-8')); "
        "assert isinstance(value,dict), 'JSON root must be object'; "
        "print(json.dumps(value,separators=(',',':'),sort_keys=True))"
    )
    result = _run(
        [sys.executable, "-I", "-c", helper, str(path), str(MAX_JSON_BYTES)],
        timeout_seconds=timeout_seconds,
        output_limit=MAX_JSON_BYTES,
    )
    if result.get("returncode") != 0:
        return {}
    try:
        value = json.loads(result["output"])
    except (KeyError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _git(repository_root: Path) -> dict[str, Any]:
    commit = _run(["git", "rev-parse", "HEAD"], cwd=repository_root)
    branch = _run(["git", "branch", "--show-current"], cwd=repository_root)
    status = _run(["git", "status", "--short"], cwd=repository_root)
    return {
        "provenance": "MEASURED",
        "commit": commit["output"] if commit["returncode"] == 0 else None,
        "branch": branch["output"] if branch["returncode"] == 0 else None,
        "working_tree_clean": status["returncode"] == 0 and not status["output"],
        "working_tree_status": status["output"].splitlines(),
    }


def _evidence_payload_sha256(evidence: Mapping[str, Any]) -> str:
    normalized = deepcopy(dict(evidence))
    binding = normalized.get("content_binding")
    if isinstance(binding, dict):
        binding.pop("evidence_payload_sha256", None)
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bound_source_hashes(repository_root: Path) -> dict[str, str | None]:
    return {
        relative: _sha256(repository_root / relative)
        for relative in BOUND_SOURCE_PATHS
    }


def _memory(
    timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    result = _bounded_filesystem_metadata(
        Path("/proc/meminfo"), "meminfo", timeout_seconds
    )
    values = result.get("values", {}) if result.get("status") == "PASS" else {}
    return {
        "provenance": "MEASURED" if values else "NOT_VERIFIED",
        "source": "/proc/meminfo",
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
        "swap_total_bytes": values.get("SwapTotal"),
        "swap_free_bytes": values.get("SwapFree"),
        "timed_out": result.get("timed_out", False),
        "timeout_seconds": timeout_seconds,
        "metadata_probe": result,
    }


def _filesystem_metadata_worker(
    path_value: str,
    operation: str,
    result_queue: multiprocessing.Queue,
) -> None:
    """Run filesystem metadata operations in a terminable child process."""

    path = Path(path_value)
    try:
        if operation == "path_kind":
            result: dict[str, Any] = {
                "status": "PASS",
                "exists": path.exists(),
                "is_directory": path.is_dir(),
                "is_file": path.is_file(),
            }
        elif operation == "disk_usage":
            usage = shutil.disk_usage(path)
            result = {
                "status": "PASS",
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            }
        elif operation == "meminfo":
            values: dict[str, int] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                key, raw = line.split(":", 1)
                amount = raw.strip().split()
                if amount and amount[0].isdigit():
                    multiplier = (
                        1024 if len(amount) > 1 and amount[1] == "kB" else 1
                    )
                    values[key] = int(amount[0]) * multiplier
            result = {"status": "PASS", "values": values}
        elif operation == "which":
            result = {
                "status": "PASS",
                "resolved": shutil.which(path_value),
            }
        else:
            result = {
                "status": "NOT_VERIFIED",
                "detail": f"unsupported metadata operation: {operation}",
            }
    except (OSError, ValueError) as exc:
        result = {
            "status": "NOT_VERIFIED",
            "detail": _bounded(f"{type(exc).__name__}: {exc}"),
        }
    result_queue.put(result)


def _bounded_filesystem_metadata(
    path: Path,
    operation: str,
    timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Bound path metadata and disk-usage calls with cleanup on every path."""

    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        return {
            "status": "NOT_VERIFIED",
            "timed_out": False,
            "detail": "metadata timeout must be finite and positive",
        }
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_filesystem_metadata_worker,
        args=(str(path), operation, result_queue),
        daemon=True,
    )
    result: dict[str, Any]
    started = False
    try:
        process.start()
        started = True
        process.join(timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(RESULT_QUEUE_TIMEOUT_SECONDS)
            result = {
                "status": "NOT_VERIFIED",
                "timed_out": True,
                "detail": f"{operation} exceeded {timeout_seconds:.3f}s",
            }
        else:
            try:
                queued = result_queue.get(timeout=RESULT_QUEUE_TIMEOUT_SECONDS)
            except queue_module.Empty:
                queued = {
                    "status": "NOT_VERIFIED",
                    "detail": f"{operation} worker returned no result",
                }
            result = dict(queued)
            result["timed_out"] = False
    except (OSError, RuntimeError) as exc:
        result = {
            "status": "NOT_VERIFIED",
            "timed_out": False,
            "detail": _bounded(f"{type(exc).__name__}: {exc}"),
        }
    finally:
        if started and process.is_alive():
            process.terminate()
            process.join(RESULT_QUEUE_TIMEOUT_SECONDS)
        if started:
            process.close()
        result_queue.close()
        result_queue.join_thread()
    result.update(
        {
            "path": str(path),
            "operation": operation,
            "timeout_seconds": timeout_seconds,
        }
    )
    return result


def _filesystem(
    path: Path,
    timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    result = _bounded_filesystem_metadata(path, "disk_usage", timeout_seconds)
    if result.get("status") != "PASS":
        return {
            "provenance": "NOT_VERIFIED",
            "path": str(path),
            "total_bytes": None,
            "free_bytes": None,
            "timed_out": result.get("timed_out", False),
            "timeout_seconds": timeout_seconds,
            "detail": result.get("detail", "filesystem capacity unavailable"),
        }
    return {
        "provenance": "MEASURED",
        "path": str(path),
        "total_bytes": result["total_bytes"],
        "used_bytes": result["used_bytes"],
        "free_bytes": result["free_bytes"],
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
    }


def _nvidia(
    metadata_timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    discovery = _bounded_filesystem_metadata(
        Path("nvidia-smi"), "which", metadata_timeout_seconds
    )
    if discovery.get("timed_out") is True:
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "name": None,
            "memory_total_mib": None,
            "memory_free_mib": None,
            "compute_capability": None,
            "timed_out": True,
            "discovery_probe": discovery,
            "detail": "nvidia-smi discovery timed out",
        }
    executable = discovery.get("resolved") if discovery.get("status") == "PASS" else None
    fallback = Path("/usr/lib/wsl/lib/nvidia-smi")
    if executable is None:
        fallback_metadata = _bounded_filesystem_metadata(
            fallback, "path_kind", metadata_timeout_seconds
        )
        if fallback_metadata.get("is_file") is True:
            executable = str(fallback)
    if executable is None:
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "name": None,
            "memory_total_mib": None,
            "memory_free_mib": None,
            "compute_capability": None,
            "timed_out": discovery.get("timed_out", False),
            "discovery_probe": discovery,
            "detail": "nvidia-smi was not found",
        }
    query = _run(
        [
            executable,
            "--query-gpu=name,memory.total,memory.free,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        timeout_seconds=10.0,
    )
    lines = [line.strip() for line in query["output"].splitlines() if line.strip()]
    if query["returncode"] != 0 or len(lines) != 1:
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "name": None,
            "memory_total_mib": None,
            "memory_free_mib": None,
            "compute_capability": None,
            "query": query,
            "discovery_probe": discovery,
            "detail": "exactly one GPU could not be measured",
        }
    parts = [part.strip() for part in lines[0].split(",")]
    try:
        name, total, free, capability = parts
        total_mib = int(total)
        free_mib = int(free)
    except (ValueError, TypeError):
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "name": None,
            "memory_total_mib": None,
            "memory_free_mib": None,
            "compute_capability": None,
            "query": query,
            "discovery_probe": discovery,
            "detail": "nvidia-smi returned an unparsable result",
        }
    return {
        "provenance": "MEASURED",
        "available": True,
        "name": name,
        "memory_total_mib": total_mib,
        "memory_free_mib": free_mib,
        "compute_capability": capability,
        "query": query,
        "discovery_probe": discovery,
        "detail": "GPU identity and capacity only; not model-training-fit evidence",
    }


def _environment_footprint(
    path: Path,
    metadata_timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    metadata = _bounded_filesystem_metadata(
        path, "path_kind", metadata_timeout_seconds
    )
    if metadata.get("is_directory") is not True:
        return {
            "provenance": "NOT_VERIFIED",
            "path": str(path),
            "bytes": None,
            "timed_out": metadata.get("timed_out", False),
            "metadata_probe": metadata,
            "detail": "accepted environment path is not a verified directory",
        }
    result = _run(["du", "-sb", str(path)], timeout_seconds=30.0)
    try:
        size = int(result["output"].split()[0]) if result["returncode"] == 0 else None
    except (ValueError, IndexError):
        size = None
    return {
        "provenance": "MEASURED" if size is not None else "NOT_VERIFIED",
        "path": str(path),
        "bytes": size,
        "query": result,
        "metadata_probe": metadata,
        "detail": "package footprint only; excludes future models, datasets, and checkpoints",
    }


def _torch_probe(
    environment_path: Path,
    metadata_timeout_seconds: float = DEFAULT_METADATA_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    interpreter = environment_path / "bin" / "python"
    metadata = _bounded_filesystem_metadata(
        interpreter, "path_kind", metadata_timeout_seconds
    )
    if metadata.get("is_file") is not True:
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "timed_out": metadata.get("timed_out", False),
            "metadata_probe": metadata,
            "model_loaded": False,
            "tensor_allocation_probe_executed": False,
            "training_executed": False,
            "optimizer_updates_executed": False,
            "hyperparameter_search_executed": False,
            "detail": "accepted VLA environment interpreter is not a verified file",
        }
    probe = (
        "import json, torch, torchvision; "
        "print(json.dumps({'python':__import__('platform').python_version(),"
        "'torch':torch.__version__,'torchvision':torchvision.__version__,"
        "'cuda_runtime':torch.version.cuda,'cuda_available':torch.cuda.is_available(),"
        "'device_count':torch.cuda.device_count(),"
        "'device_name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"
        "'total_memory_bytes':torch.cuda.get_device_properties(0).total_memory "
        "if torch.cuda.is_available() else None}))"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = ""
    result = _run(
        [str(interpreter), "-c", probe],
        timeout_seconds=30.0,
        env=environment,
    )
    try:
        values = json.loads(result["output"]) if result["returncode"] == 0 else {}
    except json.JSONDecodeError:
        values = {}
    if not isinstance(values, dict) or not values:
        return {
            "provenance": "NOT_VERIFIED",
            "available": False,
            "query": result,
            "metadata_probe": metadata,
            "model_loaded": False,
            "tensor_allocation_probe_executed": False,
            "training_executed": False,
            "optimizer_updates_executed": False,
            "hyperparameter_search_executed": False,
            "detail": "bounded PyTorch metadata probe did not return valid JSON",
        }
    values.update(
        {
            "provenance": "MEASURED",
            "available": True,
            "query": result,
            "metadata_probe": metadata,
            "model_loaded": False,
            "tensor_allocation_probe_executed": False,
            "training_executed": False,
            "optimizer_updates_executed": False,
            "hyperparameter_search_executed": False,
            "detail": "metadata/runtime visibility only; no model or training workload",
        }
    )
    return values


def collect_local_resources(repository_root: Path, environment_path: Path) -> dict[str, Any]:
    """Collect bounded host facts without allocating model/training resources."""

    cache_path = Path(
        os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    ).expanduser()
    cache_metadata = _bounded_filesystem_metadata(cache_path, "path_kind")
    cache_exists = cache_metadata.get("exists") is True
    cache_measure_path = cache_path if cache_exists else cache_path.parent
    return {
        "host": {
            "provenance": "MEASURED",
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
        },
        "gpu": _nvidia(),
        "torch_cuda": _torch_probe(environment_path),
        "ram": _memory(),
        "repository_filesystem": _filesystem(repository_root),
        "cache_filesystem": _filesystem(cache_measure_path),
        "environment_footprint": _environment_footprint(environment_path),
        "environment_path": {
            "value": str(environment_path),
            "provenance": "DOCUMENTED",
        },
        "huggingface_cache_path": {
            "value": str(cache_path),
            "provenance": "MEASURED" if "HF_HOME" in os.environ else "DOCUMENTED",
            "exists": cache_exists,
            "created_by_task": False,
            "metadata_probe": cache_metadata,
        },
    }


def unresolved_plan(repository_root: Path) -> dict[str, Any]:
    """Return the truthful canonical plan when no resource/budget was declared."""

    return {
        "local_training": {
            "classification": "TRAINING_NOT_VERIFIED",
            "provenance": "DERIVED",
            "source_reference": "accepted TASK-P0-005 evidence plus P0-007 non-training measurement",
            "model_specific_evidence": {
                "available": False,
                "authorized_by_task": False,
                "provenance": "NOT_VERIFIED",
                "source_reference": None,
                "configuration_reference": None,
                "peak_vram_bytes": None,
                "detail": "No authorized model-specific training-fit evidence exists.",
            },
            "role": "development, configuration, metadata checks, and artifact inspection only",
        },
        "execution_mode": {
            "value": "UNRESOLVED",
            "provenance": "NOT_VERIFIED",
            "source_reference": None,
            "local_role": None,
            "training_role": None,
        },
        "primary_resource": {
            "identified": False,
            "resource_id": None,
            "provider_or_owner": None,
            "compute_kind": None,
            "availability": "NOT_VERIFIED",
            "availability_provenance": "NOT_VERIFIED",
            "availability_source_reference": None,
            "resource_class": None,
            "vram_bytes": None,
            "vram_provenance": "NOT_VERIFIED",
            "vram_source_reference": None,
            "required_vram_bytes": None,
            "required_vram_provenance": "NOT_VERIFIED",
            "required_vram_source_reference": None,
            "workload_config_reference": None,
            "provenance": "NOT_VERIFIED",
            "source_reference": None,
            "compatibility": "NOT_VERIFIED",
            "compatibility_provenance": "NOT_VERIFIED",
            "compatibility_source_reference": None,
            "detail": "Local training fit is unverified and no external compute is approved or evidenced.",
        },
        "storage": {
            "strategy_defined": True,
            "readiness": "STORAGE_NOT_VERIFIED",
            "provenance": "DOCUMENTED",
            "dataset_path": str(repository_root / "data" / "vla"),
            "checkpoint_path": str(repository_root / "results" / "vla" / "checkpoints"),
            "cache_path_source": "local_resources.huggingface_cache_path",
            "dataset_size_bytes": None,
            "dataset_size_provenance": "NOT_VERIFIED",
            "dataset_size_source_reference": None,
            "checkpoint_size_bytes": None,
            "checkpoint_size_provenance": "NOT_VERIFIED",
            "checkpoint_size_source_reference": None,
            "model_cache_size_bytes": None,
            "model_cache_size_provenance": "NOT_VERIFIED",
            "model_cache_size_source_reference": None,
            "temporary_space_bytes": None,
            "temporary_space_provenance": "NOT_VERIFIED",
            "temporary_space_source_reference": None,
            "required_capacity_bytes": None,
            "required_capacity_provenance": "NOT_VERIFIED",
            "required_capacity_source_reference": None,
            "capacity_formula": STORAGE_FORMULA,
            "available_capacity_bytes": None,
            "available_capacity_provenance": "NOT_VERIFIED",
            "available_capacity_source_reference": None,
            "artifact_movement_strategy": None,
            "checkpoint_retention_strategy": None,
            "temporary_space_strategy": None,
            "source_reference": "plans/vla_training_compute_budget_plan.md#storage-plan",
            "paths_created_by_task": False,
            "detail": "Paths are planned, but Dataset V1 and size-dependent capacity are not verified.",
        },
        "budget": {
            "policy": "UNRESOLVED",
            "provenance": "NOT_VERIFIED",
            "source_reference": None,
            "applies_to_resource_id": None,
            "feasibility": "NOT_VERIFIED",
            "currency": None,
            "resource_unit": None,
            "estimation_date": None,
            "approved_ceiling": None,
            "unit_price": None,
            "estimated_training_hours": None,
            "estimated_compute_cost": None,
            "cost_inputs": [],
            "cost_formula": None,
            "approved_ceiling_provenance": "NOT_VERIFIED",
            "approved_ceiling_source_reference": None,
            "unit_price_provenance": "NOT_VERIFIED",
            "unit_price_source_reference": None,
            "estimated_training_hours_provenance": "NOT_VERIFIED",
            "estimated_training_hours_source_reference": None,
            "estimated_compute_cost_provenance": "NOT_VERIFIED",
            "estimated_compute_cost_source_reference": None,
            "prepaid_resource_id": None,
            "prepaid_resource_reference": None,
            "prepaid_resource_provenance": "NOT_VERIFIED",
            "remaining_quota": None,
            "quota_unit": None,
            "quota_provenance": "NOT_VERIFIED",
            "quota_source_reference": None,
            "required_quota": None,
            "required_quota_unit": None,
            "required_quota_provenance": "NOT_VERIFIED",
            "required_quota_source_reference": None,
            "calculation_performed": False,
            "detail": "No approved numeric ceiling, prepaid resource, or verified local-only training path exists.",
        },
        "fallback": {
            "required": True,
            "defined": False,
            "availability": "NOT_VERIFIED",
            "strategy_id": None,
            "resource_id": None,
            "provider_or_owner": None,
            "compute_kind": None,
            "resource_class": None,
            "resource": None,
            "vram_bytes": None,
            "vram_provenance": "NOT_VERIFIED",
            "vram_source_reference": None,
            "required_vram_bytes": None,
            "required_vram_provenance": "NOT_VERIFIED",
            "required_vram_source_reference": None,
            "workload_config_reference": None,
            "provenance": "NOT_VERIFIED",
            "source_reference": None,
            "availability_provenance": "NOT_VERIFIED",
            "availability_source_reference": None,
            "compatibility": "NOT_VERIFIED",
            "compatibility_provenance": "NOT_VERIFIED",
            "compatibility_source_reference": None,
            "not_required_rule": None,
            "not_required_source_reference": None,
            "redundancy_evidence_reference": None,
            "storage_strategy_reference": None,
            "storage_strategy_provenance": "NOT_VERIFIED",
            "storage_strategy_source_reference": None,
            "budget": {
                "policy": "UNRESOLVED",
                "provenance": "NOT_VERIFIED",
                "source_reference": None,
                "applies_to_resource_id": None,
                "feasibility": "NOT_VERIFIED",
                "calculation_performed": False,
            },
            "stop_condition": "Do not train; obtain explicit resource and budget approval, then rerun P0-007.",
            "detail": "A stop/escalation rule exists, but no fallback compute resource is evidenced.",
        },
        "reproduction": {
            "defined": True,
            "provenance": "DOCUMENTED",
            "environment_isolation": "uv project-local virtual environment",
            "python": EXPECTED_RUNTIME["python"],
            "lerobot": EXPECTED_RUNTIME["lerobot"],
            "torch": EXPECTED_RUNTIME["torch"],
            "torchvision": EXPECTED_RUNTIME["torchvision"],
            "dependency_strategy": "retain accepted P0-005 direct pins and compare the recorded package snapshot",
            "source_revision": "training task must record Git commit and configuration",
            "artifact_strategy": "record dataset/model/config/commit linkage in the later authorized task",
        },
    }


def _check(
    check_id: str,
    area: str,
    passed: bool,
    pass_provenance: str,
    pass_detail: str,
    fail_detail: str,
    *,
    unresolved_status: str = "BLOCKED",
    fail_provenance: str = "NOT_VERIFIED",
) -> dict[str, Any]:
    return {
        "id": check_id,
        "area": area,
        "mandatory": True,
        "status": "PASS" if passed else unresolved_status,
        "provenance": pass_provenance if passed else fail_provenance,
        "detail": pass_detail if passed else fail_detail,
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _material_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    if normalized in PLACEHOLDER_TEXT:
        return False
    if normalized.startswith("<") and normalized.endswith(">"):
        return False
    tokens = set(
        normalized.replace("_", " ").replace("-", " ").replace("/", " ").split()
    )
    placeholder_tokens = {
        "na",
        "none",
        "null",
        "pending",
        "placeholder",
        "tbc",
        "tbd",
        "todo",
        "unknown",
        "unresolved",
    }
    return not bool(tokens & placeholder_tokens)


def _finite_nonnegative(value: Any, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(float(value)):
        return False
    return value > 0 if positive else value >= 0


def _evidenced(
    provenance: Any,
    source_reference: Any,
    *,
    allowed: set[str] | None = None,
) -> bool:
    return provenance in (allowed or SUFFICIENT_PROVENANCE) and _material_text(
        source_reference
    )


def _runtime_preserved(evidence: Mapping[str, Any]) -> bool:
    runtime = evidence.get("runtime_baseline", {})
    return bool(
        isinstance(runtime, Mapping)
        and all(runtime.get(key) == value for key, value in EXPECTED_RUNTIME.items())
        and runtime.get("upgrade_performed") is False
    )


def _execution_mode_valid(execution: Mapping[str, Any]) -> bool:
    mode = execution.get("value")
    expected_roles = EXECUTION_ROLE_PAIRS.get(mode)
    return bool(
        expected_roles is not None
        and _evidenced(
            execution.get("provenance"),
            execution.get("source_reference"),
            allowed=PLAN_SELECTION_PROVENANCE,
        )
        and (
            execution.get("local_role"),
            execution.get("training_role"),
        )
        == expected_roles
    )


def _primary_resource_valid(
    evidence: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> bool:
    return bool(
        primary.get("identified") is True
        and primary.get("availability") == "AVAILABLE"
        and _material_text(primary.get("resource_id"))
        and _material_text(primary.get("provider_or_owner"))
        and primary.get("compute_kind") == CUDA_GPU_RESOURCE
        and _material_text(primary.get("resource_class"))
        and _finite_nonnegative(primary.get("vram_bytes"), positive=True)
        and _finite_nonnegative(primary.get("required_vram_bytes"), positive=True)
        and primary.get("vram_bytes") >= primary.get("required_vram_bytes")
        and _material_text(primary.get("workload_config_reference"))
        and _evidenced(
            primary.get("provenance"),
            primary.get("source_reference"),
            allowed=IDENTITY_PROVENANCE,
        )
        and _evidenced(
            primary.get("availability_provenance"),
            primary.get("availability_source_reference"),
            allowed=IDENTITY_PROVENANCE,
        )
        and _evidenced(
            primary.get("vram_provenance"),
            primary.get("vram_source_reference"),
            allowed=CAPACITY_PROVENANCE,
        )
        and _evidenced(
            primary.get("required_vram_provenance"),
            primary.get("required_vram_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and primary.get("compatibility") == "COMPATIBLE"
        and _evidenced(
            primary.get("compatibility_provenance"),
            primary.get("compatibility_source_reference"),
            allowed=COMPATIBILITY_PROVENANCE,
        )
        and _runtime_preserved(evidence)
    )


def _local_training_verified(
    evidence: Mapping[str, Any],
    training: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> bool:
    model = training.get("model_specific_evidence", {})
    local = evidence.get("local_resources", {})
    gpu = local.get("gpu", {}) if isinstance(local, Mapping) else {}
    measured_vram = gpu.get("memory_total_mib")
    peak_vram = model.get("peak_vram_bytes") if isinstance(model, Mapping) else None
    return bool(
        training.get("classification") == "TRAINING_VERIFIED"
        and _evidenced(
            training.get("provenance"),
            training.get("source_reference"),
            allowed={"DERIVED", "DOCUMENTED"},
        )
        and isinstance(model, Mapping)
        and model.get("available") is True
        and model.get("authorized_by_task") is True
        and _evidenced(
            model.get("provenance"),
            model.get("source_reference"),
            allowed={"MEASURED", "DOCUMENTED"},
        )
        and _material_text(model.get("configuration_reference"))
        and _finite_nonnegative(peak_vram, positive=True)
        and _finite_nonnegative(measured_vram, positive=True)
        and peak_vram <= measured_vram * 1024 * 1024
        and _primary_resource_valid(evidence, primary)
        and primary.get("resource_id") == "LOCAL_ACCEPTED_P0_005_GPU"
        and primary.get("vram_bytes") == measured_vram * 1024 * 1024
        and primary.get("required_vram_bytes") == peak_vram
    )


def _storage_valid(storage: Mapping[str, Any]) -> bool:
    dataset_size = storage.get("dataset_size_bytes")
    checkpoint_size = storage.get("checkpoint_size_bytes")
    model_cache_size = storage.get("model_cache_size_bytes")
    temporary_space = storage.get("temporary_space_bytes")
    required_capacity = storage.get("required_capacity_bytes")
    return bool(
        storage.get("strategy_defined") is True
        and storage.get("readiness") == "STORAGE_READY"
        and _evidenced(
            storage.get("provenance"),
            storage.get("source_reference"),
            allowed=PLAN_SELECTION_PROVENANCE,
        )
        and _material_text(storage.get("dataset_path"))
        and _material_text(storage.get("checkpoint_path"))
        and _material_text(storage.get("cache_path_source"))
        and _finite_nonnegative(storage.get("dataset_size_bytes"), positive=True)
        and _evidenced(
            storage.get("dataset_size_provenance"),
            storage.get("dataset_size_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and _finite_nonnegative(storage.get("checkpoint_size_bytes"), positive=True)
        and _evidenced(
            storage.get("checkpoint_size_provenance"),
            storage.get("checkpoint_size_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and _finite_nonnegative(model_cache_size, positive=True)
        and _evidenced(
            storage.get("model_cache_size_provenance"),
            storage.get("model_cache_size_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and _finite_nonnegative(temporary_space, positive=True)
        and _evidenced(
            storage.get("temporary_space_provenance"),
            storage.get("temporary_space_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and _finite_nonnegative(required_capacity, positive=True)
        and _evidenced(
            storage.get("required_capacity_provenance"),
            storage.get("required_capacity_source_reference"),
            allowed={"DERIVED"},
        )
        and storage.get("capacity_formula") == STORAGE_FORMULA
        and required_capacity
        == dataset_size + checkpoint_size + model_cache_size + temporary_space
        and _finite_nonnegative(storage.get("available_capacity_bytes"), positive=True)
        and _evidenced(
            storage.get("available_capacity_provenance"),
            storage.get("available_capacity_source_reference"),
            allowed=CAPACITY_PROVENANCE,
        )
        and storage.get("available_capacity_bytes") >= required_capacity
        and _material_text(storage.get("artifact_movement_strategy"))
        and _material_text(storage.get("checkpoint_retention_strategy"))
        and _material_text(storage.get("temporary_space_strategy"))
    )


def _decimal(value: Any) -> Decimal | None:
    if not _finite_nonnegative(value):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _numeric_budget_valid(
    budget: Mapping[str, Any], primary_resource_id: Any
) -> bool:
    required_fields = (
        "approved_ceiling",
        "unit_price",
        "estimated_training_hours",
        "estimated_compute_cost",
    )
    numbers = {field: _decimal(budget.get(field)) for field in required_fields}
    if any(value is None for value in numbers.values()):
        return False
    if (
        not _material_text(budget.get("applies_to_resource_id"))
        or budget.get("applies_to_resource_id") != primary_resource_id
    ):
        return False
    allowed_by_field = {
        "approved_ceiling": {"DECLARED_INPUT", "DOCUMENTED"},
        "unit_price": {"DECLARED_INPUT", "DOCUMENTED"},
        "estimated_training_hours": {
            "DECLARED_INPUT",
            "DOCUMENTED",
        },
        "estimated_compute_cost": {"DERIVED"},
    }
    if not all(
        _evidenced(
            budget.get(f"{field}_provenance"),
            budget.get(f"{field}_source_reference"),
            allowed=allowed_by_field[field],
        )
        for field in required_fields
    ):
        return False
    if budget.get("estimated_compute_cost_provenance") != "DERIVED":
        return False
    if not all(
        _material_text(budget.get(field))
        for field in ("currency", "resource_unit", "estimation_date")
    ):
        return False
    if budget.get("cost_formula") != COST_FORMULA:
        return False
    if budget.get("calculation_performed") is not True:
        return False
    inputs = budget.get("cost_inputs")
    if not isinstance(inputs, list) or len(inputs) != 3:
        return False
    expected_inputs = {
        "unit_price": budget.get("unit_price"),
        "estimated_training_hours": budget.get("estimated_training_hours"),
        "estimated_compute_cost": budget.get("estimated_compute_cost"),
    }
    actual_inputs: dict[str, Any] = {}
    for item in inputs:
        if not isinstance(item, Mapping) or item.get("name") in actual_inputs:
            return False
        name = item.get("name")
        if name not in expected_inputs or item.get("value") != expected_inputs[name]:
            return False
        if not _evidenced(
            item.get("provenance"),
            item.get("source_reference"),
            allowed=allowed_by_field[name],
        ):
            return False
        actual_inputs[name] = item.get("value")
    if set(actual_inputs) != set(expected_inputs):
        return False
    computed = numbers["unit_price"] * numbers["estimated_training_hours"]
    if numbers["estimated_compute_cost"] != computed:
        return False
    expected_feasibility = (
        "WITHIN_POLICY"
        if computed <= numbers["approved_ceiling"]
        else "OUTSIDE_POLICY"
    )
    return budget.get("feasibility") == expected_feasibility


def _budget_material(
    budget: Mapping[str, Any],
    execution_mode: Any,
    local_verified: bool,
    primary_resource_id: Any,
) -> tuple[bool, bool, bool]:
    policy = budget.get("policy")
    policy_evidenced = _evidenced(
        budget.get("provenance"),
        budget.get("source_reference"),
        allowed={"DECLARED_INPUT", "DOCUMENTED"},
    )
    if policy == "APPROVED_NUMERIC_BUDGET_CEILING":
        valid = policy_evidenced and _numeric_budget_valid(
            budget, primary_resource_id
        )
        return valid, valid, valid and budget.get("feasibility") == "WITHIN_POLICY"
    if policy == "EXISTING_PREPAID_RESOURCE":
        valid = bool(
            policy_evidenced
            and _material_text(budget.get("prepaid_resource_id"))
            and budget.get("prepaid_resource_id") == primary_resource_id
            and budget.get("applies_to_resource_id") == primary_resource_id
            and _evidenced(
                budget.get("prepaid_resource_provenance"),
                budget.get("prepaid_resource_reference"),
                allowed=IDENTITY_PROVENANCE,
            )
            and _finite_nonnegative(budget.get("remaining_quota"), positive=True)
            and _finite_nonnegative(budget.get("required_quota"), positive=True)
            and _material_text(budget.get("quota_unit"))
            and budget.get("required_quota_unit") == budget.get("quota_unit")
            and budget.get("remaining_quota") >= budget.get("required_quota")
            and _evidenced(
                budget.get("quota_provenance"),
                budget.get("quota_source_reference"),
                allowed=CAPACITY_PROVENANCE,
            )
            and _evidenced(
                budget.get("required_quota_provenance"),
                budget.get("required_quota_source_reference"),
                allowed=PLANNED_SIZE_PROVENANCE,
            )
            and all(
                budget.get(field) is None
                for field in (
                    "approved_ceiling",
                    "unit_price",
                    "estimated_training_hours",
                    "estimated_compute_cost",
                )
            )
            and budget.get("cost_inputs") == []
            and budget.get("cost_formula") is None
            and budget.get("calculation_performed") is False
            and budget.get("feasibility") == "WITHIN_POLICY"
        )
        return valid, valid, valid
    if policy == "LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET":
        valid = bool(
            policy_evidenced
            and execution_mode == "LOCAL_TRAINING"
            and local_verified
            and budget.get("applies_to_resource_id") == primary_resource_id
            and budget.get("calculation_performed") is False
            and _decimal(budget.get("estimated_compute_cost")) == Decimal("0")
            and budget.get("feasibility") == "WITHIN_POLICY"
        )
        return valid, valid, valid
    if policy == "UNRESOLVED" and budget.get("calculation_performed") is False:
        return False, True, False
    return False, False, False


def _fallback_valid(
    fallback: Mapping[str, Any], primary_resource_id: Any
) -> bool:
    # P0-007 has no authoritative rule that demonstrates a separate fallback
    # unnecessary.  READY therefore requires a concrete fallback resource.
    resource_id = fallback.get("resource_id")
    fallback_budget = _as_mapping(fallback.get("budget"))
    budget_defined, cost_valid, feasibility_valid = _budget_material(
        fallback_budget,
        "REMOTE_TRAINING",
        False,
        resource_id,
    )
    return bool(
        fallback.get("required") is True
        and fallback.get("defined") is True
        and fallback.get("availability") == "AVAILABLE"
        and _material_text(fallback.get("strategy_id"))
        and _material_text(fallback.get("resource_id"))
        and resource_id != primary_resource_id
        and _material_text(fallback.get("provider_or_owner"))
        and fallback.get("compute_kind") == CUDA_GPU_RESOURCE
        and _material_text(fallback.get("resource_class"))
        and _material_text(fallback.get("resource"))
        and _finite_nonnegative(fallback.get("vram_bytes"), positive=True)
        and _finite_nonnegative(fallback.get("required_vram_bytes"), positive=True)
        and fallback.get("vram_bytes") >= fallback.get("required_vram_bytes")
        and _material_text(fallback.get("workload_config_reference"))
        and _evidenced(
            fallback.get("provenance"),
            fallback.get("source_reference"),
            allowed=IDENTITY_PROVENANCE,
        )
        and _evidenced(
            fallback.get("availability_provenance"),
            fallback.get("availability_source_reference"),
            allowed=IDENTITY_PROVENANCE,
        )
        and _evidenced(
            fallback.get("vram_provenance"),
            fallback.get("vram_source_reference"),
            allowed=CAPACITY_PROVENANCE,
        )
        and _evidenced(
            fallback.get("required_vram_provenance"),
            fallback.get("required_vram_source_reference"),
            allowed=PLANNED_SIZE_PROVENANCE,
        )
        and fallback.get("compatibility") == "COMPATIBLE"
        and _evidenced(
            fallback.get("compatibility_provenance"),
            fallback.get("compatibility_source_reference"),
            allowed=COMPATIBILITY_PROVENANCE,
        )
        and _material_text(fallback.get("storage_strategy_reference"))
        and _evidenced(
            fallback.get("storage_strategy_provenance"),
            fallback.get("storage_strategy_source_reference"),
            allowed=PLAN_SELECTION_PROVENANCE,
        )
        and budget_defined
        and cost_valid
        and feasibility_valid
        and _material_text(fallback.get("stop_condition"))
    )


def _material_predicates(evidence: Mapping[str, Any]) -> dict[str, bool]:
    predecessors = _as_mapping(evidence.get("predecessors"))
    local = _as_mapping(evidence.get("local_resources"))
    plan = _as_mapping(evidence.get("resource_plan"))
    training = _as_mapping(plan.get("local_training"))
    execution = _as_mapping(plan.get("execution_mode"))
    primary = _as_mapping(plan.get("primary_resource"))
    storage = _as_mapping(plan.get("storage"))
    budget = _as_mapping(plan.get("budget"))
    fallback = _as_mapping(plan.get("fallback"))
    reproduction = _as_mapping(plan.get("reproduction"))
    scope = _as_mapping(evidence.get("scope_safety"))

    gpu = _as_mapping(local.get("gpu"))
    torch_cuda = _as_mapping(local.get("torch_cuda"))
    ram = _as_mapping(local.get("ram"))
    filesystem = _as_mapping(local.get("repository_filesystem"))
    classification = training.get("classification")
    no_scope_leakage = all(
        scope.get(field) is False
        for field in (
            "training_executed",
            "optimizer_updates_executed",
            "hyperparameter_search_executed",
            "dataset_v1_implemented",
            "physical_teleoperation_executed",
            "robot_camera_remediation_executed",
            "paid_compute_provisioned",
            "billing_or_credentials_created",
            "p0_006r_started",
            "p0_004r_started",
            "week1_task_started",
        )
    )
    execution_mode = execution.get("value")
    execution_valid = _execution_mode_valid(execution)
    primary_valid = _primary_resource_valid(evidence, primary)
    local_verified = _local_training_verified(evidence, training, primary)
    mode_resource_valid = bool(
        execution_valid
        and primary_valid
        and (
            execution_mode in {"REMOTE_TRAINING", "HYBRID_TRAINING"}
            or (execution_mode == "LOCAL_TRAINING" and local_verified)
        )
    )
    budget_defined, cost_provenance_valid, feasibility_valid = _budget_material(
        budget, execution_mode, local_verified, primary.get("resource_id")
    )
    training_claim_safe = classification != "TRAINING_VERIFIED" or local_verified
    storage_valid = _storage_valid(storage)
    fallback_defined = _fallback_valid(fallback, primary.get("resource_id"))
    generation = _as_mapping(evidence.get("generation"))
    training_activity_consistent = bool(
        generation.get("training_executed") is False
        and generation.get("optimizer_updates_executed") is False
        and generation.get("hyperparameter_search_executed") is False
        and torch_cuda.get("training_executed") is False
        and torch_cuda.get("optimizer_updates_executed") is False
        and torch_cuda.get("hyperparameter_search_executed") is False
        and scope.get("training_executed") is False
        and scope.get("optimizer_updates_executed") is False
        and scope.get("hyperparameter_search_executed") is False
    )

    return {
        "C01": bool(
            _as_mapping(predecessors.get("p0_005")).get("accepted") is True
            and _as_mapping(predecessors.get("p0_005")).get("hash_match") is True
            and _as_mapping(predecessors.get("p0_006")).get("accepted") is True
            and _as_mapping(predecessors.get("p0_006")).get("hash_match") is True
            and _as_mapping(predecessors.get("p0_006")).get("physical_outcome")
            == "DEVICE_IO_BLOCKED"
        ),
        "C02": bool(gpu.get("provenance") == "MEASURED" and gpu.get("name")),
        "C03": bool(gpu.get("provenance") == "MEASURED" and isinstance(gpu.get("memory_total_mib"), int) and gpu.get("memory_total_mib", 0) > 0),
        "C04": bool(torch_cuda.get("provenance") == "MEASURED" and torch_cuda.get("cuda_available") is True),
        "C05": bool(ram.get("provenance") == "MEASURED" and isinstance(ram.get("total_bytes"), int) and ram.get("total_bytes", 0) > 0),
        "C06": bool(filesystem.get("provenance") == "MEASURED" and isinstance(filesystem.get("total_bytes"), int) and filesystem.get("total_bytes", 0) > 0 and isinstance(filesystem.get("free_bytes"), int) and filesystem.get("free_bytes", 0) > 0),
        "C07": classification in LOCAL_TRAINING_CLASSIFICATIONS,
        "C08": execution_valid,
        "C09": mode_resource_valid,
        "C10": mode_resource_valid,
        "C11": storage_valid,
        "C12": budget_defined,
        "C13": cost_provenance_valid,
        "C14": feasibility_valid,
        "C15": fallback_defined,
        "C16": bool(reproduction.get("defined") is True and reproduction.get("provenance") in PROVENANCE - {"NOT_VERIFIED"} and all(reproduction.get(key) == value for key, value in EXPECTED_RUNTIME.items())),
        "C17": training_claim_safe,
        "C18": no_scope_leakage and training_activity_consistent,
        "C19": no_scope_leakage,
        "C20": bool(evidence.get("task_w1_001_authorized") is False and evidence.get("p0_004r_required") is True),
    }


def _checks_from_material(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    predicates = _material_predicates(evidence)
    details = {
        "C01": ("accepted predecessor hashes and context are intact", "accepted predecessor evidence/context is not intact"),
        "C02": ("GPU identity was measured", "GPU identity was not measured"),
        "C03": ("GPU VRAM was measured", "GPU VRAM was not measured"),
        "C04": ("PyTorch reports CUDA available in the accepted environment", "PyTorch CUDA availability was not established"),
        "C05": ("host RAM was measured", "host RAM was not characterized"),
        "C06": ("repository filesystem capacity was measured", "filesystem capacity was not characterized"),
        "C07": ("local training role has an allowed classification", "local training role is missing or invalid"),
        "C08": ("a training execution mode is selected", "training execution mode remains UNRESOLVED or invalid"),
        "C09": ("an available primary resource is evidenced", "no available primary training resource is evidenced"),
        "C10": ("primary path preserves the accepted runtime baseline", "primary-path runtime compatibility is not verified"),
        "C11": ("storage paths and unknown size-dependent requirements are explicit", "storage strategy is missing or has invalid provenance"),
        "C12": ("an allowed non-UNRESOLVED budget policy is evidenced", "budget policy remains UNRESOLVED or malformed"),
        "C13": ("cost inputs have allowed provenance, or no calculation was performed", "cost inputs are malformed or have invalid provenance"),
        "C14": ("primary path is within the evidenced budget policy", "primary-path budget feasibility is not verified or outside policy"),
        "C15": ("an available fallback compute strategy is evidenced", "no available fallback compute resource is evidenced"),
        "C16": ("accepted runtime reconstruction strategy is documented", "reproduction strategy is missing or changes the baseline"),
        "C17": ("local training remains TRAINING_NOT_VERIFIED/UNSUITABLE without unsupported fit claims", "unsupported local-training fit claim detected"),
        "C18": ("no training or optimizer update was executed", "training activity was recorded"),
        "C19": ("no procurement, device remediation, dataset, re-gate, or Week 1 work occurred", "downstream or prohibited work was recorded"),
        "C20": ("authorization remains false and P0-004R remains required", "final authorization fields are inconsistent"),
    }
    pass_provenance = {
        "C01": "DOCUMENTED",
        "C02": "MEASURED",
        "C03": "MEASURED",
        "C04": "MEASURED",
        "C05": "MEASURED",
        "C06": "MEASURED",
        "C07": "DERIVED",
        "C08": "DERIVED",
        "C09": "DERIVED",
        "C10": "DERIVED",
        "C11": "DERIVED",
        "C12": "DERIVED",
        "C13": "DERIVED",
        "C14": "DERIVED",
        "C15": "DERIVED",
        "C16": "DOCUMENTED",
        "C17": "DOCUMENTED",
        "C18": "DOCUMENTED",
        "C19": "DOCUMENTED",
        "C20": "DOCUMENTED",
    }
    fail_provenance = {
        **pass_provenance,
        "C08": "NOT_VERIFIED",
        "C09": "NOT_VERIFIED",
        "C10": "NOT_VERIFIED",
        "C11": "DOCUMENTED",
        "C12": "NOT_VERIFIED",
        "C14": "NOT_VERIFIED",
        "C15": "NOT_VERIFIED",
    }
    return [
        _check(
            check_id,
            area,
            predicates[check_id],
            pass_provenance[check_id],
            *details[check_id],
            fail_provenance=fail_provenance[check_id],
        )
        for check_id, area in EXPECTED_CHECKS
    ]


def decide_readiness(checks: Sequence[Mapping[str, Any]]) -> str:
    if len(checks) != len(EXPECTED_CHECKS):
        return BLOCKED
    for expected, check in zip(EXPECTED_CHECKS, checks, strict=True):
        if (
            check.get("id") != expected[0]
            or check.get("area") != expected[1]
            or check.get("mandatory") is not True
            or check.get("status") != "PASS"
        ):
            return BLOCKED
    return READY


def _blockers(checks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "check_id": item.get("id"),
            "area": item.get("area"),
            "status": item.get("status"),
            "detail": item.get("detail"),
        }
        for item in checks
        if item.get("mandatory") is True and item.get("status") != "PASS"
    ]


def build_evidence(
    repository_root: Path,
    local_resources: Mapping[str, Any],
    resource_plan: Mapping[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    p0_005_path = repository_root / "results" / "phase0" / "P0-005_vla_runtime.json"
    p0_006_path = repository_root / "results" / "phase0" / "P0-006_robot_io_readiness.json"
    p0_005 = _json(p0_005_path)
    p0_006 = _json(p0_006_path)
    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_ID,
        "verifier_version": VERIFIER_VERSION,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "generation": {
            "provenance": "MEASURED",
            "mode": "PRE_COMMIT_WORKTREE",
            "training_executed": False,
            "optimizer_updates_executed": False,
            "hyperparameter_search_executed": False,
            "external_resource_contacted": False,
        },
        "git": _git(repository_root),
        "predecessors": {
            "p0_005": {
                "task": "TASK-P0-005",
                "accepted": p0_005.get("runtime_decision") == "RUNTIME_READY",
                "acceptance_provenance": "DOCUMENTED",
                "evidence_path": "results/phase0/P0-005_vla_runtime.json",
                "expected_sha256": EXPECTED_P0_005_SHA256,
                "actual_sha256": _sha256(p0_005_path),
                "hash_match": _sha256(p0_005_path) == EXPECTED_P0_005_SHA256,
            },
            "p0_006": {
                "task": "TASK-P0-006",
                "accepted": p0_006.get("device_io_decision") == "DEVICE_IO_BLOCKED",
                "acceptance_provenance": "DOCUMENTED",
                "acceptance_source": "tasks/TASK-P0-007.md authoritative prerequisite contract",
                "physical_outcome": p0_006.get("device_io_decision"),
                "evidence_path": "results/phase0/P0-006_robot_io_readiness.json",
                "expected_sha256": EXPECTED_P0_006_SHA256,
                "actual_sha256": _sha256(p0_006_path),
                "hash_match": _sha256(p0_006_path) == EXPECTED_P0_006_SHA256,
            },
        },
        "runtime_baseline": {
            **EXPECTED_RUNTIME,
            "provenance": "DOCUMENTED",
            "source": "accepted TASK-P0-005 evidence",
            "upgrade_performed": False,
        },
        "local_resources": deepcopy(dict(local_resources)),
        "resource_plan": deepcopy(dict(resource_plan)),
        "scope_safety": {
            "training_executed": False,
            "optimizer_updates_executed": False,
            "hyperparameter_search_executed": False,
            "dataset_v1_implemented": False,
            "physical_teleoperation_executed": False,
            "robot_camera_remediation_executed": False,
            "paid_compute_provisioned": False,
            "billing_or_credentials_created": False,
            "p0_006r_started": False,
            "p0_004r_started": False,
            "week1_task_started": False,
            "provenance": "DOCUMENTED",
        },
        "deferred_items": [
            {"item": "model-specific local training fit", "owner": "later explicitly authorized VLA training task", "provenance": "NOT_VERIFIED"},
            {"item": "Dataset V1 size and storage consumption", "owner": "TASK-W1-003 after authorization", "provenance": "NOT_VERIFIED"},
            {"item": "external compute selection/access/quota", "owner": "project/compute owner", "provenance": "NOT_VERIFIED"},
            {"item": "numeric budget ceiling or prepaid resource", "owner": "project owner", "provenance": "NOT_VERIFIED"},
            {"item": "physical device blockers", "owner": "TASK-P0-006R", "provenance": "DOCUMENTED"},
        ],
        "task_w1_001_authorized": False,
        "p0_004r_required": True,
    }
    evidence["checks"] = _checks_from_material(evidence)
    evidence["training_resource_decision"] = decide_readiness(evidence["checks"])
    evidence["unresolved_blockers"] = _blockers(evidence["checks"])
    evidence["content_binding"] = {
        "provenance": "DERIVED",
        "source_sha256": _bound_source_hashes(repository_root),
        "predecessor_sha256": {
            "results/phase0/P0-005_vla_runtime.json": _sha256(p0_005_path),
            "results/phase0/P0-006_robot_io_readiness.json": _sha256(p0_006_path),
        },
        "evidence_payload_sha256": None,
    }
    evidence["content_binding"]["evidence_payload_sha256"] = _evidence_payload_sha256(evidence)
    return evidence


def _provenance_errors(value: Any, path: str = "evidence") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "provenance" and child not in PROVENANCE:
                errors.append(f"{child_path} has invalid provenance: {child!r}")
            if key.endswith("_provenance") and child not in PROVENANCE:
                errors.append(f"{child_path} has invalid provenance: {child!r}")
            errors.extend(_provenance_errors(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_provenance_errors(child, f"{path}[{index}]"))
    return errors


def _numeric_budget_errors(
    budget: Mapping[str, Any], primary_resource_id: Any
) -> list[str]:
    errors: list[str] = []
    fields = (
        "approved_ceiling",
        "unit_price",
        "estimated_training_hours",
        "estimated_compute_cost",
    )
    invalid_fields = [field for field in fields if _decimal(budget.get(field)) is None]
    if invalid_fields:
        errors.append(
            "malformed numeric budget: finite non-negative values required for "
            + ", ".join(invalid_fields)
        )
        return errors
    if (
        not _material_text(budget.get("applies_to_resource_id"))
        or budget.get("applies_to_resource_id") != primary_resource_id
    ):
        errors.append("numeric budget must apply to the selected primary resource")
    allowed_by_field = {
        "approved_ceiling": {"DECLARED_INPUT", "DOCUMENTED"},
        "unit_price": {"DECLARED_INPUT", "DOCUMENTED"},
        "estimated_training_hours": {"DECLARED_INPUT", "DOCUMENTED"},
        "estimated_compute_cost": {"DERIVED"},
    }
    for field in fields:
        if not _evidenced(
            budget.get(f"{field}_provenance"),
            budget.get(f"{field}_source_reference"),
            allowed=allowed_by_field[field],
        ):
            errors.append(f"numeric budget {field} lacks sufficient provenance/source")
    if budget.get("estimated_compute_cost_provenance") != "DERIVED":
        errors.append("estimated_compute_cost provenance must be DERIVED")
    if not all(
        _material_text(budget.get(field))
        for field in ("currency", "resource_unit", "estimation_date")
    ):
        errors.append("numeric budget currency/resource unit/estimation date is missing")
    if budget.get("cost_formula") != COST_FORMULA:
        errors.append("numeric budget cost formula mismatch")
    if budget.get("calculation_performed") is not True:
        errors.append("numeric budget must record calculation_performed=true")
    inputs = budget.get("cost_inputs")
    if not isinstance(inputs, list) or len(inputs) != 3:
        errors.append("numeric budget cost_inputs must contain exactly three evidenced inputs")
    else:
        expected = {
            "unit_price": budget.get("unit_price"),
            "estimated_training_hours": budget.get("estimated_training_hours"),
            "estimated_compute_cost": budget.get("estimated_compute_cost"),
        }
        seen: set[Any] = set()
        for item in inputs:
            if not isinstance(item, Mapping):
                errors.append("numeric budget cost input must be an object")
                continue
            name = item.get("name")
            if name in seen or name not in expected:
                errors.append("numeric budget cost input identity mismatch")
                continue
            seen.add(name)
            if item.get("value") != expected[name]:
                errors.append(f"numeric budget cost input {name} value mismatch")
            if not _evidenced(
                item.get("provenance"),
                item.get("source_reference"),
                allowed=allowed_by_field[name],
            ):
                errors.append(f"numeric budget cost input {name} lacks provenance/source")
        if seen != set(expected):
            errors.append("numeric budget cost input set mismatch")
    unit_price = _decimal(budget.get("unit_price"))
    hours = _decimal(budget.get("estimated_training_hours"))
    claimed = _decimal(budget.get("estimated_compute_cost"))
    ceiling = _decimal(budget.get("approved_ceiling"))
    assert unit_price is not None and hours is not None
    assert claimed is not None and ceiling is not None
    computed = unit_price * hours
    if claimed != computed:
        errors.append(
            "inconsistent cost arithmetic: estimated_compute_cost must equal "
            "unit_price * estimated_training_hours"
        )
    expected_feasibility = (
        "WITHIN_POLICY" if computed <= ceiling else "OUTSIDE_POLICY"
    )
    if budget.get("feasibility") != expected_feasibility:
        errors.append(
            f"numeric budget feasibility must be {expected_feasibility} from recomputed cost"
        )
    return errors


def _policy_validation_errors(
    budget: Mapping[str, Any],
    execution_mode: Any,
    local_verified: bool,
    primary_resource_id: Any,
) -> list[str]:
    policy = budget.get("policy")
    if policy == "UNRESOLVED":
        return []
    errors: list[str] = []
    if not _evidenced(
        budget.get("provenance"),
        budget.get("source_reference"),
        allowed={"DECLARED_INPUT", "DOCUMENTED"},
    ):
        errors.append("budget policy lacks sufficient provenance/source")
    if policy == "APPROVED_NUMERIC_BUDGET_CEILING":
        errors.extend(_numeric_budget_errors(budget, primary_resource_id))
    elif policy == "EXISTING_PREPAID_RESOURCE":
        if not _material_text(budget.get("prepaid_resource_id")) or not _evidenced(
            budget.get("prepaid_resource_provenance"),
            budget.get("prepaid_resource_reference"),
            allowed=IDENTITY_PROVENANCE,
        ):
            errors.append("prepaid budget lacks concrete resource evidence/reference")
        if (
            budget.get("prepaid_resource_id") != primary_resource_id
            or budget.get("applies_to_resource_id") != primary_resource_id
        ):
            errors.append("prepaid budget must apply to the selected primary resource")
        if not _finite_nonnegative(budget.get("remaining_quota"), positive=True):
            errors.append("prepaid budget remaining quota must be finite and positive")
        if not _finite_nonnegative(budget.get("required_quota"), positive=True):
            errors.append("prepaid budget required quota must be finite and positive")
        if not _material_text(budget.get("quota_unit")) or not _evidenced(
            budget.get("quota_provenance"),
            budget.get("quota_source_reference"),
            allowed=CAPACITY_PROVENANCE,
        ):
            errors.append("prepaid budget quota lacks unit/provenance/source")
        if (
            budget.get("required_quota_unit") != budget.get("quota_unit")
            or not _evidenced(
                budget.get("required_quota_provenance"),
                budget.get("required_quota_source_reference"),
                allowed=PLANNED_SIZE_PROVENANCE,
            )
        ):
            errors.append("prepaid required quota lacks matching unit/provenance/source")
        remaining_quota = budget.get("remaining_quota")
        required_quota = budget.get("required_quota")
        if (
            _finite_nonnegative(remaining_quota, positive=True)
            and _finite_nonnegative(required_quota, positive=True)
            and remaining_quota < required_quota
        ):
            errors.append("prepaid remaining quota is below evidenced required usage")
        if (
            any(
                budget.get(field) is not None
                for field in (
                    "approved_ceiling",
                    "unit_price",
                    "estimated_training_hours",
                    "estimated_compute_cost",
                )
            )
            or budget.get("cost_inputs") != []
            or budget.get("cost_formula") is not None
        ):
            errors.append("prepaid policy contains contradictory numeric cost inputs")
        if budget.get("calculation_performed") is not False:
            errors.append("prepaid policy must not claim a numeric cost calculation")
        if budget.get("feasibility") != "WITHIN_POLICY":
            errors.append("evidenced prepaid policy must be WITHIN_POLICY")
    elif policy == "LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET":
        if execution_mode != "LOCAL_TRAINING" or not local_verified:
            errors.append("zero incremental local budget requires verified LOCAL_TRAINING")
        if budget.get("applies_to_resource_id") != primary_resource_id:
            errors.append("local-only budget must apply to the selected primary resource")
        if budget.get("calculation_performed") is not False:
            errors.append("local-only zero budget must not claim a cost calculation")
        if _decimal(budget.get("estimated_compute_cost")) != Decimal("0"):
            errors.append("local-only zero budget requires estimated_compute_cost=0")
        if budget.get("feasibility") != "WITHIN_POLICY":
            errors.append("local-only zero budget must be WITHIN_POLICY")
    return errors


def validate_evidence(
    evidence: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
    verify_bound_files: bool = False,
) -> list[str]:
    errors: list[str] = []
    if evidence.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if evidence.get("task") != TASK_ID:
        errors.append("task identity mismatch")
    checks = evidence.get("checks")
    if not isinstance(checks, list):
        return errors + ["checks must be a list"]
    identities = [(item.get("id"), item.get("area")) for item in checks if isinstance(item, dict)]
    if identities != list(EXPECTED_CHECKS):
        errors.append("check identity/order mismatch")
    if len({identity[0] for identity in identities}) != len(identities):
        errors.append("check identities must be unique")
    for expected, item in zip(EXPECTED_CHECKS, checks):
        if not isinstance(item, dict):
            errors.append(f"{expected[0]} must be an object")
            continue
        if item.get("mandatory") is not True:
            errors.append(f"{expected[0]} must remain mandatory")
        if item.get("status") not in CHECK_STATUSES:
            errors.append(f"{expected[0]} has invalid status")
        if item.get("provenance") not in PROVENANCE:
            errors.append(f"{expected[0]} has invalid provenance")
        if item.get("status") == "PASS" and item.get("provenance") == "NOT_VERIFIED":
            errors.append(f"{expected[0]} PASS cannot use NOT_VERIFIED provenance")

    plan = evidence.get("resource_plan")
    if not isinstance(plan, dict):
        errors.append("resource_plan must be an object")
        plan = {}
    training = _as_mapping(plan.get("local_training"))
    if training.get("classification") not in LOCAL_TRAINING_CLASSIFICATIONS:
        errors.append("invalid local training classification")
    execution = _as_mapping(plan.get("execution_mode"))
    if execution.get("value") not in EXECUTION_MODES:
        errors.append("invalid training execution mode")
    budget = _as_mapping(plan.get("budget"))
    if budget.get("policy") not in BUDGET_POLICIES:
        errors.append("missing or invalid budget policy")
    if budget.get("feasibility") not in BUDGET_FEASIBILITY:
        errors.append("invalid budget feasibility")
    primary = _as_mapping(plan.get("primary_resource"))
    local_verified = _local_training_verified(evidence, training, primary)
    errors.extend(
        _policy_validation_errors(
            budget,
            execution.get("value"),
            local_verified,
            primary.get("resource_id"),
        )
    )
    if training.get("classification") == "TRAINING_VERIFIED" and not local_verified:
        errors.append(
            "unsupported local-training claim: TRAINING_VERIFIED lacks authorized "
            "model-specific fit evidence and compatible local resource facts"
        )
    generation = _as_mapping(evidence.get("generation"))
    torch_cuda = _as_mapping(
        _as_mapping(evidence.get("local_resources")).get("torch_cuda")
    )
    scope = _as_mapping(evidence.get("scope_safety"))
    if not (
        generation.get("training_executed") is False
        and generation.get("optimizer_updates_executed") is False
        and generation.get("hyperparameter_search_executed") is False
        and torch_cuda.get("training_executed") is False
        and torch_cuda.get("optimizer_updates_executed") is False
        and torch_cuda.get("hyperparameter_search_executed") is False
        and scope.get("training_executed") is False
        and scope.get("optimizer_updates_executed") is False
        and scope.get("hyperparameter_search_executed") is False
    ):
        errors.append("training activity fields are contradictory or unsafe")

    expected_checks = _checks_from_material(evidence)
    if checks != expected_checks:
        errors.append("checks do not match material facts")
    expected_decision = decide_readiness(expected_checks)
    if evidence.get("training_resource_decision") != expected_decision:
        errors.append("aggregate decision does not match mandatory material checks")
    if evidence.get("training_resource_decision") == READY and any(
        item.get("status") != "PASS" or item.get("mandatory") is not True
        for item in checks
    ):
        errors.append("TRAINING_RESOURCE_READY requires every mandatory check to PASS")
    if evidence.get("unresolved_blockers") != _blockers(expected_checks):
        errors.append("unresolved_blockers must exactly match mandatory non-PASS checks")
    if evidence.get("task_w1_001_authorized") is not False:
        errors.append("TASK-W1-001 authorization must remain false")
    if evidence.get("p0_004r_required") is not True:
        errors.append("TASK-P0-004R must remain required")
    errors.extend(_provenance_errors(evidence))

    binding = evidence.get("content_binding", {})
    if not isinstance(binding, dict):
        errors.append("content_binding must be an object")
    elif binding.get("evidence_payload_sha256") != _evidence_payload_sha256(evidence):
        errors.append("evidence payload hash mismatch")
    if verify_bound_files:
        if repository_root is None:
            errors.append("repository_root is required to verify bound files")
        else:
            source_hashes = binding.get("source_sha256", {}) if isinstance(binding, dict) else {}
            if source_hashes != _bound_source_hashes(repository_root):
                errors.append("bound source hashes do not match repository files")
            predecessors = binding.get("predecessor_sha256", {}) if isinstance(binding, dict) else {}
            expected_predecessors = {
                "results/phase0/P0-005_vla_runtime.json": _sha256(repository_root / "results/phase0/P0-005_vla_runtime.json"),
                "results/phase0/P0-006_robot_io_readiness.json": _sha256(repository_root / "results/phase0/P0-006_robot_io_readiness.json"),
            }
            if predecessors != expected_predecessors:
                errors.append("predecessor hashes do not match repository files")
            predecessor_facts = _as_mapping(evidence.get("predecessors"))
            for key, expected_hash in (
                ("p0_005", EXPECTED_P0_005_SHA256),
                ("p0_006", EXPECTED_P0_006_SHA256),
            ):
                facts = _as_mapping(predecessor_facts.get(key))
                if not (
                    facts.get("expected_sha256") == expected_hash
                    and facts.get("actual_sha256") == expected_hash
                    and facts.get("hash_match") is True
                ):
                    errors.append(f"{key} predecessor facts do not match accepted hash")
    return errors


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _default_environment_path(repository_root: Path) -> Path:
    accepted = _json(repository_root / "results/phase0/P0-005_vla_runtime.json")
    value = accepted.get("environment", {}).get("expected_environment")
    if isinstance(value, str) and value:
        return Path(value)
    return repository_root / ".venv-vla"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/phase0/P0-007_training_resource_readiness.json"),
    )
    parser.add_argument("--vla-environment", type=Path)
    parser.add_argument("--validate", type=Path, help="validate an existing artifact")
    arguments = parser.parse_args(argv)
    repository_root = Path(__file__).resolve().parents[1]
    if arguments.validate is not None:
        evidence = _json(arguments.validate)
        errors = validate_evidence(
            evidence, repository_root=repository_root, verify_bound_files=True
        )
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 3
        print(evidence.get("training_resource_decision"))
        return 0 if evidence.get("training_resource_decision") == READY else 2

    environment_path = arguments.vla_environment or _default_environment_path(repository_root)
    local = collect_local_resources(repository_root, environment_path)
    evidence = build_evidence(repository_root, local, unresolved_plan(repository_root))
    errors = validate_evidence(evidence)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 3
    output = arguments.output
    if not output.is_absolute():
        output = repository_root / output
    _atomic_write_json(output, evidence)
    print(evidence["training_resource_decision"])
    print(f"evidence: {output}")
    return 0 if evidence["training_resource_decision"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
