# Codex TASK Orchestration — Review Commits + Acceptance Recording

## 1. Recommended model assignment

The runner pins the model per role using:

```text
config/codex_model_policy.json
```

Default:

```text
Implementation → GPT-5.6 Terra / medium
Review         → GPT-5.6 Sol   / low
Fix            → GPT-5.6 Terra / medium
Re-review      → GPT-5.6 Sol   / low
Acceptance     → GPT-5.6 Luna  / low
```

Acceptance uses Luna because it is a narrow structured provenance-recording task,
not a new design or independent quality judgment.

If the acceptance schema becomes completely deterministic, replacing the Acceptance
LLM worker with a Python recorder is an even cheaper future optimization.

---

## 2. Install

Copy these files into the repository:

```text
AGENTS.md
config/codex_model_policy.json
prompts/codex/run_task_workflow_v2.md
prompts/codex/run_task_range_v2.md
prompts/codex/record_task_acceptance_v2.md
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
```

Apply the small existing-worker marker changes documented in:

```text
MODIFICATIONS.md
```

Optional:

```bash
chmod +x scripts/codex/run_task_orchestrator.py
```

---

## 3. Preconditions

Verify Codex CLI:

```bash
which codex
codex --version
```

Verify Git identity:

```bash
git config user.name
git config user.email
```

Automation requires a clean worktree:

```bash
git status --short
```

Use a dedicated branch:

```bash
git switch -c automate/sim-002-004
```

`main` and `master` are blocked by default.

---

## 4. Unit tests

From repository root:

```bash
python3 -m unittest scripts/codex/test_run_task_orchestrator.py
```

If import resolution differs in your repository, use:

```bash
cd scripts/codex
python3 test_run_task_orchestrator.py
```

---

## 5. Single TASK

Codex command:

```text
Run TASK-SIM-003
```

Direct equivalent:

```bash
python3 scripts/codex/run_task_orchestrator.py task TASK-SIM-003
```

First-pass ACCEPT:

```text
Implement [Terra]
→ Review ACCEPT [Sol]
→ commit reviewed snapshot
→ Record acceptance [Luna]
→ commit SIM-003_acceptance.json
→ ACCEPTED
```

Example Git log:

```text
<acceptance> chore(sim): record TASK-SIM-003 acceptance [ACCEPT]
<reviewed>   feat(sim): TASK-SIM-003 implementation reviewed [ACCEPT]
```

The acceptance JSON records `<reviewed>` as `accepted_commit`.

---

## 6. REJECT → Fix → ACCEPT

```text
Implement [Terra]
→ Review REJECT [Sol]
→ commit REJECT snapshot
→ Fix [Terra]
→ Re-review ACCEPT [Sol]
→ commit fixed accepted snapshot
→ Record acceptance [Luna]
→ commit acceptance JSON
→ ACCEPTED
```

Example:

```text
C chore(sim): record TASK-SIM-003 acceptance [ACCEPT]
B fix(sim): TASK-SIM-003 review findings resolved [ACCEPT]
A feat(sim): TASK-SIM-003 implementation reviewed [REJECT]
```

The acceptance JSON records commit `B`, not commit `C`.

---

## 7. TASK range

```text
Run TASK-SIM-002..TASK-SIM-004
```

Direct equivalent:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  range TASK-SIM-002 TASK-SIM-004
```

The next TASK starts only after:

```text
Review ACCEPT
+
accepted snapshot commit
+
acceptance JSON for that exact snapshot
+
acceptance-record commit
+
clean worktree
```

If Acceptance recording fails for TASK-SIM-003, TASK-SIM-004 is not started.

---

## 8. Model policy customization

Edit:

```text
config/codex_model_policy.json
```

Example acceptance override:

```json
"acceptance": {
  "model": "gpt-5.6-luna",
  "reasoning_effort": "low"
}
```

The runner explicitly passes both `--model` and `model_reasoning_effort` to each
`codex exec`. This avoids relying on a changing global/default model.

---

## 9. Fix retry budget

Default:

```text
1 Fix + Re-review cycle
```

Disable automatic Fix:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --max-fix-cycles 0 \
  task TASK-SIM-003
```

For credit control, keep the default at `1`.

---

## 10. Fail-closed behavior

The automation stops if:

- Implementation workflow is incomplete;
- Review workflow is incomplete;
- Fix is not ready;
- Re-review remains REJECT after the retry budget;
- reviewed snapshot commit fails;
- Acceptance worker fails;
- Acceptance worker modifies anything except the one acceptance JSON;
- Acceptance JSON does not reference the exact accepted commit;
- acceptance-record commit fails;
- worktree is not clean at a boundary.

A Review `ACCEPT` alone is therefore not enough to advance the range.

For orchestration, the TASK becomes `ACCEPTED` only after acceptance Evidence is
successfully recorded and committed.
