# Recommended Next Tasks After Phase 0

> These are ordered recommendations only. They are not started by TASK-P0-001.

| Order | Proposed task | Goal and bounded exit criteria | Dependencies |
|---:|---|---|---|
| 1 | **P0-002 Repository tooling baseline** | Create pinned Python environment/package configuration; add pytest, Ruff, mypy, pre-commit, `.gitignore`, config/result conventions; prove repeatable local checks | No GPU/hardware dependency |
| 2 | **P0-003 VLA and hardware proof-of-life gate** | Restore/identify CUDA route; install LeRobot in isolated environment; enumerate actual camera/manipulator with no motion; produce safety/device and import evidence | GPU access or approved remote CUDA; hardware availability for teleop half |
| 3 | **P0-004 Teleoperation/recording vertical slice** | On approved hardware, collect a small clearly labelled smoke recording (not Dataset V1), validate camera/state/action timestamps and safety stop path | P0-003; operator authorization |
| 4 | **MVP-001 Factory Agent/tool vertical slice** | Implement only contracts needed for natural-language mission -> deterministic executor -> mocked WMS/Fleet/PHM/navigation/VLA -> one failure/recovery -> durable result; add tests | P0-002; contract plan |
| 5 | **MVP-002 Agent durability and evaluation fixtures** | Add timeout/retry/idempotency/HITL/restart tests and scenario fixtures; emit structured traces and metrics | MVP-001 |
| 6 | **VLA-001 Dataset V1 and training plan** | Define dataset manifest/validator; collect authorized demonstrations; record dataset/model/config provenance; run a measured baseline only after P0-003 gates | P0-004; approved training host |
| 7 | **INT-001 ROS skill adapter dry-run** | Add namespaced native ROS 2 adapter with typed navigation/VLA results and no Agent-to-ROS escape hatch; validate on simulator/hardware path | MVP-001; ROS network gate |

The first three tasks establish the requested repository/tooling baseline, VLA/teleoperation readiness, and Day-10 Agent/tool vertical slice without prematurely building a full simulator, UI, or production service topology.
