# Simulation observability and regression v1

`TASK-SIM-010` produces `results/simulation/SIM-010_observability_regression.json`.
It is a Simulation-evidence-only index: it makes no physical, safety, latency,
reliability, or production claim.

The runner binds each SIM-003 through SIM-009 acceptance record to the exact
SHA-256 of its declared evidence. Rich Acceptance manifests bind that hash
directly; deterministic minimal manifests resolve only the task-declared
Evidence path from their immutable `accepted_commit` Git tree, recompute the
blob hash, and fail closed on any conflict. The current worktree is never used
as predecessor Evidence.

Only a complete, source-declared run envelope is admitted to the run/scenario
collection. Aggregate or provenance-only predecessor artifacts remain valid
accepted-source bindings with run extraction `NOT_REQUIRED`; an execution
source that lacks its declared run fails closed with `NO_EXTRACTABLE_RUNS`.
The aggregator never invents identities, provenance, scenarios, or replay
outcomes by mixing unrelated subtrees. Deterministic results compare replay
decisions and lifecycle outcomes; Gazebo and MuJoCo compare scenario outcomes,
lifecycle, invariants, and declared measurement tolerances rather than
bitwise physics traces.

The index fails closed for an invalid accepted commit, undeclared/missing
artifact, malformed blob, task/result mismatch, direct-binding conflict, or
hash mismatch. A blocked result remains auditable and never updates accepted
outcomes automatically. The runner records the full pytest command, exit code,
source Git SHA, and baseline classification; `PROVEN_PREEXISTING` requires the
same full pytest command to run against an isolated baseline checkout with
matching node IDs and stable failure signatures.
