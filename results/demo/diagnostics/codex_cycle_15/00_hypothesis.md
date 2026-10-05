ROOT_CAUSE_HYPOTHESIS: default/LOCALHOST shared-memory path stalls initialization on this host; UDPv4 restored it but network transport has latency.
EVIDENCE: Jazzy rmw_fastrtps participant.cpp LOCALHOST explicitly re-adds SHM despite built-in UDPv4 choice, explaining cycle14 regression.
SMALLEST_CHANGE: explicit participant UDP-only loopback transport + local initial peers (32); leave ROS discovery SUBNET and middleware publishing/QoS/timing defaults unchanged.
EXPECTED_RESULT: no SHM initialization, samehost transport latency, mission succeeds within unchanged bounds.
