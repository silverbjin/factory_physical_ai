"""Explicit additive E2E chain, independently reviewed by candidate/source identity.

Historical acceptances remain historical. Candidate-manifest acceptance is a new
contract and never represents dirty files as accepted Git blobs.
"""
from __future__ import annotations
import json
import re
from datetime import datetime
import subprocess
from pathlib import Path
from typing import Any
from scripts.verify_simulation_e2e_qualification import PREDICATES, TASKS, evaluate, read_json, sha256, evidence_result

REGISTRY = 'configs/simulation/e2e_successor_chain_v1.json'
PROFILE_NAMES = {'deterministic', 'navigation_physics', 'manipulation_physics', 'system'}


def safe_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('artifact path must be repository-relative')
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('artifact path escapes repository')
    return result


def review_binding(root: Path, route: dict[str, Any], required: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    acceptance = read_json(safe_path(root, route['acceptance_path']))
    if (acceptance.get('task_id') != route['task_id'] or acceptance.get('status') != 'ACCEPT'
        or acceptance.get('review_mode') != 'independent_candidate_manifest'
        or not isinstance(acceptance.get('reviewer_id'), str) or not acceptance['reviewer_id'].strip()):
        raise ValueError('missing independent successor ACCEPT')
    head = acceptance.get('reviewed_candidate_head')
    if not isinstance(head, str) or len(head) != 40:
        raise ValueError('missing reviewed candidate HEAD')
    exists = subprocess.run(['git','cat-file','-e',f'{head}^{{commit}}'],cwd=root,capture_output=True)
    current = subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True)
    if exists.returncode or current.returncode or current.stdout.strip()!=head:
        raise ValueError('reviewed candidate HEAD differs from exact current HEAD')
    manifest = acceptance.get('reviewed_source_manifest')
    if not isinstance(manifest, dict) or not required <= set(manifest):
        raise ValueError('incomplete reviewed source/config manifest')
    present = {str(p.relative_to(root)) for directory in ('src','scripts','config','configs','data/simulation','docs/contracts','tests') for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}}
    if set(manifest) != present:
        raise ValueError('review manifest does not cover the complete current source/config tree')
    for path, digest in manifest.items():
        if not isinstance(digest,str) or len(digest)!=64 or sha256(safe_path(root,path))!=digest:
            raise ValueError(f'reviewed source/config hash mismatch: {path}')
    binding=acceptance.get('evidence')
    if not isinstance(binding,dict) or binding.get('path') != route['evidence_path']:
        raise ValueError('successor Evidence path mismatch')
    evidence_path=safe_path(root,binding['path'])
    if sha256(evidence_path)!=binding.get('sha256'):
        raise ValueError('successor Evidence hash mismatch')
    evidence=read_json(evidence_path)
    if evidence.get('execution_source_manifest') != manifest or evidence.get('source_candidate_head') != head or evidence.get('source_manifest_stable') is not True:
        raise ValueError('execution source identity differs from reviewed candidate')
    if evidence.get('task_id')!=route['task_id']:
        raise ValueError('successor Evidence task identity mismatch')
    return evidence, acceptance


def profile_backend_proof(row: dict[str,Any]) -> bool:
    """Require the actual backend records behind a profile's success envelope."""
    from scripts.run_simulation_forward_profile_qualification import runtime_bound_proof,normalize_run_local_mujoco
    from simulation_runtime.mission_integration import PROFILES
    from types import SimpleNamespace
    name=row.get('profile');outcome=row.get('outcome',{})
    if name not in PROFILES or row.get('profile_definition')!=PROFILES[name].__dict__:
        return False
    if name in {'navigation_physics','system'}:
        measurements=row.get('runtime_measurements');proof=row.get('operation_bound_proof')
        if not isinstance(measurements,dict) or not isinstance(proof,dict) or not isinstance(proof.get('context_bounds_seconds'),dict):return False
        bounds=proof['context_bounds_seconds']
        if set(bounds)!={'startup_seconds','localization_seconds','execution_seconds','cleanup_seconds'} or any(not isinstance(value,(int,float)) or value<=0 for value in bounds.values()):return False
        from scripts.run_simulation_navigation import NavigationRuntimeBounds,LOCALIZATION_SECONDS
        defaults=NavigationRuntimeBounds()
        expected_bounds={key:getattr(defaults,key) for key in bounds} if name=='navigation_physics' else {'startup_seconds':20,'localization_seconds':LOCALIZATION_SECONDS,'execution_seconds':20,'cleanup_seconds':5}
        if bounds!=expected_bounds:return False
        reconstructed=runtime_bound_proof(SimpleNamespace(bounds=SimpleNamespace(**bounds),measurements=measurements))
        if reconstructed!=proof or reconstructed['bounded'] is not True:return False
        stages=measurements.get('owned_stage_durations',[])
        if {stage.get('stage') for stage in stages}!={'start','bootstrap_localization','close'}:return False
        loc=measurements.get('localization',{})
        if not all(loc.get(key) is True for key in ('clock_available','map_server_active','amcl_active','map_to_odom_available')) or loc.get('initial_pose',{}).get('published') is not True or not all(loc.get('prerequisites',{}).get(key) is True for key in ('map_available','scan_available','odom_available','odom_to_base_available')):return False
        executed=measurements.get('executions',[])
        required_actions={outcome['navigation']['action_id']}
        requests={}
        if name=='navigation_physics':requests[outcome['navigation']['action_id']]=row.get('public_requests',{}).get('navigation',{})
        if name=='system':
            raw=row.get('raw_execution',{});steps=raw.get('steps',[]);by_name={step.get('name'):step for step in steps if isinstance(step,dict)}
            required={'source_navigation','source_verification','destination_navigation','vla.execute','final_verification'}
            if len(by_name)!=len(steps) or not required<=set(by_name) or raw.get('mission')!=outcome['mission'] or raw.get('lifecycle',{}).get('cleanup_complete') is not True:return False
            if any(by_name[label]['result'].get('result')!='success' or by_name[label]['result'].get('status')!='succeeded' for label in required):return False
            if any(by_name[label].get('result')!=outcome[key] for key,label in (('navigation','destination_navigation'),('vla','vla.execute'),('verification','final_verification'))):return False
            required_actions.add(by_name['source_navigation']['result']['action_id'])
            requests={by_name[label]['result']['action_id']:by_name[label].get('request',{}) for label in ('source_navigation','destination_navigation')}
            source_navigation=by_name['source_navigation']['result']
            if not public_pair_valid(row.get('public_requests',{}).get('source_navigation'),source_navigation,'navigation.execute') or any(source_navigation.get(key)!=outcome['mission'].get(key) for key in ('mission_id','trace_id')):return False
            completed_at=datetime.fromisoformat(outcome['mission']['timestamp'].replace('Z','+00:00'))
            if any(datetime.fromisoformat(by_name[label]['result']['timestamp'].replace('Z','+00:00'))>completed_at for label in required):return False
            for label,nav_label in (('source_verification','source_navigation'),('final_verification','destination_navigation')):
                step=by_name[label];obs=step.get('observation',{});identity=step.get('result',{})
                if obs.get('runtime_backend')!='gz_sim_harmonic' or not isinstance(obs.get('snapshot_sha256'),str) or len(obs['snapshot_sha256'])!=64 or not isinstance(obs.get('simulation_time'),dict) or not isinstance(obs.get('pose'),dict):return False
                from simulation_runtime.smoke import canonical_sha256
                source_key='source_verification' if label=='source_verification' else 'verification'
                request=row.get('public_requests',{}).get(source_key,{})
                if not public_pair_valid(request,identity,'verification.verify') or identity.get('trace_id')!=outcome['mission']['trace_id'] or identity.get('action_id')!=(by_name['source_navigation']['result']['action_id'] if label=='source_verification' else outcome['vla']['action_id']):return False
                expected=step.get('expected_state')
                if expected!=obs.get('semantic_state') or request.get('expected_state')!=expected or not any(reference.get('sha256')==canonical_sha256({'quality':'valid',**obs.get('semantic_state',{})}) for reference in identity.get('evidence_refs',[])):return False
                if obs.get('semantic_state',{}).get('location_id')!=by_name[nav_label].get('request',{}).get('destination_id') or identity.get('verdict')!='pass' or identity.get('mission_id')!=outcome['mission']['mission_id']:return False
            world_states=measurements.get('world_state',[])
            if not world_states or not all(record.get('returncode')==0 for record in world_states):return False
        for record in executed:
            if record.get('action_id') in required_actions:
                request=requests.get(record['action_id'],{})
                if record.get('destination_id')!=request.get('destination_id') or not isinstance(request.get('timeout_ms'),(int,float)) or record.get('execution_bound_ms')!=min(bounds['execution_seconds']*1000,request['timeout_ms']):return False
                if name=='navigation_physics':
                    response=record.get('client_response',{});uuid=response.get('goal_uuid');events=response.get('events',[])
                    if record.get('client')!='persistent_canonical_action' or response.get('request_identity')!={key:request.get(key) for key in ('mission_id','trace_id','request_id','action_id')} or response.get('ok') is not True or response.get('terminal_status')!=4 or response.get('error_code')!=0 or not isinstance(uuid,str) or not re.fullmatch('[0-9a-f]{32}',uuid):return False
                    if [event.get('event') for event in events]!=['action_server_wait','action_server_ready','goal_send','goal_response','goal_terminal'] or events[3].get('accepted') is not True or events[3].get('goal_uuid')!=uuid or events[4].get('goal_uuid')!=uuid or events[4].get('status')!=4 or events[4].get('error_code')!=0:return False
                    times=[event.get('monotonic_ns') for event in events]
                    if any(not isinstance(value,int) for value in times) or times!=sorted(times) or (times[-1]-times[0])/1e6>record['execution_bound_ms']:return False
        if not required_actions <= {record.get('action_id') for record in executed if record.get('arrival_verified') is True and record.get('observed_status')=='succeeded'}:return False
    if name=='manipulation_physics':
        requests=row.get('public_requests',{})
        scope={'namespace':'deterministic_fixture','waypoint':'line-b-drop','component_bench_goal':'transfer-zone','global_world_equivalence_claimed':False}
        if row.get('navigation_route_scope')!=scope or requests.get('navigation',{}).get('destination_id')!='line-b-drop' or requests.get('mission',{}).get('goal',{}).get('part_id')!='sim-workpiece' or requests.get('mission',{}).get('goal',{}).get('destination_id')!='transfer-zone' or requests.get('vla',{}).get('task_id')!='mujoco-place-nominal' or requests.get('verification',{}).get('expected_state')!={'part_id':'sim-workpiece','location_id':'transfer-zone'}:return False
        obs=row.get('observation_proof',{});record=obs.get('action_record')
        if obs.get('source')!='mujoco_runtime' or not isinstance(record,dict) or record.get('component_version')!='sim005-mujoco-vla-backend-v1' or any(record.get(key)!=outcome['vla'].get(key) for key in ('mission_id','action_id')):return False
        normalized=normalize_run_local_mujoco(record)
        if normalized.payload.get('quality')!='valid' or outcome['vla'].get('component_version')!=record['component_version']:return False
        references=outcome['verification'].get('evidence_refs',[])
        if not any(reference.get('sha256')==normalized.reference['content_sha256'] for reference in references):return False
    if name in {'deterministic','navigation_physics'}:
        proof=row.get('observation_proof',{})
        if proof.get('source')!='deterministic_fixture' or proof.get('payload')!={'quality':'valid','part_id':'brake-ecu-b','location_id':'line-b-drop'}:return False
        from simulation_runtime.smoke import canonical_sha256
        if proof.get('reference',{}).get('content_sha256')!=canonical_sha256(proof['payload']):return False
        if not any(reference.get('sha256')==proof['reference']['content_sha256'] for reference in outcome['verification'].get('evidence_refs',[])):return False
    return True

def public_pair_valid(request: Any, result: Any, operation: str) -> bool:
    if not isinstance(request,dict) or not isinstance(result,dict) or request.get('operation')!=operation or result.get('operation')!=operation:return False
    for key in ('mission_id','trace_id','request_id'):
        if not isinstance(request.get(key),str) or not request[key] or result.get(key)!=request[key]:return False
    if operation!='mission.execute' and (not isinstance(request.get('action_id'),str) or not request['action_id'] or result.get('action_id')!=request['action_id']):return False
    try:
        issued=datetime.fromisoformat(request['timestamp'].replace('Z','+00:00'));completed=datetime.fromisoformat(result['timestamp'].replace('Z','+00:00'));deadline=datetime.fromisoformat(request['deadline_at'].replace('Z','+00:00'))
        return all(value.tzinfo is not None for value in (issued,completed,deadline)) and issued<=completed<=deadline
    except (ValueError,KeyError,TypeError,AttributeError):return False

def profiles_valid(evidence: dict[str, Any]) -> bool:
    rows=evidence.get('profile_smoke')
    if not isinstance(rows,list) or len(rows)!=4 or any(not isinstance(row,dict) for row in rows):
        return False
    if {row.get('profile') for row in rows}!=PROFILE_NAMES:
        return False
    missions=[];traces=[]
    for row in rows:
        if not all(row.get(key) is True for key in ('pass','bounded','cleanup_complete','verification_before_completion')):
            return False
        outcome=row.get('outcome')
        if not isinstance(outcome,dict) or any(not isinstance(outcome.get(key),dict) for key in ('mission','navigation','vla','verification')):
            return False
        mission=outcome['mission']; nav=outcome['navigation'];vla=outcome['vla'];verification=outcome['verification']
        if mission.get('result')!='success' or mission.get('status')!='completed':
            return False
        if any(action.get('result')!='success' or action.get('status')!='succeeded' for action in (nav,vla,verification)) or verification.get('verdict')!='pass':
            return False
        for key in ('mission_id','trace_id'):
            value=mission.get(key)
            if not isinstance(value,str) or not value or any(action.get(key)!=value for action in (nav,vla,verification)):
                return False
        if not all(isinstance(action.get('action_id'),str) and action['action_id'] for action in (nav,vla,verification)):
            return False
        if nav['action_id']==vla['action_id'] or verification['action_id']!=vla['action_id']:
            return False
        try:
            requests=row.get('public_requests',{})
            if any(not public_pair_valid(requests.get(key),outcome[key],operation) for key,operation in (('mission','mission.execute'),('navigation','navigation.execute'),('vla','vla.execute'),('verification','verification.verify'))):return False
            verified_at=datetime.fromisoformat(verification['timestamp'].replace('Z','+00:00'));completed_at=datetime.fromisoformat(mission['timestamp'].replace('Z','+00:00'));mission_deadline=datetime.fromisoformat(requests['mission']['deadline_at'].replace('Z','+00:00'))
            if not verified_at<=completed_at<=mission_deadline:return False
            if any(datetime.fromisoformat(action['timestamp'].replace('Z','+00:00'))>completed_at for action in (nav,vla,verification)):return False
            if not profile_backend_proof(row):return False
        except (ValueError,KeyError,TypeError,AttributeError):return False
        missions.append(mission['mission_id']);traces.append(mission['trace_id'])
    return len(set(missions))==4 and len(set(traces))==4


def evaluate_successor(root: Path) -> dict[str, Any]:
    root=Path(root)
    historical=evaluate(root)
    result=dict(historical)
    result['qualification_contract']='SIM-E2E-SUCCESSOR-V1'
    result['historical_decision']=historical['decision']
    result['historical_accepted_evidence_bindings']=historical['accepted_evidence_bindings']
    result['acceptance_identity_model']='independent reviewed candidate HEAD + immutable source/config manifest + Evidence SHA256'
    failures=[item for item in historical['failures'] if item!='SIM-007: required READY result not proven']
    result['failures']=failures
    successors={};bindings={}
    try:
        registry=read_json(root/REGISTRY)
        if registry.get('schema_version')!=1 or registry.get('contract_id')!='SIM-E2E-SUCCESSOR-V1':
            raise ValueError('unsupported successor contract')
        routes=registry.get('successors')
        if not isinstance(routes,dict) or set(routes)!={'SIM-007','SIM-010'}:
            raise ValueError('exact successor identities required')
        declared_required=registry.get('required_reviewed_paths')
        if not isinstance(declared_required,list) or not all(isinstance(p,str) for p in declared_required):
            raise ValueError('required source/config manifest absent')
        required=set(declared_required)|{REGISTRY}
        for owner in ('SIM-007','SIM-010'):
            route=routes[owner]
            if route.get('task_id')!=f'TASK-{owner}-R01':
                raise ValueError('unsupported successor task identity')
            successors[owner],acceptance=review_binding(root,route,required)
            bindings[owner]={**route,'evidence_sha256':acceptance['evidence']['sha256'],'reviewed_candidate_head':acceptance['reviewed_candidate_head'],'reviewed_source_manifest':acceptance['reviewed_source_manifest'],'acceptance_sha256':sha256(safe_path(root,route['acceptance_path'])),'status':'PASS','identity_model':result['acceptance_identity_model']}
            if evidence_result(successors[owner])!=TASKS[owner]:
                failures.append(f'{owner}-R01: required READY result not proven')
        if bindings['SIM-007']['reviewed_source_manifest'] != bindings['SIM-010']['reviewed_source_manifest'] or bindings['SIM-007']['reviewed_candidate_head'] != bindings['SIM-010']['reviewed_candidate_head']:
            raise ValueError('successors must share reviewed source/config identity')
        middleware=successors['SIM-007'].get('middleware_identity',{})
        if registry.get('middleware_profile') is not None:
            path=registry['middleware_profile']
            if middleware.get('profile_path')!=path or middleware.get('profile_sha256')!=bindings['SIM-007']['reviewed_source_manifest'].get(path) or middleware.get('RMW_IMPLEMENTATION')!='rmw_fastrtps_cpp' or middleware.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='SYSTEM_DEFAULT':raise ValueError('canonical middleware source authority mismatch')
            for row in successors['SIM-007'].get('profile_smoke',[]):
                if row.get('profile') in {'navigation_physics','system'}:
                    env=row.get('middleware_environment',{})
                    if env.get('FASTRTPS_DEFAULT_PROFILES_FILE')!=str(safe_path(root,path)) or env.get('RMW_IMPLEMENTATION')!='rmw_fastrtps_cpp' or env.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='SYSTEM_DEFAULT' or not env.get('ROS_DOMAIN_ID') or not env.get('GZ_PARTITION'):raise ValueError('live runtime middleware identity mismatch')
        if not profiles_valid(successors['SIM-007']):
            failures.append('SIM-007-R01: four distinct complete bounded verified profile executions not proven')
        index=successors['SIM-010']
        regression=index.get('full_repository_regression',{})
        command=regression.get('command')
        if regression.get('returncode')!=0 or regression.get('gate_result')!='PASS' or not isinstance(command,list) or len(command)!=6 or command[1:]!=['-m','pytest','-q','-p','no:cacheprovider']:
            raise ValueError('complete successful repository regression command not proven')
        logs={}
        for stream in ('stdout','stderr'):
            log=safe_path(root,regression.get(stream+'_path'))
            if sha256(log)!=regression.get(stream+'_sha256'):raise ValueError('regression log hash mismatch: '+stream)
            logs[stream]=log.read_text()
        if not re.search(r'[1-9][0-9]*\s+passed',logs['stdout']) or any(int(count)>0 for count in re.findall(r'(\d+)\s+(?:failed|errors?)',logs['stdout'])):
            raise ValueError('regression logs do not prove successful test completion')
        mission_link=index.get('fresh_mission_integration_binding')
        if not isinstance(mission_link,dict) or any(mission_link.get(key)!=bindings['SIM-007'].get(key) for key in ('task_id','evidence_path','evidence_sha256')):
            raise ValueError('successor index binds different mission integration Evidence')
        historical_index=index.get('historical_bindings')
        if not isinstance(historical_index,dict) or set(historical_index)!=set(TASKS):
            raise ValueError('successor index must bind every immutable historical source')
        for owner,row in historical['predecessors'].items():
            frozen=historical_index[owner]
            if (frozen.get('acceptance_sha256')!=sha256(root/row['acceptance_path']) or frozen.get('evidence_path')!=row.get('evidence_path') or frozen.get('evidence_sha256')!=row.get('evidence_sha256') or frozen.get('accepted_commit')!=row.get('reviewed_revision')):
                raise ValueError(f'{owner}: successor historical binding mismatch')
        sources={owner:read_json(root/row['evidence_path']) for owner,row in historical['predecessors'].items() if row['status']=='PASS'}
        sources.update(successors)
        declared=index.get('predicate_sources')
        matrix={}
        for name,(owner,check) in PREDICATES.items():
            authoritative=isinstance(declared,dict) and declared.get(name)==owner
            ok=authoritative and owner in sources and bool(check(sources[owner]))
            old=historical['matrix'][name]
            binding=bindings.get(owner,historical['predecessors'][owner])
            expected=old['expected']
            matrix[name]={**old,'actual':(not ok) if isinstance(expected,bool) else ('PASS' if ok else 'FAIL'), 'reconstruction_status':'PASS' if ok else ('FAIL' if authoritative else 'UNVERIFIED'),'reason':None if ok else ('underlying Evidence did not prove predicate' if authoritative else 'successor index lacks unique predicate-source binding'),'acceptance_artifacts':[binding['acceptance_path']],'underlying_evidence_paths':[binding['evidence_path']],'verified_bindings':[binding['evidence_sha256']],'source_identity_model':binding.get('identity_model','historical immutable accepted binding')}
        result['matrix']=matrix
        result['successor_evidence_bindings']=bindings
        result['successor_index_binding']={'path':routes['SIM-010']['evidence_path'],'sha256':bindings['SIM-010']['evidence_sha256']}
    except Exception as exc:
        failures.append(f'successor-chain validation: {exc}')
    result['decision']='SIM_E2E_QUALIFIED' if not failures and all(row['reconstruction_status']=='PASS' for row in result['matrix'].values()) else 'SIM_E2E_NOT_QUALIFIED'
    result['verifier_identity_or_version']='verify_simulation_e2e_qualification.py/successor-v1'
    result['successor_verifier_sha256']=sha256(Path(__file__))
    return result
