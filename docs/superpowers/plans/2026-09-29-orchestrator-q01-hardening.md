# Codex Task Orchestrator Q01 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in staged integration/provenance lifecycle to the existing orchestrator while preserving legacy behavior.

**Architecture:** Keep `run_task_orchestrator.py` as the compatibility entry point. Add small typed helpers and state transitions inside the existing file; use a task-side JSON contract to activate staged qualification. Host-side subprocess execution remains authoritative for gates/finalization/literal validation, while Codex remains bounded to diagnosis/fix/review roles.

**Tech Stack:** Python 3 stdlib, Git CLI, subprocess, unittest/pytest-compatible tests.

**Spec:** `docs/superpowers/specs/2026-09-29-orchestrator-q01-hardening-design.md`

## Global Constraints
- Legacy tasks without `tasks/orchestrator/<TASK_ID>.json` must preserve current lifecycle behavior.
- `accepted_commit` semantics must not change.
- Staged qualification is fail-closed.
- Protected predecessor artifacts are never auto-restored.
- Gate correction budget is separate from review fix budget.
- Exact validation argv is the authority; shell interpolation is not used.

## Review Focus
- v2 checkpoint compatibility must not silently discard existing diagnosis/fix state.
- `--force` must invalidate stale proof only for staged tasks and must not fake a PASS.
- protected path parsing must handle staged, unstaged, deletion, and rename status.
- source-finalization must not accidentally commit protected artifacts.
- gate failure payload parsing must fail closed when machine-readable blocker data is missing.

---

### Task 1: ORCH-A — schema v3, task contract, lifecycle routing
**Files:** Modify `scripts/codex/run_task_orchestrator.py`; Test `tests/test_orchestrator_q01_hardening.py`.
**Interfaces:** Produce `TaskOrchestratorContract`, `load_task_orchestrator_contract()`, `upgrade_checkpoint_state()`, staged phase routing.
- [ ] Write failing tests for contract loading, v2->v3 upgrade, staged implementation->gate routing, legacy implementation->review routing.
- [ ] Run focused tests and verify RED.
- [ ] Implement minimal schema/contract/routing support.
- [ ] Run focused tests and verify GREEN.
- [ ] Commit.

### Task 2: ORCH-B — host-owned gate resolver
**Files:** Modify orchestrator and tests.
**Interfaces:** Produce normalized blocker signature, gate cursor/baseline state, same-invariant attempt counter, attempt-scoped supplier cache invalidation.
- [ ] Write failing tests for sequential blockers, three-strike escalation, external stop, resume cursor, supplier cache attempt scoping.
- [ ] Verify RED.
- [ ] Implement minimal gate execution/state helpers and lifecycle transition.
- [ ] Verify GREEN and baseline suite.
- [ ] Commit.

### Task 3: ORCH-C — immutable source finalization
**Files:** Modify orchestrator and tests.
**Interfaces:** Produce `source_commit`, canonical execution result, evidence source binding verification.
- [ ] Write failing tests for source commit creation and SHA/source-hash mismatch rejection.
- [ ] Verify RED.
- [ ] Implement source-finalization commit and canonical evidence binding verification.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 4: ORCH-D — protected artifact guard
**Files:** Modify orchestrator and tests.
**Interfaces:** Produce protected snapshot and commit-boundary validation.
- [ ] Write failing tests for protected modification/deletion and allowed unprotected changes.
- [ ] Verify RED.
- [ ] Implement snapshot/guard and integrate it into commit helpers.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 5: ORCH-E — literal validation, force invalidation, aggregate accounting
**Files:** Modify orchestrator and tests.
**Interfaces:** Produce exact argv validation records, cumulative checkpoint metrics, staged proof invalidation on forced HEAD mismatch.
- [ ] Write failing tests for executable/interpreter provenance, non-zero validation stop, aggregate resume, force invalidation.
- [ ] Verify RED.
- [ ] Implement minimal helpers and report integration.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 6: ORCH-F — compatibility and integrated verification
**Files:** Tests plus final documentation adjustments if required.
**Interfaces:** No new production API; prove the composed lifecycle.
- [ ] Add an integrated staged lifecycle test and explicit legacy regression test.
- [ ] Verify RED for any uncovered path.
- [ ] Make only minimal production corrections needed by integration.
- [ ] Run complete test suite and `py_compile`.
- [ ] Commit verification changes.
