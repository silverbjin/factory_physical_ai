#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

SCENARIO_NAV_TIMEOUT = "SIM009-NAV-TIMEOUT-RETRY"
SCENARIO_VERIFY_UNCERTAIN = "SIM009-VERIFY-UNCERTAIN"


def repo_root() -> Path:
    env = os.environ.get("REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    cp = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise SystemExit("Repository root not found. Set REPO_ROOT.")
    return Path(cp.stdout.strip()).resolve()


def state_path(root: Path) -> Path:
    p = root / "results/demo/3d_demo_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_state(root: Path, **kw):
    payload = {"updated_at": time.time(), **kw}
    state_path(root).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run_help(script: Path) -> str:
    cp = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
    )
    return (cp.stdout or "") + "\n" + (cp.stderr or "")


def has_flag(script: Path, *flags: str) -> str | None:
    help_text = run_help(script)
    for flag in flags:
        if flag in help_text:
            return flag
    return None


def normal_runner(root: Path) -> Path:
    override = os.environ.get("DEMO_NORMAL_RUNNER")
    if override:
        p = root / override
        if not p.is_file():
            raise SystemExit(f"DEMO_NORMAL_RUNNER missing: {p}")
        return p

    candidates = [
        root / "scripts/run_simulation_normal_system_e2e.py",
        root / "scripts/run_simulation_normal_e2e.py",
    ]
    found = [p for p in candidates if p.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("Normal E2E runner not found.")
    raise SystemExit(
        "Multiple normal runners found. "
        "Set DEMO_NORMAL_RUNNER to the acceptance-bound runner."
    )


def failure_runner(root: Path) -> Path:
    override = os.environ.get("DEMO_FAILURE_RUNNER")
    if override:
        p = root / override
        if not p.is_file():
            raise SystemExit(f"DEMO_FAILURE_RUNNER missing: {p}")
        return p

    # Current repositories may use either historical name.
    candidates = [
        root / "scripts/run_simulation_failure_recovery.py",
        root / "scripts/run_simulation_failure_suite.py",
    ]
    found = [p for p in candidates if p.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit(
            "Simulation failure runner not found. Expected one of: "
            "scripts/run_simulation_failure_recovery.py, "
            "scripts/run_simulation_failure_suite.py"
        )
    raise SystemExit(
        "Multiple failure runners found. "
        "Set DEMO_FAILURE_RUNNER to the acceptance-bound runner."
    )


def qualifier(root: Path) -> Path:
    p = root / "scripts/verify_simulation_e2e_qualification.py"
    if not p.is_file():
        raise SystemExit("Qualification verifier not found.")
    return p


def accepted_sim008(root: Path) -> Path:
    override = os.environ.get("DEMO_SIM008_EVIDENCE")
    if override:
        p = root / override
        if not p.is_file():
            raise SystemExit(f"DEMO_SIM008_EVIDENCE missing: {p}")
        return p

    candidates = [
        root / "results/simulation/SIM-008_normal_system_e2e.json",
        root / "results/simulation/SIM-008_normal_e2e.json",
    ]
    found = [p for p in candidates if p.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("SIM-008 accepted Evidence not found.")
    raise SystemExit(
        "Multiple SIM-008 Evidence variants found. "
        "Set DEMO_SIM008_EVIDENCE."
    )


def accepted_sim009(root: Path) -> Path:
    p = root / "results/simulation/SIM-009_failure_recovery.json"
    if not p.is_file():
        raise SystemExit("SIM-009 accepted Evidence not found.")
    return p


def find_strings(node, key_hint=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from find_strings(value, str(key))
    elif isinstance(node, list):
        for value in node:
            yield from find_strings(value, key_hint)
    elif isinstance(node, str):
        yield key_hint, node


def resolve_world(root: Path) -> Path | None:
    override = os.environ.get("DEMO_WORLD")
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = root / p
        return p.resolve() if p.exists() else None

    try:
        data = json.loads(
            accepted_sim008(root).read_text(encoding="utf-8")
        )
    except Exception:
        return None

    scored = []
    for key, value in find_strings(data):
        low = value.lower()
        if not (low.endswith(".sdf") or low.endswith(".world")):
            continue
        p = Path(value)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            continue
        score = 0
        kl = key.lower()
        if "world" in kl:
            score += 5
        if "model" in kl:
            score -= 2
        if "scene" in kl:
            score += 1
        scored.append((score, p.resolve()))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], len(str(item[1]))))
    best_score = scored[0][0]
    best = []
    seen = set()
    for score, p in scored:
        if score != best_score:
            continue
        if str(p) not in seen:
            best.append(p)
            seen.add(str(p))
    return best[0] if len(best) == 1 else None


def gazebo_cli():
    if shutil.which("gz"):
        cp = subprocess.run(
            ["gz", "sim", "--help"],
            capture_output=True,
            text=True,
        )
        if cp.returncode == 0:
            return ["gz", "sim"]

    if shutil.which("ign"):
        cp = subprocess.run(
            ["ign", "gazebo", "--help"],
            capture_output=True,
            text=True,
        )
        if cp.returncode == 0:
            return ["ign", "gazebo"]

    return None


def _read_proc_cmdline(pid: int) -> list[str] | None:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return [
            part.decode(errors="replace")
            for part in raw.split(b"\0")
            if part
        ]
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None


def _read_proc_environ(pid: int) -> dict[str, str] | None:
    """
    Capture the process environment immediately.

    A short-lived Gazebo server may disappear between PID discovery and a
    later /proc read, so discovery calls this in the same polling iteration.
    """
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None

    env = {}
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        env[key.decode(errors="replace")] = value.decode(errors="replace")
    return env



def _read_proc_ppid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            if line.startswith("PPid:"):
                return int(line.split(":", 1)[1].strip())
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
        return None
    return None


def process_is_descendant(
    pid: int,
    ancestor_pid: int,
    max_depth: int = 32,
) -> bool:
    current = pid
    seen = set()

    for _ in range(max_depth):
        if current == ancestor_pid:
            return True
        if current in seen or current <= 1:
            return False
        seen.add(current)

        parent = _read_proc_ppid(current)
        if parent is None:
            return False
        current = parent

    return False


def gazebo_gui_snapshots() -> dict[int, dict]:
    snapshots = {}
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        tokens = _read_proc_cmdline(pid)
        if not tokens:
            continue

        joined = " ".join(tokens)
        looks_like_gz = (
            ("gz sim" in joined)
            or ("ign gazebo" in joined)
        )
        if not looks_like_gz or "-g" not in tokens:
            continue

        env = _read_proc_environ(pid)
        if env is None:
            continue

        snapshots[pid] = {
            "pid": pid,
            "cmdline": tokens,
            "env": env,
        }
    return snapshots


def transport_identity(env: dict[str, str]) -> dict[str, str | None]:
    return {
        "GZ_PARTITION": env.get("GZ_PARTITION"),
        "IGN_PARTITION": env.get("IGN_PARTITION"),
        "ROS_DOMAIN_ID": env.get("ROS_DOMAIN_ID"),
    }


def normalized_transport_identity(
    env: dict[str, str],
) -> dict[str, str | None]:
    gz = env.get("GZ_PARTITION")
    ign = env.get("IGN_PARTITION") or gz
    return {
        "GZ_PARTITION": gz,
        "IGN_PARTITION": ign,
        "ROS_DOMAIN_ID": env.get("ROS_DOMAIN_ID"),
    }


def transport_matches(
    server_env: dict[str, str],
    gui_env: dict[str, str],
) -> bool:
    return (
        normalized_transport_identity(server_env)
        == normalized_transport_identity(gui_env)
    )

def _is_gazebo_server(tokens: list[str] | None) -> bool:
    if not tokens:
        return False
    joined = " ".join(tokens)

    looks_like_gz = ("gz sim" in joined) or ("ign gazebo" in joined)
    if not looks_like_gz:
        return False

    # Canonical runners observed in this project use e.g.
    #   gz sim -r -s /tmp/nav2_xxx.sdf
    # Do not classify GUI-only `gz sim -g` as a server.
    has_server_flag = (
        "-s" in tokens
        or "--server-only" in tokens
        or "--server" in tokens
    )
    gui_only = "-g" in tokens and not has_server_flag
    return has_server_flag and not gui_only


def gazebo_server_snapshots() -> dict[int, dict]:
    snapshots = {}
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        tokens = _read_proc_cmdline(pid)
        if not _is_gazebo_server(tokens):
            continue
        env = _read_proc_environ(pid)
        if env is None:
            # It exited between cmdline and environ reads.
            continue
        snapshots[pid] = {
            "pid": pid,
            "cmdline": tokens,
            "env": env,
        }
    return snapshots


def discover_new_gazebo_server(
    before_pids: set[int],
    runner_proc: subprocess.Popen,
    timeout: float = 20.0,
) -> dict | None:
    """
    Discover the Gazebo server spawned by the canonical runner.

    Crucially, environment is captured during discovery, before the short-lived
    server can disappear. This avoids the /proc/<pid>/environ race observed in
    the first demo package.
    """
    deadline = time.monotonic() + timeout
    runner_exit_seen_at = None

    while time.monotonic() < deadline:
        snapshots = gazebo_server_snapshots()
        candidates = [
            snap
            for pid, snap in snapshots.items()
            if pid not in before_pids
        ]
        if candidates:
            # Prefer the newest PID. The canonical server is normally the
            # newest server created immediately after the runner starts.
            candidates.sort(key=lambda snap: snap["pid"], reverse=True)
            return candidates[0]

        if runner_proc.poll() is not None:
            if runner_exit_seen_at is None:
                runner_exit_seen_at = time.monotonic()
            # Keep a short grace window because process creation / cleanup can
            # race with polling on very short scenarios.
            if time.monotonic() - runner_exit_seen_at > 0.8:
                break

        time.sleep(0.05)

    return None


def gui_env_from_server(
    base_env: dict[str, str],
    server_env: dict[str, str],
) -> dict[str, str]:
    """
    Build a clean GUI environment from the desktop environment plus the exact
    runtime-owned Gazebo / ROS transport identity.

    Transport identity keys are removed first so stale values from a previous
    demo run cannot survive when the new server omits one of them.
    """
    env = dict(base_env)

    # Clear stale identity first.
    for key in ("GZ_PARTITION", "IGN_PARTITION", "ROS_DOMAIN_ID"):
        env.pop(key, None)

    # Reuse server-owned Gazebo / Ignition environment and ROS domain.
    for key, value in server_env.items():
        if (
            key == "ROS_DOMAIN_ID"
            or key.startswith("GZ_")
            or key.startswith("IGN_")
        ):
            env[key] = value

    # Gazebo / Ignition transport compatibility.
    if env.get("GZ_PARTITION") and not env.get("IGN_PARTITION"):
        env["IGN_PARTITION"] = env["GZ_PARTITION"]

    return env


def start_gui_attach_to_server(
    server_snapshot: dict,
    base_env: dict[str, str],
    log_path: Path,
):
    cli = gazebo_cli()
    if not cli:
        return None

    env = gui_env_from_server(
        base_env,
        server_snapshot["env"],
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a", encoding="utf-8")

    try:
        proc = subprocess.Popen(
            cli + ["-g"],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        proc._demo_log_handle = log
        proc._expected_transport = normalized_transport_identity(
            server_snapshot["env"]
        )

        # Verify the environment actually seen by the GUI process.
        deadline = time.monotonic() + 2.0
        actual = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            actual_env = _read_proc_environ(proc.pid)
            if actual_env is not None:
                actual = normalized_transport_identity(actual_env)
                break
            time.sleep(0.05)

        proc._actual_transport = actual
        proc._transport_verified = (
            actual == proc._expected_transport
        )

        if not proc._transport_verified:
            stop_proc(proc)
            return None

        return proc
    except Exception:
        log.close()
        return None


def runner_gazebo_servers(
    runner_pid: int,
) -> list[dict]:
    """
    Return live Gazebo server processes that belong to the canonical runner
    process tree. This avoids attaching to unrelated or stale servers.
    """
    out = []
    for snap in gazebo_server_snapshots().values():
        if process_is_descendant(
            snap["pid"],
            runner_pid,
        ):
            out.append(snap)

    out.sort(key=lambda snap: snap["pid"])
    return out


def newest_runner_gazebo_server(
    runner_pid: int,
) -> dict | None:
    servers = runner_gazebo_servers(runner_pid)
    return servers[-1] if servers else None


def context_env() -> dict[str, str]:
    """
    Isolated environment only for presentation-only context worlds.

    This is intentionally NOT used for canonical Normal/SIM-009 runners.
    """
    env = os.environ.copy()
    partition = (
        env.get("DEMO_GZ_PARTITION")
        or f"sim-first-context-{os.getpid()}"
    )
    env["GZ_PARTITION"] = partition
    env["IGN_PARTITION"] = partition
    if os.environ.get("DEMO_CONTEXT_ROS_DOMAIN_ID"):
        env["ROS_DOMAIN_ID"] = os.environ["DEMO_CONTEXT_ROS_DOMAIN_ID"]
    return env


def runner_env() -> dict[str, str]:
    """
    Preserve the caller environment but do not inject demo-owned transport
    isolation into canonical runners. The runner owns its per-run partition and
    ROS domain.
    """
    env = os.environ.copy()

    # Remove accidental values from older demo package usage when explicitly
    # marked as demo-owned.
    if env.get("GZ_PARTITION", "").startswith("sim-first-demo-"):
        env.pop("GZ_PARTITION", None)
    if env.get("IGN_PARTITION", "").startswith("sim-first-demo-"):
        env.pop("IGN_PARTITION", None)

    return env


def start_context_world(
    env: dict,
    world: Path,
    paused: bool,
    log_path: Path,
):
    cli = gazebo_cli()
    if not cli:
        return None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8")
    cmd = cli + [str(world)]
    if not paused:
        cmd += ["-r"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        proc._demo_log_handle = log
        return proc
    except Exception:
        log.close()
        return None


def stop_proc(proc):
    if not proc:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    handle = getattr(proc, "_demo_log_handle", None)
    if handle:
        try:
            handle.close()
        except Exception:
            pass





@dataclass
class RunnerSession:
    root: Path
    runner: Path | None
    cmd: list[str]
    cwd: Path
    env: dict[str, str]
    log_path: Path
    strategy: str
    final_output: Path | None = None
    generated_output: Path | None = None
    worktree: Path | None = None
    proc: subprocess.Popen | None = None
    log_handle: object | None = None

    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = open(
            self.log_path,
            "w",
            encoding="utf-8",
        )
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=str(self.cwd),
            env=self.env,
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
        )
        return self.proc

    def wait(self) -> int:
        if self.proc is None:
            raise RuntimeError("RunnerSession.start() was not called.")
        rc = self.proc.wait()
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None

        if (
            rc == 0
            and self.final_output is not None
            and self.generated_output is not None
            and self.generated_output != self.final_output
            and self.generated_output.is_file()
        ):
            self.final_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.generated_output, self.final_output)
        return rc

    def cleanup(self):
        if self.log_handle:
            try:
                self.log_handle.close()
            except Exception:
                pass
            self.log_handle = None

        if self.worktree:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.root),
                    "worktree",
                    "remove",
                    str(self.worktree),
                    "--force",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            shutil.rmtree(self.worktree, ignore_errors=True)
            self.worktree = None


def _create_detached_worktree(root: Path, prefix: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    # git worktree wants the target not to pre-exist.
    shutil.rmtree(tmp)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            "--detach",
            str(tmp),
            "HEAD",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return tmp


def prepare_normal_session(
    root: Path,
    env: dict[str, str],
    output: Path,
) -> RunnerSession:
    runner = normal_runner(root)
    if has_flag(runner, "--output"):
        return RunnerSession(
            root=root,
            runner=runner,
            cmd=[sys.executable, str(runner), "--output", str(output)],
            cwd=root,
            env=env,
            log_path=root / "results/demo/logs/normal_runner.log",
            strategy="direct-output",
            final_output=output,
            generated_output=output,
        )

    canon = accepted_sim008(root)
    rel_runner = runner.relative_to(root)
    rel_canon = canon.relative_to(root)
    tmp = _create_detached_worktree(root, "sim008-3d-demo-")

    env2 = dict(env)
    env2["PYTHONPATH"] = (
        f"{tmp / 'src'}:{tmp}:{env2.get('PYTHONPATH', '')}"
    )
    env2["REPO_ROOT"] = str(tmp)

    return RunnerSession(
        root=root,
        runner=runner,
        cmd=[sys.executable, str(tmp / rel_runner)],
        cwd=tmp,
        env=env2,
        log_path=root / "results/demo/logs/normal_runner.log",
        strategy="isolated-worktree",
        final_output=output,
        generated_output=tmp / rel_canon,
        worktree=tmp,
    )


def prepare_failure_session(
    root: Path,
    env: dict[str, str],
    scenario_id: str,
    output: Path,
) -> RunnerSession:
    envkey = (
        "DEMO_NAV_TIMEOUT_COMMAND"
        if scenario_id == SCENARIO_NAV_TIMEOUT
        else "DEMO_VERIFY_UNCERTAIN_COMMAND"
    )
    override = os.environ.get(envkey)

    runner = failure_runner(root)
    scenario_flag = has_flag(
        runner,
        "--scenario",
        "--scenario-id",
        "--only",
    )
    output_flag = has_flag(runner, "--output")

    extra = []
    if scenario_flag:
        extra += [scenario_flag, scenario_id]

    if override:
        # Execute explicit task command in an isolated worktree unless user has
        # separately designed it to write only to results/demo/.
        tmp = _create_detached_worktree(root, "sim009-3d-demo-")
        env2 = dict(env)
        env2["PYTHONPATH"] = (
            f"{tmp / 'src'}:{tmp}:{env2.get('PYTHONPATH', '')}"
        )
        env2["REPO_ROOT"] = str(tmp)
        return RunnerSession(
            root=root,
            runner=runner,
            cmd=["bash", "-lc", override],
            cwd=tmp,
            env=env2,
            log_path=root
            / f"results/demo/logs/{scenario_id}_runner.log",
            strategy="override-isolated-worktree",
            final_output=output,
            generated_output=tmp
            / "results/simulation/SIM-009_failure_recovery.json",
            worktree=tmp,
        )

    if output_flag:
        cmd = [sys.executable, str(runner), *extra, output_flag, str(output)]
        return RunnerSession(
            root=root,
            runner=runner,
            cmd=cmd,
            cwd=root,
            env=env,
            log_path=root
            / f"results/demo/logs/{scenario_id}_runner.log",
            strategy=(
                "filtered-direct-output"
                if scenario_flag
                else "full-suite-direct-output"
            ),
            final_output=output,
            generated_output=output,
        )

    # No --output: never run against canonical results in the main worktree.
    tmp = _create_detached_worktree(root, "sim009-3d-demo-")
    rel_runner = runner.relative_to(root)
    env2 = dict(env)
    env2["PYTHONPATH"] = (
        f"{tmp / 'src'}:{tmp}:{env2.get('PYTHONPATH', '')}"
    )
    env2["REPO_ROOT"] = str(tmp)
    cmd = [sys.executable, str(tmp / rel_runner), *extra]

    return RunnerSession(
        root=root,
        runner=runner,
        cmd=cmd,
        cwd=tmp,
        env=env2,
        log_path=root
        / f"results/demo/logs/{scenario_id}_runner.log",
        strategy=(
            "filtered-isolated-worktree"
            if scenario_flag
            else "full-suite-isolated-worktree"
        ),
        final_output=output,
        generated_output=tmp
        / "results/simulation/SIM-009_failure_recovery.json",
        worktree=tmp,
    )


def find_scenario(path: Path, scenario_id: str):
    data = json.loads(path.read_text(encoding="utf-8"))
    best = None
    score = -1

    def walk(node):
        nonlocal best, score
        if isinstance(node, dict):
            sid = node.get("id") or node.get("scenario_id")
            if sid == scenario_id:
                current = sum(
                    key in node
                    for key in (
                        "layer",
                        "outcome_kind",
                        "expected_decision",
                        "decision",
                        "mission",
                        "pass",
                    )
                )
                if current > score:
                    best = node
                    score = current
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return best


def print_scenario(row):
    if not row:
        print("Scenario result not found.")
        return

    mission = (
        row.get("mission")
        if isinstance(row.get("mission"), dict)
        else {}
    )
    keys = [
        "id",
        "layer",
        "backend",
        "outcome_kind",
        "expected_decision",
        "decision",
        "route",
        "pass",
        "within_budget",
        "cleanup_complete",
    ]
    out = {key: row.get(key) for key in keys if key in row}
    out["mission_state"] = mission.get("mission_state")
    out["mission_success_committed"] = mission.get(
        "mission_success_committed"
    )
    out["verification_verdict"] = mission.get(
        "verification_verdict"
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
