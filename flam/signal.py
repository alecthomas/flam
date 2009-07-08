# encoding: utf-8
#
# Copyright (C) 2009 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

"""Signal/event handling framework.

A Signal is an object for relaying events to a set of receivers.
"""


from flam import Error


class Error(Error):
    """Base event exception."""


class UnboundTrigger(Error):
    """A Trigger was not associated with a callback when triggered."""


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


class Trigger(Signal):
    """A trigger is a :class:`Signal` with exactly one callback.

    Create a new trigger:

    >>> application_version = Trigger()

    Bind it to a callback:

    >>> @application_version.connect
    ... def get_version():
    ...   return '0.1'

    Then use it as you would a :class:`Signal`:

    >>> application_version()
    '0.1'

    If multiple callbacks are bound to a Trigger, only the last one is called
    and its result returned:

    >>> @application_version.connect
    ... def get_version_2():
    ...   return '0.2'
    >>> application_version()
    '0.2'

    Callbacks can also be unbound:

    >>> application_version.disconnect(get_version_2)
    >>> application_version()
    '0.1'
    """

    def __init__(self, must_be_bound=True):
        """Create a new Trigger.

        :param must_be_bound: If True, require that a callback be bound to the
                              Trigger.
        """
        super(Trigger, self).__init__()
        self._must_be_bound = must_be_bound

    def __call__(self, *args, **kwargs):
        if not self._callbacks:
            if self._must_be_bound:
                raise UnboundTrigger
            return None
        return self._callbacks[-1](*args, **kwargs)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
