#!/usr/bin/env python3
import argparse,json,time,os
from pathlib import Path
S={
'normal':['Mission Request','Navigation','Navigation Completed','Manipulation / VLA','Verification','Verification PASS','Mission Completed'],
'nav_timeout':['Attempt #1','Navigation Timeout','UNKNOWN','Authoritative Reconciliation','Retry Authorized','Attempt #2','Bounded Outcome'],
'verify_uncertain':['Observation Received','Verification','UNCERTAIN','No Auto-Success','RECONCILE','Mission Reconciling'],
'qualification':['Acceptance Chain','Evidence Hash / Revision','SIM-010 Source Index','Predicate Reconstruction','Authorization Boundary','SIM_E2E_QUALIFIED']}
ap=argparse.ArgumentParser();ap.add_argument('scenario',choices=S);ap.add_argument('--repo-root',default=os.environ.get('REPO_ROOT') or '.');ap.add_argument('--delay',type=float,default=.9);a=ap.parse_args()
out=Path(a.repo_root).resolve()/'results/demo/visual_replay_state.json';out.parent.mkdir(parents=True,exist_ok=True)
for i,label in enumerate(S[a.scenario]):
    state='warning' if label in ('Navigation Timeout','UNKNOWN','UNCERTAIN','No Auto-Success') else ('active' if i<len(S[a.scenario])-1 else 'completed')
    p={'active':True,'scenario':a.scenario,'index':i,'total':len(S[a.scenario]),'label':label,'state':state};out.write_text(json.dumps(p,indent=2));print('[REPLAY]',label);time.sleep(a.delay)
p['active']=False;p['finished']=True;out.write_text(json.dumps(p,indent=2));print('[REPLAY] complete')
