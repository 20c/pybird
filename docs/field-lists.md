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
