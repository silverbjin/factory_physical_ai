"""Gazebo may deliver multiple JSON frames for a one-message CLI request."""
import pytest
from scripts import run_simulation_normal_system_e2e as runner


def parser():
    value=getattr(runner,'parse_gazebo_stats_time',None)
    assert callable(value), 'Gazebo stats stream parser is missing'
    return value


def test_multiple_valid_stats_frames_use_latest_complete_observation():
    text='{"simTime":{"sec":"20","nsec":994000000}}\n{"simTime":{"sec":"21","nsec":3000000}}\n'
    assert parser()(text)=={'sec':21,'nsec':3000000}


def test_protobuf_default_zero_seconds_is_valid():
    assert parser()('{"simTime":{"nsec":3000000}}')=={'sec':0,'nsec':3000000}


@pytest.mark.parametrize('text',['','{"simTime":{"sec":-1}}','{"simTime":{"sec":2,"nsec":1000000000}}','{"simTime":{"sec":2}}\ninvalid','{"realTime":{"sec":2}}'])
def test_invalid_or_truncated_observations_remain_failure(text):
    with pytest.raises(RuntimeError,match='malformed'):
        parser()(text)
