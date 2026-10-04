# Staged Integration Profile — Usage Guide

The hardened orchestrator keeps the existing lifecycle unless a task provides:

`tasks/orchestrator/<TASK_ID>.json`

with `profile: staged_integration_v1`.

## Minimal contract

```json
{
  "schema_version": 1,
  "task_id": "TASK-SIM-011",
  "profile": "staged_integration_v1",
  "gates": [
    {"id": "G0", "command": ["python3", "scripts/check_static_authority.py"]},
    {"id": "G1", "command": ["python3", "scripts/check_runtime_environment.py"]}
  ],
  "protected_paths": [
    "results/reviews/SIM-009_acceptance.json",
    "results/simulation/SIM-009_failure_recovery.json"
  ],
  "source_paths": [
    "scripts/simulation",
    "config/simulation"
  ],
  "finalization_paths": [
    "scripts/simulation",
    "config/simulation",
    "docs/task_history/TASK-SIM-011"
  ],
  "canonical": {
    "command": ["python3", "scripts/run_sim011_canonical.py"],
    "evidence_paths": ["results/simulation/SIM-011_result.json"]
  },
  "literal_validation": [
    ["python3", "-m", "pytest", "tests/test_sim011.py", "-q"]
  ]
}
```

## Contract semantics

- `gates`: exact argv commands, executed in order by the host. Exit 0 is PASS. A non-zero gate should emit `GATE_RESULT_JSON:` with `finding_id`, `root_cause_class`, `first_failing_invariant`, `affected_boundary`, and one of the supported classifications.
- `protected_paths`: immutable predecessor Acceptance/Evidence. They are snapshotted from the task's initial Git authority and guarded at commit boundaries.
- `source_paths`: source/config paths that are hashed from the immutable `source_commit` and may be referenced by canonical Evidence `source_hashes`.
- `finalization_paths`: all paths allowed to be dirty before the pre-canonical source-finalization commit. This should include `source_paths` plus durable task-history/diagnosis files created before canonical execution. If omitted, it defaults to `source_paths`.
- `canonical.command`: exact canonical producer command. It may change only declared `canonical.evidence_paths` after `source_commit` is frozen.
- `literal_validation`: exact argv commands that must exit 0 before Review. Resolved executable, interpreter, exit code, test count when detectable, and Git SHA are recorded.

## Gate failure protocol

Example failed gate output:

```text
GATE_RESULT_JSON:{"gate_id":"G4","finding_id":"SIM011-G4-001","root_cause_class":"CORRELATION","first_failing_invariant":"request_identity","affected_boundary":"collector","classification":"SAME_GATE"}
```

`SAME_GATE` and `REGRESSION` permit one bounded `gate_fix` worker cycle and then rerun the same gate. The same normalized invariant reaching the third failure produces `ARCHITECTURE_REVIEW_REQUIRED`. `NEW_EXTERNAL_FAULT_DOMAIN` and `CONTRACT_OR_ARCHITECTURE_CONTRADICTION` stop immediately.

## Resume behavior

The new host-owned resumable phases are:

- `gate_resolution`
- `finalization`
- `literal_validation`

For staged tasks, `resume --force` after a branch/HEAD mismatch invalidates prior gate baselines, supplier cache, `source_commit` binding, literal validation, and review readiness. It does not treat stale proof as current proof.

## Review boundary

The independent Review remains downstream of qualification. Before review-boundary commits the orchestrator verifies:

1. `HEAD == finalization.source_commit`;
2. no `source_paths` are dirty;
3. canonical Evidence still matches the SHA-256 recorded during finalization;
4. Evidence still declares the same `source_git_sha` and reproducible source hashes;
5. literal validation results are PASS records bound to the same source commit.

This keeps `source_commit` distinct from the existing `accepted_commit`.
