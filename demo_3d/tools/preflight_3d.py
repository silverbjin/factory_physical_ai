#!/usr/bin/env python3
import subprocess

from demo3d_common import *

root = repo_root()
print(f"[3D PREFLIGHT] repo={root}")

for rel in [
    "results/reviews/SIM-008_acceptance.json",
    "results/reviews/SIM-009_acceptance.json",
    "results/reviews/SIM-010_acceptance.json",
    "results/reviews/SIM-E2E_acceptance.json",
    "results/simulation/SIM-009_failure_recovery.json",
    "scripts/verify_simulation_e2e_qualification.py",
]:
    p = root / rel
    if not p.exists():
        raise SystemExit(f"[FAIL] missing: {rel}")

dirty = subprocess.run(
    [
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain",
        "--",
        "results/simulation",
        "results/reviews",
    ],
    capture_output=True,
    text=True,
).stdout.strip()
if dirty:
    print(dirty)
    raise SystemExit("[FAIL] canonical results tree is dirty.")

nr = normal_runner(root)
fr = failure_runner(root)
world = resolve_world(root)
cli = gazebo_cli()

print(f"[3D PREFLIGHT] normal runner={nr.relative_to(root)}")
print(
    "[3D PREFLIGHT] SIM-008 Evidence="
    f"{accepted_sim008(root).relative_to(root)}"
)
print(
    "[3D PREFLIGHT] Gazebo CLI="
    f"{' '.join(cli or []) or 'NOT FOUND'}"
)
print(
    "[3D PREFLIGHT] world="
    f"{world.relative_to(root) if world and str(world).startswith(str(root)) else world or 'UNRESOLVED'}"
)
print(f"[3D PREFLIGHT] failure runner={fr.relative_to(root)}")
print(
    "[3D PREFLIGHT] failure output="
    f"{'--output' if has_flag(fr, '--output') else 'isolated-worktree fallback'}"
)
print(
    "[3D PREFLIGHT] scenario filter="
    f"{has_flag(fr, '--scenario', '--scenario-id', '--only') or 'NOT EXPOSED (full suite fallback)'}"
)
print(
    "[3D PREFLIGHT] GUI attach="
    "runner-owned Gazebo server auto-discovery"
)

wrapper = root / "demo_3d/bin/gz"
print(
    "[3D PREFLIGHT] visual gz wrapper="
    f"{wrapper.relative_to(root) if wrapper.exists() else 'MISSING'}"
)
print(
    "[3D PREFLIGHT] scene broadcaster injection="
    "TEMP_RUNTIME_SDF_ONLY"
)
if not wrapper.exists():
    raise SystemExit("[FAIL] demo visual gz wrapper missing.")
print(
    "[3D PREFLIGHT] discovery timeout="
    f"{os.environ.get('DEMO_GZ_DISCOVERY_TIMEOUT', '20')}s"
)

if not cli:
    raise SystemExit("[FAIL] Gazebo CLI not found.")

print("[3D PREFLIGHT] PASS")
