# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""flam /flæm/ noun, verb, flammed, flam⋅ming. Informal. –noun 1. a
deception or trick. 2. a falsehood; lie. –verb (used with object), verb (used
without object) 3. to deceive; delude; cheat.

Flam - A minimalist Python application framework
"""


import inspect
import optparse
import os
import logging
import subprocess
import sys
import threading
import weakref
from Queue import Queue


# Try and determine the version of flam according to pkg_resources.
try:
    from pkg_resources import get_distribution, ResolutionError
    try:
        __version__ = get_distribution('flam').version
    except ResolutionError:
        __version__ = None  # unknown
except ImportError:
    __version__ = None  # unknown


__author__ = 'Alec Thomas <alec@swapoff.org>'
__all__ = [
    'Error', 'Flag', 'ThreadPool', 'define_flag', 'flags', 'parse_args',
    'parse_flags_from_file', 'write_flags_to_file', 'init', 'run', 'command',
    'fatal', 'dispatch_command', 'command', 'cached_property', 'WeakList',
]


class Error(Exception):
    """Base Flam exception."""


class CommandError(Error):
    """An error in the top-level command parsing code."""


def _check_list_option(option, opt, value):
    if isinstance(value, list):
        return value
    return [i.strip() for i in value.split(',')]


class FlagOption(optparse.Option):
    """Custom FlagParser option types.

    Currently supports only list.
    """
    TYPES = optparse.Option.TYPES + ("list",)
    TYPE_CHECKER = optparse.Option.TYPE_CHECKER.copy()
    TYPE_CHECKER['list'] = _check_list_option

    def __init__(self, *args, **kwargs):
        self.required = kwargs.pop('required', False)
        optparse.Option.__init__(self, *args, **kwargs)


class FlagParser(optparse.OptionParser):
    """An OptionParser that supports command and can load flags from files.

    >>> parser = FlagParser()
    >>> [o.get_opt_string() for o in parser.option_list]
    ['--help', '--flags']

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
        kwargs.setdefault('option_class', FlagOption)
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self.set_usage('%prog [<flags>] <command> ...')
        self.add_option('--flags', metavar='FILE', type=str,
                        action='callback', help='load flags from FILE',
                        callback=self._flag_loader, default=None)
        self._commands = {}

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
        if len(self._commands) > 1:
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
                optional_spec = args[-defaults_len:]
            else:
                arg_spec = ' '.join(args)
                optional_spec = []
            if argspec.varargs:
                optional_spec.extend(['<' + argspec.varargs + '>', '...'])
            optional_spec = ' '.join(optional_spec)
            if optional_spec:
                optional_spec = '[' + optional_spec.strip() + ']'
            command_args_help = ' '.join(command_args)
            result.append(' '.join(filter(None, [command_args_help, arg_spec,
                                                 optional_spec])))
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
            raise CommandError('command not provided, try "help"')

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
            raise CommandError('no command found matching %r, try "help"'
                               % ' '.join(map(str, args)))

        # Attempt to move arguments into command_args and command_kwargs from
        # args.
        command_description = ' '.join(map(str, args[:longest_match]))
        args = args[longest_match:]
        command_args = []

        argspec = inspect.getargspec(matched_command)

        if argspec.keywords:
            raise ValueError('keyword wildcards are not supported')

        # Move positional arguments required by function spec
        if argspec.args:
            func_arg_length = len(argspec.args)
            if len(args) + len(argspec.defaults or []) < func_arg_length:
                raise CommandError('insufficient arguments to %r, try "help"'
                                % command_description)
            command_args.extend(args[:func_arg_length])
            args = args[func_arg_length:]

        if argspec.varargs:
            command_args.extend(args)
            args = []

        if args:
            raise CommandError(
                'too many arguments provided to %r, try "help"' %
                command_description)

        return matched_command(*command_args)

    def parse_flags_from_file(self, filename, values=None):
        """Parse command line flags from a file.

        The format of the file is one flag per line, key = value.

        :param values: Values object to update.
        """
        args = self._load_flags(filename)
        return self.parse_args(args, values=values)

    def write_flags_to_file(self, filename, flags):
        with open(filename, 'wt') as fd:
            for key, value in vars(flags).iteritems():
                # TODO(alec) This is not reliable as the key uses the value of
                # "dest", while we use the flag name.
                option = self.get_option('--' + key)
                if value != option.default:
                    value = self._serialise_option_value(value)
                    fd.write('%s = %s\n' % (key, value))

    def _serialise_option_value(self, value):
        # TODO(alec) This is kinda ugly. It'd be better if the
        # Option object itself supported serialisation.
        if isinstance(value, (list, tuple)):
            return ','.join(map(str, value))
        elif value is None:
            return ''
        return str(value)

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
    """A convenience property for defining and accessing flags.

    This is a thin wrapper around :meth:`optparse.OptionParser.add_option`.
    Refer to optparse documentation for details.
    """

    def __init__(self, *args, **kwargs):
        """Define a new flag property.

        :param args: Positional arguments to pass to :func:`define_flag`.
        :param kwargs: Keyword arguments to pass to :func:`define_flag`.
        """
        self._option = define_flag(*args, **kwargs)

    def __get__(self, instance, owner):
        value = getattr(flags.values, self._option.dest, self._option.default)
        if self._option.required and (value is optparse.NO_DEFAULT
                                      or value is None):
            raise optparse.OptionValueError('required flag --%s not defined'
                                            % self._option.dest)
        return value


class ValuesProxy(object):
    """Acts like optparse.Values but uses defaults defined in OptionParser.

    :attr values: The real optparse.Values object.
    """

    def __init__(self, parser):
        object.__setattr__(self, '_parser', parser)
        object.__setattr__(self, 'values', optparse.Values())

    def __setattr__(self, name, value):
        setattr(self.values, name, value)

    def __getattr__(self, name):
        option = self._parser.get_option('--' + name)
        return getattr(self.values, name, option and option.default)


class ThreadPool(object):
    """A thread pool manager."""

    def __init__(self, threads=8):
        """Construct a new thread pool with :ref:`threads` threads.

        :param threads: Number of threads to start in the thread pool.
        """
        self._queue = Queue()
        self._pool = [threading.Thread(target=self._worker)
                      for _ in range(threads)]

    def _worker(self):
        """Waits for and executes jobs from the queue."""
        while True:
            message = self._queue.get()
            if message is None:
                self._queue.task_done()
                return
            job, args, kwargs = message
            try:
                job(*args, **kwargs)
            except Exception, e:
                log.error('thread pool worker failed', exc_info=e)
            self._queue.task_done()

    def add(self, function, *args, **kwargs):
        """Add a job to the thread pool.

        :param function: Function to run in the pool.
        :param args: Positional arguments to pass to function.
        :param kwargs: Keyword arguments to pass to function.
        """
        self._queue.put((function, args, kwargs))

    def quit(self):
        """Signal all workers to quit and block until they have."""
        self._queue.clear()
        for _ in range(len(self._pool)):
            self._queue.put(None)
        self._queue.join()
        for thread in self._pool:
            thread.wait()


class WeakList(list):
    """A list with weak references to its values.

    Weak references can not be created to builtin types, so we need to create
    some trivial subclasses:

    >>> class mylist(list): pass
    >>> class mydict(dict): pass
    >>> a = mylist([1, 2])
    >>> b = mydict({1: 2})

    Add the references to our WeakList:

    >>> things = WeakList()
    >>> things.append(a)
    >>> things.insert(0, b)
    >>> things
    [{1: 2}, [1, 2]]

    Then delete the original references, dropping the weak references:

    >>> del a
    >>> things
    [{1: 2}]
    >>> del b
    >>> things
    []
    """

    def append(self, value):
        ref = weakref.proxy(value, self._clear_reference)
        super(WeakList, self).append(ref)

    def insert(self, index, value):
        ref = weakref.proxy(value, self._clear_reference)
        super(WeakList, self).insert(index, ref)

    def extend(self, sequence):
        for value in sequence:
            self.append(value)

    def remove(self, value):
        for entry in self:
            if value is entry:
                return list.remove(self, entry)

    def _clear_reference(self, ref):
        for i, value in enumerate(self):
            if value is ref:
                del self[i]
                return
        raise ValueError('could not find weakref %r to remove' % ref)

    def __repr__(self):
        return '[%s]' % ', '.join(str(i) for i in self)


class cached_property(object):
    """A property that caches the result of its implementation function."""

    def __init__(self, function):
        self.function = function
        self.__name__ = function.__name__
        self.__doc__ = function.__doc__

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        value = self.function(instance)
        setattr(instance, self.__name__, value)
        return value


def parse_args(args=None):
    """Parse command-line arguments into the global :data:`flags` object.

    :param args: Command-line args, not including argv[0]. Defaults to
                 sys.argv[1:]
    :returns: Positional arguments from :data:`args`.
    """
    _, args = flag_parser.parse_args(args, values=flags)
    return args


def parse_flags_from_file(filename):
    """Parse command-line arguments from a file.

    :param filename: If not provided, try to use ~/.<application>rc
    :returns: True if file was loaded, False if not.
    """
    flag_parser.parse_flags_from_file(filename, values=flags)
    return True


def write_flags_to_file(filename):
    """Write global flags to a file."""
    flag_parser.write_flags_to_file(filename, flags)


def define_flag(*args, **kwargs):
    """Define a flag.

    This has the same semantics as :meth:`optparse.OptionParser.add_option`.

    :param args: Positional arguments passed through to add_option.
    :param kwargs: Keyword arguments passed through to add_option.
    :returns: Return value from add_option.
    """
    return flag_parser.add_option(*args, **kwargs)


def dispatch_command(args):
    """Dispatch to a command registered with @command."""
    flag_parser.dispatch_command(args)


# This is mostly here to help with testing.
def init(args=None, usage=None, version=None, epilog=None, config=None):
    """Initialise the application.

    See :func:`run` for further documentation.

    :returns: Remaining command-line arguments after flag parsing.
    """
    log_manager.set_level(logging.ERROR)
    log_manager.log_to_console(True)
    if version:
        flag_parser.set_version(version)
    if usage:
        flag_parser.set_usage(usage)
    if epilog:
        flag_parser.set_epilog(epilog)

    flags.values._update_loose(vars(flag_parser.get_default_values()))
    if config and os.path.exists(config):
        flag_parser.parse_flags_from_file(config, values=flags.values)
    _, args = flag_parser.parse_args(args, values=flags.values)
    return args


def run(main=None, args=None, usage=None, version=None, epilog=None,
        config=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, configures
    logging, and passes any remaining arguments through to the main function. If
    main() returns a false value

    >>> def main(args):
    ...   print args
    >>> run(main, ['hello', 'world'])
    ['hello', 'world']

    :param main: Main function to call, with the signature main(args). After
                 execution of main(), any commands registered with @command
                 will be dispatched. This allows main() to be used as
                 initialisation code. If main() returns True, commands will not
                 be dispatched.
    :param args: Command-line arguments. Will default to sys.argv[1:].
    :param usage: A usage string, displayed when --help is passed. If not
                  provided, the docstring from main will be used.
    :param version: The version of the application. If provided, adds a
                    --version flag.
    :param epilog: Optional help text epilog.
    :param config: Configuration file to load flags from.

    :raises Error: If main is not provided and no commands are defined with
                   :func:`command`.
    """
    if usage is None:
        usage = inspect.getdoc(main)
    args = init(args=args, usage=usage, version=version, epilog=epilog,
                config=config)
    if main and main(args):
        return
    try:
        dispatch_command(args)
    except CommandError, e:
        fatal(e)


def fatal(*args):
    """Print an error and terminate with a non-zero status."""
    program = os.path.basename(sys.argv[0])
    print >> sys.stderr, '%s: fatal: %s' % (program, ' '.join(map(str, args)))
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


def _set_logging_flag(option, opt_str, value, parser):
    """Flag callback for setting the log level."""
    level = getattr(logging, value.upper(), 'ERROR')
    log_manager.set_level(level)
    flags.logging = value


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class LogManager(object):
    """Convenience class for managing loggers.

    Sets up a logger named 'flam' that logs to level>=ERROR to stderr.
    """

    FORMAT = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    TIME_FORMAT = '%Y%m%d %H%M%S'

    def __init__(self):
        self.formatter = logging.Formatter(self.FORMAT, self.TIME_FORMAT)
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.DEBUG)
        self.console.setFormatter(self.formatter)
        self.root = logging.getLogger()
        self.root.setLevel(logging.ERROR)
        self.root.addHandler(self.console)
        self.root.addHandler(NullHandler())

    def get_logger(self, name):
        return logging.getLogger(name)

    def set_level(self, level):
        self.root.setLevel(level)

    def log_to_console(self, enable):
        switch = self.root.addHandler if enable else self.root.removeHandler
        switch(self.console)


log_manager = LogManager()
get_logger = log_manager.get_logger
log = log_manager.get_logger('flam')

flag_parser = FlagParser()
flags = ValuesProxy(flag_parser)
command = flag_parser.register_command


@command
def help():
    """Display help on available commands."""
    flag_parser.print_help()


define_flag('--logging', type=str, action='callback',
            callback=_set_logging_flag,
            help='set log level to debug, info, warning, error '
                 'or fatal [%default]',
            metavar='LEVEL', default='warning')


if __name__ == '__main__':
    import doctest
    doctest.testmod()
