#!/usr/bin/env python3
"""Write bounded TASK-SIM-007 profile smoke evidence."""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.mission_integration import PROFILES, MissionIntegrationRuntime, make_mission_request

def main() -> int:
    rows = []
    for name, profile in PROFILES.items():
        runtime = MissionIntegrationRuntime(name)
        outcome = runtime.execute(make_mission_request())
        mission = outcome["mission"]
        rows.append({"profile": name, "pass": mission["result"] == "success" and outcome.get("verification", {}).get("verdict") == "pass" and runtime.cleaned_up, "mission_id": mission["mission_id"], "trace_id": mission["trace_id"], "action_ids": [outcome.get("navigation", {}).get("action_id"), outcome.get("vla", {}).get("action_id"), outcome.get("verification", {}).get("action_id")], "system_world": profile.integrated_world, "mujoco_live_world": name != "system" and profile.vla == "mujoco", "verification_before_completion": "verification" in outcome})
    accepted = {task: json.loads((ROOT / f"results/reviews/{task}_acceptance.json").read_text()) for task in ("SIM-004", "SIM-005", "SIM-006")}
    passed = all(row["pass"] for row in rows)
    payload = {"schema_version": "1.0", "task_id": "TASK-SIM-007", "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "task_specific_result": "SIM_MISSION_INTEGRATION_READY" if passed else "SIM_MISSION_INTEGRATION_BLOCKED", "accepted_bindings": accepted, "profiles": {name: profile.__dict__ for name, profile in PROFILES.items()}, "profile_smoke": rows, "system_authority": {"integrated_world": "gazebo_harmonic", "mujoco_live_world": False, "dual_world": False}, "bounded_lifecycle": {"startup_execution_cleanup_bounded": True, "physical_activity": False}}
    path = ROOT / "results/simulation/SIM-007_mission_integration.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))
    return 0 if passed else 1
if __name__ == "__main__": raise SystemExit(main())
