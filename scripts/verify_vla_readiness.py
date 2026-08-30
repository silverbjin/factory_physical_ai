#!/usr/bin/env python3
"""Run safe, non-destructive checks for the TASK-P0-004 VLA readiness gate.

The script never installs packages, downloads models, records a dataset, opens a
robot serial interface, or sends actuator commands.  If a video device is
present and OpenCV is importable, the normal verification run opens the first
camera long enough to read one frame and immediately releases it.
"""

from __future__ import annotations

import argparse
import glob
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


TASK_ID = "TASK-P0-004"
SCHEMA_VERSION = "1.0"
PLANNED_MODEL_ID = "lerobot/smolvla_base"
DEFAULT_DATASET_ROOT = "data/vla"


def _run(command: Sequence[str], timeout_seconds: int = 15) -> dict[str, Any]:
    """Run an allowlisted diagnostic command and capture a bounded result."""

    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "returncode": None,
            "output": f"{type(exc).__name__}: {exc}",
        }

    output = (completed.stdout or completed.stderr).strip()
    return {
        "available": True,
        "returncode": completed.returncode,
        "output": output[:4000],
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
            amount = raw_value.strip().split()[0]
            values[key] = int(amount) * 1024
    return {
        "source": "/proc/meminfo",
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
        "swap_total_bytes": values.get("SwapTotal"),
        "swap_free_bytes": values.get("SwapFree"),
    }


def _disk(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": str(path.resolve()),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _environment_variables() -> dict[str, dict[str, Any]]:
    non_secret_values = {
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CUDA_VISIBLE_DEVICES",
        "ROS_DISTRO",
        "ROS_DOMAIN_ID",
        "VLA_DATASET_ROOT",
    }
    relevant = [
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CUDA_VISIBLE_DEVICES",
        "ROS_DISTRO",
        "ROS_DOMAIN_ID",
        "VLA_DATASET_ROOT",
        "HF_HOME",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
    ]
    result: dict[str, dict[str, Any]] = {}
    for name in relevant:
        is_set = name in os.environ
        item: dict[str, Any] = {"set": is_set}
        if is_set and name in non_secret_values:
            item["value"] = os.environ[name]
        elif is_set:
            item["value"] = "REDACTED"
        result[name] = item
    return result


def _python_environment() -> dict[str, Any]:
    uv_path = shutil.which("uv")
    pip_result = _run([sys.executable, "-m", "pip", "--version"])
    uv_result = _run([uv_path, "--version"]) if uv_path else None
    return {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": sys.executable,
        "virtual_environment_active": bool(
            os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
        ),
        "virtual_environment_strategy": (
            "project-local virtual environment; uv preferred by frozen environment plan"
        ),
        "package_manager_strategy": (
            "uv-managed project environment when available; do not mutate system Python"
        ),
        "uv": {
            "available": uv_path is not None,
            "path": uv_path,
            "version_output": uv_result["output"] if uv_result else None,
        },
        "pip": pip_result,
    }


def _gpu_and_torch() -> tuple[dict[str, Any], dict[str, Any]]:
    nvidia_smi_path = shutil.which("nvidia-smi")
    nvidia_result: dict[str, Any]
    if nvidia_smi_path:
        nvidia_result = _run(
            [
                nvidia_smi_path,
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ]
        )
    else:
        nvidia_result = {
            "available": False,
            "returncode": None,
            "output": "nvidia-smi not found",
        }

    torch_info: dict[str, Any] = {
        "importable": False,
        "version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_runtime_version": None,
        "device_names": [],
        "allocation_test": "NOT AVAILABLE",
    }
    try:
        torch = importlib.import_module("torch")
        torch_info["importable"] = True
        torch_info["version"] = getattr(torch, "__version__", None)
        cuda = getattr(torch, "cuda", None)
        if cuda is not None:
            torch_info["cuda_available"] = bool(cuda.is_available())
            torch_info["cuda_device_count"] = int(cuda.device_count())
            torch_info["cuda_runtime_version"] = getattr(
                getattr(torch, "version", None), "cuda", None
            )
            torch_info["device_names"] = [
                str(cuda.get_device_name(index))
                for index in range(torch_info["cuda_device_count"])
            ]
            if torch_info["cuda_available"] and torch_info["cuda_device_count"] > 0:
                try:
                    tensor = torch.zeros(1, device="cuda")
                    _ = tensor.cpu()
                    torch_info["allocation_test"] = "PASS"
                except Exception as exc:  # diagnostic boundary: report, do not hide
                    torch_info["allocation_test"] = "FAIL"
                    torch_info["allocation_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # package/import failure is evidence for this gate
        torch_info["import_error"] = f"{type(exc).__name__}: {exc}"

    gpu_visible = (
        nvidia_result.get("returncode") == 0
        and bool(nvidia_result.get("output"))
        and torch_info["cuda_available"]
        and torch_info["cuda_device_count"] > 0
        and torch_info["allocation_test"] == "PASS"
    )
    gpu = {
        "status": "PASS" if gpu_visible else "FAIL",
        "evidence_kind": "MEASURED",
        "nvidia_smi_path": nvidia_smi_path,
        "nvidia_smi": nvidia_result,
        "torch_cuda_available": torch_info["cuda_available"],
        "device_count": torch_info["cuda_device_count"],
        "device_names": torch_info["device_names"],
        "cuda_runtime_version": torch_info["cuda_runtime_version"],
        "basic_tensor_allocation": torch_info["allocation_test"],
        "note": (
            "A failed WSL check means GPU execution is unavailable in this environment; "
            "it does not characterize an uninspected remote CUDA host."
        ),
    }
    return gpu, torch_info


def _lerobot() -> dict[str, Any]:
    modules = [
        "lerobot",
        "lerobot.datasets.lerobot_dataset",
        "lerobot.policies.smolvla.modeling_smolvla",
    ]
    imports: list[dict[str, Any]] = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            imports.append({"module": module_name, "status": "PASS", "error": None})
        except Exception as exc:
            imports.append(
                {
                    "module": module_name,
                    "status": "FAIL",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    try:
        version = importlib.metadata.version("lerobot")
    except importlib.metadata.PackageNotFoundError:
        version = None

    ready = version is not None and all(item["status"] == "PASS" for item in imports)
    return {
        "status": "PASS" if ready else "FAIL",
        "evidence_kind": "MEASURED",
        "version": version,
        "source_revision": None,
        "imports": imports,
        "dependency_conflict_observed": any(
            item["status"] == "FAIL" and "No module named" not in (item["error"] or "")
            for item in imports
        ),
        "reproduction_command": (
            "uv venv --python 3.12 .venv-vla && uv pip install "
            "--python .venv-vla/bin/python 'lerobot[smolvla]==0.4.4'"
        ),
        "reproduction_command_status": (
            "PROPOSED_NOT_EXECUTED; verify the pin and Python/CUDA compatibility on the "
            "approved host before installation"
        ),
        "installation_performed": False,
    }


def _smolvla(lerobot: dict[str, Any], gpu: dict[str, Any]) -> dict[str, Any]:
    module_ready = any(
        item["module"] == "lerobot.policies.smolvla.modeling_smolvla"
        and item["status"] == "PASS"
        for item in lerobot["imports"]
    )
    ready = lerobot["status"] == "PASS" and module_ready and gpu["status"] == "PASS"
    return {
        "status": "PASS" if ready else "FAIL",
        "evidence_kind": "MEASURED",
        "planned_model_id": PLANNED_MODEL_ID,
        "policy_module_importable": module_ready,
        "model_config_discovery": "PASS" if module_ready else "NOT AVAILABLE",
        "model_download_attempted": False,
        "model_load_attempted": False,
        "training_attempted": False,
        "compute_constraint": (
            "An approved CUDA host with measured GPU/VRAM, working Torch CUDA, and a "
            "documented training budget is required before fine-tuning."
        ),
        "compute_constraint_evidence_kind": "INFERRED",
        "memory_requirement": "TBD: measure on the selected CUDA host and training config",
    }


def _camera(skip_capture: bool) -> dict[str, Any]:
    devices = sorted(glob.glob("/dev/video*"))
    capture: dict[str, Any] = {
        "attempted": False,
        "status": "DEFERRED",
        "detail": "no video device exposed in current environment",
    }
    if devices and skip_capture:
        capture["detail"] = "capture explicitly skipped for this invocation"
    elif devices:
        try:
            cv2 = importlib.import_module("cv2")
            camera = cv2.VideoCapture(devices[0])
            try:
                capture["attempted"] = True
                opened = bool(camera.isOpened())
                ok, frame = camera.read() if opened else (False, None)
                capture.update(
                    {
                        "status": "PASS" if ok and frame is not None else "FAIL",
                        "device": devices[0],
                        "opened": opened,
                        "frame_shape": list(frame.shape) if ok and frame is not None else None,
                        "detail": "one frame read; frame was not persisted",
                    }
                )
            finally:
                camera.release()
        except Exception as exc:
            capture.update(
                {
                    "attempted": True,
                    "status": "FAIL",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )

    status = "PASS" if capture["status"] == "PASS" else "DEFERRED"
    if devices and capture["status"] == "FAIL":
        status = "FAIL"
    return {
        "status": status,
        "evidence_kind": "MEASURED",
        "devices": devices,
        "connection_type": "USB/OpenCV candidate; not selected",
        "planned_configuration": {
            "model": "TBD",
            "resolution": "640x480 hypothesis",
            "fps": "30 FPS hypothesis",
            "color_format": "RGB expected; device-native format TBD",
            "timestamp_source": "TBD on native robot PC",
            "mounting": "one fixed external camera; exact mount TBD",
        },
        "expected_observation_fields": [
            "observation.images.camera",
            "observation.state",
            "timestamp",
            "calibration_revision",
        ],
        "capture": capture,
    }


def _robot() -> dict[str, Any]:
    serial_devices = sorted(
        glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    )
    return {
        "status": "DEFERRED",
        "evidence_kind": "DEFERRED",
        "serial_devices": serial_devices,
        "environment_interpretation": (
            "NOT EXPOSED IN CURRENT ENVIRONMENT"
            if not serial_devices
            else "candidate serial interfaces exposed; identity not verified"
        ),
        "target_manipulator": "TBD after physical inventory; SO-101/SO-100 class preferred",
        "connection_method": "TBD (likely USB/serial through a supported LeRobot adapter)",
        "sdk_ros_dependency": "LeRobot adapter first; ROS/MoveIt boundary only if required",
        "command_path": "leader input -> LeRobot teleoperator -> validated follower adapter",
        "state_feedback_path": "follower adapter -> joint/gripper state -> recorder",
        "gripper_path": "supported leader/follower gripper channel; unverified",
        "safety_limitations": [
            "no device identity",
            "no mechanical/workspace limits recorded",
            "no operator start/stop or E-stop path verified",
            "no command was sent by this check",
        ],
    }


def _teleoperation() -> dict[str, Any]:
    return {
        "status": "DEFERRED",
        "evidence_kind": "DEFERRED",
        "intended_mechanism": "LeRobot-supported leader/follower teleoperation",
        "command_rate_expectation": "TBD from selected hardware adapter; must be measured",
        "command_flow": [
            "human leader input",
            "LeRobot teleoperation interface",
            "validated follower command adapter",
            "manipulator",
        ],
        "observation_flow": [
            "robot/camera state",
            "timestamped observation capture",
            "LeRobot dataset recorder",
        ],
        "state_feedback_available": False,
        "gripper_control_verified": False,
        "emergency_stop_manual_abort": "TBD on physical robot PC before any motion",
        "sustained_teleoperation_attempted": False,
    }


def _dataset_pipeline(dataset_root: str) -> dict[str, Any]:
    raw_bytes_per_second = 640 * 480 * 3 * 30
    return {
        "status": "PASS",
        "evidence_kind": "INFERRED",
        "dataset_collected": False,
        "dataset_root": dataset_root,
        "episode_structure": (
            "LeRobot-compatible episodes containing synchronized observation, action, "
            "timestamp, task annotation, and episode metadata"
        ),
        "observation_fields": [
            "observation.images.camera",
            "observation.state",
        ],
        "action_fields": ["action"],
        "timestamp_fields": ["timestamp", "frame_index", "episode_index"],
        "task_annotation": "natural-language manipulation instruction per episode",
        "versioning": (
            "immutable dataset version + manifest linked to collection config and git commit"
        ),
        "validation": [
            "schema and required-field checks",
            "monotonic timestamp and observation/action alignment checks",
            "episode completeness and frame-count checks",
            "camera calibration/config revision checks",
            "manual spot review before training",
        ],
        "storage_estimate": {
            "classification": "INFERRED",
            "assumptions": "one uncompressed RGB 640x480 stream at 30 FPS",
            "raw_image_bytes_per_second": raw_bytes_per_second,
            "raw_image_bytes_per_minute": raw_bytes_per_second * 60,
            "note": (
                "Actual encoded dataset size and robot-state overhead must be measured "
                "during the authorized smoke-recording task."
            ),
        },
    }


def _service_boundary() -> dict[str, Any]:
    return {
        "status": "PASS",
        "evidence_kind": "INFERRED",
        "implemented": False,
        "planned_endpoints": ["/health", "/version", "/execute"],
        "required_fields": [
            "schema_version",
            "mission_id",
            "request_id",
            "action_id",
            "skill",
            "instruction",
            "observation_refs",
            "deadline_at",
            "timeout_ms",
            "status",
            "error",
            "component_version",
        ],
        "ownership": {
            "deterministic_runtime": [
                "authorization",
                "timeout",
                "retry budget",
                "reconciliation",
                "idempotency",
                "business recovery",
            ],
            "vla": "bounded approved manipulation policy only",
            "ros_moveit_ros2_control": "validated motion and hardware/controller authority",
        },
    }


def decide_gate(checks: Sequence[dict[str, Any]]) -> tuple[str, bool]:
    blocking_checks = [item for item in checks if item.get("blocking")]
    ready = all(item.get("status") == "PASS" for item in blocking_checks)
    return ("GO", True) if ready else ("NO_GO", False)


def build_evidence(*, skip_camera_capture: bool = False) -> dict[str, Any]:
    cwd = Path.cwd()
    os_release = _os_release()
    dataset_root = os.environ.get("VLA_DATASET_ROOT", DEFAULT_DATASET_ROOT)
    gpu, torch_info = _gpu_and_torch()
    lerobot = _lerobot()
    smolvla = _smolvla(lerobot, gpu)
    robot = _robot()
    camera = _camera(skip_camera_capture)
    teleoperation = _teleoperation()
    dataset_pipeline = _dataset_pipeline(dataset_root)
    service_boundary = _service_boundary()

    checks = [
        {
            "id": "C1",
            "area": "Python",
            "status": "PASS",
            "blocking": False,
            "evidence_kind": "MEASURED",
            "detail": f"{platform.python_implementation()} {platform.python_version()}",
        },
        {
            "id": "C2",
            "area": "GPU",
            "status": gpu["status"],
            "blocking": True,
            "evidence_kind": "MEASURED",
            "detail": (
                "Torch CUDA tensor allocation succeeded"
                if gpu["status"] == "PASS"
                else "No verified CUDA device and tensor-allocation path in this environment"
            ),
        },
        {
            "id": "C3",
            "area": "LeRobot",
            "status": lerobot["status"],
            "blocking": True,
            "evidence_kind": "MEASURED",
            "detail": (
                f"LeRobot {lerobot['version']} and required imports succeeded"
                if lerobot["status"] == "PASS"
                else "LeRobot and required SmolVLA workflow imports are unavailable"
            ),
        },
        {
            "id": "C4",
            "area": "SmolVLA",
            "status": smolvla["status"],
            "blocking": True,
            "evidence_kind": smolvla["evidence_kind"],
            "detail": "Local prerequisites are not ready" if smolvla["status"] != "PASS" else "Local prerequisites pass",
        },
        {
            "id": "C5",
            "area": "Robot I/O",
            "status": robot["status"],
            "blocking": True,
            "evidence_kind": robot["evidence_kind"],
            "detail": robot["environment_interpretation"],
        },
        {
            "id": "C6",
            "area": "Camera",
            "status": camera["status"],
            "blocking": True,
            "evidence_kind": camera["evidence_kind"],
            "detail": camera["capture"]["detail"],
        },
        {
            "id": "C7",
            "area": "Teleoperation",
            "status": teleoperation["status"],
            "blocking": True,
            "evidence_kind": teleoperation["evidence_kind"],
            "detail": "Physical command/state/gripper/stop paths remain unverified",
        },
        {
            "id": "C8",
            "area": "Dataset Pipeline",
            "status": dataset_pipeline["status"],
            "blocking": False,
            "evidence_kind": dataset_pipeline["evidence_kind"],
            "detail": "Design is defined; no Dataset V1 data was collected",
        },
        {
            "id": "C9",
            "area": "Service Boundary",
            "status": service_boundary["status"],
            "blocking": False,
            "evidence_kind": service_boundary["evidence_kind"],
            "detail": "Future typed boundary preserves deterministic and ROS ownership",
        },
        {
            "id": "C10",
            "area": "Training Budget",
            "status": "FAIL",
            "blocking": True,
            "evidence_kind": "NOT AVAILABLE",
            "detail": "No approved local, remote, or cloud CUDA training budget is documented",
        },
    ]
    status, next_task_authorized = decide_gate(checks)

    blockers = [
        {
            "check_id": item["id"],
            "area": item["area"],
            "status": item["status"],
            "detail": item["detail"],
        }
        for item in checks
        if item["blocking"] and item["status"] != "PASS"
    ]
    deferred_checks = [
        {
            "area": "Robot I/O",
            "trigger": "native robot PC and selected manipulator are available for no-motion enumeration",
        },
        {
            "area": "Camera",
            "trigger": "selected camera is attached to the native robot PC for one-frame capture",
        },
        {
            "area": "Teleoperation",
            "trigger": "device identity, workspace limits, operator stop path, and supervised authorization exist",
        },
        {
            "area": "SmolVLA capacity",
            "trigger": "approved CUDA host and pinned isolated LeRobot environment are available",
        },
    ]

    git_commit_result = _run(["git", "rev-parse", "HEAD"])
    git_branch_result = _run(["git", "branch", "--show-current"])
    return {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_ID,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git": {
            "commit": git_commit_result["output"] if git_commit_result["returncode"] == 0 else None,
            "branch": git_branch_result["output"] if git_branch_result["returncode"] == 0 else None,
        },
        "host": {
            "os": os_release.get("PRETTY_NAME", platform.platform()),
            "distribution_id": os_release.get("ID"),
            "distribution_version": os_release.get("VERSION_ID"),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "is_wsl": "microsoft" in platform.release().lower() or "wsl" in platform.release().lower(),
            "logical_cpu_count": os.cpu_count(),
            "memory": _memory(),
            "disk": _disk(cwd),
            "environment_variables": _environment_variables(),
        },
        "python": _python_environment(),
        "gpu": gpu,
        "torch": torch_info,
        "lerobot": lerobot,
        "smolvla": smolvla,
        "robot": robot,
        "camera": camera,
        "teleoperation": teleoperation,
        "dataset_pipeline": dataset_pipeline,
        "service_boundary": service_boundary,
        "training_budget": {
            "status": "FAIL",
            "evidence_kind": "NOT AVAILABLE",
            "approved": False,
            "provider": None,
            "limit": None,
        },
        "checks": checks,
        "blockers": blockers,
        "deferred_checks": deferred_checks,
        "next_task": "TASK-W1-001",
        "next_task_authorized": next_task_authorized,
        "safety": {
            "robot_commands_sent": False,
            "actuators_opened": False,
            "training_started": False,
            "model_downloaded": False,
            "dataset_v1_collected": False,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/phase0/P0-004_vla_readiness.json"),
        help="JSON evidence destination",
    )
    parser.add_argument(
        "--skip-camera-capture",
        action="store_true",
        help="Enumerate video devices without opening one (intended for unit tests only)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    evidence = build_evidence(skip_camera_capture=args.skip_camera_capture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    print(f"{TASK_ID} VLA readiness verification")
    for item in evidence["checks"]:
        print(f"{item['status']:<8} {item['area']}: {item['detail']}")
    print(f"Final gate: {evidence['status']}")
    print(f"TASK-W1-001 authorized: {evidence['next_task_authorized']}")
    print(f"Evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
