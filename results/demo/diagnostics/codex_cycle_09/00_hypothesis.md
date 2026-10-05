ROOT_CAUSE_HYPOTHESIS: canonical ROS clock CLI probes fail despite published Gazebo clock and an initialized ROS bridge; the exact CLI failure needs observation.
EVIDENCE_SUPPORTING_IT: cycle 08 live Gazebo clock/stats pass; native ROS pub/sub passes; bridge per-node logs initialize clock bridge.
SMALLEST_CHANGE: demo entry helper invokes unchanged canonical main and exports existing runtime measurements only after original close.
EXPECTED_RESULT: obtain actual readiness probe stdout/stderr/timing; preserve mission semantics and bounded lifecycle.

ACTUAL_RESULT: ROS simulation_clock probes time out at unchanged five-second bounds; no navigation actions appear during startup. Bridge is configured for /clock and live Gazebo publication was independently proven.
FAIL
NEXT_DECISION: capture ROS publisher/subscriber graph directly and via daemon, plus direct ROS/Gazebo clock topic metadata.
