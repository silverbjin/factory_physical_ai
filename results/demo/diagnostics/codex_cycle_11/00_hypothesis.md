ROOT_CAUSE_HYPOTHESIS: default Fast DDS transport under full bridge/Nav2 participant startup prevents ROS graph/clock availability; native low-load controls do not expose it.
EVIDENCE_SUPPORTING_IT: cycles 06–10 fail clock despite Gazebo clock publication; direct ROS graph requests time out, daemon sees unknown clock; ROS children hold shared Fast DDS port resources. Installed library exposes FASTDDS_BUILTIN_TRANSPORTS and UDPv4 native control eliminates SHM descriptors.
SMALLEST_CHANGE: full-run control only: FASTDDS_BUILTIN_TRANSPORTS=UDPv4, inherited by real runtime children. No package config change yet.
EXPECTED_RESULT: direct graph and ROS clock become available; unchanged real mission completes, while 3D gates remain true.
