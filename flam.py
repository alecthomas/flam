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
================================================

Global flags registry
---------------------

Register new flags with :func:`flag`. This is an alias for
optparse.OptionParser.add_option().

The underlying optparse.OptionParser object is exposed as :data:`flag_parser`.

Call :func:`parse_args` to parse command-line arguments. Defaults to parsing
sys.argv[1:].

:data:`flags` is an optparse.Values() object that will contain the parsed flag
values.

The --flags=FILE flag can be used to load flag values from a file consisting
of "key = value" lines. Both empty lines and those beginning with # are ignored.
"""


from __future__ import with_statement

import optparse


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
__all__ = ['Error', 'SignalError', 'UnboundCallback', 'Signal', 'Callback',
           'Flag', 'define_flag', 'flags', 'parse_args', 'on_args_parsed',
           'init', 'run', 'on_application_init']


class Error(Exception):
    """Base Flam exception."""


class SignalError(Error):
    """Base event exception."""


class UnboundCallback(SignalError):
    """A Callback was not associated with a callback when callbacked."""


class Signal(object):
    """A Signal tracks a set of receivers and delivers messages to them.

    Create a new Signal:

    >>> on_init = Signal()

    Register a callback decorating a function with the :class:`Signal`:

    >>> @on_init.connect
    ... def init_console(stage):
    ...   return '%d:console initialised' % stage

    Any number of callbacks can be bound to a :class:`Signal`:

    >>> @on_init.connect
    ... def init_web_server(stage):
    ...   return '%d:web server initialised' % stage

    Call the signal to deliver an event. The return values for all callbacks
    are collected and returned in a list:

    >>> on_init(1)
    ['1:console initialised', '1:web server initialised']
    """

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)
        return callback

    def __call__(self, *args, **kwargs):
        return [callback(*args, **kwargs) for callback in self._callbacks]

    def disconnect(self, callback):
        self._callbacks.remove(callback)

    def __iter__(self):
        return iter(self._callbacks)


class Callback(Signal):
    """A callback is a :class:`Signal` with exactly one callback.

    The semantics of a Callback differ from :class:`Signal`, in that calling it
    will register a function and calling :meth:`Callback.emit` will trigger the
    callback.

    Create a new callback:

    >>> application_version = Callback()

    Bind it to a callback:

    >>> @application_version
    ... def get_version():
    ...   return '0.1'

    To trigger the callback call the :meth:`Callback.emit` method:

    >>> application_version.emit()
    '0.1'

    If multiple callables are bound to a Callback, only the last one will be
    called. Its result will be returned:

    >>> @application_version
    ... def get_version_2():
    ...   return '0.2'
    >>> application_version.emit()
    '0.2'

    Callbacks can also be unbound:

    >>> application_version.disconnect(get_version_2)
    >>> application_version.emit()
    '0.1'
    """

    def __init__(self, must_be_bound=True):
        """Create a new Callback.

        :param must_be_bound: If True, require that a callback be bound to the
                              Callback.
        """
        super(Callback, self).__init__()
        self._must_be_bound = must_be_bound

    def __call__(self, function):
        return super(Callback, self).connect(function)

    def emit(self, *args, **kwargs):
        if not self._callbacks:
            if self._must_be_bound:
                raise UnboundCallback
            return None
        return self._callbacks[-1](*args, **kwargs)


class FlagParser(optparse.OptionParser):
    """An OptionParser that optionally loads flags from a file.

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
        optparse.OptionParser.__init__(self, *args, **kwargs)
        self.add_option('--flags', metavar='FILE', type=str,
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
    on_args_parsed(args, flags)
    return args


def parse_args_from_file(filename):
    """Parse command-line arguments from a file."""
    options, args = flag_parser.parse_args_from_file(filename)
    flags.__dict__.update(options.__dict__)
    on_args_parsed(args, flags)
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
    on_application_init()
    if version:
        flags.parser.set_version(version)
    if usage:
        flags.parser.set_usage(usage)
    return flag_parser.parse_args(args)


def run(main, args=None, usage=None, version=None):
    """Initialise and run the application.

    This function parses and updates the global flags object, and passes
    any remaining arguments through to the main function.

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
        usage = main.__doc__
    options, args = init(args, usage, version)
    main(args)


flag_parser = FlagParser()
flags = optparse.Values()
on_args_parsed = Signal()
on_application_init = Signal()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
