#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values(): yield from walk(v)
    elif isinstance(node, list):
        for v in node: yield from walk(v)

def first(data, names):
    for d in walk(data):
        if isinstance(d, dict):
            for n in names:
                if n in d:
                    return d[n]
    return None

ap = argparse.ArgumentParser()
ap.add_argument("evidence")
ap.add_argument("--full", action="store_true")
args = ap.parse_args()
p = Path(args.evidence)
if not p.is_file(): sys.exit(f"Evidence not found: {p}")
data = json.loads(p.read_text())

if args.full:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    raise SystemExit

summary = {
    "task_id": first(data, ["task_id"]),
    "task_specific_result": first(data, ["task_specific_result","task_specific_decision"]),
    "scenario_id": first(data, ["scenario_id","id"]),
    "mission_id": first(data, ["mission_id"]),
    "initial_state": first(data, ["initial_state","initial_mission_state"]),
    "final_state": first(data, ["final_state","final_mission_state","mission_state"]),
    "verification_verdict": first(data, ["verification_verdict","verdict"]),
    "cleanup_complete": first(data, ["cleanup_complete"]),
    "duration_ms": first(data, ["duration_ms","wall_duration_ms"]),
    "physical_dependency": first(data, ["physical_dependency"]),
}
print(json.dumps({k:v for k,v in summary.items() if v is not None}, indent=2, ensure_ascii=False))
