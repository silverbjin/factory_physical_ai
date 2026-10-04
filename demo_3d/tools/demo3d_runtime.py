#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from demo3d_common import *


def wait_for_enter(msg):
    if os.environ.get("DEMO_NO_WAIT") == "1":
        return
    try:
        input(msg)
    except EOFError:
        pass


def _server_public_info(server: dict | None) -> dict:
    if not server:
        return {}
    env = server.get("env", {})
    return {
        "gazebo_server_pid": server.get("pid"),
        "gazebo_partition": env.get("GZ_PARTITION")
        or env.get("IGN_PARTITION"),
        "ros_domain_id": env.get("ROS_DOMAIN_ID"),
        "gazebo_server_command": " ".join(
            server.get("cmdline", [])
        ),
    }


def _discover_and_attach(
    root: Path,
    session: RunnerSession,
    scene: str,
    headline: str,
):
    before = set(gazebo_server_snapshots())
    proc = session.start()

    write_state(
        root,
        scene=scene,
        mode="LIVE_CANONICAL_RUN",
        phase="runner_started",
        headline=headline,
        gazebo_3d=False,
        strategy=session.strategy,
        runner_pid=proc.pid,
    )

    timeout = float(os.environ.get("DEMO_GZ_DISCOVERY_TIMEOUT", "20"))
    server = discover_new_gazebo_server(
        before,
        proc,
        timeout=timeout,
    )

    gui = None
    if server:
        gui = start_gui_attach_to_server(
            server,
            os.environ.copy(),
            root
            / f"results/demo/logs/gazebo_gui_{scene}.log",
        )
        info = _server_public_info(server)
        write_state(
            root,
            scene=scene,
            mode="LIVE_CANONICAL_RUN",
            phase="running",
            headline=headline,
            gazebo_3d=bool(gui),
            strategy=session.strategy,
            runner_pid=proc.pid,
            **info,
        )
        print(
            "[3D DEMO] attached GUI to runtime-owned server "
            f"pid={server['pid']} "
            f"partition={info.get('gazebo_partition')} "
            f"ROS_DOMAIN_ID={info.get('ros_domain_id')}"
        )
    else:
        write_state(
            root,
            scene=scene,
            mode="LIVE_CANONICAL_RUN",
            phase="running_without_3d_attach",
            headline=headline,
            gazebo_3d=False,
            strategy=session.strategy,
            runner_pid=proc.pid,
            disclosure=(
                "No new canonical Gazebo server was discovered before "
                "the bounded timeout. Check the runner log."
            ),
        )
        print(
            "[3D DEMO][WARN] canonical Gazebo server was not "
            "discovered; GUI attach skipped.",
            file=sys.stderr,
        )

    return server, gui


def normal(root: Path):
    env = runner_env()
    out = root / "results/demo/SIM-008_normal_e2e_demo.json"
    session = prepare_normal_session(root, env, out)

    write_state(
        root,
        scene="normal",
        mode="LIVE_CANONICAL_RUN",
        phase="starting",
        headline="Starting canonical Normal E2E",
        gazebo_3d=False,
        strategy=session.strategy,
    )

    server = gui = None
    try:
        server, gui = _discover_and_attach(
            root,
            session,
            "normal",
            "Normal E2E executing in Gazebo",
        )
        rc = session.wait()

        info = _server_public_info(server)
        write_state(
            root,
            scene="normal",
            mode="LIVE_CANONICAL_RUN",
            phase="complete" if rc == 0 else "failed",
            headline=(
                "Normal E2E complete"
                if rc == 0
                else "Normal E2E failed"
            ),
            output=(
                str(out.relative_to(root))
                if out.exists()
                else None
            ),
            runner=(
                str(session.runner.relative_to(root))
                if session.runner
                else None
            ),
            strategy=session.strategy,
            exit_code=rc,
            gazebo_3d=bool(gui),
            **info,
        )

        print(
            f"[3D DEMO] strategy={session.strategy} "
            f"runner={session.runner.relative_to(root)} rc={rc}"
        )
        if out.exists():
            print(f"[3D DEMO] evidence={out.relative_to(root)}")

        wait_for_enter(
            "Gazebo 3D 실행을 확인한 뒤 Enter를 누르면 "
            "viewer를 종료합니다... "
        )
        return rc
    finally:
        stop_proc(gui)
        session.cleanup()


def run_failure(root: Path, scenario_id: str, scene: str):
    env = runner_env()
    out = root / "results/demo/SIM-009_failure_recovery_demo.json"
    session = prepare_failure_session(
        root,
        env,
        scenario_id,
        out,
    )

    mode = (
        "LIVE_FAILURE_SCENARIO"
        if "full-suite" not in session.strategy
        else "LIVE_FULL_FAILURE_SUITE"
    )
    write_state(
        root,
        scene=scene,
        mode=mode,
        phase="starting",
        headline=f"Starting {scenario_id}",
        gazebo_3d=False,
        scenario_id=scenario_id,
        runner_mode=session.strategy,
    )

    server = gui = context = None
    try:
        server, gui = _discover_and_attach(
            root,
            session,
            scene,
            f"{scenario_id} executing",
        )

        # Verification uncertainty may be a semantic evaluation with no
        # physical-motion Gazebo server. In that case show a separately
        # isolated, explicitly disclosed live 3D context world.
        if (
            server is None
            and scene == "verify_uncertain"
            and os.environ.get(
                "DEMO_UNCERTAIN_CONTEXT_WORLD",
                "1",
            )
            == "1"
        ):
            world = resolve_world(root)
            if world:
                context = start_context_world(
                    context_env(),
                    world,
                    False,
                    root
                    / "results/demo/logs/"
                    "uncertain_context_world.log",
                )
                write_state(
                    root,
                    scene=scene,
                    mode="LIVE_3D_CONTEXT_PLUS_VERIFICATION",
                    phase="running",
                    headline=(
                        "Gazebo world live; Verification uncertainty "
                        "is being evaluated"
                    ),
                    gazebo_3d=bool(context),
                    scenario_id=scenario_id,
                    disclosure=(
                        "3D world is visual context because the "
                        "Verification fixture itself may not create "
                        "physical motion."
                    ),
                )

        rc = session.wait()

        source = (
            out
            if out.exists()
            else accepted_sim009(root)
        )
        row = find_scenario(source, scenario_id)
        info = _server_public_info(server)

        write_state(
            root,
            scene=scene,
            mode=(
                "LIVE_SCENARIO_OUTPUT"
                if out.exists()
                else "LIVE_RUN_PLUS_ACCEPTED_SEMANTIC_EVIDENCE"
            ),
            phase="complete" if rc == 0 else "failed",
            headline=(
                f"{scenario_id} complete"
                if rc == 0
                else f"{scenario_id} failed"
            ),
            scenario_id=scenario_id,
            exit_code=rc,
            evidence=str(source.relative_to(root)),
            gazebo_3d=bool(gui or context),
            runner_mode=session.strategy,
            scenario=row or {},
            **info,
        )

        print(
            f"[3D DEMO] runner mode={session.strategy} rc={rc}"
        )
        print_scenario(row)

        wait_for_enter(
            "3D 장면과 상태를 확인한 뒤 Enter를 누르면 "
            "viewer를 종료합니다... "
        )
        return rc
    finally:
        stop_proc(gui)
        stop_proc(context)
        session.cleanup()


def qualification(root: Path):
    out = root / "results/demo/SIM-E2E_qualification_demo.json"
    world = resolve_world(root)
    context = None

    if world:
        context = start_context_world(
            context_env(),
            world,
            True,
            root
            / "results/demo/logs/"
            "qualification_context_world.log",
        )

    write_state(
        root,
        scene="qualification",
        mode="EVIDENCE_ONLY_GATE_WITH_PAUSED_3D_CONTEXT",
        phase="running",
        headline=(
            "Final Qualification is evaluating accepted Evidence"
        ),
        gazebo_3d=bool(context),
        disclosure=(
            "The 3D scene is paused visual context. "
            "TASK-SIM-E2E itself does not execute simulation."
        ),
    )

    q = qualifier(root)
    if not has_flag(q, "--output"):
        stop_proc(context)
        raise SystemExit(
            "Qualification verifier has no --output; refusing "
            "to overwrite canonical Evidence."
        )

    cp = subprocess.run(
        [sys.executable, str(q), "--output", str(out)],
        cwd=str(root),
        env=runner_env(),
        capture_output=True,
        text=True,
    )
    lines = (cp.stdout or "").strip().splitlines()
    decision = lines[-1] if lines else "UNRESOLVED"

    write_state(
        root,
        scene="qualification",
        mode="EVIDENCE_ONLY_GATE_WITH_PAUSED_3D_CONTEXT",
        phase="complete" if cp.returncode == 0 else "failed",
        headline=decision,
        decision=decision,
        output=(
            str(out.relative_to(root))
            if out.exists()
            else None
        ),
        gazebo_3d=bool(context),
        disclosure=(
            "3D context is presentation-only; qualification remains "
            "read-only Evidence evaluation."
        ),
    )

    print(decision)
    if cp.stderr:
        print(cp.stderr, file=sys.stderr)

    wait_for_enter(
        "Qualification 결과를 확인한 뒤 Enter를 누르면 "
        "3D context를 종료합니다... "
    )
    stop_proc(context)
    return cp.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "scene",
        choices=[
            "normal",
            "nav_timeout",
            "verify_uncertain",
            "qualification",
        ],
    )
    args = ap.parse_args()
    root = repo_root()

    if args.scene == "normal":
        rc = normal(root)
    elif args.scene == "nav_timeout":
        rc = run_failure(
            root,
            SCENARIO_NAV_TIMEOUT,
            "nav_timeout",
        )
    elif args.scene == "verify_uncertain":
        rc = run_failure(
            root,
            SCENARIO_VERIFY_UNCERTAIN,
            "verify_uncertain",
        )
    else:
        rc = qualification(root)

    raise SystemExit(rc)


if __name__ == "__main__":
    main()
