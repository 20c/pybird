
# pybird changelog

## [Unreleased]
### Added
- better debug logging for actual output

### Fixed
- regex str warnings

### Changed
- get_routes returns []

### Deprecated
### Removed
### Security


## [1.1.0]
### Added
- config_file, get_config()
- bird_cmd
- peer fields: description, address, asn
- route fields: interface, source, time
- status fields: version
- parsing test framework

### Fixed
- handle date format for newer bird
