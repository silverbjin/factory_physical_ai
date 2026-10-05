ROOT_CAUSE_HYPOTHESIS: default FastDDS transport initialization contributes to readiness failures.
SMALLEST_CHANGE: invocation-only FASTDDS_BUILTIN_TRANSPORTS=UDPv4.
ACTUAL_RESULT: clock and READY passed; source navigation aborted on compute_path action acknowledgment timeout.
FAIL: Gate G. No config transport change retained.
NEXT_DECISION: isolate inherited descriptors at installed ROS launch child boundary.
