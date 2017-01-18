
import os
from pybird import PyBird

this_dir = os.path.dirname(__file__)
data_dir = os.path.join(this_dir, 'data')

conf_basic = os.path.join(data_dir, 'config', 'basic.conf')

def test_get_config():
    bird = PyBird(None, config_file=conf_basic)
    assert bird.get_config()

def test_write_config(tmpdir):
    config_file = tmpdir.join('write.conf')
    with open(conf_basic) as fobj:
        conf = fobj.read()

    bird = PyBird(None, config_file=str(config_file))
    bird.put_config(conf)
    assert conf == config_file.read()
