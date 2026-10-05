"""Behavior tests for an explicitly reviewed additive qualification chain."""
from pathlib import Path
import hashlib
import json
import subprocess

from scripts import verify_simulation_e2e_qualification as legacy
from test_simulation_e2e_qualification import _fixture, _sha


def _successor(root: Path):
    _fixture(root)
    ep = root / 'results/simulation/SIM-007.json'
    old = json.loads(ep.read_text()); old['task_specific_result'] = 'SIM_MISSION_INTEGRATION_BLOCKED'; ep.write_text(json.dumps(old))
    ap = root / 'results/reviews/SIM-007_acceptance.json'
    a = json.loads(ap.read_text()); a['evidence']['sha256'] = _sha(ep); ap.write_text(json.dumps(a))
    ip = root / 'results/simulation/SIM-010_observability_regression.json'
    idx = json.loads(ip.read_text()); idx.pop('predicate_sources')
    row = next(r for r in idx['accepted_source_index'] if r['short_task_id'] == 'SIM-007')
    row.update(acceptance_sha256=_sha(ap), evidence_sha256=_sha(ep)); ip.write_text(json.dumps(idx))
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'config','user.email','test@example.com'],check=True)
    subprocess.run(['git','-C',str(root),'config','user.name','test'],check=True)
    subprocess.run(['git','-C',str(root),'commit','--allow-empty','-qm','candidate'],check=True)
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    cp=root/'configs/simulation/e2e_successor_chain_v1.json';cp.parent.mkdir(parents=True)
    chain={'schema_version':1,'contract_id':'SIM-E2E-SUCCESSOR-V1','successors':{
        task:{'task_id':f'TASK-{task}-R01','evidence_path':f'results/simulation/{task}-R01.json','acceptance_path':f'results/reviews/{task}-R01_acceptance.json'} for task in ('SIM-007','SIM-010')},
        'required_reviewed_paths':['configs/simulation/e2e_successor_chain_v1.json','src/runtime.py']}
    cp.write_text(json.dumps(chain)); (root/'src').mkdir(); (root/'src/runtime.py').write_text('runtime = 1\n')
    seven={'task_id':'TASK-SIM-007-R01','task_specific_result':'SIM_MISSION_INTEGRATION_READY','system_authority':old['system_authority'],'profile_smoke':[]}
    for profile in ('deterministic','navigation_physics','manipulation_physics','system'):
        ident={'mission_id':profile+'-mission','trace_id':profile+'-trace'}
        outcome={'mission':{**ident,'result':'success','status':'completed'},'navigation':{**ident,'action_id':profile+'-nav','result':'success','status':'succeeded'},'vla':{**ident,'action_id':profile+'-vla','result':'success','status':'succeeded'},'verification':{**ident,'action_id':profile+'-vla','result':'success','status':'succeeded','verdict':'pass'}}
        seven['profile_smoke'].append({'profile':profile,'pass':True,'cleanup_complete':True,'bounded':True,'outcome':outcome,'verification_before_completion':True})
    from scripts.run_simulation_forward_profile_qualification import runtime_bound_proof,normalize_run_local_mujoco
    from simulation_runtime.mission_integration import PROFILES
    from simulation_runtime.smoke import canonical_sha256
    from types import SimpleNamespace
    for row in seven['profile_smoke']:
        name=row['profile'];outcome=row['outcome'];row['profile_definition']=PROFILES[name].__dict__
        if name in {'deterministic','navigation_physics'}:
            payload={'quality':'valid','part_id':'brake-ecu-b','location_id':'line-b-drop'};digest=canonical_sha256(payload)
            row['observation_proof']={'source':'deterministic_fixture','payload':payload,'reference':{'content_sha256':digest}}
            outcome['verification']['evidence_refs']=[{'uri':'urn:test:proxy','sha256':digest}]
        if name=='manipulation_physics':
            record={'mission_id':outcome['mission']['mission_id'],'action_id':outcome['vla']['action_id'],'observed_status':'succeeded','recorded_at':'2026-10-05T00:00:00.000Z','component_version':'sim005-mujoco-vla-backend-v1','measurement':{'object_x_after':0.05,'transferred':True,'contact_detected':True,'final_contact':True,'steps':400,'timestep_seconds':0.002}}
            row['navigation_route_scope']={'namespace':'deterministic_fixture','waypoint':'line-b-drop','component_bench_goal':'transfer-zone','global_world_equivalence_claimed':False}
            row['public_requests']={'navigation':{'destination_id':'line-b-drop'},'mission':{'goal':{'part_id':'sim-workpiece','destination_id':'transfer-zone'}},'vla':{'task_id':'mujoco-place-nominal'},'verification':{'expected_state':{'part_id':'sim-workpiece','location_id':'transfer-zone'}}}
            row['observation_proof']={'source':'mujoco_runtime','action_record':record};outcome['vla']['component_version']=record['component_version']
            outcome['verification']['evidence_refs']=[{'uri':'urn:test:mujoco','sha256':normalize_run_local_mujoco(record).reference['content_sha256']}]
        if name in {'navigation_physics','system'}:
            measurements={'owned_stage_durations':[{'stage':stage,'duration_ms':100} for stage in ('start','bootstrap_localization','close')],'executions':[{'action_id':outcome['navigation']['action_id'],'duration_ms':100,'execution_bound_ms':20000,'arrival_verified':True,'observed_status':'succeeded'}],'localization':{'probes':[{'label':'initial_pose_publish','duration_ms':100,'timed_out':False,'configured_operation_bound_ms':5000,'termination_budget_ms':0,'probe_kind':'persistent_request','termination_overhead_ms':0}],'clock_available':True,'map_server_active':True,'amcl_active':True,'map_to_odom_available':True,'initial_pose':{'published':True},'prerequisites':{'map_available':True,'scan_available':True,'odom_available':True,'odom_to_base_available':True}},'cleanup':{'complete':True,'processes':[{'returncode':0}]}}
            if name=='system':
                source={**outcome['navigation'],'action_id':'source-nav'}
                measurements['executions'].append({'action_id':'source-nav','duration_ms':100,'execution_bound_ms':20000,'arrival_verified':True,'observed_status':'succeeded'})
                observations=[{'runtime_backend':'gz_sim_harmonic','snapshot_sha256':'a'*64,'simulation_time':{'sec':1,'nsec':0},'pose':{'x':0,'y':0,'z':0},'semantic_state':{'part_id':'brake-ecu-b','location_id':loc}} for loc in ('warehouse-a','line-b-drop')]
                row['raw_execution']={'mission':outcome['mission'],'lifecycle':{'cleanup_complete':True},'steps':[{'name':'source_navigation','result':source,'request':{'destination_id':'warehouse-a','timeout_ms':20000}},{'name':'source_verification','result':{**outcome['verification'],'action_id':'source-nav'},'observation':observations[0]},{'name':'destination_navigation','result':outcome['navigation'],'request':{'destination_id':'line-b-drop','timeout_ms':20000}},{'name':'vla.execute','result':outcome['vla']},{'name':'final_verification','result':outcome['verification'],'observation':observations[1]}]}
                measurements['world_state']=[{'returncode':0,'command':['gz','service']}]
            row['public_requests']={'navigation':{'timeout_ms':20000}}
            row['runtime_measurements']=measurements
            row['operation_bound_proof']=runtime_bound_proof(SimpleNamespace(bounds=SimpleNamespace(startup_seconds=45 if name=='navigation_physics' else 20,localization_seconds=30,execution_seconds=30 if name=='navigation_physics' else 20,cleanup_seconds=5),measurements=measurements))
    for row in seven['profile_smoke']:
        outcome=row['outcome'];requests=row.setdefault('public_requests',{})
        for key,operation in (('mission','mission.execute'),('navigation','navigation.execute'),('vla','vla.execute'),('verification','verification.verify')):
            result=outcome[key];result.update(operation=operation,request_id=row['profile']+'-'+key+'-request',timestamp='2026-10-05T00:00:02Z' if key=='mission' else '2026-10-05T00:00:01Z')
            request=requests.setdefault(key,{})
            request.update(operation=operation,request_id=result['request_id'],mission_id=result['mission_id'],trace_id=result['trace_id'],timestamp='2026-10-05T00:00:00Z',deadline_at='2026-10-05T00:00:30Z',timeout_ms=20000)
            if key!='mission':request['action_id']=result['action_id']
        requests['navigation'].setdefault('destination_id','line-b-drop')
        if row['profile'] in {'navigation_physics','system'}:
            for record in row['runtime_measurements']['executions']:record['destination_id']='warehouse-a' if record['action_id']=='source-nav' else 'line-b-drop'
        if row['profile']=='navigation_physics':
            record=row['runtime_measurements']['executions'][0];uuid='a'*32
            events=[{'event':event,'monotonic_ns':index*1000000} for index,event in enumerate(('action_server_wait','action_server_ready','goal_send','goal_response','goal_terminal'))]
            events[3].update(accepted=True,goal_uuid=uuid);events[4].update(goal_uuid=uuid,status=4,error_code=0)
            record.update(client='persistent_canonical_action',client_response={'request_identity':{key:requests['navigation'][key] for key in ('mission_id','trace_id','request_id','action_id')},'ok':True,'terminal_status':4,'error_code':0,'goal_uuid':uuid,'events':events})
        if row['profile']=='system':
            raw=row['raw_execution'];raw['mission_request']=requests['mission'];source_nav=raw['steps'][0]['result'];source_nav.update(operation='navigation.execute',request_id='source-nav-request',timestamp='2026-10-05T00:00:01Z')
            source_request={**requests['navigation'],'action_id':'source-nav','request_id':'source-nav-request','destination_id':'warehouse-a'};requests['source_navigation']=source_request;raw['steps'][0]['request']=source_request;raw['steps'][2]['request']=requests['navigation']
            for step,key in ((raw['steps'][1],'source_verification'),(raw['steps'][4],'verification')):
                expected=step['observation']['semantic_state'];step['expected_state']=expected;result=step['result'];result.update(operation='verification.verify',request_id=key+'-request',timestamp='2026-10-05T00:00:01Z',evidence_refs=[{'uri':'urn:test:world','sha256':canonical_sha256({'quality':'valid',**expected})}])
                requests[key]={**requests['verification'],'action_id':result['action_id'],'request_id':result['request_id'],'expected_state':expected}
    ten=json.loads((root/'results/simulation/SIM-010.json').read_text());ten['task_id']='TASK-SIM-010-R01';ten['predicate_sources']={name:owner for name,(owner,_) in legacy.PREDICATES.items()};ten['historical_bindings']={task:{'acceptance_sha256':_sha(root/f'results/reviews/{task}_acceptance.json'),'evidence_path':f'results/simulation/{task}.json','evidence_sha256':_sha(root/f'results/simulation/{task}.json'),'accepted_commit':json.loads((root/f'results/reviews/{task}_acceptance.json').read_text())['accepted_commit']} for task in legacy.TASKS}
    stdout=root/'results/simulation/regression_stdout.log';stderr=root/'results/simulation/regression_stderr.log';stdout.write_text('26 passed in 1.00s\n');stderr.write_text('')
    ten['full_repository_regression']={'gate_result':'PASS','returncode':0,'command':['python','-m','pytest','-q','-p','no:cacheprovider'],'stdout_path':str(stdout.relative_to(root)),'stdout_sha256':_sha(stdout),'stderr_path':str(stderr.relative_to(root)),'stderr_sha256':_sha(stderr)}
    for task,payload in [('SIM-007',seven),('SIM-010',ten)]:
        if task=='SIM-010':payload['fresh_mission_integration_binding']={'task_id':'TASK-SIM-007-R01','evidence_path':chain['successors']['SIM-007']['evidence_path'],'evidence_sha256':_sha(root/chain['successors']['SIM-007']['evidence_path'])}
        manifest={path:_sha(root/path) for path in chain['required_reviewed_paths']}
        payload.update(execution_source_manifest=manifest,source_candidate_head=head,source_manifest_stable=True)
        ep=root/chain['successors'][task]['evidence_path'];ep.write_text(json.dumps(payload))
        acceptance={'schema_version':1,'task_id':payload['task_id'],'status':'ACCEPT','review_mode':'independent_candidate_manifest','reviewed_candidate_head':head,'reviewer_id':'independent-review','reviewed_source_manifest':manifest,'evidence':{'path':str(ep.relative_to(root)),'sha256':_sha(ep)}}
        (root/chain['successors'][task]['acceptance_path']).write_text(json.dumps(acceptance))
    return chain


def _evaluate(root):
    fn=getattr(legacy,'evaluate_current',None)
    assert callable(fn), 'additive successor evaluator is not implemented'
    return fn(root)


def test_reviewed_additive_chain_qualifies_while_history_stays_blocked(tmp_path):
    _successor(tmp_path)
    before={str(p):p.read_bytes() for p in (tmp_path/'results/reviews').glob('SIM-*_acceptance.json') if '-R01' not in p.name}
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_QUALIFIED'
    assert legacy.evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'
    assert all(Path(path).read_bytes()==data for path,data in before.items())


def test_missing_independent_review_does_not_qualify(tmp_path):
    chain=_successor(tmp_path);(tmp_path/chain['successors']['SIM-007']['acceptance_path']).unlink()
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_reviewed_source_mutation_does_not_qualify(tmp_path):
    _successor(tmp_path);(tmp_path/'src/runtime.py').write_text('runtime = 2\n')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_successor_payload_tamper_does_not_qualify(tmp_path):
    chain=_successor(tmp_path);(tmp_path/chain['successors']['SIM-007']['evidence_path']).write_text('{}')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_new_chain_still_requires_every_profile_success(tmp_path):
    chain=_successor(tmp_path);p=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(p.read_text());d['profile_smoke'][2]['outcome']['verification']['verdict']='uncertain';p.write_text(json.dumps(d))
    a=tmp_path/chain['successors']['SIM-007']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_ownership_index_remains_mandatory(tmp_path):
    chain=_successor(tmp_path);p=tmp_path/chain['successors']['SIM-010']['evidence_path'];d=json.loads(p.read_text());d['predicate_sources'].pop('normal_system_e2e');p.write_text(json.dumps(d))
    a=tmp_path/chain['successors']['SIM-010']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_execution_manifest_cannot_be_backfilled_after_source_change(tmp_path):
    chain=_successor(tmp_path)
    p=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(p.read_text());d['execution_source_manifest']={'src/runtime.py':'0'*64};p.write_text(json.dumps(d))
    a=tmp_path/chain['successors']['SIM-007']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_new_source_file_invalidates_complete_review_identity(tmp_path):
    _successor(tmp_path);(tmp_path/'src/new_runtime.py').write_text('new = 1\n')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_successor_index_cannot_bind_different_mission_evidence(tmp_path):
    chain=_successor(tmp_path);p=tmp_path/chain['successors']['SIM-010']['evidence_path'];d=json.loads(p.read_text());d['fresh_mission_integration_binding']={'task_id':'TASK-SIM-007-R01','evidence_path':chain['successors']['SIM-007']['evidence_path'],'evidence_sha256':'0'*64};p.write_text(json.dumps(d))
    a=tmp_path/chain['successors']['SIM-010']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_head_advance_invalidates_review_even_when_sources_unchanged(tmp_path):
    _successor(tmp_path)
    subprocess.run(['git','-C',str(tmp_path),'commit','--allow-empty','-qm','advanced head'],check=True)
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_four_success_flags_without_backend_proof_do_not_qualify(tmp_path):
    chain=_successor(tmp_path);p=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(p.read_text())
    for row in d['profile_smoke']:
        for key in ('runtime_measurements','observation_proof','raw_execution','operation_bound_proof','profile_definition'):row.pop(key,None)
    p.write_text(json.dumps(d));a=tmp_path/chain['successors']['SIM-007']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_regression_pass_string_cannot_replace_execution_logs(tmp_path):
    chain=_successor(tmp_path);p=tmp_path/chain['successors']['SIM-010']['evidence_path'];d=json.loads(p.read_text());d['full_repository_regression']={'gate_result':'PASS'};p.write_text(json.dumps(d))
    a=tmp_path/chain['successors']['SIM-010']['acceptance_path'];d=json.loads(a.read_text());d['evidence']['sha256']=_sha(p);a.write_text(json.dumps(d))
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def _rebind_successor_chain(root,chain,owner):
    ep=root/chain['successors'][owner]['evidence_path'];ap=root/chain['successors'][owner]['acceptance_path'];a=json.loads(ap.read_text());a['evidence']['sha256']=_sha(ep);ap.write_text(json.dumps(a))
    if owner=='SIM-007':
        ip=root/chain['successors']['SIM-010']['evidence_path'];i=json.loads(ip.read_text());i['fresh_mission_integration_binding']['evidence_sha256']=_sha(ep);ip.write_text(json.dumps(i));_rebind_successor_chain(root,chain,'SIM-010')


def test_verification_after_mission_completion_is_not_ready(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text());row=d['profile_smoke'][0];row['outcome']['mission']['timestamp']='2026-10-05T00:00:01Z';row['outcome']['verification']['timestamp']='2026-10-05T00:00:02Z';ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_execution_destination_must_match_its_public_navigation_request(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text());row=d['profile_smoke'][1];row['runtime_measurements']['executions'][0]['destination_id']='other-waypoint';ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_system_source_verification_trace_cannot_change(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text());row=d['profile_smoke'][3];row['raw_execution']['steps'][1]['result']['trace_id']='other-trace';ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_source_navigation_must_belong_to_current_mission(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text());row=d['profile_smoke'][3]
    row['public_requests']['source_navigation']['mission_id']='another-mission';row['raw_execution']['steps'][0]['result']['mission_id']='another-mission'
    ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_navigation_after_mission_completion_is_not_ready(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text());d['profile_smoke'][0]['outcome']['navigation']['timestamp']='2026-10-05T00:00:03Z'
    ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'


def test_system_source_navigation_failure_cannot_complete_mission(tmp_path):
    chain=_successor(tmp_path);ep=tmp_path/chain['successors']['SIM-007']['evidence_path'];d=json.loads(ep.read_text())
    step=d['profile_smoke'][3]['raw_execution']['steps'][0]['result'];step.update(result='failure',status='failed')
    ep.write_text(json.dumps(d));_rebind_successor_chain(tmp_path,chain,'SIM-007')
    assert _evaluate(tmp_path)['decision']=='SIM_E2E_NOT_QUALIFIED'
