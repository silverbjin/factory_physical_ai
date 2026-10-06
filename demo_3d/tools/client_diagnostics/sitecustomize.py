"""Opt-in, demo-only timestamps for unchanged ROS CLI clients."""
import atexit
import hashlib
import json
import os
import sys
import time

TRACE = os.environ.get('DEMO_CLIENT_TRACE')

def event(event_name, **data):
    if TRACE:
        with open(TRACE, 'a') as stream:
            stream.write(json.dumps(dict(event=event_name, unix_ns=time.time_ns(), monotonic_ns=time.monotonic_ns(), pid=os.getpid(), **data), default=str)+'\n')

if TRACE and 'ros2' in os.path.basename(sys.argv[0]):
    event('client_python_start', argv=sys.argv, environment={k:os.environ.get(k) for k in ('ROS_DOMAIN_ID','GZ_PARTITION','RMW_IMPLEMENTATION','ROS_AUTOMATIC_DISCOVERY_RANGE','FASTDDS_DEFAULT_PROFILES_FILE','FASTRTPS_DEFAULT_PROFILES_FILE')}, profiles={k:hashlib.sha256(open(os.environ[k],'rb').read()).hexdigest() for k in ('FASTDDS_DEFAULT_PROFILES_FILE','FASTRTPS_DEFAULT_PROFILES_FILE') if os.environ.get(k) and os.path.isfile(os.environ[k])})
    atexit.register(lambda:event('client_python_exit'))
    try:
        from rclpy.node import Node
        from rclpy.publisher import Publisher
        from rclpy.client import Client
        original_init=Node.__init__
        def node_init(self,*args,**kwargs):
            event('node_create_start')
            original_init(self,*args,**kwargs)
            event('node_create_complete',name=self.get_name())
        Node.__init__=node_init
        original_create=Node.create_publisher
        publishers={}
        def create(self,msg_type,topic,qos,*args,**kwargs):
            pub=original_create(self,msg_type,topic,qos,*args,**kwargs)
            if topic=='/initialpose':
                publishers[id(pub)]=self
                event('publisher_created',topic=topic,qos=str(qos))
            return pub
        Node.create_publisher=create
        original_count=Publisher.get_subscription_count
        counts={}
        def count(self):
            value=original_count(self)
            if id(self) in publishers and counts.get(id(self))!=value:
                counts[id(self)]=value
                node=publishers[id(self)]
                event('subscription_match',topic='/initialpose',count=value,endpoints=[{'node':e.node_name,'namespace':e.node_namespace,'qos':str(e.qos_profile)} for e in node.get_subscriptions_info_by_topic('/initialpose')])
            return value
        Publisher.get_subscription_count=count
        original_publish=Publisher.publish
        def publish(self,msg):
            if id(self) in publishers:event('publish_call',topic='/initialpose')
            value=original_publish(self,msg)
            if id(self) in publishers:event('publish_complete',topic='/initialpose')
            return value
        Publisher.publish=publish
        original_wait=Client.wait_for_service
        def wait(self,*args,**kwargs):
            event('service_wait_start',service=self.srv_name)
            value=original_wait(self,*args,**kwargs)
            event('service_wait_complete',service=self.srv_name,available=value)
            return value
        Client.wait_for_service=wait
        original_call=Client.call_async
        def call(self,request):
            event('service_request_send',service=self.srv_name,request=str(request))
            future=original_call(self,request)
            future.add_done_callback(lambda f:event('service_response_received',service=self.srv_name,response=str(f.result())))
            return future
        Client.call_async=call
    except Exception as exc:
        event('diagnostic_error',error=repr(exc))
