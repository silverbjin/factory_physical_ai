#!/usr/bin/env python3
"""Read-only preflight; never execute mission runners to discover CLI flags."""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from demo3d_common import repo_root, gazebo_cli, gazebo_server_snapshots
from verified_normal import alive
import json

root=repo_root()
for rel in ['scripts/run_simulation_normal_system_e2e.py','data/simulation/sim008_normal_system_world.sdf',
            'results/simulation/SIM-008_normal_system_e2e.json','results/reviews/SIM-008_acceptance.json',
            'results/simulation/SIM-009_failure_recovery.json','scripts/verify_simulation_e2e_qualification.py']:
    if not (root/rel).is_file():raise SystemExit('[FAIL] missing: '+rel)
status=subprocess.check_output(['git','-C',str(root),'status','--short','--','data/simulation','results/simulation','results/reviews'],text=True)
if status.strip():raise SystemExit('[FAIL] protected canonical tree is dirty:\n'+status)
if not gazebo_cli():raise SystemExit('[FAIL] gz sim unavailable')
if not Path('/opt/ros/jazzy/bin/xacro').is_file():raise SystemExit('[FAIL] installed xacro unavailable')
example=Path('/opt/ros/jazzy/share/ros_gz_sim_demos/worlds/default.sdf')
plugin=next(p for p in ET.parse(example).getroot().find('world').findall('plugin') if p.get('name','').endswith('SceneBroadcaster'))
print('[3D PREFLIGHT] installed SceneBroadcaster:',plugin.attrib)
if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):raise SystemExit('[FAIL] no GUI display')
for rel in ['results/demo/latest_validation/01_processes.txt','results/demo/final_validation/01_processes.txt']:
    path=root/rel
    if path.is_file():
        stale=[r['pid'] for r in json.loads(path.read_text()) if alive(r)]
        if stale:raise SystemExit('[FAIL] previously owned processes still live: '+str(stale))
print('[3D PREFLIGHT] pre-existing servers (left untouched):',list(gazebo_server_snapshots()))
print('[3D PREFLIGHT] authority: headless-xacro-resolved demo worktree -> unchanged Nav2 launch -> actual runtime SDF -> exact GUI transport')
print('[3D PREFLIGHT] protected canonical tree clean; no stale recorded owned processes')
print('[3D PREFLIGHT] PASS')
