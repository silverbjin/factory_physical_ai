## Context Budget Policy

Codex must use bounded context by default.

### Implementation tasks

Read in this order:

1. `AGENTS.md`
2. the active `TASK-*.md`
3. only files explicitly listed in the Task's `Required Context`
4. task-related source paths only

Do NOT recursively read:

- `context/`
- `docs/`
- `plans/`
- `tasks/`
- repository history

unless the active Task explicitly requires it.

Do not read previous Task specifications merely to reconstruct
project history.

Expand context only when a concrete blocker requires a specific file.

### Review tasks

Read only:

- active Task specification;
- diff against merge base;
- task-related tests;
- task-related evidence;
- exact contract/ADR files required to verify a changed boundary.

Do not perform project-wide rediscovery.

### Fix tasks

Fix only the cited review findings.

Inspect:

- the findings;
- changed files;
- delta since the reviewed revision.

Do not repeat a full repository review unless the fix changes
architecture or contract boundaries.

### Project state

Current project state is not stored in `AGENTS.md`.

Use:

- `context/current_project_state.md`
- `context/task_mapping.md`

only when planning or creating tasks, not during ordinary
implementation unless explicitly listed as Required Context.