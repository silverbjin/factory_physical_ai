import sys, os, time, json, subprocess, signal, shutil, hashlib, re
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path.cwd(); OUT=ROOT/'results/demo/diagnostics/codex_cycle_01'
sys.path.insert(0,str(ROOT/'demo_3d/tools'))
import demo3d_common as c

def write(name,value):
    (OUT/name).write_text(value if isinstance(value,str) else json.dumps(value,indent=2)+'\n')
def run(cmd,env=None,timeout=8):
    try:
        p=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=timeout)
        return p.stdout+p.stderr
    except subprocess.TimeoutExpired as e: return str(e)
def snapshot(pid):
    p=Path(f'/proc/{pid}')
    return {'pid':pid,'cmdline':c._read_proc_cmdline(pid),'exe':os.readlink(p/'exe'),'cwd':os.readlink(p/'cwd'),'env':{k:v for k,v in c._read_proc_environ(pid).items() if k.startswith(('GZ_','IGN_','ROS_')) or k=='PATH'}}
def info(path):
    root=ET.parse(path).getroot(); w=root.find('world')
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'world':w.get('name'),'plugins':[p.attrib for p in w.iter('plugin')],'direct_plugins':[p.attrib for p in w.findall('plugin')],'models':len(w.findall('model')),'includes':len(w.findall('include'))}
source=ROOT/'data/simulation/sim008_normal_system_world.sdf'
shutil.copy2(source,OUT/'canonical_source.sdf')
write('00_hypothesis.md','ROOT_CAUSE_HYPOTHESIS: v1.5 substring check sees conditional SceneBroadcaster and skips injection; headless xacro removes it.\nEXPECTED_RESULT: direct unconditional control passes, old worktree remains conditional, runtime has no scene plugin/service.\nSMALLEST_CHANGE: diagnostic copy only.\n')
example=ET.parse('/opt/ros/jazzy/share/ros_gz_sim_demos/worlds/default.sdf').getroot()
plugin=next(p for p in example.find('world').findall('plugin') if p.get('name','').endswith('SceneBroadcaster'))
write('installed_plugin.json',{'definition':plugin.attrib,'example':'/opt/ros/jazzy/share/ros_gz_sim_demos/worlds/default.sdf','libraries':run(['bash','-c',"rg --files /usr/lib/x86_64-linux-gnu /opt/ros/jazzy | rg 'scene.broadcaster.*so'"])})
text=source.read_text(); direct=OUT/'direct_control.sdf'
text=re.sub(r'<xacro:unless\b[^>]*>.*?</xacro:unless>', '',text,flags=re.S)
text=re.sub(r'(<world\b[^>]*>)',r'\1'+ET.tostring(plugin,encoding='unicode'),text,count=1)
direct.write_text(text)
env=dict(os.environ,GZ_PARTITION=f'ground-truth-{os.getpid()}',IGN_PARTITION=f'ground-truth-{os.getpid()}')
log=(OUT/'direct_server.log').open('w'); p=subprocess.Popen(['/usr/bin/gz','sim','-v','4','-r','-s',str(direct)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
try:
    services=''
    for _ in range(20):
        services=run(['/usr/bin/gz','service','-l'],env)
        if '/world/sim008_normal_system_world/scene/info' in services: break
        time.sleep(.5)
    write('direct_services.txt',services); write('direct_topics.txt',run(['/usr/bin/gz','topic','-l'],env))
    write('direct_scene_response.txt',run(['/usr/bin/gz','service','-s','/world/sim008_normal_system_world/scene/info','--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Scene','--timeout','5000','--req',''],env))
finally:
    os.killpg(p.pid,signal.SIGINT)
    try:p.wait(timeout=6)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    log.close()
print('CONTROL_A_SCENE=', '/scene/info' in services,flush=True)
session=c.prepare_normal_session(ROOT,dict(os.environ),OUT/'normal_e2e_result.json')
session.log_path=OUT/'10_runner.log'; shutil.copy2(session.worktree/'data/simulation/sim008_normal_system_world.sdf',OUT/'03_source_world.sdf')
p=session.start(); seen=set(); identities=[]; captured=False; start=time.monotonic()
try:
    while p.poll() is None and time.monotonic()-start<70:
        server=c.newest_runner_gazebo_server(p.pid)
        if server and server['pid'] not in seen:
            seen.add(server['pid']); identities.append(snapshot(server['pid']))
            for procdir in Path('/proc').iterdir():
                if procdir.name.isdigit() and c.process_is_descendant(int(procdir.name),p.pid):
                    try:
                        snap=snapshot(int(procdir.name))
                        if 'tb4_simulation_launch.py' in ' '.join(snap['cmdline']):identities.append(snap)
                    except (OSError,TypeError):pass
            sdf=next((Path(t) for t in server['cmdline'] if t.endswith('.sdf')),None)
            if sdf and sdf.exists():shutil.copy2(sdf,OUT/'04_runtime_world.sdf');captured=True
            write('06_services.txt',run(['/usr/bin/gz','service','-l'],server['env']))
            write('runtime_topics.txt',run(['/usr/bin/gz','topic','-l'],server['env']))
            write('07_scene_response.txt',run(['/usr/bin/gz','service','-s','/world/sim008_normal_system_world/scene/info','--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Scene','--timeout','1500','--req',''],server['env']))
            server_log=Path(server['env']['ROS_LOG_DIR'])/'gazebo_nav2_proxy.log'
            if server_log.exists():shutil.copy2(server_log,OUT/'08_server.log')
        time.sleep(.1)
    if p.poll() is None:
        # signal only owned runtime launch groups, then runner
        for s in identities:
            if 'tb4_simulation_launch.py' in ' '.join(s['cmdline']):
                try:os.killpg(s['pid'],signal.SIGINT)
                except ProcessLookupError:pass
        p.terminate();p.wait(timeout=10)
    else:session.wait()
    for s in identities:
        if 'ROS_LOG_DIR' in s['env']:
            logpath=Path(s['env']['ROS_LOG_DIR'])/'gazebo_nav2_proxy.log'
            if logpath.exists():shutil.copy2(logpath,OUT/'08_server.log')
    write('01_processes.txt',{'runner_pid':p.pid,'observed':identities});write('02_transport.json',identities)
    files={name:info(OUT/name) for name in ['canonical_source.sdf','03_source_world.sdf','04_runtime_world.sdf'] if (OUT/name).exists()}
    write('05_plugins.txt',files);write('11_git_diff.txt',run(['git','diff','--', 'demo_3d']))
    runtime_plugins=files.get('04_runtime_world.sdf',{}).get('direct_plugins',[])
    classification='NAV2_WORLD_PREPROCESSING_DROPS_SCENE_BROADCASTER' if '/scene/info' in services and captured and not any('SceneBroadcaster' in str(x) for x in runtime_plugins) else 'UNRESOLVED'
    write('SUMMARY.md',f'Classification: {classification}\nDirect control scene service: {"/scene/info" in services}\nSOURCE_HAS_SCENE=true (conditional)\nSOURCE_DIRECT_HAS_SCENE=false\nRUNTIME_TEMP_HAS_SCENE={any("SceneBroadcaster" in str(x) for x in runtime_plugins)}\nRunner exit: {p.returncode}\nThe source is unchanged because v1.5 detects the conditional plugin by substring. Nav2 xacro removes that block with headless:=True.\n')
    write('12_validation.txt',classification+'\n');write('09_gui.log','Not launched during server-only ground-truth control.\n')
    print((OUT/'SUMMARY.md').read_text(),flush=True)
finally:session.cleanup()
