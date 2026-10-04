# CHANGELOG v1.5

## Root cause of v1.4 failure

v1.4 attempted to prepend `demo_3d/bin/gz` to `PATH`. The expected proof was:

```text
results/demo/visual_runtime_patch.jsonl
```

and `SceneBroadcaster` inside `/tmp/nav2_*.sdf`.

The user run showed both absent:

```text
scene_service=MISSING
Runtime SDF: /tmp/nav2_....sdf
SceneBroadcaster in runtime SDF: <empty>
Demo patch log: <empty>
```

Therefore the wrapper was not on the actual Gazebo launch path.

The canonical navigation runtime is launched through ROS 2 / Nav2, and the
runtime materializes the ROS installation environment. A PATH interception
outside that boundary is not authoritative.

## v1.5 correction

v1.5 removes PATH interception from the execution design.

The demo already uses a detached Git worktree to protect accepted Evidence.
v1.5 patches the **worktree copy** of the world before the canonical runner
starts:

```text
main repo canonical world  (read-only)
            ↓
detached worktree
            ↓
worktree/data/simulation/...sdf
            ↓
add SceneBroadcaster
            ↓
ros2 launch / Nav2
            ↓
/tmp/nav2_*.sdf inherits SceneBroadcaster
            ↓
gz sim -s
            ↓
/world/.../scene/info
```

No file under the main repository's `data/simulation`, `results/simulation`,
or `results/reviews` is changed.

Patch provenance is written to:

```text
results/demo/visual_worktree_patch.jsonl
```

This is portfolio visualization output only, not canonical acceptance Evidence.
