
import os
from pybird import PyBird

this_dir = os.path.dirname(__file__)
data_dir = os.path.join(this_dir, 'data')


def test_get_config(bird):
    bird = PyBird(None, config_file=os.path.join(data_dir, 'config', 'basic.conf'))
    assert bird.get_config()
