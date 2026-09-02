#!/usr/bin/env python3
"""Verify the isolated TASK-P0-005 CUDA/LeRobot/SmolVLA runtime.

This verifier is intentionally non-installing and non-actuating. It does not
open robot or camera devices, access model weights, run inference, start
training, or collect a dataset. It records bounded diagnostics and writes its
JSON result atomically, including when a runtime-blocking check fails.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


TASK_ID = "TASK-P0-005"
SCHEMA_VERSION = "1.0"
EXPECTED_ENVIRONMENT_NAME = ".venv-vla"
SELECTED_PYTHON = "3.12"
SELECTED_LEROBOT = "0.4.4"
SELECTED_LEROBOT_REVISION = "8fff0fde7c79f23a93d845d1a50e985de01f8b8a"
UPSTREAM_LEROBOT_CONSIDERED = "0.6.1"
SELECTED_TORCH = "2.10.0+cu130"
SELECTED_TORCHVISION = "0.25.0+cu130"
SELECTED_TORCH_BACKEND = "cu130"
SELECTED_UV = "0.12.9"
PLANNED_MODEL_ID = "lerobot/smolvla_base"
PYPI_INDEX = "https://pypi.org/simple"
PYTORCH_INDEX = "https://download.pytorch.org/whl/cu130"
UV_INSTALLER_URL = "https://astral.sh/uv/0.12.9/install.sh"
UV_INSTALLER_SHA256 = "222e006c0fe4a0d793031833e469b21df72311f4e3526ffecca0e19e6dfabc32"
LEROBOT_PYPI_URL = "https://pypi.org/project/lerobot/0.4.4/"
LEROBOT_SOURCE_URL = (
    "https://github.com/huggingface/lerobot/tree/"
    f"{SELECTED_LEROBOT_REVISION}"
)
PYTORCH_VERSIONS_URL = "https://pytorch.org/get-started/previous-versions/"

EVIDENCE_KINDS = {"MEASURED", "INFERRED", "DEFERRED", "NOT_AVAILABLE"}


def _bounded(value: str, limit: int = 4000) -> str:
    """Return bounded diagnostic text with surrounding whitespace removed."""

    return value.strip()[:limit]


def _run(
    command: Sequence[str],
    *,
    timeout_seconds: int = 20,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a diagnostic command and capture a bounded result."""

    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "available": True,
            "returncode": None,
            "timed_out": True,
            "output": _bounded(str(exc)),
        }
    except OSError as exc:
        return {
            "available": False,
            "returncode": None,
            "timed_out": False,
            "output": _bounded(f"{type(exc).__name__}: {exc}"),
        }

    combined = completed.stdout
    if completed.stderr:
        combined = f"{combined}\n{completed.stderr}" if combined else completed.stderr
    return {
        "available": True,
        "returncode": completed.returncode,
        "timed_out": False,
        "output": _bounded(combined),
    }


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line:
            continue
        key, raw_value = raw_line.split("=", 1)
        values[key] = raw_value.strip().strip('"')
    return values


def _memory() -> dict[str, Any]:
    values: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if path.is_file():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            key, _, raw_value = raw_line.partition(":")
            if key not in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                continue
            values[key] = int(raw_value.strip().split()[0]) * 1024
    return {
        "source": "/proc/meminfo",
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
        "swap_total_bytes": values.get("SwapTotal"),
        "swap_free_bytes": values.get("SwapFree"),
    }


def _git(repository_root: Path) -> dict[str, Any]:
    commit = _run(["git", "rev-parse", "HEAD"])
    branch = _run(["git", "branch", "--show-current"])
    status = _run(["git", "status", "--short"])
    return {
        "commit": commit["output"] if commit["returncode"] == 0 else None,
        "branch": branch["output"] if branch["returncode"] == 0 else None,
        "working_tree_clean": status["returncode"] == 0 and not status["output"],
        "working_tree_status": status["output"].splitlines(),
        "repository_root": str(repository_root),
    }


def _find_uv() -> Path | None:
    located = shutil.which("uv")
    if located:
        return Path(located).resolve()
    candidate = Path.home() / ".local" / "bin" / "uv"
    return candidate.resolve() if candidate.is_file() else None


def _python_and_environment(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_prefix = (repository_root / EXPECTED_ENVIRONMENT_NAME).resolve()
    actual_prefix = Path(sys.prefix).resolve()
    base_prefix = Path(sys.base_prefix).resolve()
    in_virtual_environment = actual_prefix != base_prefix
    ambient_pythonpath = os.environ.get("PYTHONPATH", "")
    external_pythonpath_clear = not bool(ambient_pythonpath)
    correct_environment = (
        in_virtual_environment
        and actual_prefix == expected_prefix
        and external_pythonpath_clear
    )

    system_environment = dict(os.environ)
    system_environment["PYTHONPATH"] = ""
    system_probe = _run(
        [
            "/usr/bin/python3",
            "-c",
            (
                "import importlib.util, json; "
                "print(json.dumps({'torch': importlib.util.find_spec('torch') is not None, "
                "'lerobot': importlib.util.find_spec('lerobot') is not None}))"
            ),
        ],
        environment=system_environment,
    )
    system_modules: dict[str, Any] | None = None
    if system_probe["returncode"] == 0:
        try:
            system_modules = json.loads(system_probe["output"])
        except json.JSONDecodeError:
            system_modules = None

    python = {
        "status": "PASS" if correct_environment else "FAIL",
        "evidence_kind": "MEASURED",
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": str(Path(sys.executable).absolute()),
        "sys_prefix": str(actual_prefix),
        "sys_base_prefix": str(base_prefix),
        "virtual_environment": in_virtual_environment,
        "expected_environment": str(expected_prefix),
        "expected_environment_match": correct_environment,
        "ambient_pythonpath_set": bool(ambient_pythonpath),
        "ambient_pythonpath_value_recorded": False,
        "ambient_pythonpath_requirement": "unset or empty for isolated evidence runs",
        "system_python_probe": {
            "executable": "/usr/bin/python3",
            "returncode": system_probe["returncode"],
            "modules_present": system_modules,
            "interpretation": (
                "The task installed packages only with --python .venv-vla/bin/python; "
                "the system interpreter still does not expose torch or lerobot."
            ),
        },
    }
    python_decision = {
        "status": "PASS" if platform.python_version_tuple()[:2] == ("3", "12") else "FAIL",
        "evidence_kind": "MEASURED",
        "selected_major_minor": SELECTED_PYTHON,
        "selected_exact": platform.python_version(),
        "interpreter_source": "/usr/bin/python3.12 used only as the base for uv venv",
        "environment_interpreter": str(Path(sys.executable).absolute()),
        "candidates_considered": [
            {
                "version": "3.12",
                "decision": "SELECTED",
                "reason": (
                    "Already present on Ubuntu 24.04; supported by LeRobot 0.4.4 "
                    "(Python >=3.10) and the selected PyTorch wheels."
                ),
            },
            {
                "version": "3.10 or 3.11",
                "decision": "REJECTED_NOT_REQUIRED",
                "reason": "Compatible with LeRobot 0.4.4 but would add an unnecessary managed interpreter.",
            },
            {
                "version": "3.13",
                "decision": "REJECTED_NOT_REQUIRED",
                "reason": "Not installed locally and adds no compatibility benefit for the retained baseline.",
            },
        ],
        "system_python_mutation_prohibited": True,
        "ambient_pythonpath_clear": external_pythonpath_clear,
    }
    return python_decision, python


def _uv() -> dict[str, Any]:
    path = _find_uv()
    result = _run([str(path), "--version"]) if path else None
    version_output = result["output"] if result else None
    correct_version = bool(version_output and re.search(r"\b0\.12\.9\b", version_output))
    return {
        "status": (
            "PASS"
            if path and result and result["returncode"] == 0 and correct_version
            else "FAIL"
        ),
        "evidence_kind": "MEASURED",
        "path": str(path) if path else None,
        "version_output": version_output,
        "selected_version_match": correct_version,
        "installation_scope": "user-scoped unmanaged standalone binary",
        "installer_url": UV_INSTALLER_URL,
        "installer_sha256": UV_INSTALLER_SHA256,
        "shell_profile_modified": False,
        "system_python_used_for_install": False,
    }


def _host(repository_root: Path) -> dict[str, Any]:
    release = _os_release()
    kernel = platform.release()
    disk = shutil.disk_usage(repository_root)
    return {
        "status": "PASS",
        "evidence_kind": "MEASURED",
        "os": release.get("PRETTY_NAME"),
        "distribution_id": release.get("ID"),
        "distribution_version": release.get("VERSION_ID"),
        "kernel": kernel,
        "machine": platform.machine(),
        "is_wsl": "microsoft" in kernel.lower() or "WSL" in platform.version(),
        "dev_dxg_exists": Path("/dev/dxg").exists(),
        "logical_cpu_count": os.cpu_count(),
        "memory": _memory(),
        "disk": {
            "path": str(repository_root),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
    }


def _parse_nvidia_header(output: str) -> dict[str, str | None]:
    pattern = re.compile(
        r"NVIDIA-SMI\s+(?P<smi>[0-9.]+).*?Driver Version:\s*"
        r"(?P<driver>[0-9.]+).*?CUDA Version:\s*(?P<cuda>[0-9.]+)",
        re.DOTALL,
    )
    match = pattern.search(output)
    if not match:
        return {"nvidia_smi_version": None, "driver_version": None, "driver_cuda": None}
    return {
        "nvidia_smi_version": match.group("smi"),
        "driver_version": match.group("driver"),
        "driver_cuda": match.group("cuda"),
    }


def _nvidia() -> dict[str, Any]:
    path = shutil.which("nvidia-smi")
    if path is None:
        wsl_candidate = Path("/usr/lib/wsl/lib/nvidia-smi")
        if wsl_candidate.is_file():
            path = str(wsl_candidate)
    full = _run([path] if path else ["nvidia-smi"])
    query = _run(
        [
            path or "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,memory.free,compute_cap",
            "--format=csv,noheader,nounits",
        ]
    )
    processes = _run(
        [
            path or "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    header = _parse_nvidia_header(full["output"])

    gpu: dict[str, Any] = {
        "name": None,
        "driver_version": None,
        "memory_total_mib": None,
        "memory_free_mib": None,
        "compute_capability": None,
    }
    if query["returncode"] == 0 and query["output"]:
        parts = [part.strip() for part in query["output"].splitlines()[0].split(",")]
        if len(parts) == 5:
            gpu = {
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mib": int(parts[2]),
                "memory_free_mib": int(parts[3]),
                "compute_capability": parts[4],
            }

    process_lines = [line for line in processes["output"].splitlines() if line.strip()]
    passed = (
        Path("/dev/dxg").exists()
        and full["returncode"] == 0
        and query["returncode"] == 0
        and gpu["name"] is not None
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "evidence_kind": "MEASURED",
        "nvidia_smi_path": path,
        **header,
        "gpu": gpu,
        "query": query,
        "compute_process_query": {
            "returncode": processes["returncode"],
            "count": len(process_lines) if processes["returncode"] == 0 else None,
            "processes": process_lines,
        },
        "dev_dxg_exists": Path("/dev/dxg").exists(),
        "interpretation": (
            "The CUDA value in the nvidia-smi header is the driver's reported "
            "compatibility level, not proof of a Toolkit, PyTorch runtime, LeRobot "
            "compatibility, or SmolVLA training capacity."
        ),
    }


def _cuda_toolkit() -> dict[str, Any]:
    nvcc = shutil.which("nvcc")
    result = _run([nvcc, "--version"]) if nvcc else None
    return {
        "status": "PASS" if nvcc and result and result["returncode"] == 0 else "NOT_AVAILABLE",
        "evidence_kind": "MEASURED" if nvcc else "NOT_AVAILABLE",
        "nvcc_path": nvcc,
        "version_output": result["output"] if result else None,
        "required_for_selected_wheel_runtime": False,
        "interpretation": (
            "A system CUDA Toolkit is not required for the selected official PyTorch "
            "wheel, which supplies its own CUDA runtime dependencies."
        ),
    }


def _torch_and_tensor() -> tuple[dict[str, Any], dict[str, Any]]:
    torch_info: dict[str, Any] = {
        "status": "FAIL",
        "evidence_kind": "MEASURED",
        "importable": False,
        "version": None,
        "cuda_runtime_version": None,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
    }
    tensor_test: dict[str, Any] = {
        "status": "FAIL",
        "evidence_kind": "NOT_AVAILABLE",
        "operation": "2x2 float32 matrix multiplication",
        "expected": [[19.0, 22.0], [43.0, 50.0]],
        "diagnostic_timing_only": True,
    }

    try:
        torch = importlib.import_module("torch")
        torch_info["importable"] = True
        torch_info["version"] = str(torch.__version__)
        torch_info["selected_version_match"] = str(torch.__version__) == SELECTED_TORCH
        torch_info["cuda_runtime_version"] = getattr(torch.version, "cuda", None)
        torch_info["cuda_available"] = bool(torch.cuda.is_available())
        torch_info["device_count"] = int(torch.cuda.device_count())
        torch_info["cudnn_available"] = bool(torch.backends.cudnn.is_available())
        torch_info["cudnn_version"] = torch.backends.cudnn.version()
        torch_info["build_config"] = _bounded(torch.__config__.show(), 8000)

        for index in range(torch_info["device_count"]):
            properties = torch.cuda.get_device_properties(index)
            free_bytes, total_bytes = torch.cuda.mem_get_info(index)
            torch_info["devices"].append(
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "compute_capability": list(torch.cuda.get_device_capability(index)),
                    "total_memory_bytes": int(properties.total_memory),
                    "free_memory_bytes_at_check": int(free_bytes),
                    "runtime_total_memory_bytes": int(total_bytes),
                }
            )

        torch_ready = (
            torch_info["selected_version_match"]
            and torch_info["cuda_available"]
            and torch_info["device_count"] > 0
        )
        torch_info["status"] = "PASS" if torch_ready else "FAIL"

        if torch_ready:
            torch.cuda.synchronize(0)
            torch.cuda.reset_peak_memory_stats(0)
            allocated_before = int(torch.cuda.memory_allocated(0))
            reserved_before = int(torch.cuda.memory_reserved(0))
            start = time.perf_counter()
            left = torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cuda:0")
            right = torch.tensor([[5.0, 6.0], [7.0, 8.0]], device="cuda:0")
            product = left @ right
            torch.cuda.synchronize(0)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            actual = product.cpu().tolist()
            expected = tensor_test["expected"]
            numerical_pass = actual == expected
            tensor_test.update(
                {
                    "status": "PASS" if numerical_pass else "FAIL",
                    "evidence_kind": "MEASURED",
                    "device": "cuda:0",
                    "dtype": "float32",
                    "actual": actual,
                    "numerical_assertion": numerical_pass,
                    "synchronized": True,
                    "elapsed_ms": elapsed_ms,
                    "allocated_before_bytes": allocated_before,
                    "reserved_before_bytes": reserved_before,
                    "allocated_after_bytes": int(torch.cuda.memory_allocated(0)),
                    "reserved_after_bytes": int(torch.cuda.memory_reserved(0)),
                    "peak_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
                }
            )
    except Exception as exc:
        target = tensor_test if torch_info["importable"] else torch_info
        target["error"] = _bounded(f"{type(exc).__name__}: {exc}")

    return torch_info, tensor_test


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _package_snapshot() -> list[dict[str, str]]:
    packages = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    return [
        {"name": name, "version": packages[name]}
        for name in sorted(packages, key=str.casefold)
    ]


def _lerobot_and_smolvla(torch_ready: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    modules = [
        "lerobot",
        "lerobot.datasets.lerobot_dataset",
        "lerobot.policies.smolvla",
        "lerobot.policies.smolvla.modeling_smolvla",
        "lerobot.policies.smolvla.configuration_smolvla",
        "lerobot.policies.smolvla.processor_smolvla",
    ]
    imports: list[dict[str, Any]] = []
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            module_file = getattr(module, "__file__", None)
            imports.append(
                {
                    "module": module_name,
                    "status": "PASS",
                    "evidence_kind": "MEASURED",
                    "file": str(Path(module_file).resolve()) if module_file else None,
                    "error": None,
                }
            )
        except Exception as exc:
            imports.append(
                {
                    "module": module_name,
                    "status": "FAIL",
                    "evidence_kind": "MEASURED",
                    "file": None,
                    "error": _bounded(f"{type(exc).__name__}: {exc}"),
                }
            )

    version = _package_version("lerobot")
    torchvision_version = _package_version("torchvision")
    uv_path = _find_uv()
    check_environment = dict(os.environ)
    check_environment.setdefault("UV_CACHE_DIR", "/tmp/p0-005-uv-cache")
    dependency_check = (
        _run(
            [str(uv_path), "pip", "check", "--python", sys.executable],
            environment=check_environment,
        )
        if uv_path
        else {
            "available": False,
            "returncode": None,
            "timed_out": False,
            "output": "uv not found",
        }
    )
    imports_pass = all(item["status"] == "PASS" for item in imports)
    version_pass = version == SELECTED_LEROBOT
    torchvision_pass = torchvision_version == SELECTED_TORCHVISION
    dependencies_pass = dependency_check["returncode"] == 0
    lerobot = {
        "status": (
            "PASS"
            if imports_pass and version_pass and torchvision_pass and dependencies_pass
            else "FAIL"
        ),
        "evidence_kind": "MEASURED",
        "version": version,
        "selected_version_match": version_pass,
        "source_revision": SELECTED_LEROBOT_REVISION,
        "source_revision_evidence_kind": "INFERRED",
        "torchvision_version": torchvision_version,
        "torchvision_selected_version_match": torchvision_pass,
        "imports": imports,
        "dependency_check": dependency_check,
        "dependency_conflict_observed": not dependencies_pass,
        "package_snapshot": _package_snapshot(),
        "installation_performed_by_verifier": False,
    }

    smolvla: dict[str, Any] = {
        "status": "FAIL",
        "evidence_kind": "MEASURED",
        "planned_model_id": PLANNED_MODEL_ID,
        "policy_module_discovery": imports[2]["status"],
        "modeling_module_discovery": imports[3]["status"],
        "configuration_module_discovery": imports[4]["status"],
        "processor_module_discovery": imports[5]["status"],
        "config_instantiation": "FAIL",
        "model_download_attempted": False,
        "model_load_attempted": False,
        "inference_attempted": False,
        "fine_tuning_attempted": False,
        "evaluation_attempted": False,
    }
    if all(item["status"] == "PASS" for item in imports[2:]):
        try:
            config_module = importlib.import_module(
                "lerobot.policies.smolvla.configuration_smolvla"
            )
            config_class = getattr(config_module, "SmolVLAConfig")
            config = config_class(device="cuda" if torch_ready else "cpu")
            smolvla.update(
                {
                    "status": "PASS",
                    "config_instantiation": "PASS",
                    "config": {
                        "type": config.type,
                        "device": config.device,
                        "chunk_size": config.chunk_size,
                        "n_action_steps": config.n_action_steps,
                        "resize_imgs_with_padding": list(config.resize_imgs_with_padding),
                        "tokenizer_max_length": config.tokenizer_max_length,
                        "vlm_model_name": config.vlm_model_name,
                        "freeze_vision_encoder": config.freeze_vision_encoder,
                        "train_expert_only": config.train_expert_only,
                        "load_vlm_weights": config.load_vlm_weights,
                    },
                }
            )
        except Exception as exc:
            smolvla["config_error"] = _bounded(f"{type(exc).__name__}: {exc}")

    return lerobot, smolvla


def _version_decision() -> dict[str, Any]:
    return {
        "status": "PASS",
        "evidence_kind": "INFERRED",
        "repository_baseline": SELECTED_LEROBOT,
        "upstream_release_considered": UPSTREAM_LEROBOT_CONSIDERED,
        "selected_version": SELECTED_LEROBOT,
        "selected_source_revision": SELECTED_LEROBOT_REVISION,
        "selected_extra": "smolvla",
        "selected_python": SELECTED_PYTHON,
        "selected_torch": SELECTED_TORCH,
        "selected_torchvision": SELECTED_TORCHVISION,
        "selected_torch_backend": SELECTED_TORCH_BACKEND,
        "decision": "RETAIN_REPOSITORY_BASELINE",
        "reason": (
            "Retain the ADR-004/P0-004 baseline for this focused runtime gate. "
            "LeRobot 0.6.1 was considered but would introduce an unreviewed API and "
            "dependency migration unrelated to proving the declared 0.4.4 stack."
        ),
        "compatibility": {
            "lerobot_python": ">=3.10",
            "lerobot_torch": ">=2.2.1,<2.11.0",
            "lerobot_torchvision": ">=0.21.0,<0.26.0",
            "smolvla_dependencies": (
                "transformers>=4.57.1,<5.0.0; num2words>=0.5.14,<0.6.0; "
                "accelerate>=1.7.0,<2.0.0; safetensors>=0.4.3,<1.0.0"
            ),
        },
        "sources": [LEROBOT_PYPI_URL, LEROBOT_SOURCE_URL, PYTORCH_VERSIONS_URL],
        "direct_pins": [
            "torch==2.10.0",
            "torchvision==0.25.0",
            "lerobot[smolvla]==0.4.4",
        ],
        "indexes": {"default": PYPI_INDEX, "torch": PYTORCH_INDEX},
        "reproduction_command": (
            "uv venv --python /usr/bin/python3.12 .venv-vla && "
            "uv pip install --python .venv-vla/bin/python --torch-backend cu130 "
            "--strict 'torch==2.10.0' 'torchvision==0.25.0' "
            "'lerobot[smolvla]==0.4.4'"
        ),
    }


def _check(
    check_id: str,
    area: str,
    status: str,
    detail: str,
    *,
    blocking: bool = True,
    evidence_kind: str = "MEASURED",
) -> dict[str, Any]:
    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind: {evidence_kind}")
    return {
        "id": check_id,
        "area": area,
        "status": status,
        "blocking": blocking,
        "evidence_kind": evidence_kind,
        "detail": detail,
    }


def _decide_runtime(checks: Sequence[dict[str, Any]]) -> str:
    blocking_failures = [
        item for item in checks if item["blocking"] and item["status"] != "PASS"
    ]
    if blocking_failures:
        return "RUNTIME_BLOCKED"
    conditional = any(
        item["status"] in {"FAIL", "DEFERRED", "NOT_AVAILABLE"}
        and not item["blocking"]
        for item in checks
    )
    return "CONDITIONAL_RUNTIME_READY" if conditional else "RUNTIME_READY"


def collect_evidence(repository_root: Path) -> dict[str, Any]:
    python_decision, environment = _python_and_environment(repository_root)
    uv = _uv()
    host = _host(repository_root)
    nvidia = _nvidia()
    cuda_toolkit = _cuda_toolkit()
    torch, tensor_test = _torch_and_tensor()
    torch_ready = torch["status"] == "PASS" and tensor_test["status"] == "PASS"
    lerobot, smolvla = _lerobot_and_smolvla(torch_ready)
    version_decision = _version_decision()

    checks = [
        _check("C1", "Host/WSL", "PASS" if host["is_wsl"] else "FAIL", "WSL2 host detected"),
        _check("C2", "/dev/dxg", "PASS" if host["dev_dxg_exists"] else "FAIL", "WSL GPU device bridge visibility"),
        _check("C3", "Python decision", python_decision["status"], f"selected Python {python_decision['selected_exact']}"),
        _check("C4", "Isolated environment", environment["status"], "project-local .venv-vla interpreter"),
        _check("C5", "uv", uv["status"], uv["version_output"] or "uv unavailable"),
        _check("C6", "NVIDIA", nvidia["status"], nvidia["gpu"]["name"] or "GPU query failed"),
        _check("C7", "PyTorch CUDA", torch["status"], f"torch={torch['version']} runtime={torch['cuda_runtime_version']}"),
        _check("C8", "CUDA tensor", tensor_test["status"], "synchronized 2x2 matrix multiplication with numerical assertion"),
        _check("C9", "LeRobot version decision", version_decision["status"], "explicitly retained pinned LeRobot 0.4.4"),
        _check("C10", "LeRobot imports/dependencies", lerobot["status"], f"lerobot={lerobot['version']}"),
        _check("C11", "SmolVLA module/config", smolvla["status"], "installed-code discovery and non-training config instantiation"),
    ]
    runtime_decision = _decide_runtime(checks)
    runtime_blockers = [
        {
            "check_id": item["id"],
            "area": item["area"],
            "status": item["status"],
            "detail": item["detail"],
        }
        for item in checks
        if item["blocking"] and item["status"] != "PASS"
    ]

    total_vram = nvidia["gpu"].get("memory_total_mib")
    gpu_classification = {
        "evidence_kind": "INFERRED",
        "gpu": nvidia["gpu"].get("name"),
        "vram_total_mib": total_vram,
        "cuda_tensor_execution": tensor_test["status"],
        "lerobot_imports": lerobot["status"],
        "smolvla_module_config_discovery": smolvla["status"],
        "classification": (
            "CUDA_RUNTIME_AND_SMOLVLA_CODE_READY_TRAINING_UNVERIFIED"
            if runtime_decision == "RUNTIME_READY"
            else "RUNTIME_CAPABILITY_INCOMPLETE"
        ),
        "model_loading_tested": False,
        "local_inference_tested": False,
        "local_fine_tuning_tested": False,
        "smolvla_training_fit_in_6gb": "NOT_VERIFIED",
        "interpretation": (
            "This host has a measured working CUDA tensor and installed SmolVLA code/config "
            "surface. P0-005 did not load weights, run inference, or train; 6 GB training "
            "capacity is therefore neither proven nor disproven."
        ),
        "candidate_mitigations": {
            "evidence_kind": "INFERRED",
            "items": [
                "reduced batch size",
                "mixed precision if supported by the selected configuration",
                "gradient accumulation or checkpointing",
                "parameter-efficient tuning",
                "approved remote CUDA host",
            ],
        },
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_ID,
        "runtime_decision": runtime_decision,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git": _git(repository_root),
        "host": host,
        "input_observations": {
            "evidence_kind": "INFERRED",
            "classification": "USER_SUPPLIED_INPUT_NOT_MEASURED_BY_P0_005_UNTIL_RECHECK",
            "host": "WSL2 / Ubuntu 24.04",
            "nvidia_smi_succeeds": True,
            "nvidia_smi_version": "580.102.01",
            "driver_version": "581.57",
            "driver_reported_cuda_version": "13.0",
            "gpu": "NVIDIA GeForce RTX 2060-class",
            "vram_mib": 6144,
            "dev_dxg_exists": True,
            "active_gpu_processes": 0,
        },
        "python_decision": python_decision,
        "uv": uv,
        "environment": environment,
        "nvidia": nvidia,
        "cuda_toolkit": cuda_toolkit,
        "torch": torch,
        "cuda_tensor_test": tensor_test,
        "lerobot_version_decision": version_decision,
        "lerobot": lerobot,
        "smolvla": smolvla,
        "gpu_capability_classification": gpu_classification,
        "checks": checks,
        "runtime_blockers": runtime_blockers,
        "deferred_non_runtime_blockers": [
            {
                "area": "Manipulator/device I/O and camera",
                "status": "DEFERRED",
                "evidence_kind": "DEFERRED",
                "next_task": "TASK-P0-006",
            },
            {
                "area": "Supervised teleoperation/recording and training budget",
                "status": "DEFERRED",
                "evidence_kind": "DEFERRED",
                "next_task": "TASK-P0-007",
            },
            {
                "area": "Complete VLA readiness and TASK-W1-001 authorization",
                "status": "DEFERRED",
                "evidence_kind": "DEFERRED",
                "next_task": "TASK-P0-004R",
            },
        ],
        "safety": {
            "system_python_mutated": False,
            "system_cuda_or_driver_modified": False,
            "robot_commands_sent": False,
            "robot_or_camera_devices_opened": False,
            "model_downloaded": False,
            "model_loaded": False,
            "inference_started": False,
            "training_started": False,
            "fine_tuning_started": False,
            "evaluation_started": False,
            "dataset_v1_collected": False,
        },
        "task_w1_001_authorized": False,
        "p0_004r_regate_required": True,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        finally:
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repository_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--output",
        type=Path,
        default=repository_root / "results" / "phase0" / "P0-005_vla_runtime.json",
        help="JSON evidence output path",
    )
    arguments = parser.parse_args()

    evidence = collect_evidence(repository_root)
    _atomic_write_json(arguments.output, evidence)

    print(f"TASK: {TASK_ID}")
    print(f"Runtime decision: {evidence['runtime_decision']}")
    for item in evidence["checks"]:
        print(f"{item['id']} {item['area']}: {item['status']} - {item['detail']}")
    print(f"Evidence: {arguments.output}")
    print("TASK-W1-001 authorized: false")
    print("TASK-P0-004R re-gate required: true")
    return 2 if evidence["runtime_decision"] == "RUNTIME_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
