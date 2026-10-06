ROOT_CAUSE_HYPOTHESIS: ROS launch children inherit active FastDDS descriptors because installed osrf_pycommon uses close_fds=False.
EVIDENCE_SUPPORTING_IT: cycle08 /proc FD captures and installed impl.py.
SMALLEST_CHANGE: diagnostic-only sitecustomize sets close_fds=True for asyncio launch subprocess exec/shell; default middleware, unchanged deadlines.
EXPECTED_RESULT: no inherited launch descriptors, real clock/readiness/mission pass.
