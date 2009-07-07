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

Register new flags with :func:`flag`. This is an alias for
optparse.OptionParser.add_option().

The underlying optparse.OptionParser object is exposed as :data:`parser`.

Call :func:`parse_args` to parse command-line arguments. Defaults to parsing
sys.argv[1:].

:data:`flags` is an optparse.Values() object that will contain the parsed flag
values.

The --config=FILE flag can be used to load flag values from a file consisting
of "key = value" lines. Both empty lines and those beginning with # are ignored.
"""

from __future__ import with_statement

import optparse


__all__ = ['flag', 'flags', 'parse_args']



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
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('conflict_handler', 'resolve')
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self.add_option('--config', metavar='FILE', type=str,
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

def parse_args(args=None):
    """Parse command-line arguments into the global :data:`flags` object.

    :param args: Command-line args, not including argv[0]. Defaults to sys.argv[1:]
    :returns: Positional arguments from :data:`args`.
    """
    options, args = parser.parse_args(args)
    flags.__dict__.update(options.__dict__)
    return args


def flag(*args, **kwargs):
    """Define a flag.

    This has the same semantics as :meth:`FlagParser.add_option`.

    :param args: Positional arguments passed through to add_option.
    :param kwargs: Keyword arguments passed through to add_option.
    :returns: Return value from add_option.
    """
    return parser.add_option(*args, **kwargs)


parser = FlagParser()
flags = optparse.Values()
