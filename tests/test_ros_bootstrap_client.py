"""Bounded bootstrap must observe completion without restarting a ROS CLI node."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime


def test_initial_pose_reuses_the_run_owned_client_and_original_bound():
    runtime=object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements={}
    calls=[]
    class Client:
        def request(self,label,command,timeout):
            calls.append((label,timeout))
            return {'ok':True,'events':[{'event':'publish_complete'}]}
    runtime._bootstrap_client=Client()
    with patch('scripts.run_simulation_navigation.subprocess.run',side_effect=AssertionError('fresh CLI startup consumed publication bound')):
        result=runtime._probe('initial_pose_publish',['ros2','topic','pub','--once','/initialpose','type','{}'],5)
    assert result.returncode==0
    assert calls==[('initial_pose_publish',5)]
    assert runtime.measurements['localization']['probes'][0]['client']=='persistent_ros_bootstrap'


def test_navigation_startup_requires_a_positive_service_response():
    runtime=object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements={}
    runtime._bootstrap_client=SimpleNamespace(request=lambda *_args:{'ok':False,'error':'negative service response'})
    with patch('scripts.run_simulation_navigation.subprocess.run',side_effect=AssertionError('new CLI node')):
        result=runtime._probe('navigation_lifecycle_start',['ros2','service','call'],10)
    assert result.returncode!=0


def helper():
    path=Path(__file__).resolve().parents[1]/'scripts/ros_bootstrap_client.py'
    assert path.exists(), 'run-owned ROS bootstrap helper is missing'
    spec=importlib.util.spec_from_file_location('bootstrap_helper',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_initial_pose_is_never_published_without_a_matching_amcl_subscription():
    module=helper();published=[]
    node=SimpleNamespace(get_subscriptions_info_by_topic=lambda _:[])
    publisher=SimpleNamespace(get_subscription_count=lambda:0,publish=published.append)
    result=module.publish_initial_pose(node,publisher,object(),deadline=0,spin=lambda *_:None)
    assert result['ok'] is False
    assert published==[]


def test_initial_pose_publishes_once_after_matching_without_cli_teardown_wait():
    module=helper();published=[]
    node=SimpleNamespace(get_subscriptions_info_by_topic=lambda _:[SimpleNamespace(node_name='amcl')])
    publisher=SimpleNamespace(get_subscription_count=lambda:1,publish=published.append)
    message=object()
    result=module.publish_initial_pose(node,publisher,message,deadline=float('inf'),spin=lambda *_:None)
    assert result['ok'] is True
    assert published==[message]


def test_partial_worker_response_cannot_extend_the_operation_deadline():
    import os,selectors,threading,time
    module=helper()
    read_fd,write_fd=os.pipe()
    stream=os.fdopen(read_fd,'r')
    os.write(write_fd,b'{')
    timer=threading.Timer(.3,lambda:os.write(write_fd,b'}\n'))
    client=object.__new__(module.RosBootstrapProcess)
    client.process=SimpleNamespace(stdout=stream)
    client.selector=selectors.DefaultSelector();client.selector.register(stream,selectors.EVENT_READ)
    timer.start()
    try:
        with pytest.raises(TimeoutError):client._read(time.monotonic()+.05)
    finally:
        timer.cancel();timer.join(timeout=1)
        stream.close();os.close(write_fd);client.selector.close()
