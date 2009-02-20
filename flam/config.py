"""A file-backed declarative layer on optparse.

This module allows the user to register command line options, and to load them
in bulk from a configuration file.

>>> class Config(Configuration):
...    debug = BoolOption('Enable debugging.', default=False)
...    debug_level = IntOption('Debug level 0 <= n <= 9.', default=0)
...    db = URIOption('Database URI.')

>>> config = Config(args=['--debug=true', '--db=mysql://localhost/db'])
>>> config
{'debug': True, 'debug_level': 0, 'db': URI(u'mysql://localhost/db')}
>>> config.debug
True
>>> config.db
URI(u'mysql://localhost/db')

"""

from __future__ import with_statement
import optparse
import sys

from flam.util import to_boolean, to_list, URI


__all__ = ['Configuration', 'Option', 'IntOption', 'FloatOption', 'ListOption',
           'BoolOption']


class Option(object):
    """A configuration option."""

    def __init__(self, help, default=None, *args, **kwargs):
        self.args = args
        kwargs['help'] = help
        kwargs['default'] = default
        self.init_kwargs(kwargs)
        self.kwargs = kwargs

    def init_kwargs(self, kwargs):
        """Hook for initialising keyword arguments to optparse.Option()."""
        kwargs.setdefault('action', 'store')

    def to_optparse_option(self, name):
        flag = '--' + name
        option = optparse.Option(flag, *self.args, **self.kwargs)
        return option


class ConvertingOption(Option):
    """A virtual base Option that performs type conversion."""

    def convert(self, value):
        """Override this to convert an option."""
        raise NotImplementedError

    def init_kwargs(self, kwargs):
        def convert(option, opt_str, value, parser):
            setattr(parser.values, opt_str[2:], self.convert(value))

        kwargs.update(dict(
            type='string',
            action='callback',
            callback=convert,
            ))


class IntOption(Option):
    """An integer option.

    >>> class Config(Configuration):
    ...   age = IntOption('Age.')
    >>> config = Config(args=['--age=34'])
    >>> config.age
    34
    """

    def init_kwargs(self, kwargs):
        kwargs['type'] = 'int'


class FloatOption(Option):
    """A floating point option."""
    def init_kwargs(self, kwargs):
        kwargs['type'] = 'float'


class BoolOption(ConvertingOption):
    """A boolean option.

    >>> class Config(Configuration):
    ...   alive = BoolOption('Alive?')
    >>> config = Config(args=['--alive=true'])
    >>> config.alive
    True
    """

    def convert(self, value):
        return to_boolean(value)


class URIOption(ConvertingOption):
    """A URI option.

    The value will be a flam.util.URI object.

    >>> class Config(Configuration):
    ...   db = URIOption('Database connection.')
    >>> config = Config(args=['--db=mysql://localhost:5001/db'])
    >>> config.db
    URI(u'mysql://localhost:5001/db')
    """
    def convert(self, value):
        return URI(value)


class ListOption(ConvertingOption):
    """An option with a list of values.

    >>> class Config(Configuration):
    ...   names = ListOption('Names.')
    >>> config = Config(args=['--names=bob,alice'])
    >>> config.names
    ['bob', 'alice']
    """

    def __init__(self, *args, **kwargs):
        self.sep = kwargs.pop('sep', ',')
        self.keep_empty = kwargs.pop('keep_empty', False)
        super(ListOption, self).__init__(*args, **kwargs)

    def convert(self, value):
        return to_list(value, sep=self.sep, keep_empty=self.keep_empty)


class Configuration(object):
    """Configuration container object.

    Configuration options are declared as class attributes. Options can be
    defined in a configuration file or via command line flags.
    """

    def __init__(self, file=None, args=None, **kwargs):
        """Create a new Configuration object.

        :param file: File-like object or filename to load configuration from.
        :param args: Command-line arguments, excluding argv[0]. sys.argv will
                     be used if omitted.
        :param kwargs: Extra keyword arguments to pass to the OptionParser
                       constructor.
        """
        options = self._collect_options()
        self._parser = optparse.OptionParser(option_list=options, **kwargs)
        self._parser.add_option(
            '--config', help='Configuration file to load.',
            default=filename, action='store',
            )
        defaults = dict((option.dest, option.default) for option in options)
        self._values = optparse.Values(defaults)
        if filename is not None:
            self.read(filename)
        # TODO(alec) We should preserve args somewhere...
        _, args = self._parser.parse_args(args or sys.argv[1:], values=self._values)

    def read(self, file):
        """Read option configuration from a file-like object or a filename.

        >>> class Config(Configuration):
        ...   age = IntOption('Age.')
        >>> from StringIO import StringIO
        >>> conf_file = StringIO('age=10')
        >>> config = Config(conf_file)
        >>> config.age
        10
        """
        file_args = self._read_args(file)
        self._parser.parse_args(file_args, values=self._values)

    def __repr__(self):
        return repr(self._values.__dict__)

    def _collect_options(self):
        options = []
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Option):
                value = value.to_optparse_option(name)
            elif isinstance(value, optparse.Option):
                pass
            else:
                continue
            options.append(value)
        return options

    def _read_args(self, file):
        args = []
        if isinstance(file, basestring):
            file = open(file)
        try:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                args.append('--' + key.strip())
                args.append(value.strip())
            return args
        finally:
            file.close()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
