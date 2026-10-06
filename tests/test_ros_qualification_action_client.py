import time
from types import SimpleNamespace

def test_warmed_action_requires_successful_terminal_result():
    from scripts.ros_qualification_action_client import execute_goal
    class Future:
        def __init__(self,value):self.value=value
        def done(self):return True
        def result(self):return self.value
    class Handle:
        accepted=True
        def get_result_async(self):return Future(SimpleNamespace(status=4))
    class Client:
        def wait_for_server(self,timeout_sec):return True
        def send_goal_async(self,message):return Future(Handle())
    result=execute_goal(None,Client(),None,time.monotonic()+5,lambda *args:None)
    assert result['ok'] is True and result['terminal_status']==4
    assert [e['event'] for e in result['events']]==['action_server_wait','action_server_ready','goal_send','goal_response','goal_terminal']

def test_warmed_action_rejection_is_failure():
    from scripts.ros_qualification_action_client import execute_goal
    class Future:
        def done(self):return True
        def result(self):return SimpleNamespace(accepted=False)
    class Client:
        def wait_for_server(self,timeout_sec):return True
        def send_goal_async(self,message):return Future()
    result=execute_goal(None,Client(),None,time.monotonic()+5,lambda *args:None)
    assert result['ok'] is False and result['error']=='GOAL_REJECTED'
