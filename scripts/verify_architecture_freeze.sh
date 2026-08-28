#!/usr/bin/env bash
# Non-destructive documentation audit for the P0-002 architecture freeze.
set -u -o pipefail

RESULT_PATH="${RESULT_PATH:-results/phase0/architecture_freeze_evidence.json}"
mkdir -p "$(dirname "$RESULT_PATH")"
required_failures=0
names=(); statuses=(); details=()

record() {
  names+=("$1"); statuses+=("$2"); details+=("$3")
  printf '%-4s %s — %s\n' "$2" "$1" "$3"
  [[ "$2" == FAIL ]] && required_failures=$((required_failures + 1))
}

require_text() {
  local name="$1" file="$2" text="$3"
  if [[ -f "$file" ]] && rg -Fq "$text" "$file"; then record "$name" PASS "$file"; else record "$name" FAIL "missing required freeze evidence in $file"; fi
}

escape_json() { local v="$1"; v=${v//\\/\\\\}; v=${v//\"/\\\"}; printf '%s' "$v"; }

require_text day10_scope docs/architecture/day10_mvp_scope_v1.md '## Explicitly out of scope'
require_text mock_only docs/architecture/day10_mvp_scope_v1.md 'One fake model provider'
require_text nav2_ownership docs/contracts/contract_plan.md 'Nav2 owns local planning'
require_text moveit_ownership docs/contracts/contract_plan.md 'MoveIt for named staging poses'
require_text reconciliation docs/contracts/contract_plan.md 'unknown`; the executor must query'
require_text vla_gate docs/architecture/adr/ADR-004-vla-stack.md 'time-boxed VLA readiness decision'
require_text sequencing plans/next_tasks_after_phase0.md 'must not wait for VLA hardware'
require_text review_resolution docs/reviews/P0-001_architecture_review.md '## P0-002 resolution record'

{
  printf '{\n  "schema_version": "1.0",\n'
  printf '  "evidence_kind": "documentation_audit",\n'
  printf '  "generated_at": "%s",\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  printf '  "git_commit": "%s",\n' "$(git rev-parse HEAD)"
  printf '  "scope": "P0-002 architecture freeze; no runtime, hardware, or model claim",\n'
  printf '  "checks": [\n'
  for i in "${!names[@]}"; do
    comma=','; [[ "$i" -eq $((${#names[@]} - 1)) ]] && comma=''
    printf '    {"name":"%s","status":"%s","detail":"%s"}%s\n' "$(escape_json "${names[$i]}")" "${statuses[$i]}" "$(escape_json "${details[$i]}")" "$comma"
  done
  printf '  ],\n  "required_failures": %s\n}\n' "$required_failures"
} > "$RESULT_PATH"

printf 'Evidence: %s\n' "$RESULT_PATH"
[[ "$required_failures" -eq 0 ]] || exit 1
