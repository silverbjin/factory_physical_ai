# Physical AI Project Development Environment v1.0

> Status: frozen for Phase 0 on 2026-08-28. Facts are from the local, non-destructive verification recorded in `results/phase0/environment_verification.json`. A `TBD` item is not a capability claim.

## Verified host facts

| Area | Verified fact | Status / implication |
|---|---|---|
| Host | Ubuntu 24.04.4 LTS under WSL2; kernel `6.18.33.2-microsoft-standard-WSL2` | Verified. Development-only host; not a robot runtime host. |
| CPU / memory | Intel Core i7-1185G7, 8 logical CPUs; 15 GiB RAM, 4 GiB swap | Verified. Adequate for tooling, mocks, and lightweight Agent tests. |
| GPU | `nvidia-smi` exists at the WSL compatibility path but NVML reports GPU access blocked by the operating system | Blocked. GPU model, driver, CUDA runtime, and VRAM are unverified; no local VLA training commitment. |
| Python | CPython 3.12.3; ROS Python integration is present | Verified. Project runtime will be an isolated Python 3.12 virtual environment after baseline tooling is added. |
| Node | Node.js 18.19.1 / npm 9.2.0 | Verified; optional only, not an MVP dependency. |
| Git | 2.43.0 | Verified. |
| ROS 2 | ROS 2 Jazzy, Fast DDS (`rmw_fastrtps_cpp`); `rclpy`, `rviz2`, `robot_state_publisher`, Nav2 components/commander, MoveIt 2, `ros2_control`, `robot_localization`, diagnostics tooling, and Gazebo `gz sim` are installed | Verified by P0-002 package/executable inspection. This is reusable capability, not evidence of a configured robot, map, controller, or hardware connection. |
| Docker | Docker CLI 29.6.1 is installed; daemon access is denied for the current user | CLI verified; image/service smoke tests are blocked until Docker access is granted. No image was pulled. |
| Python packages | `prometheus_client` and `rclpy` import; `torch`, `lerobot`, `langgraph`, `pydantic`, `sqlalchemy`, and OpenTelemetry were not installed in the system interpreter | Verified. Do not use the system interpreter as the application environment. |
| Physical devices | No `/dev/video*`, `/dev/ttyUSB*`, or `/dev/ttyACM*` devices observed; `lsusb` and `v4l2-ctl` unavailable | No camera or manipulator was verified. WSL USB passthrough, if needed, is `TBD`. |
| Network | No usable interface inventory was available to the sandbox; `ros2 doctor` could not inspect interface statistics | Configure ROS discovery only after deployment-network validation. |

## Runtime strategy

The project deliberately separates a development/control plane from a future robot/edge plane.

| Responsibility | Phase 0 / Day-10 location | Final intended location |
|---|---|---|
| Agent, deterministic mission executor, factory mocks, SQLite | WSL development PC | Development/server PC or an IT-side service host |
| Agent model inference | Hosted API through a provider adapter | Hosted API by default; local model remains an optional, separately measured path |
| VLA data tools and inference | Not enabled until hardware readiness gate | Robot-adjacent GPU edge PC, or a controlled remote inference service |
| VLA fine-tuning | Not feasible on verified local state | Approved cloud/remote CUDA host with recorded GPU, cost, and dependency evidence |
| ROS 2 drivers, camera capture, motion | Dry-run/mock only | Native Linux robot PC; never inside an unvalidated WSL hardware path |
| PostgreSQL / telemetry | SQLite + JSONL evidence; no Docker dependency | PostgreSQL and collector stack only for concurrent/multi-service deployment claims |

## Chosen package and tooling strategy

- Python packages will be pinned in a project-local virtual environment. The first tooling task will establish `pyproject.toml`, `uv`, `pytest`, Ruff, mypy, and pre-commit; these are intentionally not installed into the system interpreter in this task.
- LeRobot with the `smolvla` extra is the proposed VLA stack. The official guidance documents `pip install "lerobot[smolvla]"`, a 450M SmolVLA base model, and real-camera rollout support. Local installation/import and CUDA execution remain required gates before this becomes accepted. Source: [LeRobot SmolVLA documentation](https://huggingface.co/docs/lerobot/v0.4.4/smolvla).
- The Agent uses a vendor-neutral `ModelProvider` boundary. The initial hosted-provider adapter is intended to use an API with typed function calls; OpenAI's Responses API documents custom functions with strongly typed arguments/outputs. Source: [OpenAI Responses API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/web_search_call?lang=curl).
- LangGraph was evaluated as an optional orchestration library: it supports durable checkpointers and interrupts, but the selected MVP control plane is a small custom deterministic state machine so physical execution policies remain independent of framework semantics. Source: [LangGraph persistence reference](https://langchain-ai.github.io/langgraph/reference/checkpoints/?h=langgraph+checkpoint+sqlite+import+saver).

## Network and ROS 2 topology

No physical network is assumed from Phase 0. When an edge PC is introduced, use an explicit wired, private development network:

```text
Developer / service PC (IT-side)                 Robot / edge PC (OT-side)
--------------------------------                 ------------------------
Agent + factory services                         ROS 2 drivers / cameras
SQLite or PostgreSQL                             VLA skill adapter
telemetry collector                              AMR / manipulator adapters
            |                                               |
            +---- allowlisted HTTPS / service API -----------+
            +---- ROS 2 discovery only on dedicated domain --+
```

- Assign a non-default `ROS_DOMAIN_ID` per isolated test environment; exact value is `TBD` after network validation.
- Set ROS discovery scope explicitly (the current environment exposes `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`). Do not bridge a robot-control domain to untrusted networks.
- Robot drivers, cameras, and emergency-stop paths remain native to the robot PC. The Agent never receives ROS shell access.

## Constraints and validation gates

1. **VLA readiness gate:** before Dataset V1 work, time-box a GPU/hardware decision. A `GO` requires a documented CUDA host, GPU/VRAM/driver facts, Torch CUDA visibility, LeRobot import, selected manipulator/camera path, and approved training budget. A `NO-GO` blocks Dataset V1/training rather than substituting synthetic VLA evidence; the mocked Agent MVP continues independently.
2. **Docker gate:** grant scoped Docker daemon access or use a supported remote daemon before Compose-based services are adopted.
3. **hardware gate:** enumerate and identify a leader/follower manipulator, camera, and safety stop; then run no-motion connectivity checks before any calibration or teleoperation.
4. **ROS network gate:** run native-PC ROS discovery and namespaced dry-run checks on the actual robot network.
5. **secrets gate:** inject API/Hugging Face credentials from local environment or an approved secret store; credentials must not appear in repository files, logs, or results.

Run `bash scripts/verify_environment.sh` after any gate changes. Its non-zero exit denotes only a missing required baseline capability; optional capabilities yield `WARN` and preserve evidence.
