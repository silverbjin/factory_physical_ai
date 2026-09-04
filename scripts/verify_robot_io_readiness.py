#!/usr/bin/env python3
"""Verify TASK-P0-006 robot/camera I/O readiness without commanding motion.

The verifier only enumerates filesystem device metadata, checks access bits,
optionally reads an explicitly declared regular-file state snapshot, and reads
a bounded number of frames from an explicitly selected camera. It never opens
a serial/controller device, imports a vendor robot SDK, or sends robot,
gripper, trajectory, or teleoperation commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import platform
import queue as queue_module
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


TASK_ID = "TASK-P0-006"
SCHEMA_VERSION = "1.0"
VERIFIER_VERSION = "1.1.0"
READY = "DEVICE_IO_READY"
BLOCKED = "DEVICE_IO_BLOCKED"
EXPECTED_P0_005_SHA256 = (
    "aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae"
)
PROVENANCE = {
    "MEASURED",
    "DECLARED_INPUT",
    "DERIVED",
    "DOCUMENTED",
    "NOT_VERIFIED",
}
CHECK_STATUSES = {"PASS", "BLOCKED", "NOT_VERIFIED", "NOT_APPLICABLE"}
MAX_DIAGNOSTIC_BYTES = 4096
MAX_CAMERA_FRAMES = 5
DEFAULT_DEVICE_DISCOVERY_TIMEOUT_SECONDS = 5.0
RESULT_QUEUE_TIMEOUT_SECONDS = 1.0

EXPECTED_CHECKS = (
    ("C01", "Target hardware selected"),
    ("C02", "Robot/controller physically discoverable"),
    ("C03", "Stable device identity available"),
    ("C04", "Required host permission/access available"),
    ("C05", "Robot state-feedback path identified"),
    ("C06", "Robot state observable without motion"),
    ("C07", "Future actuator command path identified"),
    ("C08", "Future gripper path identified or not applicable"),
    ("C09", "Camera selected"),
    ("C10", "Camera physically discoverable"),
    ("C11", "Bounded camera frame acquisition succeeds"),
    ("C12", "Camera configuration recorded"),
    ("C13", "Workspace/motion constraints documented"),
    ("C14", "Manual abort/E-stop path documented"),
    ("C15", "Supervised teleoperation prerequisites classified"),
    ("C16", "No physical motion occurred"),
    ("C17", "No Week 1/dataset/model work occurred"),
    ("C18", "Evidence and documentation internally consistent"),
)
BOUND_SOURCE_PATHS = (
    "scripts/verify_robot_io_readiness.py",
    "tests/test_verify_robot_io_readiness.py",
    "docs/hardware/robot_camera_io_readiness_v1.md",
    "plans/robot_camera_io_risks.md",
)

AccessChecker = Callable[[Path, int], bool]
CameraProbe = Callable[[Path, int, float], dict[str, Any]]
StateProbe = Callable[[Path, float], dict[str, Any]]


def _bounded(value: str, limit: int = MAX_DIAGNOSTIC_BYTES) -> str:
    return value.strip()[:limit]


def _run(
    command: Sequence[str], *, timeout_seconds: float = 5.0, cwd: Path | None = None
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

    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}" if output else completed.stderr
    return {
        "available": True,
        "returncode": completed.returncode,
        "timed_out": False,
        "output": _bounded(output),
    }


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values


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
    """Bind evidence content without creating a self-referential hash."""

    normalized = json.loads(json.dumps(evidence))
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
        relative_path: _sha256(repository_root / relative_path)
        for relative_path in BOUND_SOURCE_PATHS
    }


def _load_declarations(path: Path | None) -> tuple[dict[str, Any], list[str], str | None]:
    if path is None:
        return {}, ["operator declaration file was not supplied"], None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"declaration load failed: {type(exc).__name__}: {exc}"], str(path)
    if not isinstance(value, dict):
        return {}, ["declaration root must be a JSON object"], str(path)
    return value, [], str(path)


def _required_text(mapping: Mapping[str, Any], field: str, errors: list[str], prefix: str) -> str | None:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}.{field} must be a non-empty string")
        return None
    return value.strip()


def _required_list(mapping: Mapping[str, Any], field: str, errors: list[str], prefix: str) -> list[Any]:
    value = mapping.get(field)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{field} must be a non-empty list")
        return []
    return value


def _validate_declarations(declarations: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    target = declarations.get("target_hardware")
    if not isinstance(target, dict):
        errors.append("target_hardware must be an object")
    else:
        for field in (
            "manufacturer",
            "model",
            "controller",
            "connection_type",
            "robot_device_path",
            "stable_device_path",
        ):
            _required_text(target, field, errors, "target_hardware")
        _required_list(target, "documentation_refs", errors, "target_hardware")
        if not isinstance(target.get("gripper_present"), bool):
            errors.append("target_hardware.gripper_present must be boolean")

    interfaces = declarations.get("interfaces")
    if not isinstance(interfaces, dict):
        errors.append("interfaces must be an object")
    else:
        for name in ("state", "command"):
            item = interfaces.get(name)
            if not isinstance(item, dict):
                errors.append(f"interfaces.{name} must be an object")
                continue
            _required_text(item, "interface", errors, f"interfaces.{name}")
            _required_text(item, "documentation_ref", errors, f"interfaces.{name}")
        state = interfaces.get("state")
        if isinstance(state, dict):
            observation = state.get("observation")
            if not isinstance(observation, dict):
                errors.append("interfaces.state.observation must be an object")
            else:
                if observation.get("kind") != "regular_file_snapshot":
                    errors.append(
                        "interfaces.state.observation.kind must be regular_file_snapshot"
                    )
                _required_text(
                    observation, "path", errors, "interfaces.state.observation"
                )
                if observation.get("safe_read_only") is not True:
                    errors.append(
                        "interfaces.state.observation.safe_read_only must be true"
                    )
        if isinstance(target, dict) and target.get("gripper_present") is True:
            gripper = interfaces.get("gripper")
            if not isinstance(gripper, dict):
                errors.append("interfaces.gripper must be an object when a gripper is present")
            else:
                _required_text(gripper, "interface", errors, "interfaces.gripper")
                _required_text(
                    gripper, "documentation_ref", errors, "interfaces.gripper"
                )

    camera = declarations.get("camera")
    if not isinstance(camera, dict):
        errors.append("camera must be an object")
    else:
        for field in ("manufacturer", "model", "device_path", "stable_device_path"):
            _required_text(camera, field, errors, "camera")
        _required_list(camera, "documentation_refs", errors, "camera")
        for field in ("width", "height"):
            value = camera.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(f"camera.{field} must be a positive integer")
        _required_text(camera, "pixel_format", errors, "camera")

    workspace = declarations.get("workspace")
    if not isinstance(workspace, dict):
        errors.append("workspace must be an object")
    else:
        for field in (
            "description",
            "joint_or_cartesian_limits",
            "prohibited_zones",
            "initial_pose_assumptions",
            "gripper_constraints",
        ):
            if field not in workspace or workspace[field] in (None, "", [], {}):
                errors.append(f"workspace.{field} must be documented")
        _required_list(workspace, "source_refs", errors, "workspace")
        if workspace.get("source_kind") not in {"DOCUMENTED", "DECLARED_INPUT"}:
            errors.append("workspace.source_kind must be DOCUMENTED or DECLARED_INPUT")
        if workspace.get("operator_supervision_required") is not True:
            errors.append("workspace.operator_supervision_required must be true")

    abort = declarations.get("abort")
    if not isinstance(abort, dict):
        errors.append("abort must be an object")
    else:
        if abort.get("availability") not in {
            "AVAILABLE",
            "DOCUMENTED_ONLY",
            "NOT_VERIFIED",
            "UNAVAILABLE",
        }:
            errors.append("abort.availability has an unsupported value")
        for field in (
            "hardware_estop",
            "controller_disable_method",
            "manual_operator_action",
            "operator_location",
        ):
            _required_text(abort, field, errors, "abort")
        if abort.get("motion_tested") is not False:
            errors.append("abort.motion_tested must be false for TASK-P0-006")
    return errors


def _is_within(path: Path, root: Path) -> bool:
    try:
        Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root)))
    except ValueError:
        return False
    return True


def _validate_declared_device_paths(
    declarations: Mapping[str, Any], dev_root: Path
) -> list[str]:
    """Reject declarations that could make a device probe escape its safe roots."""

    errors: list[str] = []
    target = declarations.get("target_hardware")
    if isinstance(target, dict):
        robot_path = target.get("robot_device_path")
        stable_path = target.get("stable_device_path")
        if isinstance(robot_path, str) and robot_path.strip():
            path = Path(robot_path)
            if not _is_within(path, dev_root) or not path.name.startswith(
                ("ttyUSB", "ttyACM")
            ):
                errors.append(
                    "target_hardware.robot_device_path must be a ttyUSB*/ttyACM* path under dev_root"
                )
        if isinstance(stable_path, str) and stable_path.strip():
            if not _is_within(Path(stable_path), dev_root / "serial" / "by-id"):
                errors.append(
                    "target_hardware.stable_device_path must be under dev_root/serial/by-id"
                )

    camera = declarations.get("camera")
    if isinstance(camera, dict):
        camera_path = camera.get("device_path")
        stable_path = camera.get("stable_device_path")
        if isinstance(camera_path, str) and camera_path.strip():
            path = Path(camera_path)
            if not _is_within(path, dev_root) or not path.name.startswith("video"):
                errors.append(
                    "camera.device_path must be a video* path under dev_root"
                )
        if isinstance(stable_path, str) and stable_path.strip():
            if not _is_within(Path(stable_path), dev_root / "v4l" / "by-id"):
                errors.append(
                    "camera.stable_device_path must be under dev_root/v4l/by-id"
                )
    return errors


def _path_metadata(path: Path, access_checker: AccessChecker) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "is_symlink": path.is_symlink(),
        "resolved_path": None,
        "mode": None,
        "uid": None,
        "gid": None,
        "readable": False,
        "writable": False,
    }
    try:
        path_stat = path.stat()
    except OSError as exc:
        result["error"] = _bounded(f"{type(exc).__name__}: {exc}")
        return result
    result.update(
        {
            "exists": True,
            "resolved_path": str(path.resolve()),
            "mode": stat.filemode(path_stat.st_mode),
            "uid": path_stat.st_uid,
            "gid": path_stat.st_gid,
            "readable": access_checker(path, os.R_OK),
            "writable": access_checker(path, os.W_OK),
        }
    )
    return result


def _enumerate_paths(dev_root: Path, access_checker: AccessChecker) -> dict[str, Any]:
    robot_paths = sorted(
        {path for pattern in ("ttyUSB*", "ttyACM*") for path in dev_root.glob(pattern)},
        key=str,
    )
    camera_paths = sorted(dev_root.glob("video*"), key=str)
    serial_by_id = sorted((dev_root / "serial" / "by-id").glob("*"), key=str)
    video_by_id = sorted((dev_root / "v4l" / "by-id").glob("*"), key=str)
    return {
        "status": "PASS",
        "provenance": "MEASURED",
        "device_root": str(dev_root),
        "robot_candidates": [_path_metadata(path, access_checker) for path in robot_paths],
        "camera_candidates": [_path_metadata(path, access_checker) for path in camera_paths],
        "serial_stable_identities": [
            _path_metadata(path, access_checker) for path in serial_by_id
        ],
        "camera_stable_identities": [
            _path_metadata(path, access_checker) for path in video_by_id
        ],
    }


def _device_discovery_worker(
    dev_root: str, access_checker: AccessChecker, queue: Any
) -> None:
    try:
        queue.put(_enumerate_paths(Path(dev_root), access_checker))
    except Exception as exc:
        queue.put(
            {
                "status": "BLOCKED",
                "provenance": "MEASURED",
                "device_root": dev_root,
                "robot_candidates": [],
                "camera_candidates": [],
                "serial_stable_identities": [],
                "camera_stable_identities": [],
                "detail": _bounded(f"{type(exc).__name__}: {exc}"),
            }
        )


def _bounded_device_discovery(
    dev_root: Path, access_checker: AccessChecker, timeout_seconds: float
) -> dict[str, Any]:
    """Enumerate fixed device patterns in a process with a hard wall-clock bound."""

    context = multiprocessing.get_context("fork")
    queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_device_discovery_worker,
        args=(str(dev_root), access_checker, queue),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        if process.is_alive():
            process.kill()
            process.join(1.0)
        return {
            "status": "BLOCKED",
            "provenance": "MEASURED",
            "device_root": str(dev_root),
            "robot_candidates": [],
            "camera_candidates": [],
            "serial_stable_identities": [],
            "camera_stable_identities": [],
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
            "detail": f"device discovery exceeded {timeout_seconds:.3f}s timeout",
        }
    try:
        result = queue.get(timeout=0.1)
    except queue_module.Empty:
        result = {
            "status": "BLOCKED",
            "provenance": "MEASURED",
            "device_root": str(dev_root),
            "robot_candidates": [],
            "camera_candidates": [],
            "serial_stable_identities": [],
            "camera_stable_identities": [],
            "detail": f"device discovery exited without a diagnostic (exitcode={process.exitcode})",
        }
    result["timed_out"] = False
    result["timeout_seconds"] = timeout_seconds
    return result


def _state_worker(path: str, result_queue: Any) -> None:
    try:
        state_path = Path(path)
        mode = state_path.stat().st_mode
        if not stat.S_ISREG(mode):
            result_queue.put(
                {
                    "status": "BLOCKED",
                    "bytes_read": 0,
                    "snapshot_sha256": None,
                    "detail": (
                        "state observation path is not a regular file; "
                        "it was not opened"
                    ),
                }
            )
            return
        with state_path.open("rb") as handle:
            value = handle.read(MAX_DIAGNOSTIC_BYTES)
        result_queue.put(
            {
                "status": "PASS",
                "bytes_read": len(value),
                "snapshot_sha256": hashlib.sha256(value).hexdigest(),
                "detail": "bounded regular-file state snapshot read",
            }
        )
    except Exception as exc:
        result_queue.put(
            {
                "status": "BLOCKED",
                "bytes_read": 0,
                "snapshot_sha256": None,
                "detail": _bounded(f"{type(exc).__name__}: {exc}"),
            }
        )


def _terminate_process(process: Any) -> None:
    """Boundedly stop and reap a probe process."""

    if not process.is_alive():
        return
    process.terminate()
    process.join(1.0)
    if process.is_alive():
        process.kill()
        process.join(1.0)


def _close_process_queue(process: Any, result_queue: Any) -> None:
    """Release process and Queue resources after a bounded probe."""

    _terminate_process(process)
    try:
        process.close()
    finally:
        result_queue.close()
        result_queue.join_thread()


def _bounded_state_probe(path: Path, timeout_seconds: float) -> dict[str, Any]:
    """Bound metadata inspection, regular-file validation, and the state read."""

    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_state_worker, args=(str(path), result_queue))
    process.start()
    try:
        process.join(timeout_seconds)
        if process.is_alive():
            _terminate_process(process)
            return {
                "status": "BLOCKED",
                "timed_out": True,
                "detail": (
                    "state metadata/read probe exceeded "
                    f"{timeout_seconds:.3f}s timeout"
                ),
            }
        exitcode = process.exitcode
        try:
            result = result_queue.get(timeout=RESULT_QUEUE_TIMEOUT_SECONDS)
        except queue_module.Empty:
            return {
                "status": "BLOCKED",
                "timed_out": False,
                "detail": (
                    "state probe exited without a diagnostic "
                    f"(exitcode={exitcode})"
                ),
            }
        result["timed_out"] = False
        return result
    finally:
        _close_process_queue(process, result_queue)


def _camera_worker(path: str, frame_count: int, queue: Any) -> None:
    camera = None
    started = time.monotonic()
    try:
        import cv2  # imported only inside the bounded camera worker

        camera = cv2.VideoCapture(path)
        if not camera.isOpened():
            raise RuntimeError("selected camera could not be opened")
        frames = []
        for _ in range(frame_count):
            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError("bounded camera frame read failed")
            frames.append(frame)
        elapsed = time.monotonic() - started
        last = frames[-1]
        fourcc_value = int(camera.get(cv2.CAP_PROP_FOURCC))
        fourcc = "".join(chr((fourcc_value >> (8 * index)) & 0xFF) for index in range(4))
        queue.put(
            {
                "status": "PASS",
                "opened": True,
                "frames_requested": frame_count,
                "frames_acquired": len(frames),
                "width": int(last.shape[1]),
                "height": int(last.shape[0]),
                "channels": int(last.shape[2]) if len(last.shape) > 2 else 1,
                "pixel_format": fourcc.strip("\\x00") or None,
                "driver_reported_fps": float(camera.get(cv2.CAP_PROP_FPS)),
                "acquisition_elapsed_seconds": round(elapsed, 6),
                "diagnostic_observed_fps": round(len(frames) / elapsed, 3)
                if elapsed > 0
                else None,
                "frames_persisted": 0,
                "detail": "bounded frame acquisition succeeded; frames were not persisted",
            }
        )
    except Exception as exc:
        queue.put(
            {
                "status": "BLOCKED",
                "opened": False,
                "frames_requested": frame_count,
                "frames_acquired": 0,
                "frames_persisted": 0,
                "detail": _bounded(f"{type(exc).__name__}: {exc}"),
            }
        )
    finally:
        if camera is not None:
            camera.release()


def _bounded_camera_probe(
    path: Path, frame_count: int, timeout_seconds: float
) -> dict[str, Any]:
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_camera_worker, args=(str(path), frame_count, result_queue)
    )
    process.start()
    try:
        process.join(timeout_seconds)
        if process.is_alive():
            _terminate_process(process)
            return {
                "status": "BLOCKED",
                "opened": False,
                "frames_requested": frame_count,
                "frames_acquired": 0,
                "frames_persisted": 0,
                "timed_out": True,
                "detail": f"camera probe exceeded {timeout_seconds:.3f}s timeout",
            }
        exitcode = process.exitcode
        try:
            result = result_queue.get(timeout=RESULT_QUEUE_TIMEOUT_SECONDS)
        except queue_module.Empty:
            return {
                "status": "BLOCKED",
                "opened": False,
                "frames_requested": frame_count,
                "frames_acquired": 0,
                "frames_persisted": 0,
                "timed_out": False,
                "detail": (
                    "camera probe exited without a diagnostic "
                    f"(exitcode={exitcode})"
                ),
            }
        result["timed_out"] = False
        return result
    finally:
        _close_process_queue(process, result_queue)


def _check(check_id: str, area: str, status: str, provenance: str, detail: str) -> dict[str, Any]:
    if status not in CHECK_STATUSES:
        raise ValueError(f"invalid check status: {status}")
    if provenance not in PROVENANCE:
        raise ValueError(f"invalid provenance: {provenance}")
    return {
        "id": check_id,
        "area": area,
        "status": status,
        "mandatory": True,
        "provenance": provenance,
        "detail": detail,
    }


def decide_readiness(checks: Sequence[Mapping[str, Any]]) -> str:
    if len(checks) != len(EXPECTED_CHECKS):
        return BLOCKED
    if any(
        not isinstance(item, Mapping)
        or item.get("id") != expected_id
        or item.get("area") != expected_area
        or item.get("mandatory") is not True
        or item.get("status") != "PASS"
        for item, (expected_id, expected_area) in zip(checks, EXPECTED_CHECKS)
    ):
        return BLOCKED
    return READY


def _declared_section(
    declarations: Mapping[str, Any], name: str
) -> dict[str, Any]:
    value = declarations.get(name)
    return dict(value) if isinstance(value, dict) else {}


def _metadata_for_path(
    discovery: Mapping[str, Any], group: str, path: Path
) -> dict[str, Any] | None:
    values = discovery.get(group)
    if not isinstance(values, list):
        return None
    target = str(path)
    return next(
        (dict(item) for item in values if isinstance(item, dict) and item.get("path") == target),
        None,
    )


def _section_valid(errors: Sequence[str], *prefixes: str) -> bool:
    known_prefixes = (
        "target_hardware",
        "interfaces",
        "camera",
        "workspace",
        "abort",
    )
    if any(not error.startswith(known_prefixes) for error in errors):
        return False
    return not any(error.startswith(prefixes) for error in errors)


def _material_consistency_errors(evidence: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    checks = evidence.get("checks")
    if not isinstance(checks, list):
        return ["checks must be a list"]
    ids = [item.get("id") for item in checks if isinstance(item, dict)]
    expected_ids = [f"C{index:02d}" for index in range(1, 18)]
    if ids != expected_ids:
        errors.append("C01-C17 checks must exist once and in order before C18")
    if evidence.get("task_w1_001_authorized") is not False:
        errors.append("TASK-W1-001 authorization invariant violated")
    if evidence.get("p0_004r_required") is not True:
        errors.append("TASK-P0-004R invariant violated")
    safety = evidence.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(field) is not False
        for field in (
            "robot_motion_commanded",
            "joint_motion_commanded",
            "gripper_motion_commanded",
            "trajectory_execution_commanded",
            "teleoperation_motion_commanded",
            "dataset_work_started",
            "model_work_started",
            "integration_work_started",
        )
    ):
        errors.append("one or more non-motion/scope safety flags are not false")
    p0 = evidence.get("prerequisites", {}).get("p0_005", {})
    if p0.get("accepted") is not True or p0.get("evidence_hash_match") is not True:
        errors.append("accepted P0-005 prerequisite is not intact")
    return errors


def collect_evidence(
    repository_root: Path,
    *,
    declarations: Mapping[str, Any] | None = None,
    declaration_source: str | None = None,
    declaration_errors: Sequence[str] = (),
    dev_root: Path = Path("/dev"),
    camera_timeout_seconds: float = 5.0,
    state_timeout_seconds: float = 2.0,
    device_discovery_timeout_seconds: float = DEFAULT_DEVICE_DISCOVERY_TIMEOUT_SECONDS,
    camera_frame_count: int = 1,
    camera_probe: CameraProbe | None = None,
    state_probe: StateProbe | None = None,
    access_checker: AccessChecker = os.access,
) -> dict[str, Any]:
    """Collect non-motion evidence. Injection points exist only for deterministic tests."""

    declarations = dict(declarations or {})
    errors = list(declaration_errors) + _validate_declarations(declarations)
    errors.extend(_validate_declared_device_paths(declarations, dev_root))
    discovery = _bounded_device_discovery(
        dev_root, access_checker, device_discovery_timeout_seconds
    )
    target = _declared_section(declarations, "target_hardware")
    interfaces = _declared_section(declarations, "interfaces")
    camera = _declared_section(declarations, "camera")
    workspace = _declared_section(declarations, "workspace")
    abort = _declared_section(declarations, "abort")

    p0_path = repository_root / "results" / "phase0" / "P0-005_vla_runtime.json"
    p0_hash = _sha256(p0_path)
    p0_history = repository_root / "docs" / "task_history" / "TASK-P0-005" / "02_review.md"
    p0_review_text = ""
    try:
        p0_review_text = p0_history.read_text(encoding="utf-8")
    except OSError:
        pass
    p0_accepted = "`ACCEPT TASK-P0-005`" in p0_review_text
    p0_intact = p0_hash == EXPECTED_P0_005_SHA256

    target_valid = bool(target) and _section_valid(errors, "target_hardware")
    camera_valid = bool(camera) and _section_valid(errors, "camera")
    workspace_valid = bool(workspace) and _section_valid(errors, "workspace")
    abort_valid = bool(abort) and _section_valid(errors, "abort")
    robot_path = Path(str(target.get("robot_device_path", ""))) if target_valid else Path("")
    stable_robot_path = Path(str(target.get("stable_device_path", ""))) if target_valid else Path("")
    robot_meta = (
        _metadata_for_path(discovery, "robot_candidates", robot_path)
        if target_valid
        else None
    )
    stable_robot_meta = (
        _metadata_for_path(discovery, "serial_stable_identities", stable_robot_path)
        if target_valid
        else None
    )
    robot_discovered = bool(
        discovery.get("status") == "PASS" and robot_meta and robot_meta["exists"]
    )
    stable_robot = bool(
        target_valid
        and robot_discovered
        and stable_robot_meta
        and stable_robot_meta["exists"]
        and stable_robot_meta.get("is_symlink") is True
        and stable_robot_meta.get("resolved_path") == robot_meta.get("resolved_path")
    )
    robot_access = bool(
        robot_meta and robot_meta["readable"] and robot_meta["writable"]
    )

    state = interfaces.get("state") if isinstance(interfaces.get("state"), dict) else {}
    observation = state.get("observation") if isinstance(state, dict) else {}
    state_path = Path(str(observation.get("path", ""))) if observation else Path("")
    state_observation: dict[str, Any] = {
        "status": "NOT_VERIFIED",
        "provenance": "NOT_VERIFIED",
        "attempted": False,
        "timed_out": False,
        "detail": "no explicitly safe regular-file state observation was declared",
    }
    state_valid = bool(state) and _section_valid(errors, "interfaces.state")
    if (
        state_valid
        and observation.get("kind") == "regular_file_snapshot"
        and observation.get("safe_read_only") is True
    ):
        probe = state_probe or _bounded_state_probe
        state_observation = probe(state_path, state_timeout_seconds)
        state_observation.update(
            {
                "provenance": "MEASURED",
                "attempted": True,
                "path": str(state_path),
                "timeout_seconds": state_timeout_seconds,
                "read_limit_bytes": MAX_DIAGNOSTIC_BYTES,
            }
        )

    camera_path = Path(str(camera.get("device_path", ""))) if camera_valid else Path("")
    stable_camera_path = Path(str(camera.get("stable_device_path", ""))) if camera_valid else Path("")
    camera_meta = (
        _metadata_for_path(discovery, "camera_candidates", camera_path)
        if camera_valid
        else None
    )
    stable_camera_meta = (
        _metadata_for_path(discovery, "camera_stable_identities", stable_camera_path)
        if camera_valid
        else None
    )
    camera_discovered = bool(
        discovery.get("status") == "PASS" and camera_meta and camera_meta["exists"]
    )
    stable_camera = bool(
        camera_valid
        and camera_discovered
        and stable_camera_meta
        and stable_camera_meta["exists"]
        and stable_camera_meta.get("is_symlink") is True
        and stable_camera_meta.get("resolved_path") == camera_meta.get("resolved_path")
    )
    camera_readable = bool(camera_meta and camera_meta["readable"])
    acquisition: dict[str, Any] = {
        "status": "NOT_VERIFIED",
        "provenance": "NOT_VERIFIED",
        "attempted": False,
        "timed_out": False,
        "frames_requested": camera_frame_count,
        "frames_acquired": 0,
        "frames_persisted": 0,
        "detail": "selected camera is not safely available for bounded acquisition",
    }
    if camera_valid and camera_discovered and camera_readable:
        probe = camera_probe or _bounded_camera_probe
        acquisition = probe(camera_path, camera_frame_count, camera_timeout_seconds)
        acquisition.update(
            {
                "provenance": "MEASURED",
                "attempted": True,
                "device_path": str(camera_path),
                "timeout_seconds": camera_timeout_seconds,
            }
        )

    target_selected = target_valid
    state_path_identified = bool(
        state_valid and state.get("interface") and state.get("documentation_ref")
    )
    command = interfaces.get("command") if isinstance(interfaces.get("command"), dict) else {}
    command_identified = bool(
        _section_valid(errors, "interfaces.command")
        and command.get("interface")
        and command.get("documentation_ref")
    )
    gripper_present = target.get("gripper_present") if target else None
    gripper = interfaces.get("gripper") if isinstance(interfaces.get("gripper"), dict) else {}
    gripper_identified = target_valid and (
        gripper_present is False
        or bool(
            _section_valid(errors, "interfaces.gripper")
            and gripper.get("interface")
            and gripper.get("documentation_ref")
        )
    )
    camera_selected = camera_valid
    state_observed = bool(
        state_observation.get("status") == "PASS"
        and state_observation.get("attempted") is True
        and state_observation.get("timed_out") is False
        and isinstance(state_observation.get("bytes_read"), int)
        and state_observation.get("bytes_read", 0) > 0
        and isinstance(state_observation.get("snapshot_sha256"), str)
        and len(state_observation["snapshot_sha256"]) == 64
    )
    camera_acquired = bool(
        acquisition.get("status") == "PASS"
        and acquisition.get("attempted") is True
        and acquisition.get("timed_out") is False
        and acquisition.get("opened") is True
        and acquisition.get("frames_requested") == camera_frame_count
        and acquisition.get("frames_acquired") == camera_frame_count
        and acquisition.get("frames_persisted") == 0
    )
    camera_configuration_recorded = bool(
        camera.get("width")
        and camera.get("height")
        and camera.get("pixel_format")
        and isinstance(acquisition.get("width"), int)
        and acquisition.get("width", 0) > 0
        and isinstance(acquisition.get("height"), int)
        and acquisition.get("height", 0) > 0
    )
    workspace_documented = workspace_valid
    abort_documented = abort_valid and abort.get("availability") in {
        "AVAILABLE",
        "DOCUMENTED_ONLY",
    }

    checks = [
        _check("C01", "Target hardware selected", "PASS" if target_selected else "BLOCKED", "DECLARED_INPUT" if target_selected else "NOT_VERIFIED", "operator declaration identifies one target" if target_selected else "target selection is unresolved"),
        _check("C02", "Robot/controller physically discoverable", "PASS" if robot_discovered else ("BLOCKED" if target_valid else "NOT_VERIFIED"), "MEASURED" if target_valid else "NOT_VERIFIED", "selected robot device exists" if robot_discovered else ("selected robot/controller device was not discovered" if target_valid else "target robot/controller is not selected")),
        _check("C03", "Stable device identity available", "PASS" if stable_robot else ("BLOCKED" if target_valid else "NOT_VERIFIED"), "MEASURED" if target_valid else "NOT_VERIFIED", "stable by-id symlink resolves to selected robot device" if stable_robot else ("no matching stable robot device identity" if target_valid else "stable identity cannot be evaluated before target selection")),
        _check("C04", "Required host permission/access available", "PASS" if robot_access else ("BLOCKED" if target_valid else "NOT_VERIFIED"), "MEASURED" if target_valid else "NOT_VERIFIED", "read/write access check passes without changing permissions" if robot_access else ("required robot device access is unavailable" if target_valid else "device access cannot be evaluated before target selection")),
        _check("C05", "Robot state-feedback path identified", "PASS" if state_path_identified else "BLOCKED", "DECLARED_INPUT" if state_path_identified else "NOT_VERIFIED", "operator declared a state interface and documentation reference" if state_path_identified else "credible state-feedback interface is not identified"),
        _check("C06", "Robot state observable without motion", "PASS" if state_observed else ("BLOCKED" if state_observation.get("attempted") else "NOT_VERIFIED"), "MEASURED" if state_observation.get("attempted") else "NOT_VERIFIED", state_observation["detail"]),
        _check("C07", "Future actuator command path identified", "PASS" if command_identified else "BLOCKED", "DECLARED_INPUT" if command_identified else "NOT_VERIFIED", "operator declared a future command interface; no call executed" if command_identified else "future command path is not identified"),
        _check("C08", "Future gripper path identified or not applicable", "PASS" if gripper_identified else "BLOCKED", "DECLARED_INPUT" if gripper_identified else "NOT_VERIFIED", "operator declared a gripper interface without actuation" if gripper_present is True and gripper_identified else ("selected target declares no gripper" if gripper_present is False else "gripper applicability/path is unresolved")),
        _check("C09", "Camera selected", "PASS" if camera_selected else "BLOCKED", "DECLARED_INPUT" if camera_selected else "NOT_VERIFIED", "operator declaration identifies one camera" if camera_selected else "camera selection is unresolved"),
        _check("C10", "Camera physically discoverable", "PASS" if camera_discovered and stable_camera else ("BLOCKED" if camera_valid else "NOT_VERIFIED"), "MEASURED" if camera_valid else "NOT_VERIFIED", "selected camera and stable identity were discovered" if camera_discovered and stable_camera else ("selected camera/stable identity was not discovered" if camera_valid else "camera is not selected")),
        _check("C11", "Bounded camera frame acquisition succeeds", "PASS" if camera_acquired else ("BLOCKED" if acquisition.get("attempted") else "NOT_VERIFIED"), "MEASURED" if acquisition.get("attempted") else "NOT_VERIFIED", acquisition["detail"]),
        _check("C12", "Camera configuration recorded", "PASS" if camera_configuration_recorded and camera_acquired else ("BLOCKED" if acquisition.get("attempted") else "NOT_VERIFIED"), "DERIVED" if camera_configuration_recorded and camera_acquired else "NOT_VERIFIED", "declared configuration and measured acquisition properties recorded" if camera_configuration_recorded and camera_acquired else "camera configuration/acquisition result is incomplete"),
        _check("C13", "Workspace/motion constraints documented", "PASS" if workspace_documented else "BLOCKED", "DECLARED_INPUT" if workspace_documented else "NOT_VERIFIED", "operator declared workspace, limits, prohibited zones, initial pose, gripper constraints, source references, and supervision" if workspace_documented else "workspace/safety constraints are incomplete"),
        _check("C14", "Manual abort/E-stop path documented", "PASS" if abort_documented else "BLOCKED", "DECLARED_INPUT" if abort_documented else "NOT_VERIFIED", f"abort availability classified {abort.get('availability')}; not tested under motion" if abort_documented else "manual abort/E-stop strategy is unavailable or not verified"),
    ]
    teleoperation_ready = all(item["status"] == "PASS" for item in checks[:14])
    checks.extend(
        [
            _check("C15", "Supervised teleoperation prerequisites classified", "PASS" if teleoperation_ready else "BLOCKED", "DERIVED", "all prerequisites are present; teleoperation remains unimplemented and unauthorized" if teleoperation_ready else "one or more prerequisites are blocked; teleoperation remains unauthorized"),
            _check("C16", "No physical motion occurred", "PASS", "DERIVED", "verifier contains no robot/gripper/trajectory/teleoperation command path"),
            _check("C17", "No Week 1/dataset/model work occurred", "PASS", "DERIVED", "verifier performed readiness diagnostics only"),
        ]
    )

    release = _os_release()
    verifier_path = Path(__file__).resolve()
    verifier_sha256 = _sha256(verifier_path)
    git_facts = _git(repository_root)
    source_hashes = _bound_source_hashes(repository_root)
    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_ID,
        "verifier": {
            "version": VERIFIER_VERSION,
            "path": str(verifier_path),
            "sha256": verifier_sha256,
            "provenance": "MEASURED",
        },
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git": git_facts,
        "content_binding": {
            "provenance": "DERIVED",
            "generation_mode": (
                "COMMITTED_TREE"
                if git_facts["working_tree_clean"]
                else "PRE_COMMIT_WORKTREE"
            ),
            "git_head_at_generation": git_facts["commit"],
            "working_tree_dirty_at_generation": not git_facts["working_tree_clean"],
            "verifier_sha256": verifier_sha256,
            "source_sha256": source_hashes,
            "evidence_payload_hash_scope": (
                "canonical JSON with content_binding.evidence_payload_sha256 omitted"
            ),
            "evidence_payload_sha256": None,
            "claim": (
                "Git HEAD identifies the base commit at generation; when generation_mode "
                "is PRE_COMMIT_WORKTREE, source hashes bind the uncommitted implementation "
                "and do not claim provenance from a later commit."
            ),
        },
        "host": {
            "provenance": "MEASURED",
            "hostname": platform.node(),
            "os": release.get("PRETTY_NAME", platform.platform()),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "is_wsl": "microsoft" in platform.release().lower() or "wsl" in platform.release().lower(),
            "uid": os.getuid(),
            "gid": os.getgid(),
            "groups": os.getgroups(),
            "python": platform.python_version(),
        },
        "prerequisites": {
            "p0_005": {
                "provenance": "MEASURED",
                "accepted": p0_accepted,
                "evidence_path": str(p0_path),
                "expected_sha256": EXPECTED_P0_005_SHA256,
                "measured_sha256": p0_hash,
                "evidence_hash_match": p0_intact,
            },
            "task_w1_001_authorized": False,
            "p0_004r_required": True,
        },
        "declarations": {
            "provenance": "DECLARED_INPUT" if declarations else "NOT_VERIFIED",
            "source": declaration_source,
            "errors": errors,
        },
        "target_hardware": {
            "provenance": "DECLARED_INPUT" if target else "NOT_VERIFIED",
            "selected": target_selected,
            "details": target if target else None,
        },
        "device_discovery": discovery,
        "robot_device": {
            "provenance": "MEASURED" if target_valid else "NOT_VERIFIED",
            "selected_path": str(robot_path) if target_valid else None,
            "selected_metadata": robot_meta,
            "stable_identity_path": str(stable_robot_path) if target_valid else None,
            "stable_identity_metadata": stable_robot_meta,
            "physically_discoverable": robot_discovered,
            "stable_identity_available": stable_robot,
            "required_access_available": robot_access,
            "permissions_changed": False,
            "serial_or_controller_opened": False,
        },
        "state_path": {
            "provenance": "DECLARED_INPUT" if state_path_identified else "NOT_VERIFIED",
            "identified": state_path_identified,
            "declaration": state if state else None,
            "observation": state_observation,
        },
        "command_path": {
            "provenance": "DECLARED_INPUT" if command_identified else "NOT_VERIFIED",
            "identified": command_identified,
            "declaration": command if command else None,
            "executed": False,
        },
        "gripper_path": {
            "provenance": "DECLARED_INPUT" if gripper_identified else "NOT_VERIFIED",
            "gripper_present": gripper_present,
            "identified_or_not_applicable": gripper_identified,
            "declaration": gripper if gripper else None,
            "executed": False,
        },
        "camera": {
            "identity_provenance": "DECLARED_INPUT" if camera else "NOT_VERIFIED",
            "selected": camera_selected,
            "declaration": camera if camera else None,
            "device_provenance": "MEASURED" if camera_valid else "NOT_VERIFIED",
            "selected_metadata": camera_meta,
            "stable_identity_metadata": stable_camera_meta,
            "physically_discoverable": camera_discovered,
            "stable_identity_available": stable_camera,
            "readable": camera_readable,
            "acquisition": acquisition,
        },
        "workspace_safety_boundary": {
            "provenance": "DECLARED_INPUT" if workspace_documented else "NOT_VERIFIED",
            "declared_source_kind": workspace.get("source_kind") if workspace else None,
            "documented": workspace_documented,
            "details": workspace if workspace else None,
            "physically_exercised": False,
        },
        "abort_estop": {
            "provenance": "DECLARED_INPUT" if abort else "NOT_VERIFIED",
            "classification": abort.get("availability", "NOT_VERIFIED"),
            "documented": abort_documented,
            "details": abort if abort else None,
            "functionally_tested_under_motion": False,
        },
        "teleoperation_prerequisites": {
            "provenance": "DERIVED",
            "status": "PASS" if teleoperation_ready else "BLOCKED",
            "implemented": False,
            "executed": False,
            "task_w1_002_authorized": False,
        },
        "checks": checks,
        "unresolved_blockers": [],
        "deferred_non_blockers": [
            {"item": "physical teleoperation implementation", "owner": "TASK-W1-002", "provenance": "DOCUMENTED"},
            {"item": "Dataset V1", "owner": "TASK-W1-003", "provenance": "DOCUMENTED"},
            {"item": "fine-tuning", "owner": "TASK-W1-004", "provenance": "DOCUMENTED"},
            {"item": "training compute/budget resolution", "owner": "TASK-P0-007", "provenance": "DOCUMENTED"},
            {"item": "final Phase 0 authorization", "owner": "TASK-P0-004R", "provenance": "DOCUMENTED"},
        ],
        "safety": {
            "provenance": "DERIVED",
            "non_motion_verifier": True,
            "robot_motion_commanded": False,
            "joint_motion_commanded": False,
            "gripper_motion_commanded": False,
            "trajectory_execution_commanded": False,
            "teleoperation_motion_commanded": False,
            "unknown_vendor_interface_executed": False,
            "robot_serial_or_controller_opened": False,
            "camera_frames_persisted": False,
            "permissions_or_security_policy_changed": False,
            "dataset_work_started": False,
            "model_work_started": False,
            "integration_work_started": False,
        },
        "task_w1_001_authorized": False,
        "p0_004r_required": True,
    }
    consistency_errors = _material_consistency_errors(evidence)
    checks.append(
        _check(
            "C18",
            "Evidence and documentation internally consistent",
            "PASS" if not consistency_errors else "BLOCKED",
            "DERIVED",
            "material invariants are consistent" if not consistency_errors else "; ".join(consistency_errors),
        )
    )
    decision = decide_readiness(checks)
    evidence["device_io_decision"] = decision
    evidence["unresolved_blockers"] = [
        {
            "check_id": item["id"],
            "area": item["area"],
            "status": item["status"],
            "detail": item["detail"],
        }
        for item in checks
        if item["mandatory"] and item["status"] != "PASS"
    ]
    evidence["content_binding"]["evidence_payload_sha256"] = (
        _evidence_payload_sha256(evidence)
    )
    return evidence


def validate_evidence(evidence: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "task",
        "device_io_decision",
        "content_binding",
        "host",
        "target_hardware",
        "device_discovery",
        "robot_device",
        "camera",
        "state_path",
        "command_path",
        "gripper_path",
        "workspace_safety_boundary",
        "abort_estop",
        "teleoperation_prerequisites",
        "unresolved_blockers",
        "deferred_non_blockers",
        "checks",
        "safety",
    }
    missing = sorted(required - set(evidence))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
    if evidence.get("task") != TASK_ID:
        errors.append("task identity mismatch")
    checks_value = evidence.get("checks", [])
    checks: list[Mapping[str, Any]] = []
    if not isinstance(checks_value, list):
        errors.append("checks must be a list")
    else:
        for index, expected in enumerate(EXPECTED_CHECKS):
            if index >= len(checks_value):
                break
            item = checks_value[index]
            if not isinstance(item, Mapping):
                errors.append(f"check at index {index} must be an object")
                continue
            checks.append(item)
            expected_id, expected_area = expected
            if item.get("id") != expected_id or item.get("area") != expected_area:
                errors.append(
                    f"check identity mismatch at index {index}: expected "
                    f"{expected_id} {expected_area}"
                )
            if item.get("mandatory") is not True:
                errors.append(f"{expected_id} must remain mandatory")
            if item.get("status") not in CHECK_STATUSES:
                errors.append(f"{expected_id} has invalid status")
            if item.get("provenance") not in PROVENANCE:
                errors.append(f"{expected_id} has invalid provenance")
        if len(checks_value) != len(EXPECTED_CHECKS):
            errors.append("checks must contain C01-C18 exactly once and in order")
        elif len(checks) == len(EXPECTED_CHECKS):
            ids = [item.get("id") for item in checks]
            if len(set(ids)) != len(EXPECTED_CHECKS):
                errors.append("check identities must be unique")

    expected_decision = (
        decide_readiness(checks_value) if isinstance(checks_value, list) else BLOCKED
    )
    if evidence.get("device_io_decision") != expected_decision:
        errors.append("aggregate decision does not propagate mandatory check failures")
    check_items = checks_value if isinstance(checks_value, list) else []
    if evidence.get("device_io_decision") == READY and (
        len(check_items) != len(EXPECTED_CHECKS)
        or any(
            not isinstance(item, Mapping)
            or item.get("mandatory") is not True
            or item.get("status") != "PASS"
            for item in check_items
        )
    ):
        errors.append("DEVICE_IO_READY requires every mandatory readiness check to PASS")
    if evidence.get("device_io_decision") not in {READY, BLOCKED}:
        errors.append("invalid device I/O decision")

    expected_blockers = [
        {
            "check_id": item.get("id"),
            "area": item.get("area"),
            "status": item.get("status"),
            "detail": item.get("detail"),
        }
        for item in check_items
        if isinstance(item, Mapping)
        and item.get("mandatory") is True
        and item.get("status") != "PASS"
    ]
    if evidence.get("unresolved_blockers") != expected_blockers:
        errors.append(
            "unresolved_blockers must exactly match all mandatory non-PASS checks"
        )

    def validate_provenance(value: Any, location: str = "evidence") -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                nested_location = f"{location}.{key}"
                if (key == "provenance" or key.endswith("_provenance")) and (
                    nested not in PROVENANCE
                ):
                    errors.append(f"{nested_location} has invalid provenance")
                else:
                    validate_provenance(nested, nested_location)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                validate_provenance(nested, f"{location}[{index}]")

    validate_provenance(evidence)

    binding = evidence.get("content_binding")
    git_facts = evidence.get("git")
    verifier = evidence.get("verifier")
    if not isinstance(binding, Mapping):
        errors.append("content_binding must be an object")
    else:
        mode = binding.get("generation_mode")
        if mode not in {"COMMITTED_TREE", "PRE_COMMIT_WORKTREE"}:
            errors.append("content_binding has invalid generation_mode")
        if isinstance(git_facts, Mapping):
            if binding.get("git_head_at_generation") != git_facts.get("commit"):
                errors.append("content_binding Git HEAD mismatch")
            expected_dirty = not bool(git_facts.get("working_tree_clean"))
            if binding.get("working_tree_dirty_at_generation") is not expected_dirty:
                errors.append("content_binding working-tree state mismatch")
            expected_mode = "PRE_COMMIT_WORKTREE" if expected_dirty else "COMMITTED_TREE"
            if mode != expected_mode:
                errors.append("content_binding generation mode contradicts Git state")
        if isinstance(verifier, Mapping) and (
            binding.get("verifier_sha256") != verifier.get("sha256")
        ):
            errors.append("content_binding verifier hash mismatch")
        source_hashes = binding.get("source_sha256")
        expected_source_hashes = _bound_source_hashes(
            Path(__file__).resolve().parents[1]
        )
        if source_hashes != expected_source_hashes:
            errors.append("content_binding source hashes do not match current files")
        if binding.get("evidence_payload_sha256") != _evidence_payload_sha256(evidence):
            errors.append("content_binding evidence payload hash mismatch")
    if evidence.get("task_w1_001_authorized") is not False:
        errors.append("TASK-W1-001 must remain unauthorized")
    if evidence.get("p0_004r_required") is not True:
        errors.append("TASK-P0-004R must remain required")
    return errors


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
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
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=repository_root / "results" / "phase0" / "P0-006_robot_io_readiness.json",
    )
    parser.add_argument(
        "--declarations",
        type=Path,
        help="operator-supplied JSON identity/interface/safety declarations",
    )
    parser.add_argument("--dev-root", type=Path, default=Path("/dev"))
    parser.add_argument(
        "--device-discovery-timeout-seconds",
        type=float,
        default=DEFAULT_DEVICE_DISCOVERY_TIMEOUT_SECONDS,
    )
    parser.add_argument("--camera-timeout-seconds", type=float, default=5.0)
    parser.add_argument("--state-timeout-seconds", type=float, default=2.0)
    parser.add_argument("--camera-frame-count", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    if not 0 < arguments.device_discovery_timeout_seconds <= 30:
        print("device discovery timeout must be > 0 and <= 30 seconds", file=sys.stderr)
        return 3
    if not 0 < arguments.camera_timeout_seconds <= 30:
        print("camera timeout must be > 0 and <= 30 seconds", file=sys.stderr)
        return 3
    if not 0 < arguments.state_timeout_seconds <= 30:
        print("state timeout must be > 0 and <= 30 seconds", file=sys.stderr)
        return 3
    if not 0 < arguments.camera_frame_count <= MAX_CAMERA_FRAMES:
        print(f"camera frame count must be between 1 and {MAX_CAMERA_FRAMES}", file=sys.stderr)
        return 3

    declarations, load_errors, source = _load_declarations(arguments.declarations)
    try:
        evidence = collect_evidence(
            repository_root,
            declarations=declarations,
            declaration_source=source,
            declaration_errors=load_errors,
            dev_root=arguments.dev_root,
            device_discovery_timeout_seconds=arguments.device_discovery_timeout_seconds,
            camera_timeout_seconds=arguments.camera_timeout_seconds,
            state_timeout_seconds=arguments.state_timeout_seconds,
            camera_frame_count=arguments.camera_frame_count,
        )
        validation_errors = validate_evidence(evidence)
        if validation_errors:
            evidence["verifier_error"] = {
                "provenance": "DERIVED",
                "errors": validation_errors,
            }
            evidence["device_io_decision"] = BLOCKED
            _atomic_write_json(arguments.output, evidence)
            return 3
        _atomic_write_json(arguments.output, evidence)
    except Exception as exc:
        error_evidence = {
            "schema_version": SCHEMA_VERSION,
            "task": TASK_ID,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "device_io_decision": BLOCKED,
            "verifier_error": {
                "provenance": "MEASURED",
                "type": type(exc).__name__,
                "detail": _bounded(str(exc)),
            },
            "task_w1_001_authorized": False,
            "p0_004r_required": True,
        }
        _atomic_write_json(arguments.output, error_evidence)
        print(f"verifier error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    print(f"TASK: {TASK_ID}")
    print(f"Device I/O decision: {evidence['device_io_decision']}")
    for item in evidence["checks"]:
        print(f"{item['id']} {item['area']}: {item['status']} - {item['detail']}")
    print(f"Evidence: {arguments.output}")
    print("TASK-W1-001 authorized: false")
    print("TASK-P0-004R required: true")
    return 0 if evidence["device_io_decision"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
