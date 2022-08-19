import os

import filedata
import pytest

from pybird import PyBird

this_dir = os.path.dirname(__file__)
data_dir = os.path.join(this_dir, "data")


@pytest.fixture
def bird():
    return PyBird(None)


def pytest_generate_tests(metafunc):
    for fixture in metafunc.fixturenames:
        if fixture.startswith("data_"):
            data = filedata.get_test_data(fixture)
            metafunc.parametrize(fixture, data.values(), ids=data.keys())
