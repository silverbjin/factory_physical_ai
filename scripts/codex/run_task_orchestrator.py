#!/usr/bin/env python3
"""Host-side bounded-context Codex TASK orchestrator.

Key properties:
- quiet progress console by default;
- full child stdout/stderr persisted outside the repository;
- child final responses persisted separately;
- stage/protocol/Git errors collected rather than lost in terminal noise;
- summary.md + run_report.json written for every run;
- explicit next_action in every terminal report;
- Review-boundary + acceptance commits remain fail-closed.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKFLOW_RESULT_PREFIX = "WORKFLOW_RESULT_JSON:"
ACCEPTANCE_RESULT_PREFIX = "ACCEPTANCE_RESULT_JSON:"
TASK_RE = re.compile(r"^(?P<prefix>TASK-[A-Z0-9]+-)(?P<num>\d+)$")
PROTECTED_BRANCHES = {"main", "master"}
DEFAULT_MODEL_POLICY_PATH = Path("config/codex_model_policy.json")
SIGNAL_RE = re.compile(
    r"(status|result|evidence|error|fail|failed|failure|blocked|blocker|"
    r"incomplete|reject|missing|cannot|unable|next|deviation|reason|token|context|limit|quota|credit|"
    r"실패|차단|원인|다음|불완전|토큰|한도)",
    re.IGNORECASE,
)


class OrchestratorError(RuntimeError):
    pass


class ChildProcessError(OrchestratorError):
    def __init__(self, message: str, *, task_id: str, role: str, log_path: Path, final_path: Path):
        super().__init__(message)
        self.task_id = task_id
        self.role = role
        self.log_path = log_path
        self.final_path = final_path


class ChildProtocolError(OrchestratorError):
    def __init__(
        self,
        message: str,
        *,
        task_id: str,
        role: str,
        log_path: Path,
        final_path: Path,
        final_message: str,
    ):
        super().__init__(message)
        self.task_id = task_id
        self.role = role
        self.log_path = log_path
        self.final_path = final_path
        self.final_message = final_message


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


@dataclass
class StageRunRecord:
    task_id: str
    role: str
    model: str
    reasoning_effort: str
    started_at: str
    ended_at: str | None = None
    duration_seconds: float | None = None
    exit_code: int | None = None
    result_status: str | None = None
    workflow_complete: bool | None = None
    log_path: str | None = None
    final_path: str | None = None
    prompt_path: str | None = None
    tokens_reported: int | None = None
    signals: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


@dataclass
class ErrorRecord:
    kind: str
    stage: str
    task_id: str
    message: str
    signals: list[str] = field(default_factory=list)
    log_path: str | None = None
    final_path: str | None = None


class RunContext:
    def __init__(
        self,
        *,
        repo: Path,
        target: str,
        report_base: Path,
        verbose: bool,
        show_tail: int,
        heartbeat_seconds: int,
    ) -> None:
        self.repo = repo
        self.target = target
        self.verbose = verbose
        self.show_tail = max(0, show_tail)
        self.heartbeat_seconds = max(0, heartbeat_seconds)
        self.started_monotonic = time.monotonic()
        self.started_at = iso_now()
        self.stage_records: list[StageRunRecord] = []
        self.errors: list[ErrorRecord] = []
        self.sequence = 0

        repo_key = safe_name(repo.name or "repo")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_key = safe_name(target)
        self.run_dir = report_base.expanduser().resolve() / repo_key / f"{stamp}_{target_key}"
        self.run_dir.mkdir(parents=True, exist_ok=False)

    def progress(self, kind: str, message: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {kind:<7} {message}", flush=True)

    def new_stage(self, task_id: str, role: str, config: ModelConfig) -> StageRunRecord:
        self.sequence += 1
        stem = f"{self.sequence:02d}_{safe_name(task_id)}_{safe_name(role)}"
        record = StageRunRecord(
            task_id=task_id,
            role=role,
            model=config.model,
            reasoning_effort=config.reasoning_effort,
            started_at=iso_now(),
            log_path=str(self.run_dir / f"{stem}.log"),
            final_path=str(self.run_dir / f"{stem}_final.txt"),
            prompt_path=str(self.run_dir / f"{stem}_prompt.txt"),
        )
        self.stage_records.append(record)
        return record

    def add_error(
        self,
        *,
        kind: str,
        stage: str,
        task_id: str,
        message: str,
        signals: list[str] | None = None,
        log_path: str | None = None,
        final_path: str | None = None,
    ) -> None:
        self.errors.append(
            ErrorRecord(
                kind=kind,
                stage=stage,
                task_id=task_id,
                message=message,
                signals=signals or [],
                log_path=log_path,
                final_path=final_path,
            )
        )


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "run"


def default_report_base() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg) / "codex-task-orchestrator"
    return Path.home() / ".local" / "state" / "codex-task-orchestrator"


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
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
    proc = run_git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise OrchestratorError(
            "AUTO_COMMIT_BLOCKED: detached HEAD is not supported. "
            "Switch to a dedicated automation branch."
        )
    return proc.stdout.strip()


def ensure_automation_branch(repo: Path, allow_protected_branch: bool = False) -> str:
    branch = current_branch(repo)
    if branch in PROTECTED_BRANCHES and not allow_protected_branch:
        raise OrchestratorError(
            f"AUTO_COMMIT_BLOCKED: branch '{branch}' is protected. "
            "Create a dedicated automation branch or explicitly pass "
            "--allow-protected-branch."
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
        raise OrchestratorError("AUTO_COMMIT_BLOCKED: worktree is not clean.\n" + status)


def load_model_policy(repo: Path, policy_path: Path) -> dict[str, ModelConfig]:
    resolved = policy_path if policy_path.is_absolute() else repo / policy_path
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrchestratorError(f"Model policy not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid model policy JSON: {resolved}") from exc

    required_roles = {"implementation", "review", "fix", "rereview", "acceptance"}
    policy: dict[str, ModelConfig] = {}
    for role in required_roles:
        item = raw.get(role)
        if not isinstance(item, dict):
            raise OrchestratorError(f"Missing model policy role: {role}")
        model = item.get("model")
        effort = item.get("reasoning_effort")
        if not isinstance(model, str) or not model:
            raise OrchestratorError(f"Invalid model for role: {role}")
        if not isinstance(effort, str) or not effort:
            raise OrchestratorError(f"Invalid reasoning effort for role: {role}")
        policy[role] = ModelConfig(model=model, reasoning_effort=effort)
    return policy


def tail_text(path: Path, max_bytes: int = 65536) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return data[-max_bytes:].decode("utf-8", errors="replace")


def extract_tokens(log_path: Path) -> int | None:
    text = tail_text(log_path)
    matches = re.findall(r"tokens\s+used\s*\n?\s*([\d,]+)", text, re.IGNORECASE)
    if not matches:
        return None
    try:
        return int(matches[-1].replace(",", ""))
    except ValueError:
        return None


def extract_signal_lines(text: str, limit: int = 12) -> list[str]:
    signals: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip().strip("` ")
        if not line or WORKFLOW_RESULT_PREFIX in line or ACCEPTANCE_RESULT_PREFIX in line:
            continue
        if SIGNAL_RE.search(line):
            compact = re.sub(r"\s+", " ", line)
            if compact not in seen:
                seen.add(compact)
                signals.append(compact[:500])
        if len(signals) >= limit:
            break
    return signals


def parse_json_marker(text: str, prefix: str, *, task_id: str, role: str, log_path: Path, final_path: Path) -> dict[str, Any]:
    candidates: list[str] = []
    for line in text.splitlines():
        if prefix in line:
            candidates.append(line.split(prefix, 1)[1].strip())
    if not candidates:
        raise ChildProtocolError(
            f"Missing {prefix} marker in Codex final response.",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        )
    raw = candidates[-1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ChildProtocolError(
            f"Invalid marker JSON after {prefix}: {raw}",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        ) from exc
    if not isinstance(payload, dict):
        raise ChildProtocolError(
            f"Marker after {prefix} must be a JSON object.",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        )
    return payload


def parse_workflow_result(text: str, *, task_id: str = "UNKNOWN", role: str = "worker", log_path: Path | None = None, final_path: Path | None = None) -> StageResult:
    log_path = log_path or Path("<unknown-log>")
    final_path = final_path or Path("<unknown-final>")
    payload = parse_json_marker(
        text,
        WORKFLOW_RESULT_PREFIX,
        task_id=task_id,
        role=role,
        log_path=log_path,
        final_path=final_path,
    )
    for key in ("task_id", "stage", "status"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ChildProtocolError(
                f"Missing/invalid workflow result field: {key}",
                task_id=task_id,
                role=role,
                log_path=log_path,
                final_path=final_path,
                final_message=text,
            )
    if not isinstance(payload.get("workflow_complete"), bool):
        raise ChildProtocolError(
            "Missing/invalid workflow result field: workflow_complete",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        )
    return StageResult(
        task_id=payload["task_id"],
        stage=payload["stage"],
        status=payload["status"],
        payload=payload,
    )


def parse_acceptance_result(text: str, *, task_id: str = "UNKNOWN", role: str = "acceptance", log_path: Path | None = None, final_path: Path | None = None) -> AcceptanceResult:
    log_path = log_path or Path("<unknown-log>")
    final_path = final_path or Path("<unknown-final>")
    payload = parse_json_marker(
        text,
        ACCEPTANCE_RESULT_PREFIX,
        task_id=task_id,
        role=role,
        log_path=log_path,
        final_path=final_path,
    )
    for key in ("task_id", "status", "accepted_commit"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ChildProtocolError(
                f"Missing/invalid acceptance result field: {key}",
                task_id=task_id,
                role=role,
                log_path=log_path,
                final_path=final_path,
                final_message=text,
            )
    if not isinstance(payload.get("workflow_complete"), bool):
        raise ChildProtocolError(
            "Missing/invalid acceptance field: workflow_complete",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        )
    acceptance_path = payload.get("acceptance_path")
    if acceptance_path is not None and not isinstance(acceptance_path, str):
        raise ChildProtocolError(
            "acceptance_path must be a string or null",
            task_id=task_id,
            role=role,
            log_path=log_path,
            final_path=final_path,
            final_message=text,
        )
    return AcceptanceResult(
        task_id=payload["task_id"],
        status=payload["status"],
        accepted_commit=payload["accepted_commit"],
        acceptance_path=acceptance_path,
        payload=payload,
    )


def _reader_thread(stream: Any, q: queue.Queue[str | None]) -> None:
    try:
        for line in iter(stream.readline, ""):
            q.put(line)
    finally:
        q.put(None)



CHILD_ROLE_PROMPTS = {
    "implementation": "prompts/codex/implement_task_v2.md",
    "review": "prompts/codex/read_only_review_v2.md",
    "rereview": "prompts/codex/read_only_review_v2.md",
    "fix": "prompts/codex/fix_review_findings_v2.md",
    "acceptance": "prompts/codex/record_task_acceptance_v2.md",
}


def child_prompt(
    *,
    task_id: str,
    worker_role: str,
    accepted_commit: str | None = None,
    resume: bool = False,
    resume_from_stage: str | None = None,
    previous_run_dir: str | None = None,
    resume_reason: str | None = None,
) -> str:
    """Build an explicit child-worker envelope so Codex cannot confuse the worker
    with the host-side `Run ...` entry point.
    """
    if worker_role not in CHILD_ROLE_PROMPTS:
        raise OrchestratorError(f"Unsupported child worker role: {worker_role}")

    lines = [
        "ORCHESTRATOR_CHILD",
        "protocol_version=1",
        f"worker_role={worker_role}",
        f"task_id={task_id}",
        f"worker_prompt={CHILD_ROLE_PROMPTS[worker_role]}",
    ]

    if accepted_commit is not None:
        lines.append(f"accepted_commit={accepted_commit}")

    if resume:
        lines.append("resume=true")
        lines.append(f"resume_from_stage={resume_from_stage or worker_role}")
        if previous_run_dir:
            lines.append(f"previous_run_dir={previous_run_dir}")
        if resume_reason:
            lines.append(f"resume_reason={resume_reason}")

    lines.extend(
        [
            "",
            "You are already running as a child worker of",
            "scripts/codex/run_task_orchestrator.py.",
            "",
            "Do NOT invoke or recommend the host orchestrator.",
            "Do NOT redirect this work back to a normal terminal.",
            "Do NOT reinterpret this message as a host-side `Run ...` request.",
            "Execute exactly the declared worker_role using worker_prompt.",
            "Resolve only the supplied task_id.",
            "Finish with the mandatory machine-result marker required by worker_prompt",
            "as the last non-empty line of the final response.",
        ]
    )

    if resume:
        lines.extend(
            [
                "",
                "RESUME RULES:",
                "- Continue from the current repository/worktree state.",
                "- Do not reset, restore, clean, stash, checkout, or discard target-task changes.",
                "- Inspect existing partial target-task work before editing.",
                "- Do not repeat already completed lifecycle stages.",
                "- Complete only the declared resumed worker stage.",
                "- Re-run that stage's required validation before reporting completion.",
                "- Treat prior incomplete history/events as audit context, not proof of completion.",
            ]
        )

    return "\n".join(lines)



RESUMABLE_PHASES = {
    "implementation",
    "review",
    "commit_implementation_review",
    "fix",
    "rereview",
    "commit_fix_rereview",
    "acceptance",
    "commit_acceptance",
}


def resume_checkpoint_path(report_base: Path, repo: Path, task_id: str) -> Path:
    repo_key = safe_name(repo.name or "repo")
    base = report_base.expanduser().resolve() / repo_key
    base.mkdir(parents=True, exist_ok=True)
    return base / f"resume_{safe_name(task_id)}.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def save_resume_checkpoint(
    ctx: RunContext,
    task_id: str,
    state: dict[str, Any],
) -> Path:
    path = ctx.run_dir.parent / f"resume_{safe_name(task_id)}.json"
    state["schema_version"] = 1
    state["task_id"] = task_id
    state["repo"] = str(ctx.repo)
    state["current_run_dir"] = str(ctx.run_dir)
    state["updated_at"] = iso_now()
    try:
        state["current_head"] = run_git(
            ctx.repo, "rev-parse", "HEAD"
        ).stdout.strip()
    except Exception:
        state.setdefault("current_head", None)
    _atomic_write_json(path, state)
    return path


def load_resume_checkpoint(
    report_base: Path,
    repo: Path,
    task_id: str,
) -> tuple[Path, dict[str, Any]]:
    path = resume_checkpoint_path(report_base, repo, task_id)
    if not path.is_file():
        raise OrchestratorError(
            "No resume checkpoint found for "
            f"{task_id}: {path}. "
            "Use `resume <TASK_ID> --from-stage <stage>` only when "
            "manually recovering a run created before checkpoint support."
        )
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OrchestratorError(
            f"Invalid resume checkpoint JSON: {path}"
        ) from exc
    if state.get("task_id") != task_id:
        raise OrchestratorError(
            f"Resume checkpoint TASK mismatch: {state.get('task_id')} != {task_id}"
        )
    return path, state


def create_manual_resume_state(
    repo: Path,
    task_id: str,
    *,
    phase: str,
    max_fix_cycles: int,
) -> dict[str, Any]:
    if phase not in RESUMABLE_PHASES:
        raise OrchestratorError(f"Unsupported resume phase: {phase}")
    branch = current_branch(repo)
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    accepted_commit = head if phase in {"acceptance", "commit_acceptance"} else None
    return {
        "schema_version": 1,
        "task_id": task_id,
        "repo": str(repo),
        "branch": branch,
        "initial_head": head,
        "current_head": head,
        "phase": phase,
        "status": "MANUAL_RESUME",
        "review_status": None,
        "accepted_commit": accepted_commit,
        "acceptance_path": None,
        "acceptance_commit": None,
        "fix_cycles_used": 0,
        "max_fix_cycles": max_fix_cycles,
        "commits": [],
        "previous_run_dir": None,
        "current_run_dir": None,
        "updated_at": iso_now(),
    }


def transition_checkpoint(
    ctx: RunContext,
    state: dict[str, Any],
    *,
    phase: str | None = None,
    status: str | None = None,
    **updates: Any,
) -> Path:
    if phase is not None:
        state["phase"] = phase
    if status is not None:
        state["status"] = status
    state.update(updates)
    return save_resume_checkpoint(ctx, str(state["task_id"]), state)


def mark_checkpoint_interrupted(
    report_base: Path,
    repo: Path,
    task_id: str,
    *,
    error_type: str,
    error_message: str,
) -> None:
    try:
        path, state = load_resume_checkpoint(report_base, repo, task_id)
    except Exception:
        return
    state["status"] = "INTERRUPTED"
    state["last_error_type"] = error_type
    state["last_error"] = error_message
    state["updated_at"] = iso_now()
    try:
        state["current_head"] = run_git(
            repo, "rev-parse", "HEAD"
        ).stdout.strip()
    except Exception:
        pass
    _atomic_write_json(path, state)


def validate_resume_state(
    repo: Path,
    task_id: str,
    state: dict[str, Any],
    *,
    force: bool = False,
) -> None:
    if state.get("task_id") != task_id:
        raise OrchestratorError("Resume state TASK mismatch.")
    if state.get("phase") == "accepted" or state.get("status") == "ACCEPTED":
        raise OrchestratorError(f"{task_id} is already ACCEPTED; nothing to resume.")
    phase = str(state.get("phase") or "")
    if phase not in RESUMABLE_PHASES:
        raise OrchestratorError(
            f"Checkpoint phase is not resumable: {phase or '<missing>'}"
        )

    current = current_branch(repo)
    expected_branch = state.get("branch")
    if expected_branch and current != expected_branch and not force:
        raise OrchestratorError(
            f"Resume branch mismatch: current={current}, checkpoint={expected_branch}. "
            "Use --force only after manually verifying repository provenance."
        )

    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    expected_head = state.get("current_head")
    if expected_head and head != expected_head and not force:
        raise OrchestratorError(
            f"Resume HEAD mismatch: current={head}, checkpoint={expected_head}. "
            "Use --force only after manually verifying the intervening Git change."
        )


def resumable_worker_role(phase: str) -> str | None:
    return {
        "implementation": "implementation",
        "review": "review",
        "fix": "fix",
        "rereview": "rereview",
        "acceptance": "acceptance",
    }.get(phase)


def write_manual_resume_prompt(
    ctx: RunContext,
    state: dict[str, Any],
) -> Path | None:
    phase = str(state.get("phase") or "")
    role = resumable_worker_role(phase)
    if role is None:
        return None
    accepted_commit = state.get("accepted_commit") if role == "acceptance" else None
    prompt = child_prompt(
        task_id=str(state["task_id"]),
        worker_role=role,
        accepted_commit=accepted_commit,
        resume=True,
        resume_from_stage=phase,
        previous_run_dir=state.get("previous_run_dir")
        or state.get("current_run_dir"),
        resume_reason=state.get("last_error")
        or state.get("status"),
    )
    path = ctx.run_dir / "resume_prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return path



def run_codex_text(
    prompt: str,
    repo: Path,
    config: ModelConfig,
    *,
    ctx: RunContext,
    task_id: str,
    role: str,
) -> tuple[str, StageRunRecord]:
    if shutil.which("codex") is None:
        raise OrchestratorError("`codex` executable was not found on PATH.")

    record = ctx.new_stage(task_id, role, config)
    log_path = Path(record.log_path or "")
    final_path = Path(record.final_path or "")
    prompt_path = Path(record.prompt_path or "")
    prompt_path.write_text(prompt, encoding="utf-8")
    ctx.progress("START", f"{task_id} {role.upper()} — {config.model} / {config.reasoning_effort}")

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="codex-last-", suffix=".txt", delete=False
    ) as handle:
        last_message = Path(handle.name)

    started = time.monotonic()
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

        with log_path.open("w", encoding="utf-8") as log_file:
            proc = subprocess.Popen(
                cmd,
                cwd=repo,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            q: queue.Queue[str | None] = queue.Queue()
            reader = threading.Thread(target=_reader_thread, args=(proc.stdout, q), daemon=True)
            reader.start()
            last_heartbeat = time.monotonic()
            stream_done = False

            while not stream_done:
                timeout = 1.0
                try:
                    item = q.get(timeout=timeout)
                except queue.Empty:
                    item = ""
                if item is None:
                    stream_done = True
                elif item:
                    log_file.write(item)
                    log_file.flush()
                    if ctx.verbose:
                        print(item, end="", flush=True)

                now = time.monotonic()
                if (
                    ctx.heartbeat_seconds > 0
                    and proc.poll() is None
                    and now - last_heartbeat >= ctx.heartbeat_seconds
                ):
                    elapsed = int(now - started)
                    ctx.progress("WAIT", f"{task_id} {role.upper()} still running ({elapsed}s)")
                    last_heartbeat = now

            return_code = proc.wait()
            reader.join(timeout=1)

        final_message = last_message.read_text(encoding="utf-8") if last_message.exists() else ""
        final_path.write_text(final_message, encoding="utf-8")

        ended = time.monotonic()
        record.ended_at = iso_now()
        record.duration_seconds = round(ended - started, 3)
        record.exit_code = return_code
        record.tokens_reported = extract_tokens(log_path)
        record.signals = extract_signal_lines(final_message)

        if return_code != 0:
            record.error_type = "CHILD_PROCESS"
            record.error_message = f"Codex child exited with code {return_code}"
            ctx.add_error(
                kind="CHILD_PROCESS",
                stage=role,
                task_id=task_id,
                message=record.error_message,
                signals=record.signals,
                log_path=str(log_path),
                final_path=str(final_path),
            )
            ctx.progress("FAIL", f"{task_id} {role.upper()} child exit={return_code}")
            raise ChildProcessError(
                record.error_message,
                task_id=task_id,
                role=role,
                log_path=log_path,
                final_path=final_path,
            )

        return final_message, record
    finally:
        last_message.unlink(missing_ok=True)


def run_stage(prompt: str, repo: Path, config: ModelConfig, *, ctx: RunContext, task_id: str, role: str) -> StageResult:
    text, record = run_codex_text(prompt, repo, config, ctx=ctx, task_id=task_id, role=role)
    try:
        result = parse_workflow_result(
            text,
            task_id=task_id,
            role=role,
            log_path=Path(record.log_path or ""),
            final_path=Path(record.final_path or ""),
        )
    except ChildProtocolError as exc:
        record.error_type = "CHILD_PROTOCOL"
        record.error_message = str(exc)
        record.signals = extract_signal_lines(exc.final_message)
        ctx.add_error(
            kind="CHILD_PROTOCOL",
            stage=role,
            task_id=task_id,
            message=str(exc),
            signals=record.signals,
            log_path=str(exc.log_path),
            final_path=str(exc.final_path),
        )
        ctx.progress("ERROR", f"{task_id} {role.upper()} protocol — {exc}")
        raise

    record.result_status = result.status
    record.workflow_complete = bool(result.payload.get("workflow_complete"))
    kind = "PASS"
    if result.status in {"REJECT", "INCOMPLETE", "NOT_READY_FOR_RE_REVIEW"}:
        kind = "REJECT" if result.status == "REJECT" else "STOP"
    ctx.progress(kind, f"{task_id} {role.upper()} — {result.status}")
    return result


def run_acceptance(prompt: str, repo: Path, config: ModelConfig, *, ctx: RunContext, task_id: str) -> AcceptanceResult:
    text, record = run_codex_text(prompt, repo, config, ctx=ctx, task_id=task_id, role="acceptance")
    try:
        result = parse_acceptance_result(
            text,
            task_id=task_id,
            role="acceptance",
            log_path=Path(record.log_path or ""),
            final_path=Path(record.final_path or ""),
        )
    except ChildProtocolError as exc:
        record.error_type = "CHILD_PROTOCOL"
        record.error_message = str(exc)
        record.signals = extract_signal_lines(exc.final_message)
        ctx.add_error(
            kind="CHILD_PROTOCOL",
            stage="acceptance",
            task_id=task_id,
            message=str(exc),
            signals=record.signals,
            log_path=str(exc.log_path),
            final_path=str(exc.final_path),
        )
        ctx.progress("ERROR", f"{task_id} ACCEPTANCE protocol — {exc}")
        raise
    record.result_status = result.status
    record.workflow_complete = bool(result.payload.get("workflow_complete"))
    ctx.progress("PASS" if result.status == "RECORDED" else "FAIL", f"{task_id} ACCEPTANCE — {result.status}")
    return result


def require_result(result: StageResult, *, task_id: str, stage: str, allowed: set[str]) -> None:
    if result.task_id != task_id:
        raise OrchestratorError(f"TASK identity mismatch: expected {task_id}, got {result.task_id}")
    if result.stage != stage:
        raise OrchestratorError(f"Stage mismatch: expected {stage}, got {result.stage}")
    if result.status not in allowed:
        raise OrchestratorError(
            f"Unexpected {stage} status: {result.status}; allowed={sorted(allowed)}"
        )


def workflow_is_complete(result: StageResult) -> bool:
    return bool(result.payload["workflow_complete"])


def task_scope(task_id: str) -> str:
    match = TASK_RE.fullmatch(task_id)
    if match:
        prefix = match.group("prefix")
        return prefix[len("TASK-"):-1].lower()
    return "task"


def task_short(task_id: str) -> str:
    if not task_id.startswith("TASK-"):
        raise OrchestratorError(f"Invalid TASK_ID: {task_id}")
    return task_id[len("TASK-"):]


def expected_acceptance_filename(task_id: str) -> str:
    return f"{task_short(task_id)}_acceptance.json"


def commit_subject(task_id: str, boundary: str, review_status: str | None = None) -> str:
    scope = task_scope(task_id)
    if boundary == "implementation-review":
        if review_status not in {"ACCEPT", "REJECT"}:
            raise OrchestratorError("Review status required for implementation-review commit")
        return f"feat({scope}): {task_id} implementation reviewed [{review_status}]"
    if boundary == "fix-rereview":
        if review_status == "ACCEPT":
            return f"fix({scope}): {task_id} review findings resolved [ACCEPT]"
        if review_status == "REJECT":
            return f"fix({scope}): {task_id} review findings reviewed [REJECT]"
        raise OrchestratorError("Review status required for fix-rereview commit")
    if boundary == "acceptance":
        return f"chore({scope}): record {task_id} acceptance [ACCEPT]"
    raise OrchestratorError(f"Unknown commit boundary: {boundary}")


def commit_all_changes(
    repo: Path,
    *,
    task_id: str,
    boundary: str,
    review_status: str | None = None,
    ctx: RunContext | None = None,
) -> str:
    if ctx:
        ctx.progress("COMMIT", f"{task_id} {boundary}")
    run_git(repo, "add", "-A")
    run_git(repo, "diff", "--cached", "--check")
    staged = run_git(repo, "diff", "--cached", "--quiet", check=False)
    allow_empty = staged.returncode == 0
    subject = commit_subject(task_id, boundary, review_status=review_status)
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
    cmd.extend(["-m", subject, "-m", "\n".join(body_lines)])
    run_git(repo, *cmd)
    commit_hash = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    ensure_clean_worktree(repo)
    if ctx:
        ctx.progress("PASS", f"commit {commit_hash[:10]} — {subject}")
    return commit_hash


def validate_acceptance_write(repo: Path, result: AcceptanceResult, *, task_id: str, accepted_commit: str) -> Path:
    if result.task_id != task_id:
        raise OrchestratorError(f"Acceptance TASK mismatch: expected {task_id}, got {result.task_id}")
    if result.status != "RECORDED":
        raise OrchestratorError(f"Acceptance recording did not succeed: {result.status}")
    if not result.payload.get("workflow_complete"):
        raise OrchestratorError("Acceptance workflow incomplete.")
    if result.accepted_commit != accepted_commit:
        raise OrchestratorError(
            f"Acceptance commit mismatch: expected {accepted_commit}, got {result.accepted_commit}"
        )
    if not result.acceptance_path:
        raise OrchestratorError("Acceptance result did not provide acceptance_path.")
    rel_path = Path(result.acceptance_path)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise OrchestratorError(f"Unsafe acceptance_path: {rel_path}")
    if rel_path.name != expected_acceptance_filename(task_id):
        raise OrchestratorError(
            f"Acceptance filename mismatch: expected {expected_acceptance_filename(task_id)}, got {rel_path.name}"
        )
    abs_path = repo / rel_path
    if not abs_path.is_file():
        raise OrchestratorError(f"Acceptance file not found: {rel_path}")
    paths = changed_paths(repo)
    if paths != [rel_path.as_posix()]:
        raise OrchestratorError(
            "Acceptance worker changed unexpected files. "
            f"Expected only {rel_path.as_posix()}, got {paths}"
        )
    try:
        artifact = json.loads(abs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Acceptance artifact is invalid JSON: {rel_path}") from exc
    if artifact.get("task_id") != task_id:
        raise OrchestratorError("Acceptance artifact task_id mismatch.")
    if artifact.get("status") != "ACCEPT":
        raise OrchestratorError("Acceptance artifact status must be ACCEPT.")
    if artifact.get("accepted_commit") != accepted_commit:
        raise OrchestratorError("Acceptance artifact accepted_commit mismatch.")
    return rel_path


def run_acceptance_record(
    repo: Path,
    *,
    task_id: str,
    accepted_commit: str,
    config: ModelConfig,
    ctx: RunContext,
    resume: bool = False,
    previous_run_dir: str | None = None,
    resume_reason: str | None = None,
) -> str:
    if resume:
        dirty = changed_paths(repo)
        if dirty:
            expected_name = expected_acceptance_filename(task_id)
            if len(dirty) != 1 or Path(dirty[0]).name != expected_name:
                raise OrchestratorError(
                    "Acceptance resume may start dirty only when the sole changed "
                    f"path is {expected_name}; got {dirty}"
                )
    else:
        ensure_clean_worktree(repo)

    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if head != accepted_commit:
        raise OrchestratorError(
            "Acceptance recording requires HEAD to equal accepted_commit. "
            f"HEAD={head}, accepted_commit={accepted_commit}"
        )

    prompt = child_prompt(
        task_id=task_id,
        worker_role="acceptance",
        accepted_commit=accepted_commit,
        resume=resume,
        resume_from_stage="acceptance" if resume else None,
        previous_run_dir=previous_run_dir,
        resume_reason=resume_reason,
    )
    result = run_acceptance(
        prompt,
        repo,
        config,
        ctx=ctx,
        task_id=task_id,
    )
    rel_path = validate_acceptance_write(
        repo,
        result,
        task_id=task_id,
        accepted_commit=accepted_commit,
    )
    return rel_path.as_posix()



def stage_event(result: StageResult, config: ModelConfig, *, role: str) -> dict[str, Any]:
    event = dict(result.payload)
    event["model_role"] = role
    event["model"] = config.model
    event["reasoning_effort"] = config.reasoning_effort
    return event


def commit_event(*, task_id: str, boundary: str, commit_hash: str, review_status: str | None = None) -> dict[str, Any]:
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


def record_technical_stop(ctx: RunContext, task_id: str, role: str, message: str) -> None:
    record = next((r for r in reversed(ctx.stage_records) if r.task_id == task_id and r.role == role), None)
    ctx.add_error(
        kind="TECHNICAL",
        stage=role,
        task_id=task_id,
        message=message,
        signals=(record.signals if record else []),
        log_path=(record.log_path if record else None),
        final_path=(record.final_path if record else None),
    )


def finalize_accept(
    repo: Path,
    *,
    task_id: str,
    accepted_commit: str,
    acceptance_config: ModelConfig,
    commits: list[str],
    events: list[dict[str, Any]],
    ctx: RunContext,
) -> dict[str, Any]:
    try:
        acceptance_path, acceptance_commit = record_acceptance_and_commit(
            repo,
            task_id=task_id,
            accepted_commit=accepted_commit,
            config=acceptance_config,
            ctx=ctx,
        )
    except KeyboardInterrupt:
        if args.command in {"task", "resume"}:
            mark_checkpoint_interrupted(
                args.report_dir,
                repo,
                args.task_id,
                error_type="INTERRUPTED",
                error_message="Host orchestration interrupted by user/process.",
            )
        ctx.add_error(
            kind="INTERRUPTED",
            stage="orchestrator",
            task_id=target,
            message="Host orchestration interrupted by user/process.",
        )
        result = {
            "status": "ERROR",
            "error_type": "INTERRUPTED",
            "error": "Host orchestration interrupted by user/process.",
            "target": target,
        }
    except OrchestratorError as exc:
        ctx.add_error(
            kind="ACCEPTANCE",
            stage="acceptance",
            task_id=task_id,
            message=str(exc),
        )
        ctx.progress("FAIL", f"{task_id} ACCEPTANCE — {exc}")
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
    *,
    ctx: RunContext,
    max_fix_cycles: int = 1,
    resume_state: dict[str, Any] | None = None,
    resume_force: bool = False,
) -> dict[str, Any]:
    """Run or resume one TASK lifecycle.

    The checkpoint is written outside the repository before every lifecycle stage.
    If a child is interrupted by token/context/runtime limits, `resume` re-enters
    exactly that phase with a fresh bounded Codex context and preserves the
    existing target-task worktree.
    """
    events: list[dict[str, Any]] = []

    if resume_state is None:
        ensure_clean_worktree(repo)
        initial_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        state: dict[str, Any] = {
            "schema_version": 1,
            "task_id": task_id,
            "repo": str(repo),
            "branch": current_branch(repo),
            "initial_head": initial_head,
            "current_head": initial_head,
            "phase": "implementation",
            "status": "RUNNING",
            "review_status": None,
            "accepted_commit": None,
            "acceptance_path": None,
            "acceptance_commit": None,
            "fix_cycles_used": 0,
            "max_fix_cycles": max_fix_cycles,
            "commits": [],
            "previous_run_dir": None,
            "current_run_dir": str(ctx.run_dir),
            "updated_at": iso_now(),
        }
        save_resume_checkpoint(ctx, task_id, state)
        resuming = False
        resume_source_dir: str | None = None
        resume_reason: str | None = None
    else:
        state = dict(resume_state)
        validate_resume_state(
            repo,
            task_id,
            state,
            force=resume_force,
        )
        resume_source_dir = state.get("current_run_dir") or state.get("previous_run_dir")
        resume_reason = state.get("last_error") or state.get("status")
        state["previous_run_dir"] = resume_source_dir
        state["current_run_dir"] = str(ctx.run_dir)
        state["max_fix_cycles"] = max_fix_cycles
        state["status"] = "RESUMING"
        save_resume_checkpoint(ctx, task_id, state)
        resuming = True
        ctx.progress("RESUME", f"{task_id} from phase={state['phase']}")

    commits: list[str] = list(state.get("commits") or [])
    phase = str(state["phase"])
    resume_phase = phase if resuming else None

    def is_resumed_stage(name: str) -> bool:
        return bool(resuming and resume_phase == name)

    while True:
        transition_checkpoint(
            ctx,
            state,
            phase=phase,
            status="RUNNING" if not is_resumed_stage(phase) else "RESUMING",
            commits=commits,
        )

        if phase == "implementation":
            implementation = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="implementation",
                    resume=is_resumed_stage("implementation"),
                    resume_from_stage="implementation" if is_resumed_stage("implementation") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("implementation") else None,
                    resume_reason=resume_reason if is_resumed_stage("implementation") else None,
                ),
                repo,
                policy["implementation"],
                ctx=ctx,
                task_id=task_id,
                role="implementation",
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
                record_technical_stop(
                    ctx,
                    task_id,
                    "implementation",
                    "Implementation workflow bookkeeping incomplete.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="implementation",
                    status="BLOCKED",
                    last_error="Implementation workflow bookkeeping incomplete.",
                )
                return {
                    "task_id": task_id,
                    "status": "IMPLEMENTATION_WORKFLOW_INCOMPLETE",
                    "commits": commits,
                    "events": events,
                }
            if implementation.status != "COMPLETE":
                record_technical_stop(
                    ctx,
                    task_id,
                    "implementation",
                    "Implementation technical result is INCOMPLETE/BLOCKED.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="implementation",
                    status="BLOCKED",
                    last_error="Implementation technical result is INCOMPLETE/BLOCKED.",
                )
                return {
                    "task_id": task_id,
                    "status": "INCOMPLETE",
                    "commits": commits,
                    "events": events,
                }
            phase = "review"
            resuming = False
            continue

        if phase == "review":
            review = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="review",
                    resume=is_resumed_stage("review"),
                    resume_from_stage="review" if is_resumed_stage("review") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("review") else None,
                    resume_reason=resume_reason if is_resumed_stage("review") else None,
                ),
                repo,
                policy["review"],
                ctx=ctx,
                task_id=task_id,
                role="review",
            )
            require_result(
                review,
                task_id=task_id,
                stage="review",
                allowed={"ACCEPT", "REJECT"},
            )
            events.append(stage_event(review, policy["review"], role="review"))
            if not workflow_is_complete(review):
                record_technical_stop(
                    ctx,
                    task_id,
                    "review",
                    "Review workflow bookkeeping incomplete.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="review",
                    status="BLOCKED",
                    last_error="Review workflow bookkeeping incomplete.",
                )
                return {
                    "task_id": task_id,
                    "status": "REVIEW_WORKFLOW_INCOMPLETE",
                    "commits": commits,
                    "events": events,
                }
            state["review_status"] = review.status
            phase = "commit_implementation_review"
            resuming = False
            continue

        if phase == "commit_implementation_review":
            review_status = state.get("review_status")
            if review_status not in {"ACCEPT", "REJECT"}:
                raise OrchestratorError(
                    "Cannot resume implementation-review commit without review_status."
                )
            first_commit = commit_all_changes(
                repo,
                task_id=task_id,
                boundary="implementation-review",
                review_status=str(review_status),
                ctx=ctx,
            )
            if first_commit not in commits:
                commits.append(first_commit)
            events.append(
                commit_event(
                    task_id=task_id,
                    boundary="implementation-review",
                    review_status=str(review_status),
                    commit_hash=first_commit,
                )
            )
            if review_status == "ACCEPT":
                state["accepted_commit"] = first_commit
                phase = "acceptance"
            else:
                if max_fix_cycles == 0:
                    transition_checkpoint(
                        ctx,
                        state,
                        phase="fix",
                        status="REJECTED_NO_FIX",
                        commits=commits,
                    )
                    return {
                        "task_id": task_id,
                        "status": "REJECTED_NO_FIX",
                        "commits": commits,
                        "events": events,
                    }
                phase = "fix"

            transition_checkpoint(
                ctx,
                state,
                phase=phase,
                status="RUNNING",
                commits=commits,
                accepted_commit=state.get("accepted_commit"),
            )
            continue

        if phase == "fix":
            used = int(state.get("fix_cycles_used") or 0)
            if used >= max_fix_cycles:
                transition_checkpoint(
                    ctx,
                    state,
                    phase="fix",
                    status="REJECTED_AFTER_REVIEW",
                    commits=commits,
                )
                return {
                    "task_id": task_id,
                    "status": "REJECTED_AFTER_REVIEW",
                    "commits": commits,
                    "events": events,
                }

            fix = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="fix",
                    resume=is_resumed_stage("fix"),
                    resume_from_stage="fix" if is_resumed_stage("fix") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("fix") else None,
                    resume_reason=resume_reason if is_resumed_stage("fix") else None,
                ),
                repo,
                policy["fix"],
                ctx=ctx,
                task_id=task_id,
                role="fix",
            )
            require_result(
                fix,
                task_id=task_id,
                stage="fix",
                allowed={"READY_FOR_RE_REVIEW", "NOT_READY_FOR_RE_REVIEW"},
            )
            events.append(stage_event(fix, policy["fix"], role="fix"))
            if not workflow_is_complete(fix):
                record_technical_stop(
                    ctx,
                    task_id,
                    "fix",
                    "Fix workflow bookkeeping incomplete.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="fix",
                    status="BLOCKED",
                    last_error="Fix workflow bookkeeping incomplete.",
                )
                return {
                    "task_id": task_id,
                    "status": "FIX_WORKFLOW_INCOMPLETE",
                    "commits": commits,
                    "events": events,
                }
            if fix.status != "READY_FOR_RE_REVIEW":
                record_technical_stop(
                    ctx,
                    task_id,
                    "fix",
                    "Fix is NOT_READY_FOR_RE_REVIEW.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="fix",
                    status="BLOCKED",
                    last_error="Fix is NOT_READY_FOR_RE_REVIEW.",
                )
                return {
                    "task_id": task_id,
                    "status": "FIX_NOT_READY",
                    "commits": commits,
                    "events": events,
                }

            state["fix_cycles_used"] = used + 1
            phase = "rereview"
            resuming = False
            continue

        if phase == "rereview":
            rereview = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="rereview",
                    resume=is_resumed_stage("rereview"),
                    resume_from_stage="rereview" if is_resumed_stage("rereview") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("rereview") else None,
                    resume_reason=resume_reason if is_resumed_stage("rereview") else None,
                ),
                repo,
                policy["rereview"],
                ctx=ctx,
                task_id=task_id,
                role="rereview",
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
                record_technical_stop(
                    ctx,
                    task_id,
                    "rereview",
                    "Re-review workflow bookkeeping incomplete.",
                )
                transition_checkpoint(
                    ctx,
                    state,
                    phase="rereview",
                    status="BLOCKED",
                    last_error="Re-review workflow bookkeeping incomplete.",
                )
                return {
                    "task_id": task_id,
                    "status": "REVIEW_WORKFLOW_INCOMPLETE",
                    "commits": commits,
                    "events": events,
                }
            state["review_status"] = rereview.status
            phase = "commit_fix_rereview"
            resuming = False
            continue

        if phase == "commit_fix_rereview":
            review_status = state.get("review_status")
            if review_status not in {"ACCEPT", "REJECT"}:
                raise OrchestratorError(
                    "Cannot resume fix-rereview commit without review_status."
                )
            fix_commit = commit_all_changes(
                repo,
                task_id=task_id,
                boundary="fix-rereview",
                review_status=str(review_status),
                ctx=ctx,
            )
            if fix_commit not in commits:
                commits.append(fix_commit)
            events.append(
                commit_event(
                    task_id=task_id,
                    boundary="fix-rereview",
                    review_status=str(review_status),
                    commit_hash=fix_commit,
                )
            )
            if review_status == "ACCEPT":
                state["accepted_commit"] = fix_commit
                phase = "acceptance"
            else:
                if int(state.get("fix_cycles_used") or 0) < max_fix_cycles:
                    phase = "fix"
                else:
                    transition_checkpoint(
                        ctx,
                        state,
                        phase="fix",
                        status="REJECTED_AFTER_REVIEW",
                        commits=commits,
                    )
                    return {
                        "task_id": task_id,
                        "status": "REJECTED_AFTER_REVIEW",
                        "commits": commits,
                        "events": events,
                    }

            transition_checkpoint(
                ctx,
                state,
                phase=phase,
                status="RUNNING",
                commits=commits,
                accepted_commit=state.get("accepted_commit"),
            )
            continue

        if phase == "acceptance":
            accepted_commit = state.get("accepted_commit")
            if not accepted_commit:
                accepted_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
                state["accepted_commit"] = accepted_commit
            acceptance_path = run_acceptance_record(
                repo,
                task_id=task_id,
                accepted_commit=str(accepted_commit),
                config=policy["acceptance"],
                ctx=ctx,
                resume=is_resumed_stage("acceptance"),
                previous_run_dir=resume_source_dir if is_resumed_stage("acceptance") else None,
                resume_reason=resume_reason if is_resumed_stage("acceptance") else None,
            )
            state["acceptance_path"] = acceptance_path
            phase = "commit_acceptance"
            resuming = False
            transition_checkpoint(
                ctx,
                state,
                phase=phase,
                status="RUNNING",
                acceptance_path=acceptance_path,
                accepted_commit=state.get("accepted_commit"),
                commits=commits,
            )
            continue

        if phase == "commit_acceptance":
            acceptance_path = state.get("acceptance_path")
            if not acceptance_path:
                raise OrchestratorError(
                    "Cannot commit acceptance without acceptance_path."
                )
            acceptance_commit = commit_all_changes(
                repo,
                task_id=task_id,
                boundary="acceptance",
                ctx=ctx,
            )
            if acceptance_commit not in commits:
                commits.append(acceptance_commit)
            state["acceptance_commit"] = acceptance_commit
            events.append(
                acceptance_event(
                    task_id=task_id,
                    accepted_commit=str(state["accepted_commit"]),
                    acceptance_path=str(acceptance_path),
                    acceptance_commit=acceptance_commit,
                    config=policy["acceptance"],
                )
            )
            transition_checkpoint(
                ctx,
                state,
                phase="accepted",
                status="ACCEPTED",
                commits=commits,
                acceptance_commit=acceptance_commit,
            )
            return {
                "task_id": task_id,
                "status": "ACCEPTED",
                "accepted_commit": state["accepted_commit"],
                "acceptance_path": acceptance_path,
                "acceptance_commit": acceptance_commit,
                "commits": commits,
                "events": events,
            }

        raise OrchestratorError(f"Unsupported lifecycle phase: {phase}")



def expand_range(start: str, end: str) -> list[str]:
    sm = TASK_RE.fullmatch(start)
    em = TASK_RE.fullmatch(end)
    if not sm or not em:
        raise OrchestratorError("TASK range requires IDs like TASK-SIM-002 TASK-SIM-004.")
    if sm.group("prefix") != em.group("prefix"):
        raise OrchestratorError("TASK range prefixes must match.")
    start_num = int(sm.group("num"))
    end_num = int(em.group("num"))
    if end_num < start_num:
        raise OrchestratorError("TASK range must be ascending.")
    width = max(len(sm.group("num")), len(em.group("num")))
    prefix = sm.group("prefix")
    return [f"{prefix}{number:0{width}d}" for number in range(start_num, end_num + 1)]


def run_range(
    start: str,
    end: str,
    repo: Path,
    policy: dict[str, ModelConfig],
    *,
    ctx: RunContext,
    max_fix_cycles: int = 1,
) -> dict[str, Any]:
    tasks = expand_range(start, end)
    results: list[dict[str, Any]] = []
    all_commits: list[str] = []
    for index, task_id in enumerate(tasks):
        ensure_clean_worktree(repo)
        ctx.progress("RUN", task_id)
        result = run_task(task_id, repo, policy, ctx=ctx, max_fix_cycles=max_fix_cycles)
        results.append(result)
        all_commits.extend(result.get("commits", []))
        if result["status"] != "ACCEPTED":
            next_task = tasks[index + 1] if index + 1 < len(tasks) else None
            return {
                "range": f"{start}..{end}",
                "status": "STOPPED",
                "accepted": [item["task_id"] for item in results if item["status"] == "ACCEPTED"],
                "commits": all_commits,
                "stopping_task": task_id,
                "stopping_status": result["status"],
                "worktree_clean": not bool(worktree_status(repo)),
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


def derive_next_action(result: dict[str, Any], errors: list[ErrorRecord]) -> tuple[str, list[str]]:
    status = str(result.get("status", "ERROR"))
    if status in {"ACCEPTED", "COMPLETE"}:
        return "NONE", ["No TASK lifecycle action is required."]
    if status in {"INCOMPLETE", "IMPLEMENTATION_WORKFLOW_INCOMPLETE"}:
        return "RESOLVE_IMPLEMENTATION_BLOCKER_THEN_RESUME", [
            "Inspect the failing Implementation final response and full log listed below.",
            "Resolve the implementation/environment blocker without discarding target-task work.",
            "Then resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "REVIEW_WORKFLOW_INCOMPLETE":
        return "REPAIR_REVIEW_WORKFLOW_THEN_RESUME", [
            "Inspect the Review/Re-review final response and protocol/error log.",
            "Do not claim acceptance until an independent Review completes and is committed.",
            "Then resume the checkpointed stage with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status in {"FIX_NOT_READY", "FIX_WORKFLOW_INCOMPLETE"}:
        return "RESOLVE_FIX_BLOCKER_THEN_RESUME", [
            "Inspect the Fix final response/log and remaining Findings.",
            "Resolve the blocker without discarding target-task work.",
            "Then resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status in {"REJECTED_AFTER_REVIEW", "REJECTED_NO_FIX"}:
        return "MANUAL_REVIEW_REQUIRED", [
            "Inspect the latest independent Review findings.",
            "Decide whether another Fix cycle is authorized before continuing.",
        ]
    if status == "ACCEPTANCE_RECORD_FAILED":
        return "REPAIR_ACCEPTANCE_RECORDING_THEN_RESUME", [
            "Inspect the Acceptance worker final response/log.",
            "Do not start a downstream TASK until acceptance JSON and acceptance commit are valid.",
            "Then resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "STOPPED":
        stopping = result.get("stopping_status")
        return f"RESOLVE_{stopping or 'STOPPED_TASK'}", [
            f"Resolve the stopping TASK status: {stopping}.",
            "Downstream TASKs were intentionally not started.",
        ]

    kinds = {e.kind for e in errors}
    if "CHILD_PROTOCOL" in kinds:
        return "REPAIR_WORKER_RESULT_PROTOCOL", [
            "Inspect the child final response; the required machine-result marker is missing/invalid.",
            "Keep the technical failure signals separate from the protocol failure.",
        ]
    if "CHILD_PROCESS" in kinds:
        return "INSPECT_CHILD_PROCESS_FAILURE_THEN_RESUME", [
            "Inspect the child full log and final response.",
            "If the child stopped because of token/context/runtime limits, preserve the current worktree.",
            "Resume the checkpointed stage with: scripts/codex/resume-task <TASK_ID>",
        ]
    if "GIT" in kinds or "AUTO_COMMIT" in " ".join(e.message for e in errors):
        return "RECONCILE_GIT_STATE", [
            "Inspect Git status/diff and restore a valid clean workflow boundary.",
        ]
    return "INSPECT_RUN_REPORT", ["Inspect summary.md and the failing stage log before continuing."]


def result_terminal_task(result: dict[str, Any]) -> str | None:
    if "task_id" in result:
        return str(result["task_id"])
    if result.get("stopping_task"):
        return str(result["stopping_task"])
    return None


def write_reports(
    ctx: RunContext,
    *,
    result: dict[str, Any],
    branch: str | None,
    repo_status: str | None,
) -> tuple[Path, Path]:
    next_action, next_steps = derive_next_action(result, ctx.errors)
    ended_at = iso_now()
    duration = round(time.monotonic() - ctx.started_monotonic, 3)
    report = {
        "schema_version": 1,
        "target": ctx.target,
        "repo": str(ctx.repo),
        "branch": branch,
        "started_at": ctx.started_at,
        "ended_at": ended_at,
        "duration_seconds": duration,
        "result": result,
        "next_action": next_action,
        "next_steps": next_steps,
        "worktree_clean": None if repo_status is None else (repo_status == ""),
        "worktree_status": repo_status,
        "stages": [asdict(r) for r in ctx.stage_records],
        "errors": [asdict(e) for e in ctx.errors],
        "resume_checkpoint": None,
        "resume_command": None,
        "manual_resume_prompt": None,
    }

    terminal_task_for_resume = result_terminal_task(result)
    if terminal_task_for_resume:
        checkpoint = ctx.run_dir.parent / f"resume_{safe_name(terminal_task_for_resume)}.json"
        if checkpoint.is_file():
            report["resume_checkpoint"] = str(checkpoint)
            report["resume_command"] = f"scripts/codex/resume-task {terminal_task_for_resume}"
            try:
                resume_state = json.loads(checkpoint.read_text(encoding="utf-8"))
                if resume_state.get("status") != "ACCEPTED":
                    manual_prompt_path = write_manual_resume_prompt(ctx, resume_state)
                    if manual_prompt_path:
                        report["manual_resume_prompt"] = str(manual_prompt_path)
            except Exception:
                pass

    json_path = ctx.run_dir / "run_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines += [
        f"# TASK Run Summary — {ctx.target}",
        "",
        "## Result",
        "",
        f"- Status: `{result.get('status', 'ERROR')}`",
        f"- Branch: `{branch or 'UNKNOWN'}`",
        f"- Worktree clean: `{report['worktree_clean']}`",
        f"- Duration: `{duration:.1f}s`",
    ]
    terminal_task = result_terminal_task(result)
    if terminal_task:
        lines.append(f"- Terminal TASK: `{terminal_task}`")
    if result.get("accepted_commit"):
        lines.append(f"- Accepted commit: `{result['accepted_commit']}`")
    if result.get("acceptance_commit"):
        lines.append(f"- Acceptance commit: `{result['acceptance_commit']}`")
    if result.get("acceptance_path"):
        lines.append(f"- Acceptance artifact: `{result['acceptance_path']}`")

    lines += ["", "## Stage Results", "", "| Stage | Model | Result | Duration | Tokens |", "|---|---|---|---:|---:|"]
    if ctx.stage_records:
        for r in ctx.stage_records:
            model = f"{r.model} / {r.reasoning_effort}"
            status = r.result_status or (f"ERROR:{r.error_type}" if r.error_type else f"exit={r.exit_code}")
            dur = "" if r.duration_seconds is None else f"{r.duration_seconds:.1f}s"
            tok = "" if r.tokens_reported is None else f"{r.tokens_reported:,}"
            lines.append(f"| `{r.task_id}:{r.role}` | `{model}` | `{status}` | {dur} | {tok} |")
    else:
        lines.append("| - | - | NOT STARTED | - | - |")

    lines += ["", "## Errors", ""]
    if not ctx.errors:
        lines.append("None.")
    else:
        for e in ctx.errors:
            lines += [f"### {e.kind} — {e.task_id}:{e.stage}", "", f"- {e.message}"]
            if e.signals:
                lines.append("- Signals:")
                for s in e.signals:
                    lines.append(f"  - `{s}`")
            if e.final_path:
                lines.append(f"- Final response: `{e.final_path}`")
            if e.log_path:
                lines.append(f"- Full log: `{e.log_path}`")
            lines.append("")

    lines += ["## Repository State", "", "```text", repo_status or "CLEAN", "```", ""]
    lines += ["## Next Action", "", f"`{next_action}`", ""]
    for i, step in enumerate(next_steps, 1):
        rendered = step.replace("<TASK_ID>", terminal_task or "<TASK_ID>")
        lines.append(f"{i}. {rendered}")
    if report.get("resume_command"):
        lines += ["", f"Resume command: `{report['resume_command']}`"]
    if report.get("resume_checkpoint"):
        lines.append(f"Resume checkpoint: `{report['resume_checkpoint']}`")
    if report.get("manual_resume_prompt"):
        lines.append(f"Manual fresh-session prompt: `{report['manual_resume_prompt']}`")
    lines += ["", "## Logs", ""]
    for r in ctx.stage_records:
        lines.append(f"- `{r.task_id}:{r.role}` prompt: `{r.prompt_path}`")
        lines.append(f"- `{r.task_id}:{r.role}` log: `{r.log_path}`")
        lines.append(f"- `{r.task_id}:{r.role}` final: `{r.final_path}`")
    lines += ["", f"Machine report: `{json_path}`", ""]

    md_path = ctx.run_dir / "summary.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def print_failure_tail(ctx: RunContext) -> None:
    if ctx.show_tail <= 0 or not ctx.errors:
        return
    error = ctx.errors[-1]
    if not error.log_path:
        return
    path = Path(error.log_path)
    if not path.exists():
        return
    tail = tail_text(path, max_bytes=32768).splitlines()[-ctx.show_tail:]
    if not tail:
        return
    print("\n--- failing child log tail ---")
    for line in tail:
        print(line)
    print("--- end tail ---")


def print_final_console(ctx: RunContext, result: dict[str, Any], summary_path: Path, json_path: Path) -> None:
    status = str(result.get("status", "ERROR"))
    kind = "DONE" if status in {"ACCEPTED", "COMPLETE"} else "STOP"
    ctx.progress(kind, f"{ctx.target} — {status}")
    if ctx.errors:
        print("\nErrors:")
        for e in ctx.errors:
            print(f"  - [{e.kind}] {e.task_id}:{e.stage}: {e.message}")
            for signal in e.signals[:5]:
                print(f"      {signal}")
    next_action, steps = derive_next_action(result, ctx.errors)
    print(f"\nNext action: {next_action}")
    terminal_task = result_terminal_task(result)
    for i, step in enumerate(steps, 1):
        rendered = step.replace("<TASK_ID>", terminal_task or "<TASK_ID>")
        print(f"  {i}. {rendered}")
    if terminal_task:
        checkpoint = ctx.run_dir.parent / f"resume_{safe_name(terminal_task)}.json"
        if checkpoint.is_file() and status not in {"ACCEPTED", "COMPLETE"}:
            print(f"  Resume: scripts/codex/resume-task {terminal_task}")
            print(f"  Checkpoint: {checkpoint}")
    print(f"\nSummary: {summary_path}")
    print(f"Report:  {json_path}")
    print_failure_tail(ctx)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root; defaults to current directory.")
    parser.add_argument("--model-policy", type=Path, default=DEFAULT_MODEL_POLICY_PATH, help="Model policy JSON path relative to repo root.")
    parser.add_argument("--max-fix-cycles", type=int, default=1, choices=range(0, 4), metavar="N")
    parser.add_argument("--allow-protected-branch", action="store_true")
    parser.add_argument("--report-dir", type=Path, default=default_report_base(), help="Base directory for persistent orchestration logs/reports.")
    parser.add_argument("--verbose", action="store_true", help="Echo complete child Codex output to the terminal.")
    parser.add_argument("--show-tail", type=int, default=12, metavar="N", help="Show N lines from the failing child log at the end; 0 disables.")
    parser.add_argument("--heartbeat-seconds", type=int, default=30, metavar="N", help="Print a quiet WAIT heartbeat every N seconds; 0 disables.")

    sub = parser.add_subparsers(dest="command", required=True)
    task_parser = sub.add_parser("task")
    task_parser.add_argument("task_id")
    range_parser = sub.add_parser("range")
    range_parser.add_argument("start_task_id")
    range_parser.add_argument("end_task_id")

    resume_parser = sub.add_parser(
        "resume",
        help="Resume the last checkpointed stage for one TASK.",
    )
    resume_parser.add_argument("task_id")
    resume_parser.add_argument(
        "--from-stage",
        choices=[
            "implementation",
            "review",
            "fix",
            "rereview",
            "acceptance",
        ],
        default=None,
        help=(
            "Manual bootstrap/override stage. Use when resuming an older run "
            "that has no checkpoint, or only after verifying repository state."
        ),
    )
    resume_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow branch/HEAD mismatch after manual provenance verification.",
    )

    args = parser.parse_args()

    repo = args.repo.resolve()
    if args.command in {"task", "resume"}:
        target = args.task_id
    else:
        target = f"{args.start_task_id}..{args.end_task_id}"
    ctx = RunContext(
        repo=repo,
        target=target,
        report_base=args.report_dir,
        verbose=args.verbose,
        show_tail=args.show_tail,
        heartbeat_seconds=args.heartbeat_seconds,
    )
    result: dict[str, Any] = {"status": "ERROR", "target": target}
    branch: str | None = None

    try:
        ctx.progress("RUN", target)
        if not (repo / ".git").exists():
            raise OrchestratorError(f"Not a Git repository: {repo}")
        branch = ensure_automation_branch(
            repo,
            allow_protected_branch=args.allow_protected_branch,
        )
        policy = load_model_policy(repo, args.model_policy)

        if args.command == "task":
            ensure_clean_worktree(repo)
            ctx.progress("CHECK", f"branch={branch}, worktree=CLEAN")
            result = run_task(
                args.task_id,
                repo,
                policy,
                ctx=ctx,
                max_fix_cycles=args.max_fix_cycles,
            )
        elif args.command == "resume":
            if args.from_stage:
                checkpoint_path = resume_checkpoint_path(
                    args.report_dir, repo, args.task_id
                )
                if checkpoint_path.is_file():
                    _, resume_state = load_resume_checkpoint(
                        args.report_dir, repo, args.task_id
                    )
                    resume_state["phase"] = args.from_stage
                else:
                    resume_state = create_manual_resume_state(
                        repo,
                        args.task_id,
                        phase=args.from_stage,
                        max_fix_cycles=args.max_fix_cycles,
                    )
            else:
                _, resume_state = load_resume_checkpoint(
                    args.report_dir, repo, args.task_id
                )

            validate_resume_state(
                repo,
                args.task_id,
                resume_state,
                force=args.force,
            )
            ctx.progress(
                "CHECK",
                (
                    f"branch={branch}, resume_phase={resume_state['phase']}, "
                    f"worktree={'CLEAN' if not worktree_status(repo) else 'PRESERVED-DIRTY'}"
                ),
            )
            result = run_task(
                args.task_id,
                repo,
                policy,
                ctx=ctx,
                max_fix_cycles=args.max_fix_cycles,
                resume_state=resume_state,
                resume_force=args.force,
            )
        else:
            ensure_clean_worktree(repo)
            ctx.progress("CHECK", f"branch={branch}, worktree=CLEAN")
            result = run_range(
                args.start_task_id,
                args.end_task_id,
                repo,
                policy,
                ctx=ctx,
                max_fix_cycles=args.max_fix_cycles,
            )
        result["branch"] = branch
        result["model_policy"] = {
            role: {"model": cfg.model, "reasoning_effort": cfg.reasoning_effort}
            for role, cfg in policy.items()
        }
    except ChildProtocolError as exc:
        if args.command in {"task", "resume"}:
            mark_checkpoint_interrupted(
                args.report_dir,
                repo,
                exc.task_id,
                error_type="CHILD_PROTOCOL",
                error_message=str(exc),
            )
        result = {
            "status": "ERROR",
            "error_type": "CHILD_PROTOCOL",
            "error": str(exc),
            "task_id": exc.task_id,
            "failed_stage": exc.role,
        }
    except ChildProcessError as exc:
        if args.command in {"task", "resume"}:
            mark_checkpoint_interrupted(
                args.report_dir,
                repo,
                exc.task_id,
                error_type="CHILD_PROCESS",
                error_message=str(exc),
            )
        result = {
            "status": "ERROR",
            "error_type": "CHILD_PROCESS",
            "error": str(exc),
            "task_id": exc.task_id,
            "failed_stage": exc.role,
        }
    except OrchestratorError as exc:
        ctx.add_error(kind="ORCHESTRATOR", stage="orchestrator", task_id=target, message=str(exc))
        result = {"status": "ERROR", "error_type": "ORCHESTRATOR", "error": str(exc), "target": target}
    except Exception as exc:  # defensive fail-closed reporting
        ctx.add_error(kind="UNEXPECTED", stage="orchestrator", task_id=target, message=repr(exc))
        result = {"status": "ERROR", "error_type": "UNEXPECTED", "error": repr(exc), "target": target}

    repo_status: str | None = None
    if (repo / ".git").exists():
        try:
            repo_status = worktree_status(repo)
        except Exception:
            repo_status = None

    summary_path, json_path = write_reports(ctx, result=result, branch=branch, repo_status=repo_status)
    print_final_console(ctx, result, summary_path, json_path)

    if args.command in {"task", "resume"}:
        return 0 if result.get("status") == "ACCEPTED" else 1
    return 0 if result.get("status") == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
