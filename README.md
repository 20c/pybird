
# pybird

[![PyPI](https://img.shields.io/pypi/v/pybird.svg?maxAge=3600)](https://pypi.python.org/pypi/pybird)
[![Travis CI](https://img.shields.io/travis/20c/pybird.svg?maxAge=3600)](https://travis-ci.org/20c/pybird)
[![Code Health](https://landscape.io/github/20c/pybird/master/landscape.svg?style=flat)](https://landscape.io/github/20c/pybird/master)
[![Codecov](https://img.shields.io/codecov/c/github/20c/pybird/master.svg?maxAge=3600)](https://codecov.io/github/20c/pybird)
[![Requires.io](https://img.shields.io/requires/github/20c/pybird.svg?maxAge=3600)](https://requires.io/github/20c/pybird/requirements)

BIRD interface handler for Python

PyBird is a Python interface to the BIRD Internet Routing Daemon's UNIX control
socket, handling the socket connections and parsing the output. It was
originally written by [Erik Romijn](https://github.com/erikr), forked from
<https://bitbucket.org/erikr/pybird>, and relicensed with permission.


In it's current state, you can use it to query the status of specific or all
BGP peers, to query the routes received, accepted and rejected from a peer,
or the general status of BIRD (router ID, last config change)


### Usage example

```py
    >>> from pybird import PyBird
    >>> pybird = PyBird(socket_file='/var/run/bird.ctl')
    >>> peer_state = pybird.get_peer_status('KPN')
    >>> peer_state['up']
    True
    >>> peer_state['import_updates_received']
    4214
    >>> peer_state['last_change']
    datetime.datetime(2011, 6, 19, 19, 57, 0, 0)

    >>> rejected = pybird.get_peer_prefixes_rejected('KPN')
    >>> rejected[0]['as_path']
    '23456 65592'
    
    >>> status = pybird.get_status()
    >>> status['last_reconfiguration_time']
    datetime.datetime(2012, 1, 3, 12, 46, 40)
    >>> status['router_id']
    "192.168.0.1"
```

You can also call ``get_peer_status()`` without a peer name, to get an array
with all the BGP peers.


### Full field list for peers

All fields that are decoded, if present:

- ``name``: Name as configured in BIRD
- ``protocol``: Currently always "BGP"
- ``last_change``: Last state change as a ``datetime.datetime`` object
- ``state``: String of the peer status, e.g. "Established" or "Passive"
- ``up``: Boolean, True if session is Established
- ``routes_imported``: Number of imported routes
- ``routes_exported``: Number of exported routes
- ``router_id``: BGP router id

And all combinations of:
``[import,export]_[updates,withdraws]_[received,rejected,filtered,ignored,accepted]``
which BIRD supports.


### Full field list for routes

All fields that are decoded, if present:

- ``origin``: BGP origin, e.g. "IGP"
- ``as_path``: AS path as string
- ``next_hop``: BGP next hop
- ``local_pref``: Local pref, e.g. '100'
- ``community``: Communities in string format, e.g. '8954:220 8954:620'

And any other BGP attribute fields BIRD has found.


### Full field list for BIRD status

- ``router_id``: BGP Router ID as string
- ``last_reboot``: Last BIRD restart time as datetime
- ``last_reconfiguration``: Last BIRD config change as datetime
- ``version``: BIRD version as string


### Test suite

There is a series of tests in ``tests.py``. This includes a ``MockBird``: a
mocked BIRD instance, with fixed but real responses, that listens on a real
UNIX socket. This means the tests do not only test parsing, but also socket
interaction.

#### Parsing tests

To automatically add parsing tests, just add `$test_name` with extensions
.input and .expected to the correct parsing directory under
<tests/data/parse/>.


### License

Copyright 2016 20C, LLC

Copyright 2011, Erik Romijn <eromijn@solidlinks.nl>

All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this softare except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
