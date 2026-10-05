import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from observed_normal_entry import wrap_close

class RuntimeObservation(unittest.TestCase):
    def test_observation_runs_only_after_the_original_cleanup_and_preserves_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'observations.json';events=[]
            port=SimpleNamespace(runtime=SimpleNamespace(measurements={'localization':{'probes':[{'label':'simulation_clock','stdout':'sec: 12','timed_out':False}]}},environment={'ROS_DOMAIN_ID':'81','GZ_PARTITION':'test'}))
            def close(self):events.append('cleanup');return True
            wrapped=wrap_close(close,path)
            self.assertFalse(path.exists());self.assertEqual(events,[])
            self.assertIs(wrapped(port),True)
            self.assertEqual(events,['cleanup'])
            self.assertEqual(json.loads(path.read_text())['measurements']['localization']['probes'][0]['stdout'],'sec: 12')

if __name__=='__main__':unittest.main()
