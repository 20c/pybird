
import collections
import json
import os
from pybird import PyBird
import pytest


this_dir = os.path.dirname(__file__)
data_dir = os.path.join(this_dir, 'data')



@pytest.fixture
def bird():
    return PyBird(None)


class FileTestData(object):
    def __init__(self, inp=None, exp=None):
        self.input = inp
        self.expected = exp


def json_hook(data):
    date_keys = (
        'last_change',
        'last_reboot',
        'last_reconfiguration',
        )
    for key in date_keys:
        if key in data:
            data[key] = datetime.strptime(data[key], "%Y-%m-%dT%H:%M:%S")
    return data


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def get_test_files(name):
    """
    gets a list of files in directory specified by name
    underscore convered to /
    """
    dirname = os.path.join(this_dir, *name.split('_'))
    if not os.path.isdir(dirname):
        raise ValueError("data directory '{}' does not exist".format(dirname))
    path = dirname + "/{}"
    return map(path.format, sorted(os.listdir(dirname)))


def get_test_data(name):
    data = collections.OrderedDict()

    for each in get_test_files(name):
        fname = os.path.basename(each)
        if fname.startswith('.'):
            continue

        test_name, ext = os.path.splitext(fname)
        data.setdefault(test_name, FileTestData())

        # could setattr
        attr = ext[1:]
        if ext == '.expected':
            with open(each) as fobj:
                data[test_name].expected = json.load(fobj, object_hook=json_hook)
        else:
            with open(each) as fobj:
                setattr(data[test_name], attr, fobj.read())

    return data


def pytest_generate_tests(metafunc):
    for fixture in metafunc.fixturenames:
        if fixture.startswith('data_'):
            data = get_test_data(fixture)
            metafunc.parametrize(fixture, data.values(), ids=data.keys())

