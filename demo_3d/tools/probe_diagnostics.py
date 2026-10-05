"""Opt-in timing capture; preserves probe commands, deadlines and results."""
import json
import os
from pathlib import Path
import subprocess
import time

def install(runtime_class, output):
    original=runtime_class._probe
    def observed(self,label,command,timeout=10):
        start=time.time_ns()
        monotonic_start=time.monotonic_ns()
        if label == 'simulation_clock' and not hasattr(self, '_diagnostic_control'):
            env=dict(self.environment)
            env['DEMO_CONTROL_TRACE']=str(output.parent/'persistent_control_events.jsonl')
            self._diagnostic_control=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).parent/'client_diagnostics/persistent_control.py')],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        original_run=subprocess.run
        captured={}
        def run(args,*a,**kw):
            if args==command:
                env=dict(kw.get('env',os.environ))
                env['PYTHONPATH']=str(Path(__file__).parent/'client_diagnostics')+':'+env.get('PYTHONPATH','')
                env['DEMO_CLIENT_TRACE']=str(output.parent/'client_events.jsonl')
                env['PYTHONUNBUFFERED']='1'
                kw['env']=env
                try:
                    return original_run(args,*a,**kw)
                except subprocess.TimeoutExpired as exc:
                    def decode(value):return value.decode(errors='replace') if isinstance(value,bytes) else value
                    captured.update(timeout_at_unix_ns=time.time_ns(),partial_stdout=decode(exc.stdout),partial_stderr=decode(exc.stderr))
                    raise
            return original_run(args,*a,**kw)
        subprocess.run=run
        try:
            if label == 'initial_pose_publish' and os.environ.get('DEMO_PERSISTENT_POSE_CONTROL') == '1':
                import yaml
                stdout,stderr=self._diagnostic_control.communicate(json.dumps(yaml.safe_load(command[-1]))+'\n',timeout=timeout)
                result=subprocess.CompletedProcess(command,self._diagnostic_control.returncode,stdout,stderr)
                self.measurements['localization']['probes'].append({'label':label,'command':command,'returncode':result.returncode,'stdout':stdout,'stderr':stderr,'duration_ms':(time.monotonic_ns()-monotonic_start)/1e6,'timed_out':False,'control':'persistent client, identical pose'})
                return result
            result=original(self,label,command,timeout)
            if label == 'initial_pose_publish' and result is None:
                import yaml
                try:
                    stdout,stderr=self._diagnostic_control.communicate(json.dumps(yaml.safe_load(command[-1]))+'\n',timeout=5)
                    captured['persistent_control']={'stdout':stdout,'stderr':stderr,'returncode':self._diagnostic_control.returncode}
                except subprocess.TimeoutExpired:
                    self._diagnostic_control.kill()
                    stdout,stderr=self._diagnostic_control.communicate()
                    captured['persistent_control']={'timed_out':True,'stdout':stdout,'stderr':stderr}
            return result
        finally:
            subprocess.run=original_run
            record=self.measurements['localization']['probes'][-1]
            record.update(start_unix_ns=start,end_unix_ns=time.time_ns(),start_monotonic_ns=monotonic_start,end_monotonic_ns=time.monotonic_ns(),**captured)
            with (output.parent/'probe_events.jsonl').open('a') as stream:stream.write(json.dumps(record,default=str)+'\n')
    runtime_class._probe=observed
