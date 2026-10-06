ACTUAL_RESULT: UDPv4 again restored clock/localization; navigation lifecycle service exceeded unchanged10s bound despite nodes eventually active. FAIL Gate G. Confirms clock mitigation but not complete runtime qualification.
NEXT_DECISION: constrain discovery to same-host LOCALHOST because every mission participant is local, test latency without changing deadlines.

EVIDENCE_SUPPORTING_IT: simulation_clock probe succeeds; unchanged navigation_lifecycle_start probe times out at10s; server later reports active nodes.
