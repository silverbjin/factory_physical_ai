#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from run_task_orchestrator import (
    AcceptanceResult,
    ModelConfig,
    OrchestratorError,
    commit_all_changes,
    commit_subject,
    expected_acceptance_filename,
    expand_range,
    load_model_policy,
    parse_acceptance_result,
    parse_workflow_result,
    task_scope,
    validate_acceptance_write,
)


class OrchestratorUnitTests(unittest.TestCase):
    def test_parse_workflow_result(self):
        text = (
            "hello\n"
            "WORKFLOW_RESULT_JSON: "
            '{"v":1,"task_id":"TASK-SIM-002",'
            '"stage":"review","status":"ACCEPT",'
            '"workflow_complete":true}\n'
        )
        result = parse_workflow_result(text)
        self.assertEqual(result.task_id, "TASK-SIM-002")
        self.assertEqual(result.stage, "review")
        self.assertEqual(result.status, "ACCEPT")
        self.assertTrue(
            result.payload["workflow_complete"]
        )

    def test_parse_acceptance_result(self):
        text = (
            "ok\n"
            "ACCEPTANCE_RESULT_JSON: "
            '{"v":1,"task_id":"TASK-SIM-003",'
            '"status":"RECORDED",'
            '"accepted_commit":"abc123",'
            '"acceptance_path":"results/simulation/'
            'SIM-003_acceptance.json",'
            '"workflow_complete":true}\n'
        )
        result = parse_acceptance_result(text)
        self.assertEqual(
            result.task_id,
            "TASK-SIM-003",
        )
        self.assertEqual(
            result.status,
            "RECORDED",
        )
        self.assertEqual(
            result.acceptance_path,
            "results/simulation/SIM-003_acceptance.json",
        )

    def test_expand_range(self):
        self.assertEqual(
            expand_range(
                "TASK-SIM-002",
                "TASK-SIM-004",
            ),
            [
                "TASK-SIM-002",
                "TASK-SIM-003",
                "TASK-SIM-004",
            ],
        )

    def test_range_prefix_mismatch(self):
        with self.assertRaises(OrchestratorError):
            expand_range(
                "TASK-SIM-002",
                "TASK-MVP-004",
            )

    def test_scope_subject_and_acceptance_name(self):
        self.assertEqual(
            task_scope("TASK-SIM-002"),
            "sim",
        )
        self.assertEqual(
            expected_acceptance_filename(
                "TASK-SIM-003"
            ),
            "SIM-003_acceptance.json",
        )
        self.assertEqual(
            commit_subject(
                "TASK-SIM-002",
                "implementation-review",
                "REJECT",
            ),
            (
                "feat(sim): TASK-SIM-002 "
                "implementation reviewed [REJECT]"
            ),
        )
        self.assertEqual(
            commit_subject(
                "TASK-SIM-003",
                "acceptance",
            ),
            (
                "chore(sim): record TASK-SIM-003 "
                "acceptance [ACCEPT]"
            ),
        )

    def test_load_model_policy(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            config_dir = repo / "config"
            config_dir.mkdir()
            policy_path = (
                config_dir
                / "codex_model_policy.json"
            )
            policy_path.write_text(
                json.dumps(
                    {
                        "implementation": {
                            "model": "gpt-5.6-terra",
                            "reasoning_effort": "medium",
                        },
                        "review": {
                            "model": "gpt-5.6-sol",
                            "reasoning_effort": "low",
                        },
                        "fix": {
                            "model": "gpt-5.6-terra",
                            "reasoning_effort": "medium",
                        },
                        "rereview": {
                            "model": "gpt-5.6-sol",
                            "reasoning_effort": "low",
                        },
                        "acceptance": {
                            "model": "gpt-5.6-luna",
                            "reasoning_effort": "low",
                        },
                    }
                ),
                encoding="utf-8",
            )
            policy = load_model_policy(
                repo,
                Path("config/codex_model_policy.json"),
            )
            self.assertEqual(
                policy["acceptance"],
                ModelConfig(
                    model="gpt-5.6-luna",
                    reasoning_effort="low",
                ),
            )

    def test_commit_review_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(
                ["git", "init", "-q"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.name",
                    "Test User",
                ],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.email",
                    "test@example.com",
                ],
                cwd=repo,
                check=True,
            )

            (repo / "file.txt").write_text(
                "base\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "-A"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-qm", "initial"],
                cwd=repo,
                check=True,
            )

            (repo / "file.txt").write_text(
                "changed\n",
                encoding="utf-8",
            )

            commit_hash = commit_all_changes(
                repo,
                task_id="TASK-SIM-002",
                boundary="implementation-review",
                review_status="REJECT",
            )

            self.assertTrue(commit_hash)
            subject = subprocess.run(
                [
                    "git",
                    "log",
                    "-1",
                    "--pretty=%s",
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()
            self.assertEqual(
                subject,
                (
                    "feat(sim): TASK-SIM-002 "
                    "implementation reviewed [REJECT]"
                ),
            )

            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()
            self.assertEqual(status, "")

    def test_validate_acceptance_write(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(
                ["git", "init", "-q"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.name",
                    "Test User",
                ],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.email",
                    "test@example.com",
                ],
                cwd=repo,
                check=True,
            )

            (repo / "seed.txt").write_text(
                "seed\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "-A"],
                cwd=repo,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-qm", "initial"],
                cwd=repo,
                check=True,
            )

            accepted_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()

            out = repo / "results/simulation"
            out.mkdir(parents=True)
            acceptance_file = (
                out / "SIM-003_acceptance.json"
            )
            acceptance_file.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task_id": "TASK-SIM-003",
                        "status": "ACCEPT",
                        "accepted_commit": (
                            accepted_commit
                        ),
                        "review_record": (
                            "docs/task_history/"
                            "TASK-SIM-003/"
                            "04_review.md"
                        ),
                        "evidence": {
                            "path": None,
                            "sha256": None,
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = AcceptanceResult(
                task_id="TASK-SIM-003",
                status="RECORDED",
                accepted_commit=accepted_commit,
                acceptance_path=(
                    "results/simulation/"
                    "SIM-003_acceptance.json"
                ),
                payload={
                    "workflow_complete": True
                },
            )

            rel_path = validate_acceptance_write(
                repo,
                result,
                task_id="TASK-SIM-003",
                accepted_commit=accepted_commit,
            )
            self.assertEqual(
                rel_path.as_posix(),
                (
                    "results/simulation/"
                    "SIM-003_acceptance.json"
                ),
            )


if __name__ == "__main__":
    unittest.main()
