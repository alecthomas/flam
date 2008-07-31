"""Provide class-level "statements", functions applied to new classes on
creation.
"""


_statements = []


class Statement(object):
    """A Statement."""
    def __init__(self):
        _statements.append(self)

    def __call__(self, cls):
        """Apply statement to class."""


def statement(function):
    """Decorator transforming a function into a statement.

    >>> _statements
    []
    >>> def echo(cls):
    ...   print cls
    >>> echo = statement(echo)
    >>> echo  # doctest: +ELLIPSIS
    <function decorate at ...>
    """
    def decorate(*args, **kwargs):
        def apply(cls):
            return function(cls, *args, **kwargs)
        _statements.append(apply)
    return decorate


class StatementMeta(type):
    """Metaclass that applies statements to a class."""

    def __new__(cls, name, bases, d):
        new_class = type.__new__(cls, name, bases, d)
        while _statements:
            statement = _statements.pop(0)
            new_class = statement(new_class)
        return new_class


if __name__ == '__main__':
    import doctest
    doctest.testmod()
