#!/usr/bin/env python3

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEWED_COMMIT = "6a30757602ea0fd7e540b2c3b10b9cab1c610ac0"

EXPECTED = {
    "results/simulation/SIM-GATE_readiness.json":
        "82c837e519c37799cb5a88af14470d2b74ba5d75913e811eac752f8e80f8b312",
    "scripts/verify_simulation_lane_gate.py":
        "04b23c1734b18e7ef96cd534dc7ff70dd31d5d602a4c54add6cba861ab917637",
    "tests/test_simulation_lane_gate.py":
        "a036e13a324ea16185ce03ad3232a6ae830e1c712164f3e6bb415e2205ab30ae",
    "docs/simulation/simulation_lane_gate_v1.md":
        "036cc02fef12e146ba3e18af99dc19a9d87c49369a295d3e3f582fa38be711fd",
    "results/reviews/SIM-001_acceptance.json":
        "bf1fe8df30a73339fcdd90a5bbc3d0cf5963a0a02d538102e732054e175f5e53",
    "results/reviews/SIM-002_acceptance.json":
        "07ee8867208498719b1a5bed04fb7572a881e2e470b6d218648aaecaf5d02951",
}

EXPECTED_PAYLOAD_SHA = (
    "543bf8387ee0c9045e715efd805a0c439a0684df89a7af349320e83df94d6fc3"
)

OUTPUT = ROOT / "results/reviews/SIM-GATE_acceptance.json"


def fail(message):
    print(f"[FAIL] {message}", file=sys.stderr)
    sys.exit(1)


def run_git(*args):
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes())


def git_blob(commit, path):
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"{path} does not exist in reviewed commit {commit}")
    return result.stdout


def find_payload_sha(obj):
    if isinstance(obj, dict):
        for key in ("payload_sha256", "payload_hash", "canonical_payload_sha256"):
            if key in obj:
                return obj[key]
        for value in obj.values():
            found = find_payload_sha(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_payload_sha(value)
            if found:
                return found
    return None


def find_gate_result(obj):
    if isinstance(obj, dict):
        for key in ("gate_result", "decision", "task_specific_decision"):
            value = obj.get(key)
            if value == "SIM_GO":
                return value
        for value in obj.values():
            found = find_gate_result(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_gate_result(value)
            if found:
                return found
    return None


# ----------------------------------------------------------------------
# 1. Repository sanity
# ----------------------------------------------------------------------

run_git("cat-file", "-e", f"{REVIEWED_COMMIT}^{{commit}}")

head = run_git("rev-parse", "HEAD")

if subprocess.run(
    ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", REVIEWED_COMMIT, head]
).returncode != 0:
    fail(f"reviewed commit {REVIEWED_COMMIT} is not an ancestor of HEAD {head}")

status = run_git("status", "--porcelain")

if status:
    fail(
        "worktree is not clean. Commit or discard unrelated changes before "
        "recording acceptance."
    )


# ----------------------------------------------------------------------
# 2. Verify current canonical hashes
# ----------------------------------------------------------------------

verified = {}

for relpath, expected_sha in EXPECTED.items():
    path = ROOT / relpath

    if not path.is_file():
        fail(f"missing canonical artifact: {relpath}")

    actual_sha = sha256_file(path)

    if actual_sha != expected_sha:
        fail(
            f"canonical SHA mismatch for {relpath}: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    verified[relpath] = {
        "sha256": actual_sha,
    }


# ----------------------------------------------------------------------
# 3. Verify reviewed commit contains EXACT reviewed Gate content
#
# Only Gate implementation artifacts are expected to exist in
# REVIEWED_COMMIT. Post-review acceptance artifacts are intentionally
# excluded from this comparison.
# ----------------------------------------------------------------------

REVIEWED_GATE_ARTIFACTS = (
    "results/simulation/SIM-GATE_readiness.json",
    "scripts/verify_simulation_lane_gate.py",
    "tests/test_simulation_lane_gate.py",
    "docs/simulation/simulation_lane_gate_v1.md",
)

for relpath in REVIEWED_GATE_ARTIFACTS:
    expected_sha = EXPECTED[relpath]

    blob_sha = sha256_bytes(git_blob(REVIEWED_COMMIT, relpath))

    if blob_sha != expected_sha:
        fail(
            f"reviewed Git blob mismatch for {relpath}: "
            f"expected={expected_sha} git_blob={blob_sha}"
        )

    verified[relpath]["reviewed_commit_blob_sha256"] = blob_sha


# ----------------------------------------------------------------------
# 4. Verify Gate evidence semantic fields
# ----------------------------------------------------------------------

evidence_path = ROOT / "results/simulation/SIM-GATE_readiness.json"

try:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"cannot parse Gate evidence: {exc}")

gate_result = find_gate_result(evidence)

if gate_result != "SIM_GO":
    fail(f"canonical Gate result is not SIM_GO: {gate_result!r}")

payload_sha = find_payload_sha(evidence)

if payload_sha != EXPECTED_PAYLOAD_SHA:
    fail(
        "Gate payload SHA mismatch: "
        f"expected={EXPECTED_PAYLOAD_SHA} actual={payload_sha}"
    )


# ----------------------------------------------------------------------
# 5. Create transparent human-equivalence acceptance
# ----------------------------------------------------------------------

if OUTPUT.exists():
    fail(
        f"{OUTPUT.relative_to(ROOT)} already exists; "
        "refusing to overwrite an acceptance record"
    )

acceptance = {
    "schema_version": "1.0",
    "task_id": "TASK-SIM-GATE",

    "review_decision": "ACCEPT",
    "task_specific_decision": "SIM_GO",

    "reviewed_commit": REVIEWED_COMMIT,

    "review_provenance": {
        "method": "human_content_equivalence_attestation",
        "stable_commit_directly_reviewed_by_codex": False,
        "basis": (
            "A prior independent READ-ONLY review returned ACCEPT for the "
            "same Gate content before that worktree was committed. "
            "This recording independently verifies that the stable Git "
            "commit contains byte-identical Gate artifacts."
        ),
        "content_equivalence_verified": True,
    },

    "gate_evidence": {
        "path": "results/simulation/SIM-GATE_readiness.json",
        "sha256": EXPECTED[
            "results/simulation/SIM-GATE_readiness.json"
        ],
        "payload_sha256": EXPECTED_PAYLOAD_SHA,
    },

    "gate_verifier": {
        "path": "scripts/verify_simulation_lane_gate.py",
        "sha256": EXPECTED[
            "scripts/verify_simulation_lane_gate.py"
        ],
    },

    "gate_tests": {
        "path": "tests/test_simulation_lane_gate.py",
        "sha256": EXPECTED[
            "tests/test_simulation_lane_gate.py"
        ],
    },

    "gate_report": {
        "path": "docs/simulation/simulation_lane_gate_v1.md",
        "sha256": EXPECTED[
            "docs/simulation/simulation_lane_gate_v1.md"
        ],
    },

    "predecessor_acceptance": {
        "SIM-001": {
            "path": "results/reviews/SIM-001_acceptance.json",
            "sha256": EXPECTED[
                "results/reviews/SIM-001_acceptance.json"
            ],
        },
        "SIM-002": {
            "path": "results/reviews/SIM-002_acceptance.json",
            "sha256": EXPECTED[
                "results/reviews/SIM-002_acceptance.json"
            ],
        },
    },

    "authorization": {
        "simulation_lane_authorized": True,

        "task_w1_001_authorized": False,
        "task_w1_002_authorized": False,

        "dataset_v1_authorized": False,
        "fine_tuning_authorized": False,
        "physical_motion_authorized": False,
        "hardware_target_frozen": False,

        "p0_004r": "NO_GO",
    },

    "verification": {
        "git_blob_equivalence": True,
        "canonical_hashes_verified": True,
        "payload_hash_verified": True,
        "gate_result_verified": True,
        "worktree_clean_before_recording": True,
    },

    "recorded_at": datetime.now(timezone.utc).isoformat(),

    "note": (
        "This record uses deterministic content-equivalence verification "
        "plus explicit human approval instead of consuming additional "
        "Codex credits for a duplicate review of byte-identical content."
    ),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(acceptance, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("[PASS] SIM-GATE acceptance recorded")
print(f"reviewed_commit: {REVIEWED_COMMIT}")
print(f"current_head:    {head}")
print(f"gate_result:     {gate_result}")
print("simulation_lane_authorized: true")
print(f"output: {OUTPUT.relative_to(ROOT)}")
print(f"output_sha256: {sha256_file(OUTPUT)}")
