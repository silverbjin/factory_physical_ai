"""Diagnostic publisher; never publishes unless commanded after a failed probe."""
import json,os,sys,threading,time
from pathlib import Path
import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.qos import QoSProfile
from rosidl_runtime_py import set_message_fields

path=Path(os.environ['DEMO_CONTROL_TRACE'])
def event(name,**kw):
    with path.open('a') as f:f.write(json.dumps(dict(event=name,unix_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),pid=os.getpid(),**kw),default=str)+'\n')
event('persistent_process_start')
rclpy.init();node=rclpy.create_node('initial_pose_diagnostic_control')
pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',QoSProfile(depth=10))
event('persistent_publisher_created')
received=[]
def pose(msg):
    event('amcl_pose_received',pose=str(msg));received.append(msg)
sub=node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',pose,10)
command=[]
def reader():
    line=sys.stdin.readline()
    if line:command.append(json.loads(line))
threading.Thread(target=reader,daemon=True).start()
last=None;sent=False;deadline=None
try:
    while rclpy.ok():
        count=pub.get_subscription_count()
        if count!=last:
            last=count;event('persistent_subscription_match',count=count,endpoints=[{'node':e.node_name,'qos':str(e.qos_profile)} for e in node.get_subscriptions_info_by_topic('/initialpose')])
        if command and not sent:
            deadline=time.monotonic()+5
            if count:
                msg=PoseWithCovarianceStamped();set_message_fields(msg,command[0]);received.clear()
                event('control_publish_call');pub.publish(msg);event('control_publish_complete');sent=True
        if sent and (received or time.monotonic()>deadline):
            print(json.dumps({'published':sent,'amcl_received':bool(received)}),flush=True);break
        rclpy.spin_once(node,timeout_sec=0.1)
finally:
    event('persistent_client_exit');node.destroy_node();rclpy.shutdown()
