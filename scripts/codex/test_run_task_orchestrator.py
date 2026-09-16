#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from run_task_orchestrator import (
    AcceptanceResult,
    ErrorRecord,
    ModelConfig,
    OrchestratorError,
    RunContext,
    child_prompt,
    commit_all_changes,
    commit_subject,
    default_report_base,
    derive_next_action,
    expected_acceptance_filename,
    create_manual_resume_state,
    load_resume_checkpoint,
    resume_checkpoint_path,
    save_resume_checkpoint,
    validate_resume_state,
    expand_range,
    extract_signal_lines,
    load_model_policy,
    parse_acceptance_result,
    parse_workflow_result,
    task_scope,
    validate_acceptance_write,
    write_reports,
)


class OrchestratorUnitTests(unittest.TestCase):
    def test_parse_workflow_result(self):
        text = (
            'hello\nWORKFLOW_RESULT_JSON: '
            '{"v":1,"task_id":"TASK-SIM-002","stage":"review",'
            '"status":"ACCEPT","workflow_complete":true}\n'
        )
        result = parse_workflow_result(text, task_id="TASK-SIM-002", role="review")
        self.assertEqual(result.status, "ACCEPT")

    def test_parse_acceptance_result(self):
        text = (
            'ACCEPTANCE_RESULT_JSON: '
            '{"v":1,"task_id":"TASK-SIM-003","status":"RECORDED",'
            '"accepted_commit":"abc123","acceptance_path":"results/sim/SIM-003_acceptance.json",'
            '"workflow_complete":true}\n'
        )
        result = parse_acceptance_result(text, task_id="TASK-SIM-003")
        self.assertEqual(result.status, "RECORDED")

    def test_child_prompt_implementation(self):
        prompt = child_prompt(
            task_id="TASK-SIM-004",
            worker_role="implementation",
        )
        self.assertTrue(prompt.startswith("ORCHESTRATOR_CHILD\n"))
        self.assertIn("worker_role=implementation", prompt)
        self.assertIn("task_id=TASK-SIM-004", prompt)
        self.assertIn(
            "worker_prompt=prompts/codex/implement_task_v2.md",
            prompt,
        )
        self.assertIn("Do NOT invoke or recommend the host orchestrator.", prompt)

    def test_child_prompt_resume(self):
        prompt = child_prompt(
            task_id="TASK-SIM-004",
            worker_role="implementation",
            resume=True,
            resume_from_stage="implementation",
            previous_run_dir="/tmp/previous-run",
            resume_reason="token limit",
        )
        self.assertIn("resume=true", prompt)
        self.assertIn("resume_from_stage=implementation", prompt)
        self.assertIn("previous_run_dir=/tmp/previous-run", prompt)
        self.assertIn("resume_reason=token limit", prompt)
        self.assertIn("RESUME RULES:", prompt)

    def test_child_prompt_rereview(self):
        prompt = child_prompt(
            task_id="TASK-SIM-004",
            worker_role="rereview",
        )
        self.assertIn("worker_role=rereview", prompt)
        self.assertIn(
            "worker_prompt=prompts/codex/read_only_review_v2.md",
            prompt,
        )

    def test_child_prompt_acceptance(self):
        prompt = child_prompt(
            task_id="TASK-SIM-004",
            worker_role="acceptance",
            accepted_commit="a" * 40,
        )
        self.assertIn("worker_role=acceptance", prompt)
        self.assertIn(f"accepted_commit={'a' * 40}", prompt)
        self.assertIn(
            "worker_prompt=prompts/codex/record_task_acceptance_v2.md",
            prompt,
        )

    def test_expand_range(self):
        self.assertEqual(
            expand_range("TASK-SIM-002", "TASK-SIM-004"),
            ["TASK-SIM-002", "TASK-SIM-003", "TASK-SIM-004"],
        )

    def test_range_prefix_mismatch(self):
        with self.assertRaises(OrchestratorError):
            expand_range("TASK-SIM-002", "TASK-MVP-004")

    def test_scope_subject_and_acceptance_name(self):
        self.assertEqual(task_scope("TASK-SIM-002"), "sim")
        self.assertEqual(expected_acceptance_filename("TASK-SIM-003"), "SIM-003_acceptance.json")
        self.assertEqual(
            commit_subject("TASK-SIM-002", "implementation-review", "REJECT"),
            "feat(sim): TASK-SIM-002 implementation reviewed [REJECT]",
        )

    def test_extract_signal_lines(self):
        signals = extract_signal_lines(
            "Status: INCOMPLETE\n43 passed\nSIM_NAVIGATION_BACKEND_BLOCKED\nNext: BLOCKED\n"
        )
        self.assertTrue(any("INCOMPLETE" in s for s in signals))
        self.assertTrue(any("BLOCKED" in s for s in signals))

    def test_next_action_incomplete(self):
        action, steps = derive_next_action({"status": "INCOMPLETE"}, [])
        self.assertEqual(action, "RESOLVE_IMPLEMENTATION_BLOCKER_THEN_RESUME")
        self.assertTrue(steps)

    def test_next_action_protocol(self):
        action, _ = derive_next_action(
            {"status": "ERROR"},
            [ErrorRecord(kind="CHILD_PROTOCOL", stage="implementation", task_id="TASK-SIM-004", message="missing")],
        )
        self.assertEqual(action, "REPAIR_WORKER_RESULT_PROTOCOL")

    def test_load_model_policy(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "config").mkdir()
            data = {
                role: {"model": model, "reasoning_effort": effort}
                for role, model, effort in [
                    ("implementation", "gpt-5.6-terra", "medium"),
                    ("review", "gpt-5.6-sol", "low"),
                    ("fix", "gpt-5.6-terra", "medium"),
                    ("rereview", "gpt-5.6-sol", "low"),
                    ("acceptance", "gpt-5.6-luna", "low"),
                ]
            }
            (repo / "config/codex_model_policy.json").write_text(json.dumps(data), encoding="utf-8")
            policy = load_model_policy(repo, Path("config/codex_model_policy.json"))
            self.assertEqual(policy["acceptance"], ModelConfig("gpt-5.6-luna", "low"))

    def test_commit_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            (repo / "file.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            (repo / "file.txt").write_text("changed\n", encoding="utf-8")
            commit_hash = commit_all_changes(
                repo,
                task_id="TASK-SIM-002",
                boundary="implementation-review",
                review_status="REJECT",
            )
            self.assertTrue(commit_hash)
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=repo, text=True, stdout=subprocess.PIPE, check=True
            ).stdout.strip()
            self.assertEqual(status, "")

    def test_validate_acceptance_write(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            accepted_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True, stdout=subprocess.PIPE, check=True
            ).stdout.strip()
            out = repo / "results/sim"
            out.mkdir(parents=True)
            acceptance_file = out / "SIM-003_acceptance.json"
            acceptance_file.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task_id": "TASK-SIM-003",
                        "status": "ACCEPT",
                        "accepted_commit": accepted_commit,
                        "review_record": "docs/task_history/TASK-SIM-003/04_review.md",
                        "evidence": {"path": None, "sha256": None},
                    }
                ) + "\n",
                encoding="utf-8",
            )
            result = AcceptanceResult(
                task_id="TASK-SIM-003",
                status="RECORDED",
                accepted_commit=accepted_commit,
                acceptance_path="results/sim/SIM-003_acceptance.json",
                payload={"workflow_complete": True},
            )
            rel = validate_acceptance_write(repo, result, task_id="TASK-SIM-003", accepted_commit=accepted_commit)
            self.assertEqual(rel.as_posix(), "results/sim/SIM-003_acceptance.json")

    def test_resume_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as state_td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)

            ctx = RunContext(
                repo=repo,
                target="TASK-SIM-004",
                report_base=Path(state_td),
                verbose=False,
                show_tail=0,
                heartbeat_seconds=0,
            )
            state = create_manual_resume_state(
                repo,
                "TASK-SIM-004",
                phase="implementation",
                max_fix_cycles=1,
            )
            save_resume_checkpoint(ctx, "TASK-SIM-004", state)
            path, loaded = load_resume_checkpoint(
                Path(state_td),
                repo,
                "TASK-SIM-004",
            )
            self.assertTrue(path.is_file())
            self.assertEqual(loaded["phase"], "implementation")
            validate_resume_state(repo, "TASK-SIM-004", loaded)

    def test_resume_state_rejects_head_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            state = create_manual_resume_state(
                repo,
                "TASK-SIM-004",
                phase="implementation",
                max_fix_cycles=1,
            )
            (repo / "later.txt").write_text("later\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "later"], cwd=repo, check=True)
            with self.assertRaises(OrchestratorError):
                validate_resume_state(repo, "TASK-SIM-004", state)

    def test_resume_checkpoint_path_is_outside_repo(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as state_td:
            repo = Path(td)
            p = resume_checkpoint_path(
                Path(state_td),
                repo,
                "TASK-SIM-004",
            )
            self.assertFalse(str(p).startswith(str(repo)))
            self.assertTrue(p.name.startswith("resume_TASK-SIM-004"))

    def test_reports_written_outside_repo(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as state_td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            ctx = RunContext(
                repo=repo,
                target="TASK-SIM-004",
                report_base=Path(state_td),
                verbose=False,
                show_tail=0,
                heartbeat_seconds=0,
            )
            stage = ctx.new_stage(
                "TASK-SIM-004",
                "implementation",
                ModelConfig("gpt-5.6-terra", "medium"),
            )
            self.assertTrue(stage.prompt_path.endswith("_prompt.txt"))
            ctx.add_error(
                kind="TECHNICAL",
                stage="implementation",
                task_id="TASK-SIM-004",
                message="blocked",
                signals=["Status: INCOMPLETE"],
            )
            md, js = write_reports(
                ctx,
                result={"task_id": "TASK-SIM-004", "status": "INCOMPLETE"},
                branch="task/sim-004",
                repo_status=" M src/x.py",
            )
            self.assertTrue(md.is_file())
            self.assertTrue(js.is_file())
            self.assertFalse(str(md).startswith(str(repo)))
            self.assertIn("RESOLVE_IMPLEMENTATION_BLOCKER_THEN_RESUME", md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
