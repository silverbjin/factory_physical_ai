from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.mission_integration import PROFILES, MissionIntegrationRuntime, ProfileUnavailable, make_mission_request, select_profile
from simulation_runtime.smoke import validate_contract_message

def test_every_frozen_profile_smokes_through_public_contracts() -> None:
    for name in PROFILES:
        runtime = MissionIntegrationRuntime(name)
        outcome = runtime.execute(make_mission_request())
        assert outcome["mission"]["result"] == "success"
        assert outcome["verification"]["verdict"] == "pass"
        assert runtime.cleaned_up
        for key in ("mission", "navigation", "vla", "verification"):
            validate_contract_message(outcome[key])

def test_system_has_gazebo_as_only_integrated_world_authority() -> None:
    profile = select_profile("system")
    assert profile.integrated_world == "gazebo_harmonic"
    assert profile.vla == "gazebo_contract_preserving_surrogate"
    assert "mujoco" not in profile.vla

def test_identity_is_preserved_and_verification_gates_completion() -> None:
    outcome = MissionIntegrationRuntime("navigation_physics").execute(make_mission_request())
    mission = outcome["mission"]
    assert all(outcome[name]["mission_id"] == mission["mission_id"] for name in ("navigation", "vla", "verification"))
    assert all(outcome[name]["trace_id"] == mission["trace_id"] for name in ("navigation", "vla", "verification"))
    assert outcome["verification"]["verdict"] == "pass" and mission["status"] == "completed"

def test_unknown_or_unavailable_profile_fails_closed() -> None:
    try: select_profile("unknown")
    except ProfileUnavailable: pass
    else: raise AssertionError("unknown profile must fail closed")
    runtime = MissionIntegrationRuntime("system", available_backends=set())
    result = runtime.execute(make_mission_request())["mission"]
    assert result["result"] == "failure" and result["error"]["code"] == "PROFILE_UNAVAILABLE"
