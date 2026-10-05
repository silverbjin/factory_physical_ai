"""Regression for the conditional plugin that silently vanished at runtime."""
import subprocess, sys, tempfile, unittest, xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demo3d_common import inject_scene_broadcaster_text, _is_gazebo_server, has_flag

class SceneAugmentation(unittest.TestCase):
    def test_scene_plugin_survives_real_nav2_headless_xacro(self):
        source=Path(__file__).resolve().parents[2]/'data/simulation/sim008_normal_system_world.sdf'
        text, changed=inject_scene_broadcaster_text(source.read_text())
        processed=subprocess.run(['/opt/ros/jazzy/bin/xacro','headless:=True','/dev/stdin'],input=text,text=True,capture_output=True,check=True).stdout
        world=ET.fromstring(processed).find('world')
        self.assertEqual(len([p for p in world.findall('plugin') if p.get('name')=='gz::sim::systems::SceneBroadcaster']),1)
        self.assertIsNotNone(world.find("model[@name='brake_ecu_type_b_001']"))
        second, changed=inject_scene_broadcaster_text(text)
        self.assertFalse(changed)
        self.assertEqual(second,text)
    def test_capability_probe_never_executes_a_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); marker=root/'mission_executed'
            script=root/'runner.py'
            script.write_text("import argparse\nfrom pathlib import Path\np=argparse.ArgumentParser()\np.add_argument('--output')\nPath("+repr(str(marker))+").write_text('executed')\n")
            flag=has_flag(script,'--output')
            self.assertFalse(marker.exists(), 'Capability discovery executed the mission')
            self.assertEqual(flag,'--output')
    def test_server_discovery_handles_gazebo_rewritten_process_title(self):
        self.assertTrue(_is_gazebo_server(['gz sim -r -s /tmp/nav2_actual.sdf']))
        self.assertFalse(_is_gazebo_server(['gz sim -g']))
        self.assertFalse(_is_gazebo_server(['bash','-c',"echo 'unbalanced"]))
        self.assertTrue(_is_gazebo_server(['ruby','/opt/ros/jazzy/bin/gz','sim','-r','-s','/tmp/nav2_actual.sdf']))

if __name__=='__main__':unittest.main()
