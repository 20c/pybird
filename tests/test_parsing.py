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
# def make_parse_test(name):
#    def func(request, bird):
#        data_parse_routes = request.getfixturevalue(name)
#        data = bird._parse_route_data(data_parse_routes.input)
#        filedata.dump(data)
#        assert data_parse_routes.expected == data
#    return func
#
# test_parse_routes = make_parse_test('data_parse_routes')
