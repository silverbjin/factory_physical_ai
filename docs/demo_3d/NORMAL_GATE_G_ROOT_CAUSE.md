# Normal Gate G — proven root causes

First observed frontier: INITIAL_POSE_PUBLISH_FAILED. Earlier archived runs also exhibited NAVIGATION_LIFECYCLE_START_FAILED and malformed simulation-time observations.

PROVEN: failure invocation4f960ad3b61643d78dfbb8c38e07853b reports AMCL initialPoseReceived and Setting pose before the outer ros2 CLI timeout. A five-second CLI process completion bound includes interpreter/plugin startup, a new DDS participant's discovery, publication, keep-alive and exit. It does not isolate actual publication completion. The archived client failed84ms after AMCL receipt; the CLI itself keeps the publisher alive100ms after publication.

OBSERVED: diagnostic_02/03/04 all passed; fresh CLI initial-pose calls took2.577/2.643/3.228s. The same profile/domain and identical pose through a warmed matched publisher took0.351s, with AMCL pose output80ms after publish. This control rejects AMCL receipt/QoS failure for the diagnosed timeout. Monotonic timestamps govern elapsed comparisons because wall-clock corrections were also observed.

Correction1: scripts/ros_bootstrap_client.py owns one ROS participant for the run; BoundedGazeboNav2Runtime warms it during bootstrap. It explicitly matches AMCL before publishing once, remains alive through existing map→odom proof, and requires a positive navigation STARTUP response. The original5s publication and10s STARTUP bounds, mission deadlines, navigation goal bounds, retry budgets, and A–H predicates are unchanged. All response framing remains bounded even for partial lines. Cleanup terminates and reaps the client.

Live fix_01 proves initialpose completion3.833ms and positive STARTUP response5.559s within those original bounds. Independent review exposed partial-line blocking; a RED test reproduced it and the reader now frames bytes with the original monotonic deadline.

Correction2: Gazebo's stats CLI returned two complete JSON messages despite -n1. The former whole-output json.loads raised Extra data and classified valid telemetry as malformed. parse_gazebo_stats_time validates each delivered frame, reads the latest complete simulation clock, handles protobuf omission of zero-valued fields, and rejects malformed/truncated/range-invalid input. This correction was justified by the exact control_01 and fix_01 retained streams, independently of the bootstrap correction.

Why PASS/FAIL varied: fresh CLI participant costs vary under the live ROS/Gazebo workload; near-bound successful operations race CLI completion. Independently, Gazebo may deliver multiple queued stats frames. Both introduce host/client artifacts into semantic mission success without a simulator behavior failure.

Minimum scope: the runtime's two bounded bootstrap operations and the stats transport parser. The demo validates the current source overlay in its isolated worktree and stores matching SHA256 values; canonical accepted artifacts are not modified by demo execution.

Evidence: results/demo/resolution/track_a/continuation/A3_CONTROL_AND_A4_DECISION.md, client_events.jsonl/probe_events.jsonl/persistent_control_events.jsonl in the diagnostic/control directories, bootstrap_red/green.log, stats_red/green.log, client_deadline_red/green.log. Failed cycles remain present and are excluded from stability counts.

Later integrated frontiers and minimal corrections:

- RuntimeSDF generation readiness: final_stability_01 copies0bytes and fails XML parsing beforeattachment. Checking pathname existence was insufficient. The demo now observes complete valid world XML using file-write notifications within the existing3s bound, and uses one exact byte snapshot for provenance/copy/parse. Event-controlled delayed-writer RED/GREEN plus independent9checks reject malformed/truncated/no-world cases.
- Forward-artifact integrity: final_normal_after_canonical passedA–G but H rejected legitimate newlyuntracked successor evidence solely because Gitstatus was nonempty. H now permits only exact fresh-qualified successor evidence/acceptance/log paths; anytrackedchange/unknownfile/tampering fails. Protected snapshots include all tracked and untracked files plus history/contracts. Independent13tamperchecks confirm historical/in-run protection. This implements the authorized forward-only artifact boundary without changing mission-success predicates.

The final consecutive proof uses frozen demohelper SHAa6a044f6f4f81989e6cbe6f94da0c4b15761bae1d84cd788b80396715c9dbcf0. Earlier successful runtime proof and failed/mixed-version integrated runs remain archived; they do not count toward the final five.
