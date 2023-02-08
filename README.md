# pybird

[![PyPI](https://img.shields.io/pypi/v/pybird.svg?maxAge=60)](https://pypi.python.org/pypi/pybird)
[![PyPI](https://img.shields.io/pypi/pyversions/pybird.svg?maxAge=600)](https://pypi.python.org/pypi/pybird)
[![Tests](https://github.com/20c/pybird/workflows/tests/badge.svg)](https://github.com/20c/confu)
[![Codecov](https://img.shields.io/codecov/c/github/20c/pybird/main.svg?maxAge=3600)](https://codecov.io/github/20c/pybird)
[![CodeQL](https://github.com/20c/pybird/actions/workflows/codeql.yml/badge.svg)](https://github.com/20c/pybird/actions/workflows/codeql.yml)

BIRD interface handler for Python

PyBird is a Python interface to the BIRD Internet Routing Daemon's UNIX control
socket, handling the socket connections and parsing the output. It was
originally written by [Sasha Romijn](https://github.com/mxsasha), forked from
the original BitBucket repository, and relicensed with permission.


In it's current state, you can use it to query the status of specific or all
BGP peers, to query the routes received, accepted and rejected from a peer,
or the general status of BIRD (router ID, last config change)


# License

Copyright 2016 20C, LLC

Copyright 2011, Sasha Romijn <github@mxsasha.eu>

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
