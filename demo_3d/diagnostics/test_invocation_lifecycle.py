"""Regression checks for review findings without running a mission."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demo3d_common as c
import verified_normal as v

ROOT=Path(__file__).resolve().parents[2]

class InvocationLifecycle(unittest.TestCase):
    def test_patch_failure_removes_the_real_detached_worktree(self):
        def worktrees():
            return {line[9:] for line in subprocess.check_output(['git','-C',str(ROOT),'worktree','list','--porcelain'],text=True).splitlines() if line.startswith('worktree ')}
        before=worktrees()
        try:
            with patch.object(c,'patch_sim008_worktree_world',side_effect=ValueError('injected xacro failure')):
                with self.assertRaises(ValueError):c.prepare_normal_session(ROOT,dict(os.environ),Path('/tmp/unused-demo-output'))
            self.assertEqual(worktrees(),before,'Preparation leaked a registered worktree')
        finally:
            for path in worktrees()-before:
                subprocess.run(['git','-C',str(ROOT),'worktree','remove','--force',path],check=True)
    def test_each_default_invocation_has_fresh_proof_and_current_metadata(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{},clear=True), patch.object(v,'_execute',return_value=0):
            root=Path(tmp)
            self.assertEqual(v.run(root),0)
            first=(root/'results/demo/latest_validation').resolve()
            self.assertEqual(v.run(root),0)
            second=(root/'results/demo/latest_validation').resolve()
            self.assertNotEqual(first,second)
            self.assertEqual(json.loads((second/'invocation.json').read_text())['state'],'complete')
            self.assertTrue(first.exists())
    def test_incomplete_invocation_cannot_reuse_old_passing_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            (path/'invocation.json').write_text(json.dumps({'invocation_id':'current','state':'pending'}))
            (path/'runtime_identity.json').write_text(json.dumps([{'server':{'pid':999999999,'start_ticks':'0'},'gui':{'pid':999999998,'start_ticks':'0'}}]))
            (path/'gates.json').write_text(json.dumps(dict.fromkeys('ABCDEFGH',True)))
            tool=ROOT/'demo_3d/tools/verify_3d_runtime.py'
            cp=subprocess.run([sys.executable,str(tool),'--validation-dir',tmp],text=True,capture_output=True)
            self.assertNotEqual(cp.returncode,0,'Incomplete invocation reused stale success')
            self.assertIn('incomplete',cp.stdout+cp.stderr)

if __name__=='__main__':unittest.main()
