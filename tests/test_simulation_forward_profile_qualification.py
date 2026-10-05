from scripts import verify_simulation_e2e_qualification


def test_live_measurement_normalizer_preserves_physics_source_and_non_success():
    import importlib.util
    spec=importlib.util.find_spec('scripts.run_simulation_forward_profile_qualification')
    assert spec is not None, 'fresh profile qualification runner is missing'
    from scripts.run_simulation_forward_profile_qualification import normalize_run_local_mujoco
    record={'mission_id':'m','action_id':'a','observed_status':'succeeded','recorded_at':'2026-10-05T00:00:00.000Z','component_version':'sim005-mujoco-vla-backend-v1','measurement':{'object_x_after':0.05,'transferred':True,'contact_detected':True,'final_contact':True,'steps':400,'timestep_seconds':0.002}}
    observation=normalize_run_local_mujoco(record)
    assert observation.source=='mujoco_runtime'
    assert dict(observation.payload)=={'quality':'valid','part_id':'sim-workpiece','location_id':'transfer-zone'}
    record['measurement']['final_contact']=False
    assert normalize_run_local_mujoco(record).payload['quality']=='insufficient'


def test_measurement_verifier_rejects_cross_mission_identity():
    from scripts.run_simulation_forward_profile_qualification import normalize_run_local_mujoco,RunLocalMuJoCoVerifier
    from simulation_runtime.mission_integration import MissionIntegrationRuntime,make_mission_request
    runtime=MissionIntegrationRuntime('deterministic');mission=make_mission_request()
    request=runtime._action_request(mission,'verification.verify','verify')
    for key in ('idempotency_key','attempt','retry_budget_remaining'):request.pop(key)
    request.update(verifier_id='exact-state-verifier',expected_state={'part_id':'sim-workpiece','location_id':'transfer-zone'},verification_profile_version='sim-exact-match-v1')
    record={'mission_id':'wrong-mission','action_id':request['action_id'],'observed_status':'succeeded','recorded_at':request['timestamp'],'component_version':'sim005-mujoco-vla-backend-v1','measurement':{'object_x_after':0.05,'transferred':True,'contact_detected':True,'final_contact':True,'steps':400,'timestep_seconds':0.002}}
    observation=normalize_run_local_mujoco(record);request['observation_refs']=[dict(observation.reference)]
    result=RunLocalMuJoCoVerifier(record).verify(request,[observation])
    assert result['result']=='failure'
    assert result['error']['code']=='INVALID_VERIFICATION_EVIDENCE'


def test_individual_runtime_bounds_allow_long_composed_lifecycle():
    from scripts import run_simulation_forward_profile_qualification as runner
    fn=getattr(runner,'runtime_bound_proof',None)
    assert callable(fn),'per-operation bound reconstruction missing'
    class Runtime:
        class Bounds:
            startup_seconds=20;localization_seconds=50;execution_seconds=20;cleanup_seconds=5
        bounds=Bounds()
        measurements={'executions':[{'duration_ms':8000,'execution_bound_ms':20000},{'duration_ms':12000,'execution_bound_ms':20000}], 'localization':{'probes':[{'label':'initial_pose_publish','duration_ms':2200,'timed_out':False,'configured_operation_bound_ms':5000,'termination_budget_ms':0,'probe_kind':'persistent_request','termination_overhead_ms':0}]},'cleanup':{'complete':True,'processes':[{'returncode':0}]}}
    assert fn(Runtime())['bounded'] is True
    Runtime.measurements['executions'][1]['duration_ms']=21000
    assert fn(Runtime())['bounded'] is False


def test_timeout_flag_cannot_hide_unbounded_probe_duration():
    from scripts.run_simulation_forward_profile_qualification import runtime_bound_proof
    class Runtime:
        class Bounds:
            startup_seconds=20;localization_seconds=50;execution_seconds=20;cleanup_seconds=5
        bounds=Bounds()
        measurements={'executions':[],'localization':{'probes':[{'label':'simulation_clock','duration_ms':600000,'timed_out':True,'configured_operation_bound_ms':5000,'termination_budget_ms':2000,'probe_kind':'cli','termination_overhead_ms':595000}]},'cleanup':{'complete':True,'processes':[]}}
    assert runtime_bound_proof(Runtime())['bounded'] is False


def test_successful_pose_cannot_inflate_five_second_bound():
    from scripts.run_simulation_forward_profile_qualification import runtime_bound_proof
    class Runtime:
        class Bounds:
            startup_seconds=45;localization_seconds=30;execution_seconds=30;cleanup_seconds=5
        bounds=Bounds()
        measurements={'executions':[],'localization':{'probes':[{'label':'initial_pose_publish','duration_ms':8000,'timed_out':False,'configured_operation_bound_ms':10000,'termination_budget_ms':0,'probe_kind':'persistent_request','termination_overhead_ms':0}]},'cleanup':{'complete':True,'processes':[]}}
    assert runtime_bound_proof(Runtime())['bounded'] is False


def test_generic_manipulation_smoke_routes_fixture_waypoint_and_measures_transfer():
    import pytest
    pytest.importorskip('mujoco')
    from scripts.run_simulation_forward_profile_qualification import component_profile
    row=component_profile('manipulation_physics')
    assert row['pass'] is True
    assert row['public_requests']['navigation']['destination_id']=='line-b-drop'
    assert row['public_requests']['mission']['goal']['destination_id']=='transfer-zone'
    assert row['observation_proof']['action_record']['measurement']['transferred'] is True
    assert row['outcome']['verification']['verdict']=='pass'


def test_candidate_manifest_covers_legacy_config_assets(tmp_path):
    from scripts.run_simulation_forward_profile_qualification import candidate_manifest
    asset=tmp_path/'config/simulation/world.sdf';asset.parent.mkdir(parents=True);asset.write_text('<sdf/>')
    before=candidate_manifest(tmp_path)
    assert 'config/simulation/world.sdf' in before
    asset.write_text('<sdf version="1.10"/>')
    assert candidate_manifest(tmp_path)!=before
