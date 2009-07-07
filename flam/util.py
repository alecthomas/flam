# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Utility classes, constants and functions."""


import datetime
import posixpath
import re
import StringIO
import time
import urllib
import random
import time
import weakref


__all__ = [
    'URI', 'Signal', 'DecoratorSignal', 'cached_property', 'to_iso_time',
    'from_iso_time', 'to_boolean', 'to_list', 'get_last_traceback',
    'random_sleep', 'WeakList',
    ]


# XXX Appropriated from http://swapoff.org/pyndexter
class URI(object):
    """Parse a URI into its component parts. The `query` component is passed
    through `cgi.parse_qs()`.

        scheme://username:password@host/path?query#fragment

    Each component is available as an attribute of the object.

    TODO: Support "parameters???" Never seen this in the wild:
        scheme://username:password@host/path;parameters?query#fragment

    PS. `urlparse` is not useful.

    The URI constructor can be passed a string:

    >>> u = URI('http://user:password@www.example.com:12345/some/path?parm=1&parm=2&other=3#fragment')
    >>> u
    URI(u'http://user:password@www.example.com:12345/some/path?other=3&parm=1&parm=2#fragment')
    >>> u.scheme
    'http'
    >>> u.username
    'user'
    >>> u.password
    'password'
    >>> u.host
    'www.example.com'
    >>> u.path
    '/some/path'
    >>> u.query
    {'parm': ['1', '2'], 'other': ['3']}
    >>> u.fragment
    'fragment'

    ...or the individual URI components as keyword arguments:

    >>> URI(scheme='http', username='user', password='password', host='www.example.com', port=12345, path='/some/path', query={'parm': [1, 2], 'other': [3]}, fragment='fragment')
    URI(u'http://user:password@www.example.com:12345/some/path?other=3&parm=1&parm=2#fragment')

    ...or a combination of the two, in which case keyword arguments are used as
    defaults if not provided by the URI:

    >>> URI('http://localhost', port=80)
    URI(u'http://localhost:80')

    ...and finally, another URI object:

    >>> v = URI(u)
    >>> v == u
    True
    >>> v.query is u.query
    False
    >>> v
    URI(u'http://user:password@www.example.com:12345/some/path?other=3&parm=1&parm=2#fragment')

    URI also normalises the path component:

    >>> URI('http://www.example.com//some/../foo/path/')
    URI(u'http://www.example.com/foo/path')

    Query parameters must be passed as a dictionary with list values. Values
    are encoded automatically:

    >>> URI('http://localhost', query={'q': ['#1', 'foo']})
    URI(u'http://localhost?q=%231&q=foo')
    """

    _pattern = re.compile(r"""
        (?:(?P<scheme>[^:]+)://)?
        (?:(?P<username>[^:@]*)
            (?::(?P<password>[^@]*))?@)?
        (?P<host>[^?/#:]*)
        (?::(?P<port>[\d]+))?
        (?P<path>/[^#?]*)?
        (?:\?(?P<query>[^#]*))?
        (?:\#(?P<fragment>.*))?
        """, re.VERBOSE)

    __slots__ = ['scheme', 'username', 'password', 'host', 'port', '_path',
                             'query', 'fragment']

    def __init__(self, uri=None, scheme=None, username=None, password=None,
                             host=None, port=None, path=None, query=None, fragment=None):
        # TODO(aat) Make the logic in this constructor more efficient.
        self._path = ''
        query = query or {}
        # Copy attributes of a URI object
        if isinstance(uri, URI):
            from copy import copy
            (self.scheme, self.username, self.password, self.host, self.port,
             self.path, self.query, self.fragment) = (
                     uri.scheme, uri.username, uri.password, uri.host,
                     uri.port, uri.path, copy(uri.query), uri.fragment)
        elif uri is not None:
            # Parse URI string
            from cgi import parse_qs

            match = self._pattern.match(uri)
            if match is None:
                raise ValueError('Invalid URI')
            groups = [g or '' for g in match.groups()]
            groups = (map(urllib.unquote, groups[0:6]) +
                                [parse_qs(groups[6] or '')] +
                                map(urllib.unquote, groups[7:]))
            (self.scheme, self.username, self.password, self.host, self.port,
                self.path, self.query, self.fragment) = groups
        else:
            # Explicitly provide URI components
            (self.scheme, self.username, self.password, self.host, self.port,
             self.path, self.query, self.fragment) = (
                     scheme, username, password, host, port, path, query, fragment)

        # Set any remaining defaults
        if not self.scheme: self.scheme = scheme or ''
        if not self.username: self.username = username or ''
        if not self.password: self.password = password or ''
        if not self.host: self.host = host or ''
        if not self.port: self.port = port or ''
        if not self.path: self.path = path or ''
        if not self.query: self.query = query or {}
        if not self.fragment: self.fragment = fragment or ''

    def _set_path(self, path):
        """Return a normalised path."""
        if path:
            self._path = '/' + posixpath.normpath(path).lstrip('/')
        else:
            self._path = ''

    def _get_path(self):
        return self._path

    path = property(_get_path, _set_path)

    def __cmp__(self, other):
        """Compare two URI objects.

        >>> u = URI('http://user:password@www.example.com/some/path?parm=1&parm=2&other=3#fragment')
        >>> v = URI(u)
        >>> u == v
        True
        >>> v.host = 'www.blue.com'
        >>> v
        URI(u'http://user:password@www.blue.com/some/path?other=3&parm=1&parm=2#fragment')
        >>> u == v
        False
        """
        return cmp(repr(self), repr(other))

    def __repr__(self):
        return "URI(u'%s')" % unicode(self)

    def __nonzero__(self):
        return len(str(self))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        uri = unicode(self.scheme and (urllib.quote(self.scheme) + u'://') or u'')
        if self.username or self.password:
            if self.username:
                uri += urllib.quote(self.username)
            if self.password:
                uri += u':' + urllib.quote(self.password)
            uri += u'@'
        uri += urllib.quote(self.host)
        if self.port:
            uri += u':%s' % self.port
        uri += urllib.quote(self.path)
        if self.query:
            uri += u'?' + u'&'.join(
                [u'&'.join([u'%s=%s' % (urllib.quote(k), urllib.quote(str(v)))
                            for v in l])
                 for k, l in sorted(self.query.items())]
                )
        if self.fragment:
            uri += u'#' + urllib.quote(self.fragment)
        return uri


class Signal(object):
    """An object for implementing the observer pattern.

    Listeners connect functions to signals. All listeners are called when the
    producer calls the signal.

    >>> trigger = Signal()
    >>> def func1():
    ...   print 'func1()'
    >>> def func2():
    ...   print 'func2()'
    >>> trigger.connect(func1)
    >>> trigger.connect(func2)
    >>> trigger()
    func1()
    func2()
    """
    def __init__(self, limit=None):
        """Construct a new Signal.

        :param limit: Number of callbacks allowed in the FIFO.
        """
        self._callbacks = []
        self._limit = limit

    def reset(self):
        """Reset signal state."""
        self._callbacks = []

    def connect(self, callback):
        """Connect a function to the signal."""
        self._callbacks.append(callback)
        if self._limit is not None and len(self._callbacks) > self._limit:
            del self._callbacks[:len(self._callbacks) - self._limit]

    def disconnect(self, callback):
        """Disconnect a function from the signal."""
        self._callbacks.remove(callback)

    def __call__(self, *args, **kwargs):
        response = None
        for callback in self._callbacks:
            response = callback(*args, **kwargs)
        return response


class DecoratorSignal(Signal):
    """Define signal callbacks with a decorator.

    >>> mark = DecoratorSignal()
    >>> @mark
    ... def func1():
    ...   print 'func1()'
    >>> @mark
    ... def func2():
    ...   print 'func2()'
    >>> mark.dispatch()
    func1()
    func2()
    """

    def dispatch(self, *args, **kwargs):
        """Dispatch to the callbacks."""
        return super(DecoratorSignal, self).__call__(*args, **kwargs)

    def __call__(self, function):
        """Connect this DecoratorSignal to the given function."""
        self.connect(function)
        return function


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


def to_iso_time(dtime):
    """Convert a datetime object into a ISO8601 formatted datetime string.

    Args:
        dtime: datetime.datetime object

    Returns:
        ISO8601 formatted datetime string
    """
    return iso8601.tostring(time.mktime(dtime.timetuple()))


def from_iso_time(iso):
    """Convert an ISO8601 formatted string into a datetime object.
    
    Args:
        iso: ISO8601 formatted string.
        
    Returns:
        datetime.datetime object
    """
    return datetime.datetime.fromtimestamp(iso8601.parse(iso))


def to_boolean(value):
    """Convert a "human" readable value to a bool.

    :param value: String to convert.
    :return: True or False.
    """
    return value in ('yes', 'true', 'on', 'aye', '1', 1, True)


def to_list(value, sep=',', keep_empty=False):
    """Convert a token-separated string to a list."""
    if isinstance(value, basestring):
        items = [item.strip() for item in value.split(sep)]
    else:
        items = list(value or [])
    if not keep_empty:
        items = filter(None, items)
    return items


def get_last_traceback():
    """Write current exception traceback to a string.

    :return: Exception traceback as a string.
    """
    import traceback
    tb = StringIO.StringIO()
    traceback.print_exc(file=tb)
    return tb.getvalue()


def random_sleep(a,b):
    """Sleep a random amount of time between a anb b seconds.

    :param a: minimum time to sleep
    b: maximum time to sleep
    """
    delay = random.uniform(a, b)
    time.sleep(delay)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
