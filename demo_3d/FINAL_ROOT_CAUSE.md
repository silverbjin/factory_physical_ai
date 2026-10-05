# Gazebo 3D root-cause resolution — 1.6

The primary root cause was **conditional SceneBroadcaster removal by the real Nav2 headless xacro path, combined with a no-op augmentation helper**. Transport attachment had already been corrected. The server was running the mission but lacked the scene publication system required by the GUI.

The original SIM-008 SDF contains SceneBroadcaster under:

```xml
<xacro:unless value="$(arg headless)">
  <plugin filename="gz-sim-scene-broadcaster-system"
          name="gz::sim::systems::SceneBroadcaster"/>
</xacro:unless>
```

`inject_scene_broadcaster_text` in 1.5 searched the raw text for that name and returned `changed=false`. It never inserted an unconditional plugin. The installed `tb4_simulation_launch.py` invokes `xacro -o /tmp/nav2_*.sdf headless:=True <world>` and passes that generated file to `gz sim -r -s`. The conditional definition is removed. This is the evidenced `NAV2_WORLD_PREPROCESSING_DROPS_SCENE_BROADCASTER` case, specifically a conditional plugin removal; Nav2 does not drop every unconditional world plugin.

## Ground-truth evidence

`results/demo/diagnostics/codex_cycle_01/` contains the installed launch, installed plugin example, direct server control, original/worktree/runtime SDFs, plugin lists, hashes, `/proc` launch and server identities, service listing and scene request.

Direct control used an unconditional definition discovered from `/opt/ros/jazzy/share/ros_gz_sim_demos/worlds/default.sdf`. Scene service and ECU content passed. The real canonical runner used the intended detached-worktree world, so a different-world explanation was ruled out. Its source remained conditional; `/tmp/nav2_z1ioeq_p.sdf` lacked SceneBroadcaster and its graph lacked the scene service. The mission itself completed successfully.

The definition is `filename="gz-sim-scene-broadcaster-system"`, `name="gz::sim::systems::SceneBroadcaster"`, at world scope. Both system and ROS-vendored installations were inspected; the authoritative declaration comes from the installed ROS example and loading is proven by the actual runtime. No additional system package or renderer environment change was required.

## Exact repaired boundary

The demo resolves **the same headless xacro transformation first**, then inserts the installed plugin into the resolved SDF. It writes that resolved augmented file only to the disposable worktree's scenario world path. The unchanged runner supplies that path to unchanged Nav2. Nav2's second xacro pass preserves the unconditional plugin. A regression test actually executes installed xacro and verifies preservation and idempotence.

This is a deterministic boundary after equivalent headless world generation. It does not intercept `gz`, poll and edit a file already being consumed, change the installed launch, or force `headless:=False`. The actual `/tmp/nav2_*.sdf` is captured and checked before claims are made.

Earlier incorrect assumptions were that matching transport proved rendering, that text containing a plugin proved an active world plugin, that editing a source file proved runtime contents, and that `--help` was read-only for these runners. SIM-008 and SIM-009 ignore that argument and execute missions. Capability discovery now reads literal argparse declarations without executing the scripts. Gazebo also rewrites its argv into a single process title; discovery now handles that form without parsing arbitrary unrelated shell command strings.

## Diagnosis cycles and limits

Cycle 02 exposed a new observer race: the server process could be seen before concurrent xacro finished writing its temporary file. A bounded observer wait fixed that race without delaying the mission.

Cycles 03 and 05 passed A–H and rendered the warehouse/tree. Other runs failed the unchanged mission bounds. Their failures are retained, rather than hidden by a package version: cycle 04 hit navigation lifecycle activation, cycles 06–10 stalled before a usable ROS clock, and cycles 11/13 restored clock with UDPv4 but respectively hit action acknowledgment and lifecycle bounds.

The Gazebo clock existed even when ROS clock initialization failed. The bridge had no Gazebo clock subscriber in cycle 10. Native ROS controls worked after failed launches, but did not establish health while those failing participants were alive. A diagnostic close-fds hook in cycle 12 removed inherited launch-parent DDS descriptors and still failed clock; it is **not retained**.

The middleware controls identify a working demo environment, with a deliberately limited causal claim. Default shared-memory-enabled startup repeatedly stalled on this host. UDP-only transport restored clock in cycles 11/13. `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` reproduced the stall because Jazzy's RMW explicitly installs a shared-memory transport, overriding the built-in UDP choice. The installed FastDDS 2.14 library recognizes `FASTRTPS_DEFAULT_PROFILES_FILE`; the newer variable alone was ignored in cycle 15. The corrected native profile control exchanged messages with zero shared-memory descriptors.

Cycle 16 used the explicit UDP-only loopback profile and `SYSTEM_DEFAULT` discovery, had zero shared-memory descriptors in four live ROS participants, and completed the real mission with all A–H gates. The profile under `demo_3d/config/fastdds_loopback.xml` enables UDP on 127.0.0.1 and local initial peers; it does not alter DDS reliability/QoS, publication mode, mission or Nav2 parameters. Both supported profile variable names point to that single file in demo children. `SYSTEM_DEFAULT` prevents the RMW from adding shared memory again. No hook or installed file is modified. This **DEMO_MIDDLEWARE_ADAPTATION** is separately disclosed from scene augmentation. The precise internal shared-memory stall mechanism and broad reliability on other hosts are not proven; the observed failing/passing transport paths are recorded.

The final package run and current concrete proof are reported in [FINAL_VALIDATION.md](FINAL_VALIDATION.md). No lifecycle deadline, action timeout, retry budget, mission state, startup pause or simulation timing was changed. Each failure exits nonzero and keeps its evidence.

Primary source corroboration: [Jazzy RMW participant construction](https://github.com/ros2/rmw_fastrtps/blob/jazzy/rmw_fastrtps_shared_cpp/src/participant.cpp) establishes the LOCALHOST transport behavior; [FastDDS 2.14 interface whitelist](https://fast-dds.docs.eprosima.com/en/2.14.x/fastdds/transport/whitelist.html) documents the explicit loopback restriction. Installed library strings, live environment and descriptor captures establish this host's actual behavior.

## Final proof and claim boundary

`results/demo/final_validation/` contains the live world response, scene response, exact runtime SDF and hash, matched `/proc` identities, rendered GUI screenshot, mission result, cleanup inventory and canonical hash comparison. [FINAL_VALIDATION.md](FINAL_VALIDATION.md) records the concrete identities and outcomes.

**Canonical behavior:** existing Normal mission, Nav2 launch, transport isolation, semantic placement via the existing VLA surrogate, final verification and bounded execution contract.

**DEMO_VISUALIZATION_AUGMENTATION:** headless-resolved world plus unconditional SceneBroadcaster, GUI attachment, screenshots and observation/cleanup helpers. The canonical `main` is called through a demo entry that exports already-collected probe measurements only after original cleanup; the runner file itself is byte-identical. The demo SDF and Evidence hashes differ from the frozen accepted run.

**DEMO_MIDDLEWARE_ADAPTATION:** one explicit UDP loopback participant profile, FastDDS RMW, and `SYSTEM_DEFAULT` discovery in demo children only. These environment settings are additional to the frozen accepted run; the execution contract and mission code remain unchanged.

**Presentation context:** optional post-suite Verification Uncertain world and paused Final Qualification world. They do not co-simulate the Normal mission. Qualification evaluates accepted Evidence, without a new canonical acceptance claim.

**Accepted Evidence:** original `data/simulation`, `results/simulation` and `results/reviews` remain byte-identical and clean. Accepted history, acceptance records and execution contracts were not edited. MuJoCo is supporting component Evidence only, with no live Gazebo coupling.
