import subprocess,sys,time,os,json,concurrent.futures
from pathlib import Path
root=Path.cwd();out=root/'results/demo/diagnostics/codex_cycle_10';proof=root/'results/demo/final_validation'
sys.path.insert(0,str(root/'demo_3d/tools'));import demo3d_common as c
log=(out/'package_console.txt').open('w');env=dict(os.environ,DEMO_VALIDATION_DIR=str(proof),DEMO_NO_WAIT='1')
p=subprocess.Popen(['bash',str(root/'demo_3d/scripts/01_normal_e2e_3d.sh')],env=env,stdout=log,stderr=subprocess.STDOUT)
started=time.monotonic();probed=False
while p.poll() is None:
 if not probed and time.monotonic()-started>15 and (proof/'runtime_identity.json').exists():
  identity=json.loads((proof/'runtime_identity.json').read_text())[-1];server=c._read_proc_environ(identity['server']['pid'])
  if server:
   probes={'ros_clock_info_daemon':['/opt/ros/jazzy/bin/ros2','topic','info','/clock','-v'],
           'ros_clock_info_direct':['/opt/ros/jazzy/bin/ros2','topic','info','/clock','-v','--no-daemon'],
           'ros_nodes_direct':['/opt/ros/jazzy/bin/ros2','node','list','--no-daemon'],
           'ros_clock_echo_direct':['/opt/ros/jazzy/bin/ros2','topic','echo','--once','/clock','rosgraph_msgs/msg/Clock','--no-daemon'],
           'gz_clock_info':['gz','topic','-i','-t','/clock']}
   def probe(item):
    name,args=item
    try:
     r=subprocess.run(args,env=server,text=True,capture_output=True,timeout=6)
     result={'command':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
     result={'command':args,'timed_out':True,'stdout':(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else e.stdout,'stderr':(e.stderr or b'').decode() if isinstance(e.stderr,bytes) else e.stderr}
    (out/(name+'.json')).write_text(json.dumps(result,indent=2))
   with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:list(executor.map(probe,probes.items()))
   probed=True
 time.sleep(.3)
log.close();print((out/'package_console.txt').read_text());raise SystemExit(p.returncode)
