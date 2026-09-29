import importlib.util
import tempfile
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).with_name('run_task_orchestrator.py')
spec = importlib.util.spec_from_file_location('orch', MODULE_PATH)
orch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = orch
assert spec.loader
spec.loader.exec_module(orch)


class DummyCtx:
    def __init__(self):
        self.messages = []
    def progress(self, kind, message):
        self.messages.append((kind, message))


class DiagnosisHistoryTests(unittest.TestCase):
    def test_status_parser_does_not_confuse_unresolved_with_resolved(self):
        self.assertEqual(orch.parse_diagnosis_history_status('- Status: UNRESOLVED\n'), 'UNRESOLVED')

    def test_final_status_wins_over_prior_pass_context(self):
        text = '''\nPrevious diagnosis result: UNRESOLVED\nFinal diagnosis status: RESOLVED\n'''
        self.assertEqual(orch.parse_diagnosis_history_status(text), 'RESOLVED')

    def test_latest_resolved_ignores_newer_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            (hist / '04_diagnosis.md').write_text('Status: RESOLVED\n', encoding='utf-8')
            (hist / '10_diagnosis.md').write_text('Final diagnosis status: RESOLVED\n', encoding='utf-8')
            (hist / '11_diagnosis.md').write_text('Status: UNRESOLVED\n', encoding='utf-8')
            rec = orch.latest_resolved_diagnosis(repo, 'TASK-SIM-009')
            self.assertIsNotNone(rec)
            self.assertEqual(rec.sequence, 10)
            self.assertEqual(rec.path.name, '10_diagnosis.md')

    def test_binding_refreshes_stale_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            p4 = hist / '04_diagnosis.md'
            p10 = hist / '10_diagnosis.md'
            p4.write_text('Status: RESOLVED\n', encoding='utf-8')
            p10.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = {'diagnosis_path': str(p4), 'diagnosis_sequence': 4}
            ctx = DummyCtx()
            changed = orch.bind_latest_resolved_diagnosis(repo, 'TASK-SIM-009', state, ctx=ctx)
            self.assertTrue(changed)
            self.assertEqual(Path(state['diagnosis_path']), p10.resolve())
            self.assertEqual(state['diagnosis_sequence'], 10)
            self.assertEqual(state['diagnosis_binding_source'], 'task_history')
            self.assertTrue(any(kind == 'BIND' and '10_diagnosis.md' in msg for kind, msg in ctx.messages))

    def test_old_resolved_diagnosis_is_stale_after_newer_review(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            p4 = hist / '04_diagnosis.md'
            p4.write_text('Status: RESOLVED\n', encoding='utf-8')
            (hist / '09_review.md').write_text('Recommendation: REJECT\n', encoding='utf-8')
            state = {
                'repo': str(repo),
                'diagnosis_path': str(p4),
                'diagnosis_sequence': 4,
                'diagnosis_binding_source': 'task_history',
            }
            changed = orch.bind_latest_resolved_diagnosis(repo, 'TASK-SIM-009', state, ctx=DummyCtx())
            self.assertTrue(changed)
            self.assertIsNone(state['diagnosis_path'])
            self.assertIsNone(state['diagnosis_sequence'])

    def test_new_resolved_diagnosis_after_review_is_bindable(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            (hist / '04_diagnosis.md').write_text('Status: RESOLVED\n', encoding='utf-8')
            (hist / '09_review.md').write_text('Recommendation: REJECT\n', encoding='utf-8')
            p10 = hist / '10_diagnosis.md'
            p10.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = {'repo': str(repo), 'diagnosis_path': None}
            changed = orch.bind_latest_resolved_diagnosis(repo, 'TASK-SIM-009', state, ctx=DummyCtx())
            self.assertTrue(changed)
            self.assertEqual(Path(state['diagnosis_path']), p10.resolve())

    def test_binding_recovers_missing_checkpoint_path(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            p10 = hist / '10_diagnosis.md'
            p10.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = {'diagnosis_path': str(repo / 'missing.md')}
            changed = orch.bind_latest_resolved_diagnosis(repo, 'TASK-SIM-009', state, ctx=DummyCtx())
            self.assertTrue(changed)
            self.assertEqual(Path(state['diagnosis_path']), p10.resolve())


class TransitionTests(unittest.TestCase):
    def test_green_local_review_reject_goes_to_fix(self):
        self.assertEqual(orch.review_reject_next_phase('GREEN', 'simple null guard failure'), 'fix')

    def test_yellow_architecture_review_reject_goes_to_diagnosis(self):
        text = 'authoritative source cannot be proven for the integration boundary'
        self.assertEqual(orch.review_reject_next_phase('YELLOW', text), 'diagnosis')

    def test_red_review_reject_always_goes_to_diagnosis(self):
        self.assertEqual(orch.review_reject_next_phase('RED', 'simple test assertion mismatch'), 'diagnosis')

    def test_red_rereview_reject_diagnoses_before_budget_decision(self):
        self.assertEqual(
            orch.rereview_reject_next_phase('RED', 'new HIGH finding', fix_budget_available=False),
            'diagnosis',
        )

    def test_green_simple_rereview_reject_stops_when_budget_exhausted(self):
        self.assertEqual(
            orch.rereview_reject_next_phase('GREEN', 'simple assertion mismatch', fix_budget_available=False),
            'stop',
        )

    def test_fix_not_ready_same_diagnosed_signature_stops_loop(self):
        text = 'authoritative source cannot be proven'
        sig = orch.diagnosis_trigger_signature(text)
        self.assertEqual(
            orch.fix_not_ready_next_phase('RED', text, diagnosed_trigger_signature=sig),
            'stop',
        )

    def test_fix_not_ready_new_architecture_blocker_diagnoses(self):
        text = 'authoritative source cannot be proven'
        self.assertEqual(
            orch.fix_not_ready_next_phase('YELLOW', text, diagnosed_trigger_signature=None),
            'diagnosis',
        )


class PromptTests(unittest.TestCase):
    def test_child_prompt_includes_binding_provenance(self):
        prompt = orch.child_prompt(
            task_id='TASK-SIM-009',
            worker_role='fix',
            diagnosis_path='/repo/docs/task_history/TASK-SIM-009/10_diagnosis.md',
            diagnosis_reason='rereview_architecture_finding',
            diagnosis_binding_source='task_history',
            diagnosis_sequence=10,
        )
        self.assertIn('diagnosis_binding_source=task_history', prompt)
        self.assertIn('diagnosis_sequence=10', prompt)


class StateMachineIntegrationTests(unittest.TestCase):
    def make_policy(self):
        roles = {
            role: orch.ModelConfig('model', 'medium')
            for role in ('implementation', 'review', 'fix', 'rereview', 'diagnosis', 'diagnosis_escalated', 'acceptance')
        }
        classes = {
            name: orch.TaskClassConfig(
                diagnosis_required=(name == 'RED'),
                allow_high_escalation=True,
                review_reasoning_effort='medium',
                rereview_reasoning_effort='medium',
            )
            for name in ('GREEN', 'YELLOW', 'RED')
        }
        return orch.ModelPolicy(
            roles=roles,
            task_classes=classes,
            classification=orch.ClassificationConfig(2, 6, ('task_class',)),
            acceptance_mode='deterministic',
        )

    def base_state(self, repo, phase, task_class='RED', fix_cycles_used=0):
        return {
            'schema_version': 2,
            'task_id': 'TASK-SIM-009',
            'repo': str(repo),
            'branch': 'task/test',
            'initial_head': 'base',
            'current_head': 'base',
            'phase': phase,
            'status': 'RUNNING',
            'task_assessment': {
                'task_id': 'TASK-SIM-009', 'task_class': task_class, 'score': 8,
                'reasons': [], 'task_path': 'tasks/TASK-SIM-009.md', 'explicit_override': False,
            },
            'effective_task_class': task_class,
            'fix_cycles_used': fix_cycles_used,
            'max_fix_cycles': 1,
            'commits': [],
            'current_run_dir': '/tmp/previous',
            'previous_run_dir': None,
        }

    def test_red_rereview_new_reject_runs_diagnosis_even_when_fix_budget_exhausted(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            review_file = repo / 'rereview.txt'
            diagnosis_file = repo / 'diagnosis.txt'
            review_file.write_text('new HIGH runtime architecture finding\n', encoding='utf-8')
            diagnosis_file.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = self.base_state(repo, 'rereview', 'RED', fix_cycles_used=1)
            ctx = SimpleNamespace(run_dir=repo / 'run', stage_records=[], errors=[], progress=lambda *args: None)
            (repo / 'run').mkdir()
            calls = []

            def fake_run_stage(prompt, repo_arg, config, *, ctx, task_id, role):
                calls.append(role)
                if role == 'rereview':
                    return orch.StageResult(task_id, 'review', 'REJECT', {'workflow_complete': True})
                if role == 'diagnosis':
                    return orch.StageResult(task_id, 'diagnosis', 'RESOLVED', {'workflow_complete': True})
                raise AssertionError(role)

            def fake_record(ctx_arg, task_id, role):
                path = review_file if role == 'rereview' else diagnosis_file
                return SimpleNamespace(final_path=str(path))

            with patch.object(orch, 'validate_resume_state', lambda *a, **k: None), \
                 patch.object(orch, 'save_resume_checkpoint', lambda *a, **k: None), \
                 patch.object(orch, 'transition_checkpoint', lambda *a, **k: None), \
                 patch.object(orch, 'commit_all_changes', return_value='commit1'), \
                 patch.object(orch, 'run_stage', side_effect=fake_run_stage), \
                 patch.object(orch, 'latest_stage_final_text', side_effect=lambda c, t, r: review_file.read_text() if r == 'rereview' else diagnosis_file.read_text()), \
                 patch.object(orch, 'latest_stage_record', side_effect=fake_record):
                result = orch.run_task(
                    'TASK-SIM-009', repo, self.make_policy(), ctx=ctx,
                    max_fix_cycles=1, resume_state=state,
                )
            self.assertEqual(calls, ['rereview', 'diagnosis'])
            self.assertEqual(result['status'], 'DIAGNOSIS_RESOLVED_FIX_BUDGET_EXHAUSTED')

    def test_red_fix_resume_with_only_stale_diagnosis_routes_to_diagnosis(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            p4 = hist / '04_diagnosis.md'
            p4.write_text('Status: RESOLVED\n', encoding='utf-8')
            (hist / '09_review.md').write_text('Recommendation: REJECT\n', encoding='utf-8')
            diagnosis_file = repo / 'diagnosis.txt'
            diagnosis_file.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = self.base_state(repo, 'fix', 'RED', fix_cycles_used=1)
            state['diagnosis_path'] = str(p4)
            state['diagnosis_sequence'] = 4
            state['diagnosis_binding_source'] = 'task_history'
            ctx = SimpleNamespace(run_dir=repo / 'run', stage_records=[], errors=[], progress=lambda *args: None)
            (repo / 'run').mkdir()
            calls = []

            def fake_run_stage(prompt, repo_arg, config, *, ctx, task_id, role):
                calls.append(role)
                if role == 'diagnosis':
                    return orch.StageResult(task_id, 'diagnosis', 'RESOLVED', {'workflow_complete': True})
                raise AssertionError(role)

            with patch.object(orch, 'validate_resume_state', lambda *a, **k: None), \
                 patch.object(orch, 'save_resume_checkpoint', lambda *a, **k: None), \
                 patch.object(orch, 'transition_checkpoint', lambda *a, **k: None), \
                 patch.object(orch, 'run_stage', side_effect=fake_run_stage), \
                 patch.object(orch, 'latest_stage_record', return_value=SimpleNamespace(final_path=str(diagnosis_file))):
                result = orch.run_task(
                    'TASK-SIM-009', repo, self.make_policy(), ctx=ctx,
                    max_fix_cycles=1, resume_state=state,
                )
            self.assertEqual(calls, ['diagnosis'])
            self.assertEqual(result['status'], 'DIAGNOSIS_RESOLVED_FIX_BUDGET_EXHAUSTED')

    def test_fix_resume_binds_latest_history_before_budget_stop(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hist = repo / 'docs/task_history/TASK-SIM-009'
            hist.mkdir(parents=True)
            p10 = hist / '10_diagnosis.md'
            p10.write_text('Status: RESOLVED\n', encoding='utf-8')
            state = self.base_state(repo, 'fix', 'RED', fix_cycles_used=0)
            state['diagnosis_path'] = str(repo / 'old_missing.md')
            ctx = SimpleNamespace(run_dir=repo / 'run', stage_records=[], errors=[], progress=lambda *args: None)
            (repo / 'run').mkdir()
            saved = []

            def capture_save(ctx_arg, task_id, st):
                saved.append(dict(st))

            with patch.object(orch, 'validate_resume_state', lambda *a, **k: None), \
                 patch.object(orch, 'save_resume_checkpoint', side_effect=capture_save), \
                 patch.object(orch, 'transition_checkpoint', lambda *a, **k: None):
                result = orch.run_task(
                    'TASK-SIM-009', repo, self.make_policy(), ctx=ctx,
                    max_fix_cycles=0, resume_state=state,
                )
            self.assertEqual(result['status'], 'REJECTED_AFTER_REVIEW')
            self.assertTrue(saved)
            self.assertEqual(Path(saved[0]['diagnosis_path']), p10.resolve())
            self.assertEqual(saved[0]['diagnosis_sequence'], 10)
            self.assertEqual(saved[0]['diagnosis_binding_source'], 'task_history')


if __name__ == '__main__':
    unittest.main(verbosity=2)
