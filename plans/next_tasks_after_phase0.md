# Recommended Next Tasks After P0-002

> Ordered recommendation only. TASK-P0-002 does not start any item below.

| Order | Task | Scope and gate |
|---:|---|---|
| 1 | **P0-003 Repository tooling baseline** | Pin the project-local Python environment and add test/lint/type/config/result conventions. No GPU, hardware, or provider dependency. |
| 2 | **MVP-001 Factory Agent/tool vertical slice** | Implement only the frozen Day-10 scope in `docs/architecture/day10_mvp_scope_v1.md`. It may begin immediately after P0-003 and must not wait for VLA hardware. |
| Parallel to 1–2 | **P0-004 VLA readiness gate** | Time-box CUDA/LeRobot/manipulator/camera/budget `GO`/`NO-GO`; no Dataset V1 or robot motion. |
| After P0-004 GO | **P0-005 Teleoperation/recording smoke slice** | Authorized, supervised no-production recording; validate device safety, timestamps, calibration, and storage. |
| After MVP-001 | **MVP-002 Agent durability/evaluation fixtures** | Add restart/idempotency/HITL/failure fixtures and structured evidence. |
| After P0-005 | **VLA-001 Dataset V1 and training plan** | Dataset manifest/validation and measured training/evaluation only on approved hardware. |
| After MVP-001 and relevant gates | **INT-001 ROS skill adapter dry-run** | Reuse Nav2/MoveIt/`ros2_control` boundaries; no Agent-to-ROS escape hatch. |

Do not start a simulator build, Nav2 map, MoveIt configuration, Docker topology, real-provider integration, or VLA training merely because packages are installed. Each requires its own exit criterion.
