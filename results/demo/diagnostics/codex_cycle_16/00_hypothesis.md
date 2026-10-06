ROOT_CAUSE_HYPOTHESIS: explicit UDP-only loopback profile avoids default SHM startup stall and network latency.
SMALLEST_CHANGE: installed supported FASTRTPS_DEFAULT_PROFILES_FILE points to previously tested identical profile; SYSTEM_DEFAULT avoids RMW adding SHM. No new world/GUI/deadline/retry change.
EXPECTED_RESULT: complete mission, all gates.
