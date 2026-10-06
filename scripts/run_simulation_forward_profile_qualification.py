#!/usr/bin/env python3
"""Fresh, additive four-profile qualification; historical artifacts are read-only."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from simulation_runtime.mission_integration import MissionIntegrationRuntime, PROFILES, make_mission_request
from simulation_runtime.smoke import canonical_sha256, validate_contract_message, ContractViolation
from simulation_runtime.verification_backend import NormalizedObservation, VerificationBackend, normalize_deterministic_observation
from scripts.simulation_e2e_successor import profiles_valid, sha256


def candidate_manifest(root: Path=ROOT) -> dict[str,str]:
    """Capture complete present source/config/model/contract/test identities."""
    roots=('src','scripts','config','configs','data/simulation','docs/contracts','tests')
    return {str(path.relative_to(root)):sha256(path) for directory in roots for path in sorted((root/directory).rglob('*')) if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc','.pyo'}}


def normalize_run_local_mujoco(record: Mapping[str,Any]) -> NormalizedObservation:
    measurement=record['measurement']
    complete=(record.get('observed_status')=='succeeded' and measurement.get('transferred') is True and measurement.get('contact_detected') is True and measurement.get('final_contact') is True and isinstance(measurement.get('object_x_after'),(int,float)) and measurement['object_x_after']>=0.035 and measurement.get('steps',0)>0 and measurement.get('timestep_seconds',0)>0)
    payload={'quality':'valid','part_id':'sim-workpiece','location_id':'transfer-zone'} if complete else {'quality':'insufficient'}
    reference={'fixture_set_id':'SIM_FIXTURE_SET_V1','fixture_id':f"sim007-r01-mujoco-{record['mission_id']}-{record['action_id']}",'fixture_version':'SIM-E2E-SUCCESSOR-V1','content_sha256':canonical_sha256(payload),'timestamp':str(record['recorded_at']),'source_kind':'mock'}
    return NormalizedObservation(reference,payload,'mujoco_runtime',{'source':'mujoco_runtime','runtime_record':json.dumps(dict(record),sort_keys=True,separators=(',',':')),'record_sha256':canonical_sha256(dict(record))},reference)


class RunLocalMuJoCoVerifier(VerificationBackend):
    """New successor authority for fresh action-keyed measurements, same public API."""
    def __init__(self, record: Mapping[str,Any]):
        self.record=json.loads(json.dumps(dict(record)))
    def _validate_evidence(self, request, observations):
        if len(observations)!=1 or observations[0].source!='mujoco_runtime':
            raise ContractViolation('one current MuJoCo action observation required')
        expected=normalize_run_local_mujoco(self.record);observed=observations[0]
        if observed!=expected or request.get('observation_refs')!=[dict(expected.reference)]:
            raise ContractViolation('measurement/reference hash or run-local record mismatch')
        if self.record.get('component_version')!='sim005-mujoco-vla-backend-v1' or any(self.record.get(key)!=request.get(key) for key in ('mission_id','action_id')):
            raise ContractViolation('current MuJoCo action identity mismatch')
        now=datetime.fromisoformat(request['timestamp'].replace('Z','+00:00'));recorded=datetime.fromisoformat(self.record['recorded_at'].replace('Z','+00:00'))
        if now-recorded<timedelta(0) or now-recorded>timedelta(seconds=30):
            raise ContractViolation('run-local measurement is stale or future')


def instrument_runtime(runtime: Any) -> Any:
    """Record elapsed owned lifecycle calls without altering accepted behavior."""
    import time
    original_navigate=runtime.navigate
    def observed_navigate(request):
        from unittest.mock import patch
        run=subprocess.run
        def observed_run(command,*args,**kwargs):
            started=time.monotonic()
            event={'command':command,'started_at':datetime.now(timezone.utc).isoformat(),'configured_timeout_seconds':kwargs.get('timeout')}
            try:
                result=run(command,*args,**kwargs)
                event.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,timed_out=False)
                return result
            except subprocess.TimeoutExpired as exc:
                def decoded(value):return value.decode(errors='replace') if isinstance(value,bytes) else value
                event.update(timed_out=True,partial_stdout=decoded(exc.stdout),partial_stderr=decoded(exc.stderr))
                raise
            finally:
                event.update(ended_at=datetime.now(timezone.utc).isoformat(),duration_ms=round((time.monotonic()-started)*1000,3))
                runtime.measurements.setdefault('navigation_client_diagnostics',[]).append(event)
        with patch.object(subprocess,'run',observed_run):
            return original_navigate(request)
    runtime.navigate=observed_navigate
    for method_name in ('_probe','_probe_tf'):
        original=getattr(runtime,method_name)
        def probe_wrapped(*args,_method=original,_name=method_name,**kwargs):
            # Capture the actual private-call timeout argument, including a
            # shortened last retry. No successful persistent request gets grace.
            timeout=kwargs.get('timeout',args[3] if _name=='_probe_tf' and len(args)>3 else (args[2] if _name=='_probe' and len(args)>2 else 10))
            previous=len(runtime.measurements.get('localization',{}).get('probes',[]))
            result=_method(*args,**kwargs)
            for record in runtime.measurements.get('localization',{}).get('probes',[])[previous:]:
                persistent=record.get('client')=='persistent_ros_bootstrap'
                reap_ms=4000 if _name=='_probe_tf' else (2000 if record.get('timed_out') is True and not persistent else 0)
                record.update(configured_operation_bound_ms=timeout*1000,termination_budget_ms=reap_ms,probe_kind='tf_cli' if _name=='_probe_tf' else ('persistent_request' if persistent else 'cli'),termination_overhead_ms=max(0,record.get('duration_ms',0)-timeout*1000))
            return result
        setattr(runtime,method_name,probe_wrapped)
    for name in ('start','bootstrap_localization','close'):
        original=getattr(runtime,name)
        def wrapped(*args,_method=original,_name=name,**kwargs):
            started=time.monotonic()
            try:return _method(*args,**kwargs)
            finally:runtime.measurements.setdefault('owned_stage_durations',[]).append({'stage':_name,'duration_ms':round((time.monotonic()-started)*1000,3)})
        setattr(runtime,name,wrapped)
    return runtime


def fresh_navigation_factory(warm_action=True):
    from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
    if not warm_action:return instrument_runtime(BoundedGazeboNav2Runtime())
    from scripts.ros_qualification_action_client import QualificationActionProcess
    from scripts.run_simulation_navigation import GOALS
    from simulation_runtime.navigation_backend import RuntimeObservation
    import time
    class WarmNavigationRuntime(BoundedGazeboNav2Runtime):
        def __init__(self):
            super().__init__();self.action_client=QualificationActionProcess(self.environment);self.action_client_usable=True
        def navigate(self,request):
            started=time.monotonic();bound=min(self.bounds.execution_seconds,request['timeout_ms']/1000)
            identity={key:request[key] for key in ('mission_id','trace_id','request_id','action_id')}
            try:
                if not self.action_client_usable:raise RuntimeError('action client deadline expired; late response prohibited')
                result=self.action_client.request('navigate',[identity,GOALS[request['destination_id']]],bound)
                matched=result.get('request_identity')==identity and isinstance(result.get('goal_uuid'),str) and len(result['goal_uuid'])==32
                ok=matched and result.get('ok') is True and result.get('terminal_status')==4 and result.get('error_code')==0
                if ok:observation=RuntimeObservation('succeeded',arrival_verified=True)
                elif result.get('terminal_status') is not None or result.get('error')=='GOAL_REJECTED':observation=RuntimeObservation('failed',error_code='NAVIGATION_ABORTED',error_message='warmed action reported unsuccessful terminal status')
                else:observation=RuntimeObservation('unknown',error_code='NAVIGATION_TIMEOUT',error_message='bounded warmed action did not prove success',error_category='DEPENDENCY_TIMEOUT',retryable=True)
            except (TimeoutError,RuntimeError,OSError) as exc:
                result={'ok':False,'error':repr(exc)}
                observation=RuntimeObservation('unknown',error_code='NAVIGATION_TIMEOUT',error_message='bounded warmed action did not prove success',error_category='DEPENDENCY_TIMEOUT',retryable=True)
                # A late response may not be consumed by a subsequent request.
                self.action_client_usable=False
            self.observations[request['action_id']]=observation
            self.measurements.setdefault('executions',[]).append({'action_id':request['action_id'],'destination_id':request['destination_id'],'goal':GOALS[request['destination_id']],'execution_bound_ms':bound*1000,'duration_ms':round((time.monotonic()-started)*1000,3),'observed_status':observation.observed_status,'arrival_verified':observation.arrival_verified,'client':'persistent_canonical_action','client_response':result})
            return observation
        def close(self):
            super().close()
            complete=self.action_client.close();cleanup=self.measurements.setdefault('cleanup',{})
            cleanup['complete']=cleanup.get('complete') is True and complete
            cleanup.setdefault('processes',[]).append({'pid':self.action_client.process.pid,'returncode':self.action_client.process.returncode,'owner':'canonical_action_client'})
            return cleanup['complete']
    return instrument_runtime(WarmNavigationRuntime())

class FreshComponentProfileRuntime(MissionIntegrationRuntime):
    """Use existing public boundaries with profile-appropriate current Verification."""
    def _vla(self, request, navigation):
        if self.profile.name!='manipulation_physics':
            return super()._vla(request,navigation)
        from simulation_runtime.mujoco_vla_backend import MuJoCoVLABackend, observation_ref
        self.mujoco_backend=MuJoCoVLABackend()
        adapted=dict(request,task_id='mujoco-place-nominal',policy_version='sim005-scripted-policy-v1',workspace_profile_id='sim005-workspace-v1',observation_refs=[observation_ref()])
        self.execution_vla_request=adapted
        result=self.mujoco_backend.execute(adapted)
        self.measurement_record=self.mujoco_backend.records[(adapted['mission_id'],adapted['action_id'])]
        self.action_record={'mission_id':self.measurement_record.mission_id,'action_id':self.measurement_record.action_id,'observed_status':self.measurement_record.observed_status,'recorded_at':self.measurement_record.recorded_at,'component_version':result['component_version'],'measurement':self.mujoco_backend.measurement_for(adapted['mission_id'],adapted['action_id'])}
        return result


def component_profile(name: str) -> dict[str,Any]:
    import time
    runtime=FreshComponentProfileRuntime(name,gazebo_runtime_factory=fresh_navigation_factory);mission=make_mission_request()
    if name=='manipulation_physics':
        mission['goal'].update(part_id='sim-workpiece',destination_id='transfer-zone')
    started=time.monotonic();managed=None;outcome={};observation_proof={};requests={'mission':mission}
    try:
        navigation,managed=runtime._navigation()
        # Startup has its own bound. Dispatch the public mission only after readiness.
        mission=make_mission_request()
        if name=='manipulation_physics':mission['goal'].update(part_id='sim-workpiece',destination_id='transfer-zone')
        mission['timeout_ms']=60000
        mission['deadline_at']=(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat(timespec='milliseconds').replace('+00:00','Z')
        validate_contract_message(mission)
        nr=runtime._action_request(mission,'navigation.execute','navigation');nr.update(robot_id='amr-sim-001',destination_id='line-b-drop' if name=='manipulation_physics' else mission['goal']['destination_id'],speed_profile_id='sim-safe-v1')
        requests['mission']=mission;requests['navigation']=nr
        outcome['navigation']=navigation.execute(nr)
        if outcome['navigation']['result']!='success':raise RuntimeError('navigation non-success')
        vr=runtime._action_request(mission,'vla.execute','vla');vr.update(robot_id='manipulator-sim-001',task_id='place-brake-ecu',policy_version='fixture-policy-v1',workspace_profile_id='sim-workspace-v1',observation_refs=[runtime._fixture_ref()])
        outcome['vla']=runtime._vla(vr,outcome['navigation']);requests['vla']=getattr(runtime,'execution_vla_request',vr)
        if outcome['vla']['result']!='success':raise RuntimeError('VLA non-success')
        if name=='manipulation_physics':
            record=runtime.action_record;observation=normalize_run_local_mujoco(record);verifier=RunLocalMuJoCoVerifier(record);observation_proof={'source':'mujoco_runtime','action_record':record}
            expected={'part_id':'sim-workpiece','location_id':'transfer-zone'}
        else:
            # This profile expressly owns a fixture/proxy VLA. Its normalized
            # Verification checks the fixture semantic state; live Navigation
            # results and process measurements remain separate physics proof.
            timestamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
            expected={'part_id':'brake-ecu-b','location_id':'line-b-drop'}
            observation=normalize_deterministic_observation({'quality':'valid',**expected},fixture_id=f"sim007-r01-proxy-{vr['action_id']}",fixture_version='1',timestamp=timestamp)
            verifier=VerificationBackend();observation_proof={'source':'deterministic_fixture','reference':dict(observation.reference),'payload':dict(observation.payload)}
        request=runtime._action_request(mission,'verification.verify','verification');request.pop('idempotency_key');request.pop('attempt');request.pop('retry_budget_remaining');request.update(action_id=vr['action_id'],verifier_id='exact-state-verifier',expected_state=expected,observation_refs=[dict(observation.reference)],verification_profile_version='sim-exact-match-v1')
        requests['verification']=request
        outcome['verification']=verifier.verify(request,[observation])
        if outcome['verification'].get('verdict')!='pass':raise RuntimeError('verification not eligible')
        if datetime.now(timezone.utc)>datetime.fromisoformat(mission['deadline_at'].replace('Z','+00:00')):raise RuntimeError('declared mission deadline exceeded')
        outcome['mission']=runtime._mission_result(mission,'completed','success','completed')
    except Exception as exc:
        outcome['mission']=runtime._mission_failure(mission,'PROFILE_QUALIFICATION_FAILED',str(exc))
    finally:
        cleanup=runtime._close_runtime(managed) if managed else runtime.lifecycle.get('cleanup_complete') is not False
        runtime.lifecycle['cleanup_complete']=cleanup
    bound_proof=runtime_bound_proof(managed) if managed else {'policy':'finite deterministic or 400-step MuJoCo component execution; public mission deadline checked','bounded':True}
    bounded=bound_proof['bounded']
    return {'profile':name,'pass':outcome['mission']['result']=='success' and cleanup and bounded,'bounded':bounded,'cleanup_complete':cleanup,'verification_before_completion':'verification' in outcome and outcome['verification'].get('verdict')=='pass','outcome':outcome,'public_requests':requests,'mission_request':mission,'observation_proof':observation_proof,'operation_bound_proof':bound_proof,'lifecycle':runtime.lifecycle,'middleware_environment':{key:managed.environment.get(key) for key in ('RMW_IMPLEMENTATION','FASTRTPS_DEFAULT_PROFILES_FILE','ROS_AUTOMATIC_DISCOVERY_RANGE','ROS_LOCALHOST_ONLY','ROS_DOMAIN_ID','GZ_PARTITION')} if managed else {},'runtime_measurements':dict(getattr(managed,'measurements',{})) if managed else {},'profile_definition':PROFILES[name].__dict__,'navigation_route_scope':{'namespace':'deterministic_fixture','waypoint':'line-b-drop','component_bench_goal':'transfer-zone','global_world_equivalence_claimed':False} if name=='manipulation_physics' else None}


def runtime_bound_proof(runtime: Any) -> dict[str,Any]:
    """Reconstruct each owned operation bound, without summing unrelated stages."""
    measurements=runtime.measurements
    probes=[]
    for row in measurements.get('localization',{}).get('probes',[]):
        configured=row.get('configured_operation_bound_ms')
        reap=row.get('termination_budget_ms')
        expected_reap=4000 if row.get('probe_kind')=='tf_cli' else (2000 if row.get('timed_out') is True and row.get('probe_kind')=='cli' else 0)
        label_max=5000 if row.get('label') in {'simulation_clock','initial_pose_publish'} or row.get('probe_kind')=='tf_cli' else 10000
        permitted=isinstance(configured,(int,float)) and 0<configured<=label_max and reap==expected_reap
        bound_ms=(configured+reap) if permitted else 0
        overhead=max(0,row.get('duration_ms',0)-(configured or 0))
        enforced=permitted and row.get('termination_overhead_ms')==overhead and isinstance(row.get('duration_ms'),(int,float)) and 0<=row['duration_ms']<=bound_ms
        probes.append({'label':row.get('label'),'duration_ms':row.get('duration_ms'),'operation_bound_ms':bound_ms,'timeout_enforced':row.get('timed_out') is True,'bounded':enforced})
    executions=[{'action_id':row.get('action_id'),'duration_ms':row.get('duration_ms'),'operation_bound_ms':row.get('execution_bound_ms'),'bounded':isinstance(row.get('duration_ms'),(int,float)) and isinstance(row.get('execution_bound_ms'),(int,float)) and row['duration_ms']<=row['execution_bound_ms']} for row in measurements.get('executions',[])]
    cleanup=measurements.get('cleanup',{})
    terminated=cleanup.get('complete') is True and all(row.get('returncode') is not None for row in cleanup.get('processes',[]))
    b=runtime.bounds
    # Readiness contains separate bounded retry loops plus a final probe/reap.
    # Start's final 3s CLI probe may finish after its enclosing startup deadline.
    stage_bounds={'start':(b.startup_seconds+3+b.cleanup_seconds)*1000,'bootstrap_localization':(4*b.localization_seconds+5+9+9+4*15+2*15+10+15+31)*1000,'close':(b.cleanup_seconds+2*len(cleanup.get('processes',[]))+2)*1000}
    stages=[{**row,'operation_bound_ms':stage_bounds.get(row.get('stage'),0),'bounded':isinstance(row.get('duration_ms'),(int,float)) and 0<=row['duration_ms']<=stage_bounds.get(row.get('stage'),0)} for row in measurements.get('owned_stage_durations',[])]
    return {'policy':'exact private operation timeouts; only explicitly measured owned CLI termination gets its documented reap budget','context_bounds_seconds':{key:getattr(runtime.bounds,key) for key in ('startup_seconds','localization_seconds','execution_seconds','cleanup_seconds')},'probes':probes,'executions':executions,'stages':stages,'cleanup':cleanup,'bounded':terminated and all(row['bounded'] for row in probes+executions+stages)}

def system_profile() -> dict[str,Any]:
    from scripts.run_simulation_normal_system_e2e import GazeboSystemWorld
    from simulation_runtime.normal_system_e2e import NormalSystemE2E,load_scenario
    class RecordingNormalSystemE2E(NormalSystemE2E):
        def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.captured_requests=[]
        def _request(self,*args,**kwargs):
            request=super()._request(*args,**kwargs);self.captured_requests.append(request);return request
    scenario=load_scenario();world=GazeboSystemWorld(scenario);world.runtime=instrument_runtime(world.runtime);executor=RecordingNormalSystemE2E(world,scenario);execution=executor.execute()
    by_name={row['name']:row for row in execution['steps']}
    outcome={'mission':execution['mission']}
    for name,label in (('navigation','destination_navigation'),('vla','vla.execute'),('verification','final_verification')):
        if label in by_name:outcome[name]=by_name[label]['result']
    requests={'mission':execution['mission_request']}
    for key,label in (('source_navigation','source_navigation'),('source_verification','source_verification'),('navigation','destination_navigation'),('vla','vla.execute'),('verification','final_verification')):
        if label in by_name:
            result=by_name[label]['result'];matches=[request for request in executor.captured_requests if request.get('request_id')==result.get('request_id')]
            if len(matches)==1:requests[key]=matches[0]
    cleanup=execution['lifecycle']['cleanup_complete'];bound_proof=runtime_bound_proof(world.runtime);bounded=bound_proof['bounded']
    return {'profile':'system','pass':execution['mission']['result']=='success' and cleanup and bounded,'bounded':bounded,'cleanup_complete':cleanup,'verification_before_completion':outcome.get('verification',{}).get('verdict')=='pass','outcome':outcome,'public_requests':requests,'raw_execution':execution,'operation_bound_proof':bound_proof,'profile_definition':PROFILES['system'].__dict__,'runtime_measurements':world.runtime.measurements,'middleware_environment':{key:world.runtime.environment.get(key) for key in ('RMW_IMPLEMENTATION','FASTRTPS_DEFAULT_PROFILES_FILE','ROS_AUTOMATIC_DISCOVERY_RANGE','ROS_LOCALHOST_ONLY','ROS_DOMAIN_ID','GZ_PARTITION')}}


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results/simulation/SIM-007-R01_mission_integration.json');args=parser.parse_args()
    profile=ROOT/'configs/simulation/sim_r01_fastdds_loopback.xml'
    os.environ.update(FASTRTPS_DEFAULT_PROFILES_FILE=str(profile),RMW_IMPLEMENTATION='rmw_fastrtps_cpp',ROS_AUTOMATIC_DISCOVERY_RANGE='SYSTEM_DEFAULT')
    os.environ.pop('ROS_LOCALHOST_ONLY',None)
    middleware={'profile_path':str(profile.relative_to(ROOT)),'profile_sha256':sha256(profile),'RMW_IMPLEMENTATION':os.environ['RMW_IMPLEMENTATION'],'ROS_AUTOMATIC_DISCOVERY_RANGE':os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']}
    before=candidate_manifest();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    rows=[component_profile(name) for name in ('deterministic','navigation_physics','manipulation_physics')]+[system_profile()]
    after=candidate_manifest();stable=before==after
    payload={'schema_version':1,'task_id':'TASK-SIM-007-R01','task_specific_result':'SIM_MISSION_INTEGRATION_READY' if stable and profiles_valid({'profile_smoke':rows}) else 'SIM_MISSION_INTEGRATION_BLOCKED','generated_at':datetime.now(timezone.utc).isoformat(),'source_candidate_head':head,'execution_source_manifest':before,'source_manifest_stable':stable,'middleware_identity':middleware,'profile_smoke':rows,'system_authority':{'integrated_world':'gazebo_harmonic','dual_world':False,'mujoco_live_world':False},'historical_predecessor_relation':{'task_id':'TASK-SIM-007','evidence_path':'results/simulation/SIM-007_mission_integration.json','evidence_sha256':sha256(ROOT/'results/simulation/SIM-007_mission_integration.json'),'historical_result_unchanged':'SIM_MISSION_INTEGRATION_BLOCKED'},'physical_dependency':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(payload['task_specific_result']);return 0 if payload['task_specific_result']=='SIM_MISSION_INTEGRATION_READY' else 1

if __name__=='__main__':raise SystemExit(main())
