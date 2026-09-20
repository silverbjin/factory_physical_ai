# Diagnosis — TASK-SIM-009

- Task: `TASK-SIM-009`
- Stage: `diagnosis`
- Status: `UNRESOLVED`
- Diagnosis disposition: `NEEDS_HOST_EVIDENCE`
- Mode: `READ_ONLY`
- Trigger stage: `host_live_validation_after_debug_fix`
- Trigger source: `TASK-SIM-009 runtime readiness regression`
- Triggering finding: `GoalTrackedGazeboNav2Runtime.start/bootstrap_localization did not reach live readiness; all four L1-NAV scenarios had runtime_calls=0.`

## Root cause and boundary

The failing boundary is localized, but repository evidence does not prove its root cause:

```text
GoalTrackedGazeboNav2Runtime()
→ live_runtime.start()
→ live_runtime.bootstrap_localization()
→ returns False OR raises exception
→ live_ready = False
```

The accepted runtime sets `_ready=True` only after the complete sequence:

```text
map_server/amcl configure+activate
→ topics
→ amcl active
→ odom→base_link TF
→ initial pose
→ map→odom TF
→ navigation lifecycle startup
→ bt_navigator active
→ navigate_to_pose available
→ _ready=True
```

Recent SIM-009 changes did not override or alter accepted SIM-004 `start()`, ROS domain or Gazebo partition propagation, subprocess launch/redirection, `bootstrap_localization()`, or the accepted localization/lifecycle/TF readiness procedure. The changed scenario-context, evidence-filtering, TF-injection, and behavior-tree attribution paths execute after readiness and were not reached by this host run.

Stored evidence shows SIM-009 startup failure at `2026-09-20T02:45:35Z`, while accepted SIM-004 later succeeded at `2026-09-20T02:53:13Z`, reaching localization TF, active `bt_navigator`, `/navigate_to_pose`, and real success/blocked goals. A persistent host-wide failure is therefore unsupported; repository evidence cannot distinguish a transient/run-specific failure, a bootstrap probe timeout, or a bootstrap exception.

`run_failure_suite()` currently loses startup diagnostics on this path: the canonical artifact does not retain sufficient exception type/message/traceback, localization readiness probes, process status, process-log tail, or runtime measurements to reconstruct the cause. This is a diagnosis finding only and does not authorize a source change.

## Required host evidence

### Host Test A — accepted SIM-004

Run the canonical accepted-runtime command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 scripts/run_simulation_navigation.py
```

Interpretation:

- `SIM_NAVIGATION_BACKEND_BLOCKED`: host/accepted-runtime startup issue.
- `SIM_NAVIGATION_BACKEND_READY`: accepted runtime works; continue with Test B.

### Host Test B — minimal SIM-009 startup probe

Run this read-only probe; it must not execute the full failure suite or any fault scenario:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
import sys
import traceback
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "src"))

from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime

runtime = GoalTrackedGazeboNav2Runtime()
bootstrap_result = None
failure = None
try:
    runtime.start()
    bootstrap_result = runtime.bootstrap_localization()
except Exception as exc:
    failure = {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
finally:
    pre_cleanup_process_status = [
        {"pid": process.pid, "returncode": process.poll()}
        for process in runtime.processes
    ]
    cleanup_complete = runtime.close()

print(json.dumps({
    "bootstrap_result": bootstrap_result,
    "ready": runtime.ready,
    "failure": failure,
    "environment": {
        "ROS_DOMAIN_ID": runtime.environment.get("ROS_DOMAIN_ID"),
        "GZ_PARTITION": runtime.environment.get("GZ_PARTITION"),
        "ROS_LOG_DIR": runtime.environment.get("ROS_LOG_DIR"),
    },
    "world_path": str(runtime.world_path),
    "pre_cleanup_process_status": pre_cleanup_process_status,
    "measurements": runtime.measurements,
    "cleanup_complete": cleanup_complete,
}, indent=2, sort_keys=True))
PY
```

Interpretation:

- `bootstrap_result=true` and `ready=true`: previous failure was not reproduced; likely transient/run-specific.
- Non-null `failure`: exception type/message/traceback identifies the next diagnosis boundary.
- `bootstrap_result=false`: inspect the first failed localization/lifecycle/TF readiness probe.
- SIM-004 READY plus repeated SIM-009 probe failure: evidence for a SIM-009-specific regression.

## Process assessment

The previous debugging pass was too broad. These should have been independent RED→GREEN cycles: scenario execution context; BLOCKED/TIMEOUT goal binding; goal Evidence filtering; TF Evidence filtering; TF baseline validation; and behavior-tree server-log attribution. Bundling them did not prove they caused readiness failure, but it made isolation harder when host validation stopped before those paths.

## Authorization and handoff

- Source Fix authorized: **NO**
- Accepted predecessor modification authorized: **NO**
- Acceptance authorized: **NO**
- Next action: `COLLECT_HOST_EVIDENCE`

After Host Tests A/B, continue with a read-only diagnosis. Only a later `RESOLVED` diagnosis may authorize the next Fix. No `acceptance_handoff` is created by this record.

## Modification scope

No implementation, configuration, test, Evidence, acceptance, checkpoint, or predecessor files are modified by this diagnosis record. The accepted SIM-004 runtime boundary remains protected.

## Authoritative sources

- `prompts/codex/task_history_recording_v2.md`
- `docs/task_history/TASK-SIM-009/10_diagnosis.md`
- `docs/task_history/TASK-SIM-009/11_fix.md`
- `results/simulation/SIM-009_failure_recovery.json`
- `results/simulation/SIM-004_navigation_backend.json`
- `scripts/run_simulation_navigation.py`
- `scripts/sim009_goal_tracked_navigation.py`
- `src/simulation_runtime/failure_recovery.py`
