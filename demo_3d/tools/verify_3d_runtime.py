"""Recheck the currently owned Normal demo server, or inspect completed proof."""
import argparse
import json
import re
import os
import subprocess
from pathlib import Path
from verified_normal import alive, SERVICE, ENTITY, command
import demo3d_common as c

parser=argparse.ArgumentParser()
parser.add_argument('--validation-dir',type=Path,default=c.repo_root()/'results/demo/latest_validation')
args=parser.parse_args()
path=args.validation_dir
manifest_path=path/'invocation.json'
if not manifest_path.is_file():
    raise SystemExit('FAIL: proof has no invocation metadata')
manifest=json.loads(manifest_path.read_text())
if manifest['state']=='failed':
    raise SystemExit('FAIL: this invocation failed')
if not (path/'runtime_identity.json').is_file():
    raise SystemExit('FAIL: invocation has no runtime identity yet')
pairs=json.loads((path/'runtime_identity.json').read_text())
pair=pairs[-1]
if alive(pair['server']) and alive(pair['gui']):
    server=c._read_proc_environ(pair['server']['pid']);gui=c._read_proc_environ(pair['gui']['pid'])
    cli=__import__('shutil').which('gz',path=server['PATH'])
    rc,response=command([cli,'service','-s',SERVICE,'--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Scene','--timeout','3000','--req',''],server)
    world_rc,world_response=command([cli,'service','-s','/gazebo/worlds','--reqtype','gz.msgs.Empty','--reptype','gz.msgs.StringMsg_V','--timeout','3000','--req',''],server)
    world_ok=world_rc==0 and 'data: "sim008_normal_system_world"' in world_response
    (path/'live_world_response.txt').write_text(world_response)
    (path/'world_validation.json').write_text(json.dumps({'service':'/gazebo/worlds','server_pid':pair['server']['pid'],'partition':server['GZ_PARTITION'],'response':world_response,'pass':world_ok},indent=2)+'\n')
    (path/'live_scene_recheck.txt').write_text(response)
    (path/'live_scene_recheck.json').write_text(json.dumps({'model_count':len(re.findall(r'^\s*model \{',response,re.M)),'expected_entity_present':ENTITY in response,'server_pid':pair['server']['pid']},indent=2)+'\n')
    passed=rc==0 and ENTITY in response and world_ok and c.transport_matches(server,gui)
    print('LIVE_RUNTIME_PASS' if passed else 'LIVE_RUNTIME_FAIL')
else:
    if manifest['state']!='complete':
        raise SystemExit('FAIL: invocation is incomplete; prior success is not reusable')
    gates=json.loads((path/'gates.json').read_text())
    passed=all(gates.values())
    print('COMPLETED_RUN_PROOF_PASS (owned runtime has been cleaned)' if passed else 'COMPLETED_RUN_PROOF_FAIL')
raise SystemExit(0 if passed else 1)
