import datetime

import pytest


def test_datetime(bird):
    expected = datetime.datetime(2019, 12, 10, 10, 12, 19)
    assert expected == bird._calculate_datetime("2019-12-10 10:12:19")


def test_date(bird):
    expected = datetime.datetime(2019, 12, 10)
    assert expected == bird._calculate_datetime("2019-12-10")


def test_time(bird):
    now = datetime.datetime(2019, 12, 10, 10, 12, 19)

    # before
    expected = datetime.datetime(now.year, now.month, now.day, 4, 20)
    assert expected == bird._calculate_datetime("4:20", now=now)

    # same
    expected = datetime.datetime.combine(now, datetime.time(10, 12))
    assert expected == bird._calculate_datetime("10:12", now=now)

    # after
    expected = datetime.datetime(now.year, now.month, now.day - 1, 14, 20)
    assert expected == bird._calculate_datetime("14:20", now=now)


def test_monthday(bird):
    now = datetime.datetime(2019, 12, 10)

    # before
    expected = datetime.datetime(2019, 6, 29)
    assert expected == bird._calculate_datetime("Jun29", now=now)

    # same
    expected = datetime.datetime(2018, 12, 10)
    assert expected == bird._calculate_datetime("Dec10", now=now)

    # after
    expected = datetime.datetime(2018, 12, 31)
    assert expected == bird._calculate_datetime("Dec31", now=now)


def test_year(bird):
    expected = datetime.datetime(2019, 1, 1)
    assert expected == bird._calculate_datetime("2019")


def test_fail(bird):
    with pytest.raises(ValueError):
        bird._calculate_datetime("invalid")
