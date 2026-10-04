#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path
from demo3d_common import *

def wait_for_enter(msg):
    if os.environ.get("DEMO_NO_WAIT")=="1":
        return
    try: input(msg)
    except EOFError: pass

def normal(root):
    env=demo_env()
    out=root/"results/demo/SIM-008_normal_e2e_demo.json"
    write_state(root, scene="normal", mode="LIVE_CANONICAL_RUN", phase="starting",
                headline="Starting canonical Normal E2E", gazebo_3d=True)
    gui=start_gui_attach(env, root/"results/demo/logs/gazebo_gui_normal.log")
    time.sleep(1.0)
    write_state(root, scene="normal", mode="LIVE_CANONICAL_RUN", phase="running",
                headline="Normal E2E executing in Gazebo", gazebo_3d=True)
    rc,runner,strategy=safe_normal_run(root,env,out)
    write_state(root, scene="normal", mode="LIVE_CANONICAL_RUN", phase="complete" if rc==0 else "failed",
                headline="Normal E2E complete" if rc==0 else "Normal E2E failed",
                output=str(out.relative_to(root)), runner=str(runner.relative_to(root)),
                strategy=strategy, exit_code=rc, gazebo_3d=True)
    print(f"[3D DEMO] strategy={strategy} runner={runner.relative_to(root)} rc={rc}")
    if out.exists():
        print(f"[3D DEMO] evidence={out.relative_to(root)}")
    wait_for_enter("Gazebo 3D 장면을 확인한 뒤 Enter를 누르면 viewer를 종료합니다... ")
    stop_proc(gui)
    return rc

def run_failure(root, scenario_id, scene):
    env=demo_env()
    out=root/"results/demo/SIM-009_failure_recovery_demo.json"
    cmd,mode=scenario_command(root,scenario_id,out)
    write_state(root, scene=scene, mode="LIVE_FAILURE_SCENARIO" if mode!="full-suite" else "LIVE_FULL_FAILURE_SUITE",
                phase="starting", headline=f"Starting {scenario_id}", gazebo_3d=True,
                scenario_id=scenario_id, runner_mode=mode)

    # Attach a Gazebo GUI to the canonical server. If the verification scenario does
    # not start Gazebo itself, optionally provide a clearly labeled live 3D context world.
    gui=start_gui_attach(env, root/f"results/demo/logs/gazebo_gui_{scene}.log")
    context=None
    if scene=="verify_uncertain" and os.environ.get("DEMO_UNCERTAIN_CONTEXT_WORLD","1")=="1":
        world=resolve_world(root)
        if world:
            # Give canonical runner/server a chance first. Context world is used only as
            # visual context and is explicitly labeled in state.
            time.sleep(1.2)
            if gui and gui.poll() is not None:
                gui=None
            context=start_context_world(env,world,False,root/"results/demo/logs/uncertain_context_world.log")
            write_state(root, scene=scene, mode="LIVE_3D_CONTEXT_PLUS_VERIFICATION",
                        phase="running", headline="Gazebo world live; Verification uncertainty is being evaluated",
                        gazebo_3d=True, scenario_id=scenario_id,
                        disclosure="3D world is visual context when the Verification fixture itself has no physical motion.")
    time.sleep(1.0)
    log=root/f"results/demo/logs/{scene}_runner.log"
    rc=run_cmd(cmd,root,env,log)

    # If runner could not redirect output, use accepted evidence for semantic display,
    # but never overwrite canonical evidence.
    source=out if out.exists() else accepted_sim009(root)
    row=find_scenario(source,scenario_id)
    write_state(root, scene=scene,
                mode=("LIVE_SCENARIO_OUTPUT" if out.exists() else "LIVE_RUN_PLUS_ACCEPTED_SEMANTIC_EVIDENCE"),
                phase="complete" if rc==0 else "failed",
                headline=f"{scenario_id} complete" if rc==0 else f"{scenario_id} failed",
                scenario_id=scenario_id, exit_code=rc,
                evidence=str(source.relative_to(root)), gazebo_3d=True,
                scenario=row or {})
    print(f"[3D DEMO] runner mode={mode} rc={rc}")
    print_scenario(row)
    wait_for_enter("3D 장면과 상태를 확인한 뒤 Enter를 누르면 viewer를 종료합니다... ")
    stop_proc(gui); stop_proc(context)
    return rc

def qualification(root):
    env=demo_env()
    out=root/"results/demo/SIM-E2E_qualification_demo.json"
    world=resolve_world(root)
    context=None
    if world:
        context=start_context_world(env,world,True,root/"results/demo/logs/qualification_context_world.log")
    write_state(root, scene="qualification", mode="EVIDENCE_ONLY_GATE_WITH_PAUSED_3D_CONTEXT",
                phase="running", headline="Final Qualification is evaluating accepted Evidence",
                gazebo_3d=bool(world),
                disclosure="The 3D scene is paused visual context. TASK-SIM-E2E itself does not execute simulation.")
    q=qualifier(root)
    flag=has_flag(q,"--output")
    if not flag:
        raise SystemExit("Qualification verifier has no --output; refusing to overwrite canonical Evidence.")
    cp=subprocess.run([sys.executable,str(q),"--output",str(out)], cwd=str(root), env=env,
                      capture_output=True,text=True)
    decision=(cp.stdout or "").strip().splitlines()
    decision=decision[-1] if decision else "UNRESOLVED"
    write_state(root, scene="qualification", mode="EVIDENCE_ONLY_GATE_WITH_PAUSED_3D_CONTEXT",
                phase="complete" if cp.returncode==0 else "failed",
                headline=decision, decision=decision,
                output=str(out.relative_to(root)) if out.exists() else None,
                gazebo_3d=bool(world),
                disclosure="3D context is presentation-only; qualification remains read-only evidence evaluation.")
    print(decision)
    if cp.stderr:
        print(cp.stderr,file=sys.stderr)
    wait_for_enter("Qualification 결과를 확인한 뒤 Enter를 누르면 3D context를 종료합니다... ")
    stop_proc(context)
    return cp.returncode

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("scene",choices=["normal","nav_timeout","verify_uncertain","qualification"])
    args=ap.parse_args()
    root=repo_root()
    if args.scene=="normal": rc=normal(root)
    elif args.scene=="nav_timeout": rc=run_failure(root,SCENARIO_NAV_TIMEOUT,"nav_timeout")
    elif args.scene=="verify_uncertain": rc=run_failure(root,SCENARIO_VERIFY_UNCERTAIN,"verify_uncertain")
    else: rc=qualification(root)
    raise SystemExit(rc)

if __name__=="__main__":
    main()
