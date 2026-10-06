ROOT_CAUSE_HYPOTHESIS: full-run ROS graph or clock forwarding is failing between the initialized bridge and canonical ROS clock probe.
EVIDENCE_SUPPORTING_IT: Gazebo clock publishes; native ROS pub/sub passes; canonical probe times out and Nav2 components do not load.
SMALLEST_CHANGE: none; compare daemon/direct ROS graph and clock reads on the exact live server domain, plus GZ clock endpoint metadata.
EXPECTED_RESULT: identify whether publisher discovery, QoS, or bridge forwarding is the failing boundary.

ACTUAL_RESULT: Gazebo publishes /clock but advertises no subscribers; daemon ROS query reports unknown /clock and direct ROS graph calls time out. Full mission clock gate fails. Native pub/sub alone passes with both transports.
FAIL
NEXT_DECISION: one-variable full-system transport control with installed Fast DDS UDPv4 transport, to test SHM/participant startup behavior under real bridge/Nav2 load. No mission/world/GUI change.
