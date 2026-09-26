# Architecture Decision — Freeze MIN-Q01 for SIM-010

- Decision: `Q01_MINIMAL_REQUIRED`
- Architecture state: `MIN_Q01_CONTRACT_FROZEN`
- Previous state: Full-Q01, with a 25-subject readiness manifest
- Analyzed implementation HEAD: `57b64b46b42cdfabb7030581180a712ba200dfce`
- Runtime qualification executed by this transition: NO
- Qualification accepted by this transition: NO

## Context

The Full-Q01 design promoted internal runs from conditional SIM-004 and
SIM-005 provenance sources, plus SIM-007 profile aggregates, into mandatory
new qualification subjects. A read-only reverse trace against the frozen
`TASK-SIM-010` contract found that this was broader than the downstream
dependency.

SIM-010 directly requires the accepted SIM-008 normal run and all mandatory
SIM-009 failure/recovery scenarios. SIM-004 and SIM-005 are conditional
sources for version-wide backend authority. SIM-007 profile/source authority
can be resolved from its immutable accepted Git tree without a new runtime
session.

The decision preserves the true additive gap: SIM-008 needs distinct
execution-bound bridge and launch/run authority, and the applicable SIM-009
Gazebo/MuJoCo scenarios need scenario-bound run-local provenance.

## Decision

Freeze MIN-Q01 as exactly eleven operation subjects:

- one SIM-008 normal-system authority qualification;
- four SIM-009 Gazebo Navigation qualifications;
- six SIM-009 MuJoCo qualifications.

The deterministic machine contract is
`configs/simulation/min_q01_scope.json`. The normative task contract is
`tasks/TASK-SIM-Q01-MIN.md`.

MIN-Q01 retains the existing canonical Q01 Evidence path, Acceptance path,
task identity, and `SIM_PROVENANCE_QUALIFICATION_READY | BLOCKED` tokens to
avoid an unimplemented SIM-010 consumer migration.

## Excluded Full-Q01 work

The SIM-010 dependency gate no longer requires:

- three standalone SIM-004 operation qualifications;
- seven standalone SIM-005 operation qualifications;
- standalone SIM-005 `mujoco-invalid-observation` qualification;
- four new SIM-007 runtime/profile qualification sessions;
- the Full-Q01 25-subject completeness gate;
- the Full-Q01 Markdown report as a mandatory downstream artifact.

These historical implementation paths remain in the repository. They are not
deleted, rewritten, or claimed to have passed.

## Preserved implementation

The following existing Q01 implementation is reusable within the frozen
scope:

- immutable predecessor resolver;
- qualification models, applicability validator, aggregator, and JSON writer;
- SIM-008 execution, run-local extraction, collector, and live supplier;
- SIM-009 execution, run-local extraction, collector, and live supplier.

No runtime implementation changed in this architecture transition.

## Applicability consequence

Structured simulator time and physics measurement are required only when the
actual execution reaches the corresponding simulator/physics boundary. A
structured early rejection or pre-physics failure may declare those fields
`NOT_APPLICABLE`. Missing required provenance remains fail-closed.

This rule prevents Full-Q01's standalone SIM-005 invalid-observation lookup
failure from blocking MIN-Q01 while retaining the mandatory, scenario-bound
SIM009 VLA ambiguous outcome.

## Downstream consequence

After independent MIN-Q01 Acceptance, SIM-010 resumes at its Q01-aware
resolver and Evidence-regeneration step. It may consume only the claim scopes
declared by the eleven subjects plus the immutable non-execution authority.
It must not infer Full-Q01 completion or success of excluded subjects.

## Protected scope

This decision does not modify accepted SIM-004, SIM-005, SIM-007, SIM-008, or
SIM-009 Acceptance/Evidence, the frozen SIM-010 implementation/state, or the
existing Full-Q01 task specification/history.

## Reopening rule

Future work may expand MIN-Q01 only through a new explicit architecture
decision. A newly discovered dependency must report
`MIN_Q01_SCOPE_REOPEN_REQUIRED`, identify its authoritative SIM-010 source,
explain why this freeze missed it, and state the minimum contract change.
