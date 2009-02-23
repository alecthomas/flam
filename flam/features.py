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

Register it:

>>> uri_handlers = FeatureBroker()
>>> uri_handlers.append('handlers', http_handler)

Note that the feature key is a list. This indicates to the FeatureBroker that
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
>>> uri_handlers.append('handlers', ftp_handler)

And try again:

>>> fetch('ftp://example.com')
'fake FTP content'


Inspired by:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/413268
"""


from flam.core import Error


__all__ = ['Error', 'UnknownFeature', 'Sequence',
           'deferred', 'FeatureBroker', 'Require', 'features', 'provide',
           'extend', 'append', 'require', 'remove']


class Error(Error):
    """Base feature exception."""


class UnknownFeature(Error):
    """Unkown feature."""

    def __str__(self):
        return 'Unknown feature %r' % (self.args[0],)


class Sequence(list):
    """Marker class for discriminating between feature lists and features."""


class deferred(object):
    """Defer a callable until it is "required".

    >>> features = FeatureBroker()
    >>> def counter():
    ...   counter.count += 1
    ...   return counter.count
    >>> counter.count = 0
    >>> features.provide('counter', deferred(counter))
    >>> features.require('counter')
    1
    >>> features.require('counter')
    2
    """

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        """Call the deferred object."""
        return self.callback(*self.args, **self.kwargs)


class FeatureBroker(object):
    """Register and locate features.

    Features are arbitrary objects referenced by a feature key. In our example,
    the key is the string 'name' and the feature is a string with the value
    'Bob Smith':

    >>> features = FeatureBroker()
    >>> features.provide('name', 'Bob Smith')
    >>> features.require('name')
    'Bob Smith'

    Features may also be classes, which is useful with "interfaces". First,
    define our interface:

    >>> class INameProvider(object):
    ...   def get_names(self): pass

    Then some implementations:

    >>> class AngloNameProvider(object):
    ...   def get_names(self):
    ...     return ['Smith', 'Bathingthwaite']
    >>> class ChineseNameProvider(object):
    ...   def get_names(self):
    ...     return ['Zhang', 'Wu']

    Declare them as a feature, keyed on the interface class:

    >>> features.extend(INameProvider, [AngloNameProvider(),
    ...                                 ChineseNameProvider()])

    Then use the implementations:

    >>> for provider in features.require(INameProvider):
    ...   for name in provider.get_names():
    ...     print name
    Smith
    Bathingthwaite
    Zhang
    Wu

    Functions may also be called when "required" by wrapping them in a
    :class:`deferred` object:

    >>> def counter():
    ...   counter.count += 1
    ...   return counter.count
    >>> counter.count = 0
    >>> features.provide('counter', deferred(counter))
    >>> features.require('counter')
    1
    >>> features.require('counter')
    2


    """

    def __init__(self):
        """Construct a new FeatureBroker."""
        self._features = {}

    def require(self, feature):
        """Require a feature.

        :param feature: A feature can be any orderable, hashable object,
                        including classes, builtin type values, etc.

        :returns: The required feature.

        :raises UnknownFeature: If the feature could not be found.
        """
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

        Or as a callable:

        >>> def full_name(first_name, surname):
        ...   return '%s %s' % (first_name, surname)
        >>> features.provide('name', lambda: full_name('Philleas', 'Phogg'))

        :param feature: A key uniquely identifying the feature.
        :param what: The object tied to the feature key.
        """
        self._provide(feature, what)

    def extend(self, feature, sequence):
        """Extend a feature sequence with an iterable.

        >>> features = FeatureBroker()
        >>> features.extend('countries', ['Australia', 'New Zealand'])
        >>> features.extend('countries', ['Czech', 'Slovakia'])
        >>> features.require('countries')
        ['Australia', 'New Zealand', 'Czech', 'Slovakia']
        """
        for i in sequence:
            self._provide(feature, i, sequence=True)

    def append(self, feature, what):
        """Append a feature to a feature sequence.

        >>> features = FeatureBroker()
        >>> features.append('somefeatures', 'One Feature')
        >>> features.append('somefeatures', 'Two Features')
        >>> features.require('somefeatures')
        ['One Feature', 'Two Features']

        Appending to a non-sequence is invalid:

        >>> features.provide('name', 'Barry')
        >>> features.append('name', 'White')
        Traceback (most recent call last):
        ...
        Error: Feature 'name' can not be redeclared.
        """
        self._provide(feature, what, sequence=True)

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
    def _provide(self, feature, what, sequence=False):
        """Register function as feature."""
        if isinstance(what, deferred):
            callback = what
        else:
            callback = lambda: what
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
extend = features.extend
append = features.append
require = features.require
remove = features.remove


if __name__ == '__main__':
    import doctest
    doctest.testmod()
