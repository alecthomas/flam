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
from tempfile import NamedTemporaryFile

from flam import flags


def setup():
    # XXX Reset flag module state.
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
    flags.define_flag('--test', type=int, default=9)
    assert '--test' in _parser_options(flags.parser)


def test_global_flag_parse():
    flags.define_flag('--test', type=int, default=9)
    options, args = flags.parser.parse_args(['moo', '--test=1', 'bar'])
    assert options.__dict__ == {'test': 1, 'config': None}
    assert args == ['moo', 'bar']


def test_global_flags_parse_args():
    flags.define_flag('--test', type=int, default=9)
    args = flags.parse_args(['moo', '--test=1', 'bar'])
    assert args == ['moo', 'bar'], args
    assert flags.flags.__dict__ == {'test': 1, 'config': None}


def test_set_version_adds_flag():
    parser = flags.FlagParser()
    parser.set_version('0.1')
    assert _parser_options(parser) == ['--help', '--config', '--version']
    assert parser.version == '0.1'
