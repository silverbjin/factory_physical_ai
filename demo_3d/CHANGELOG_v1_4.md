# v1.4 Changes

- Added demo-only `gz` PATH wrapper.
- Injects `gz::sim::systems::SceneBroadcaster` only into temporary runtime SDF files passed to `gz sim -s`.
- Does not modify canonical `data/simulation/*.sdf`, accepted Evidence, or Acceptance artifacts.
- Records each temporary SDF patch in `results/demo/visual_runtime_patch.jsonl` with original/patched SHA256.
- Waits for `/world/.../scene/info` and reports the discovered scene service during GUI attach.
- Added `05_verify_scene_broadcaster.sh` for live verification.
- Demo-only paused / fallback context worlds are copied and augmented separately under `results/demo/runtime/`.
- Keeps v1.3 runtime-owned server following and transport verification.
