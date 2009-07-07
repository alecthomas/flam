# encoding: utf-8
#
# Copyright (C) 2009 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

from __future__ import with_statement

import optparse
import os
import sys
from tempfile import NamedTemporaryFile

from flam import flags


def setup():
    """Reset flag module."""
    flags.parser = flags.FlagParser()
    flags.flags = optparse.Values()


def _parser_options(parser):
    return [o.get_opt_string() for o in parser.option_list]


def test_config_option():
    parser = flags.FlagParser()
    assert _parser_options(parser) == ['--help', '--config']


def test_config_from_file():
    """Test basic config loading from a file."""
    parser = flags.FlagParser()
    parser.add_option('--test', type=int, default=9)
    with NamedTemporaryFile() as fd:
        print >> fd, """
        # this is a comment
        test = 99
        """
        fd.flush()
        options, _ = parser.parse_args(['--config', fd.name])
        assert options.test == 99


def test_global_flag_add():
    flags.flag('--test', type=int, default=9)
    assert '--test' in _parser_options(flags.parser)


def test_set_version_adds_flag():
    parser = flags.FlagParser()
    parser.set_version('0.1')
    assert _parser_options(parser) == ['--help', '--config', '--version']
    assert parser.version == '0.1'
