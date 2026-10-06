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
                if n in d: return d[n]
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

summary = {}
for keyset, label in [
    (["task_id"], "task_id"),
    (["task_specific_result","gate_result","decision","result"], "decision"),
    (["qualification_matrix","matrix"], "qualification_matrix"),
    (["authorization_snapshot","authorization"], "authorization_snapshot"),
    (["physical_dependency"], "physical_dependency"),
    (["dual_world_cosimulation_required"], "dual_world_cosimulation_required"),
    (["evaluation_repo_head","source_git_sha","git_sha"], "git_revision"),
]:
    v = first(data, keyset)
    if v is not None: summary[label] = v
print(json.dumps(summary, indent=2, ensure_ascii=False))
