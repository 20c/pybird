# Changelog

## Unreleased
### Added
- Python 3.7, 3.8, 3.9, 3.10 support (#21)
- BIRD 2 compatibility
### Fixed
- all tests are fixed and run again (on MacOS and Ubuntu Linux)
- remote connections over SSH
### Removed
- Support for Python versions older than 3.7 (#21)

## 1.1.1
### Added
- better debug logging for actual output
### Fixed
- regex str warnings
### Changed
- get_routes returns []


## 1.1.0
### Added
- config_file, get_config()
- bird_cmd
- peer fields: description, address, asn
- route fields: interface, source, time
- status fields: version
- parsing test framework
### Fixed
- handle date format for newer bird