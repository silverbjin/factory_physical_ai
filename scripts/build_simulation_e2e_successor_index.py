#!/usr/bin/env python3
"""Reconstruct a new canonical source index; never rewrite historical SIM010."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.verify_simulation_e2e_qualification import evaluate,PREDICATES
from scripts.run_simulation_forward_profile_qualification import candidate_manifest
from scripts.simulation_e2e_successor import sha256,profiles_valid
from simulation_runtime.observability_regression import build_regression_evidence


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--python',required=True,type=Path);parser.add_argument('--output',type=Path,default=ROOT/'results/simulation/SIM-010-R01_observability_regression.json');args=parser.parse_args()
    before=candidate_manifest();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    historical=evaluate(ROOT)
    normalized=build_regression_evidence(ROOT)
    command=[str(args.python),'-m','pytest','-q','-p','no:cacheprovider']
    regression_environment=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join(filter(None,(str(ROOT/'src'),os.environ.get('PYTHONPATH'))))}
    regression=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=regression_environment)
    log_root=args.output.parent/(args.output.stem+'_logs');log_root.mkdir(parents=True,exist_ok=True)
    stdout=log_root/'pytest_stdout.log';stderr=log_root/'pytest_stderr.log';stdout.write_text(regression.stdout);stderr.write_text(regression.stderr)
    after=candidate_manifest();stable=before==after
    seven=json.loads((ROOT/'results/simulation/SIM-007-R01_mission_integration.json').read_text())
    ready=(normalized['task_specific_result']=='SIM_OBSERVABILITY_REGRESSION_READY' and regression.returncode==0 and stable and seven.get('task_specific_result')=='SIM_MISSION_INTEGRATION_READY' and profiles_valid(seven) and not [x for x in historical['failures'] if x!='SIM-007: required READY result not proven'])
    payload={**normalized,'task_id':'TASK-SIM-010-R01','task_specific_result':'SIM_OBSERVABILITY_REGRESSION_READY' if ready else 'SIM_OBSERVABILITY_REGRESSION_BLOCKED','generated_at':datetime.now(timezone.utc).isoformat(),'source_candidate_head':head,'execution_source_manifest':before,'source_manifest_stable':stable,'predicate_sources':{name:owner for name,(owner,_) in PREDICATES.items()},'historical_bindings':{owner:{'acceptance_sha256':sha256(ROOT/row['acceptance_path']),'evidence_path':row['evidence_path'],'evidence_sha256':row['evidence_sha256'],'accepted_commit':row['reviewed_revision']} for owner,row in historical['predecessors'].items()},'fresh_mission_integration_binding':{'task_id':'TASK-SIM-007-R01','evidence_path':'results/simulation/SIM-007-R01_mission_integration.json','evidence_sha256':sha256(ROOT/'results/simulation/SIM-007-R01_mission_integration.json')},'full_repository_regression':{'gate_result':'PASS' if regression.returncode==0 else 'BLOCKED','command':command,'returncode':regression.returncode,'stdout_path':str(stdout.relative_to(ROOT)),'stdout_sha256':sha256(stdout),'stderr_path':str(stderr.relative_to(ROOT)),'stderr_sha256':sha256(stderr)},'physical_dependency':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(payload['task_specific_result']);return 0 if ready else 1

if __name__=='__main__':raise SystemExit(main())
