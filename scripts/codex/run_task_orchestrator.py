#!/usr/bin/env python3
"""
Bounded-context Codex TASK orchestrator with:
- role-specific model routing;
- automatic Review-boundary Git commits;
- post-ACCEPT acceptance recording;
- separate acceptance-record commit;
- fail-closed range execution.

Each worker stage uses a fresh `codex exec`.

Default model policy:
    implementation -> GPT-5.6 Terra / medium
    review         -> GPT-5.6 Sol / low
    fix            -> GPT-5.6 Terra / medium
    re-review      -> GPT-5.6 Sol / low
    acceptance     -> GPT-5.6 Luna / low

The policy is loaded from:
    config/codex_model_policy.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKFLOW_RESULT_PREFIX = "WORKFLOW_RESULT_JSON:"
ACCEPTANCE_RESULT_PREFIX = "ACCEPTANCE_RESULT_JSON:"
TASK_RE = re.compile(r"^(?P<prefix>TASK-[A-Z0-9]+-)(?P<num>\d+)$")
PROTECTED_BRANCHES = {"main", "master"}
DEFAULT_MODEL_POLICY_PATH = Path("config/codex_model_policy.json")


class OrchestratorError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelConfig:
    model: str
    reasoning_effort: str


@dataclass
class StageResult:
    task_id: str
    stage: str
    status: str
    payload: dict[str, Any]


@dataclass
class AcceptanceResult:
    task_id: str
    status: str
    accepted_commit: str
    acceptance_path: str | None
    payload: dict[str, Any]


def run_git(
    repo: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise OrchestratorError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def current_branch(repo: Path) -> str:
    proc = run_git(
        repo,
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise OrchestratorError(
            "AUTO_COMMIT_BLOCKED: detached HEAD is not supported. "
            "Switch to a dedicated automation branch."
        )
    return proc.stdout.strip()


def ensure_automation_branch(
    repo: Path,
    allow_protected_branch: bool = False,
) -> str:
    branch = current_branch(repo)
    if branch in PROTECTED_BRANCHES and not allow_protected_branch:
        raise OrchestratorError(
            f"AUTO_COMMIT_BLOCKED: branch '{branch}' is protected. "
            "Create a dedicated branch, e.g. "
            "`git switch -c automate/sim-002-004`, "
            "or explicitly pass --allow-protected-branch."
        )
    return branch


def worktree_status(repo: Path) -> str:
    return run_git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip()


def changed_paths(repo: Path) -> list[str]:
    status = worktree_status(repo)
    if not status:
        return []

    paths: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return sorted(set(paths))


def ensure_clean_worktree(repo: Path) -> None:
    status = worktree_status(repo)
    if status:
        raise OrchestratorError(
            "AUTO_COMMIT_BLOCKED: worktree is not clean.\n" + status
        )


def load_model_policy(repo: Path, policy_path: Path) -> dict[str, ModelConfig]:
    resolved = policy_path
    if not resolved.is_absolute():
        resolved = repo / resolved

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrchestratorError(
            f"Model policy not found: {resolved}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise OrchestratorError(
            f"Invalid model policy JSON: {resolved}"
        ) from exc

    required_roles = {
        "implementation",
        "review",
        "fix",
        "rereview",
        "acceptance",
    }

    policy: dict[str, ModelConfig] = {}
    for role in required_roles:
        item = raw.get(role)
        if not isinstance(item, dict):
            raise OrchestratorError(
                f"Missing model policy role: {role}"
            )
        model = item.get("model")
        effort = item.get("reasoning_effort")
        if not isinstance(model, str) or not model:
            raise OrchestratorError(
                f"Invalid model for role: {role}"
            )
        if not isinstance(effort, str) or not effort:
            raise OrchestratorError(
                f"Invalid reasoning effort for role: {role}"
            )
        policy[role] = ModelConfig(model=model, reasoning_effort=effort)

    return policy


def parse_json_marker(text: str, prefix: str) -> dict[str, Any]:
    candidates: list[str] = []
    for line in text.splitlines():
        if prefix in line:
            candidates.append(line.split(prefix, 1)[1].strip())

    if not candidates:
        raise OrchestratorError(
            f"Missing {prefix} marker in Codex final response."
        )

    raw = candidates[-1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OrchestratorError(
            f"Invalid marker JSON after {prefix}: {raw}"
        ) from exc

    if not isinstance(payload, dict):
        raise OrchestratorError(
            f"Marker after {prefix} must be a JSON object."
        )

    return payload


def parse_workflow_result(text: str) -> StageResult:
    payload = parse_json_marker(text, WORKFLOW_RESULT_PREFIX)

    for key in ("task_id", "stage", "status"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise OrchestratorError(
                f"Missing/invalid workflow result field: {key}"
            )

    if not isinstance(payload.get("workflow_complete"), bool):
        raise OrchestratorError(
            "Missing/invalid workflow result field: workflow_complete"
        )

    return StageResult(
        task_id=payload["task_id"],
        stage=payload["stage"],
        status=payload["status"],
        payload=payload,
    )


def parse_acceptance_result(text: str) -> AcceptanceResult:
    payload = parse_json_marker(text, ACCEPTANCE_RESULT_PREFIX)

    for key in ("task_id", "status", "accepted_commit"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise OrchestratorError(
                f"Missing/invalid acceptance result field: {key}"
            )

    if not isinstance(payload.get("workflow_complete"), bool):
        raise OrchestratorError(
            "Missing/invalid acceptance field: workflow_complete"
        )

    acceptance_path = payload.get("acceptance_path")
    if acceptance_path is not None and not isinstance(acceptance_path, str):
        raise OrchestratorError(
            "acceptance_path must be a string or null"
        )

    return AcceptanceResult(
        task_id=payload["task_id"],
        status=payload["status"],
        accepted_commit=payload["accepted_commit"],
        acceptance_path=acceptance_path,
        payload=payload,
    )


def run_codex_text(
    prompt: str,
    repo: Path,
    config: ModelConfig,
) -> str:
    if shutil.which("codex") is None:
        raise OrchestratorError(
            "`codex` executable was not found on PATH."
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="codex-last-",
        suffix=".txt",
        delete=False,
    ) as handle:
        last_message = Path(handle.name)

    try:
        cmd = [
            "codex",
            "exec",
            "--model",
            config.model,
            "--config",
            f'model_reasoning_effort="{config.reasoning_effort}"',
            "--config",
            'model_verbosity="low"',
            "--output-last-message",
            str(last_message),
            prompt,
        ]

        proc = subprocess.run(
            cmd,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            raise OrchestratorError(
                f"Codex stage failed with exit code {proc.returncode}: "
                f"{prompt}"
            )

        return last_message.read_text(encoding="utf-8")
    finally:
        last_message.unlink(missing_ok=True)


def run_stage(
    prompt: str,
    repo: Path,
    config: ModelConfig,
) -> StageResult:
    return parse_workflow_result(
        run_codex_text(prompt, repo, config)
    )


def run_acceptance(
    prompt: str,
    repo: Path,
    config: ModelConfig,
) -> AcceptanceResult:
    return parse_acceptance_result(
        run_codex_text(prompt, repo, config)
    )


def require_result(
    result: StageResult,
    *,
    task_id: str,
    stage: str,
    allowed: set[str],
) -> None:
    if result.task_id != task_id:
        raise OrchestratorError(
            f"TASK identity mismatch: expected {task_id}, "
            f"got {result.task_id}"
        )
    if result.stage != stage:
        raise OrchestratorError(
            f"Stage mismatch: expected {stage}, got {result.stage}"
        )
    if result.status not in allowed:
        raise OrchestratorError(
            f"Unexpected {stage} status: {result.status}; "
            f"allowed={sorted(allowed)}"
        )


def workflow_is_complete(result: StageResult) -> bool:
    return bool(result.payload["workflow_complete"])


def task_scope(task_id: str) -> str:
    match = TASK_RE.fullmatch(task_id)
    if match:
        prefix = match.group("prefix")
        middle = prefix[len("TASK-"):-1]
        return middle.lower()
    return "task"


def task_short(task_id: str) -> str:
    if not task_id.startswith("TASK-"):
        raise OrchestratorError(
            f"Invalid TASK_ID: {task_id}"
        )
    return task_id[len("TASK-"):]


def expected_acceptance_filename(task_id: str) -> str:
    return f"{task_short(task_id)}_acceptance.json"


def commit_subject(
    task_id: str,
    boundary: str,
    review_status: str | None = None,
) -> str:
    scope = task_scope(task_id)

    if boundary == "implementation-review":
        if review_status not in {"ACCEPT", "REJECT"}:
            raise OrchestratorError(
                "Review status required for implementation-review commit"
            )
        return (
            f"feat({scope}): {task_id} "
            f"implementation reviewed [{review_status}]"
        )

    if boundary == "fix-rereview":
        if review_status == "ACCEPT":
            return (
                f"fix({scope}): {task_id} "
                "review findings resolved [ACCEPT]"
            )
        if review_status == "REJECT":
            return (
                f"fix({scope}): {task_id} "
                "review findings reviewed [REJECT]"
            )
        raise OrchestratorError(
            "Review status required for fix-rereview commit"
        )

    if boundary == "acceptance":
        return (
            f"chore({scope}): record {task_id} acceptance [ACCEPT]"
        )

    raise OrchestratorError(
        f"Unknown commit boundary: {boundary}"
    )


def commit_all_changes(
    repo: Path,
    *,
    task_id: str,
    boundary: str,
    review_status: str | None = None,
) -> str:
    run_git(repo, "add", "-A")
    run_git(repo, "diff", "--cached", "--check")

    staged = run_git(
        repo,
        "diff",
        "--cached",
        "--quiet",
        check=False,
    )
    allow_empty = staged.returncode == 0

    subject = commit_subject(
        task_id,
        boundary,
        review_status=review_status,
    )

    body_lines = [
        f"Task: {task_id}",
        f"Workflow-Stage: {boundary}",
        "Automation: codex-task-orchestrator",
    ]
    if review_status is not None:
        body_lines.append(f"Review-Result: {review_status}")

    cmd = ["commit"]
    if allow_empty:
        cmd.append("--allow-empty")
    cmd.extend(
        [
            "-m",
            subject,
            "-m",
            "\n".join(body_lines),
        ]
    )

    run_git(repo, *cmd)

    commit_hash = run_git(
        repo,
        "rev-parse",
        "HEAD",
    ).stdout.strip()
    ensure_clean_worktree(repo)
    return commit_hash


def validate_acceptance_write(
    repo: Path,
    result: AcceptanceResult,
    *,
    task_id: str,
    accepted_commit: str,
) -> Path:
    if result.task_id != task_id:
        raise OrchestratorError(
            f"Acceptance TASK mismatch: expected {task_id}, "
            f"got {result.task_id}"
        )

    if result.status != "RECORDED":
        raise OrchestratorError(
            f"Acceptance recording did not succeed: {result.status}"
        )

    if not result.payload.get("workflow_complete"):
        raise OrchestratorError(
            "Acceptance workflow incomplete."
        )

    if result.accepted_commit != accepted_commit:
        raise OrchestratorError(
            "Acceptance commit mismatch: "
            f"expected {accepted_commit}, "
            f"got {result.accepted_commit}"
        )

    if not result.acceptance_path:
        raise OrchestratorError(
            "Acceptance result did not provide acceptance_path."
        )

    rel_path = Path(result.acceptance_path)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise OrchestratorError(
            f"Unsafe acceptance_path: {rel_path}"
        )

    if rel_path.name != expected_acceptance_filename(task_id):
        raise OrchestratorError(
            "Acceptance filename mismatch: "
            f"expected {expected_acceptance_filename(task_id)}, "
            f"got {rel_path.name}"
        )

    abs_path = repo / rel_path
    if not abs_path.is_file():
        raise OrchestratorError(
            f"Acceptance file not found: {rel_path}"
        )

    paths = changed_paths(repo)
    if paths != [rel_path.as_posix()]:
        raise OrchestratorError(
            "Acceptance worker changed unexpected files. "
            f"Expected only {rel_path.as_posix()}, got {paths}"
        )

    try:
        artifact = json.loads(
            abs_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise OrchestratorError(
            f"Acceptance artifact is invalid JSON: {rel_path}"
        ) from exc

    if artifact.get("task_id") != task_id:
        raise OrchestratorError(
            "Acceptance artifact task_id mismatch."
        )
    if artifact.get("status") != "ACCEPT":
        raise OrchestratorError(
            "Acceptance artifact status must be ACCEPT."
        )
    if artifact.get("accepted_commit") != accepted_commit:
        raise OrchestratorError(
            "Acceptance artifact accepted_commit mismatch."
        )

    return rel_path


def record_acceptance_and_commit(
    repo: Path,
    *,
    task_id: str,
    accepted_commit: str,
    config: ModelConfig,
) -> tuple[str, str]:
    """
    Run a fresh, low-cost acceptance worker against a clean accepted snapshot,
    validate that it changed exactly one acceptance JSON, then commit it.
    """
    ensure_clean_worktree(repo)

    head = run_git(
        repo,
        "rev-parse",
        "HEAD",
    ).stdout.strip()
    if head != accepted_commit:
        raise OrchestratorError(
            "Acceptance recording requires HEAD to equal accepted_commit. "
            f"HEAD={head}, accepted_commit={accepted_commit}"
        )

    prompt = (
        f"Record {task_id} acceptance for commit {accepted_commit}"
    )
    result = run_acceptance(prompt, repo, config)

    rel_path = validate_acceptance_write(
        repo,
        result,
        task_id=task_id,
        accepted_commit=accepted_commit,
    )

    acceptance_commit = commit_all_changes(
        repo,
        task_id=task_id,
        boundary="acceptance",
    )

    return rel_path.as_posix(), acceptance_commit


def stage_event(
    result: StageResult,
    config: ModelConfig,
    *,
    role: str,
) -> dict[str, Any]:
    event = dict(result.payload)
    event["model_role"] = role
    event["model"] = config.model
    event["reasoning_effort"] = config.reasoning_effort
    return event


def commit_event(
    *,
    task_id: str,
    boundary: str,
    commit_hash: str,
    review_status: str | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "stage": "git_commit",
        "boundary": boundary,
        "review_status": review_status,
        "commit": commit_hash,
        "workflow_complete": True,
    }


def acceptance_event(
    *,
    task_id: str,
    accepted_commit: str,
    acceptance_path: str,
    acceptance_commit: str,
    config: ModelConfig,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "stage": "acceptance",
        "status": "RECORDED",
        "accepted_commit": accepted_commit,
        "acceptance_path": acceptance_path,
        "acceptance_commit": acceptance_commit,
        "model_role": "acceptance",
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "workflow_complete": True,
    }


def finalize_accept(
    repo: Path,
    *,
    task_id: str,
    accepted_commit: str,
    acceptance_config: ModelConfig,
    commits: list[str],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        acceptance_path, acceptance_commit = (
            record_acceptance_and_commit(
                repo,
                task_id=task_id,
                accepted_commit=accepted_commit,
                config=acceptance_config,
            )
        )
    except OrchestratorError as exc:
        return {
            "task_id": task_id,
            "status": "ACCEPTANCE_RECORD_FAILED",
            "accepted_commit": accepted_commit,
            "acceptance_path": None,
            "acceptance_commit": None,
            "commits": commits,
            "events": events,
            "error": str(exc),
        }

    commits.append(acceptance_commit)
    events.append(
        acceptance_event(
            task_id=task_id,
            accepted_commit=accepted_commit,
            acceptance_path=acceptance_path,
            acceptance_commit=acceptance_commit,
            config=acceptance_config,
        )
    )

    return {
        "task_id": task_id,
        "status": "ACCEPTED",
        "accepted_commit": accepted_commit,
        "acceptance_path": acceptance_path,
        "acceptance_commit": acceptance_commit,
        "commits": commits,
        "events": events,
    }


def run_task(
    task_id: str,
    repo: Path,
    policy: dict[str, ModelConfig],
    max_fix_cycles: int = 1,
) -> dict[str, Any]:
    ensure_clean_worktree(repo)
    events: list[dict[str, Any]] = []
    commits: list[str] = []

    implementation = run_stage(
        f"Implement {task_id}",
        repo,
        policy["implementation"],
    )
    require_result(
        implementation,
        task_id=task_id,
        stage="implementation",
        allowed={"COMPLETE", "INCOMPLETE"},
    )
    events.append(
        stage_event(
            implementation,
            policy["implementation"],
            role="implementation",
        )
    )

    if not workflow_is_complete(implementation):
        return {
            "task_id": task_id,
            "status": "IMPLEMENTATION_WORKFLOW_INCOMPLETE",
            "commits": commits,
            "events": events,
        }

    if implementation.status != "COMPLETE":
        return {
            "task_id": task_id,
            "status": "INCOMPLETE",
            "commits": commits,
            "events": events,
        }

    review = run_stage(
        task_id,
        repo,
        policy["review"],
    )
    require_result(
        review,
        task_id=task_id,
        stage="review",
        allowed={"ACCEPT", "REJECT"},
    )
    events.append(
        stage_event(
            review,
            policy["review"],
            role="review",
        )
    )

    if not workflow_is_complete(review):
        return {
            "task_id": task_id,
            "status": "REVIEW_WORKFLOW_INCOMPLETE",
            "commits": commits,
            "events": events,
        }

    first_commit = commit_all_changes(
        repo,
        task_id=task_id,
        boundary="implementation-review",
        review_status=review.status,
    )
    commits.append(first_commit)
    events.append(
        commit_event(
            task_id=task_id,
            boundary="implementation-review",
            review_status=review.status,
            commit_hash=first_commit,
        )
    )

    if review.status == "ACCEPT":
        return finalize_accept(
            repo,
            task_id=task_id,
            accepted_commit=first_commit,
            acceptance_config=policy["acceptance"],
            commits=commits,
            events=events,
        )

    if max_fix_cycles == 0:
        return {
            "task_id": task_id,
            "status": "REJECTED_NO_FIX",
            "commits": commits,
            "events": events,
        }

    for _ in range(max_fix_cycles):
        ensure_clean_worktree(repo)

        fix = run_stage(
            f"Fix {task_id}",
            repo,
            policy["fix"],
        )
        require_result(
            fix,
            task_id=task_id,
            stage="fix",
            allowed={
                "READY_FOR_RE_REVIEW",
                "NOT_READY_FOR_RE_REVIEW",
            },
        )
        events.append(
            stage_event(
                fix,
                policy["fix"],
                role="fix",
            )
        )

        if not workflow_is_complete(fix):
            return {
                "task_id": task_id,
                "status": "FIX_WORKFLOW_INCOMPLETE",
                "commits": commits,
                "events": events,
            }

        if fix.status != "READY_FOR_RE_REVIEW":
            return {
                "task_id": task_id,
                "status": "FIX_NOT_READY",
                "commits": commits,
                "events": events,
            }

        rereview = run_stage(
            task_id,
            repo,
            policy["rereview"],
        )
        require_result(
            rereview,
            task_id=task_id,
            stage="review",
            allowed={"ACCEPT", "REJECT"},
        )
        events.append(
            stage_event(
                rereview,
                policy["rereview"],
                role="rereview",
            )
        )

        if not workflow_is_complete(rereview):
            return {
                "task_id": task_id,
                "status": "REVIEW_WORKFLOW_INCOMPLETE",
                "commits": commits,
                "events": events,
            }

        fix_commit = commit_all_changes(
            repo,
            task_id=task_id,
            boundary="fix-rereview",
            review_status=rereview.status,
        )
        commits.append(fix_commit)
        events.append(
            commit_event(
                task_id=task_id,
                boundary="fix-rereview",
                review_status=rereview.status,
                commit_hash=fix_commit,
            )
        )

        if rereview.status == "ACCEPT":
            return finalize_accept(
                repo,
                task_id=task_id,
                accepted_commit=fix_commit,
                acceptance_config=policy["acceptance"],
                commits=commits,
                events=events,
            )

    return {
        "task_id": task_id,
        "status": "REJECTED_AFTER_REVIEW",
        "commits": commits,
        "events": events,
    }


def expand_range(start: str, end: str) -> list[str]:
    sm = TASK_RE.fullmatch(start)
    em = TASK_RE.fullmatch(end)

    if not sm or not em:
        raise OrchestratorError(
            "TASK range requires IDs like TASK-SIM-002 TASK-SIM-004."
        )

    if sm.group("prefix") != em.group("prefix"):
        raise OrchestratorError(
            "TASK range prefixes must match."
        )

    start_num = int(sm.group("num"))
    end_num = int(em.group("num"))

    if end_num < start_num:
        raise OrchestratorError(
            "TASK range must be ascending."
        )

    width = max(
        len(sm.group("num")),
        len(em.group("num")),
    )
    prefix = sm.group("prefix")

    return [
        f"{prefix}{number:0{width}d}"
        for number in range(start_num, end_num + 1)
    ]


def run_range(
    start: str,
    end: str,
    repo: Path,
    policy: dict[str, ModelConfig],
    max_fix_cycles: int = 1,
) -> dict[str, Any]:
    tasks = expand_range(start, end)
    results: list[dict[str, Any]] = []
    all_commits: list[str] = []

    for index, task_id in enumerate(tasks):
        ensure_clean_worktree(repo)

        result = run_task(
            task_id,
            repo,
            policy,
            max_fix_cycles=max_fix_cycles,
        )
        results.append(result)
        all_commits.extend(
            result.get("commits", [])
        )

        if result["status"] != "ACCEPTED":
            next_task = (
                tasks[index + 1]
                if index + 1 < len(tasks)
                else None
            )
            return {
                "range": f"{start}..{end}",
                "status": "STOPPED",
                "accepted": [
                    item["task_id"]
                    for item in results
                    if item["status"] == "ACCEPTED"
                ],
                "commits": all_commits,
                "stopping_task": task_id,
                "stopping_status": result["status"],
                "worktree_clean": not bool(
                    worktree_status(repo)
                ),
                "next_unexecuted_task": next_task,
                "task_results": results,
            }

        ensure_clean_worktree(repo)

    return {
        "range": f"{start}..{end}",
        "status": "COMPLETE",
        "accepted": tasks,
        "commits": all_commits,
        "stopping_task": None,
        "stopping_status": None,
        "worktree_clean": True,
        "next_unexecuted_task": None,
        "task_results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root; defaults to current directory.",
    )
    parser.add_argument(
        "--model-policy",
        type=Path,
        default=DEFAULT_MODEL_POLICY_PATH,
        help=(
            "Model policy JSON path relative to repo root "
            "(default: config/codex_model_policy.json)."
        ),
    )
    parser.add_argument(
        "--max-fix-cycles",
        type=int,
        default=1,
        choices=range(0, 4),
        metavar="N",
        help=(
            "Maximum Fix + Re-review cycles per TASK "
            "(default: 1)."
        ),
    )
    parser.add_argument(
        "--allow-protected-branch",
        action="store_true",
        help=(
            "Allow auto-commit on main/master. "
            "Not recommended."
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    task_parser = sub.add_parser("task")
    task_parser.add_argument("task_id")

    range_parser = sub.add_parser("range")
    range_parser.add_argument("start_task_id")
    range_parser.add_argument("end_task_id")

    args = parser.parse_args()
    repo = args.repo.resolve()

    if not (repo / ".git").exists():
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error": (
                        f"Not a Git repository: {repo}"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    try:
        branch = ensure_automation_branch(
            repo,
            allow_protected_branch=(
                args.allow_protected_branch
            ),
        )
        ensure_clean_worktree(repo)
        policy = load_model_policy(
            repo,
            args.model_policy,
        )

        if args.command == "task":
            result = run_task(
                args.task_id,
                repo,
                policy,
                max_fix_cycles=args.max_fix_cycles,
            )
        else:
            result = run_range(
                args.start_task_id,
                args.end_task_id,
                repo,
                policy,
                max_fix_cycles=args.max_fix_cycles,
            )

        result["branch"] = branch
        result["model_policy"] = {
            role: {
                "model": cfg.model,
                "reasoning_effort": (
                    cfg.reasoning_effort
                ),
            }
            for role, cfg in policy.items()
        }

    except OrchestratorError as exc:
        result = {
            "status": "ERROR",
            "error": str(exc),
            "worktree_clean": (
                not bool(worktree_status(repo))
                if (repo / ".git").exists()
                else None
            ),
        }
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.command == "task":
        return (
            0
            if result.get("status") == "ACCEPTED"
            else 1
        )

    return (
        0
        if result.get("status") == "COMPLETE"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
