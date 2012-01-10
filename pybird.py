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

import re
import socket
import select
import itertools
from datetime import datetime, timedelta, date

class PyBird(object):
    ignored_field_numbers = [0001, 2002, 0000, 1008, 0013]
    
    def __init__(self, socket_file):
        """Basic pybird setup.
        Required argument: socket_file: full path to the BIRD control socket."""
        self.socket_file = socket_file
        self.clean_input_re = re.compile('\W+')
        self.field_number_re = re.compile('^(\d+)[ -]')
        self.routes_field_re = re.compile('(\d+) imported, (\d+) exported')


    def get_bird_status(self):
        """Get the status of the BIRD instance. Returns a dict with keys:
        - router_id (string)
        - last_reboot (datetime)
        - last_reconfiguration (datetime)"""
        query = "show status"
        data = self._send_query(query)

        line_iterator = iter(data.splitlines())
        data = {}
        
        for line in line_iterator:
            line = line.strip()
            (field_number, line) = self._extract_field_number(line)

            if field_number in self.ignored_field_numbers:
                continue
            
            if field_number == 1011:
                # Parse the status section, which looks like:
                #1011-Router ID is 195.69.146.34
                # Current server time is 10-01-2012 10:24:37
                # Last reboot on 03-01-2012 12:46:40
                # Last reconfiguration on 03-01-2012 12:46:40
                data['router_id'] = self._parse_router_status_line(line)
                line = line_iterator.next() # skip current server time
                data['last_reboot'] = self._parse_router_status_line(line_iterator.next(), parse_date=True)
                data['last_reconfiguration'] = self._parse_router_status_line(line_iterator.next(), parse_date=True)
                                            
        return data
        
    def _parse_router_status_line(self, line, parse_date=False):
        """Parse a line like:
            Current server time is 10-01-2012 10:24:37
        optionally (if parse_date=True), parse it into a datetime"""
        data = line.strip().split(' ', 3)[-1]
        if parse_date:
            return datetime.strptime(data, '%d-%m-%Y %H:%M:%S')
        else:
            return data
        

    def get_peer_prefixes_announced(self, peer_name):
        """Get prefixes announced by a specific peer, without applying
        filters - i.e. this includes routes which were not accepted"""
        clean_peer_name = self._clean_input(peer_name)
        query = "show route table T_%s all protocol %s" % (clean_peer_name, clean_peer_name)
        data = self._send_query(query)
        return self._parse_route_data(data)


    def get_peer_prefixes_accepted(self, peer_name):
        """Get prefixes announced by a specific peer, which were also
        accepted by the filters"""
        query = "show route all protocol %s" % self._clean_input(peer_name)
        data = self._send_query(query)
        return self._parse_route_data(data)


    def get_peer_prefixes_rejected(self, peer_name):
        announced = self.get_peer_prefixes_announced(peer_name)
        accepted = self.get_peer_prefixes_accepted(peer_name)
        
        announced_prefixes = [i['prefix'] for i in announced]
        accepted_prefixes = [i['prefix'] for i in accepted]
        
        rejected_prefixes = [item for item in announced_prefixes if not item in accepted_prefixes]
        rejected_routes = [item for item in announced if item['prefix'] in rejected_prefixes]
        return rejected_routes


    def _parse_route_data(self, data):
        """Parse a blob like:
            0001 BIRD 1.3.3 ready.
            1007-2a02:898::/32      via 2001:7f8:1::a500:8954:1 on eth1 [PS2 12:46] * (100) [AS8283i]
            1008-	Type: BGP unicast univ
            1012-	BGP.origin: IGP
             	BGP.as_path: 8954 8283
             	BGP.next_hop: 2001:7f8:1::a500:8954:1 fe80::21f:caff:fe16:e02
             	BGP.local_pref: 100
             	BGP.community: (8954,620)
            [....]
            0000
     	"""
        lines = data.splitlines()
        routes = []
        
        route_summary = None
        
        line_counter = -1
        while line_counter < len(lines)-1:
            line_counter += 1
            line = lines[line_counter].strip()
            (field_number, line) = self._extract_field_number(line)

            if field_number in self.ignored_field_numbers:
                continue
            
            if field_number == 1007:
                route_summary = self._parse_route_summary(line)
                    
            route_detail = None
            if field_number == 1012:
                if not route_summary:
                    # This is not detail of a BGP route
                    continue
                
                # A route detail spans multiple lines, read them all     
                route_detail_raw = []
                while 'BGP.' in line:
                    route_detail_raw.append(line)
                    line_counter += 1
                    line = lines[line_counter]
                # this loop will have walked a bit too far, correct it
                line_counter -= 1
                
                route_detail = self._parse_route_detail(route_detail_raw)
            
                # Save the summary+detail info in our result
                route_detail.update(route_summary)
                routes.append(route_detail)
                # Do not use this summary again on the next run
                route_summary = None
                
        return routes
        
        
    def _parse_route_summary(self, line):
        """Parse a line like:
            2a02:898::/32      via 2001:7f8:1::a500:8954:1 on eth1 [PS2 12:46] * (100) [AS8283i]
        """
        # Note that split acts on sections of whitespace - not just single chars
        elements = line.strip().split()
        return {'prefix': elements[0], 'peer': elements[2]}

        
    def _parse_route_detail(self, lines):
        """Parse a blob like:
            1012-	BGP.origin: IGP
             	BGP.as_path: 8954 8283
             	BGP.next_hop: 2001:7f8:1::a500:8954:1 fe80::21f:caff:fe16:e02
             	BGP.local_pref: 100
             	BGP.community: (8954,620)
     	"""
     	attributes = {}
     	
     	for line in lines:
     	    line = line.strip()
     	    # remove 'BGP.'
     	    line = line[4:]
     	    
     	    (key, value) = line.split(": ")
     	    attributes[key] = value
     	    
     	return attributes
    
        
    def get_peer_status(self, peer_name=None):
        """Get the status of all peers or a specific peer.

        Optional argument: peer_name: case-sensitive full name of a peer,
        as configured in BIRD.
        
        If no argument is given, returns a list of peers - each peer represented
        by a dict with fields. See README for a full list.
        
        If a peer_name argument is given, returns a single peer, represented
        as a dict. If the peer is not found, returns None.
        """
        
        if peer_name:
            query = 'show protocols all "%s"' % self._clean_input(peer_name)
        else:
            query = 'show protocols all'
            
        data = self._send_query(query)
        peers = self._parse_peer_data(data=data, data_contains_detail=True)
        
        if not peer_name:
            return peers
        
        if len(peers) == 0:
            return None
        elif len(peers) > 1:
            raise ValueError("Searched for a specific peer, but got multiple returned from BIRD?")
        else:
            return peers[0]


    def _parse_peer_data(self, data, data_contains_detail):
        """Parse the data from BIRD to find peer information."""
        lineiterator = iter(data.splitlines())
        peers = []
        
        peer_summary = None
        
        for line in lineiterator:
            line = line.strip()
            (field_number, line) = self._extract_field_number(line)

            if field_number in self.ignored_field_numbers:
                continue
            
            if field_number == 1002:
                peer_summary = self._parse_peer_summary(line)
                if peer_summary['protocol'] != 'BGP':
                    peer_summary = None
                    continue
                    
            # If there is no detail section to be expected,
            # we are done.
            if not data_contains_detail:
                peers.append_peer_summary()
                continue
                    
            peer_detail = None
            if field_number == 1006:
                if not peer_summary:
                    # This is not detail of a BGP peer
                    continue
                
                # A peer summary spans multiple lines, read them all
                peer_detail_raw = []
                while line.strip() != "":
                    peer_detail_raw.append(line)
                    line = lineiterator.next()
                    
                peer_detail = self._parse_peer_detail(peer_detail_raw)
            
                # Save the summary+detail info in our result
                peer_detail.update(peer_summary)
                peers.append(peer_detail)
                # Do not use this summary again on the next run
                peer_summary = None
                
        return peers
        
            
    def _parse_peer_summary(self, line):
        """Parse the summary of a peer line, like:
        PS1      BGP      T_PS1    start  Jun13       Passive
        
        Returns a dict with the fields:
            name, protocol, last_change, state, up
            ("PS1", "BGP", "Jun13", "Passive", False)
        
        """
        elements = line.split()
        
        try:
            state = elements[5]
            up = (state.lower() == "established")
        except IndexError:
            state = None
            up = None
        
        last_change = self._calculate_datetime(elements[4])
        
        return {
            'name': elements[0],
            'protocol': elements[1],
            'last_change': last_change,
            'state': state,
            'up': up,
        }
        
    
    def _parse_peer_detail(self, peer_detail_raw):
        """Parse the detailed peer information from BIRD, like:
        
        1006-  Description:    Peering AS8954 - InTouch
          Preference:     100
          Input filter:   ACCEPT
          Output filter:  ACCEPT
          Routes:         24 imported, 23 exported, 0 preferred
          Route change stats:     received   rejected   filtered    ignored   accepted
            Import updates:             50          3          19         0          0
            Import withdraws:            0          0        ---          0          0
            Export updates:              0          0          0        ---          0
            Export withdraws:            0        ---        ---        ---          0
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

        peer_detail_raw must be an array, where each element is a line of BIRD output.

        Returns a dict with the fields, if the peering is up:
            routes_imported, routes_exported, router_id
            and all combinations of:
            [import,export]_[updates,withdraws]_[received,rejected,filtered,ignored,accepted]
            wfor which the value above is not "---"
            
        """
        result = {}
        
        route_change_fields = ["import updates", "import withdraws", "export updates", "export withdraws"]
        
        lineiterator = iter(peer_detail_raw)

        for line in lineiterator:
            line = line.strip()
            (field, value) = line.split(":", 1)
            value = value.strip()
            
            if field.lower() == "routes":
                routes = self.routes_field_re.findall(value)[0]
                result['routes_imported'] = int(routes[0])
                result['routes_exported'] = int(routes[1])
                
            if field.lower() in route_change_fields:
                (received, rejected, filtered, ignored, accepted) = value.split()
                key_name_base = field.lower().replace(' ', '_')
                self._parse_route_stats(result, key_name_base+'_received', received)
                self._parse_route_stats(result, key_name_base+'_rejected', rejected)
                self._parse_route_stats(result, key_name_base+'_filtered', filtered)
                self._parse_route_stats(result, key_name_base+'_ignored', ignored)
                self._parse_route_stats(result, key_name_base+'_accepted', accepted)
                
            if field.lower() == "neighbor id":
                result['router_id'] = value
            
        return result
    
    
    def _parse_route_stats(self, result_dict, key_name, value):
        if value.strip() == "---":
            return        
        result_dict[key_name] = int(value)
        
    
    def _extract_field_number(self, line):
        """Parse the field type number from a line.
        Line must start with a number, followed by a dash or space.

        Returns a tuple of (field_number, cleaned_line), where field_number
        is None if no number was found, and cleaned_line is the line without
        the field number, if applicable.
        """
        matches = self.field_number_re.findall(line)

        if len(matches):
            field_number = int(matches[0])
            cleaned_line = self.field_number_re.sub('', line).strip('-')
            return (field_number, cleaned_line)
        else:
            return (None, line)


    def _calculate_datetime(self, value):
        """Turn the BIRD date format into a python datetime."""
        now = datetime.now()
        
        # Case 1: HH:mm timestamp
        try:
            parsed_value = datetime.strptime(value, "%H:%M")
            result_date = datetime(now.year, now.month, now.day, parsed_value.hour, parsed_value.minute)
            
            if now.hour < parsed_value.hour or (now.hour == parsed_value.hour and now.minute < parsed_value.minute):
                result_date = result_date - timedelta(days=1)
            
            return result_date
            
        except ValueError:
            # It's a different format, keep on processing
            pass
        
        # Case 2: "Jun13" timestamp
        try:
            # Run this for a (fake) leap year, or 29 feb will get us in trouble
            parsed_value = datetime.strptime("1996 "+value, "%Y %b%d")
            result_date = datetime(now.year, parsed_value.month, parsed_value.day)

            if now.month <= parsed_value.month and now.day < parsed_value.day:
                # This may have an off-by-one-day issue with leap years, but that's not important
                result_date = result_date - timedelta(days=365)
            
            return result_date
        except ValueError:
            pass
            
        # Must be a plain year
        try:
            year = int(value)
            return datetime(year, 1, 1)
        except ValueError:
            raise ValueError("Can not parse datetime: [%s]" % value)
        
        
    def _send_query(self, query):
        """Open a socket to the BIRD control socket, send the query and get
        the response.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_file)
        sock.send(query+"\n")

        data = ''
        prev_data = None

        while (data.find("\n0000") == -1) and (data.find("\n8003") == -1) and (data.find("\n0013") == -1):
            data += sock.recv(1024)
            if data == prev_data:
                raise ValueError("Could not read additional data from BIRD")
            prev_data = data
            
        sock.close()
        return str(data)
        
        
    def _clean_input(self, input):
        """Clean the input string of anything not plain alphanumeric chars,
        return the cleaned string."""
        return self.clean_input_re.sub('', input).strip()

