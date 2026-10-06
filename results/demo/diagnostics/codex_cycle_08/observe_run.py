import subprocess,sys,time,os,json
from pathlib import Path
root=Path.cwd();out=root/'results/demo/diagnostics/codex_cycle_08';proof=root/'results/demo/final_validation'
sys.path.insert(0,str(root/'demo_3d/tools'));import demo3d_common as c
log=(out/'package_console.txt').open('w')
env=dict(os.environ,DEMO_VALIDATION_DIR=str(proof),DEMO_NO_WAIT='1')
p=subprocess.Popen(['bash',str(root/'demo_3d/scripts/01_normal_e2e_3d.sh')],env=env,stdout=log,stderr=subprocess.STDOUT)
started=time.monotonic();samples=[];last=0;clock_checked=False
while p.poll() is None:
 elapsed=time.monotonic()-started
 if elapsed-last>4:
  last=elapsed
  sample={'elapsed_seconds':elapsed,'processes':[]}
  for entry in Path('/proc').iterdir():
   if not entry.name.isdigit():continue
   pid=int(entry.name)
   cmd=c._read_proc_cmdline(pid) or []
   if c.process_is_descendant(pid,p.pid) and any(s in ' '.join(cmd) for s in ['parameter_bridge','robot_state_publisher','component_container_isolated']):
    try:
     sample['processes'].append({'pid':pid,'cmd':cmd,'status':(entry/'status').read_text(),'wchan':(entry/'wchan').read_text(),
       'threads':[{'tid':t.name,'wchan':(t/'wchan').read_text()} for t in (entry/'task').iterdir()],
       'fds':{fd.name:os.readlink(fd) for fd in (entry/'fd').iterdir()},
       'relevant_env':{k:v for k,v in (c._read_proc_environ(pid) or {}).items() if k.startswith(('ROS','GZ_','IGN_','FAST','RMW','RCUTILS','LD_'))}})
    except OSError:pass
  samples.append(sample);(out/'ros_startup_samples.json').write_text(json.dumps(samples,indent=2))
 if not clock_checked and elapsed>15 and (proof/'runtime_identity.json').is_file():
  try:
   identity=json.loads((proof/'runtime_identity.json').read_text())[-1]
   server_env=c._read_proc_environ(identity['server']['pid'])
   if server_env:
    for name,args in [('clock',['gz','topic','-e','-n','1','-t','/clock']),('world_stats',['gz','topic','-e','-n','1','-t','/world/sim008_normal_system_world/stats'])]:
     result=subprocess.run(args,env=server_env,text=True,capture_output=True,timeout=3)
     (out/(name+'.txt')).write_text(result.stdout+result.stderr)
    clock_checked=True
  except (OSError,IndexError,subprocess.TimeoutExpired):clock_checked=True
 time.sleep(.3)
log.close();print('observed runner exit=',p.returncode)
print((out/'package_console.txt').read_text())
raise SystemExit(p.returncode)
