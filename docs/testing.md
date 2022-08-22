# Test suite

There is a series of tests in ``tests/``. This includes a ``MockBird``: a mocked BIRD instance, with fixed but real responses, that listens on a real UNIX socket. This means the tests do not only test parsing, but also socket interaction.

## Parsing tests
To add tests for parsing, simply put `$testname` `.input` and `.expected` in the directory named after the function name. `$testname.expected` should contain JSON encoded data.
