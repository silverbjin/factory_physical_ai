# Normal stability report

NORMAL_RUNTIME_STABLE: **YES**

Five consecutive final-version executions: all A–H PASS, exit 0, identical current source hashes. Candidate HEAD `82b9a5e57ffd871a29b5ea60cb531e1b75e7631b`; each row records the actual working-tree runtime SHA256 manifest and its isolated worktree match.

| Run | Invocation ID | A–H | Exit | Duration seconds | Evidence |
|---|---|---|---|---|---|
| 1 | 67581794853847e4927e1f4fc1b96f13 | PASS | 0 | 85.613 | results/demo/resolution/track_a/continuation/confirmed_stability_01 |
| 2 | 9f53cae822114cf0ae8c5a947fcdd72f | PASS | 0 | 87.332 | results/demo/resolution/track_a/continuation/confirmed_stability_02 |
| 3 | 86f50220f4cb4af98f7e1364e5a62302 | PASS | 0 | 83.722 | results/demo/resolution/track_a/continuation/confirmed_stability_03 |
| 4 | 7ad3f6f13e2447079f666e7421f8ed83 | PASS | 0 | 82.977 | results/demo/resolution/track_a/continuation/confirmed_stability_04 |
| 5 | 13a42c913f0446cb9051a244919dbb41 | PASS | 0 | 81.712 | results/demo/resolution/track_a/continuation/confirmed_stability_05 |

Source hashes:

- `scripts/ros_bootstrap_client.py`: `70c4e16741107d839705610df6e183364ab417b69ea2dfa773140f702c048c7e`
- `scripts/run_simulation_navigation.py`: `ff5e4545422fa529bdb4f4ba6391dcc01071fb3f9d120ae3e6ff0f27f0957b34`
- `scripts/run_simulation_normal_system_e2e.py`: `3e06a0d55f8de8240595a8b5ec6dabafe08e2092564943c488074f5cbc2eb049`
- `demo_3d/tools/verified_normal.py`: `a6a044f6f4f81989e6cbe6f94da0c4b15761bae1d84cd788b80396715c9dbcf0`
- `demo_3d/tools/demo3d_common.py`: `616c3c1a162f85d48e180adb7c217ae56d0ebe918a701da226140b07d7e2279a`

Proof index: `results/demo/resolution/track_a/continuation/confirmed_five_run_stability.json`. Every run also stores native gates, normal result, transport identity, scene/world validation, process lifecycle, root/runtime code comparison and all-protected-file hash snapshots.

The original five runtime passes are retained in `five_run_stability.json`. Later `final_normal_after_canonical` HFAIL, mixed-version integrated samples, and `final_stability_01` empty-world readiness failure are preserved and excluded from this final consecutive count. Diagnostic, control and failed-fix evidence remains in the continuation directory. No historical accepted evidence was rewritten.

Additional final Normal after the five-run proof: `2d5fd89ecf204653b8b59b8fdb9ca8ef`, all A–H PASS / exit 0; `results/demo/resolution/track_c/final_normal_integrated/`.
