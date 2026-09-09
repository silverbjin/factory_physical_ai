# TASK-XXX — Title

## Metadata

- Related Backlog:
- Phase:
- Dependency:
- Branch:
- Worktree:

## Goal

...

## Required Context

Read only:

- `...`
- `...`

## Relevant Repository Paths

Inspect first:

- `...`

## Inputs / Evidence

- `...`

## Scope

...

## Explicit Out-of-Scope

...

## Architecture Constraints

...

## Required Outputs

...

## Validation Commands

...

## Evidence

...

## Exit Criteria
- `...`
- `...`

## Review Scope

Reviewer should inspect only:

- this Task
- `git diff <merge-base>...HEAD`
- task-related Evidence
- task-related tests
- exact contracts listed above

## Context Expansion Rule

If additional project context appears necessary:

1. identify the concrete missing fact;
2. identify the exact file likely to contain it;
3. read that file only;
4. do not recursively search all context/docs/plans.

## Project State Update

After merge update:

- `context/current_project_state.md`
- `context/session_handoff.md`

Update `task_mapping.md` only if dependency/mapping changed.

## Recommended Commit

...

## Codex Execution Prompt

Implement TASK-XXX only.

Read:

- AGENTS.md
- this Task
- Required Context listed above

Do not perform repository-wide rediscovery.
