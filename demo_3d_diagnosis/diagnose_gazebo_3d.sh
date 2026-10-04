#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-$ROOT/results/demo/diagnostics/gazebo_3d_${STAMP}}"
mkdir -p "$OUT"

REPORT="$OUT/REPORT.txt"
SUMMARY="$OUT/SUMMARY.txt"

say() {
  printf '%s\n' "$*" | tee -a "$REPORT"
}

section() {
  printf '\n============================================================\n' | tee -a "$REPORT"
  printf '%s\n' "$*" | tee -a "$REPORT"
  printf '============================================================\n' | tee -a "$REPORT"
}

capture() {
  local name="$1"; shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$OUT/$name.txt" 2>&1 || true
}

proc_env_value() {
  local pid="$1" key="$2"
  tr '\0' '\n' <"/proc/$pid/environ" 2>/dev/null \
    | sed -n "s/^${key}=//p" | head -n1
}

proc_cmdline() {
  local pid="$1"
  tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null
}

is_server_pid() {
  local pid="$1"
  local cmd
  cmd="$(proc_cmdline "$pid")"
  [[ "$cmd" == *"gz sim"* || "$cmd" == *"ign gazebo"* ]] || return 1
  [[ "$cmd" == *" -s "* || "$cmd" == *" --server"* ]] || return 1
  [[ "$cmd" == *" -g "* ]] && [[ "$cmd" != *" -s "* ]] && return 1
  return 0
}

is_gui_pid() {
  local pid="$1"
  local cmd
  cmd="$(proc_cmdline "$pid")"
  [[ "$cmd" == *"gz sim"* || "$cmd" == *"ign gazebo"* ]] || return 1
  [[ "$cmd" == *" -g"* ]]
}

transport_cmd() {
  # Run gz/ign command with the exact server transport environment while
  # preserving current DISPLAY/WSLg desktop variables.
  local server_pid="$1"; shift
  local gzpart ignpart domain
  gzpart="$(proc_env_value "$server_pid" GZ_PARTITION)"
  ignpart="$(proc_env_value "$server_pid" IGN_PARTITION)"
  domain="$(proc_env_value "$server_pid" ROS_DOMAIN_ID)"

  env \
    ${gzpart:+GZ_PARTITION="$gzpart"} \
    ${ignpart:+IGN_PARTITION="$ignpart"} \
    ${domain:+ROS_DOMAIN_ID="$domain"} \
    "$@"
}

section "Gazebo 3D Diagnostic"
say "repo=$ROOT"
say "output=$OUT"
say "time=$(date --iso-8601=seconds 2>/dev/null || date)"

section "1. Host / WSL / Display"
capture uname uname -a
capture os_release cat /etc/os-release
{
  echo "WSL_DISTRO_NAME=${WSL_DISTRO_NAME:-}"
  echo "WSL_INTEROP=${WSL_INTEROP:-}"
  echo "DISPLAY=${DISPLAY:-}"
  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
  echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-}"
  echo "LIBGL_ALWAYS_SOFTWARE=${LIBGL_ALWAYS_SOFTWARE:-}"
  echo "MESA_D3D12_DEFAULT_ADAPTER_NAME=${MESA_D3D12_DEFAULT_ADAPTER_NAME:-}"
  echo "QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-}"
} >"$OUT/display_env.txt"

if command -v glxinfo >/dev/null 2>&1; then
  glxinfo -B >"$OUT/glxinfo.txt" 2>&1 || true
fi
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi >"$OUT/nvidia_smi.txt" 2>&1 || true
fi

section "2. Gazebo version / CLI"
if command -v gz >/dev/null 2>&1; then
  capture gz_version gz sim --versions
  capture gz_help gz sim --help
elif command -v ign >/dev/null 2>&1; then
  capture gz_version ign gazebo --versions
  capture gz_help ign gazebo --help
else
  say "FAIL: neither 'gz' nor 'ign' was found."
fi

section "3. Current Gazebo processes"
pgrep -af 'gz sim|ign gazebo' | tee "$OUT/gazebo_processes.txt" | tee -a "$REPORT" || true

SERVER_PID=""
GUI_PID=""
for p in $(pgrep -f 'gz sim|ign gazebo' 2>/dev/null || true); do
  [[ -r "/proc/$p/cmdline" ]] || continue
  if is_server_pid "$p"; then
    SERVER_PID="$p"
  elif is_gui_pid "$p"; then
    GUI_PID="$p"
  fi
done

say "detected_server_pid=${SERVER_PID:-NONE}"
say "detected_gui_pid=${GUI_PID:-NONE}"

if [[ -z "$SERVER_PID" ]]; then
  cat >"$SUMMARY" <<'EOF'
DIAGNOSIS=SERVER_NOT_RUNNING
The Gazebo GUI may be open, but no live `gz sim ... -s ...` server was found.
Run the Normal E2E demo again and execute this diagnostic while the server is still alive.
EOF
  say ""
  say "No Gazebo server is alive. See $SUMMARY"
  exit 3
fi

section "4. Server / GUI environment match"
{
  echo "SERVER PID=$SERVER_PID"
  echo "SERVER CMD=$(proc_cmdline "$SERVER_PID")"
  echo "SERVER GZ_PARTITION=$(proc_env_value "$SERVER_PID" GZ_PARTITION)"
  echo "SERVER IGN_PARTITION=$(proc_env_value "$SERVER_PID" IGN_PARTITION)"
  echo "SERVER ROS_DOMAIN_ID=$(proc_env_value "$SERVER_PID" ROS_DOMAIN_ID)"
  echo
  if [[ -n "$GUI_PID" ]]; then
    echo "GUI PID=$GUI_PID"
    echo "GUI CMD=$(proc_cmdline "$GUI_PID")"
    echo "GUI GZ_PARTITION=$(proc_env_value "$GUI_PID" GZ_PARTITION)"
    echo "GUI IGN_PARTITION=$(proc_env_value "$GUI_PID" IGN_PARTITION)"
    echo "GUI ROS_DOMAIN_ID=$(proc_env_value "$GUI_PID" ROS_DOMAIN_ID)"
  fi
} | tee "$OUT/transport_env.txt" | tee -a "$REPORT"

SERVER_GZ="$(proc_env_value "$SERVER_PID" GZ_PARTITION)"
SERVER_IGN="$(proc_env_value "$SERVER_PID" IGN_PARTITION)"
SERVER_ROS="$(proc_env_value "$SERVER_PID" ROS_DOMAIN_ID)"
GUI_GZ=""
GUI_IGN=""
GUI_ROS=""
if [[ -n "$GUI_PID" ]]; then
  GUI_GZ="$(proc_env_value "$GUI_PID" GZ_PARTITION)"
  GUI_IGN="$(proc_env_value "$GUI_PID" IGN_PARTITION)"
  GUI_ROS="$(proc_env_value "$GUI_PID" ROS_DOMAIN_ID)"
fi

MATCH=1
[[ -n "$GUI_PID" ]] || MATCH=0
[[ "$SERVER_GZ" == "$GUI_GZ" ]] || MATCH=0
[[ "$SERVER_ROS" == "$GUI_ROS" ]] || MATCH=0
say "transport_match=$MATCH"

section "5. Gazebo topics visible from SERVER environment"
if command -v gz >/dev/null 2>&1; then
  transport_cmd "$SERVER_PID" gz topic -l >"$OUT/gz_topics.txt" 2>&1 || true
  transport_cmd "$SERVER_PID" gz service -l >"$OUT/gz_services.txt" 2>&1 || true
elif command -v ign >/dev/null 2>&1; then
  transport_cmd "$SERVER_PID" ign topic -l >"$OUT/gz_topics.txt" 2>&1 || true
  transport_cmd "$SERVER_PID" ign service -l >"$OUT/gz_services.txt" 2>&1 || true
fi

grep -E '^/world/|^/clock$' "$OUT/gz_topics.txt" 2>/dev/null \
  | tee "$OUT/world_topics.txt" | tee -a "$REPORT" || true

WORLD_NAME="$(
  sed -n 's#^/world/\([^/]*\)/.*#\1#p' "$OUT/gz_topics.txt" 2>/dev/null \
    | sort -u | head -n1
)"
say "detected_world_name=${WORLD_NAME:-NONE}"

SCENE_TOPICS="$(
  grep -E '/scene|/pose/info|/dynamic_pose/info' "$OUT/gz_topics.txt" 2>/dev/null || true
)"
printf '%s\n' "$SCENE_TOPICS" >"$OUT/scene_topics.txt"
say "scene_topic_count=$(printf '%s\n' "$SCENE_TOPICS" | sed '/^$/d' | wc -l)"

section "6. One-shot scene / pose traffic probe"
PROBE_RESULT="NO_SCENE_TOPIC"
if [[ -n "$WORLD_NAME" ]]; then
  CANDIDATES=(
    "/world/$WORLD_NAME/pose/info"
    "/world/$WORLD_NAME/dynamic_pose/info"
    "/world/$WORLD_NAME/scene/info"
  )
  for topic in "${CANDIDATES[@]}"; do
    if grep -Fxq "$topic" "$OUT/gz_topics.txt" 2>/dev/null; then
      say "probing=$topic"
      if command -v gz >/dev/null 2>&1; then
        timeout 3s bash -c '
          export GZ_PARTITION="$1"
          export IGN_PARTITION="$2"
          gz topic -e -t "$3"
        ' _ "$SERVER_GZ" "${SERVER_IGN:-$SERVER_GZ}" "$topic" \
          >"$OUT/scene_probe.txt" 2>&1 || true
      else
        timeout 3s bash -c '
          export IGN_PARTITION="$1"
          ign topic -e -t "$2"
        ' _ "${SERVER_IGN:-$SERVER_GZ}" "$topic" \
          >"$OUT/scene_probe.txt" 2>&1 || true
      fi
      if [[ -s "$OUT/scene_probe.txt" ]]; then
        PROBE_RESULT="TRAFFIC_PRESENT"
      else
        PROBE_RESULT="TOPIC_PRESENT_NO_TRAFFIC"
      fi
      break
    fi
  done
fi
say "scene_probe=$PROBE_RESULT"

section "7. Server SDF / world inspection"
SERVER_CMD="$(proc_cmdline "$SERVER_PID")"
SDF_PATH="$(
  printf '%s\n' "$SERVER_CMD" \
    | grep -oE '(/[^ ]+\.(sdf|world))' | head -n1
)"
say "server_sdf=${SDF_PATH:-NONE}"

if [[ -n "$SDF_PATH" && -f "$SDF_PATH" ]]; then
  cp "$SDF_PATH" "$OUT/server_world.sdf" 2>/dev/null || true
  python3 - "$SDF_PATH" >"$OUT/sdf_summary.txt" 2>&1 <<'PY'
import sys, xml.etree.ElementTree as ET
p=sys.argv[1]
root=ET.parse(p).getroot()
worlds=root.findall(".//world")
print("world_count=",len(worlds))
for w in worlds:
    print("world_name=",w.attrib.get("name"))
    models=w.findall("./model")
    includes=w.findall("./include")
    lights=w.findall("./light")
    plugins=w.findall("./plugin")
    print("direct_models=",len(models))
    print("direct_includes=",len(includes))
    print("direct_lights=",len(lights))
    print("direct_plugins=",len(plugins))
    for m in models[:30]:
        print("model=",m.attrib.get("name"))
    for inc in includes[:30]:
        uri=inc.findtext("uri")
        name=inc.findtext("name")
        print("include=",name or "",uri or "")
PY
  cat "$OUT/sdf_summary.txt" | tee -a "$REPORT"
fi

section "8. GUI and runner logs"
LOG_DIR="$ROOT/results/demo/logs"
if [[ -d "$LOG_DIR" ]]; then
  find "$LOG_DIR" -maxdepth 1 -type f -printf '%f\n' \
    | sort >"$OUT/demo_log_files.txt" 2>/dev/null || true

  for f in \
    "$LOG_DIR/gazebo_gui_normal.log" \
    "$LOG_DIR/normal_runner.log"; do
    if [[ -f "$f" ]]; then
      cp "$f" "$OUT/$(basename "$f")" 2>/dev/null || true
    fi
  done
fi

{
  grep -RniE \
    'error|exception|ogre|render|GLX|EGL|OpenGL|scene|transport|partition|unable|failed' \
    "$OUT/gazebo_gui_normal.log" "$OUT/normal_runner.log" 2>/dev/null \
    | tail -n 160
} >"$OUT/log_errors.txt" || true

if [[ -s "$OUT/log_errors.txt" ]]; then
  tail -n 80 "$OUT/log_errors.txt" | tee -a "$REPORT"
else
  say "No obvious render/transport error found in copied demo logs."
fi

section "9. Server lifetime observation (5 seconds)"
{
  date +%s.%N
  for i in $(seq 1 25); do
    if [[ -d "/proc/$SERVER_PID" ]]; then
      printf '%s ALIVE\n' "$(date +%s.%N)"
    else
      printf '%s EXITED\n' "$(date +%s.%N)"
      break
    fi
    sleep 0.2
  done
} >"$OUT/server_lifetime.txt"
tail -n 5 "$OUT/server_lifetime.txt" | tee -a "$REPORT"

SERVER_ALIVE=0
[[ -d "/proc/$SERVER_PID" ]] && SERVER_ALIVE=1

section "10. Rendering sanity"
RENDER_HINT="UNKNOWN"
if [[ -f "$OUT/glxinfo.txt" ]]; then
  grep -E 'OpenGL vendor|OpenGL renderer|OpenGL version' "$OUT/glxinfo.txt" \
    | tee -a "$REPORT" || true
fi
if grep -qiE 'Ogre::|Rendering|GL3Plus|EGL|GLX.*error|OpenGL.*error|copyTo' \
    "$OUT/log_errors.txt" 2>/dev/null; then
  RENDER_HINT="RENDERER_ERROR"
else
  RENDER_HINT="NO_OBVIOUS_RENDER_ERROR"
fi
say "render_hint=$RENDER_HINT"

section "11. Automatic diagnosis"

WORLD_TOPICS=0
if [[ -s "$OUT/world_topics.txt" ]]; then
  WORLD_TOPICS=1
fi

SDF_ENTITIES=0
if [[ -f "$OUT/sdf_summary.txt" ]] \
  && grep -Eq 'direct_models= [1-9]|direct_includes= [1-9]' "$OUT/sdf_summary.txt"; then
  SDF_ENTITIES=1
fi

DIAG="UNRESOLVED"
NEXT="Inspect generated files manually."

if [[ "$MATCH" -eq 0 ]]; then
  DIAG="TRANSPORT_ENV_MISMATCH"
  NEXT="GUI and server do not share GZ_PARTITION / ROS_DOMAIN_ID. Fix attach environment first."
elif [[ "$WORLD_TOPICS" -eq 0 ]]; then
  DIAG="SERVER_HAS_NO_WORLD_TRANSPORT"
  NEXT="The server process exists but no /world/* topics are visible. Inspect normal_runner.log and the launch path."
elif [[ -z "$WORLD_NAME" ]]; then
  DIAG="WORLD_NAME_NOT_DISCOVERED"
  NEXT="Gazebo transport is visible but no world namespace was found."
elif [[ "$SDF_ENTITIES" -eq 0 && "$PROBE_RESULT" != "TRAFFIC_PRESENT" ]]; then
  DIAG="WORLD_OR_SCENE_CONTENT_MISSING"
  NEXT="The server may be running an empty/minimal world, or scene data is not being published. Inspect server_world.sdf and scene topics."
elif [[ "$RENDER_HINT" == "RENDERER_ERROR" ]]; then
  DIAG="GUI_RENDERER_FAILURE"
  NEXT="Transport/world appear present, but GUI log contains renderer/OpenGL/OGRE errors. Test software rendering next."
elif [[ "$PROBE_RESULT" == "TRAFFIC_PRESENT" && "$SERVER_ALIVE" -eq 1 ]]; then
  DIAG="GUI_NOT_POPULATING_DESPITE_LIVE_SCENE"
  NEXT="Server is alive and scene/pose traffic exists. Focus on Gazebo GUI plugin/render configuration; test a fresh GUI and software rendering."
elif [[ "$SERVER_ALIVE" -eq 0 ]]; then
  DIAG="SERVER_LIFETIME_TOO_SHORT"
  NEXT="The server exits before the GUI can remain populated. Diagnose runner cleanup timing and keep the runtime alive for presentation without changing canonical Evidence."
fi

{
  echo "DIAGNOSIS=$DIAG"
  echo "transport_match=$MATCH"
  echo "world_topics=$WORLD_TOPICS"
  echo "world_name=${WORLD_NAME:-NONE}"
  echo "scene_probe=$PROBE_RESULT"
  echo "sdf_entities=$SDF_ENTITIES"
  echo "server_alive_after_probe=$SERVER_ALIVE"
  echo "render_hint=$RENDER_HINT"
  echo
  echo "NEXT_ACTION=$NEXT"
} | tee "$SUMMARY" | tee -a "$REPORT"

section "12. Safe follow-up commands"
cat <<EOF | tee -a "$REPORT"
Read summary:
  cat "$SUMMARY"

Inspect world / scene:
  cat "$OUT/world_topics.txt"
  cat "$OUT/scene_topics.txt"
  cat "$OUT/sdf_summary.txt"

Inspect GUI errors:
  cat "$OUT/log_errors.txt"

If diagnosis is GUI_RENDERER_FAILURE or GUI_NOT_POPULATING_DESPITE_LIVE_SCENE:
  # Run while the server is alive, using its exact transport environment.
  SERVER_PID=$SERVER_PID
  export GZ_PARTITION="$SERVER_GZ"
  export IGN_PARTITION="${SERVER_IGN:-$SERVER_GZ}"
  export ROS_DOMAIN_ID="$SERVER_ROS"

  # First normal renderer:
  gz sim -g

  # Then software rendering comparison:
  LIBGL_ALWAYS_SOFTWARE=1 gz sim -g

Do not use pkill gz; it may kill the canonical server.
EOF

say ""
say "Diagnostic complete."
say "Share these two files for the next diagnosis:"
say "  $SUMMARY"
say "  $REPORT"
