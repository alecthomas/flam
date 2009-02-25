"""Monitoring for FLAM.

This module exports namespaced application variables to a monitoring system
through a request handler.

The Monitor object manages monitor variables:

>>> monitor = Monitor()

Variables can be defined declaratively through container objects:

>>> vars = monitor.container('namespace')
>>> vars.some_value = 456
>>> monitor.export()
{'namespace.some_value': 456}

Or through callbacks with monitor.variable():

>>> @monitor.variable
... def time():
...   return 123
>>> monitor.export()
{'time': 123, 'namespace.some_value': 456}
"""


__all__ = ['Monitor', 'Variables', 'variable']


import weakref
from flam.web import Response, expose, json, request, tag


class Container(object):
    """A collection of namespaced attributes:

    >>> vars = Container({}, 'namespace')
    >>> vars.some_var = 10
    >>> vars
    {'namespace.some_var': 10}
    """

    def __init__(self, variables, namespace, **defaults):
        object.__setattr__(self, '_namespace', namespace)
        object.__setattr__(self, '_variables', variables)
        for key, value in defaults.iteritems():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        self._variables[self._namespace + '.' + key] = value

    def __getattr__(self, key):
        return self._variables[self._namespace + '.' + key]

    def __repr__(self):
        return repr(self._variables)



class Monitor(object):
    """Manager object for monitor variables."""

    def __init__(self):
        self._variables = {}
        self._callbacks = weakref.WeakValueDictionary()

    def variable(self, name=None, function=None):
        """Register a monitor variable callback.

        >>> monitor = Monitor()

        Callbacks can be registered using a decorator. The name of the variable
        is the callback name:

        >>> @monitor.variable
        ... def var1():
        ...   return 123
        >>> monitor.export()
        {'var1': 123}

        Or explicitly by calling Monitor.variable():

        >>> def var2():
        ...   return 567
        >>> _ = monitor.variable(var2)
        >>> monitor.export()
        {'var1': 123, 'var2': 567}

        Finally, the variable name can be overridden:

        >>> def var99():
        ...   return 890
        >>> _ = monitor.variable('var3', var99)
        >>> monitor.export()
        {'var1': 123, 'var3': 890, 'var2': 567}
        """
        def wrapper(function):
            self._callbacks[name or function.__name__] = function
            return function

        if callable(function):
            return wrapper(function)

        if callable(name):
            function = name
            name = None
            return wrapper(function)

        return wrapper

    def container(self, namespace, **defaults):
        """Return a namespaced monitor variable container."""
        return Container(self._variables, namespace, **defaults)

    def export(self):
        """Export monitor variables as a dictionary."""
        data = self._variables.copy()
        data.update((name, callback()) for name, callback
                    in self._callbacks.iteritems())
        return data


_monitor = Monitor()
variable = _monitor.variable
Variables = _monitor.container


@expose
def monitor():
    format = request.args.get('format', 'text')
    if format == 'json':
        return json(_monitor.export())
    else:
        return Response('\n'.join('%s=%r' % (k, v) for k, v
                                  in _monitor.export().items()))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
