"""A loosely coupled feature broker.

A feature is an arbitrary object referenced by a feature key. Feature providers
and consumers have no awareness of each other beyond the contract implicit in
the feature itself. In the spirit of Python this contract is not enforced, but
is rather an agreement.

An example follows, providing simple, extensible URL content fetchers. The
feature "contract" is that the provided features are callables accepting a URI
and raising a ValueError if the URI is unacceptable.

Define a HTTP handler:

>>> def http_handler(uri):
...   if not uri.startswith('http://'):
...     raise ValueError
...   return 'fake HTTP content'

Register them:

>>> uri_handlers = FeatureBroker()
>>> uri_handlers.provide(['handlers'], http_handler)

Notice how the feature key is a list. This indicates to the FeatureBroker that
the feature should be an extensible sequence.

We then provide a convenience function for accessing them:

>>> def fetch(uri):
...   for handler in uri_handlers.require('handlers'):
...     try:
...       return handler(uri)
...     except ValueError:
...       continue
...   else:
...     raise ValueError('No handlers found for %r' % uri)

Now "fetch" data from a URI:

>>> fetch('http://example.com')
'fake HTTP content'

Excellent. Except we can't fetch from FTP servers:

>>> fetch('ftp://example.com')
Traceback (most recent call last):
...
ValueError: No handlers found for 'ftp://example.com'

Fortunately, we can easily add support for it:

>>> def ftp_handler(uri):
...   if not uri.startswith('ftp://'):
...     raise ValueError
...   return 'fake FTP content'
>>> uri_handlers.provide(['handlers'], ftp_handler)

And try again:

>>> fetch('ftp://example.com')
'fake FTP content'


Based on:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/413268
"""


class Error(Exception):
    """Base feature exception."""


class UnknownFeature(Error):
    """Unkown feature."""

    def __str__(self):
        return 'Unknown feature %r' % (self.args[0],)


class ValidationError(Error):
    """A feature did not match the validation criteria."""


class Sequence(list):
    """Marker class for discriminating between feature lists and features."""


class FeatureBroker(object):
    """Register and locate features.

    Features are arbitrary objects referenced by a feature key. In our example,
    the key is the string 'name' and the feature is a string with the value
    'Bob Smith':

    >>> features = FeatureBroker()
    >>> features.provide('name', 'Bob Smith')
    >>> features.require('name')
    'Bob Smith'

    Or callbacks:

    >>> def counter():
    ...   counter.count += 1
    ...   return counter.count
    >>> counter.count = 0
    >>> features.deferred('counter', counter)
    >>> features.require('counter')
    1
    >>> features.require('counter')
    2

    Finally, if the feature identifier is a single-element list, the value of
    the feature will be a sequence:

    >>> features.provide(['users'], 'Bob')
    >>> features.provide(['users'], 'Barry')
    >>> features.deferred(['users'], lambda: 'Barnaby')
    >>> features.require(['users'])
    ['Bob', 'Barry', 'Barnaby']
    """

    def __init__(self):
        """Construct a new FeatureBroker."""
        self._features = {}

    def require(self, feature):
        """Require a feature.

        :param feature: A feature can be any orderable, hashable object
                        including classes, builtin type values, etc.

        :returns: The required feature.

        :raises UnknownFeature: If the feature could not be found.
        """
        if isinstance(feature, list):
            feature = feature[0]
            sequence = True
        else:
            sequence = False
        try:
            result = self._features[feature]
            if isinstance(result, Sequence):
                return [r() for r in result]
            return result()
        except KeyError:
            raise UnknownFeature(feature)

    def provide(self, feature, what):
        """Register an object as a feature.

        Provide a feature as a single object:

        >>> features = FeatureBroker()
        >>> features.provide('afeature', 'A Feature')
        >>> features.require('afeature')
        'A Feature'

        Or as a sequence:

        >>> features.provide(['somefeatures'], 'One Feature')
        >>> features.provide(['somefeatures'], 'Two Features')
        >>> features.require('somefeatures')
        ['One Feature', 'Two Features']

        :param feature: A key uniquely identifying the feature. If this is a
                        list, the feature will be assumed to be a sequence,
                        with the first element the feature key.
        :param what: The object tied to the feature key.
        """
        def call():
            return what
        self._provide(feature, call)

    def deferred(self, feature, what, *args, **kwargs):
        """Register a deferred callable as a feature.

        Any positional/keyword arguments supplied to :meth:`deferred` will be
        passed to the callable when it is "required".

        >>> features = FeatureBroker()
        >>> def full_name(first_name, surname):
        ...   return '%s %s' % (first_name, surname)
        >>> features.deferred('name', full_name, 'Philleas', surname='Phogg')
        >>> features.require('name')
        'Philleas Phogg'

        :param feature: See :meth:`provide` for details.
        :param what: Function to call when the feature is :meth:`require`'d.
        :param args: Positional arguments to pass through to `what` when
                     calling.
        :param kwargs: Keyword arguments to pass to `what`.
        """
        def call():
            return what(*args, **kwargs)
        self._provide(feature, call)

    def remove(self, feature, element=None):
        """Unregister a feature.

        :raises UnknownFeature: Feature does not exist.
        """
        try:
            found = self._features[feature]
        except KeyError:
            raise UnknownFeature(feature)
        if isinstance(found, Sequence) and element is not None:
            found.remove(element)
        else:
            del self._features[feature]

    # Internal methods
    def _provide(self, feature, callback):
        """Register function as feature."""
        if isinstance(feature, list):
            feature = feature[0]
            sequence = True
        else:
            sequence = False
        try:
            current = self._features[feature]
            if isinstance(current, Sequence):
                if not sequence:
                    raise Error('Can not redeclare feature sequence %r as '
                                'non-sequence' % feature)
                current.append(callback)
            else:
                raise Error('Feature %r can not be redeclared.' % (feature,))
        except KeyError:
            if sequence:
                callback = Sequence([callback])
            self._features[feature] = callback


class Require(object):
    """Convenience property wrapper for FeatureBroker.require.

    >>> class A(object):
    ...   username = Require('username')
    >>> a = A()

    Accessing the property before it is "provided" results in an UnknownFeature
    exception:

    >>> a.username
    Traceback (most recent call last):
    ...
    UnknownFeature: Unknown feature 'username'

    Providing the feature works as you would expect:

    >>> provide('username', 'Bob')
    >>> a.username
    'Bob'
    """
    def __init__(self, feature, locator=None):
        self._feature = feature
        self._locator = locator or features

    def __get__(self, instance, owner):
        if not instance:
            return self
        return self._locator.require(self._feature)


features = FeatureBroker()
provide = features.provide
deferred = features.deferred
require = features.require
remove = features.remove


if __name__ == '__main__':
    import doctest
    doctest.testmod()
