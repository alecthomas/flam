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
    """An OptionParser that optionally loads flags from a file.

    >>> parser = FlagParser()
    >>> [o.get_opt_string() for o in parser.option_list]
    ['--help', '--config']

    Flags can be loaded from a file:

    Add a test flag:

    >>> _ = parser.add_option('--test-flag', type=str)

    It works from the command-line:

    >>> options, _ = parser.parse_args(['--test-flag=two'])
    >>> options.test_flag
    'two'

    A dummy config file with a comment:

    >>> from StringIO import StringIO
    >>> config = StringIO('''
    ...   # ignore this comment
    ...   test-flag = one two three
    ...   ''')

    Now load the flag from the file-like dummy object (a filename will also
    work):

    >>> options, _ = parser.parse_args(['--config', config])
    >>> options.test_flag
    'one two three'
    """

    def __init__(self, *args, **kwargs):
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self.add_option('--config', metavar='FILE', nargs=1,
                        action='callback', help='load flags from FILE',
                        callback=self._flag_loader, default=None)

    def set_version(self, version):
        """Set the application version.

        >>> parser = FlagParser()
        >>> parser.exit = lambda: None

        Set the version and emulate calling it from the command-line:

        >>> parser.set_version('0.1')
        >>> _ = parser.parse_args(['--version'])
        0.1
        """
        self.version = version
        self._add_version_option()


    # Internal methods
    def _flag_loader(self, option, opt_str, value, parser):
        args = self._load_flags(value)
        for arg in args:
            parser.rargs.insert(0, arg)

    def _load_flags(self, file):
        args = []
        if isinstance(file, basestring):
            file = open(file)
            close = True
        else:
            close = False
        try:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                args.append('--' + key.strip() + '=' + value.strip())
            return args
        finally:
            if close:
                file.close()


parser = FlagParser()
flags = optparse.Values()
add = parser.add_option
parse_args = parser.parse_args
