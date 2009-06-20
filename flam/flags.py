# encoding: utf-8
#
# Copyright (C) 2009 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Global flags registry.

Register new flags with add(). This is an alias for
optparse.OptionParser.add_option().

Call parse_args(args) to parse command-line arguments. Defaults to parsing
sys.argv[1:].

"flags" is an optparse.Values() object that will contain the parsed flag
values.

The --config=FILE flag can be used to load flag values from a file consisting
of "key = value" lines. Both empty lines and those beginning with # are ignored.

The underlying optparse.OptionParser object is exposed as "parser".
"""

from __future__ import with_statement

import optparse
import sys


__all__ = ['add', 'flags', 'parse_args', 'parser']



class FlagParser(optparse.OptionParser):
    """An OptionParser that optionally loads flags from a file."""

    def __init__(self, *args, **kwargs):
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self.add_option('--config', metavar='FILE',
                        dest='config', help='load flags from FILE.',
                        default=None)

    def parse_args(self, args=None, values=None):
        """See optparse.OptionParser.parse_args() for details."""
        options, remainder = \
            optparse.OptionParser.parse_args(self, args, values)
        if options.config:
            args = self._load_flags(options.config) + remainder
            overlay = options
            options, remainder = \
                optparse.OptionParser.parse_args(self, args)
            options.__dict__.update(overlay.__dict__)
        return options, remainder

    def set_version(self, version):
        """Set the application version."""
        self.version = version
        self._add_version_option()


    def _load_flags(self, filename):
        args = []
        with open(filename) as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                args.append('--' + key.strip() + '=' + value.strip())
            return args


parser = FlagParser()
flags = optparse.Values()
add = parser.add_option
parse_args = parser.parse_args
