#!/usr/bin/env python3
from __future__ import annotations
import json, os, shlex, subprocess, sys, tempfile, time
from pathlib import Path

SCENARIO_NAV_TIMEOUT = "SIM009-NAV-TIMEOUT-RETRY"
SCENARIO_VERIFY_UNCERTAIN = "SIM009-VERIFY-UNCERTAIN"

def repo_root() -> Path:
    env = os.environ.get("REPO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    cp = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit("Repository root not found. Set REPO_ROOT.")
    return Path(cp.stdout.strip()).resolve()

def state_path(root: Path) -> Path:
    p = root/"results/demo/3d_demo_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def write_state(root: Path, **kw):
    payload = {
        "updated_at": time.time(),
        **kw
    }
    state_path(root).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def run_help(script: Path) -> str:
    cp = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
    return (cp.stdout or "") + "\n" + (cp.stderr or "")

def has_flag(script: Path, *flags: str) -> str | None:
    h = run_help(script)
    for f in flags:
        if f in h:
            return f
    return None

def normal_runner(root: Path) -> Path:
    override = os.environ.get("DEMO_NORMAL_RUNNER")
    if override:
        p = root/override
        if not p.is_file():
            raise SystemExit(f"DEMO_NORMAL_RUNNER missing: {p}")
        return p
    candidates = [
        root/"scripts/run_simulation_normal_system_e2e.py",
        root/"scripts/run_simulation_normal_e2e.py",
    ]
    found = [p for p in candidates if p.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("Normal E2E runner not found.")
    raise SystemExit("Multiple normal runners found. Set DEMO_NORMAL_RUNNER to the acceptance-bound runner.")

def failure_runner(root: Path) -> Path:
    override = os.environ.get("DEMO_FAILURE_RUNNER")
    if override:
        p = root/override
        if not p.is_file():
            raise SystemExit(f"DEMO_FAILURE_RUNNER missing: {p}")
        return p
    p = root/"scripts/run_simulation_failure_suite.py"
    if not p.is_file():
        raise SystemExit("scripts/run_simulation_failure_suite.py not found.")
    return p

def qualifier(root: Path) -> Path:
    p = root/"scripts/verify_simulation_e2e_qualification.py"
    if not p.is_file():
        raise SystemExit("Qualification verifier not found.")
    return p

def accepted_sim008(root: Path) -> Path:
    override = os.environ.get("DEMO_SIM008_EVIDENCE")
    if override:
        p = root/override
        if not p.is_file():
            raise SystemExit(f"DEMO_SIM008_EVIDENCE missing: {p}")
        return p
    candidates = [
        root/"results/simulation/SIM-008_normal_system_e2e.json",
        root/"results/simulation/SIM-008_normal_e2e.json",
    ]
    found = [p for p in candidates if p.is_file()]
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("SIM-008 accepted Evidence not found.")
    raise SystemExit("Multiple SIM-008 Evidence variants found. Set DEMO_SIM008_EVIDENCE.")

def accepted_sim009(root: Path) -> Path:
    p = root/"results/simulation/SIM-009_failure_recovery.json"
    if not p.is_file():
        raise SystemExit("SIM-009 accepted Evidence not found.")
    return p

def find_strings(node, key_hint=""):
    if isinstance(node, dict):
        for k,v in node.items():
            yield from find_strings(v, str(k))
    elif isinstance(node, list):
        for v in node:
            yield from find_strings(v, key_hint)
    elif isinstance(node, str):
        yield key_hint, node

def resolve_world(root: Path) -> Path | None:
    override = os.environ.get("DEMO_WORLD")
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = root/p
        return p.resolve() if p.exists() else None

    try:
        data = json.loads(accepted_sim008(root).read_text(encoding="utf-8"))
    except Exception:
        return None

    scored = []
    for key, value in find_strings(data):
        low = value.lower()
        if not (low.endswith(".sdf") or low.endswith(".world")):
            continue
        p = Path(value)
        if not p.is_absolute():
            p = root/p
        if p.exists():
            score = 0
            kl = key.lower()
            if "world" in kl: score += 5
            if "model" in kl: score -= 2
            if "scene" in kl: score += 1
            scored.append((score, p.resolve()))
    if not scored:
        return None
    scored.sort(key=lambda x:(-x[0], len(str(x[1]))))
    best_score = scored[0][0]
    best = []
    seen=set()
    for s,p in scored:
        if s != best_score: continue
        if str(p) not in seen:
            best.append(p); seen.add(str(p))
    return best[0] if len(best)==1 else None

def gazebo_cli():
    if subprocess.run(["bash","-lc","command -v gz >/dev/null 2>&1"]).returncode == 0:
        cp = subprocess.run(["gz","sim","--help"], capture_output=True, text=True)
        if cp.returncode == 0:
            return ["gz","sim"]
    if subprocess.run(["bash","-lc","command -v ign >/dev/null 2>&1"]).returncode == 0:
        cp = subprocess.run(["ign","gazebo","--help"], capture_output=True, text=True)
        if cp.returncode == 0:
            return ["ign","gazebo"]
    return None

def start_gui_attach(env: dict, log_path: Path):
    cli = gazebo_cli()
    if not cli:
        return None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8")
    try:
        return subprocess.Popen(cli+["-g"], stdout=log, stderr=subprocess.STDOUT, env=env)
    except Exception:
        log.close()
        return None

def start_context_world(env: dict, world: Path, paused: bool, log_path: Path):
    cli = gazebo_cli()
    if not cli:
        return None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8")
    cmd = cli + [str(world)]
    if not paused:
        cmd += ["-r"]
    try:
        return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    except Exception:
        log.close()
        return None

def stop_proc(p):
    if not p:
        return
    try:
        p.terminate()
        p.wait(timeout=3)
    except Exception:
        try: p.kill()
        except Exception: pass

def demo_env():
    env = os.environ.copy()
    partition = env.get("DEMO_GZ_PARTITION") or f"sim-first-demo-{os.getpid()}"
    env.setdefault("GZ_PARTITION", partition)
    env.setdefault("IGN_PARTITION", partition)
    env.setdefault("ROS_DOMAIN_ID", env.get("DEMO_ROS_DOMAIN_ID","42"))
    return env

def run_cmd(cmd, cwd: Path, env: dict, log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as log:
        return subprocess.run(cmd, cwd=str(cwd), env=env, stdout=log, stderr=subprocess.STDOUT).returncode

def safe_normal_run(root: Path, env: dict, output: Path):
    runner = normal_runner(root)
    flag = has_flag(runner, "--output")
    if flag:
        rc = run_cmd([sys.executable,str(runner),"--output",str(output)], root, env,
                     root/"results/demo/logs/normal_runner.log")
        return rc, runner, "direct-output"

    canon = accepted_sim008(root)
    rel_runner = runner.relative_to(root)
    rel_canon = canon.relative_to(root)
    tmp = Path(tempfile.mkdtemp(prefix="sim008-3d-demo-"))
    subprocess.run(["git","-C",str(root),"worktree","add","--detach",str(tmp),"HEAD"],
                   check=True, stdout=subprocess.DEVNULL)
    try:
        env2 = env.copy()
        env2["PYTHONPATH"] = f"{tmp/'src'}:{tmp}:{env2.get('PYTHONPATH','')}"
        rc = run_cmd([sys.executable,str(tmp/rel_runner)], tmp, env2,
                     root/"results/demo/logs/normal_runner.log")
        generated = tmp/rel_canon
        if rc == 0 and generated.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(generated.read_bytes())
        return rc, runner, "isolated-worktree"
    finally:
        subprocess.run(["git","-C",str(root),"worktree","remove",str(tmp),"--force"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            tmp.rmdir()
        except Exception:
            pass

def scenario_command(root: Path, scenario_id: str, output: Path):
    # Explicit command overrides are safest when the repository has task-specific CLI.
    envkey = "DEMO_NAV_TIMEOUT_COMMAND" if scenario_id==SCENARIO_NAV_TIMEOUT else "DEMO_VERIFY_UNCERTAIN_COMMAND"
    override = os.environ.get(envkey)
    if override:
        return ["bash","-lc",override], "override"

    runner = failure_runner(root)
    scenario_flag = has_flag(runner, "--scenario", "--scenario-id", "--only")
    output_flag = has_flag(runner, "--output")
    cmd = [sys.executable,str(runner)]
    if scenario_flag:
        cmd += [scenario_flag, scenario_id]
    if output_flag:
        cmd += [output_flag, str(output)]
    return cmd, ("filtered-suite" if scenario_flag else "full-suite")

def find_scenario(path: Path, scenario_id: str):
    data = json.loads(path.read_text(encoding="utf-8"))
    best=None; score=-1
    def walk(n):
        nonlocal best,score
        if isinstance(n,dict):
            sid=n.get("id") or n.get("scenario_id")
            if sid==scenario_id:
                s=sum(k in n for k in ("layer","outcome_kind","expected_decision","decision","mission","pass"))
                if s>score: best=n; score=s
            for v in n.values(): walk(v)
        elif isinstance(n,list):
            for v in n: walk(v)
    walk(data)
    return best

def print_scenario(row):
    if not row:
        print("Scenario result not found.")
        return
    mission = row.get("mission") if isinstance(row.get("mission"),dict) else {}
    keys = ["id","layer","backend","outcome_kind","expected_decision","decision","route","pass","within_budget","cleanup_complete"]
    out={k:row.get(k) for k in keys if k in row}
    out["mission_state"]=mission.get("mission_state")
    out["mission_success_committed"]=mission.get("mission_success_committed")
    out["verification_verdict"]=mission.get("verification_verdict")
    print(json.dumps(out,indent=2,ensure_ascii=False))
