
from datetime import datetime, timedelta, date
import json
import os
import pytest
import socket
from tempfile import mkdtemp
from threading import Thread
from time import sleep
import traceback
import unittest

from pybird import PyBird


this_dir = os.path.dirname(__file__)
data_dir = os.path.join(this_dir, 'data')


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


class MockBirdTestBase(unittest.TestCase):
    """Base class which sets up a MockBird - a tiny fake BIRD
    control running on a unix socket"""

    def setUp(self):
        tmp_path = mkdtemp()
        self.socket_file = "%s/birdmock" % tmp_path

        self.mock_bird = MockBird(socket_file=self.socket_file)
        self.mock_bird.start()
        sleep(0.2)

    def tearDown(self):
        self._send_query('terminate mockserver')

    def _send_query(self, query):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_file)
        sock.send(query)

        sock.settimeout(1)
        data = sock.recv(1024000)
        sock.close()
        return str(data)


def get_test_files(cmd):
    dirname = cmd.strip().replace(' ', '_')
    dirname = os.path.join(data_dir, 'commands', dirname)
    if not os.path.isdir(dirname):
        raise ValueError("response directory '{}' does not exist".format(dirname) )
    path = dirname + "/{}"
    return map(path.format, os.listdir(dirname))


def get_expected(cmd):
    for each in get_test_files(cmd):
        fname, ext = os.path.splitext(each)
        # load based on input files so they always match up
        if ext == '.input':
            path = fname + '.expected'
            if os.path.exists(path):
                with open(path) as fobj:
                    yield json.load(fobj, object_hook=json_hook)
            else:
                yield ''


def get_responses(cmd):
    for each in get_test_files(cmd):
        fname, ext = os.path.splitext(each)
        if ext == '.input':
            with open(each) as fobj:
                yield fobj.read()


class Expected(PyBird):
    """ overrides bird instance to return generator of expected responses """
    def _send_query(self, cmd):
        return get_expected(cmd)


class PyBirdTestCase(MockBirdTestBase):
    """Test the PyBird library"""

    def setUp(self):
        super(PyBirdTestCase, self).setUp()
        self.pybird = PyBird(socket_file=self.socket_file)
        self.expected = Expected(None)

    def test_all_peer_status(self):
        """Test that we can get a list of all peers and their status.
        Testing of individual fields here is limited, that's mostly done
        in test_specific_peer_status()."""
        statuses = self.pybird.get_peer_status()
        expected = self.expected.get_peer_status().next()

        assert expected == statuses

    def test_nonexistant_peer_status(self):
        """Test that we get None if the peer did not exist."""
        status = self.pybird.get_peer_status("HAMSTER")
        assert status == None

    def test_specific_peer_status(self):
        """Test the retrieval of specific peer info, and check all the fields
        for correctness."""
        ps2_status = self.pybird.get_peer_status("PS2")
        assert ps2_status['up']

        # The test data says 14:20, so that could be today or yesterday
        now = datetime.now()
        expected_date = datetime(now.year, now.month, now.day, 14, 20)
        if now.hour < 14 or now.hour == 14 and now.minute < 20:
            expected_date = expected_date - timedelta(days=1)
        assert ps2_status['last_change'] == expected_date
        assert ps2_status['state'] == "Established"
        assert ps2_status['routes_imported'] == 24
        assert ps2_status['routes_exported'] == 23
        assert ps2_status['import_updates_received'] == 12
        assert ps2_status['import_withdraws_accepted'] == 3
        assert ps2_status['export_updates_rejected'] == 12
        assert ps2_status['router_id'] == "85.184.4.5"

        ps1_status = self.pybird.get_peer_status("PS1")
        self.assertFalse(ps1_status['up'])

        assert ps1_status['last_change'] == datetime(now.year, 6, 13)
        assert ps1_status['state'] == "Passive"

    def test_specific_peer_prefixes_announced(self):
        """Test the retrieval of prefixes announced by a peer."""
        announced_prefixes = self.pybird.get_peer_prefixes_announced("PS1")
        assert len(announced_prefixes) == 2

    def test_specific_peer_prefixes_accepted(self):
        """Test the retrieval of prefixes announced by a peer."""
        accepted_prefixes = self.pybird.get_peer_prefixes_accepted("PS1")
        assert len(accepted_prefixes) == 1
        assert accepted_prefixes[0]['origin'] == 'IGP'
        assert accepted_prefixes[0]['as_path'] == '8954 8283'
        assert accepted_prefixes[0]['community'] == '8954:220 8954:620'

    def test_specific_peer_prefixes_rejected(self):
        """Test the retrieval of prefixes rejected from a peer."""
        rejected_prefixes = self.pybird.get_peer_prefixes_rejected("PS1")
        assert len(rejected_prefixes) == 1
        assert rejected_prefixes[0]['as_path'] == '8954 20144'

    def test_specific_peer_prefixes_accepted_nonexistant_peer(self):
        """Test the handling of asking for accepted prefixes for a non-existing peer"""
        accepted_prefixes = self.pybird.get_peer_prefixes_accepted("PS99")
        assert len(accepted_prefixes) == 0

    def test_cleans_peer_name(self):
        """Test that improper characters are removed from the peer_name field
        before it is sent to BIRD."""
        ps1_status = self.pybird.get_peer_status("PS1{\"'}")
        assert not ps1_status['up']

    def test_handles_no_output(self):
        """Test that the code detects that it reached the end of the output
        without finding proper data."""
        with pytest.raises(ValueError):
            self.pybird.get_peer_status("no output")

    def test_bird_status(self):
        """Test that we can fetch the status & uptime info"""
        for expected in self.expected.get_bird_status():
            status = self.pybird.get_bird_status()
            print(json.dumps(status, cls=JSONEncoder))
            assert expected == status

        assert not self.mock_bird.unused_tests()


class MockBirdTestCase(MockBirdTestBase):
    """Run a basic test to see whether our mocked BIRD control socket
     actually works. Can save a lot of work in debugging."""

    def test_show_protocols_mocked_correctly(self):
        data = self._send_query("show protocols\n")
        assert data == """0001 BIRD 1.3.0 ready.
2002-name     proto    table    state  since       info
1002-device1  Device   master   up     14:07
 P_PS2    Pipe     master   up     14:07       => T_PS2
 PS2      BGP      T_PS2    up     14:20       Established
 P_PS1    Pipe     master   up     Jun13       => T_PS1
 PS1      BGP      T_PS1    start  Jun13       Passive
0000
"""

    def test_show_protocols_all_mocked_correctly(self):
        data = self._send_query("show protocols all\n")
        assert data == """
0001 BIRD 1.3.0 ready.
2002-name     proto    table    state  since       info
1002-device1  Device   master   up     Jun13       
1006-  Preference:     240
  Input filter:   ACCEPT
  Output filter:  REJECT
  Routes:         0 imported, 0 exported, 0 preferred
  Route change stats:     received   rejected   filtered    ignored   accepted
    Import updates:              0          0          0          0          0
    Import withdraws:            0          0        ---          0          0
    Export updates:              0          0          0        ---          0
    Export withdraws:            0        ---        ---        ---          0

1002-P_PS1    Pipe     master   up     Jun13       => T_PS1
1006-  Preference:     70
  Input filter:   <NULL>
  Output filter:  <NULL>
  Routes:         0 imported, 0 exported
  Route change stats:     received   rejected   filtered    ignored   accepted
    Import updates:              0          0          0          0          0
    Import withdraws:            0          0        ---          0          0
    Export updates:              0          0          0          0          0
    Export withdraws:            0          0        ---          0          0

1002-PS1      BGP      T_PS1    start  Jun13       Passive       
1006-  Description:    Peering AS8954 - InTouch
  Preference:     100
  Input filter:   ACCEPT
  Output filter:  ACCEPT
  Routes:         0 imported, 0 exported, 0 preferred
  Route change stats:     received   rejected   filtered    ignored   accepted
    Import updates:              0          0          0          0          0
    Import withdraws:            0          0        ---          0          0
    Export updates:              0          0          0        ---          0
    Export withdraws:            0        ---        ---        ---          0
  BGP state:          Passive

1002-P_PS2    Pipe     master   up     14:20       => T_PS2
1006-  Preference:     70
  Input filter:   <NULL>
  Output filter:  <NULL>
  Routes:         0 imported, 0 exported
  Route change stats:     received   rejected   filtered    ignored   accepted
    Import updates:              0          0          0          0          0
    Import withdraws:            0          0        ---          0          0
    Export updates:              0          0          0          0          0
    Export withdraws:            0          0        ---          0          0

1002-PS2      BGP      T_PS2    start  14:20       Established       
1006-  Description:    Peering AS8954 - InTouch
  Preference:     100
  Input filter:   ACCEPT
  Output filter:  ACCEPT
  Routes:         24 imported, 23 exported, 0 preferred
  Route change stats:     received   rejected   filtered    ignored   accepted
  Import updates:             12          0          0          0         12
  Import withdraws:            3          0        ---          0          3
  Export updates:             12         12          0        ---          0
  Export withdraws:            3        ---        ---        ---          0
    BGP state:          Established
      Session:          external route-server AS4
      Neighbor AS:      8954
      Neighbor ID:      85.184.4.5
      Neighbor address: 2001:7f8:1::a500:8954:1
      Source address:   2001:7f8:1::a519:7754:1
      Neighbor caps:    refresh AS4
      Route limit:      9/1000
      Hold timer:       112/180
      Keepalive timer:  16/60
    
0000 
"""

class MockBird(Thread):
    """Very small Mock(ing?) BIRD control socket, that can understand
    a few commands and reply with static output. Note that this is the same
    for IPv4 and IPv6. This Mock BIRD only accepts one query per connect."""

    def __init__(self, socket_file):
        Thread.__init__(self)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.remove(socket_file)
        except OSError:
            pass
        self.socket.bind(socket_file)
        self.socket.listen(1)

        self.responses = {}

    def get_response(self, cmd):
        try:
            return next(self.responses.get(cmd, iter([])))
        except StopIteration:
            self.responses[cmd] = get_responses(cmd)
            return next(self.responses[cmd])

    def unused_tests(self):
        left_tests = []
        for k, v in self.responses.items():
            try:
                next(v)
                left_tests.append(k)
            except StopIteration:
                pass

    def run(self):
        while 1:
            try:
                conn, addr = self.socket.accept()
                cmd = conn.recv(1024)

                if not cmd or cmd == 'terminate mockserver':
                    break

                conn.send(self.get_response(cmd))

            except Exception as e:
                conn.send("{}: {}".format(str(e), traceback.format_exc()))

            conn.close()
