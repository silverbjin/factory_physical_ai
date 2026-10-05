ROOT_CAUSE_HYPOTHESIS: full-run ROS initialization intermittently stalls, although native DDS controls initialize normally.
EVIDENCE_SUPPORTING_IT: prior scene/rendering gates pass; bridge/state publisher/Nav2 threads sleep before logging; single-node native controls pass even on failed domains.
SMALLEST_CHANGE: no runtime change; automate startup resource/clock snapshots in an independent owned observer.
EXPECTED_RESULT: prove actual clock publication and capture timely ROS process state; retain full mission outcome rather than infer readiness from GUI.

ACTUAL_RESULT: A–F/H PASS, G FAIL with SIMULATION_CLOCK_UNAVAILABLE. Live Gazebo clock and stats publish. Bridge ROS per-node log confirms creation of /clock bridge; earlier lack of consolidated stdout was insufficient to infer no initialization. Native talker/listener message flow passes in domain 164 with both default and UDPv4.
FAIL
NEXT_DECISION: export existing canonical readiness probe measurements after original cleanup to capture failing ROS CLI stdout/stderr/timing, with no changed probes/deadlines.
