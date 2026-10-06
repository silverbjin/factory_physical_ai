ROOT_CAUSE_HYPOTHESIS: default SHM middleware startup stalls; UDPv4 avoids startup stall but planning abort may be variable.
SMALLEST_CHANGE: repeat UDPv4-only full-system control; no close-fds hook, no timing/retry changes.
EXPECTED_RESULT: clock/readiness reproducible; assess mission action acknowledgment.
