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
import sys


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
__all__ = [
    'Error', 'Flag', 'define_flag', 'flags', 'parse_args',
    'parse_flags_from_file', 'write_flags_to_file', 'init', 'run', 'command',
    'log', 'fatal', 'dispatch_command', 'command',
]


class Error(Exception):
    """Base Flam exception."""


class CommandError(Error):
    """An error in the top-level command parsing code."""


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
        self.set_usage('%prog [<flags>] <command> ...')
        self.add_option('--flags', metavar='FILE', type=str,
                        action='callback', help='load flags from FILE',
                        callback=self._flag_loader, default=None)
        self.add_option('--logging', type=str, action='callback',
                        callback=self._set_logging_flag,
                        help='set log level to debug, info, warning, error '
                             'or fatal [%default]',
                        metavar='LEVEL', default='warning')
        self._commands = {}

    def _set_logging_flag(self, option, opt_str, value, parser):
        """Flag callback for setting the log level."""
        level = getattr(logging, value.upper(), 'ERROR')
        log.setLevel(level)

    def set_epilog(self, epilog):
        """Set help epilog text."""
        self.epilog = epilog

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

    def register_command(self, function):
        """Register a command."""
        commands = tuple(function.__name__.split('_'))
        self._commands[commands] = function
        return function

    def format_help(self, formatter=None):
        if formatter is None:
            formatter = self.formatter
        result = []
        if self.usage:
            result.append(self.get_usage() + '\n')
        if self.description:
            result.append(self.format_description(formatter) + '\n')
        if self._commands:
            result.append(self.format_commands(formatter))
        result.append(self.format_option_help(formatter))
        result.append(self.format_epilog(formatter))
        return ''.join(result)

    def format_commands(self, formatter=None):
        """Format commands for help."""
        result = []
        result.append('Commands:')
        for command_args, command in sorted(self._commands.iteritems()):
            help = inspect.getdoc(command)
            argspec = inspect.getargspec(command)
            defaults_len = len(argspec.defaults or [])
            args = ['<%s>' % arg for arg in argspec.args]
            if defaults_len:
                arg_spec = ' '.join(args[:-defaults_len])
                optional_spec = ' '.join(args[-defaults_len:])
            else:
                arg_spec = ' '.join(args)
                optional_spec = ''
            if argspec.varargs:
                optional_spec += ' <' + argspec.varargs + '> ...'
            if optional_spec:
                optional_spec = '[' + optional_spec.strip() + ']'
            command_args_help = ' '.join(command_args)
            result.append('  ' + ' '.join([command_args_help, arg_spec,
                                          optional_spec]))
            if help:
                result.extend('    ' + line for line in help.splitlines())
            result.append('')
        result.append('')
        return '\n'.join(result)

    def dispatch_command(self, args):
        """Dispatch to command functions registered with @command.

        :param args: Command-line argument list.
        :returns: Tuple of (function, args)
        """
        # If only "help" is registered, assume we don't want commands
        if len(self._commands) == 1:
            return

        if not args:
            raise CommandError('no command provided, try "help"')

        # Find longest matching command
        matched_command = None
        longest_match = 0
        for command_args, command in sorted(self._commands.iteritems()):
            command_length = len(command_args)
            if args[:command_length] == list(command_args) and \
                    command_length > longest_match:
                matched_command = command
                longest_match = command_length

        if not matched_command:
            raise CommandError('no command found matching %r.' % ' '.join(args))

        # Attempt to move arguments into command_args and command_kwargs from
        # args.
        command_description = ' '.join(args[:longest_match])
        args = args[longest_match:]
        command_args = []

        argspec = inspect.getargspec(matched_command)

        if argspec.keywords:
            raise CommandError('keyword wildcards are not supported')

        # Move positional arguments required by function spec
        if argspec.args:
            func_arg_length = len(argspec.args)
            if len(args) + len(argspec.defaults or []) < func_arg_length:
                raise CommandError('insufficient arguments to %r'
                                % command_description)
            command_args.extend(args[:func_arg_length])
            args = args[func_arg_length:]

        if argspec.varargs:
            command_args.extend(args)
            args = []

        if args:
            raise CommandError('too many arguments provided to %r' %
                            command_description)

        return matched_command(*command_args)


    def parse_flags_from_file(self, filename):
        """Parse command line flags from a file.

        The format of the file is one flag per line, key = value.
        """
        args = self._load_flags(filename)
        return self.parse_args(args)

    def write_flags_to_file(self, filename, flags):
        with open(filename, 'wt') as fd:
            for key, value in flags.__dict__.iteritems():
                fd.write('%s = %s\n' % (key, value))

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


def parse_flags_from_file(filename):
    """Parse command-line arguments from a file."""
    options, args = flag_parser.parse_flags_from_file(filename)
    flags.__dict__.update(options.__dict__)
    return args


def write_flags_to_file(filename):
    """Write global flags to a file."""
    flag_parser.write_flags_to_file(filename, flags)


def define_flag(*args, **kwargs):
    """Define a flag.

    This has the same semantics as :meth:`FlagParser.add_option`.

    :param args: Positional arguments passed through to add_option.
    :param kwargs: Keyword arguments passed through to add_option.
    :returns: Return value from add_option.
    """
    return flag_parser.add_option(*args, **kwargs)


def dispatch_command(args):
    """Dispatch to a command registered with @command."""
    flag_parser.dispatch_command(args)


def init(args=None, usage=None, version=None, epilog=None):
    """Initialise the application.

    :returns: Tuple of (options, args)
    """
    if version:
        flag_parser.set_version(version)
    if usage:
        flag_parser.set_usage(usage)
    if epilog:
        flag_parser.set_epilog(epilog)
    return parse_args(args)


def run(main=None, args=None, usage=None, version=None, epilog=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, configures
    logging, and passes any remaining arguments through to the main function.

    >>> def main(args):
    ...   print args
    >>> run(main, ['hello', 'world'])
    ['hello', 'world']

    :param main: Main function to call, with the signature main(args). After
                 execution of main(), any commands registered with @command
                 will be dispatched. This allows main() to be used as
                 initialisation code.
    :param args: Command-line arguments. Will default to sys.argv[1:].
    :param usage: A usage string, displayed when --help is passed. If not
                  provided, the docstring from main will be used.
    :param version: The version of the application. If provided, adds a
                    --version flag.
    :raises Error: If main is not provided and no commands are defined with
                   :func:`command`.
    """
    if usage is None:
        usage = inspect.getdoc(main)
    args = init(args, usage, version, epilog)
    if main:
        main(args)
    try:
        dispatch_command(args)
    except CommandError, e:
        fatal(e)


def fatal(*args):
    """Print an error and terminate with a non-zero status."""
    print >> sys.stderr, 'fatal:', ' '.join(map(str, args))
    sys.exit(1)


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


# Command dispatching
log_formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    '%Y-%m-%d %H:%M:%S',
    )
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(log_formatter)

log = logging.getLogger('flam')
log.setLevel(logging.ERROR)
log.addHandler(console)

flag_parser = FlagParser()
flags = optparse.Values()
command = flag_parser.register_command


@command
def help(command=None):
    """Display help on available commands."""
    sys.stdout.write(flag_parser.format_help())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
