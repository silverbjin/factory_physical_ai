ROOT_CAUSE_HYPOTHESIS: DDS discovery/data transport on WSL network path adds latency; current fixed lifecycle and action bounds exposed by UDPv4.
SMALLEST_CHANGE: add ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST to established UDPv4 diagnostic environment, all participants samehost. No timing changes.
EXPECTED_RESULT: complete readiness and mission within original bounds.
