#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

for evidence_path in (Path("results/mvp/MVP-006.json"), Path("results/mvp/MVP-007.json")):
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "PASS", evidence_path
    for item in evidence["source_files"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
    for item in evidence["run_artifacts"].values():
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
print("Day-10 MVP evidence validation: PASS")
PY
