# encoding: utf-8
#
# Copyright (C) 2009 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>


import datetime
import logging

from flam import util
from flam.test import patch


@patch('time.sleep')
def test_random_sleep(mock_sleep):
    for i in range(10000):
        util.random_sleep(1, 10)
    assert mock_sleep.call_count == 10000
    for args, kwargs in mock_sleep.call_args_list:
        assert 1.0 < args[0] <= 10.0


def test_get_last_traceback():
    try:
        raise ValueError('This is an error')
    except ValueError:
        traceback = util.get_last_traceback()
        lines = traceback.splitlines()
        assert lines[0] == 'Traceback (most recent call last):'
        assert lines[-2].strip() == 'raise ValueError(\'This is an error\')'
        assert lines[-1] == 'ValueError: This is an error'


def test_to_boolean_true_values():
    truth_values = ('yes', 'true', 'on', 'aye', '1', 1, True)
    for truth in truth_values:
        assert util.to_boolean(truth) is True


def test_to_boolean_false_values():
    false_values = ('no', 'false', 'off', '0', 0, False, 'not', 'moo')
    for lie in false_values:
        assert util.to_boolean(lie) is False


def test_to_list_basic():
    assert util.to_list('a,b,c,d') == ['a', 'b', 'c', 'd']


def test_to_list_custom_sep():
    assert util.to_list('a:b:c', sep=':') == ['a', 'b', 'c']


def test_to_list_empty_element():
    assert util.to_list('a,,b,c') == ['a', 'b', 'c']


def test_to_list_keep_empty_element():
    assert util.to_list('a,,b,c', keep_empty=True) == ['a', '', 'b', 'c']


def test_to_list_with_false_value():
    assert util.to_list(False) == []
    assert util.to_list(None) == []


def test_to_list_from_iterables():
    assert util.to_list([1, 2]) == [1, 2]
    assert util.to_list((i for i in (1, 2, 3))) == [1, 2, 3]


def test_from_iso_time():
    assert util.from_iso_time('2009-01-29T22:33:44Z') == \
           datetime.datetime(2009, 01, 29, 22, 33, 44)


def test_to_iso_time():
    date = datetime.datetime(2009, 01, 29, 22, 33, 44)
    assert util.to_iso_time(date) == '2009-01-29T22:33:44Z'


def test_cached_property():
    class Test(object):
        def __init__(self):
            self._value = 0

        @util.cached_property
        def value(self):
            self._value += 1
            return self._value

    test = Test()
    assert test.value == 1
    assert test.value == 1
    assert isinstance(Test.value, util.cached_property)
