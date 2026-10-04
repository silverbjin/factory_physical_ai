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


def _attach_to_exact_server(
    root: Path,
    server: dict,
    scene: str,
):
    gui = start_gui_attach_to_server(
        server,
        os.environ.copy(),
        root / f"results/demo/logs/gazebo_gui_{scene}.log",
    )

    info = _server_public_info(server)
    verified = bool(
        gui
        and getattr(gui, "_transport_verified", False)
    )

    if verified:
        print(
            "[3D DEMO] GUI transport verified "
            f"server_pid={server['pid']} "
            f"gui_pid={gui.pid} "
            f"partition={info.get('gazebo_partition')} "
            f"ROS_DOMAIN_ID={info.get('ros_domain_id')}"
        )
    else:
        print(
            "[3D DEMO][WARN] GUI transport verification failed "
            f"for server pid={server['pid']}",
            file=sys.stderr,
        )

    return gui, verified


def _run_with_gui_follow(
    root: Path,
    session: RunnerSession,
    scene: str,
    headline: str,
):
    """
    Run the canonical session without SIGSTOP / timing manipulation.

    While the runner is alive:
      * follow only Gazebo servers in the runner's descendant process tree;
      * attach the GUI to the current server's exact transport identity;
      * if the runtime replaces its Gazebo server, close the stale GUI and
        automatically attach a new GUI to the replacement server.

    This directly addresses the observed case where the GUI retained the
    partition/domain of an earlier server while a new server was active.
    """
    stale_guis = gazebo_gui_snapshots()
    if stale_guis:
        ids = ", ".join(str(pid) for pid in sorted(stale_guis))
        raise RuntimeError(
            "A Gazebo GUI is already running before this demo "
            f"(PID(s): {ids}). Close only those GUI windows/processes "
            "and rerun. The demo refuses to mix stale and current GUI."
        )

    proc = session.start()
    current_server = None
    gui = None
    ever_attached = False
    server_history = []

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

    poll_s = float(
        os.environ.get("DEMO_SERVER_FOLLOW_POLL_SECONDS", "0.10")
    )
    poll_s = max(0.03, min(poll_s, 0.50))

    while proc.poll() is None:
        server = newest_runner_gazebo_server(proc.pid)

        if server is not None:
            changed = (
                current_server is None
                or server["pid"] != current_server["pid"]
                or not Path(
                    f"/proc/{current_server['pid']}"
                ).exists()
            )

            if changed:
                if gui is not None:
                    stop_proc(gui)
                    gui = None

                current_server = server
                server_history.append(
                    _server_public_info(server)
                )

                gui, verified = _attach_to_exact_server(
                    root,
                    server,
                    scene,
                )
                ever_attached = ever_attached or verified

                info = _server_public_info(server)
                write_state(
                    root,
                    scene=scene,
                    mode="LIVE_CANONICAL_RUN",
                    phase="running",
                    headline=headline,
                    gazebo_3d=verified,
                    transport_verified=verified,
                    strategy=session.strategy,
                    runner_pid=proc.pid,
                    gui_pid=gui.pid if gui else None,
                    server_history=server_history,
                    **info,
                )

        # If the server vanished, discard the stale GUI immediately rather
        # than leaving a blank window that looks connected.
        if (
            current_server is not None
            and not Path(
                f"/proc/{current_server['pid']}"
            ).exists()
        ):
            stop_proc(gui)
            gui = None
            current_server = None
            write_state(
                root,
                scene=scene,
                mode="LIVE_CANONICAL_RUN",
                phase="server_transition",
                headline="Runtime is transitioning Gazebo server",
                gazebo_3d=False,
                strategy=session.strategy,
                runner_pid=proc.pid,
                server_history=server_history,
            )

        time.sleep(poll_s)

    rc = session.wait()

    # The canonical runtime owns bounded server cleanup. Close the GUI as soon
    # as the runner ends so the audience is never left looking at an empty
    # Entity Tree from a disconnected GUI.
    stop_proc(gui)
    gui = None

    return rc, current_server, ever_attached, server_history



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

    try:
        rc, server, attached, history = _run_with_gui_follow(
            root,
            session,
            "normal",
            "Normal E2E executing in Gazebo",
        )

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
            gazebo_3d=False,
            transport_verified_during_run=attached,
            server_history=history,
            disclosure=(
                "Gazebo GUI is intentionally closed when the canonical "
                "runner finishes because the runtime also performs bounded "
                "server cleanup."
            ),
            **info,
        )

        print(
            f"[3D DEMO] strategy={session.strategy} "
            f"runner={session.runner.relative_to(root)} rc={rc}"
        )
        print(
            f"[3D DEMO] GUI transport verified during run={attached}"
        )
        if out.exists():
            print(f"[3D DEMO] evidence={out.relative_to(root)}")

        return rc
    finally:
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

    context = None
    try:
        rc, server, attached, history = _run_with_gui_follow(
            root,
            session,
            scene,
            f"{scenario_id} executing",
        )

        # Verification uncertainty may legitimately have no Gazebo server in
        # its semantic fixture. Only after the live canonical run ends do we
        # optionally show a separately disclosed context world.
        if (
            not attached
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
            gazebo_3d=bool(context),
            transport_verified_during_run=attached,
            runner_mode=session.strategy,
            scenario=row or {},
            server_history=history,
            **info,
        )

        print(
            f"[3D DEMO] runner mode={session.strategy} rc={rc}"
        )
        print(
            f"[3D DEMO] GUI transport verified during run={attached}"
        )
        print_scenario(row)

        if context:
            wait_for_enter(
                "Verification context world를 확인한 뒤 "
                "Enter를 누르면 종료합니다... "
            )

        return rc
    finally:
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
