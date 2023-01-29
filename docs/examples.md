# Usage example

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


# Example web server with cherrypy

Thanks to @martzuk

```py
import cherrypy
import json
from pybird import PyBird

class PybirdAPI(object):
    pybird = PyBird(socket_file='/run/bird.ctl')

    @cherrypy.expose
    def index(self):
        return "PybirdAPI"

    @cherrypy.expose
    def peer_state(self):
        peer_state = self.pybird.get_peer_status()
        return json.dumps(str(peer_state))

if __name__ == '__main__':
    cherrypy.quickstart(PybirdAPI())
```

