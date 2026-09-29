#!/usr/bin/env python3
"""Generate the TASK-SIM-010 accepted-evidence regression artifact."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.observability_regression import (  # noqa: E402
    build_regression_evidence,
    classify_regression_failures,
    failure_signatures,
)

BASELINE_COMMIT = "6909c6cceb727598570f6e170ae8d1d293418c9a"
EXPECTED_MUJOCO_VERSION = "3.13.0"
PYTEST_ARGS = ["-m", "pytest", "-q", "-p", "no:cacheprovider"]


def resolve_qualified_python(value: Path) -> Path:
    """Retain a venv entry-point path while requiring an executable file."""
    path = Path(os.path.abspath(value))
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError("QUALIFIED_PYTHON_INVALID")
    return path


def regression_command(python: Path) -> list[str]:
    return [str(python), *PYTEST_ARGS]


def _qualified_environment(cwd: Path) -> dict[str, str]:
    return os.environ | {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(cwd / "src"),
    }


def preflight_environment(python: Path) -> dict[str, str]:
    code = (
        "import json,sys,mujoco,pytest; "
        "print(json.dumps({'python_executable':sys.executable,"
        "'python_version':sys.version,'mujoco_version':mujoco.__version__,"
        "'mujoco_file':mujoco.__file__,'pytest_file':pytest.__file__},sort_keys=True))"
    )
    result = subprocess.run(
        [str(python), "-c", code], text=True, capture_output=True, check=False,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        raise RuntimeError("DEPENDENCY_PREFLIGHT_FAILED")
    try:
        details = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DEPENDENCY_PREFLIGHT_FAILED") from exc
    if details.get("python_executable") != str(python) or details.get("mujoco_version") != EXPECTED_MUJOCO_VERSION:
        raise RuntimeError("DEPENDENCY_PREFLIGHT_FAILED")
    return details


def probe_worktree_environment(cwd: Path, python: Path) -> dict[str, str]:
    code = (
        "import json,os,sys,mujoco,pytest; "
        "import simulation_runtime.mujoco_vla_backend as project_module; "
        "print(json.dumps({'cwd':os.getcwd(),'python_executable':sys.executable,"
        "'python_version':sys.version,'mujoco_version':mujoco.__version__,"
        "'mujoco_file':mujoco.__file__,'pytest_file':pytest.__file__,"
        "'project_module_origin':project_module.__file__,'sys_path':sys.path},sort_keys=True))"
    )
    result = subprocess.run(
        [str(python), "-c", code], cwd=cwd, text=True, capture_output=True,
        check=False, env=_qualified_environment(cwd),
    )
    if result.returncode:
        raise RuntimeError("SOURCE_ISOLATION_PROBE_FAILED")
    try:
        details = json.loads(result.stdout)
        origin = Path(details["project_module_origin"]).resolve()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError("SOURCE_ISOLATION_PROBE_FAILED") from exc
    if (details.get("python_executable") != str(python)
            or details.get("mujoco_version") != EXPECTED_MUJOCO_VERSION
            or not origin.is_relative_to(cwd.resolve())):
        raise RuntimeError("ENVIRONMENT_SOURCE_ISOLATION_FAILED")
    return details


def _run_regression(cwd: Path, python: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        regression_command(python), cwd=cwd, text=True, capture_output=True,
        check=False, env=_qualified_environment(cwd),
    )


def classify_execution(
    current_exit: int,
    baseline_exit: int,
    current: dict[str, str],
    baseline: dict[str, str],
    infrastructure_error: str | None = None,
) -> str:
    """Only pytest PASS/failure exits are valid comparison executions."""
    if infrastructure_error or current_exit not in {0, 1} or baseline_exit not in {0, 1}:
        return "POSSIBLY_TASK_RELATED"
    if current_exit == 0:
        return "PASS"
    if baseline_exit != 1:
        return "POSSIBLY_TASK_RELATED"
    return classify_regression_failures(current, baseline)


def _detached_checkout(root: Path, commit: str, prefix: str) -> Path:
    temporary = Path(tempfile.mkdtemp(prefix=prefix))
    temporary.rmdir()
    checkout = subprocess.run(
        ["git", "worktree", "add", "--detach", str(temporary), commit],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if checkout.returncode:
        # Some sandboxed runners can read the shared Git directory but cannot
        # create its worktree-admin entry.  A local shared clone remains a
        # clean detached checkout of the same immutable object without using
        # mutable source files from the active worktree.
        clone = subprocess.run(
            ["git", "clone", "--shared", "--no-checkout", str(root), str(temporary)],
            cwd=root, text=True, capture_output=True, check=False,
        )
        detached = subprocess.run(
            ["git", "checkout", "--detach", commit], cwd=temporary,
            text=True, capture_output=True, check=False,
        ) if clone.returncode == 0 else None
        if clone.returncode or detached is None or detached.returncode:
            shutil.rmtree(temporary, ignore_errors=True)
            raise RuntimeError("REGRESSION_WORKTREE_CREATE_FAILED")
    return temporary


def _remove_checkout(root: Path, checkout_path: Path) -> None:
    if (checkout_path / ".git").is_dir():
        shutil.rmtree(checkout_path)
        return
    removal = subprocess.run(
        ["git", "worktree", "remove", "--force", str(checkout_path)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if removal.returncode:
        raise RuntimeError("REGRESSION_WORKTREE_CLEANUP_FAILED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True, type=Path, help="qualified absolute Python interpreter")
    args = parser.parse_args(argv)
    try:
        python = resolve_qualified_python(args.python)
        environment = preflight_environment(python)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    evidence = build_regression_evidence(ROOT)
    candidate_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
    comparison_error = None
    current = baseline = None
    validation = baseline_result = None
    current_failures: dict[str, str] = {}
    baseline_failures: dict[str, str] = {}
    current_environment = baseline_environment = None
    try:
        current = _detached_checkout(ROOT, candidate_commit, "sim010-current-wt-")
        baseline = _detached_checkout(ROOT, BASELINE_COMMIT, "sim010-baseline-wt-")
        current_environment = probe_worktree_environment(current, python)
        baseline_environment = probe_worktree_environment(baseline, python)
        validation = _run_regression(current, python)
        current_failures = failure_signatures(validation.stdout)
        baseline_result = _run_regression(baseline, python)
        baseline_failures = failure_signatures(baseline_result.stdout)
    except (OSError, RuntimeError) as exc:
        comparison_error = str(exc)
    finally:
        for checkout_path in (baseline, current):
            if checkout_path is None:
                continue
            try:
                _remove_checkout(ROOT, checkout_path)
            except RuntimeError as exc:
                comparison_error = str(exc)
    classification = classify_execution(
        validation.returncode if validation is not None else -1,
        baseline_result.returncode if baseline_result is not None else -1,
        current_failures,
        baseline_failures,
        comparison_error,
    )
    command = "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<detached>/src " + " ".join(regression_command(python))
    evidence["full_repository_regression"] = {
        "command": command,
        "candidate_commit": candidate_commit,
        "exit_code": validation.returncode if validation is not None else None,
        "result": "PASS" if validation is not None and validation.returncode == 0 else "FAIL",
        "baseline_commit": BASELINE_COMMIT,
        "python_executable": str(python),
        "qualified_environment": environment,
        "candidate_environment": current_environment,
        "baseline_environment": baseline_environment,
        "failure_classification": classification,
        "failed_node_ids": sorted(current_failures),
        "failure_signatures": current_failures,
        "baseline_failure_signatures": baseline_failures,
    }
    if baseline_result is not None:
        evidence["full_repository_regression"]["baseline_exit_code"] = baseline_result.returncode
    if comparison_error:
        evidence["full_repository_regression"]["comparison_error"] = comparison_error
    if validation is None or validation.returncode != 0:
        if classification == "PROVEN_PREEXISTING":
            evidence["full_repository_regression"]["blocking_reason"] = "PROVEN_PREEXISTING_FULL_REGRESSION_FAILURES"
        else:
            evidence["task_specific_result"] = "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
            evidence["full_repository_regression"]["blocking_reason"] = "FULL_REGRESSION_FAILED"
    evidence["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence["source_git_sha"] = candidate_commit
    path = ROOT / "results/simulation/SIM-010_observability_regression.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY" and validation is not None and (validation.returncode == 0 or classification == "PROVEN_PREEXISTING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
