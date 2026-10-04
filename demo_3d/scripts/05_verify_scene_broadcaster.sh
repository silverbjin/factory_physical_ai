#!/usr/bin/env bash
set -euo pipefail

ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

SERVER_PID="$(
  for p in $(pgrep -f 'gz sim|ign gazebo' 2>/dev/null || true); do
    [[ -r "/proc/$p/cmdline" ]] || continue
    cmd="$(tr '\0' ' ' <"/proc/$p/cmdline" 2>/dev/null)"
    if [[ "$cmd" == *"gz sim"* && "$cmd" == *" -s "* ]]; then
      echo "$p"
    fi
  done | tail -1
)"

if [[ -z "${SERVER_PID:-}" ]]; then
  echo "[VERIFY] No live Gazebo server found." >&2
  exit 2
fi

GZ_PARTITION="$(
  tr '\0' '\n' <"/proc/$SERVER_PID/environ" \
    | sed -n 's/^GZ_PARTITION=//p' | head -1
)"
ROS_DOMAIN_ID="$(
  tr '\0' '\n' <"/proc/$SERVER_PID/environ" \
    | sed -n 's/^ROS_DOMAIN_ID=//p' | head -1
)"
export GZ_PARTITION
export IGN_PARTITION="$GZ_PARTITION"
export ROS_DOMAIN_ID

echo "[VERIFY] server_pid=$SERVER_PID"
echo "[VERIFY] GZ_PARTITION=$GZ_PARTITION"
echo "[VERIFY] ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

echo
echo "[VERIFY] Scene service:"
SCENE="$(
  gz service -l \
    | grep -E '^/world/.+/scene/info$' \
    | head -1 || true
)"
echo "${SCENE:-MISSING}"

echo
echo "[VERIFY] Runtime SDF:"
SDF="$(
  tr '\0' ' ' <"/proc/$SERVER_PID/cmdline" \
    | grep -oE '/[^ ]+\.(sdf|world)' \
    | head -1
)"
echo "${SDF:-MISSING}"

if [[ -n "${SDF:-}" && -f "$SDF" ]]; then
  echo
  echo "[VERIFY] SceneBroadcaster in runtime SDF:"
  grep -n -A1 -B1 \
    'SceneBroadcaster\|scene-broadcaster' \
    "$SDF" || true
fi

echo
echo "[VERIFY] Demo worktree patch log:"
tail -n 8 "$ROOT/results/demo/visual_worktree_patch.jsonl" \
  2>/dev/null || true

if [[ -z "$SCENE" ]]; then
  echo
  echo "[VERIFY] FAIL: /world/.../scene/info is missing."
  exit 3
fi

echo
echo "[VERIFY] PASS: SceneBroadcaster service is available."
