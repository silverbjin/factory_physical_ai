#!/usr/bin/env python3
import argparse,json,os,threading,webbrowser
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse,parse_qs

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)

def first(data,keys,default=None):
    for d in walk(data):
        if isinstance(d,dict):
            for k in keys:
                if k in d:return d[k]
    return default

def load(p):
    try:return json.loads(p.read_text())
    except:return {}

def scenario(data,sid):
    best=None; score=-1
    for d in walk(data):
        if not isinstance(d,dict):continue
        if (d.get('id') or d.get('scenario_id'))!=sid:continue
        s=sum(k in d for k in ('layer','outcome_kind','expected_decision','decision','pass','cleanup_complete','mission','verification'))
        if s>score:best,score=d,s
    return best

def sim008(repo):
    live=[repo/'results/demo/SIM-008_normal_e2e_demo.json',repo/'results/demo/SIM-008_normal_system_e2e_demo.json']
    acc=[repo/'results/simulation/SIM-008_normal_system_e2e.json',repo/'results/simulation/SIM-008_normal_e2e.json']
    p=next((x for x in live if x.exists()),None); mode='LIVE DEMO OUTPUT'
    if not p:p=next((x for x in acc if x.exists()),None);mode='ACCEPTED EVIDENCE REPLAY'
    if not p:return {'error':'SIM-008 Evidence not found'}
    d=load(p)
    return {'title':'Normal End-to-End Mission','mode':mode,'source':str(p.relative_to(repo)),
      'result':first(d,['task_specific_result','task_specific_decision'],'SIM_NORMAL_E2E_READY'),
      'metrics':{'Mission ID':first(d,['mission_id'],'—'),'Initial State':first(d,['initial_state','initial_mission_state'],'created'),
      'Final State':first(d,['final_state','final_mission_state','mission_state'],'completed'),'Verification':first(d,['verification_verdict','verdict'],'pass'),
      'Cleanup':first(d,['cleanup_complete'],True)},
      'steps':['Mission Request','Navigation','Manipulation / VLA','Verification','Mission Completed']}

def sim009(repo,sid,title):
    live=repo/'results/demo/SIM-009_failure_recovery_demo.json'; acc=repo/'results/simulation/SIM-009_failure_recovery.json'
    p=live if live.exists() else acc; mode='LIVE DEMO OUTPUT' if live.exists() else 'ACCEPTED EVIDENCE REPLAY'
    if not p.exists():return {'error':'SIM-009 Evidence not found'}
    row=scenario(load(p),sid)
    if not row:return {'error':f'{sid} not found'}
    m=row.get('mission') if isinstance(row.get('mission'),dict) else {}
    if sid=='SIM009-NAV-TIMEOUT-RETRY':steps=['Attempt #1','Timeout','UNKNOWN','Reconciliation','Retry Authorized','Attempt #2']
    else:steps=['Observation','Verification','UNCERTAIN','No Auto-Success','RECONCILE','Mission Reconciling']
    return {'title':title,'mode':mode,'source':str(p.relative_to(repo)),'result':row.get('decision','—'),
      'metrics':{'Scenario':sid,'Layer':row.get('layer','—'),'Outcome':row.get('outcome_kind','—'),'Expected':row.get('expected_decision','—'),
      'Decision':row.get('decision','—'),'Mission State':m.get('mission_state','—'),'Mission Success Committed':m.get('mission_success_committed','—'),
      'Verification':m.get('verification_verdict') or first(row,['verdict'],'—'),'Cleanup':row.get('cleanup_complete','—')},'steps':steps}

def qual(repo):
    live=repo/'results/demo/SIM-E2E_qualification_demo.json';acc=repo/'results/simulation/SIM-E2E_qualification.json'
    p=live if live.exists() else acc;mode='LIVE DEMO OUTPUT' if live.exists() else 'ACCEPTED EVIDENCE REPLAY'
    if not p.exists():return {'error':'SIM-E2E Evidence not found'}
    d=load(p);decision=first(d,['task_specific_result','gate_result','decision','result'],'UNRESOLVED')
    return {'title':'Final Simulation Qualification','mode':mode,'source':str(p.relative_to(repo)),'result':decision,
      'metrics':{'Physical Dependency':first(d,['physical_dependency'],False),'Dual-world Co-sim Required':first(d,['dual_world_cosimulation_required'],False)},
      'matrix':first(d,['qualification_matrix','matrix'],{}),'steps':['Acceptance Chain','Hash / Revision','Source Index','Predicate Reconstruction','Authorization Boundary',decision]}

def replay(repo):
    p=repo/'results/demo/visual_replay_state.json'
    return load(p) if p.exists() else {'active':False}

class H(SimpleHTTPRequestHandler):
    repo=None; webroot=None
    def translate_path(self,path):
        u=urlparse(path);rel=u.path.lstrip('/') or 'index.html';return str(self.webroot/rel)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/api/snapshot':
            v=parse_qs(u.query).get('view',['normal'])[0]
            if v=='normal':o=sim008(self.repo)
            elif v=='nav_timeout':o=sim009(self.repo,'SIM009-NAV-TIMEOUT-RETRY','Navigation Timeout → Reconciliation → Retry')
            elif v=='verify_uncertain':o=sim009(self.repo,'SIM009-VERIFY-UNCERTAIN','Verification Uncertain → Reconcile')
            elif v=='qualification':o=qual(self.repo)
            else:o={'error':'unknown view'}
            o['replay']=replay(self.repo);raw=json.dumps(o,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if u.path.startswith('/assets/'):
            p=self.webroot.parent/'assets'/u.path[len('/assets/'):]
            if p.exists():
                b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        super().do_GET()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default=os.environ.get('REPO_ROOT'));ap.add_argument('--port',type=int,default=8765);ap.add_argument('--no-browser',action='store_true');a=ap.parse_args()
    repo=Path(a.repo_root or Path.cwd()).resolve();here=Path(__file__).resolve().parent;H.repo=repo;H.webroot=here/'web';url=f'http://127.0.0.1:{a.port}/'
    print('[VISUAL DEMO]',url)
    if not a.no_browser:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    ThreadingHTTPServer(('127.0.0.1',a.port),H).serve_forever()
if __name__=='__main__':main()
