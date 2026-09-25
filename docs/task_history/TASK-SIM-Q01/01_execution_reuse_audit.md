# Q01 execution reuse audit

| Task | Accepted entrypoint | Strategy | Q01 integration boundary |
| --- | --- | --- | --- |
| SIM-004 | `scripts/run_simulation_navigation.py` | SIDECAR_INSTRUMENT | `BoundedGazeboNav2Runtime`; add structured Gazebo stats/clock observation without changing predecessor runner. |
| SIM-005 | `scripts/run_simulation_mujoco_vla.py` | WRAP_EXISTING | `MuJoCoVLABackend.execute` and `measurement_for`; create Q01 identities before invocation. |
| SIM-008 | `scripts/run_simulation_normal_system_e2e.py` | WRAP_EXISTING | `NormalSystemE2E` / `GazeboSystemWorld.observe`; preserve distinct runner and scenario assets. |
| SIM-009 | `scripts/run_simulation_failure_recovery.py` | WRAP_EXISTING | `run_failure_suite`; use manifest scenario IDs and per-scenario runtime observations. |

Historical authority is read from each listed accepted commit and Evidence blob.
No predecessor Acceptance, Evidence, or source is modified by Q01.
