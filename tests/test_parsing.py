import filedata


def assert_parsed(data, parsed):
    # dump in json format for easily adding expected
    print(filedata.dumps(parsed))
    assert data.expected == parsed


def test_parse_status(bird, data_parse_status):
    data = data_parse_status
    assert_parsed(data, bird._parse_status(data.input))


def test_parse_route_data(bird, data_parse_route_data):
    data = data_parse_route_data
    assert_parsed(data, bird._parse_route_data(data.input))


# pytest doesn't load fixtures at runtime
# so we can't use def make_parse_test(name)
