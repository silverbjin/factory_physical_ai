ACTUAL_RESULT: profile variable FASTDDS_DEFAULT_PROFILES_FILE ignored by installed FastDDS2.14 library; SHM descriptors present, CLOCK failed. strings shows only FASTRTPS_DEFAULT_PROFILES_FILE supported. Correct-variable native pub/sub control succeeds with zero SHM FDs. FAIL full run; corrected variable verified separately.

EVIDENCE_SUPPORTING_IT: live participants retained SHM descriptors under newer profile variable; installed library strings support older variable; corrected-variable native pub/sub exchanged messages with zero SHM descriptors.
NEXT_DECISION: run identical profile using supported FASTRTPS_DEFAULT_PROFILES_FILE.
