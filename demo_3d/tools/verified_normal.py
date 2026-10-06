"""Run the real SIM-008 mission and require live 3D evidence before success."""
from __future__ import annotations
import fcntl
import uuid
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import demo3d_common as c

WORLD = 'sim008_normal_system_world'
ENTITY = 'brake_ecu_type_b_001'
SERVICE = f'/world/{WORLD}/scene/info'


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def command(args, env=None, timeout=7):
    try:
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout+p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, str(e)


def proc_identity(pid):
    path = Path(f'/proc/{pid}')
    env = c._read_proc_environ(pid)
    if env is None:
        raise ProcessLookupError(pid)
    return {'pid': pid, 'start_ticks': path.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
            'cmdline': c._read_proc_cmdline(pid), 'exe': os.readlink(path/'exe'),
            'cwd': os.readlink(path/'cwd'), 'env': {k: v for k, v in env.items()
            if k in ('PATH','ROS_DOMAIN_ID','ROS_LOG_DIR','DISPLAY','WAYLAND_DISPLAY','FASTDDS_BUILTIN_TRANSPORTS','ROS_AUTOMATIC_DISCOVERY_RANGE','RMW_IMPLEMENTATION','FASTDDS_DEFAULT_PROFILES_FILE','FASTRTPS_DEFAULT_PROFILES_FILE') or k.startswith(('GZ_','IGN_'))}}


def alive(record):
    try:
        stat = Path(f"/proc/{record['pid']}/stat").read_text().rsplit(')',1)[1].split()
        return stat[0] != 'Z' and stat[19] == record['start_ticks']
    except (OSError, IndexError):
        return False


def protected_hashes(root):
    args=['git','-C',str(root),'ls-files','-z','--','data/simulation','results/simulation','results/reviews']
    paths=subprocess.check_output(args).decode().split('\0')
    return {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths if p and (root/p).is_file()}


def capture_window(out, gui_pid):
    """Capture the mapped Gazebo X11 window (WSLg root capture can fail)."""
    from screenshot_window import capture
    return capture(out, gui_pid)


def run(root):
    """One invocation owns one fresh proof directory; stale success is invalid."""
    base=root/'results/demo'
    base.mkdir(parents=True,exist_ok=True)
    with (base/'.normal_3d.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('[3D DEMO] another owned Normal 3D invocation is running',flush=True)
            return 1
        invocation=uuid.uuid4().hex
        explicit=os.environ.get('DEMO_VALIDATION_DIR')
        out=Path(explicit).resolve() if explicit else base/'runs'/invocation
        out.mkdir(parents=True,exist_ok=True)
        if any((out/name).exists() for name in ('invocation.json','10_runner.log','gates.json','runtime_identity.json')):
            print('[3D DEMO] refusing to mix proof with an existing invocation: '+str(out),flush=True)
            return 1
        manifest={'invocation_id':invocation,'state':'pending','directory':str(out)}
        dump(out/'invocation.json',manifest)
        if not explicit:
            latest=base/'latest_validation'
            if latest.exists() and not latest.is_symlink():
                # Preserve earlier package output rather than deleting it.
                archive=base/'runs'/('legacy-'+invocation)
                latest.rename(archive)
            link=base/('.latest-'+invocation)
            link.symlink_to(out.resolve(),target_is_directory=True)
            link.replace(latest)
        try:
            rc=_execute(root,out)
        except BaseException as error:
            manifest.update(state='failed',error=f'{type(error).__name__}: {error}')
            dump(out/'invocation.json',manifest)
            raise
        manifest.update(state='complete' if rc==0 else 'failed',exit_code=rc)
        dump(out/'invocation.json',manifest)
        return rc


def remember_owned(roots, owned):
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            pid=int(entry.name)
            if any(pid==root or c.process_is_descendant(pid,root) for root in roots if root):
                try:owned[pid]=proc_identity(pid)
                except (OSError, TypeError, IndexError):pass


def _execute(root,out):
    before = protected_hashes(root)
    dump(out/'canonical_hashes_before.json',before)
    preexisting = c.gazebo_server_snapshots()
    dump(out/'preexisting_servers.json',{pid: s['cmdline'] for pid,s in preexisting.items()})
    session=c.prepare_normal_session(root, c.visual_runner_env(root,c.runner_env()),out/'normal_e2e_result.json')
    session.log_path=out/'10_runner.log'
    try:
        shutil.copy2(session.worktree/'data/simulation/sim008_normal_system_world.sdf',out/'03_source_world.sdf')
    except BaseException:
        session.cleanup()
        raise
    owned={}; records=[]; gui=None; current=None; log_paths=set(); scene_ok=False
    world_confirmed=False; gui_received=False; screenshot=None; rc=1; runtime=None; failure=None; start=time.monotonic(); last_capture=0; last_live_pair=None
    proc=None
    try:
        proc=session.start()
        while proc.poll() is None:
            # Sample both runner and GUI trees, including during shutdown below.
            remember_owned([proc.pid, gui.pid if gui else None],owned)
            server=c.newest_runner_gazebo_server(proc.pid)
            if server and (current is None or server['pid'] != current['pid']):
                c.stop_proc(gui); gui=None
                current=server
                env=server['env']; cli=shutil.which('gz',path=env.get('PATH'))
                identity=proc_identity(server['pid'])
                tokens=shlex.split(' '.join(identity['cmdline']))
                sdf=next((Path(t) for t in tokens if t.endswith('.sdf')),None)
                deadline=time.monotonic()+3
                while sdf and not sdf.is_file() and time.monotonic()<deadline:
                    time.sleep(.05)
                if not sdf or not sdf.is_file():
                    raise RuntimeError('Exact live runtime SDF is unavailable after generation wait')
                shutil.copy2(sdf,out/'04_runtime_world.sdf')
                world=ET.parse(sdf).getroot().find('world')
                runtime={'path':str(sdf),'sha256':hashlib.sha256(sdf.read_bytes()).hexdigest(),
                         'world':world.get('name'),'plugins':[p.attrib for p in world.iter('plugin')],
                         'source_models':len(world.findall('model')),'source_includes':len(world.findall('include')),
                         'visualization_augmentation':any('SceneBroadcaster' in p.get('name','') for p in world.findall('plugin'))}
                dump(out/'runtime_sdf_provenance.json',runtime)
                profile=Path(env['FASTRTPS_DEFAULT_PROFILES_FILE'])
                dump(out/'middleware_configuration.json',{'disclosure':'DEMO_MIDDLEWARE_ADAPTATION',
                     'profile_path':str(profile),'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
                     'actual_server_environment':{k:env.get(k) for k in ('RMW_IMPLEMENTATION','ROS_AUTOMATIC_DISCOVERY_RANGE','FASTRTPS_DEFAULT_PROFILES_FILE','FASTDDS_DEFAULT_PROFILES_FILE')},
                     'mission_deadlines_and_retries_changed':False})
                shutil.copy2(profile,out/'fastdds_loopback.xml')
                dump(out/'05_plugins.txt',runtime['plugins'])
                log_paths.add(Path(env['ROS_LOG_DIR'])/'gazebo_nav2_proxy.log')
                gui=c.start_gui_attach_to_server(server,os.environ.copy(),out/'09_gui.log')
                if gui is None: raise RuntimeError('GUI transport attachment failed')
                owned[gui.pid]=proc_identity(gui.pid)
                print(f"[3D DEMO] attached server={server['pid']} gui={gui.pid} partition={env.get('GZ_PARTITION')} domain={env.get('ROS_DOMAIN_ID')}",flush=True)
                deadline=time.monotonic()+8
                response=''; services=''
                while time.monotonic()<deadline and proc.poll() is None:
                    _,services=command([cli,'service','-l'],env,3)
                    (out/'06_services.txt').write_text(services)
                    if SERVICE in services:
                        _,response=command([cli,'service','-s',SERVICE,'--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Scene','--timeout','2000','--req',''],env,3)
                        if ENTITY in response: break
                    time.sleep(.1)
                world_rc,world_response=command([cli,'service','-s','/gazebo/worlds','--reqtype','gz.msgs.Empty','--reptype','gz.msgs.StringMsg_V','--timeout','2000','--req',''],env,3)
                world_confirmed=world_rc==0 and f'data: "{WORLD}"' in world_response
                (out/'live_world_response.txt').write_text(world_response)
                dump(out/'world_validation.json',{'service':'/gazebo/worlds','server_pid':server['pid'],'response':world_response,'pass':world_confirmed})
                (out/'07_scene_response.txt').write_text(response)
                scene_ok = SERVICE in services and ENTITY in response
                scene={'service':SERVICE,'service_available':SERVICE in services,'non_empty':bool(response.strip()),
                       'expected_entity':ENTITY,'expected_entity_present':ENTITY in response,
                       'world_name':WORLD,'scene_name_confirmed':f'name: "{WORLD}"' in response,
                       'model_count':len(re.findall(r'^\s*model \{',response,re.M)),
                       'link_count':len(re.findall(r'^\s*link \{',response,re.M)),
                       'visual_count':len(re.findall(r'^\s*visual \{',response,re.M)), 'pass':scene_ok}
                dump(out/'scene_validation.json',scene)
                pair={'server':proc_identity(server['pid']), 'gui':proc_identity(gui.pid)}
                pair['transport_match']=c.transport_matches(pair['server']['env'],pair['gui']['env'])
                pair['both_alive']=alive(pair['server']) and alive(pair['gui'])
                records.append(pair)
                dump(out/'runtime_identity.json',records)
                print(f'[3D DEMO] live scene confirmed={scene_ok} models={scene["model_count"]}',flush=True)
            if gui:
                # Inspect renderer logs and capture the owned GUI window.
                log=(out/'09_gui.log').read_text(errors='replace')
                gui_received=gui_received or ('Received scene' in log or 'Received scene information' in log)
                if screenshot is None and time.monotonic()-start>12 and time.monotonic()-last_capture>3:
                    last_capture=time.monotonic()
                    try:
                        candidate=capture_window(out/'gazebo_candidate.png', gui.pid)
                        if candidate.get('rendered_content'):
                            (out/'gazebo_candidate.png').replace(out/'gazebo_3d.png')
                            candidate['path']=str(out/'gazebo_3d.png')
                            screenshot=candidate
                    except Exception as e:(out/'screenshot_error.txt').write_text(str(e)+'\n')
                if gui.poll() is not None: raise RuntimeError('GUI exited while mission was running')
                if current and Path(f"/proc/{current['pid']}").exists():
                    try:
                        last_live_pair={'server':proc_identity(current['pid']),'gui':proc_identity(gui.pid)}
                        if not c.transport_matches(last_live_pair['server']['env'],last_live_pair['gui']['env']):
                            raise RuntimeError('GUI/server transport changed during mission')
                    except (OSError, TypeError):pass
            if time.monotonic()-start>150:
                raise RuntimeError('Demo runner exceeded 150-second outer safety bound')
            time.sleep(.1)
        rc=session.wait()
    except Exception as e:
        failure=str(e)
        print('[3D DEMO] verification error: '+failure,flush=True)
    finally:
        remember_owned([proc.pid if proc else None, gui.pid if gui else None],owned)
        if failure and proc is not None and proc.poll() is None:
            proc.terminate()
        c.stop_proc(gui)
        # Give canonical cleanup time to finish; terminate only identities owned here.
        deadline=time.monotonic()+6
        while any(alive(r) for r in owned.values()) and time.monotonic()<deadline:
            remember_owned([proc.pid if proc else None]+[r['pid'] for r in owned.values() if alive(r)],owned)
            time.sleep(.1)
        leftovers=[r for r in owned.values() if alive(r)]
        for sig in (signal.SIGTERM,signal.SIGKILL):
            for record in leftovers:
                if alive(record):
                    try:os.kill(record['pid'],sig)
                    except ProcessLookupError:pass
            if leftovers:time.sleep(.3)
        if proc is not None:
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:pass
        if session.generated_output.is_file() and not (out/'normal_e2e_result.json').exists():
            shutil.copy2(session.generated_output,out/'normal_e2e_result.json')
        for logpath in log_paths:
            if logpath.exists():shutil.copy2(logpath,out/'08_server.log')
        session.cleanup()
    dump(out/'01_processes.txt',list(owned.values()))
    dump(out/'02_transport.json',records)
    lifecycle={'elapsed_seconds':round(time.monotonic()-start,2),'runner_exit_code':rc,'exception':failure,
               'owned_pids':sorted(owned),'alive_after_cleanup':[r['pid'] for r in owned.values() if alive(r)],
               'supplemental_cleanup_pids':[r['pid'] for r in leftovers],
               'preexisting_pids_untouched':sorted(preexisting)}
    dump(out/'process_lifecycle.json',lifecycle)
    after=protected_hashes(root)
    status=subprocess.check_output(['git','-C',str(root),'status','--short','--','data/simulation','results/simulation','results/reviews'],text=True)
    intact=before==after and not status.strip()
    (out/'canonical_integrity.txt').write_text(f'hashes_identical={before==after}\n'+status)
    result=json.loads((out/'normal_e2e_result.json').read_text()) if (out/'normal_e2e_result.json').exists() else {}
    log=(out/'09_gui.log').read_text(errors='replace') if (out/'09_gui.log').exists() else ''
    fatal=re.findall(r'^.*(?:OGRE EXCEPTION|RenderingAPIException|Unable to create.*(?:render|GL)|Failed to (?:initialize|create).*(?:EGL|GL|render)|Segmentation fault|terminate called).*$' ,log,re.M|re.I)
    dump(out/'gui_health.json',{'fatal_errors':fatal,'scene_received_in_log':gui_received,'screenshot':screenshot,
                             'alive_on_attach':all(r['both_alive'] for r in records) if records else False,
                             'last_live_pair':last_live_pair})
    gates={'A':bool(records) and all(r['transport_match'] for r in records),
           'B':bool(runtime) and runtime['world']==WORLD and world_confirmed,
           'C':(out/'06_services.txt').exists() and SERVICE in (out/'06_services.txt').read_text(),
           'D':scene_ok,'E':bool(runtime) and runtime['visualization_augmentation'],
           'F':bool(records) and all(r['both_alive'] for r in records) and not fatal and failure is None and bool(screenshot and screenshot.get('rendered_content')),
           'G':rc==0 and result.get('task_specific_result')=='SIM_NORMAL_E2E_READY' and result.get('execution',{}).get('lifecycle',{}).get('cleanup_complete') is True and not lifecycle['alive_after_cleanup'],
           'H':intact}
    dump(out/'gates.json',gates)
    (out/'11_git_diff.txt').write_text(command(['git','-C',str(root),'diff','--','demo_3d'])[1])
    (out/'12_validation.txt').write_text(json.dumps(gates,indent=2)+'\n')
    summary='\n'.join([f'Gate {k}: {"PASS" if v else "FAIL"}' for k,v in gates.items()])
    (out/'SUMMARY.md').write_text('# Live SIM-008 3D validation\n\n'+summary+'\n\nDEMO_VISUALIZATION_AUGMENTATION: resolved headless world plus installed SceneBroadcaster.\nMission uses the unchanged SIM-008 runner and Nav2 launch. Accepted Evidence is preserved.\nScreenshot: '+str(screenshot)+'\nGUI scene receive log: '+str(gui_received)+'\nException: '+str(failure)+'\n')
    c.write_state(root,scene='normal',phase='complete' if all(gates.values()) else 'failed',validation=str(out),gates=gates)
    print(summary,flush=True)
    return 0 if all(gates.values()) else 1
