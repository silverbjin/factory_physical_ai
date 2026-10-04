#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
from demo3d_common import *

root=repo_root()
print(f"[3D PREFLIGHT] repo={root}")
for rel in [
    "results/reviews/SIM-008_acceptance.json",
    "results/reviews/SIM-009_acceptance.json",
    "results/reviews/SIM-010_acceptance.json",
    "results/reviews/SIM-E2E_acceptance.json",
    "results/simulation/SIM-009_failure_recovery.json",
    "scripts/verify_simulation_e2e_qualification.py",
]:
    p=root/rel
    if not p.exists():
        raise SystemExit(f"[FAIL] missing: {rel}")

dirty=subprocess.run(["git","-C",str(root),"status","--porcelain","--","results/simulation","results/reviews"],
                     capture_output=True,text=True).stdout.strip()
if dirty:
    print(dirty)
    raise SystemExit("[FAIL] canonical results tree is dirty.")

print(f"[3D PREFLIGHT] normal runner={normal_runner(root).relative_to(root)}")
print(f"[3D PREFLIGHT] SIM-008 Evidence={accepted_sim008(root).relative_to(root)}")
print(f"[3D PREFLIGHT] Gazebo CLI={' '.join(gazebo_cli() or []) or 'NOT FOUND'}")
world=resolve_world(root)
print(f"[3D PREFLIGHT] world={world.relative_to(root) if world and str(world).startswith(str(root)) else world or 'UNRESOLVED'}")
fr=failure_runner(root)
print(f"[3D PREFLIGHT] failure runner={fr.relative_to(root)}")
print(f"[3D PREFLIGHT] scenario filter={has_flag(fr,'--scenario','--scenario-id','--only') or 'NOT EXPOSED (full suite fallback)'}")
print("[3D PREFLIGHT] PASS")
