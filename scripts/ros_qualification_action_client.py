"""Canonical component control: run-owned warmed NavigateToPose client."""
from __future__ import annotations
import json
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.ros_bootstrap_client import RosBootstrapProcess,stamp


def execute_goal(node,client,message,deadline,spin):
    events=[stamp('action_server_wait')]
    if not client.wait_for_server(timeout_sec=max(0,deadline-time.monotonic())):
        return {'ok':False,'error':'ACTION_SERVER_UNAVAILABLE','events':events+[stamp('timeout')]}
    events.extend([stamp('action_server_ready'),stamp('goal_send')])
    future=client.send_goal_async(message)
    spin(node,future,max(0,deadline-time.monotonic()))
    if not future.done():return {'ok':False,'error':'GOAL_ACK_TIMEOUT','events':events+[stamp('timeout')]}
    handle=future.result();goal_uuid=bytes(handle.goal_id.uuid).hex() if getattr(handle,'goal_id',None) is not None else None
    events.append(stamp('goal_response',accepted=handle.accepted,goal_uuid=goal_uuid))
    if not handle.accepted:return {'ok':False,'error':'GOAL_REJECTED','events':events}
    future=handle.get_result_async()
    spin(node,future,max(0,deadline-time.monotonic()))
    if not future.done():
        handle.cancel_goal_async()
        return {'ok':False,'error':'GOAL_TERMINAL_TIMEOUT','events':events+[stamp('timeout')]}
    response=future.result();status=response.status;error_code=getattr(getattr(response,'result',None),'error_code',0)
    events.append(stamp('goal_terminal',status=status,goal_uuid=goal_uuid,error_code=error_code))
    return {'ok':status==4 and error_code==0,'terminal_status':status,'goal_uuid':goal_uuid,'error_code':error_code,'events':events}


class QualificationActionProcess(RosBootstrapProcess):
    def __init__(self,environment):
        self.process=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).resolve()),'--worker'],env=dict(environment),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        os.set_blocking(self.process.stdout.fileno(),False);self._response_buffer=b'';self.initialized=False


def worker():
    import rclpy
    import yaml
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from rosidl_runtime_py import set_message_fields
    rclpy.init();node=rclpy.create_node('canonical_qualification_action')
    client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
    print(json.dumps({'ready':True,'events':[stamp('action_participant_ready')]}),flush=True)
    try:
        for line in sys.stdin:
            request=json.loads(line);message=NavigateToPose.Goal()
            set_message_fields(message,yaml.safe_load(request['command'][-1]))
            result=execute_goal(node,client,message,request['deadline'],lambda n,f,t:rclpy.spin_until_future_complete(n,f,timeout_sec=t))
            result['request_identity']=request['command'][0]
            print(json.dumps(result),flush=True)
    finally:
        client.destroy();node.destroy_node();rclpy.shutdown()


if __name__=='__main__':worker()
