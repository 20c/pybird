from builtins import str
from builtins import next
from builtins import object

import logging
import re
import socket
from datetime import datetime, timedelta
from subprocess import Popen, PIPE


class PyBird(object):
    ignored_field_numbers = [0, 1, 13, 1008, 2002, 9001]

    def __init__(self, socket_file, hostname=None, user=None, password=None, config_file=None, bird_cmd=None):
        """Basic pybird setup.
        Required argument: socket_file: full path to the BIRD control socket."""
        self.socket_file = socket_file
        self.hostname = hostname
        self.user = user
        self.password = password
        self.config_file = config_file
        if not bird_cmd:
            self.bird_cmd = 'birdc'
        else:
            self.bird_cmd = bird_cmd

        self.clean_input_re = re.compile(r'\W+')
        self.field_number_re = re.compile(r'^(\d+)[ -]')
        self.routes_field_re = re.compile(r'(\d+) imported, (\d+) exported')
        self.log = logging.getLogger(__name__)

    def get_config(self):
        if not self.config_file:
            raise ValueError("config_file is not set")
        return self._read_file(self.config_file)

    def put_config(self, data):
        if not self.config_file:
            raise ValueError("config_file is not set")
        return self._write_file(data, self.config_file)

    def commit_config(self):
        return

    def check_config(self):
        query = "configure check"
        data = self._send_query(query)
        if not self.socket_file:
            return data

        err = self._parse_configure(data)
        if err:
            raise ValueError(err)

    def get_bird_status(self):
        """Get the status of the BIRD instance. Returns a dict with keys:
        - router_id (string)
        - last_reboot (datetime)
        - last_reconfiguration (datetime)"""
        query = "show status"
        data = self._send_query(query)
        if not self.socket_file:
            return data
        return self._parse_status(data)

    def _parse_status(self, data):
        line_iterator = iter(data.splitlines())
        data = {}

        for line in line_iterator:
            line = line.strip()
            (field_number, line) = self._extract_field_number(line)

            if field_number in self.ignored_field_numbers:
                continue

            if field_number == 1000:
                data['version'] = line.split(' ')[1]

            elif field_number == 1011:
                # Parse the status section, which looks like:
                # 1011-Router ID is 195.69.146.34
                # Current server time is 10-01-2012 10:24:37
                # Last reboot on 03-01-2012 12:46:40
                # Last reconfiguration on 03-01-2012 12:46:40
                data['router_id'] = self._parse_router_status_line(line)
                line = next(line_iterator)  # skip current server time
                data['last_reboot'] = self._parse_router_status_line(
                    next(line_iterator), parse_date=True)
                data['last_reconfiguration'] = self._parse_router_status_line(
                    next(line_iterator), parse_date=True)

        return data

    def _parse_configure(self, data):
        """
        returns error on error, None on success
0001 BIRD 1.4.5 ready.
0002-Reading configuration from /home/grizz/c/20c/tstbird/dev3.conf
8002 /home/grizz/c/20c/tstbird/dev3.conf, line 3: syntax error

0001 BIRD 1.4.5 ready.
0002-Reading configuration from /home/grizz/c/20c/tstbird/dev3.conf
0020 Configuration OK

0004 Reconfiguration in progress
0018 Reconfiguration confirmed
0003 Reconfigured

bogus undo:
0019 Nothing to do

        """
        error_fields = (19, 8002)
        success_fields = (3, 4, 18, 20)

        for line in data.splitlines():
            fieldno, line = self._extract_field_number(line)

            if fieldno == 2:
                if not self.config_file:
                    self.config_file = line.split(' ')[3]

            elif fieldno in error_fields:
                return line

            elif fieldno in success_fields:
                return
        raise ValueError("unable to parse configure response")

    def _parse_router_status_line(self, line, parse_date=False):
        """Parse a line like:
            Current server time is 10-01-2012 10:24:37
        optionally (if parse_date=True), parse it into a datetime"""
        data = line.strip().split(' ', 3)[-1]
        if parse_date:
            try:
                return datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
            # old versions of bird used DD-MM-YYYY
            except ValueError:
                return datetime.strptime(data, '%d-%m-%Y %H:%M:%S')
        else:
            return data

    def configure(self, soft=False, timeout=0):
        """
        birdc configure command
        """
        query = "configure check"
        data = self._send_query(query)
        if not self.socket_file:
            return data

        err = self._parse_configure(data)
        if err:
            raise ValueError(err)

    def get_routes(self, prefix=None, peer=None):
        query = "show route all"
        if prefix:
            query += " for {}".format(prefix)
        if peer:
            query += " protocol {}".format(peer)
        data = self._send_query(query)
        parsed = self._parse_route_data(data)
        return parsed

    # deprecated by get_routes_received
    def get_peer_prefixes_announced(self, peer_name):
        """Get prefixes announced by a specific peer, without applying
        filters - i.e. this includes routes which were not accepted"""
        clean_peer_name = self._clean_input(peer_name)
        query = "show route table T_%s all protocol %s" % (
            clean_peer_name, clean_peer_name)
        data = self._send_query(query)
        return self._parse_route_data(data)

    def get_routes_received(self, peer=None):
        return self.get_peer_prefixes_announced(peer)

    def get_peer_prefixes_exported(self, peer_name):
        """Get prefixes exported TO a specific peer"""
        clean_peer_name = self._clean_input(peer_name)
        query = "show route all table T_%s export %s" % (
            clean_peer_name, clean_peer_name)
        data = self._send_query(query)
        if not self.socket_file:
            return data
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

        rejected_prefixes = [
            item for item in announced_prefixes if item not in accepted_prefixes]
        rejected_routes = [item for item in announced if item[
            'prefix'] in rejected_prefixes]
        return rejected_routes

    def get_prefix_info(self, prefix, peer_name=None):
        """Get route-info for specified prefix"""
        query = "show route for %s all" % prefix
        if peer_name is not None:
            query += " protocol %s" % peer_name
        data = self._send_query(query)
        if not self.socket_file:
            return data
        return self._parse_route_data(data)

    def _parse_route_data(self, data):
        """Parse a blob like:
            0001 BIRD 1.3.3 ready.
            1007-2a02:898::/32      via 2001:7f8:1::a500:8954:1 on eth1 [PS2 12:46] * (100) [AS8283i]
            1008-   Type: BGP unicast univ
            1012-   BGP.origin: IGP
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
        while line_counter < len(lines) - 1:
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
                # Do not use this summary again on the next run
                route_summary = None
                routes.append(route_detail)

            if field_number == 8001:
                # network not in table
                return []

        return routes

    def _re_route_summary(self):
        return re.compile(
            r"(?P<prefix>[a-f0-9\.:\/]+)?\s+"
            "(?:via\s+(?P<peer>[^\s]+) on (?P<interface>[^\s]+)|(?:\w+)?)?\s*"
            "\[(?P<source>[^\s]+) (?P<time>[^\]\s]+)(?: from (?P<peer2>[^\s]+))?\]"
            )

    def _parse_route_summary(self, line):
        """Parse a line like:
            2a02:898::/32      via 2001:7f8:1::a500:8954:1 on eth1 [PS2 12:46] * (100) [AS8283i]
        """
        match = self._re_route_summary().match(line)
        if not match:
            raise ValueError("couldn't parse line '{}'".format(line))
        # Note that split acts on sections of whitespace - not just single
        # chars
        route = match.groupdict()

        # python regex doesn't allow group name reuse
        if not route['peer']:
            route['peer'] = route.pop('peer2')
        else:
            del route['peer2']
        return route

    def _parse_route_detail(self, lines):
        """Parse a blob like:
            1012-   BGP.origin: IGP
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
            parts = line.split(": ")
            if len(parts) == 2:
                (key, value) = parts
            else:
                # handle [BGP.atomic_aggr:]
                key = parts[0].strip(":")
                value = True

            if key == 'community':
                # convert (8954,220) (8954,620) to 8954:220 8954:620
                value = value.replace(",", ":").replace(
                    "(", "").replace(")", "")

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
        if not self.socket_file:
            return data

        peers = self._parse_peer_data(data=data, data_contains_detail=True)

        if not peer_name:
            return peers

        if len(peers) == 0:
            return None
        elif len(peers) > 1:
            raise ValueError(
                "Searched for a specific peer, but got multiple returned from BIRD?")
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
                    line = next(lineiterator)

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
            if ':' in elements[5]:  # newer versions include a timestamp before the state
                state = elements[6]
            else:
                state = elements[5]
            up = (state.lower() == "established")
        except IndexError:
            state = None
            up = None

        raw_datetime = elements[4]
        last_change = self._calculate_datetime(raw_datetime)

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

        route_change_fields = [
            "import updates",
            "import withdraws",
            "export updates",
            "export withdraws"
            ]
        field_map = {
            'description': 'description',
            'neighbor id': 'router_id',
            'neighbor address': 'address',
            'neighbor as': 'asn',
            }
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
                self._parse_route_stats(
                    result, key_name_base + '_received', received)
                self._parse_route_stats(
                    result, key_name_base + '_rejected', rejected)
                self._parse_route_stats(
                    result, key_name_base + '_filtered', filtered)
                self._parse_route_stats(
                    result, key_name_base + '_ignored', ignored)
                self._parse_route_stats(
                    result, key_name_base + '_accepted', accepted)

            if field.lower() in field_map.keys():
                result[field_map[field.lower()]] = value

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

    def _calculate_datetime(self, value, now=datetime.now()):
        """Turn the BIRD date format into a python datetime."""

        # Case: YYYY-MM-DD HH:MM:SS
        try:
            return datetime(*map(int, (value[:4], value[5:7], value[8:10], value[11:13], value[14:16], value[17:19])))
        except ValueError:
            pass

        # Case: YYYY-MM-DD
        try:
            return datetime(*map(int, (value[:4], value[5:7], value[8:10])))
        except ValueError:
            pass

        # Case: HH:mm or HH:mm:ss timestamp
        try:
            try:
                parsed_value = datetime.strptime(value, "%H:%M")

            except ValueError:
                parsed_value = datetime.strptime(value, "%H:%M:%S")

            result_date = datetime(
                now.year, now.month, now.day, parsed_value.hour, parsed_value.minute)

            if now.hour < parsed_value.hour or (now.hour == parsed_value.hour and now.minute < parsed_value.minute):
                result_date = result_date - timedelta(days=1)

            return result_date
        except ValueError:
            # It's a different format, keep on processing
            pass

        # Case: "Jun13" timestamp
        try:
            parsed = datetime.strptime(value, '%b%d')

            # if now is past the month, it's this year, else last year
            if now.month == parsed.month:
                # bird shows time for same day
                if now.day <= parsed.day:
                    year = now.year - 1
                else:
                    year = now.year

            elif now.month > parsed.month:
                year = now.year

            else:
                year = now.year - 1

            result_date = datetime(year, parsed.month, parsed.day)
            return result_date
        except ValueError:
            pass

        # Case: plain year
        try:
            year = int(value)
            return datetime(year, 1, 1)
        except ValueError:
            raise ValueError("Can not parse datetime: [%s]" % value)

    def _remote_cmd(self, cmd, inp=None):
        to = '{}@{}'.format(self.user, self.hostname)
        proc = Popen(['ssh', to, cmd], stdin=PIPE, stdout=PIPE)
        res, stderr = proc.communicate(input=inp)
        return res

    def _read_file(self, fname):
        if self.hostname:
            cmd = "cat " + fname
            return self._remote_cmd(cmd)
        with open(fname) as fobj:
            return fobj.read()

    def _write_file(self, data, fname):
        if self.hostname:
            cmd = "cat >" + fname
            self._remote_cmd(cmd, inp=data)
            return

        with open(fname, 'w') as fobj:
            fobj.write(data)
            return

    def _send_query(self, query):
        self.log.debug("query %s" % query)
        if self.hostname:
            return self._remote_query(query)
        return self._socket_query(query)

    def _remote_query(self, query):
        """
        mimic a direct socket connect over ssh
        """
        cmd = "{} -v -s {} '{}'".format(self.bird_cmd, self.socket_file, query)
        res = self._remote_cmd(cmd)
        res += "0000\n"
        return res

    def _socket_query(self, query):
        """Open a socket to the BIRD control socket, send the query and get
        the response.
        """
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_file)
        sock.send(query + "\n")

        data = ''
        prev_data = None

        while ((data.find("\n0000") == -1) and
               (data.find("\n8003") == -1) and
               (data.find("\n0013") == -1) and
               (data.find("\n9001") == -1) and
               (data.find("\n8001") == -1)):
            data += sock.recv(1024)
            if data == prev_data:
                self.log.debug(data)
                raise ValueError("Could not read additional data from BIRD")
            prev_data = data

        sock.close()
        return str(data)

    def _clean_input(self, inp):
        """Clean the input string of anything not plain alphanumeric chars,
        return the cleaned string."""
        return self.clean_input_re.sub('', inp).strip()
