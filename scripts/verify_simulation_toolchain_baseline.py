#!/usr/bin/env python3
"""Generate the bounded, non-mutating TASK-SIM-003 toolchain baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "TASK-SIM-003"
BASELINE_ID = "SIM_BASELINE_V1"
SCHEMA_VERSION = "1.0"
READY = "SIM_BASELINE_READY"
BLOCKED = "SIM_BASELINE_BLOCKED"
GAZEBO_HARMONIC_MAJOR = 8
MAX_OUTPUT_BYTES = 4096

ACCEPTANCE_PATHS = {
    "TASK-SIM-C01": "results/reviews/SIM-C01_acceptance.json",
    "TASK-SIM-001": "results/reviews/SIM-001_acceptance.json",
    "TASK-SIM-002": "results/reviews/SIM-002_acceptance.json",
    "TASK-SIM-GATE": "results/reviews/SIM-GATE_acceptance.json",
}
EXPECTED_DECISIONS = {
    "TASK-SIM-C01": "SIM_CONTRACT_GAPS_RESOLVED",
    "TASK-SIM-001": "SIM_CONTRACT_PROFILE_READY",
    "TASK-SIM-002": "SIM_SMOKE_READY",
    "TASK-SIM-GATE": "SIM_GO",
}
SOURCE_PATHS = (
    "tasks/TASK-SIM-003.md",
    "docs/contracts/simulation_execution_contract_v1.md",
    "docs/contracts/schemas/simulation_execution_contract_v1.schema.json",
    "scripts/run_simulation_smoke.py",
    "src/simulation_runtime/smoke.py",
    "tests/test_simulation_execution_contract.py",
    "tests/test_simulation_smoke.py",
    "scripts/verify_simulation_toolchain_baseline.py",
    "tests/test_simulation_toolchain_baseline.py",
    "config/simulation/sim_baseline_empty.sdf",
    "config/simulation/mujoco_baseline.xml",
)
ROS_GZ_ENTRY_POINTS = (
    ("ros_gz_bridge", "parameter_bridge"),
    ("ros_gz_sim", "gzserver"),
    ("ros_gz_sim", "create"),
)
NAV2_ENTRY_POINTS = (
    ("nav2_amcl", "amcl"),
    ("nav2_behaviors", "behavior_server"),
    ("nav2_bt_navigator", "bt_navigator"),
    ("nav2_controller", "controller_server"),
    ("nav2_lifecycle_manager", "lifecycle_manager"),
    ("nav2_map_server", "map_server"),
    ("nav2_planner", "planner_server"),
)
FIDELITY_LEVELS = ("L0", "L1-NAV", "L1-VLA", "L1-VERIFY", "L2-SYSTEM")
AUTHORITY_POLICY = {
    "ros2_distro": "jazzy",
    "gazebo_release": "harmonic",
    "system_simulator": "gazebo_harmonic",
    "navigation_backend": "ros2_jazzy_gazebo_harmonic",
    "manipulation_physics_backend": "mujoco",
    "integrated_world_authority": "gazebo_harmonic",
    "dual_world_cosimulation": "prohibited_v1",
}
DETERMINISTIC_COMMAND = (
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "-p",
    "no:cacheprovider",
    "tests/test_simulation_execution_contract.py",
    "tests/test_simulation_smoke.py",
)

RunResult = dict[str, Any]
Runner = Callable[..., RunResult]


def _bounded(value: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    return value.strip()[:limit]


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_process_group(process_group_id: int) -> bool:
    """Terminate every child in a probe's isolated process group."""

    if not _process_group_exists(process_group_id):
        return True
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        return True
    for _ in range(10):
        if not _process_group_exists(process_group_id):
            return True
        time.sleep(0.05)
    try:
        os.killpg(process_group_id, signal.SIGKILL)
    except ProcessLookupError:
        return True
    for _ in range(10):
        if not _process_group_exists(process_group_id):
            return True
        time.sleep(0.05)
    return not _process_group_exists(process_group_id)


def run_bounded(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> RunResult:
    """Run a probe with an explicit timeout and isolated process group."""

    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        return {
            "command": list(command),
            "timeout_seconds": timeout_seconds,
            "available": False,
            "returncode": None,
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 6),
            "stdout": "",
            "stderr": _bounded(f"{type(exc).__name__}: {exc}"),
            "process_group_cleanup_complete": True,
        }

    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process.pid)
        stdout, stderr = process.communicate()

    cleanup_complete = _terminate_process_group(process.pid)
    return {
        "command": list(command),
        "timeout_seconds": timeout_seconds,
        "available": True,
        "returncode": process.returncode,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 6),
        "stdout": _bounded(stdout),
        "stderr": _bounded(stderr),
        "process_group_cleanup_complete": cleanup_complete,
    }


def canonical_payload_sha256(document: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(document))
    payload.pop("payload_sha256", None)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _payload_valid(value: Mapping[str, Any] | None) -> bool:
    if not isinstance(value, Mapping) or not isinstance(value.get("payload_sha256"), str):
        return False
    return canonical_payload_sha256(value) == value["payload_sha256"]


def _commit_exists(git_root: Path, commit: object) -> bool:
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        return False
    result = run_bounded(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        timeout_seconds=5,
        cwd=git_root,
    )
    return result["returncode"] == 0 and not result["timed_out"]


def _binding_matches(root: Path, record: Mapping[str, Any], path_key: str, hash_key: str) -> bool:
    relative = record.get(path_key)
    expected = record.get(hash_key)
    return (
        isinstance(relative, str)
        and isinstance(expected, str)
        and _sha256(root / relative) == expected
    )


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _evidence_matches(
    root: Path,
    acceptance: Mapping[str, Any],
    *,
    evidence_path_key: str,
    evidence_hash_key: str,
    accepted_payload_key: str,
) -> bool:
    if not _binding_matches(root, acceptance, evidence_path_key, evidence_hash_key):
        return False
    relative = acceptance.get(evidence_path_key)
    evidence = _load_json(root / str(relative))
    return (
        _payload_valid(evidence)
        and evidence is not None
        and evidence.get("payload_sha256") == acceptance.get(accepted_payload_key)
    )


def validate_predecessors(root: Path, *, git_root: Path) -> dict[str, Any]:
    """Validate the complete accepted chain before any toolchain probe runs."""

    records = {task: _load_json(root / path) for task, path in ACCEPTANCE_PATHS.items()}
    checks: list[dict[str, Any]] = []

    def add(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail})

    for task_id, expected_decision in EXPECTED_DECISIONS.items():
        record = records[task_id]
        add(
            f"{task_id}:acceptance",
            isinstance(record, Mapping)
            and record.get("task_id") == task_id
            and record.get("review_decision") == "ACCEPT"
            and record.get("task_specific_decision") == expected_decision,
            f"requires ACCEPT + {expected_decision}",
        )
        add(
            f"{task_id}:reviewed_commit",
            isinstance(record, Mapping) and _commit_exists(git_root, record.get("reviewed_commit")),
            "reviewed commit must exist",
        )

    c01 = records["TASK-SIM-C01"] or {}
    sim001 = records["TASK-SIM-001"] or {}
    sim002 = records["TASK-SIM-002"] or {}
    gate = records["TASK-SIM-GATE"] or {}
    gate_readiness = _load_json(root / "results/simulation/SIM-GATE_readiness.json")

    add(
        "SIM-C01:evidence",
        _evidence_matches(
            root,
            c01,
            evidence_path_key="evidence_path",
            evidence_hash_key="evidence_sha256",
            accepted_payload_key="accepted_payload_sha256",
        ),
        "C01 evidence file and canonical payload must match acceptance",
    )
    add(
        "SIM-001:evidence",
        _evidence_matches(
            root,
            sim001,
            evidence_path_key="evidence_path",
            evidence_hash_key="evidence_sha256",
            accepted_payload_key="accepted_payload_sha256",
        ),
        "SIM-001 evidence file and canonical payload must match acceptance",
    )
    add(
        "SIM-002:evidence",
        _evidence_matches(
            root,
            sim002,
            evidence_path_key="evidence_path",
            evidence_hash_key="evidence_sha256",
            accepted_payload_key="evidence_payload_sha256",
        ),
        "SIM-002 evidence file and canonical payload must match acceptance",
    )

    for task_name, record, bindings in (
        (
            "SIM-C01",
            c01,
            (("contract_path", "contract_sha256"), ("schema_path", "schema_sha256")),
        ),
        (
            "SIM-001",
            sim001,
            (
                ("profile_path", "profile_sha256"),
                ("simulation_execution_contract_path", "simulation_execution_contract_sha256"),
                ("simulation_execution_schema_path", "simulation_execution_schema_sha256"),
            ),
        ),
        (
            "SIM-002",
            sim002,
            (
                ("smoke_report_path", "smoke_report_sha256"),
                ("smoke_entry_point_path", "smoke_entry_point_sha256"),
                ("runtime_module_path", "runtime_module_sha256"),
                ("focused_test_path", "focused_test_sha256"),
                ("simulation_execution_contract_path", "simulation_execution_contract_sha256"),
                ("simulation_execution_schema_path", "simulation_execution_schema_sha256"),
            ),
        ),
    ):
        add(
            f"{task_name}:artifact_bindings",
            all(_binding_matches(root, record, path_key, hash_key) for path_key, hash_key in bindings),
            "all acceptance-bound artifacts must retain their accepted hashes",
        )

    c01_hash = _sha256(root / ACCEPTANCE_PATHS["TASK-SIM-C01"])
    sim001_hash = _sha256(root / ACCEPTANCE_PATHS["TASK-SIM-001"])
    sim002_hash = _sha256(root / ACCEPTANCE_PATHS["TASK-SIM-002"])
    readiness_hash = _sha256(root / "results/simulation/SIM-GATE_readiness.json")
    add(
        "acceptance_chain:SIM-C01",
        c01_hash == sim001.get("sim_c01_acceptance_sha256") == sim002.get("sim_c01_acceptance_sha256"),
        "SIM-001 and SIM-002 must bind the current C01 acceptance",
    )
    gate_predecessors = _as_mapping(gate.get("predecessor_acceptance"))
    gate_sim001 = _as_mapping(gate_predecessors.get("SIM-001"))
    gate_sim002 = _as_mapping(gate_predecessors.get("SIM-002"))
    gate_evidence = _as_mapping(gate.get("gate_evidence"))
    gate_authorization = _as_mapping(gate.get("authorization"))
    add(
        "acceptance_chain:SIM-001",
        sim001_hash == sim002.get("sim_001_acceptance_sha256") == gate_sim001.get("sha256"),
        "SIM-002 and SIM-GATE must bind the current SIM-001 acceptance",
    )
    add(
        "acceptance_chain:SIM-002",
        sim002_hash == gate_sim002.get("sha256"),
        "SIM-GATE must bind the current SIM-002 acceptance",
    )
    add(
        "SIM-GATE:readiness_binding",
        isinstance(gate_readiness, Mapping)
        and readiness_hash == gate_evidence.get("sha256")
        and _payload_valid(gate_readiness)
        and gate_readiness.get("payload_sha256") == gate_evidence.get("payload_sha256")
        and gate_readiness.get("gate_result") == "SIM_GO",
        "accepted gate evidence must be canonical SIM_GO",
    )
    add(
        "SIM-GATE:authorization",
        gate_authorization.get("simulation_lane_authorized") is True
        and gate_authorization.get("physical_motion_authorized") is False
        and gate_authorization.get("task_w1_001_authorized") is False
        and gate_authorization.get("task_w1_002_authorized") is False,
        "post-review simulation authorization must preserve physical and Week isolation",
    )
    grouped_gate_ok = True
    for key in ("gate_verifier", "gate_tests", "gate_report"):
        item = _as_mapping(gate.get(key))
        relative = item.get("path")
        grouped_gate_ok = (
            grouped_gate_ok
            and isinstance(relative, str)
            and _sha256(root / relative) == item.get("sha256")
        )
    add(
        "SIM-GATE:artifact_bindings",
        grouped_gate_ok,
        "accepted gate verifier, tests, and report must retain their hashes",
    )

    valid = all(item["status"] == "PASS" for item in checks)
    bindings = []
    for task_id, relative in ACCEPTANCE_PATHS.items():
        record = records[task_id] or {}
        bindings.append(
            {
                "task_id": task_id,
                "path": relative,
                "sha256": _sha256(root / relative),
                "review_decision": record.get("review_decision"),
                "task_specific_decision": record.get("task_specific_decision"),
                "reviewed_commit": record.get("reviewed_commit"),
            }
        )
    bindings.append(
        {
            "task_id": "TASK-SIM-GATE-EVIDENCE",
            "path": "results/simulation/SIM-GATE_readiness.json",
            "sha256": readiness_hash,
            "payload_sha256": gate_readiness.get("payload_sha256") if gate_readiness else None,
            "gate_result": gate_readiness.get("gate_result") if gate_readiness else None,
        }
    )
    return {"status": "PASS" if valid else "FAIL", "bindings": bindings, "checks": checks}


def _probe_ok(result: Mapping[str, Any]) -> bool:
    return (
        result.get("available") is True
        and result.get("returncode") == 0
        and result.get("timed_out") is False
        and result.get("process_group_cleanup_complete") is True
    )


def _parse_executables(output: str) -> set[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            entries.add((parts[0], parts[1]))
    return entries


def _entry_point_evidence(
    available: set[tuple[str, str]], required: Sequence[tuple[str, str]]
) -> list[dict[str, Any]]:
    return [
        {"package": package, "executable": executable, "available": (package, executable) in available}
        for package, executable in required
    ]


def _git_provenance(root: Path, git_root: Path) -> dict[str, Any]:
    head = run_bounded(["git", "rev-parse", "HEAD"], timeout_seconds=5, cwd=git_root)
    status = run_bounded(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        timeout_seconds=5,
        cwd=git_root,
    )
    paths = [] if not _probe_ok(status) else [line for line in status["stdout"].splitlines() if line]
    return {
        "git_sha": head["stdout"] if _probe_ok(head) else None,
        "worktree_clean": _probe_ok(status) and not paths,
        "worktree_status": paths,
    }


def _skipped_runtime() -> dict[str, Any]:
    return {
        "probe_order": "SKIPPED_DUE_TO_PREDECESSOR_FAILURE",
        "ros2": {"status": "NOT_EVALUATED"},
        "gazebo": {"status": "NOT_EVALUATED"},
        "ros_gz": {"status": "NOT_EVALUATED"},
        "nav2": {"status": "NOT_EVALUATED"},
        "mujoco": {"status": "NOT_EVALUATED", "version": None},
    }


def evaluate_baseline(
    root: Path = ROOT,
    *,
    git_root: Path | None = None,
    runner: Runner = run_bounded,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    generation_timestamp: str | None = None,
    pre_implementation_clean: bool | None = None,
) -> dict[str, Any]:
    git_root = git_root or root
    environment = dict(os.environ if environ is None else environ)
    generated_at = generation_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    predecessors = validate_predecessors(root, git_root=git_root)
    blockers: list[str] = []

    if predecessors["status"] != "PASS":
        blockers.extend(
            item["check_id"] for item in predecessors["checks"] if item["status"] != "PASS"
        )
        runtime = _skipped_runtime()
        deterministic = {"status": "NOT_EVALUATED", "reason": "predecessor validation failed"}
        provenance = _git_provenance(root, git_root)
    else:
        provenance = _git_provenance(root, git_root)
        ros2_executable = which("ros2")
        gz_executable = which("gz")
        ros_distro = environment.get("ROS_DISTRO")

        ros_help = runner(
            [ros2_executable or "ros2", "--help"], timeout_seconds=5, cwd=root, env=environment
        )
        rclpy = runner(
            [sys.executable, "-c", "import importlib.metadata as m; print(m.version('rclpy'))"],
            timeout_seconds=5,
            cwd=root,
            env=environment,
        )
        ros2 = {
            "required_distro": "jazzy",
            "measured_distro": ros_distro,
            "executable": ros2_executable,
            "rclpy_version": rclpy["stdout"] if _probe_ok(rclpy) else None,
            "cli_probe": ros_help,
            "status": "PASS"
            if ros2_executable and ros_distro == "jazzy" and _probe_ok(ros_help) and _probe_ok(rclpy)
            else "FAIL",
        }

        required_packages = sorted({package for package, _ in (*ROS_GZ_ENTRY_POINTS, *NAV2_ENTRY_POINTS)})
        executable_probes: dict[str, RunResult] = {}
        executable_set: set[tuple[str, str]] = set()
        for package in required_packages:
            probe = runner(
                [ros2_executable or "ros2", "pkg", "executables", package],
                timeout_seconds=5,
                cwd=root,
                env=environment,
            )
            executable_probes[package] = probe
            if _probe_ok(probe):
                executable_set.update(_parse_executables(probe["stdout"]))
        ros_gz_entries = _entry_point_evidence(executable_set, ROS_GZ_ENTRY_POINTS)
        nav2_entries = _entry_point_evidence(executable_set, NAV2_ENTRY_POINTS)
        ros_gz = {
            "entry_points": ros_gz_entries,
            "discovery_probes": {
                package: executable_probes[package]
                for package in sorted({item[0] for item in ROS_GZ_ENTRY_POINTS})
            },
            "status": "PASS" if all(item["available"] for item in ros_gz_entries) else "FAIL",
        }
        nav2 = {
            "purpose": "minimum SIM-004 Nav2-facing server surface; no navigation behavior executed",
            "entry_points": nav2_entries,
            "discovery_probes": {
                package: executable_probes[package]
                for package in sorted({item[0] for item in NAV2_ENTRY_POINTS})
            },
            "status": "PASS" if all(item["available"] for item in nav2_entries) else "FAIL",
        }

        gazebo_version_probe = runner(
            [gz_executable or "gz", "sim", "--version"],
            timeout_seconds=5,
            cwd=root,
            env=environment,
        )
        match = re.search(r"version\s+(\d+\.\d+\.\d+)", gazebo_version_probe["stdout"], re.I)
        gazebo_version = match.group(1) if match else None
        gazebo_release = (
            "harmonic"
            if gazebo_version and int(gazebo_version.split(".", maxsplit=1)[0]) == GAZEBO_HARMONIC_MAJOR
            else None
        )
        with tempfile.TemporaryDirectory(prefix="sim003-gz-") as temporary:
            temporary_path = Path(temporary)
            gazebo_env = dict(environment)
            gazebo_env.update(
                {
                    "XDG_CACHE_HOME": str(temporary_path / "cache"),
                    "XDG_CONFIG_HOME": str(temporary_path / "config"),
                    "XDG_DATA_HOME": str(temporary_path / "data"),
                    "GZ_LOG_PATH": str(temporary_path / "log"),
                    "GZ_IP": "127.0.0.1",
                    "IGN_IP": "127.0.0.1",
                }
            )
            gazebo_smoke = runner(
                [
                    gz_executable or "gz",
                    "sim",
                    "-s",
                    "-r",
                    "--iterations",
                    "2",
                    str(root / "config/simulation/sim_baseline_empty.sdf"),
                ],
                timeout_seconds=15,
                cwd=root,
                env=gazebo_env,
            )
            temporary_created = temporary_path.exists()
        gazebo_smoke["temporary_workspace_created"] = temporary_created
        gazebo_smoke["temporary_workspace_cleanup_complete"] = not temporary_path.exists()
        gazebo = {
            "required_release": "harmonic",
            "executable": gz_executable,
            "version": gazebo_version,
            "release": gazebo_release,
            "version_probe": gazebo_version_probe,
            "headless_smoke": gazebo_smoke,
            "smoke_mode": "server_only_headless",
            "iterations": 2,
            "navigation_mission_executed": False,
            "status": "PASS"
            if gz_executable
            and gazebo_release == "harmonic"
            and _probe_ok(gazebo_smoke)
            and gazebo_smoke["temporary_workspace_cleanup_complete"]
            else "FAIL",
        }

        mujoco_model = root / "config/simulation/mujoco_baseline.xml"
        mujoco_code = (
            "import json,sys\n"
            "import mujoco\n"
            "model=mujoco.MjModel.from_xml_path(sys.argv[1])\n"
            "data=mujoco.MjData(model)\n"
            "before=float(data.time)\n"
            "mujoco.mj_step(model,data)\n"
            "print(json.dumps({'version':mujoco.__version__,'model_loaded':True,"
            "'steps':1,'time_before':before,'time_after':float(data.time),"
            "'nq':model.nq,'nv':model.nv,'viewer_used':False,'rendering_requested':False},sort_keys=True))\n"
        )
        mujoco_env = dict(environment)
        mujoco_env.pop("DISPLAY", None)
        mujoco_probe = runner(
            [sys.executable, "-c", mujoco_code, str(mujoco_model)],
            timeout_seconds=10,
            cwd=root,
            env=mujoco_env,
        )
        try:
            decoded_mujoco = json.loads(mujoco_probe["stdout"]) if _probe_ok(mujoco_probe) else {}
        except json.JSONDecodeError:
            decoded_mujoco = {}
        mujoco_detail = decoded_mujoco if isinstance(decoded_mujoco, dict) else {}
        steps = mujoco_detail.get("steps")
        time_before = mujoco_detail.get("time_before")
        time_after = mujoco_detail.get("time_after")
        mujoco_pass = (
            _probe_ok(mujoco_probe)
            and isinstance(mujoco_detail, dict)
            and mujoco_detail.get("model_loaded") is True
            and isinstance(steps, int)
            and steps >= 1
            and isinstance(mujoco_detail.get("version"), str)
            and isinstance(time_before, (int, float))
            and isinstance(time_after, (int, float))
            and time_after > time_before
        )
        mujoco = {
            "version": mujoco_detail.get("version"),
            "headless": True,
            "model_path": "config/simulation/mujoco_baseline.xml",
            "step_result": mujoco_detail or None,
            "probe": mujoco_probe,
            "status": "PASS" if mujoco_pass else "FAIL",
        }

        deterministic_probe = runner(
            list(DETERMINISTIC_COMMAND), timeout_seconds=60, cwd=root, env=environment
        )
        deterministic = {
            "command": list(DETERMINISTIC_COMMAND),
            "probe": deterministic_probe,
            "accepted_evidence_modified": False,
            "status": "PASS" if _probe_ok(deterministic_probe) else "FAIL",
        }
        runtime = {
            "probe_order": "AFTER_PREDECESSOR_VALIDATION",
            "python": {"executable": sys.executable, "version": platform.python_version()},
            "ros2": ros2,
            "gazebo": gazebo,
            "ros_gz": ros_gz,
            "nav2": nav2,
            "mujoco": mujoco,
        }
        for name, item in (
            ("ros2_jazzy", ros2),
            ("gazebo_harmonic_smoke", gazebo),
            ("ros_gz_entry_points", ros_gz),
            ("nav2_entry_points", nav2),
            ("mujoco_headless_step", mujoco),
            ("deterministic_regression", deterministic),
        ):
            if item["status"] != "PASS":
                blockers.append(name)

    source_bindings = [
        {"path": relative, "exists": (root / relative).is_file(), "sha256": _sha256(root / relative)}
        for relative in SOURCE_PATHS
    ]
    if not all(item["exists"] and item["sha256"] for item in source_bindings):
        blockers.append("source_bindings")

    result = READY if not blockers else BLOCKED
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "baseline_id": BASELINE_ID,
        "implementation_complete": True,
        "task_specific_result": result,
        "generation_timestamp": generated_at,
        "provenance": {
            **provenance,
            "pre_implementation_clean": pre_implementation_clean,
            "host": {
                "system": platform.system(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
            },
        },
        "predecessors": predecessors,
        "source_bindings": source_bindings,
        "runtime": runtime,
        "fidelity_policy": {
            "levels": list(FIDELITY_LEVELS),
            "L0": "deterministic_contract_lifecycle_regression",
            "L1-NAV": "ros2_jazzy_gazebo_harmonic_navigation_component",
            "L1-VLA": "mujoco_manipulation_physics_component",
            "L1-VERIFY": "simulator_neutral_verification_adapter",
            "L2-SYSTEM": "ros2_jazzy_gazebo_harmonic_integrated_world",
        },
        "authority_policy": {
            **AUTHORITY_POLICY,
            "mujoco_version": runtime["mujoco"].get("version"),
            "simulation_evidence_is_physical_evidence": False,
            "physical_target_frozen": False,
        },
        "deterministic_regression": deterministic,
        "validation_commands": {
            "baseline_verifier": [
                sys.executable,
                "scripts/verify_simulation_toolchain_baseline.py",
                "--pre-implementation-clean",
            ],
            "focused": [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_simulation_toolchain_baseline.py",
                "tests/test_simulation_execution_contract.py",
                "tests/test_simulation_smoke.py",
            ],
            "deterministic_regression": list(DETERMINISTIC_COMMAND),
        },
        "blockers": sorted(set(blockers)),
        "downstream_eligibility": {
            "required_state": "ACCEPTED + SIM_BASELINE_READY",
            "task_sim_004_eligible_now": False,
            "task_sim_005_eligible_now": False,
            "eligible_after_independent_acceptance": result == READY,
            "physical_authorization": False,
        },
        "independent_acceptance": "PENDING",
        "payload_hash_algorithm": (
            "sha256(canonical JSON with sorted keys and compact separators, excluding payload_sha256)"
        ),
    }
    document["payload_sha256"] = canonical_payload_sha256(document)
    return document


def render_report(evidence: Mapping[str, Any]) -> str:
    runtime = evidence["runtime"]
    blocker_lines = evidence.get("blockers") or []
    blockers = "None." if not blocker_lines else "\n".join(f"- `{item}`" for item in blocker_lines)
    entries = []
    for section in ("ros_gz", "nav2"):
        for item in runtime.get(section, {}).get("entry_points", []):
            entries.append(
                f"| `{item['package']}` | `{item['executable']}` | "
                f"{'PASS' if item['available'] else 'FAIL'} |"
            )
    entry_table = "\n".join(entries) or "| not evaluated | not evaluated | BLOCKED |"
    predecessor_table = "\n".join(
        f"| `{item['task_id']}` | `{item['path']}` | `{item['sha256']}` |"
        for item in evidence["predecessors"]["bindings"]
    )
    source_table = "\n".join(
        f"| `{item['path']}` | `{item['sha256']}` |"
        for item in evidence["source_bindings"]
    )
    validation_lines = "\n".join(
        f"- `{name}`: `{' '.join(command)}`"
        for name, command in evidence["validation_commands"].items()
    )
    return f"""# SIM_BASELINE_V1 — Simulation Toolchain Baseline

> Task: `{TASK_ID}`
> Result: `{evidence['task_specific_result']}`
> Generated: `{evidence['generation_timestamp']}`
> Git SHA: `{evidence['provenance']['git_sha']}`
> Independent acceptance: `PENDING`

## Runtime result

| Runtime | Required | Measured | Status |
|---|---|---|---|
| ROS 2 | Jazzy | `{runtime.get('ros2', {}).get('measured_distro')}` | {runtime.get('ros2', {}).get('status')} |
| Gazebo | Harmonic | `{runtime.get('gazebo', {}).get('version')}` | {runtime.get('gazebo', {}).get('status')} |
| MuJoCo | measured, headless model load + step | `{runtime.get('mujoco', {}).get('version')}` | {runtime.get('mujoco', {}).get('status')} |
| Deterministic L0 | accepted contract + smoke regression | pytest | {evidence['deterministic_regression']['status']} |

## Frozen ROS/Gazebo and Nav2-facing entry points

| Package | Executable | Availability |
|---|---|---|
{entry_table}

These identities are the minimum integration surface for `TASK-SIM-004`; they do not implement or execute Navigation behavior.

## Accepted predecessor bindings

| Task | Canonical path | SHA-256 |
|---|---|---|
{predecessor_table}

## Source and simulator-input bindings

| Path | SHA-256 |
|---|---|
{source_table}

## Validation commands

{validation_lines}

## Fidelity and authority

- `L0`: deterministic contract and lifecycle regression.
- `L1-NAV`: ROS 2 Jazzy + Gazebo Harmonic navigation component simulation.
- `L1-VLA`: MuJoCo manipulation-physics component bench.
- `L1-VERIFY`: simulator-neutral Verification adapter.
- `L2-SYSTEM`: Gazebo Harmonic authoritative integrated world.
- `dual_world_cosimulation = prohibited_v1`.
- Simulation evidence is not physical evidence and freezes no physical target.

## Blockers

{blockers}

`SIM_BASELINE_READY` still requires independent acceptance before `TASK-SIM-004` or `TASK-SIM-005` becomes eligible. `SIM_BASELINE_BLOCKED` is non-authorizing.
"""


def _write_outputs(evidence: Mapping[str, Any], output: Path, report: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report.write_text(render_report(evidence), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/simulation/SIM-003_baseline.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "docs/simulation/simulation_baseline_v1.md",
    )
    parser.add_argument("--pre-implementation-clean", action="store_true")
    args = parser.parse_args()
    evidence = evaluate_baseline(pre_implementation_clean=args.pre_implementation_clean)
    _write_outputs(evidence, args.output, args.report)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
