"""Invoke the unchanged canonical main; export existing probes after cleanup."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def wrap_close(original, output):
    def observed_close(port):
        try:
            return original(port)
        finally:
            control=getattr(port.runtime, '_diagnostic_control', None)
            if control is not None and control.poll() is None:
                control.terminate()
                try: control.communicate(timeout=2)
                except Exception:
                    control.kill()
                    control.communicate()
            payload={'measurements':port.runtime.measurements,
                     'transport':{k:port.runtime.environment.get(k) for k in ['ROS_DOMAIN_ID','GZ_PARTITION','ROS_LOG_DIR','FASTDDS_BUILTIN_TRANSPORTS','ROS_AUTOMATIC_DISCOVERY_RANGE','RMW_IMPLEMENTATION','FASTDDS_DEFAULT_PROFILES_FILE','FASTRTPS_DEFAULT_PROFILES_FILE']},
                     'disclosure':'DEMO_RUNTIME_OBSERVATION: existing measurements exported after original cleanup'}
            try:
                output.write_text(json.dumps(payload,indent=2,default=str)+'\n')
            except OSError as error:
                print('Could not export runtime observations: '+str(error),file=sys.stderr)
    return observed_close


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runner',type=Path,required=True)
    parser.add_argument('--observations',type=Path,required=True)
    args=parser.parse_args()
    spec=importlib.util.spec_from_file_location('canonical_sim008',args.runner)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if os.environ.get('DEMO_DIAGNOSTIC_PROBES') == '1':
        from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
        from probe_diagnostics import install
        install(BoundedGazeboNav2Runtime, args.observations)
    module.GazeboSystemWorld.close=wrap_close(module.GazeboSystemWorld.close,args.observations)
    return module.main()


if __name__=='__main__':raise SystemExit(main())
