# Changelog

## 1.6 — runtime scene publication proven

- Resolve headless xacro before adding an unconditional installed SceneBroadcaster in the disposable worktree.
- Capture and verify the actual Nav2-generated runtime SDF, live scene, ECU entity, exact transport and mission result.
- Handle Gazebo's Ruby process-title rewrite and the temporary SDF generation race.
- Replace mission-script `--help` execution with read-only argparse declaration inspection.
- Capture the exact GUI PID's mapped window and retain rendered frames; track owned identities for bounded cleanup.
- Add the proven demo-only UDP loopback profile, retain original QoS/deadlines, and record actual environment/profile hash.
- Reject stale/concurrent invocations, guard preparation cleanup, and export existing runtime probes after canonical cleanup.
- Require live world enumeration alongside scene and runtime-SDF proof.
- Remove the unused PATH wrapper, stale pause/fixed-transport settings and conflicting historical execution guides.

Earlier iterations: 1.1 had a transport mismatch; 1.3 corrected attachment but lacked scene publication. The 1.4 PATH interception missed the authoritative execution path. The 1.5 substring check incorrectly accepted a conditional SceneBroadcaster, so augmentation was skipped and headless xacro removed the plugin. Those mechanisms are not execution options in 1.6.
