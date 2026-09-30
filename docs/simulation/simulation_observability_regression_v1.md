# Simulation observability and regression v1

`TASK-SIM-010` produces `results/simulation/SIM-010_observability_regression.json`.
It is a Simulation-evidence-only index: it makes no physical, safety, latency,
reliability, or production claim.

The runner binds each SIM-003 through SIM-009 acceptance record to the exact
SHA-256 of its declared evidence. Each artifact must declare backend profile,
source/config hashes, Mission/request/action/trace identities, Skill and
Verification results, failure/recovery decision, and structured scenarios.
Deterministic results compare replay decisions and lifecycle outcomes; Gazebo
and MuJoCo compare scenario outcomes, lifecycle, invariants, and declared
measurement tolerances rather than bitwise physics traces.

The index fails closed for a missing acceptance binding, missing artifact,
hash mismatch, or unavailable required predecessor. A blocked result remains
auditable and never updates accepted outcomes automatically. A failed full
repository pytest run also forces `SIM_OBSERVABILITY_REGRESSION_BLOCKED`; the
runner records the command, exit code, test count, and source Git SHA.
