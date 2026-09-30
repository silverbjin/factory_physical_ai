# Diagnosis — TASK-SIM-010

- Stage: diagnosis
- Status: RESOLVED
- Result: RESOLVED
- Read-only mode: YES
- Trigger: Repeated Implementation INCOMPLETE after prior RESOLVED Diagnosis.
- Triggering lifecycle status: INCOMPLETE
- Diagnosis tier/model: GPT-5.6 Sol / Medium

## Trigger

`Implementation #2`도 predecessor Acceptance provenance를 직접적인 `evidence` binding으로만 해석하여 `SIM_OBSERVABILITY_REGRESSION_BLOCKED`를 유지했다.

## Primary Architecture Question

TASK-SIM-010은 Evidence metadata가 Acceptance JSON 내부에 물리적으로 존재할 것을 요구하지 않는다. 현재 canonical deterministic Acceptance에서 `accepted_commit`은 독립 Review가 `ACCEPT`한 뒤 커밋된 immutable repository state를 가리킨다. 따라서 정확한 TASK-declared Evidence path를 그 commit에서 읽고 SHA256을 재계산하며 Evidence의 `task_id`와 `task_specific_result`를 검증하는 Contract B가 유효하다.

## Evidence Examined

- `tasks/TASK-SIM-010.md`
- `tasks/TASK-SIM-008.md`, `tasks/TASK-SIM-009.md` at each accepted commit
- `results/reviews/SIM-003_acceptance.json` through `SIM-009_acceptance.json`의 schema 비교
- `results/reviews/SIM-008_acceptance.json`, `results/reviews/SIM-009_acceptance.json`
- `results/simulation/SIM-008_normal_system_e2e.json` at `ea91e0c16412e20c8cae66355a1a39129919dd42`
- `results/simulation/SIM-009_failure_recovery.json` at `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be`
- accepted Review records `TASK-SIM-008/03_review.md`, `TASK-SIM-009/24_review.md`
- `scripts/codex/run_task_orchestrator.py::{expected_acceptance_path,write_deterministic_acceptance}` and lifecycle commit transitions
- `config/codex_model_policy.json`
- `prompts/codex/record_task_acceptance_v2.md`
- `src/simulation_runtime/observability_regression.py`, `scripts/run_simulation_observability_regression.py`, `tests/test_simulation_observability_regression.py`
- `docs/contracts/simulation_execution_contract_v1.md`

## Acceptance Model Comparison

두 pattern이 공존한다.

- Older/rich Acceptance는 `review_record`와 `evidence.path`/`evidence.sha256`를 직접 bind한다. SIM-008은 이 pattern이다.
- Generic deterministic Acceptance는 `task_id`, `status`, `accepted_commit`, `recorded_at`, `recording_mode`, `workflow_complete`만 기록한다. SIM-009는 이 pattern이다.

`config/codex_model_policy.json`과 실제 main lifecycle은 deterministic mode를 선택하고 `write_deterministic_acceptance()`를 직접 호출하므로 minimal manifest는 의도된 active schema evolution이다. 다만 `record_task_acceptance_v2.md`의 rich minimum structure와 downstream rich-only consumer가 함께 갱신되지 않은 것은 accidental compatibility gap이다. TASK-SIM-010은 두 형태를 수용하되 모든 기술 provenance를 `accepted_commit`의 Git tree에 고정해야 한다.

## SIM-008 Provenance

- Canonical Acceptance path: `results/reviews/SIM-008_acceptance.json`
- `accepted_commit`: `ea91e0c16412e20c8cae66355a1a39129919dd42`
- Canonical Evidence path: `results/simulation/SIM-008_normal_system_e2e.json`
- Evidence SHA256 at accepted commit: `ebf0ef0a27114e3c04fa6bec05aa3eef792fdfc282d2be009640bac7ecc26290`
- Canonical task-specific decision: `SIM_NORMAL_E2E_READY`
- Acceptance sufficient: YES; direct Evidence binding이 accepted Git blob과 일치한다.
- `accepted_commit` sufficient: YES; accepted TASK spec이 exact Evidence path와 허용 decision을 선언하며 blob은 정확히 1개 존재한다.
- Missing provenance: NONE for identity/path/hash/decision. 다만 normalized SIM-010 envelope로의 shape adaptation은 resolver 책임이다.

## SIM-009 Provenance

- Canonical Acceptance path: `results/reviews/SIM-009_acceptance.json`
- `accepted_commit`: `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be`
- Canonical Evidence path: `results/simulation/SIM-009_failure_recovery.json`
- Evidence SHA256 at accepted commit: `91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e`
- Canonical task-specific decision: `SIM_FAILURE_SUITE_READY`
- Acceptance sufficient: NO when interpreted as a standalone JSON; it has no direct Evidence binding.
- `accepted_commit` sufficient: YES; accepted TASK spec and TASK-SIM-010 both declare the exact Evidence path, the accepted tree contains exactly that blob, and its top-level decision matches the required value.
- Missing provenance: direct duplicate `evidence.path`/`evidence.sha256` fields only; immutable accepted-state provenance is not missing.

## Root Cause

`build_regression_evidence()` assumes every Acceptance uses the older rich schema and reads predecessor Evidence from the current working tree. It therefore rejects the canonical minimal SIM-009 Acceptance before following `accepted_commit`. It also expects an already-normalized top-level predecessor payload, although TASK-SIM-010 owns creation of the normalized envelope and SIM-008/SIM-009 retain their task-specific nested Evidence shapes.

## Violated or Missing Contract

The active generic Acceptance contract and the SIM-010 consumer are schema-incompatible. This is a consumer migration defect, not absent predecessor truth: `accepted_commit` plus exact TASK-declared Evidence identity provides the immutable source. `record_task_acceptance_v2.md` still documents the legacy rich form and should be treated as a separate repository-wide documentation/tooling inconsistency, not repaired inside TASK-SIM-010.

## Primary Fault Domain

`SIM010_IMPLEMENTATION_DEFECT`

Secondary finding: `ACCEPTANCE_SCHEMA_MISMATCH` between rich and generic deterministic manifests.

## Architecture Decision

Primary disposition: `SIM010_RESOLVER_CHANGE`.

Use a dual-form fail-closed resolver:

1. validate canonical Acceptance identity/status and a full immutable `accepted_commit`;
2. resolve only the exact Evidence path declared by the TASK contract (direct rich binding when present; otherwise the fixed task-specific path declared by the accepted TASK spec/TASK-SIM-010);
3. read the blob from `accepted_commit`, never from the working tree;
4. recompute SHA256 and compare a rich binding when one exists;
5. validate Evidence `task_id` and extract the contract-defined `task_specific_result` from Evidence;
6. normalize task-specific Evidence shapes into the SIM-010 index without changing predecessors;
7. fail closed on an invalid commit, missing exact blob, conflicting rich binding, wrong task ID/result, malformed JSON, or ambiguous/undeclared path.

No additive manifest, Acceptance schema change, or predecessor repair is needed for TASK-SIM-010.

## Required Architecture Answers

- Q1 — Evidence metadata physically inside Acceptance JSON: `NO`
- Q2 — `accepted_commit` authoritative immutable provenance root: `YES`
- Q3 — canonical SIM-008 Evidence deterministically resolvable: `YES`
- Q4 — canonical SIM-009 Evidence deterministically resolvable: `YES`
- Q5 — authoritative `task_specific_decision`: `Evidence`
- Q6 — existing SIM-008/SIM-009 Acceptance records may be modified: `NO`
- Q7 — minimum authorized correction boundary: `SIM010_RESOLVER_CHANGE`
- Q8 — protected artifacts: predecessor Acceptance, Evidence, TASK/history/review records; repository Acceptance tooling/policy; contracts; all unrelated production/test/config surfaces.

## Authorized Correction Boundary

- `src/simulation_runtime/observability_regression.py`: accepted-commit resolver, exact source-contract mapping/validation, Git-blob SHA256, decision extraction, and predecessor-shape normalization.
- `tests/test_simulation_observability_regression.py`: rich/minimal Acceptance fixtures and positive/negative accepted-tree provenance tests.
- `scripts/run_simulation_observability_regression.py` only if required to pass repository root/Git access into the resolver without changing its orchestration behavior.
- TASK-SIM-010-owned generated artifacts after successful validation: `results/simulation/SIM-010_observability_regression.json` and `docs/simulation/simulation_observability_regression_v1.md`.

## Protected Boundary

Do not modify:

- `results/reviews/SIM-008_acceptance.json`, `results/reviews/SIM-009_acceptance.json`;
- `results/simulation/SIM-008_normal_system_e2e.json`, `results/simulation/SIM-009_failure_recovery.json`;
- SIM-008/SIM-009 TASK specs, source, tests, configs, Review/history, Evidence, contracts, or accepted commits;
- `scripts/codex/run_task_orchestrator.py`, `config/codex_model_policy.json`, `prompts/codex/record_task_acceptance_v2.md`;
- unrelated failing tests or production/config surfaces.

Accepted canonical Acceptance records are immutable for this correction.

## Required Verification

- Focused command: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_observability_regression.py`
- Prove rich SIM-008 direct binding and minimal SIM-009 accepted-commit resolution both pass.
- Prove Evidence is read from the accepted Git tree even when the working-tree file differs.
- Prove SHA256 is recomputed from exact blob bytes and rich binding mismatch fails closed.
- Prove invalid/missing commit, undeclared or missing path, malformed JSON, task mismatch, unexpected decision, and direct-binding/path conflict fail closed.
- Run the TASK aggregator and confirm the index records Acceptance path/hash, accepted commit, exact Evidence path/hash, and extracted decision.
- Run `git diff --check`.

## Regression Baseline Requirement

The reported four full-suite failures are `UNPROVEN`; prior worker prose is not baseline proof. Post-diagnosis implementation validation must run the identical full pytest command in a disposable clean worktree at baseline commit `6909c6cceb727598570f6e170ae8d1d293418c9a`, then in the corrected TASK-SIM-010 worktree. Classify failures as `PROVEN_PREEXISTING` only when the same node IDs and failure signatures reproduce at baseline; otherwise classify them `POSSIBLY_TASK_RELATED` and keep TASK-SIM-010 blocked. Do not repair unrelated failures in this TASK.

## Handoff / Next Action

- Next action: RESUME_IMPLEMENTATION

## Next Action

`AUTONOMOUS_IMPLEMENTATION_VALIDATE`

Final diagnosis status: RESOLVED
