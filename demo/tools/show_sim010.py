#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values(): yield from walk(v)
    elif isinstance(node, list):
        for v in node: yield from walk(v)

def collect_first(data, keys):
    found = {}
    for d in walk(data):
        if not isinstance(d, dict): continue
        for k in keys:
            if k not in found and k in d:
                found[k] = d[k]
    return found

ap = argparse.ArgumentParser()
ap.add_argument("evidence")
ap.add_argument("--full", action="store_true")
args = ap.parse_args()
p = Path(args.evidence)
if not p.is_file(): sys.exit(f"Evidence not found: {p}")
data = json.loads(p.read_text())
if args.full:
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    keys = [
        "task_id","task_specific_result","evidence_reproducible","regression_green",
        "observability_sufficient","replay","regression","accepted_sources",
        "source_index","claim_scope","simulation_only"
    ]
    print(json.dumps(collect_first(data, keys), indent=2, ensure_ascii=False))
