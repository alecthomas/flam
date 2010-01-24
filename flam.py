# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""flam /flæm/ noun, verb, flammed, flam⋅ming. Informal. –noun 1. a deception
or trick. 2. a falsehood; lie. –verb (used with object), verb (used without
object) 3. to deceive; delude; cheat.

Flam - A minimalist Python application framework
"""


from __future__ import with_statement

import inspect
import optparse
import logging
import subprocess


# Try and determine the version of flam according to pkg_resources.
try:
    from pkg_resources import get_distribution, ResolutionError
    try:
        __version__ = get_distribution('flam').version
    except ResolutionError:
        __version__ = None # unknown
except ImportError:
    __version__ = None # unknown


__author__ = 'Alec Thomas <alec@swapoff.org>'
__all__ = ['Error', 'Flag', 'define_flag', 'flags', 'parse_args',
           'parse_args_from_file', 'init', 'run', 'log']


class Error(Exception):
    """Base Flam exception."""


class FlagParser(optparse.OptionParser):
    """An OptionParser that optionally loads flags from a file.

    >>> parser = FlagParser()
    >>> [o.get_opt_string() for o in parser.option_list]
    ['--help', '--flags', '--logging']

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
        self.add_option('--flags', metavar='FILE', type=str,
                        action='callback', help='load flags from FILE',
                        callback=self._flag_loader, default=None)
        self.add_option('--logging', type=str, action='callback',
                        callback=self._set_logging_flag,
                        help='set log level to debug, info, warning, error '
                             'or fatal [%default]',
                        metavar='LEVEL', default='warning')

    def _set_logging_flag(self, option, opt_str, value, parser):
        """Flag callback for setting the log level."""
        level = getattr(logging, value.upper(), 'WARN')
        log.setLevel(level)

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

    def parse_args_from_file(self, filename):
        """Parse command line flags from a file.

        The format of the file is one flag per line, key = value.
        """
        args = self._load_flags(filename)
        return self.parse_args(args)

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


class Flag(object):
    """A convenience property for defining and accessing flags."""

    def __init__(self, *args, **kwargs):
        self._option = define_flag(*args, **kwargs)

    def __get__(self, instance, owner):
        return getattr(flags, self._option.dest)


def parse_args(args=None):
    """Parse command-line arguments into the global :data:`flags` object.

    :param args: Command-line args, not including argv[0]. Defaults to sys.argv[1:]
    :returns: Positional arguments from :data:`args`.
    """
    options, args = flag_parser.parse_args(args)
    flags.__dict__.update(options.__dict__)
    return args


def parse_args_from_file(filename):
    """Parse command-line arguments from a file."""
    options, args = flag_parser.parse_args_from_file(filename)
    flags.__dict__.update(options.__dict__)
    return args


def define_flag(*args, **kwargs):
    """Define a flag.

    This has the same semantics as :meth:`FlagParser.add_option`.

    :param args: Positional arguments passed through to add_option.
    :param kwargs: Keyword arguments passed through to add_option.
    :returns: Return value from add_option.
    """
    return flag_parser.add_option(*args, **kwargs)


def init(args=None, usage=None, version=None):
    """Initialise the application.

    :returns: Tuple of (options, args)
    """
    log.setLevel(logging.WARN)
    if version:
        flag_parser.set_version(version)
    if usage:
        flag_parser.set_usage(usage)
    return flag_parser.parse_args(args)


def run(main, args=None, usage=None, version=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, configures
    logging, and passes any remaining arguments through to the main function.

    >>> def main(args):
    ...   print args
    >>> run(main, ['hello', 'world'])
    ['hello', 'world']

    :param main: Main function to call, with the signature main(args).
    :param args: Command-line arguments. Will default to sys.argv[1:].
    :param usage: A usage string, displayed when --help is passed. If not
                  provided, the docstring from main will be used.
    :param version: The version of the application. If provided, adds a
                    --version flag.
    """
    if usage is None:
        usage = inspect.getdoc(main)
    options, args = init(args, usage, version)
    main(args)


def execute(command, **kwargs):
    """Execute a command.

    :param command: Command to execute, as a list of args.
    :param kwargs: Extra keyword args to pass to subprocess.Popen.
    :returns: Tuple of (returncode, stdout, stderr)
    """
    kwargs.setdefault('close_fds', True)
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


log_formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    '%Y-%m-%d %H:%M:%S',
    )
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(log_formatter)

log = logging.getLogger('flam')
log.setLevel(logging.FATAL)
log.addHandler(console)

flag_parser = FlagParser()
flags = optparse.Values()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
