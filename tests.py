# Copyright (c) 2011, Erik Romijn <eromijn@solidlinks.nl>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS


import socket
import os
import unittest
from tempfile import mkdtemp
from time import sleep
from datetime import datetime, timedelta, date
from threading import Thread

from pybird import PyBird


class MockBirdTestBase(unittest.TestCase):
    """Base class which sets up a MockBird - a tiny fake BIRD
    control running on a unix socket"""
    
    def setUp(self):
        tmp_path = mkdtemp()
        self.socket_file = "%s/birdmock" % tmp_path
        
        mock_bird = MockBird(socket_file=self.socket_file)
        mock_bird.start()
        sleep(0.2)

               
class PyBirdTestCase(MockBirdTestBase):
    """Test the PyBird library"""
    
    def setUp(self):
        super(PyBirdTestCase, self).setUp()
        self.pybird = PyBird(socket_file=self.socket_file)


    def test_all_peer_status(self):
        """Test that we can get a list of all peers and their status.
        Testing of individual fields here is limited, that's mostly done
        in test_specific_peer_status()."""
        statuses = self.pybird.get_peer_status()
        
        self.assertEquals(statuses[0]['name'], "PS1")
        self.assertEquals(statuses[0]['state'], "Passive")
        self.assertEquals(statuses[1]['name'], "PS2")
        self.assertEquals(statuses[1]['state'], "Established")


    def test_specific_peer_status(self):
        """Test the retrieval of specific peer info, and check all the fields
        for correctness."""
        ps2_status = self.pybird.get_peer_status("PS2")
        self.assertTrue(ps2_status['up'])
        
        # The test data says 14:20, so that could be today or yesterday
        now = datetime.now()
        expected_date = datetime(now.year, now.month, now.day, 14, 20)
        if now.hour <= 14 and now.hour < 20:
            expected_date = expected_date - timedelta(days=1)    
        self.assertEquals(ps2_status['last_change'], expected_date)
        
        self.assertEquals(ps2_status['state'], "Established")
        self.assertEquals(ps2_status['routes_imported'], 24)
        self.assertEquals(ps2_status['routes_exported'], 23)
        self.assertEquals(ps2_status['import_updates_received'], 12)
        self.assertEquals(ps2_status['import_withdraws_accepted'], 3)
        self.assertEquals(ps2_status['export_updates_rejected'], 12)
        self.assertEquals(ps2_status['router_id'], "85.184.4.5")

        ps1_status = self.pybird.get_peer_status("PS1")
        self.assertFalse(ps1_status['up'])

        expected_date = datetime(now.year, 6, 13)
        if now.month <= 6 and now.day < 13:
            result_date = result_date - timedelta(years=1)
        self.assertEquals(ps1_status['last_change'], datetime(2011, 6, 13))

        self.assertEquals(ps1_status['state'], "Passive")


    def test_cleans_peer_name(self):
        """Test that improper characters are removed from the peer_name field
        before it is sent to BIRD."""
        ps1_status = self.pybird.get_peer_status("PS1{\"'}")
        self.assertFalse(ps1_status['up'])
        
       
class MockBirdTestCase(MockBirdTestBase):
    """Run a basic test to see whether our mocked BIRD control socket
     actually works. Can save a lot of work in debugging."""
    
    def test_show_protocols_mocked_correctly(self):
        data = self._send_query("show protocols")
        self.assertEquals(data,
            "0001 BIRD 1.3.0 ready.\n"
            "2002-name     proto    table    state  since       info\n"
            "1002-device1  Device   master   up     14:07       \n"
            " P_PS2    Pipe     master   up     14:07       => T_PS2\n"
            " PS2      BGP      T_PS2    up     14:20       Established   \n"
            " P_PS1    Pipe     master   up     Jun13       => T_PS1\n"
            " PS1      BGP      T_PS1    start  Jun13       Passive\n"
            "0000"        
        )

    def test_show_protocols_all_mocked_correctly(self):
        data = self._send_query("show protocols all")
        self.assertEquals(data, """
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
        )
        
    def _send_query(self, query):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_file)
        sock.send(query)
        
        data = sock.recv(1024000)
        sock.close()
        return str(data)
        

class MockBird(Thread):
    """Very small Mock(ing?) BIRD control socket, that can understand
    a few commands and reply with static output. Note that this is the same
    for IPv4 and IPv6. This Mock BIRD only accepts one query per connect."""
    
    responses = {
        'show protocols all "HAMSTER"':
            "0001 BIRD 1.3.0 ready.\n"
            "8003 No protocols match\n",
        'show protocols':
            "0001 BIRD 1.3.0 ready.\n"
            "2002-name     proto    table    state  since       info\n"
            "1002-device1  Device   master   up     14:07       \n"
            " P_PS2    Pipe     master   up     14:07       => T_PS2\n"
            " PS2      BGP      T_PS2    up     14:20       Established   \n"
            " P_PS1    Pipe     master   up     Jun13       => T_PS1\n"
            " PS1      BGP      T_PS1    start  Jun13       Passive\n"
            "0000",
        'show protocols all': """
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
""",
        'show protocols all "ps2"': """
0001 BIRD 1.3.0 ready.
2002-name     proto    table    state  since       info
1002-PS2      BGP      T_PS2    up     14:20       Established   
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
     Hold timer:       121/180
     Keepalive timer:  20/60

0000
""",
'show protocols all "ps1"': """
0001 BIRD 1.3.0 ready.
2002-name     proto    table    state  since       info
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

0000
"""
    }
    
    def __init__(self, socket_file):
        Thread.__init__(self)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.remove(socket_file)
        except OSError:
            pass
        self.socket.bind(socket_file)
        self.socket.listen(1)
    
    
    def run(self):
        while 1:
            conn, addr = self.socket.accept()
            data = conn.recv(1024)
            if not data: break
            
            response = self.responses[data.lower()]
            conn.send(response)
            
            conn.close()    
