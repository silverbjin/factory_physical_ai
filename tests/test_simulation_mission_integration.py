from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.mission_integration import PROFILES, MissionIntegrationRuntime, ProfileUnavailable, make_mission_request, select_profile
from simulation_runtime.navigation_backend import RuntimeObservation
from simulation_runtime.smoke import validate_contract_message


class SpyGazeboRuntime:
    def __init__(self, *, ready: bool = True, cleanup: bool = True) -> None:
        self.ready, self.cleanup, self.calls = ready, cleanup, []
    def start(self) -> None: self.calls.append("start")
    def bootstrap_localization(self) -> bool:
        self.calls.append("bootstrap"); return self.ready
    def navigate(self, request: dict[str, object]) -> RuntimeObservation:
        self.calls.append("navigate"); return RuntimeObservation("succeeded", arrival_verified=True)
    def reconcile(self, action_id: str) -> RuntimeObservation: return RuntimeObservation("succeeded", arrival_verified=True)
    def close(self) -> bool:
        self.calls.append("close"); return self.cleanup


def test_every_frozen_profile_uses_the_same_public_contracts() -> None:
    for name in PROFILES:
        spy = SpyGazeboRuntime()
        runtime = MissionIntegrationRuntime(name, gazebo_runtime_factory=lambda: spy)
        outcome = runtime.execute(make_mission_request())
        assert outcome["mission"]["result"] in {"success", "failure"}
        assert runtime.cleaned_up
        validate_contract_message(outcome["mission"])
        if name in {"navigation_physics", "system"}:
            assert spy.calls == ["start", "bootstrap", "navigate", "close"]
            assert outcome["mission"]["result"] == "failure"
        else:
            assert spy.calls == []

def test_system_has_gazebo_as_only_integrated_world_authority() -> None:
    profile = select_profile("system")
    assert profile.integrated_world == "gazebo_harmonic"
    assert profile.vla == "gazebo_contract_preserving_surrogate"
    assert "mujoco" not in profile.vla

def test_system_does_not_fabricate_a_gazebo_manipulation_surrogate() -> None:
    spy = SpyGazeboRuntime()
    outcome = MissionIntegrationRuntime("system", gazebo_runtime_factory=lambda: spy).execute(make_mission_request())
    mission = outcome["mission"]
    assert all(outcome[name]["mission_id"] == mission["mission_id"] for name in ("navigation", "vla"))
    assert all(outcome[name]["trace_id"] == mission["trace_id"] for name in ("navigation", "vla"))
    assert outcome["navigation"]["result"] == "success"
    assert outcome["vla"]["error"]["code"] == "GAZEBO_SURROGATE_UNAVAILABLE"
    assert mission["error"]["code"] == "VLA_NON_SUCCESS"

def test_startup_or_cleanup_failure_fails_closed() -> None:
    startup = SpyGazeboRuntime(ready=False)
    outcome = MissionIntegrationRuntime("navigation_physics", gazebo_runtime_factory=lambda: startup).execute(make_mission_request())
    assert outcome["mission"]["error"]["code"] == "PROFILE_UNAVAILABLE"
    # Failed startup is still torn down and never proceeds to navigation.
    assert startup.calls == ["start", "bootstrap", "close"]
    cleanup = SpyGazeboRuntime(cleanup=False)
    runtime = MissionIntegrationRuntime("system", gazebo_runtime_factory=lambda: cleanup)
    runtime.execute(make_mission_request())
    assert runtime.cleaned_up is False and cleanup.calls[-1] == "close"

def test_unknown_or_unavailable_profile_fails_closed() -> None:
    try: select_profile("unknown")
    except ProfileUnavailable: pass
    else: raise AssertionError("unknown profile must fail closed")
    runtime = MissionIntegrationRuntime("system", available_backends=set())
    result = runtime.execute(make_mission_request())["mission"]
    assert result["result"] == "failure" and result["error"]["code"] == "PROFILE_UNAVAILABLE"
