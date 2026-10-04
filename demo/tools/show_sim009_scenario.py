#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)

def sid(d):
    return d.get("id") or d.get("scenario_id")

def find_scenarios(data):
    out = {}
    for d in walk(data):
        if isinstance(d, dict) and sid(d):
            s = str(sid(d))
            # Prefer objects that look like scenario result rows.
            score = sum(k in d for k in ("layer","decision","expected_decision","outcome_kind","pass","cleanup_complete"))
            if s not in out or score > out[s][0]:
                out[s] = (score, d)
    return {k:v for k,(_,v) in out.items()}

def compact(row):
    keys = [
        "id","scenario_id","layer","backend","injection","outcome_kind",
        "expected_decision","decision","route","pass","within_budget",
        "cleanup_complete","duration_ms","failure_code","error"
    ]
    result = {k:row[k] for k in keys if k in row}
    for k in ("mission","navigation","verification","retry","reconciliation","attempts","identity","idempotency"):
        if k in row:
            result[k] = row[k]
    return result

ap = argparse.ArgumentParser()
ap.add_argument("evidence")
ap.add_argument("scenario", nargs="?")
ap.add_argument("--list", action="store_true")
ap.add_argument("--full", action="store_true")
args = ap.parse_args()

p = Path(args.evidence)
if not p.is_file():
    sys.exit(f"Evidence not found: {p}")
data = json.loads(p.read_text())
scenarios = find_scenarios(data)

if args.list:
    for name in sorted(scenarios):
        r = scenarios[name]
        print(f"{name:32} layer={r.get('layer','?'):8} expected={r.get('expected_decision','?'):12} decision={r.get('decision','?')}")
    sys.exit(0)

if not args.scenario:
    sys.exit("scenario is required unless --list is used")
if args.scenario not in scenarios:
    print("Available scenario IDs:", file=sys.stderr)
    for name in sorted(scenarios):
        print("  " + name, file=sys.stderr)
    sys.exit(f"Scenario not found: {args.scenario}")

row = scenarios[args.scenario]
print(json.dumps(row if args.full else compact(row), indent=2, ensure_ascii=False))
