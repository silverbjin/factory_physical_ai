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
import hashlib
import json
import os
import queue
import re
import shutil
import signal
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
GATE_RESULT_PREFIX = "GATE_RESULT_JSON:"
TASK_RE = re.compile(r"^(?P<prefix>TASK-[A-Z0-9]+-)(?P<num>\d+)$")
PROTECTED_BRANCHES = {"main", "master"}
DEFAULT_MODEL_POLICY_PATH = Path("config/codex_model_policy.json")
CODEX_SANDBOX_MODES = frozenset({"read-only", "workspace-write", "danger-full-access"})
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


class ChildInterruptedError(OrchestratorError):
    def __init__(
        self,
        message: str,
        *,
        task_id: str,
        role: str,
        log_path: Path,
        final_path: Path,
    ):
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


@dataclass(frozen=True)
class TaskClassConfig:
    diagnosis_required: bool
    allow_high_escalation: bool
    review_reasoning_effort: str
    rereview_reasoning_effort: str


@dataclass(frozen=True)
class ClassificationConfig:
    green_max_score: int
    yellow_max_score: int
    explicit_override_keys: tuple[str, ...]


@dataclass(frozen=True)
class ModelPolicy:
    roles: dict[str, ModelConfig]
    task_classes: dict[str, TaskClassConfig]
    classification: ClassificationConfig
    acceptance_mode: str


@dataclass(frozen=True)
class TaskOrchestratorContract:
    task_id: str
    profile: str
    gates: tuple[dict[str, Any], ...]
    protected_paths: tuple[str, ...]
    source_paths: tuple[str, ...]
    finalization_paths: tuple[str, ...]
    canonical_command: tuple[str, ...]
    canonical_evidence_paths: tuple[str, ...]
    literal_validation: tuple[tuple[str, ...], ...]


def _string_argv(value: Any, *, label: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty) or not all(isinstance(x, str) and x for x in value):
        raise OrchestratorError(f"Invalid {label}; expected a non-empty argv string list.")
    return tuple(value)


def load_task_orchestrator_contract(repo: Path, task_id: str) -> TaskOrchestratorContract | None:
    path = repo / "tasks" / "orchestrator" / f"{task_id}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid orchestrator task contract JSON: {path}") from exc
    if raw.get("schema_version") != 1 or raw.get("task_id") != task_id:
        raise OrchestratorError(f"Invalid orchestrator task contract identity/schema: {path}")
    if raw.get("profile") != "staged_integration_v1":
        raise OrchestratorError(f"Unsupported orchestrator task profile: {raw.get('profile')!r}")
    gates_raw = raw.get("gates")
    if not isinstance(gates_raw, list):
        raise OrchestratorError("Task orchestrator contract gates must be a list.")
    gates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in gates_raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise OrchestratorError("Every gate requires a non-empty id.")
        gate_id = item["id"]
        if gate_id in seen:
            raise OrchestratorError(f"Duplicate gate id: {gate_id}")
        seen.add(gate_id)
        gates.append({**item, "command": list(_string_argv(item.get("command"), label=f"gate {gate_id} command"))})
    canonical = raw.get("canonical") or {}
    if not isinstance(canonical, dict):
        raise OrchestratorError("canonical must be an object.")
    canonical_command = _string_argv(canonical.get("command"), label="canonical command")
    evidence_paths = canonical.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths or not all(isinstance(x, str) and x for x in evidence_paths):
        raise OrchestratorError("canonical.evidence_paths must be a non-empty string list.")
    literal_raw = raw.get("literal_validation") or []
    if not isinstance(literal_raw, list):
        raise OrchestratorError("literal_validation must be a list of argv arrays.")
    literal = tuple(_string_argv(cmd, label="literal validation command") for cmd in literal_raw)
    def string_list(name: str) -> tuple[str, ...]:
        value = raw.get(name) or []
        if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
            raise OrchestratorError(f"{name} must be a string list.")
        return tuple(value)
    source_paths = string_list("source_paths")
    finalization_raw = raw.get("finalization_paths")
    finalization_paths = source_paths if finalization_raw is None else string_list("finalization_paths")
    if not source_paths:
        raise OrchestratorError("source_paths must be a non-empty string list.")
    if not finalization_paths:
        raise OrchestratorError("finalization_paths must be a non-empty string list.")
    missing_source_scopes = [p for p in source_paths if not _path_within_scopes(p, finalization_paths)]
    if missing_source_scopes:
        raise OrchestratorError(
            "finalization_paths must include every source_paths scope: " + ", ".join(missing_source_scopes)
        )
    return TaskOrchestratorContract(
        task_id=task_id,
        profile="staged_integration_v1",
        gates=tuple(gates),
        protected_paths=string_list("protected_paths"),
        source_paths=source_paths,
        finalization_paths=finalization_paths,
        canonical_command=canonical_command,
        canonical_evidence_paths=tuple(evidence_paths),
        literal_validation=literal,
    )


def upgrade_checkpoint_state(state: dict[str, Any], *, staged: bool) -> dict[str, Any]:
    upgraded = dict(state)
    upgraded["schema_version"] = 3
    upgraded.setdefault("qualification_profile", "staged_integration_v1" if staged else None)
    upgraded.setdefault("review_return_phase", "review")
    upgraded.setdefault("gate_state", {
        "current_gate_index": 0,
        "attempt_id": 1,
        "passed_gates": {},
        "current_blocker": None,
        "blocker_attempt_counts": {},
        "gate_resolution_cycles": 0,
        "supplier_cache": {},
    })
    upgraded.setdefault("finalization", {
        "source_commit": None,
        "source_hashes": {},
        "canonical_results": [],
        "binding_verified": False,
    })
    upgraded.setdefault("protected_artifacts", {})
    upgraded.setdefault("literal_validation", {"results": []})
    upgraded.setdefault("aggregate_counted_runs", [])
    upgraded.setdefault("aggregate", {
        "orchestrator_runs": 0,
        "codex_calls": 0,
        "reported_tokens_total": 0,
        "diagnosis_calls": 0,
        "gate_fix_calls": 0,
        "review_fix_calls": 0,
        "review_calls": 0,
        "gate_resolution_cycles": 0,
    })
    return upgraded


def phase_after_implementation(*, staged: bool) -> str:
    return "gate_resolution" if staged else "review"


def phase_after_review_fix(*, staged: bool) -> str:
    return "gate_resolution" if staged else "rereview"


@dataclass(frozen=True)
class TaskAssessment:
    task_id: str
    task_class: str
    score: int
    reasons: tuple[str, ...]
    task_path: str
    explicit_override: bool = False


@dataclass(frozen=True)
class DiagnosisHistoryRecord:
    path: Path
    sequence: int
    status: str


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


def runtime_sandbox_override() -> str | None:
    """Return the explicit child sandbox override, preserving Codex defaults otherwise."""
    value = os.environ.get("CODEX_RUNTIME_SANDBOX")
    if value in (None, ""):
        return None
    if value not in CODEX_SANDBOX_MODES:
        allowed = ", ".join(sorted(CODEX_SANDBOX_MODES))
        raise OrchestratorError(
            f"Invalid CODEX_RUNTIME_SANDBOX={value!r}; expected one of: {allowed}."
        )
    return value


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
    return run_git(repo, "status", "--porcelain", "--untracked-files=all").stdout.rstrip("\n")


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


def _load_model_config(item: Any, *, label: str) -> ModelConfig:
    if not isinstance(item, dict):
        raise OrchestratorError(f"Missing/invalid model policy entry: {label}")
    model = item.get("model")
    effort = item.get("reasoning_effort")
    if not isinstance(model, str) or not model:
        raise OrchestratorError(f"Invalid model for policy entry: {label}")
    if not isinstance(effort, str) or not effort:
        raise OrchestratorError(f"Invalid reasoning effort for policy entry: {label}")
    return ModelConfig(model=model, reasoning_effort=effort)


def load_model_policy(repo: Path, policy_path: Path) -> ModelPolicy:
    resolved = policy_path if policy_path.is_absolute() else repo / policy_path
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OrchestratorError(f"Model policy not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid model policy JSON: {resolved}") from exc

    if raw.get("schema_version") != 2:
        raise OrchestratorError(
            "codex_model_policy.json schema_version=2 is required for TASK-class routing. "
            f"Got: {raw.get('schema_version')!r}"
        )

    roles_raw = raw.get("roles")
    if not isinstance(roles_raw, dict):
        raise OrchestratorError("Model policy must contain a roles object.")
    required_roles = {
        "implementation",
        "review",
        "fix",
        "rereview",
        "diagnosis",
        "diagnosis_escalated",
    }
    roles = {
        role: _load_model_config(roles_raw.get(role), label=f"roles.{role}")
        for role in required_roles
    }

    task_classes_raw = raw.get("task_classes")
    if not isinstance(task_classes_raw, dict):
        raise OrchestratorError("Model policy must contain task_classes.")
    task_classes: dict[str, TaskClassConfig] = {}
    for task_class in ("GREEN", "YELLOW", "RED"):
        item = task_classes_raw.get(task_class)
        if not isinstance(item, dict):
            raise OrchestratorError(f"Missing task class policy: {task_class}")
        diagnosis_required = item.get("diagnosis_required")
        allow_high = item.get("allow_high_escalation")
        review_effort = item.get("review_reasoning_effort")
        rereview_effort = item.get("rereview_reasoning_effort")
        if not isinstance(diagnosis_required, bool) or not isinstance(allow_high, bool):
            raise OrchestratorError(f"Invalid diagnosis flags for task class: {task_class}")
        if not isinstance(review_effort, str) or not isinstance(rereview_effort, str):
            raise OrchestratorError(f"Invalid review effort override for task class: {task_class}")
        task_classes[task_class] = TaskClassConfig(
            diagnosis_required=diagnosis_required,
            allow_high_escalation=allow_high,
            review_reasoning_effort=review_effort,
            rereview_reasoning_effort=rereview_effort,
        )

    classification_raw = raw.get("classification")
    if not isinstance(classification_raw, dict):
        raise OrchestratorError("Model policy must contain classification.")
    green_max = classification_raw.get("green_max_score")
    yellow_max = classification_raw.get("yellow_max_score")
    keys = classification_raw.get("explicit_override_keys")
    if not isinstance(green_max, int) or not isinstance(yellow_max, int) or green_max < 0 or yellow_max < green_max:
        raise OrchestratorError("Invalid classification score thresholds.")
    if not isinstance(keys, list) or not keys or not all(isinstance(x, str) and x for x in keys):
        raise OrchestratorError("classification.explicit_override_keys must be a non-empty string list.")

    acceptance_raw = raw.get("acceptance")
    if not isinstance(acceptance_raw, dict) or acceptance_raw.get("mode") != "deterministic":
        raise OrchestratorError("Only acceptance.mode=deterministic is supported by policy schema v2.")

    return ModelPolicy(
        roles=roles,
        task_classes=task_classes,
        classification=ClassificationConfig(
            green_max_score=green_max,
            yellow_max_score=yellow_max,
            explicit_override_keys=tuple(keys),
        ),
        acceptance_mode="deterministic",
    )


def policy_summary(policy: ModelPolicy) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "roles": {
            role: {"model": cfg.model, "reasoning_effort": cfg.reasoning_effort}
            for role, cfg in sorted(policy.roles.items())
        },
        "task_classes": {
            name: asdict(cfg) for name, cfg in sorted(policy.task_classes.items())
        },
        "classification": asdict(policy.classification),
        "acceptance": {"mode": policy.acceptance_mode},
    }


def resolve_model_config(policy: ModelPolicy, task_class: str, role: str) -> ModelConfig:
    if role not in policy.roles:
        raise OrchestratorError(f"Unknown model role: {role}")
    if task_class not in policy.task_classes:
        raise OrchestratorError(f"Unknown TASK class: {task_class}")
    base = policy.roles[role]
    class_cfg = policy.task_classes[task_class]
    if role == "review":
        return ModelConfig(base.model, class_cfg.review_reasoning_effort)
    if role == "rereview":
        return ModelConfig(base.model, class_cfg.rereview_reasoning_effort)
    return base


def locate_task_spec(repo: Path, task_id: str) -> Path:
    candidates = [
        repo / "tasks" / f"{task_id}.md",
        repo / "Tasks" / f"{task_id}.md",
        repo / f"{task_id}.md",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    ignored = {".git", ".venv", "venv", "build", "install", "log", "node_modules"}
    matches = [
        path
        for path in repo.rglob(f"{task_id}.md")
        if not any(part in ignored for part in path.relative_to(repo).parts)
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise OrchestratorError(
            f"TASK_CLASSIFICATION_FAILED: specification for {task_id} was not found. "
            "Expected tasks/<TASK_ID>.md or one unique matching Markdown file."
        )
    rendered = ", ".join(str(path.relative_to(repo)) for path in matches[:10])
    raise OrchestratorError(
        f"TASK_CLASSIFICATION_FAILED: multiple specifications found for {task_id}: {rendered}"
    )


_HARD_RED_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "authoritative_or_root_cause_unproven",
        re.compile(
            r"(?:authoritative(?: source)?|source of truth|root cause).{0,60}"
            r"(?:unproven|unknown|undefined|unclear|not defined|cannot be proven)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "cannot_prove_source_of_truth",
        re.compile(
            r"(?:cannot|unable to|fails? to).{0,60}(?:prove|determine|identify).{0,60}"
            r"(?:authoritative|source of truth|root cause)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "conflicting_contract",
        re.compile(
            r"(?:conflicting|inconsistent).{0,40}(?:contract|requirement|source of truth)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "repeated_blocker",
        re.compile(
            r"(?:repeated|same|recurring).{0,40}(?:blocker|reject|failure)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)

_SCORE_RULES: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    (
        "architecture_or_contract_choice",
        2,
        re.compile(
            r"(?:architect(?:ure|ural).{0,40}(?:decision|choice|change|boundary)|"
            r"contract.{0,30}(?:choice|decision|change))",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "authoritative_source",
        2,
        re.compile(r"authoritative|source of truth|single source of truth", re.IGNORECASE),
    ),
    (
        "live_runtime",
        1,
        re.compile(
            r"\b(?:gazebo|ros\s*2|nav2|dds|hardware|world state)\b|live runtime|unrestricted runtime",
            re.IGNORECASE,
        ),
    ),
    (
        "end_to_end",
        1,
        re.compile(r"\be2e\b|end[- ]to[- ]end", re.IGNORECASE),
    ),
    (
        "integration_boundary",
        1,
        re.compile(r"\b(?:integration|backend|bridge|adapter)\b", re.IGNORECASE),
    ),
    (
        "observation_or_evidence",
        1,
        re.compile(r"\b(?:observation|observable|verification|evidence)\b", re.IGNORECASE),
    ),
)


def _explicit_task_class(text: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        parts = [re.escape(part) for part in re.split(r"[_ -]+", key) if part]
        flexible = r"[_ -]?".join(parts)
        pattern = re.compile(
            rf"(?im)^\s*(?:[-*]\s*)?{flexible}\s*:\s*(GREEN|YELLOW|RED)\s*$"
        )
        match = pattern.search(text)
        if match:
            return match.group(1).upper()
    return None


def classify_task(repo: Path, task_id: str, policy: ModelPolicy) -> TaskAssessment:
    path = locate_task_spec(repo, task_id)
    text = path.read_text(encoding="utf-8", errors="replace")
    explicit = _explicit_task_class(text, policy.classification.explicit_override_keys)
    rel = path.relative_to(repo).as_posix()
    if explicit:
        return TaskAssessment(
            task_id=task_id,
            task_class=explicit,
            score=0,
            reasons=(f"explicit override in {rel}",),
            task_path=rel,
            explicit_override=True,
        )

    hard_reasons = [name for name, pattern in _HARD_RED_RULES if pattern.search(text)]
    if hard_reasons:
        return TaskAssessment(
            task_id=task_id,
            task_class="RED",
            score=policy.classification.yellow_max_score + 1,
            reasons=tuple(f"hard-red:{name}" for name in hard_reasons),
            task_path=rel,
        )

    score = 0
    reasons: list[str] = []
    for name, weight, pattern in _SCORE_RULES:
        if pattern.search(text):
            score += weight
            reasons.append(f"+{weight}:{name}")

    if score <= policy.classification.green_max_score:
        task_class = "GREEN"
    elif score <= policy.classification.yellow_max_score:
        task_class = "YELLOW"
    else:
        task_class = "RED"
    if not reasons:
        reasons.append("no complexity signals")
    return TaskAssessment(
        task_id=task_id,
        task_class=task_class,
        score=score,
        reasons=tuple(reasons),
        task_path=rel,
    )


def text_requires_diagnosis(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in _HARD_RED_RULES)


_DIAGNOSIS_FINAL_STATUS_RE = re.compile(
    r"^\s*(?:[-*]\s*)?final\s+diagnosis\s+(?:status|result)\s*:\s*(RESOLVED|UNRESOLVED)\s*$",
    re.IGNORECASE,
)
_DIAGNOSIS_GENERIC_STATUS_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:diagnosis\s+)?(?:status|result)\s*:\s*(RESOLVED|UNRESOLVED)\s*$",
    re.IGNORECASE,
)
_DIAGNOSIS_HISTORY_NAME_RE = re.compile(r"^(?P<seq>\d+)_diagnosis\.md$", re.IGNORECASE)
_REVIEW_HISTORY_NAME_RE = re.compile(r"^(?P<seq>\d+)_(?:re)?review\.md$", re.IGNORECASE)


def parse_diagnosis_history_status(text: str) -> str | None:
    """Parse the final diagnosis status without substring ambiguity.

    Explicit `Final diagnosis status/result` wins. Otherwise a generic exact
    `Status/Result: RESOLVED|UNRESOLVED` form is accepted only when all such
    generic declarations agree. This intentionally prevents UNRESOLVED from
    matching RESOLVED by substring.
    """
    final_statuses: list[str] = []
    generic_statuses: list[str] = []
    for line in text.splitlines():
        match = _DIAGNOSIS_FINAL_STATUS_RE.match(line)
        if match:
            final_statuses.append(match.group(1).upper())
            continue
        match = _DIAGNOSIS_GENERIC_STATUS_RE.match(line)
        if match:
            generic_statuses.append(match.group(1).upper())

    if final_statuses:
        return final_statuses[-1]
    if generic_statuses and len(set(generic_statuses)) == 1:
        return generic_statuses[-1]
    return None


def diagnosis_history_sequence(path: Path) -> int | None:
    match = _DIAGNOSIS_HISTORY_NAME_RE.fullmatch(path.name)
    return int(match.group("seq")) if match else None


def latest_resolved_diagnosis(repo: Path, task_id: str) -> DiagnosisHistoryRecord | None:
    history_dir = repo / "docs" / "task_history" / task_id
    if not history_dir.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for path in history_dir.iterdir():
        if not path.is_file():
            continue
        sequence = diagnosis_history_sequence(path)
        if sequence is not None:
            candidates.append((sequence, path))
    for sequence, path in sorted(candidates, key=lambda item: item[0], reverse=True):
        try:
            status = parse_diagnosis_history_status(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if status == "RESOLVED":
            return DiagnosisHistoryRecord(path=path.resolve(), sequence=sequence, status=status)
    return None


def latest_review_history_sequence(repo: Path, task_id: str) -> int | None:
    history_dir = repo / "docs" / "task_history" / task_id
    if not history_dir.is_dir():
        return None
    sequences: list[int] = []
    for path in history_dir.iterdir():
        if not path.is_file():
            continue
        match = _REVIEW_HISTORY_NAME_RE.fullmatch(path.name)
        if match:
            sequences.append(int(match.group("seq")))
    return max(sequences) if sequences else None


def _clear_bound_diagnosis_state(state: dict[str, Any]) -> None:
    state["diagnosis_path"] = None
    state["diagnosis_sequence"] = None
    state["diagnosis_binding_source"] = None
    state["diagnosis_bound_at"] = None


def _diagnosis_path_exists(repo: Path, state: dict[str, Any]) -> bool:
    raw = state.get("diagnosis_path")
    if not raw:
        return False
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = repo / path
    return path.is_file()


def _checkpoint_diagnosis_record(state: dict[str, Any]) -> DiagnosisHistoryRecord | None:
    raw = state.get("diagnosis_path")
    if not raw:
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        repo_raw = state.get("repo")
        if repo_raw:
            path = Path(str(repo_raw)) / path
    if not path.is_file():
        return None
    sequence = diagnosis_history_sequence(path)
    if sequence is None:
        return None
    try:
        status = parse_diagnosis_history_status(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    if status != "RESOLVED":
        return None
    return DiagnosisHistoryRecord(path=path.resolve(), sequence=sequence, status=status)


def bind_latest_resolved_diagnosis(
    repo: Path,
    task_id: str,
    state: dict[str, Any],
    *,
    ctx: RunContext | None = None,
) -> bool:
    """Bind the newest durable RESOLVED task-history diagnosis into checkpoint state."""
    latest = latest_resolved_diagnosis(repo, task_id)
    latest_review_sequence = latest_review_history_sequence(repo, task_id)
    current = _checkpoint_diagnosis_record(state)
    current_raw = str(state.get("diagnosis_path") or "")

    def stale_after_review(record: DiagnosisHistoryRecord | None) -> bool:
        return bool(
            record is not None
            and latest_review_sequence is not None
            and record.sequence < latest_review_sequence
        )

    # A repository diagnosis older than a newer Review/Re-review generation is
    # stale for RED Fix resume. Never silently reuse it for the new finding.
    if latest is not None and stale_after_review(latest):
        latest = None
    if current is not None and stale_after_review(current):
        old_name = Path(current_raw).name if current_raw else None
        _clear_bound_diagnosis_state(state)
        if ctx is not None:
            ctx.progress(
                "BIND",
                f"{task_id} stale diagnosis cleared old={old_name or '-'} "
                f"latest_review_seq={latest_review_sequence}",
            )
        current = None
        current_raw = ""
        if latest is None:
            return True

    if latest is None:
        return False

    should_bind = current is None or latest.sequence > current.sequence

    # A transient Codex final output is intentionally superseded once durable
    # task history contains a current RESOLVED diagnosis. Rebind if any
    # checkpoint metadata disagrees with the durable record.
    if not should_bind and (
        state.get("diagnosis_binding_source") != "task_history"
        or state.get("diagnosis_sequence") != latest.sequence
        or current.path != latest.path
    ):
        should_bind = True

    if not should_bind:
        return False

    old_name = Path(current_raw).name if current_raw else None
    state["diagnosis_path"] = str(latest.path)
    state["diagnosis_sequence"] = latest.sequence
    state["diagnosis_binding_source"] = "task_history"
    state["diagnosis_bound_at"] = iso_now()
    if ctx is not None:
        if old_name and old_name != latest.path.name:
            ctx.progress(
                "BIND",
                f"{task_id} diagnosis refreshed old={old_name} new={latest.path.name} "
                f"source=task_history seq={latest.sequence}",
            )
        else:
            ctx.progress(
                "BIND",
                f"{task_id} diagnosis {latest.path.relative_to(repo).as_posix()} "
                f"source=task_history seq={latest.sequence} status=RESOLVED",
            )
    return True


GATE_BLOCKER_CLASSIFICATIONS = frozenset({
    "SAME_GATE",
    "REGRESSION",
    "NEW_EXTERNAL_FAULT_DOMAIN",
    "CONTRACT_OR_ARCHITECTURE_CONTRADICTION",
})


def normalize_gate_blocker(payload: dict[str, Any], *, gate_id: str | None = None) -> dict[str, str]:
    required = (
        "finding_id",
        "root_cause_class",
        "first_failing_invariant",
        "affected_boundary",
        "classification",
    )
    normalized: dict[str, str] = {"gate_id": str(payload.get("gate_id") or gate_id or "")}
    if not normalized["gate_id"]:
        raise OrchestratorError("Gate blocker is missing gate_id.")
    for key in required:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise OrchestratorError(f"Gate blocker is missing/invalid {key}.")
        normalized[key] = value.strip()
    if normalized["classification"] not in GATE_BLOCKER_CLASSIFICATIONS:
        raise OrchestratorError(
            f"Unsupported gate blocker classification: {normalized['classification']}"
        )
    return normalized


def gate_blocker_signature(blocker: dict[str, Any]) -> str:
    normalized = normalize_gate_blocker(blocker, gate_id=str(blocker.get("gate_id") or ""))
    identity = {
        key: normalized[key]
        for key in (
            "gate_id",
            "finding_id",
            "root_cause_class",
            "first_failing_invariant",
            "affected_boundary",
        )
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def register_gate_failure(
    gate_state: dict[str, Any],
    blocker: dict[str, Any],
    *,
    max_attempts: int = 3,
) -> str:
    normalized = normalize_gate_blocker(blocker, gate_id=str(blocker.get("gate_id") or ""))
    gate_state["current_blocker"] = normalized
    classification = normalized["classification"]
    if classification in {"NEW_EXTERNAL_FAULT_DOMAIN", "CONTRACT_OR_ARCHITECTURE_CONTRADICTION"}:
        return "STOP"
    signature = gate_blocker_signature(normalized)
    counts = gate_state.setdefault("blocker_attempt_counts", {})
    attempts = int(counts.get(signature) or 0) + 1
    counts[signature] = attempts
    if attempts >= max_attempts:
        return "ARCHITECTURE_REVIEW_REQUIRED"
    return "FIX"


def mark_gate_pass(gate_state: dict[str, Any], gate_id: str, record: dict[str, Any]) -> None:
    frozen = dict(record)
    frozen["status"] = "PASS"
    gate_state.setdefault("passed_gates", {})[gate_id] = frozen
    gate_state["current_blocker"] = None
    gate_state["current_gate_index"] = int(gate_state.get("current_gate_index") or 0) + 1


def begin_new_gate_attempt(gate_state: dict[str, Any]) -> None:
    gate_state["attempt_id"] = int(gate_state.get("attempt_id") or 1) + 1
    gate_state["supplier_cache"] = {}
    gate_state["current_blocker"] = None


def supplier_cache_key(gate_state: dict[str, Any], supplier_id: str) -> str:
    return f"attempt-{int(gate_state.get('attempt_id') or 1)}:{supplier_id}"


def supplier_cache_get(gate_state: dict[str, Any], supplier_id: str) -> Any:
    return gate_state.setdefault("supplier_cache", {}).get(supplier_cache_key(gate_state, supplier_id))


def supplier_cache_put(gate_state: dict[str, Any], supplier_id: str, value: Any) -> None:
    gate_state.setdefault("supplier_cache", {})[supplier_cache_key(gate_state, supplier_id)] = value


def _parse_prefixed_json(text: str, prefix: str) -> dict[str, Any] | None:
    candidates = [line.split(prefix, 1)[1].strip() for line in text.splitlines() if prefix in line]
    if not candidates:
        return None
    try:
        payload = json.loads(candidates[-1])
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid {prefix} JSON: {candidates[-1]}") from exc
    if not isinstance(payload, dict):
        raise OrchestratorError(f"{prefix} payload must be a JSON object.")
    return payload


def _resolve_command_executable(repo: Path, command0: str) -> str | None:
    if os.sep in command0:
        candidate = Path(command0)
        if not candidate.is_absolute():
            candidate = repo / candidate
        return str(candidate.resolve()) if candidate.exists() else None
    resolved = shutil.which(command0)
    return str(Path(resolved).resolve()) if resolved else None


def _detect_command_interpreter(resolved_executable: str | None) -> str | None:
    if not resolved_executable:
        return None
    path = Path(resolved_executable)
    name = path.name.lower()
    if name.startswith("python") or name.startswith("pypy"):
        return str(path.resolve())
    try:
        first = path.open("rb").readline(4096).decode("utf-8", errors="replace").strip()
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    shebang = first[2:].strip().split()
    if not shebang:
        return None
    if Path(shebang[0]).name == "env" and len(shebang) > 1:
        resolved = shutil.which(shebang[1])
        return str(Path(resolved).resolve()) if resolved else shebang[1]
    return str(Path(shebang[0]).resolve()) if Path(shebang[0]).exists() else shebang[0]


def _extract_test_count(text: str) -> int | None:
    patterns = (
        r"(?:^|\s)(\d+)\s+passed(?:\s|,|$)",
        r"collected\s+(\d+)\s+items?",
        r"Ran\s+(\d+)\s+tests?",
    )
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            try:
                return int(matches[-1])
            except ValueError:
                pass
    return None


def run_literal_validation(repo: Path, argv: tuple[str, ...]) -> dict[str, Any]:
    command = _string_argv(list(argv), label="literal validation command")
    resolved = _resolve_command_executable(repo, command[0])
    record = run_exact_argv(repo, command)
    combined = record["stdout"] + "\n" + record["stderr"]
    return {
        "requested_command": list(command),
        "resolved_executable": resolved,
        "interpreter": _detect_command_interpreter(resolved),
        "exit_code": record["exit_code"],
        "test_count": _extract_test_count(combined),
        "git_sha": record["head"],
        "duration_seconds": record["duration_seconds"],
        "recorded_at": record["recorded_at"],
        "stdout_sha256": hashlib.sha256(record["stdout"].encode("utf-8", errors="replace")).hexdigest(),
        "stderr_sha256": hashlib.sha256(record["stderr"].encode("utf-8", errors="replace")).hexdigest(),
    }


def accumulate_stage_record(
    state: dict[str, Any],
    record: StageRunRecord,
    *,
    logical_role: str | None = None,
) -> None:
    aggregate = state.setdefault("aggregate", {})
    for key in (
        "orchestrator_runs", "codex_calls", "reported_tokens_total", "diagnosis_calls",
        "gate_fix_calls", "review_fix_calls", "review_calls", "gate_resolution_cycles",
    ):
        aggregate.setdefault(key, 0)
    aggregate["codex_calls"] = int(aggregate["codex_calls"] or 0) + 1
    aggregate["reported_tokens_total"] = int(aggregate["reported_tokens_total"] or 0) + int(record.tokens_reported or 0)
    role = logical_role or record.role
    if role in {"diagnosis", "diagnosis_escalated"}:
        aggregate["diagnosis_calls"] = int(aggregate["diagnosis_calls"] or 0) + 1
    elif role == "gate_fix":
        aggregate["gate_fix_calls"] = int(aggregate["gate_fix_calls"] or 0) + 1
    elif role == "fix":
        aggregate["review_fix_calls"] = int(aggregate["review_fix_calls"] or 0) + 1
    elif role in {"review", "rereview"}:
        aggregate["review_calls"] = int(aggregate["review_calls"] or 0) + 1


def merge_run_stage_metrics(state: dict[str, Any], records: list[StageRunRecord], *, run_id: str) -> bool:
    counted = state.setdefault("aggregate_counted_runs", [])
    if run_id in counted:
        return False
    for record in records:
        accumulate_stage_record(state, record, logical_role=record.role)
    counted.append(run_id)
    return True


def invalidate_staged_proof(state: dict[str, Any]) -> None:
    gate_state = state.setdefault("gate_state", {})
    gate_state["current_gate_index"] = 0
    gate_state["attempt_id"] = int(gate_state.get("attempt_id") or 1) + 1
    gate_state["passed_gates"] = {}
    gate_state["current_blocker"] = None
    gate_state["blocker_attempt_counts"] = {}
    gate_state["supplier_cache"] = {}
    state["finalization"] = {
        "source_commit": None,
        "source_hashes": {},
        "canonical_results": [],
        "binding_verified": False,
    }
    state["literal_validation"] = {"results": []}
    state["review_status"] = None
    state["accepted_commit"] = None
    state["acceptance_path"] = None
    state["acceptance_commit"] = None


def run_exact_argv(repo: Path, argv: tuple[str, ...] | list[str]) -> dict[str, Any]:
    command = [str(x) for x in argv]
    if not command:
        raise OrchestratorError("Cannot execute an empty command.")
    started = time.monotonic()
    proc = subprocess.run(
        command,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    ended = time.monotonic()
    combined = proc.stdout + "\n" + proc.stderr
    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_seconds": round(ended - started, 3),
        "head": run_git(repo, "rev-parse", "HEAD").stdout.strip(),
        "result_sha256": hashlib.sha256(combined.encode("utf-8", errors="replace")).hexdigest(),
        "recorded_at": iso_now(),
    }


def _porcelain_changed_paths(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise OrchestratorError(
            "git status --porcelain failed: " + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    fields = proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    paths: list[str] = []
    i = 0
    while i < len(fields):
        field = fields[i]
        if not field:
            i += 1
            continue
        if len(field) < 4:
            i += 1
            continue
        status = field[:2]
        paths.append(field[3:])
        if "R" in status or "C" in status:
            if i + 1 < len(fields) and fields[i + 1]:
                paths.append(fields[i + 1])
                i += 1
        i += 1
    return sorted(set(paths))


def _tracked_files_at_commit(repo: Path, commit: str, scopes: tuple[str, ...]) -> list[str]:
    files: set[str] = set()
    for scope in scopes:
        proc = run_git(repo, "ls-tree", "-r", "--name-only", commit, "--", scope, check=False)
        if proc.returncode != 0:
            raise OrchestratorError(f"Unable to enumerate protected path at {commit}: {scope}")
        for line in proc.stdout.splitlines():
            if line.strip():
                files.add(line.strip())
        if not proc.stdout.strip():
            exists = run_git(repo, "cat-file", "-e", f"{commit}:{scope}", check=False)
            if exists.returncode == 0:
                files.add(scope)
    return sorted(files)


def snapshot_protected_artifacts(
    repo: Path,
    protected_paths: tuple[str, ...],
    *,
    authority_commit: str | None = None,
) -> dict[str, dict[str, str]]:
    if not protected_paths:
        return {}
    commit = authority_commit or run_git(repo, "rev-parse", "HEAD").stdout.strip()
    files = _tracked_files_at_commit(repo, commit, protected_paths)
    if not files:
        raise OrchestratorError(
            "PROTECTED_ARTIFACT_VIOLATION: declared protected paths resolve to no tracked files."
        )
    snapshot: dict[str, dict[str, str]] = {}
    for path in files:
        oid_proc = run_git(repo, "rev-parse", f"{commit}:{path}", check=False)
        if oid_proc.returncode != 0:
            raise OrchestratorError(f"PROTECTED_ARTIFACT_VIOLATION: cannot resolve {commit}:{path}")
        snapshot[path] = {
            "authority_commit": commit,
            "git_blob_oid": oid_proc.stdout.strip(),
            "sha256": git_path_sha256(repo, commit, path),
        }
    return snapshot


def assert_protected_artifacts_unchanged(
    repo: Path,
    protected_paths: tuple[str, ...],
    snapshot: dict[str, Any],
) -> None:
    if not protected_paths:
        return
    dirty = [p for p in _porcelain_changed_paths(repo) if _path_within_scopes(p, protected_paths)]
    if dirty:
        raise OrchestratorError(
            "PROTECTED_ARTIFACT_VIOLATION: protected paths are dirty: " + ", ".join(dirty)
        )
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    current_files = set(_tracked_files_at_commit(repo, head, protected_paths))
    expected_files = set(snapshot)
    if current_files != expected_files:
        added = sorted(current_files - expected_files)
        removed = sorted(expected_files - current_files)
        raise OrchestratorError(
            "PROTECTED_ARTIFACT_VIOLATION: protected tracked set changed; "
            f"added={added}, removed={removed}"
        )
    for path, record_any in snapshot.items():
        if not isinstance(record_any, dict):
            raise OrchestratorError("PROTECTED_ARTIFACT_VIOLATION: invalid protected snapshot record.")
        record = record_any
        oid_proc = run_git(repo, "rev-parse", f"{head}:{path}", check=False)
        current_oid = oid_proc.stdout.strip() if oid_proc.returncode == 0 else None
        current_sha = git_path_sha256(repo, head, path) if current_oid else None
        if current_oid != record.get("git_blob_oid") or current_sha != record.get("sha256"):
            raise OrchestratorError(
                f"PROTECTED_ARTIFACT_VIOLATION: immutable predecessor changed at {path}."
            )


def _path_within_scopes(path: str, scopes: tuple[str, ...] | list[str]) -> bool:
    normalized = Path(path).as_posix().rstrip("/")
    for raw in scopes:
        scope = Path(str(raw)).as_posix().rstrip("/")
        if normalized == scope or normalized.startswith(scope + "/"):
            return True
    return False


def _git_blob_bytes(repo: Path, commit: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=repo,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise OrchestratorError(
            f"Cannot reproduce source path from immutable Git state: {commit}:{path}: "
            + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    return proc.stdout


def git_path_sha256(repo: Path, commit: str, path: str) -> str:
    return hashlib.sha256(_git_blob_bytes(repo, commit, path)).hexdigest()


def _source_files_at_commit(repo: Path, commit: str, source_paths: tuple[str, ...]) -> list[str]:
    files: set[str] = set()
    for source in source_paths:
        proc = run_git(repo, "ls-tree", "-r", "--name-only", commit, "--", source, check=False)
        if proc.returncode != 0:
            raise OrchestratorError(f"Unable to enumerate source path at {commit}: {source}")
        for line in proc.stdout.splitlines():
            if line.strip():
                files.add(line.strip())
        if not proc.stdout.strip():
            # A direct file may still be absent; fail closed rather than hash worktree bytes.
            exists = run_git(repo, "cat-file", "-e", f"{commit}:{source}", check=False)
            if exists.returncode == 0:
                files.add(source)
    return sorted(files)


def commit_source_finalization(
    repo: Path,
    *,
    task_id: str,
    source_paths: tuple[str, ...],
    finalization_paths: tuple[str, ...] | None = None,
    ctx: RunContext | None = None,
    protected_paths: tuple[str, ...] = (),
    protected_snapshot: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    if protected_paths:
        assert_protected_artifacts_unchanged(repo, protected_paths, protected_snapshot or {})
    if not source_paths:
        raise OrchestratorError("SOURCE_FINALIZATION_SCOPE_VIOLATION: source_paths is empty.")
    commit_paths = finalization_paths or source_paths
    if not commit_paths:
        raise OrchestratorError("SOURCE_FINALIZATION_SCOPE_VIOLATION: finalization_paths is empty.")
    missing_source_scopes = [path for path in source_paths if not _path_within_scopes(path, commit_paths)]
    if missing_source_scopes:
        raise OrchestratorError(
            "SOURCE_FINALIZATION_SCOPE_VIOLATION: finalization_paths do not include source scope: "
            + ", ".join(missing_source_scopes)
        )
    dirty = changed_paths(repo)
    outside = [path for path in dirty if not _path_within_scopes(path, commit_paths)]
    if outside:
        raise OrchestratorError(
            "SOURCE_FINALIZATION_SCOPE_VIOLATION: dirty paths outside declared finalization scope: "
            + ", ".join(outside)
        )
    if ctx:
        ctx.progress("FINALIZE", f"{task_id} immutable source boundary")
    run_git(repo, "add", "--", *commit_paths)
    run_git(repo, "diff", "--cached", "--check")
    staged = run_git(repo, "diff", "--cached", "--quiet", check=False)
    if staged.returncode != 0:
        scope = task_scope(task_id)
        subject = f"chore({scope}): {task_id} source finalized"
        body = "\n".join([
            f"Task: {task_id}",
            "Workflow-Stage: source-finalization",
            "Automation: codex-task-orchestrator",
        ])
        run_git(repo, "commit", "-m", subject, "-m", body)
    source_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if worktree_status(repo):
        raise OrchestratorError("SOURCE_FINALIZATION_SCOPE_VIOLATION: worktree not clean after source commit.")
    files = _source_files_at_commit(repo, source_commit, source_paths)
    source_hashes = {path: git_path_sha256(repo, source_commit, path) for path in files}
    return source_commit, source_hashes


def verify_canonical_evidence_bindings(
    repo: Path,
    source_commit: str,
    evidence_paths: tuple[str, ...],
) -> dict[str, Any]:
    verified: dict[str, Any] = {}
    for rel in evidence_paths:
        path = repo / rel
        if not path.is_file():
            raise OrchestratorError(f"Canonical evidence missing: {rel}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise OrchestratorError(f"Canonical evidence is invalid JSON: {rel}") from exc
        if not isinstance(payload, dict):
            raise OrchestratorError(f"Canonical evidence must be a JSON object: {rel}")
        actual_source = payload.get("source_git_sha")
        if actual_source != source_commit:
            raise OrchestratorError(
                f"Canonical evidence source_git_sha mismatch for {rel}: "
                f"expected {source_commit}, got {actual_source}"
            )
        declared_hashes = payload.get("source_hashes") or {}
        if not isinstance(declared_hashes, dict):
            raise OrchestratorError(f"Canonical evidence source_hashes must be an object: {rel}")
        reproduced: dict[str, str] = {}
        for source_path, declared in declared_hashes.items():
            if not isinstance(source_path, str) or not isinstance(declared, str):
                raise OrchestratorError(f"Invalid source_hashes entry in {rel}")
            actual = git_path_sha256(repo, source_commit, source_path)
            if actual != declared:
                raise OrchestratorError(
                    f"Canonical evidence source hash mismatch for {rel}:{source_path}: "
                    f"expected {actual}, got {declared}"
                )
            reproduced[source_path] = actual
        verified[rel] = {
            "source_git_sha": source_commit,
            "source_hashes": reproduced,
            "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return verified


def assert_finalization_authority_unchanged(
    repo: Path,
    *,
    finalization: dict[str, Any],
    source_paths: tuple[str, ...],
    evidence_paths: tuple[str, ...],
    literal_results: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> None:
    if not bool(finalization.get("binding_verified")):
        raise OrchestratorError("FINALIZATION_AUTHORITY_VIOLATION: binding is not verified.")
    source_commit = finalization.get("source_commit")
    if not isinstance(source_commit, str) or not source_commit:
        raise OrchestratorError("FINALIZATION_AUTHORITY_VIOLATION: source_commit is missing.")
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if head != source_commit:
        raise OrchestratorError(
            f"FINALIZATION_AUTHORITY_VIOLATION: HEAD changed after source finalization: {head} != {source_commit}"
        )
    dirty_source = [p for p in _porcelain_changed_paths(repo) if _path_within_scopes(p, source_paths)]
    if dirty_source:
        raise OrchestratorError(
            "FINALIZATION_AUTHORITY_VIOLATION: source paths changed after source_commit: "
            + ", ".join(dirty_source)
        )
    binding = finalization.get("binding")
    if not isinstance(binding, dict):
        raise OrchestratorError("FINALIZATION_AUTHORITY_VIOLATION: canonical binding record is missing.")
    verify_canonical_evidence_bindings(repo, source_commit, evidence_paths)
    for rel in evidence_paths:
        record = binding.get(rel)
        if not isinstance(record, dict) or not isinstance(record.get("evidence_sha256"), str):
            raise OrchestratorError(
                f"FINALIZATION_AUTHORITY_VIOLATION: recorded evidence hash missing for {rel}."
            )
        path = repo / rel
        if not path.is_file():
            raise OrchestratorError(f"FINALIZATION_AUTHORITY_VIOLATION: evidence missing: {rel}")
        current_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if current_sha != record["evidence_sha256"]:
            raise OrchestratorError(
                f"FINALIZATION_AUTHORITY_VIOLATION: canonical evidence changed after binding: {rel}"
            )
    for result in literal_results:
        if result.get("exit_code") != 0 or result.get("git_sha") != source_commit:
            raise OrchestratorError(
                "FINALIZATION_AUTHORITY_VIOLATION: literal validation is not bound to source_commit."
            )


def run_gate_command(repo: Path, gate: dict[str, Any]) -> tuple[bool, dict[str, Any], dict[str, str] | None]:
    gate_id = str(gate.get("id") or "")
    if not gate_id:
        raise OrchestratorError("Gate is missing id.")
    argv = _string_argv(gate.get("command"), label=f"gate {gate_id} command")
    record = run_exact_argv(repo, argv)
    record["gate_id"] = gate_id
    payload = _parse_prefixed_json(record["stdout"] + "\n" + record["stderr"], GATE_RESULT_PREFIX)
    if record["exit_code"] == 0:
        if payload is not None and str(payload.get("status") or "PASS").upper() not in {"PASS", "COMPLETE"}:
            raise OrchestratorError(f"Gate {gate_id} exited 0 but reported non-PASS status.")
        return True, record, None
    if payload is None:
        payload = {
            "gate_id": gate_id,
            "finding_id": f"{gate_id}-PROTOCOL",
            "root_cause_class": "GATE_RESULT_PROTOCOL",
            "first_failing_invariant": "machine_readable_gate_result",
            "affected_boundary": "gate_runner",
            "classification": "CONTRACT_OR_ARCHITECTURE_CONTRADICTION",
        }
    blocker = normalize_gate_blocker(payload, gate_id=gate_id)
    return False, record, blocker


def gate_fix_child_prompt(task_id: str, gate: dict[str, Any], blocker: dict[str, Any]) -> str:
    base = child_prompt(task_id=task_id, worker_role="gate_fix")
    context = [
        "",
        "GATE_FIX_CONTEXT:",
        f"gate_id={gate.get('id')}",
        "gate_command_json=" + json.dumps(gate.get("command"), ensure_ascii=False),
        "blocker_json=" + json.dumps(blocker, ensure_ascii=False, sort_keys=True),
        "Resolve exactly this blocker. Do not advance to another gate.",
    ]
    return base + "\n" + "\n".join(context)


def diagnosis_trigger_signature(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def review_reject_next_phase(task_class: str, review_text: str) -> str:
    if task_class == "RED" or text_requires_diagnosis(review_text):
        return "diagnosis"
    return "fix"


def fix_not_ready_next_phase(
    task_class: str,
    fix_text: str,
    *,
    diagnosed_trigger_signature: str | None,
) -> str:
    del task_class  # class is retained in the interface for policy evolution.
    if not text_requires_diagnosis(fix_text):
        return "stop"
    signature = diagnosis_trigger_signature(fix_text)
    if diagnosed_trigger_signature == signature:
        return "stop"
    return "diagnosis"


def rereview_reject_next_phase(
    task_class: str,
    rereview_text: str,
    *,
    fix_budget_available: bool,
) -> str:
    if task_class == "RED" or text_requires_diagnosis(rereview_text):
        return "diagnosis"
    return "fix" if fix_budget_available else "stop"


def latest_stage_record(ctx: RunContext, task_id: str, role: str) -> StageRunRecord | None:
    return next(
        (record for record in reversed(ctx.stage_records) if record.task_id == task_id and record.role == role),
        None,
    )


def latest_stage_final_text(ctx: RunContext, task_id: str, role: str) -> str:
    record = latest_stage_record(ctx, task_id, role)
    if not record or not record.final_path:
        return ""
    path = Path(record.final_path)
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


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
    "gate_fix": "prompts/codex/fix_gate_v1.md",
    "diagnosis": "prompts/codex/diagnose_task_v1.md",
    "diagnosis_escalated": "prompts/codex/diagnose_task_v1.md",
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
    diagnosis_path: str | None = None,
    diagnosis_reason: str | None = None,
    diagnosis_binding_source: str | None = None,
    diagnosis_sequence: int | None = None,
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

    if worker_role == "acceptance":
        lines.append(f"acceptance_path={expected_acceptance_path(task_id).as_posix()}")

    if diagnosis_path:
        lines.append(f"upstream_diagnosis_path={diagnosis_path}")
        lines.append("Read that bounded diagnosis before editing or re-reviewing.")
    if diagnosis_reason:
        lines.append(f"diagnosis_reason={diagnosis_reason}")
    if diagnosis_binding_source:
        lines.append(f"diagnosis_binding_source={diagnosis_binding_source}")
    if diagnosis_sequence is not None:
        lines.append(f"diagnosis_sequence={diagnosis_sequence}")

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
    "diagnosis",
    "diagnosis_escalated",
    "implementation",
    "gate_resolution",
    "finalization",
    "literal_validation",
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
    state["schema_version"] = 3
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
        "schema_version": 3,
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
        "diagnosis": "diagnosis",
        "diagnosis_escalated": "diagnosis_escalated",
        "implementation": "implementation",
        "review": "review",
        "fix": "fix",
        "rereview": "rereview",
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
        diagnosis_path=state.get("diagnosis_path"),
        diagnosis_reason=state.get("diagnosis_reason"),
        diagnosis_binding_source=state.get("diagnosis_binding_source"),
        diagnosis_sequence=state.get("diagnosis_sequence"),
    )
    path = ctx.run_dir / "resume_prompt.txt"
    path.write_text(prompt, encoding="utf-8")
    return path



def terminate_child_process(
    proc: subprocess.Popen[str],
    *,
    interrupt_grace: float = 2.0,
    terminate_grace: float = 2.0,
) -> None:
    """Stop one Codex child process group without leaving an orphan.

    Children are launched in a new session, so Ctrl+C reaches the host
    orchestrator first. The host then performs SIGINT -> SIGTERM -> SIGKILL
    escalation on the entire child process group.
    """
    if proc.poll() is not None:
        return

    def send(sig: int) -> None:
        try:
            if os.name == "posix":
                os.killpg(proc.pid, sig)
            elif sig == signal.SIGKILL:
                proc.kill()
            else:
                proc.terminate()
        except ProcessLookupError:
            pass

    send(signal.SIGINT)
    try:
        proc.wait(timeout=interrupt_grace)
        return
    except subprocess.TimeoutExpired:
        pass

    send(signal.SIGTERM)
    try:
        proc.wait(timeout=terminate_grace)
        return
    except subprocess.TimeoutExpired:
        pass

    send(signal.SIGKILL)
    try:
        proc.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        pass


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
    sandbox = runtime_sandbox_override()

    record = ctx.new_stage(task_id, role, config)
    log_path = Path(record.log_path or "")
    final_path = Path(record.final_path or "")
    prompt_path = Path(record.prompt_path or "")
    prompt_path.write_text(prompt, encoding="utf-8")
    ctx.progress("START", f"{task_id} {role.upper()} — {config.model} / {config.reasoning_effort}")
    if sandbox is not None:
        ctx.progress("SANDBOX", f"{task_id} {role.upper()} — {sandbox}")

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="codex-last-", suffix=".txt", delete=False
    ) as handle:
        last_message = Path(handle.name)

    started = time.monotonic()
    try:
        cmd = [
            "codex",
            "exec",
            *(["-s", sandbox] if sandbox is not None else []),
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
                start_new_session=True,
            )
            assert proc.stdout is not None
            q: queue.Queue[str | None] = queue.Queue()
            reader = threading.Thread(target=_reader_thread, args=(proc.stdout, q), daemon=True)
            reader.start()
            ctx.progress(
                "CHILD",
                f"{task_id} {role.upper()} pid={proc.pid} started; waiting for Codex output",
            )
            last_heartbeat = time.monotonic()
            first_output_seen = False
            stream_done = False

            try:
                while not stream_done:
                    timeout = 1.0
                    try:
                        item = q.get(timeout=timeout)
                    except queue.Empty:
                        item = ""
                    if item is None:
                        stream_done = True
                    elif item:
                        if not first_output_seen:
                            first_output_seen = True
                            ctx.progress(
                                "ACTIVE",
                                f"{task_id} {role.upper()} child output detected",
                            )
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
                        state = "active" if first_output_seen else "starting"
                        ctx.progress(
                            "WAIT",
                            f"{task_id} {role.upper()} {state} ({elapsed}s)",
                        )
                        last_heartbeat = now
            except KeyboardInterrupt:
                ctx.progress(
                    "INTERRUPT",
                    f"{task_id} {role.upper()} Ctrl+C received; stopping child cleanly",
                )
                terminate_child_process(proc)
                reader.join(timeout=2)
                log_file.flush()

                final_message = (
                    last_message.read_text(encoding="utf-8")
                    if last_message.exists()
                    else ""
                )
                final_path.write_text(final_message, encoding="utf-8")
                ended = time.monotonic()
                record.ended_at = iso_now()
                record.duration_seconds = round(ended - started, 3)
                record.exit_code = proc.poll()
                record.tokens_reported = extract_tokens(log_path)
                record.signals = extract_signal_lines(final_message)
                record.error_type = "INTERRUPTED"
                record.error_message = "Interrupted by Ctrl+C while child Codex was running."
                ctx.add_error(
                    kind="INTERRUPTED",
                    stage=role,
                    task_id=task_id,
                    message=record.error_message,
                    signals=record.signals,
                    log_path=str(log_path),
                    final_path=str(final_path),
                )
                raise ChildInterruptedError(
                    record.error_message,
                    task_id=task_id,
                    role=role,
                    log_path=log_path,
                    final_path=final_path,
                )

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


ACCEPTANCE_DIR = Path("results/reviews")


def expected_acceptance_filename(task_id: str) -> str:
    return f"{task_short(task_id)}_acceptance.json"


def expected_acceptance_path(task_id: str) -> Path:
    """Return the repository-wide canonical acceptance manifest path."""
    return ACCEPTANCE_DIR / expected_acceptance_filename(task_id)


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
    protected_paths: tuple[str, ...] = (),
    protected_snapshot: dict[str, Any] | None = None,
) -> str:
    if protected_paths:
        assert_protected_artifacts_unchanged(repo, protected_paths, protected_snapshot or {})
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
    expected_path = expected_acceptance_path(task_id)
    if rel_path != expected_path:
        raise OrchestratorError(
            "Acceptance path mismatch: "
            f"expected {expected_path.as_posix()}, got {rel_path.as_posix()}"
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


def write_deterministic_acceptance(
    repo: Path,
    *,
    task_id: str,
    accepted_commit: str,
) -> str:
    """Record canonical acceptance without spending a Codex/LLM call."""
    ensure_clean_worktree(repo)
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if head != accepted_commit:
        raise OrchestratorError(
            "Acceptance recording requires HEAD to equal accepted_commit. "
            f"HEAD={head}, accepted_commit={accepted_commit}"
        )

    rel_path = expected_acceptance_path(task_id)
    abs_path = repo / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema_version": 1,
        "task_id": task_id,
        "status": "ACCEPT",
        "accepted_commit": accepted_commit,
        "recorded_at": iso_now(),
        "recorded_by": "codex-task-orchestrator",
        "recording_mode": "deterministic",
        "workflow_complete": True,
    }
    abs_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    paths = changed_paths(repo)
    if paths != [rel_path.as_posix()]:
        raise OrchestratorError(
            "Deterministic acceptance changed unexpected files. "
            f"Expected only {rel_path.as_posix()}, got {paths}"
        )
    reread = json.loads(abs_path.read_text(encoding="utf-8"))
    if reread.get("task_id") != task_id or reread.get("status") != "ACCEPT":
        raise OrchestratorError("Deterministic acceptance artifact identity/status mismatch.")
    if reread.get("accepted_commit") != accepted_commit:
        raise OrchestratorError("Deterministic acceptance artifact accepted_commit mismatch.")
    return rel_path.as_posix()


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
            expected_path = expected_acceptance_path(task_id).as_posix()
            if dirty != [expected_path]:
                raise OrchestratorError(
                    "Acceptance resume may start dirty only when the sole changed "
                    f"path is {expected_path}; got {dirty}"
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
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "stage": "acceptance",
        "status": "RECORDED",
        "accepted_commit": accepted_commit,
        "acceptance_path": acceptance_path,
        "acceptance_commit": acceptance_commit,
        "model_role": "acceptance",
        "model": "deterministic",
        "reasoning_effort": "none",
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


def run_task(
    task_id: str,
    repo: Path,
    policy: ModelPolicy,
    *,
    ctx: RunContext,
    max_fix_cycles: int = 1,
    resume_state: dict[str, Any] | None = None,
    resume_force: bool = False,
) -> dict[str, Any]:
    """Run or resume one TASK lifecycle with class-aware bounded model routing."""
    events: list[dict[str, Any]] = []
    contract = load_task_orchestrator_contract(repo, task_id)
    staged = contract is not None

    if resume_state is None:
        ensure_clean_worktree(repo)
        initial_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        assessment = classify_task(repo, task_id, policy)
        class_cfg = policy.task_classes[assessment.task_class]
        initial_phase = "diagnosis" if class_cfg.diagnosis_required else "implementation"
        state: dict[str, Any] = {
            "schema_version": 3,
            "task_id": task_id,
            "repo": str(repo),
            "branch": current_branch(repo),
            "initial_head": initial_head,
            "current_head": initial_head,
            "phase": initial_phase,
            "status": "RUNNING",
            "task_assessment": asdict(assessment),
            "effective_task_class": assessment.task_class,
            "diagnosis_return_phase": "implementation",
            "diagnosis_reason": "initial_red_classification" if class_cfg.diagnosis_required else None,
            "diagnosis_path": None,
            "diagnosis_sequence": None,
            "diagnosis_binding_source": None,
            "diagnosis_bound_at": None,
            "diagnosis_trigger_stage": "classification" if class_cfg.diagnosis_required else None,
            "diagnosis_trigger_path": None,
            "diagnosis_trigger_signature": None,
            "implementation_escalated": False,
            "implementation_resume_after_diagnosis": False,
            "fix_resume_after_diagnosis": False,
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
        state = upgrade_checkpoint_state(state, staged=staged)
        if staged and contract is not None and contract.protected_paths:
            state["protected_artifacts"] = snapshot_protected_artifacts(
                repo, contract.protected_paths, authority_commit=initial_head
            )
        state["aggregate"]["orchestrator_runs"] += 1
        save_resume_checkpoint(ctx, task_id, state)
        resuming = False
        resume_source_dir: str | None = None
        resume_reason: str | None = None
        ctx.progress(
            "CLASS",
            f"{task_id}={assessment.task_class} score={assessment.score} "
            f"({'; '.join(assessment.reasons)})",
        )
    else:
        state = upgrade_checkpoint_state(dict(resume_state), staged=staged)
        if staged and contract is not None and contract.protected_paths and not state.get("protected_artifacts"):
            authority = str(state.get("initial_head") or run_git(repo, "rev-parse", "HEAD").stdout.strip())
            state["protected_artifacts"] = snapshot_protected_artifacts(
                repo, contract.protected_paths, authority_commit=authority
            )
        state["aggregate"]["orchestrator_runs"] = int(state["aggregate"].get("orchestrator_runs") or 0) + 1
        current_head_for_resume = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        current_branch_for_resume = current_branch(repo)
        provenance_mismatch = bool(
            (state.get("current_head") and state.get("current_head") != current_head_for_resume)
            or (state.get("branch") and state.get("branch") != current_branch_for_resume)
        )
        validate_resume_state(repo, task_id, state, force=resume_force)
        if staged and resume_force and provenance_mismatch:
            invalidate_staged_proof(state)
            if str(state.get("phase") or "") not in {"diagnosis", "diagnosis_escalated", "implementation"}:
                state["phase"] = "gate_resolution"
            state["last_error"] = "Forced resume provenance mismatch invalidated staged qualification proof."
            if contract is not None and contract.protected_paths:
                assert_protected_artifacts_unchanged(
                    repo, contract.protected_paths, state.get("protected_artifacts") or {}
                )
        if not isinstance(state.get("task_assessment"), dict):
            assessment = classify_task(repo, task_id, policy)
            state["task_assessment"] = asdict(assessment)
            state.setdefault("effective_task_class", assessment.task_class)
        else:
            raw_assessment = state["task_assessment"]
            assessment = TaskAssessment(
                task_id=str(raw_assessment.get("task_id", task_id)),
                task_class=str(raw_assessment.get("task_class", "GREEN")),
                score=int(raw_assessment.get("score", 0)),
                reasons=tuple(raw_assessment.get("reasons") or ()),
                task_path=str(raw_assessment.get("task_path", "")),
                explicit_override=bool(raw_assessment.get("explicit_override", False)),
            )
        state.setdefault("diagnosis_return_phase", "implementation")
        state.setdefault("diagnosis_reason", None)
        state.setdefault("diagnosis_path", None)
        state.setdefault("diagnosis_sequence", None)
        state.setdefault("diagnosis_binding_source", None)
        state.setdefault("diagnosis_bound_at", None)
        state.setdefault("diagnosis_trigger_stage", None)
        state.setdefault("diagnosis_trigger_path", None)
        state.setdefault("diagnosis_trigger_signature", None)
        state.setdefault("implementation_escalated", False)
        state.setdefault("implementation_resume_after_diagnosis", False)
        state.setdefault("fix_resume_after_diagnosis", False)
        resume_phase_name = str(state.get("phase") or "")
        effective_resume_class = str(state.get("effective_task_class") or assessment.task_class)
        if resume_phase_name == "fix":
            bind_latest_resolved_diagnosis(repo, task_id, state, ctx=ctx)
            if effective_resume_class == "RED" and not _diagnosis_path_exists(repo, state):
                state["phase"] = "diagnosis"
                state["diagnosis_return_phase"] = "fix"
                state["diagnosis_reason"] = "fix_resume_missing_current_resolved_diagnosis"
                state["diagnosis_trigger_stage"] = "resume_fix"
                state["diagnosis_trigger_path"] = None
                state["diagnosis_trigger_signature"] = None
                state["fix_resume_after_diagnosis"] = True
                ctx.progress("ESCALATE", f"{task_id} fix resume lacks current diagnosis → RED diagnosis")
        if (
            resume_phase_name == "implementation"
            and effective_resume_class == "RED"
            and bool(state.get("implementation_resume_after_diagnosis"))
        ):
            bind_latest_resolved_diagnosis(repo, task_id, state, ctx=ctx)
            durable_diagnosis = _checkpoint_diagnosis_record(state)
            if (
                state.get("diagnosis_binding_source") != "task_history"
                or durable_diagnosis is None
            ):
                _clear_bound_diagnosis_state(state)
                state["phase"] = "diagnosis"
                state["diagnosis_return_phase"] = "implementation"
                state["diagnosis_reason"] = "implementation_resume_missing_current_resolved_diagnosis"
                state["diagnosis_trigger_stage"] = "resume_implementation"
                state["diagnosis_trigger_path"] = None
                state["diagnosis_trigger_signature"] = None
                state["implementation_resume_after_diagnosis"] = True
                ctx.progress(
                    "ESCALATE",
                    f"{task_id} implementation resume lacks current diagnosis → RED diagnosis",
                )
        resume_source_dir = state.get("current_run_dir") or state.get("previous_run_dir")
        resume_reason = state.get("last_error") or state.get("status")
        state["previous_run_dir"] = resume_source_dir
        state["current_run_dir"] = str(ctx.run_dir)
        state["max_fix_cycles"] = max_fix_cycles
        state["status"] = "RESUMING"
        save_resume_checkpoint(ctx, task_id, state)
        resuming = True
        ctx.progress(
            "RESUME",
            f"{task_id} from phase={state['phase']} class={state.get('effective_task_class')}",
        )

    commits: list[str] = list(state.get("commits") or [])
    phase = str(state["phase"])
    resume_phase = phase if resuming else None

    def is_resumed_stage(name: str) -> bool:
        return bool(resuming and resume_phase == name)

    def effective_class() -> str:
        value = str(state.get("effective_task_class") or assessment.task_class)
        if value not in policy.task_classes:
            raise OrchestratorError(f"Invalid effective TASK class in checkpoint: {value}")
        return value

    def clear_diagnosis_binding() -> None:
        state["diagnosis_path"] = None
        state["diagnosis_sequence"] = None
        state["diagnosis_binding_source"] = None
        state["diagnosis_bound_at"] = None

    def schedule_diagnosis(
        reason: str,
        return_phase: str,
        *,
        trigger_stage: str,
        trigger_text: str = "",
        trigger_path: str | None = None,
    ) -> None:
        state["effective_task_class"] = "RED"
        state["diagnosis_reason"] = reason
        state["diagnosis_return_phase"] = return_phase
        state["diagnosis_trigger_stage"] = trigger_stage
        state["diagnosis_trigger_path"] = trigger_path
        state["diagnosis_trigger_signature"] = (
            diagnosis_trigger_signature(trigger_text) if trigger_text else None
        )
        clear_diagnosis_binding()

    def promote_to_red(reason: str, return_phase: str) -> None:
        schedule_diagnosis(
            reason,
            return_phase,
            trigger_stage=return_phase,
        )

    def diagnosis_prompt_metadata() -> dict[str, Any]:
        return {
            "diagnosis_path": state.get("diagnosis_path"),
            "diagnosis_reason": state.get("diagnosis_reason"),
            "diagnosis_binding_source": state.get("diagnosis_binding_source"),
            "diagnosis_sequence": state.get("diagnosis_sequence"),
        }

    while True:
        transition_checkpoint(
            ctx,
            state,
            phase=phase,
            status="RUNNING" if not is_resumed_stage(phase) else "RESUMING",
            commits=commits,
        )

        if phase in {"diagnosis", "diagnosis_escalated"}:
            role = phase
            config = resolve_model_config(policy, effective_class(), role)
            diagnosis = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role=role,
                    resume=is_resumed_stage(phase),
                    resume_from_stage=phase if is_resumed_stage(phase) else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage(phase) else None,
                    resume_reason=resume_reason if is_resumed_stage(phase) else None,
                    diagnosis_path=state.get("diagnosis_path") if phase == "diagnosis_escalated" else None,
                    diagnosis_reason=str(state.get("diagnosis_reason") or "task_classification"),
                    diagnosis_binding_source=(
                        state.get("diagnosis_binding_source") if phase == "diagnosis_escalated" else None
                    ),
                    diagnosis_sequence=(state.get("diagnosis_sequence") if phase == "diagnosis_escalated" else None),
                ),
                repo,
                config,
                ctx=ctx,
                task_id=task_id,
                role=role,
            )
            require_result(
                diagnosis,
                task_id=task_id,
                stage="diagnosis",
                allowed={"RESOLVED", "UNRESOLVED"},
            )
            events.append(stage_event(diagnosis, config, role=role))
            if not workflow_is_complete(diagnosis):
                transition_checkpoint(
                    ctx,
                    state,
                    phase=phase,
                    status="BLOCKED",
                    last_error="Diagnosis workflow bookkeeping incomplete.",
                )
                return {
                    "task_id": task_id,
                    "status": "DIAGNOSIS_WORKFLOW_INCOMPLETE",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }

            record = latest_stage_record(ctx, task_id, role)
            if record and record.final_path:
                state["diagnosis_path"] = record.final_path
                state["diagnosis_sequence"] = None
                state["diagnosis_binding_source"] = "worker_output"
                state["diagnosis_bound_at"] = iso_now()

            if diagnosis.status == "RESOLVED":
                return_phase = str(state.get("diagnosis_return_phase") or "implementation")
                if return_phase == "fix" and int(state.get("fix_cycles_used") or 0) >= max_fix_cycles:
                    transition_checkpoint(
                        ctx,
                        state,
                        phase="fix",
                        status="DIAGNOSIS_RESOLVED_FIX_BUDGET_EXHAUSTED",
                        last_error="Diagnosis resolved the new blocker, but no Fix cycle remains.",
                        commits=commits,
                    )
                    return {
                        "task_id": task_id,
                        "status": "DIAGNOSIS_RESOLVED_FIX_BUDGET_EXHAUSTED",
                        "task_assessment": state["task_assessment"],
                        "effective_task_class": effective_class(),
                        "diagnosis_path": state.get("diagnosis_path"),
                        "commits": commits,
                        "events": events,
                    }
                phase = return_phase
                resuming = False
                continue

            class_cfg = policy.task_classes[effective_class()]
            if phase == "diagnosis" and class_cfg.allow_high_escalation:
                phase = "diagnosis_escalated"
                resuming = False
                continue

            transition_checkpoint(
                ctx,
                state,
                phase=phase,
                status="ESCALATION_REQUIRED",
                last_error="Diagnosis could not prove a safe implementation/fix path.",
            )
            return {
                "task_id": task_id,
                "status": "ESCALATION_REQUIRED",
                "task_assessment": state["task_assessment"],
                "effective_task_class": effective_class(),
                "diagnosis_path": state.get("diagnosis_path"),
                "commits": commits,
                "events": events,
            }

        if phase == "implementation":
            config = resolve_model_config(policy, effective_class(), "implementation")
            internal_resume = bool(state.get("implementation_resume_after_diagnosis"))
            implementation = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="implementation",
                    resume=is_resumed_stage("implementation") or internal_resume,
                    resume_from_stage="implementation"
                    if is_resumed_stage("implementation") or internal_resume
                    else None,
                    previous_run_dir=(
                        resume_source_dir
                        if is_resumed_stage("implementation")
                        else (str(ctx.run_dir) if internal_resume else None)
                    ),
                    resume_reason=(
                        resume_reason
                        if is_resumed_stage("implementation")
                        else (str(state.get("diagnosis_reason") or "diagnosis_resolved") if internal_resume else None)
                    ),
                    **diagnosis_prompt_metadata(),
                ),
                repo,
                config,
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
            events.append(stage_event(implementation, config, role="implementation"))
            if not workflow_is_complete(implementation):
                record_technical_stop(ctx, task_id, "implementation", "Implementation workflow bookkeeping incomplete.")
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
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }
            if implementation.status != "COMPLETE":
                if effective_class() != "RED" and not bool(state.get("implementation_escalated")):
                    state["implementation_escalated"] = True
                    state["implementation_resume_after_diagnosis"] = True
                    promote_to_red("implementation_incomplete", "implementation")
                    phase = "diagnosis"
                    resuming = False
                    ctx.progress("ESCALATE", f"{task_id} implementation incomplete → RED diagnosis")
                    continue
                record_technical_stop(ctx, task_id, "implementation", "Implementation technical result is INCOMPLETE/BLOCKED.")
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
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }
            state["implementation_resume_after_diagnosis"] = False
            state["review_return_phase"] = "review"
            phase = phase_after_implementation(staged=staged)
            resuming = False
            continue

        if phase == "gate_resolution":
            if contract is None:
                raise OrchestratorError("gate_resolution requires staged_integration_v1 contract.")
            gate_state = state["gate_state"]
            index = int(gate_state.get("current_gate_index") or 0)
            if index >= len(contract.gates):
                phase = "finalization"
                resuming = False
                continue
            gate = contract.gates[index]
            gate_id = str(gate["id"])
            gate_state["gate_resolution_cycles"] = int(gate_state.get("gate_resolution_cycles") or 0) + 1
            state["aggregate"]["gate_resolution_cycles"] = int(state["aggregate"].get("gate_resolution_cycles") or 0) + 1
            passed, gate_record, blocker = run_gate_command(repo, gate)
            events.append({
                "task_id": task_id,
                "stage": "gate_resolution",
                "gate_id": gate_id,
                "status": "PASS" if passed else "FAIL",
                "record": gate_record,
                "blocker": blocker,
                "workflow_complete": True,
            })
            if passed:
                mark_gate_pass(gate_state, gate_id, {
                    "head": gate_record["head"],
                    "result_sha256": gate_record["result_sha256"],
                    "recorded_at": gate_record["recorded_at"],
                    "attempt_id": gate_state.get("attempt_id"),
                })
                continue
            assert blocker is not None
            action = register_gate_failure(gate_state, blocker)
            if action == "STOP":
                transition_checkpoint(
                    ctx, state, phase="gate_resolution", status="GATE_BLOCKED",
                    last_error=f"{gate_id} blocked by {blocker['classification']}", commits=commits,
                )
                return {
                    "task_id": task_id, "status": "GATE_BLOCKED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(), "gate_id": gate_id,
                    "blocker": blocker, "commits": commits, "events": events,
                }
            if action == "ARCHITECTURE_REVIEW_REQUIRED":
                transition_checkpoint(
                    ctx, state, phase="gate_resolution", status="ARCHITECTURE_REVIEW_REQUIRED",
                    last_error=f"{gate_id} same invariant survived bounded fixes", commits=commits,
                )
                return {
                    "task_id": task_id, "status": "ARCHITECTURE_REVIEW_REQUIRED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(), "gate_id": gate_id,
                    "blocker": blocker, "commits": commits, "events": events,
                }
            config = resolve_model_config(policy, effective_class(), "fix")
            gate_fix = run_stage(
                gate_fix_child_prompt(task_id, gate, blocker), repo, config,
                ctx=ctx, task_id=task_id, role="gate_fix",
            )
            require_result(
                gate_fix, task_id=task_id, stage="gate_fix",
                allowed={"READY_FOR_GATE_RERUN", "NOT_READY_FOR_GATE_RERUN"},
            )
            events.append(stage_event(gate_fix, config, role="gate_fix"))
            if not workflow_is_complete(gate_fix) or gate_fix.status != "READY_FOR_GATE_RERUN":
                transition_checkpoint(
                    ctx, state, phase="gate_resolution", status="GATE_FIX_NOT_READY",
                    last_error=f"Bounded gate fix for {gate_id} was not ready for rerun.", commits=commits,
                )
                return {
                    "task_id": task_id, "status": "GATE_FIX_NOT_READY",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(), "gate_id": gate_id,
                    "blocker": blocker, "commits": commits, "events": events,
                }
            begin_new_gate_attempt(gate_state)
            resuming = False
            continue

        if phase == "finalization":
            if contract is None:
                raise OrchestratorError("finalization requires staged_integration_v1 contract.")
            try:
                source_commit, source_hashes = commit_source_finalization(
                    repo, task_id=task_id, source_paths=contract.source_paths,
                    finalization_paths=contract.finalization_paths, ctx=ctx,
                    protected_paths=contract.protected_paths,
                    protected_snapshot=state.get("protected_artifacts") or {},
                )
            except OrchestratorError as exc:
                transition_checkpoint(
                    ctx, state, phase="finalization", status="IMMUTABLE_FINALIZATION_FAILED",
                    last_error=str(exc), commits=commits,
                )
                return {
                    "task_id": task_id, "status": "IMMUTABLE_FINALIZATION_FAILED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "error": str(exc), "commits": commits, "events": events,
                }
            state["finalization"]["source_commit"] = source_commit
            state["finalization"]["source_hashes"] = source_hashes
            canonical_record = run_exact_argv(repo, contract.canonical_command)
            events.append({
                "task_id": task_id, "stage": "canonical_finalization",
                "status": "PASS" if canonical_record["exit_code"] == 0 else "FAIL",
                "record": canonical_record, "workflow_complete": True,
            })
            if canonical_record["exit_code"] != 0:
                transition_checkpoint(
                    ctx, state, phase="finalization", status="CANONICAL_RUN_FAILED",
                    last_error="Canonical finalization command failed.", commits=commits,
                )
                return {
                    "task_id": task_id, "status": "CANONICAL_RUN_FAILED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "canonical_record": canonical_record, "commits": commits, "events": events,
                }
            canonical_dirty = changed_paths(repo)
            canonical_outside = [
                path for path in canonical_dirty
                if not _path_within_scopes(path, contract.canonical_evidence_paths)
            ]
            if canonical_outside:
                error = (
                    "IMMUTABLE_FINALIZATION_FAILED: canonical command changed paths outside evidence scope: "
                    + ", ".join(canonical_outside)
                )
                transition_checkpoint(
                    ctx, state, phase="finalization", status="IMMUTABLE_FINALIZATION_FAILED",
                    last_error=error, commits=commits,
                )
                return {
                    "task_id": task_id, "status": "IMMUTABLE_FINALIZATION_FAILED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "error": error, "commits": commits, "events": events,
                }
            try:
                binding = verify_canonical_evidence_bindings(
                    repo, source_commit, contract.canonical_evidence_paths,
                )
            except OrchestratorError as exc:
                transition_checkpoint(
                    ctx, state, phase="finalization", status="IMMUTABLE_FINALIZATION_FAILED",
                    last_error=str(exc), commits=commits,
                )
                return {
                    "task_id": task_id, "status": "IMMUTABLE_FINALIZATION_FAILED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "error": str(exc), "commits": commits, "events": events,
                }
            state["finalization"]["canonical_results"] = [canonical_record]
            state["finalization"]["binding"] = binding
            state["finalization"]["binding_verified"] = True
            phase = "literal_validation"
            resuming = False
            continue

        if phase == "literal_validation":
            if contract is None:
                raise OrchestratorError("literal_validation requires staged_integration_v1 contract.")
            if not bool(state.get("finalization", {}).get("binding_verified")):
                transition_checkpoint(
                    ctx, state, phase="literal_validation", status="LITERAL_VALIDATION_BLOCKED",
                    last_error="Immutable source finalization binding is not verified.", commits=commits,
                )
                return {
                    "task_id": task_id, "status": "LITERAL_VALIDATION_BLOCKED",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(), "commits": commits, "events": events,
                }
            validation_results: list[dict[str, Any]] = []
            for argv in contract.literal_validation:
                result = run_literal_validation(repo, argv)
                validation_results.append(result)
                events.append({
                    "task_id": task_id, "stage": "literal_validation",
                    "status": "PASS" if result["exit_code"] == 0 else "FAIL",
                    "result": result, "workflow_complete": True,
                })
                if result["exit_code"] != 0:
                    state["literal_validation"]["results"] = validation_results
                    transition_checkpoint(
                        ctx, state, phase="literal_validation", status="LITERAL_VALIDATION_FAILED",
                        last_error="Literal validation command failed.", commits=commits,
                    )
                    return {
                        "task_id": task_id, "status": "LITERAL_VALIDATION_FAILED",
                        "task_assessment": state["task_assessment"],
                        "effective_task_class": effective_class(),
                        "literal_validation": validation_results, "commits": commits, "events": events,
                    }
            state["literal_validation"]["results"] = validation_results
            assert_finalization_authority_unchanged(
                repo,
                finalization=state.get("finalization") or {},
                source_paths=contract.source_paths,
                evidence_paths=contract.canonical_evidence_paths,
                literal_results=validation_results,
            )
            return_phase = str(state.get("review_return_phase") or "review")
            if return_phase not in {"review", "rereview"}:
                raise OrchestratorError(f"Invalid staged review_return_phase: {return_phase}")
            phase = return_phase
            resuming = False
            continue

        if phase == "review":
            config = resolve_model_config(policy, effective_class(), "review")
            review = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="review",
                    resume=is_resumed_stage("review"),
                    resume_from_stage="review" if is_resumed_stage("review") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("review") else None,
                    resume_reason=resume_reason if is_resumed_stage("review") else None,
                    **diagnosis_prompt_metadata(),
                ),
                repo,
                config,
                ctx=ctx,
                task_id=task_id,
                role="review",
            )
            require_result(review, task_id=task_id, stage="review", allowed={"ACCEPT", "REJECT"})
            events.append(stage_event(review, config, role="review"))
            if not workflow_is_complete(review):
                record_technical_stop(ctx, task_id, "review", "Review workflow bookkeeping incomplete.")
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
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }
            review_text = latest_stage_final_text(ctx, task_id, "review")
            review_record = latest_stage_record(ctx, task_id, "review")
            state["review_status"] = review.status
            state["review_requires_diagnosis"] = (
                review.status == "REJECT" and text_requires_diagnosis(review_text)
            )
            state["review_trigger_signature"] = (
                diagnosis_trigger_signature(review_text) if review.status == "REJECT" else None
            )
            state["review_final_path"] = review_record.final_path if review_record else None
            phase = "commit_implementation_review"
            resuming = False
            continue

        if phase == "commit_implementation_review":
            if contract is not None:
                assert_finalization_authority_unchanged(
                    repo, finalization=state.get("finalization") or {},
                    source_paths=contract.source_paths,
                    evidence_paths=contract.canonical_evidence_paths,
                    literal_results=state.get("literal_validation", {}).get("results") or [],
                )
            review_status = state.get("review_status")
            if review_status not in {"ACCEPT", "REJECT"}:
                raise OrchestratorError("Cannot resume implementation-review commit without review_status.")
            first_commit = commit_all_changes(
                repo,
                task_id=task_id,
                boundary="implementation-review",
                review_status=str(review_status),
                ctx=ctx,
                protected_paths=(contract.protected_paths if contract else ()),
                protected_snapshot=state.get("protected_artifacts") or {},
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
                    transition_checkpoint(ctx, state, phase="fix", status="REJECTED_NO_FIX", commits=commits)
                    return {
                        "task_id": task_id,
                        "status": "REJECTED_NO_FIX",
                        "task_assessment": state["task_assessment"],
                        "effective_task_class": effective_class(),
                        "commits": commits,
                        "events": events,
                    }
                review_path = state.get("review_final_path")
                review_text = (
                    Path(str(review_path)).read_text(encoding="utf-8", errors="replace")
                    if review_path and Path(str(review_path)).is_file()
                    else ""
                )
                next_phase = review_reject_next_phase(effective_class(), review_text)
                if next_phase == "diagnosis":
                    schedule_diagnosis(
                        "review_reject_requires_formal_diagnosis",
                        "fix",
                        trigger_stage="review",
                        trigger_text=review_text,
                        trigger_path=review_path,
                    )
                phase = next_phase

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
                transition_checkpoint(ctx, state, phase="fix", status="REJECTED_AFTER_REVIEW", commits=commits)
                return {
                    "task_id": task_id,
                    "status": "REJECTED_AFTER_REVIEW",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }

            config = resolve_model_config(policy, effective_class(), "fix")
            internal_resume = bool(state.get("fix_resume_after_diagnosis"))
            fix = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="fix",
                    resume=is_resumed_stage("fix") or internal_resume,
                    resume_from_stage="fix" if is_resumed_stage("fix") or internal_resume else None,
                    previous_run_dir=(
                        resume_source_dir if is_resumed_stage("fix") else (str(ctx.run_dir) if internal_resume else None)
                    ),
                    resume_reason=(
                        resume_reason if is_resumed_stage("fix") else (str(state.get("diagnosis_reason") or "diagnosis_resolved") if internal_resume else None)
                    ),
                    **diagnosis_prompt_metadata(),
                ),
                repo,
                config,
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
            events.append(stage_event(fix, config, role="fix"))
            if not workflow_is_complete(fix):
                record_technical_stop(ctx, task_id, "fix", "Fix workflow bookkeeping incomplete.")
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
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }
            if fix.status != "READY_FOR_RE_REVIEW":
                fix_text = latest_stage_final_text(ctx, task_id, "fix")
                fix_record = latest_stage_record(ctx, task_id, "fix")
                if bool(state.get("fix_resume_after_diagnosis")) and state.get("diagnosis_trigger_stage") == "fix":
                    next_phase = "stop"
                else:
                    next_phase = fix_not_ready_next_phase(
                        effective_class(),
                        fix_text,
                        diagnosed_trigger_signature=state.get("diagnosis_trigger_signature"),
                    )
                if next_phase == "diagnosis":
                    state["fix_resume_after_diagnosis"] = True
                    schedule_diagnosis(
                        "fix_not_ready_requires_formal_diagnosis",
                        "fix",
                        trigger_stage="fix",
                        trigger_text=fix_text,
                        trigger_path=fix_record.final_path if fix_record else None,
                    )
                    phase = "diagnosis"
                    resuming = False
                    ctx.progress("ESCALATE", f"{task_id} fix not ready → RED diagnosis")
                    continue
                record_technical_stop(ctx, task_id, "fix", "Fix is NOT_READY_FOR_RE_REVIEW.")
                transition_checkpoint(ctx, state, phase="fix", status="BLOCKED", last_error="Fix is NOT_READY_FOR_RE_REVIEW.")
                return {
                    "task_id": task_id,
                    "status": "FIX_NOT_READY",
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }

            state["fix_resume_after_diagnosis"] = False
            state["fix_cycles_used"] = used + 1
            if staged:
                invalidate_staged_proof(state)
            state["review_return_phase"] = "rereview"
            phase = phase_after_review_fix(staged=staged)
            resuming = False
            continue

        if phase == "rereview":
            config = resolve_model_config(policy, effective_class(), "rereview")
            rereview = run_stage(
                child_prompt(
                    task_id=task_id,
                    worker_role="rereview",
                    resume=is_resumed_stage("rereview"),
                    resume_from_stage="rereview" if is_resumed_stage("rereview") else None,
                    previous_run_dir=resume_source_dir if is_resumed_stage("rereview") else None,
                    resume_reason=resume_reason if is_resumed_stage("rereview") else None,
                    **diagnosis_prompt_metadata(),
                ),
                repo,
                config,
                ctx=ctx,
                task_id=task_id,
                role="rereview",
            )
            require_result(rereview, task_id=task_id, stage="review", allowed={"ACCEPT", "REJECT"})
            events.append(stage_event(rereview, config, role="rereview"))
            if not workflow_is_complete(rereview):
                record_technical_stop(ctx, task_id, "rereview", "Re-review workflow bookkeeping incomplete.")
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
                    "task_assessment": state["task_assessment"],
                    "effective_task_class": effective_class(),
                    "commits": commits,
                    "events": events,
                }
            rereview_text = latest_stage_final_text(ctx, task_id, "rereview")
            rereview_record = latest_stage_record(ctx, task_id, "rereview")
            state["review_status"] = rereview.status
            state["rereview_requires_diagnosis"] = (
                rereview.status == "REJECT" and text_requires_diagnosis(rereview_text)
            )
            state["rereview_trigger_signature"] = (
                diagnosis_trigger_signature(rereview_text) if rereview.status == "REJECT" else None
            )
            state["rereview_final_path"] = rereview_record.final_path if rereview_record else None
            phase = "commit_fix_rereview"
            resuming = False
            continue

        if phase == "commit_fix_rereview":
            if contract is not None:
                assert_finalization_authority_unchanged(
                    repo, finalization=state.get("finalization") or {},
                    source_paths=contract.source_paths,
                    evidence_paths=contract.canonical_evidence_paths,
                    literal_results=state.get("literal_validation", {}).get("results") or [],
                )
            review_status = state.get("review_status")
            if review_status not in {"ACCEPT", "REJECT"}:
                raise OrchestratorError("Cannot resume fix-rereview commit without review_status.")
            fix_commit = commit_all_changes(
                repo,
                task_id=task_id,
                boundary="fix-rereview",
                review_status=str(review_status),
                ctx=ctx,
                protected_paths=(contract.protected_paths if contract else ()),
                protected_snapshot=state.get("protected_artifacts") or {},
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
                budget_available = int(state.get("fix_cycles_used") or 0) < max_fix_cycles
                rereview_path = state.get("rereview_final_path")
                rereview_text = (
                    Path(str(rereview_path)).read_text(encoding="utf-8", errors="replace")
                    if rereview_path and Path(str(rereview_path)).is_file()
                    else ""
                )
                next_phase = rereview_reject_next_phase(
                    effective_class(),
                    rereview_text,
                    fix_budget_available=budget_available,
                )
                if next_phase == "diagnosis":
                    schedule_diagnosis(
                        "rereview_reject_requires_formal_diagnosis",
                        "fix",
                        trigger_stage="rereview",
                        trigger_text=rereview_text,
                        trigger_path=rereview_path,
                    )
                    phase = "diagnosis"
                elif next_phase == "fix":
                    phase = "fix"
                else:
                    transition_checkpoint(ctx, state, phase="fix", status="REJECTED_AFTER_REVIEW", commits=commits)
                    return {
                        "task_id": task_id,
                        "status": "REJECTED_AFTER_REVIEW",
                        "task_assessment": state["task_assessment"],
                        "effective_task_class": effective_class(),
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
            acceptance_path = write_deterministic_acceptance(
                repo,
                task_id=task_id,
                accepted_commit=str(accepted_commit),
            )
            ctx.progress("PASS", f"{task_id} ACCEPTANCE — deterministic record created")
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
                raise OrchestratorError("Cannot commit acceptance without acceptance_path.")
            acceptance_commit = commit_all_changes(
                repo, task_id=task_id, boundary="acceptance", ctx=ctx,
                protected_paths=(contract.protected_paths if contract else ()),
                protected_snapshot=state.get("protected_artifacts") or {},
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
                "task_assessment": state["task_assessment"],
                "effective_task_class": effective_class(),
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
    policy: ModelPolicy,
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
    if status in {"ESCALATION_REQUIRED", "DIAGNOSIS_WORKFLOW_INCOMPLETE"}:
        return "RESOLVE_DIAGNOSIS_BEFORE_IMPLEMENTATION", [
            "Inspect the bounded Diagnosis final response and evidence.",
            "Do not continue implementation speculatively while the authoritative contract/root cause is unresolved.",
            "Resolve the missing evidence or contract, then resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status in {"INCOMPLETE", "IMPLEMENTATION_WORKFLOW_INCOMPLETE"}:
        return "RESOLVE_IMPLEMENTATION_BLOCKER_THEN_RESUME", [
            "Inspect the failing Implementation final response and full log listed below.",
            "Resolve the implementation/environment blocker without discarding target-task work.",
            "Then resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "GATE_BLOCKED":
        return "RESOLVE_GATE_BLOCKER", [
            "Inspect the current gate blocker classification and first failing invariant.",
            "Do not advance to a later gate; resolve the external/contract blocker or revise the task contract explicitly.",
            "Resume the checkpointed gate with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "ARCHITECTURE_REVIEW_REQUIRED":
        return "REVIEW_GATE_ARCHITECTURE", [
            "The same normalized gate invariant survived the bounded correction budget.",
            "Review architecture/contract/scope before authorizing another correction.",
        ]
    if status == "GATE_FIX_NOT_READY":
        return "RESOLVE_GATE_FIX_BLOCKER", [
            "Inspect the bounded gate-fix final response and the current gate blocker.",
            "Keep the current gate cursor and existing passed-gate baselines; do not advance manually.",
            "Resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "IMMUTABLE_FINALIZATION_FAILED":
        return "REPAIR_IMMUTABLE_FINALIZATION", [
            "Inspect source scope, protected-artifact state, and canonical Evidence source binding.",
            "Do not start Review until source_commit and Evidence binding are reproducible from Git objects.",
            "Resume with: scripts/codex/resume-task <TASK_ID>",
        ]
    if status == "CANONICAL_RUN_FAILED":
        return "REPAIR_CANONICAL_RUN", [
            "Inspect the exact canonical command result and preserve the immutable source_commit.",
            "Correct only the bounded canonical-run blocker, then resume finalization.",
        ]
    if status in {"LITERAL_VALIDATION_FAILED", "LITERAL_VALIDATION_BLOCKED"}:
        return "REPAIR_LITERAL_VALIDATION", [
            "Inspect the exact literal validation command, resolved executable/interpreter, exit code, and Git SHA.",
            "Do not claim review readiness until the literal command itself passes.",
            "Resume with: scripts/codex/resume-task <TASK_ID>",
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
    if status == "DIAGNOSIS_RESOLVED_FIX_BUDGET_EXHAUSTED":
        return "AUTHORIZE_ADDITIONAL_FIX_CYCLE_OR_STOP", [
            "The new Review/Re-review blocker was formally diagnosed and resolved.",
            "No Fix cycle remains under the current --max-fix-cycles budget.",
            "If another Fix is authorized, resume with a larger --max-fix-cycles value and --from-stage fix.",
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
    if "INTERRUPTED" in kinds:
        return "RESUME_INTERRUPTED_STAGE", [
            "The host received Ctrl+C while a child Codex stage was running.",
            "The child process group was stopped and the TASK checkpoint/worktree were preserved.",
            "Resume with: scripts/codex/resume-task <TASK_ID>",
        ]
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
    reported_stages = [r for r in ctx.stage_records if r.tokens_reported is not None]
    token_summary = {
        "total_reported_tokens": sum(int(r.tokens_reported or 0) for r in reported_stages),
        "sol_reported_tokens": sum(
            int(r.tokens_reported or 0) for r in reported_stages if "sol" in r.model.lower()
        ),
        "terra_reported_tokens": sum(
            int(r.tokens_reported or 0) for r in reported_stages if "terra" in r.model.lower()
        ),
        "codex_calls": len(ctx.stage_records),
        "deterministic_acceptance_calls_saved": 1
        if result.get("status") in {"ACCEPTED", "COMPLETE"}
        or result.get("acceptance_path")
        else 0,
    }
    report = {
        "schema_version": 2,
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
        "token_summary": token_summary,
        "task_lifetime_summary": None,
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
                resume_state = upgrade_checkpoint_state(
                    resume_state, staged=bool(resume_state.get("qualification_profile"))
                )
                if merge_run_stage_metrics(resume_state, ctx.stage_records, run_id=str(ctx.run_dir)):
                    _atomic_write_json(checkpoint, resume_state)
                report["task_lifetime_summary"] = dict(resume_state.get("aggregate") or {})
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
    assessment_view = result.get("task_assessment")
    if isinstance(assessment_view, dict):
        lines.append(
            f"- TASK class: `{assessment_view.get('task_class')}` "
            f"(effective: `{result.get('effective_task_class', assessment_view.get('task_class'))}`, "
            f"score: `{assessment_view.get('score')}`)"
        )
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

    lines += [
        "",
        "## Token Summary",
        "",
        f"- Reported total: `{token_summary['total_reported_tokens']:,}`",
        f"- Sol: `{token_summary['sol_reported_tokens']:,}`",
        f"- Terra: `{token_summary['terra_reported_tokens']:,}`",
        f"- Codex child calls: `{token_summary['codex_calls']}`",
        f"- Deterministic acceptance calls saved: `{token_summary['deterministic_acceptance_calls_saved']}`",
        "",
        "## Task Lifetime Summary",
        "",
    ]
    lifetime = report.get("task_lifetime_summary")
    if isinstance(lifetime, dict):
        for key in (
            "orchestrator_runs", "codex_calls", "reported_tokens_total", "diagnosis_calls",
            "gate_fix_calls", "review_fix_calls", "review_calls", "gate_resolution_cycles",
        ):
            lines.append(f"- {key}: `{int(lifetime.get(key) or 0):,}`")
    else:
        lines.append("Not available.")
    lines += [
        "",
        "## Errors",
        "",
    ]
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
    parser.add_argument("--heartbeat-seconds", type=int, default=30, metavar="N", help="Print a quiet WAIT heartbeat every N seconds; 0 disables. Default: 30.")

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
            "diagnosis",
            "diagnosis_escalated",
            "implementation",
            "gate_resolution",
            "finalization",
            "literal_validation",
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
        result["model_policy"] = policy_summary(policy)
    except ChildInterruptedError as exc:
        mark_checkpoint_interrupted(
            args.report_dir,
            repo,
            exc.task_id,
            error_type="INTERRUPTED",
            error_message=str(exc),
        )
        result = {
            "status": "ERROR",
            "error_type": "INTERRUPTED",
            "error": str(exc),
            "task_id": exc.task_id,
            "failed_stage": exc.role,
        }
    except ChildProtocolError as exc:
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
    except KeyboardInterrupt:
        active_task = (
            ctx.stage_records[-1].task_id
            if ctx.stage_records
            else (args.task_id if args.command in {"task", "resume"} else target)
        )
        if active_task and TASK_RE.fullmatch(str(active_task)):
            mark_checkpoint_interrupted(
                args.report_dir,
                repo,
                str(active_task),
                error_type="INTERRUPTED",
                error_message="Host orchestration interrupted by Ctrl+C.",
            )
        ctx.add_error(
            kind="INTERRUPTED",
            stage="orchestrator",
            task_id=str(active_task),
            message="Host orchestration interrupted by Ctrl+C.",
        )
        result = {
            "status": "ERROR",
            "error_type": "INTERRUPTED",
            "error": "Host orchestration interrupted by Ctrl+C.",
            "task_id": str(active_task),
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
