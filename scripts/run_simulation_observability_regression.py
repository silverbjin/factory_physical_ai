#!/usr/bin/env python3
"""Generate the TASK-SIM-010 accepted-evidence regression artifact."""
from __future__ import annotations

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
COMMAND = ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def _run_regression(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(COMMAND, cwd=cwd, text=True, capture_output=True, check=False, env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})


def _baseline_checkout(root: Path) -> Path:
    temporary = Path(tempfile.mkdtemp(prefix="sim010-baseline-wt-"))
    temporary.rmdir()
    checkout = subprocess.run(
        ["git", "worktree", "add", "--detach", str(temporary), BASELINE_COMMIT],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if checkout.returncode:
        raise RuntimeError("BASELINE_WORKTREE_CREATE_FAILED")
    return temporary


def _remove_baseline_checkout(root: Path, baseline: Path) -> None:
    removal = subprocess.run(
        ["git", "worktree", "remove", "--force", str(baseline)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if removal.returncode:
        raise RuntimeError("BASELINE_WORKTREE_CLEANUP_FAILED")


def main() -> int:
    evidence = build_regression_evidence(ROOT)
    validation = _run_regression(ROOT)
    current_failures = failure_signatures(validation.stdout)
    baseline_error = None
    baseline_failures: dict[str, str] = {}
    baseline_result = None
    baseline = None
    try:
        baseline = _baseline_checkout(ROOT)
        baseline_result = _run_regression(baseline)
        baseline_failures = failure_signatures(baseline_result.stdout)
    except (OSError, RuntimeError) as exc:
        baseline_error = str(exc)
    finally:
        if baseline is not None:
            try:
                _remove_baseline_checkout(ROOT, baseline)
            except RuntimeError as exc:
                baseline_error = str(exc)
    classification = "POSSIBLY_TASK_RELATED" if baseline_error else classify_regression_failures(current_failures, baseline_failures)
    evidence["full_repository_regression"] = {
        "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider",
        "exit_code": validation.returncode,
        "result": "PASS" if validation.returncode == 0 else "FAIL",
        "baseline_commit": BASELINE_COMMIT,
        "python_executable": shutil.which("python3"),
        "virtual_env": os.environ.get("VIRTUAL_ENV"),
        "failure_classification": classification,
        "failed_node_ids": sorted(current_failures),
        "failure_signatures": current_failures,
        "baseline_failure_signatures": baseline_failures,
    }
    if baseline_result is not None:
        evidence["full_repository_regression"]["baseline_exit_code"] = baseline_result.returncode
    if baseline_error:
        evidence["full_repository_regression"]["baseline_error"] = baseline_error
    if validation.returncode != 0:
        if classification == "PROVEN_PREEXISTING":
            evidence["full_repository_regression"]["blocking_reason"] = "PROVEN_PREEXISTING_FULL_REGRESSION_FAILURES"
        else:
            evidence["task_specific_result"] = "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
            evidence["full_repository_regression"]["blocking_reason"] = "FULL_REGRESSION_FAILED"
    evidence["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence["source_git_sha"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
    path = ROOT / "results/simulation/SIM-010_observability_regression.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY" and (validation.returncode == 0 or classification == "PROVEN_PREEXISTING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
