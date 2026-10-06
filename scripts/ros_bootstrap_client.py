#!/usr/bin/env python3
"""Run-owned persistent ROS clients for bounded bootstrap operations.

ROS imports stay in the system-Python worker. The orchestration environment does
not need ROS Python packages, and the participant inherits the run's DDS identity.
"""
from __future__ import annotations
import json
import os
import selectors
import subprocess
import time
from pathlib import Path


def stamp(event, **fields):
    return dict(event=event, unix_ns=time.time_ns(), monotonic_ns=time.monotonic_ns(), **fields)


def publish_initial_pose(node, publisher, message, *, deadline, spin):
    events=[stamp('subscription_wait_start')]
    while time.monotonic() < deadline:
        subscribers=node.get_subscriptions_info_by_topic('/initialpose')
        if publisher.get_subscription_count() and any(item.node_name=='amcl' for item in subscribers):
            events.append(stamp('amcl_subscription_matched'))
            events.append(stamp('publish_call'))
            publisher.publish(message)
            events.append(stamp('publish_complete'))
            # Participant remains alive through TF/action readiness and mission
            # execution. map->odom is still independently required after publish.
            return {'ok':True,'events':events}
        spin(node,min(0.1,max(0,deadline-time.monotonic())))
    return {'ok':False,'error':'AMCL_SUBSCRIPTION_UNAVAILABLE','events':events+[stamp('timeout')]}


class RosBootstrapProcess:
    def __init__(self, environment):
        self.process=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).resolve()),'--worker'],env=dict(environment),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.selector=selectors.DefaultSelector()
        self.selector.register(self.process.stdout,selectors.EVENT_READ)
        os.set_blocking(self.process.stdout.fileno(),False)
        self._response_buffer=b''
        self.initialized=False

    def _read(self, deadline):
        buffer=getattr(self,'_response_buffer',b'')
        while time.monotonic()<deadline:
            if b'\n' in buffer:
                line,self._response_buffer=buffer.split(b'\n',1)
                return json.loads(line)
            if not self.selector.select(max(0,deadline-time.monotonic())):
                break
            chunk=os.read(self.process.stdout.fileno(),65536)
            if not chunk:raise RuntimeError('bootstrap client exited before response')
            buffer+=chunk
        self._response_buffer=buffer
        raise TimeoutError('bootstrap client response deadline exceeded')

    def request(self,label,command,timeout):
        deadline=time.monotonic()+timeout
        if not self.initialized:
            ready=self._read(deadline)
            if ready.get('ready') is not True:raise RuntimeError('bootstrap client initialization failed')
            self.initialized=True
        self.process.stdin.write(json.dumps({'label':label,'command':command,'deadline':deadline})+'\n')
        self.process.stdin.flush()
        return self._read(deadline)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:self.process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill();self.process.communicate()
        self.selector.close()
        return self.process.poll() is not None


def worker():
    import sys
    import rclpy
    import yaml
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav2_msgs.srv import ManageLifecycleNodes
    from rosidl_runtime_py import set_message_fields
    rclpy.init()
    node=rclpy.create_node('bounded_runtime_bootstrap')
    publisher=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
    client=node.create_client(ManageLifecycleNodes,'/lifecycle_manager_navigation/manage_nodes')
    print(json.dumps({'ready':True,'events':[stamp('participant_ready')]}),flush=True)
    try:
        for line in sys.stdin:
            request=json.loads(line);deadline=request['deadline'];label=request['label']
            try:
                if label=='initial_pose_publish':
                    message=PoseWithCovarianceStamped()
                    set_message_fields(message,yaml.safe_load(request['command'][-1]))
                    result=publish_initial_pose(node,publisher,message,deadline=deadline,spin=lambda n,t:rclpy.spin_once(n,timeout_sec=t))
                elif label=='navigation_lifecycle_start':
                    events=[stamp('service_wait_start')]
                    if not client.wait_for_service(timeout_sec=max(0,deadline-time.monotonic())):
                        result={'ok':False,'error':'NAVIGATION_SERVICE_UNAVAILABLE','events':events}
                    else:
                        events.append(stamp('service_available'))
                        message=ManageLifecycleNodes.Request();message.command=0
                        events.append(stamp('service_request_send'))
                        future=client.call_async(message)
                        rclpy.spin_until_future_complete(node,future,timeout_sec=max(0,deadline-time.monotonic()))
                        response=future.result() if future.done() else None
                        result={'ok':response is not None and response.success is True,'events':events+[stamp('service_response_received' if response is not None else 'timeout')], 'response':str(response)}
                else:result={'ok':False,'error':'UNSUPPORTED_BOOTSTRAP_OPERATION'}
            except Exception as exc:result={'ok':False,'error':repr(exc)}
            print(json.dumps(result),flush=True)
    finally:
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__':worker()
