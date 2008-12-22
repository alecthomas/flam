"""A system for adapting objects and types.

A good example of when adaption is useful is when needing to represent data in
a variety of output formats. An adapter can be registered for each destination
format, allowing new formats and data types to be added without modification of
existing code.

For example:

>>> adapter = Adapter()

First define a content conversion function:

>>> def list_to_html(what):
...   ul = '<ol>'
...   if what:
...     ul += '<li>' + '</li><li>'.join(map(str, what)) + '</li>'
...   ul += '</ol>'
...   return ul

Then register the function as a transcoder from list objects to the MIME type
'text/html':

>>> adapter.adapts(list, 'text/html', list_to_html)

Then we simply adapt the input data to the desired MIME type:

>>> data = [1, 2, 3]
>>> print adapter.adapt(data, 'text/html')
<ol><li>1</li><li>2</li><li>3</li></ol>

Adding new formats is easy:

>>> def list_to_wiki(what):
...   if what:
...     return ' # ' + '\\n # '.join(map(str, what))
...   else:
...     return ''

Register adaptions from multiple source types by passing a sequence to adapt:

>>> adapter.adapts((list, tuple), 'application/x-wiki', list_to_wiki)

Then adapt as normal:

>>> print adapter.adapt(data, 'application/x-wiki')
 # 1
 # 2
 # 3
>>> print adapter.adapt(('A', 'B', 'C'), 'application/x-wiki')
 # A
 # B
 # C

Attempted conversion to an unknown MIME type results in an InvalidAdaption:

>>> print adapter.adapt([1, 2, 3], 'text/plain')
Traceback (most recent call last):
...
InvalidAdaption: Could not adapt [1, 2, 3] to 'text/plain'.
"""


from inspect import isclass
from features import FeatureBroker, UnknownFeature, features


class Error(Exception):
    """Base adaption exception."""


class InvalidAdaption(Error):
    """Could not find an adapter."""

    def __str__(self):
        return 'Could not adapt %r to %r.' % self.args[:2]


class Adaption(object):
    """Unique type for adaptions in the FeatureBroker."""

    __slots__ = ['key']

    def __init__(self, from_, to):
        self.key = (from_, to)

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return 'Adaption(%r, %r)' % self.key



class Adapter(object):
    """A class for registering and using adapters.

    Adapters are callables that can convert from one type of object to another.

    >>> adapter = Adapter()
    >>> adapter.adapts(tuple, str, str)
    >>> adapter.adapt((1, 2, 3), str)
    '(1, 2, 3)'

    The target may be any hashable, comparable object:

    >>> adapter.adapts(tuple, 'List', list)
    >>> adapter.adapt((1, 2, 3), 'List')
    [1, 2, 3]

    Adaption is attempted for all base classes of the source type:

    >>> class A(object):
    ...   def __str__(self): return 'A()'
    >>> class B(A):
    ...   def __str__(self): return 'B()'
    >>> adapter.adapts(A, str, str)
    >>> adapter.adapt(A(), str)
    'A()'
    >>> adapter.adapt(B(), str)
    'B()'

    Unfortunately this does not work for old-style classes:

    >>> class C():
    ...   def __str__(self): return 'C()'
    >>> class D(C):
    ...   def __str__(self): return 'D()'
    >>> adapter.adapts(C, str, str)
    >>> adapter.adapt(C(), str)
    'C()'
    >>> adapter.adapt(D(), str)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    InvalidAdaption: ...

    Adaptions may also be removed:

    >>> adapter.remove(tuple, 'List')
    >>> adapter.adapt((1, 2, 3), 'List')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    InvalidAdaption: ...
    """
    def __init__(self, features=None):
        """Construct a new Adapter class.

        :param features: A FeatureBroker object. If not provided, an empty new
                         will be constructed.
        """
        self._features = features or FeatureBroker()

    def adapts(self, from_, to, adapter):
        """Register an adapter.

        :param from_: The data type to adapt from. Specify multiple source
                      types by passing a tuple or list of types.
        :param to: The destination "adaption key". This can be any hashable
                   object, not limited to but including, types, classes,
                   strings, integers, floats, etc.
        """
        if not isinstance(from_, (tuple, list)):
            from_ = [from_]
        for from_type in from_:
            for base in getattr(from_type, 'mro', lambda: [from_type])():
                if base is object:
                    continue
                self._features.provide(Adaption(base, to), adapter)

    def remove(self, from_, to):
        """Unregister an adapter.

        :param from_: The registered source type in an adaption.
        :param to: The registered destination adaption key.
        """
        self._features.remove(Adaption(from_, to))

    def adapt(self, from_, to):
        """Attempt to adapt object from_ to "to".

        :param from_: The object to adapt from. The class of this object is
                      used as the key when looking up the adapter.
        :param to: The registered destination adaption key.

        :returns: Adapted object. Typically but not necessarily of the same
                  type as "to".

        :raises InvalidAdaption: Could not perform the adaption.
        """
        cls = from_.__class__
        for from_type in getattr(cls, 'mro', lambda: [cls])():
            handle = Adaption(from_type, to)
            try:
                return self._features.require(handle)(from_)
            except UnknownFeature, e:
                pass
        else:
            raise InvalidAdaption(from_, to)


_adapter = Adapter(features)
adapt = _adapter.adapt
adapts = _adapter.adapts
remove = _adapter.remove


if __name__ == '__main__':
    import doctest
    doctest.testmod()
