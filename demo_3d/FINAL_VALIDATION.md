# Final Gazebo 3D validation — 1.6

Validated on 2026-10-05 (Asia/Seoul) from the package entry point, after preflight. The clean cycle17 invocation passed all gates A–H and returned `SIM_NORMAL_E2E_READY`, mission success, final verification `pass`, exit code0.

| Gate | Actual evidence | Result |
|---|---|---|
| A: transport | server PID202768, GUI PID202885; partition `sim004-f87a93a4b2ac`, ROS domain `45` match in live `/proc` | PASS |
| B: live world | `/gazebo/worlds` returned `sim008_normal_system_world` | PASS |
| C: publication | live `/world/sim008_normal_system_world/scene/info` available and requested | PASS |
| D: semantics | 3 models, 28 links, 32 visuals; ECU, Depot and TurtleBot4 present | PASS |
| E: actual input | `/tmp/nav2_ceh3npt3.sdf` captured live; unconditional installed SceneBroadcaster | PASS |
| F: GUI | matched GUI alive alongside server; no fatal renderer error; screenshot inspected, warehouse and populated Entity Tree visible | PASS |
| G: mission/cleanup | both navigation goals succeeded; semantic final verification pass; canonical cleanup_complete true; zero owned processes remain | PASS |
| H: canonical integrity | 34 protected tracked files retain identical SHA256; scoped git status empty | PASS |

Actual runtime SDF SHA256: `b39dd0278d29284ff091c781581e1a0a26dd9b9a776e19075467fae0c9137b0f`. Plugin list: SceneBroadcaster, Physics, UserCommands, Sensors, Imu. Its input has one source model and one include; the live response includes the loaded Depot and dynamically spawned robot. `world_comparison.json` compares the canonical source, resolved worktree source and exact consumed input. The scene response lacks a world-name field; live world enumeration supplies that check.

`gazebo_3d.png` was captured from GUI PID202885's mapped X11 window and inspected directly. The world inspector and Entity Tree show the expected world, Depot, `brake_ecu_type_b_001`, and `turtlebot4`; meshes/objects render in the 3D View. The automated pixel-variance check is a nonblank heuristic, not entity recognition. Direct inspection provides semantic visual confirmation for this run; no human-only check remains. The installed GUI does not emit the searched scene-receive log phrase, so that optional flag is false; live service response, transport identity and actual rendered window provide the proof. Default rendering worked without software rendering.

The real mission ran with **DEMO_VISUALIZATION_AUGMENTATION** (resolved world plus SceneBroadcaster) and **DEMO_MIDDLEWARE_ADAPTATION** (explicit UDP-only loopback FastDDS participant profile, `SYSTEM_DEFAULT` discovery). Actual server/ROS child environment and profile hash are retained. Profile SHA256: `76b59e79c49e05368a45d794e8f8985415f52bd0a2679230775cc655342aa6c3`. Installed FastDDS2.14 uses `FASTRTPS_DEFAULT_PROFILES_FILE`; both variable names reference the same package config. Reliability/QoS, Nav2 parameters, mission/retry semantics and original bounds are unchanged. This is additional to frozen accepted Evidence, not new canonical acceptance.

The invocation lasted 88.53 seconds including startup, mission and cleanup. Supplemental cleanup terminated only the recorded owned residual ROS CLI daemon PID202716. No owned process survives, and pre-existing server PID176573 was untouched. Post-run preflight and completed-proof verifier pass.

The probe exporter calls the unchanged canonical main and exports existing measurements only after original cleanup. `runtime_code_integrity.json` compares runner/navigation files to the detached worktree's Git base after cleanup; it does not claim independent live reads of those files. Canonical data, Evidence, review/acceptance records, task history and execution contracts were not edited.

Earlier failures remain in cycles01–15; successful controls are cycles03/05/16. UDP-only built-ins restored clock but still exposed the original lifecycle/action bounds. The explicit loopback profile completed control16 and clean package17. A descriptor-inheritance hook failed its control and was discarded. The exact internal shared-memory stall mechanism and reliability across other hosts are not established. [FINAL_ROOT_CAUSE.md](FINAL_ROOT_CAUSE.md) explains the evidenced repair and limits.

Static validation passes: 11 Python files compile, eight shell scripts pass `bash -n`, seven regression checks pass, and `git diff --check` passes. Independent read-only review reports no unresolved Critical or Important findings. Shared runtime code was not modified; accepted Evidence was not regenerated. Optional SIM-009/Qualification presentations are outside this Normal qualification claim.

Proof is under `results/demo/final_validation/`: required summary/identity/scene/lifecycle/mission/integrity/package reports, actual SDFs, live responses, middleware profile/hash, logs, invocation metadata and screenshot. Full diagnosis records remain under `results/demo/diagnostics/`.
