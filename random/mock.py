"""An intuitive record/replay mock object.

First, use the mock as you would the real object:

>>> mopen = Mock()
>>> fd = mopen('/etc/passwd')

One exception to this is return values, which are specified by defining the
"returns" attributes:

>>> fd.read().returns = 'This is a test'
>>> fd.close()

Once all the functions that your test will use have been called, call replay()
to prime the mock for testing:

>>> mopen.replay()

Then patch our mock over the real function:

>>> real_open = open
>>> open = mopen

And run your test with the mocked object:

>>> fd = open('/etc/passwd')
>>> assert fd.read() == 'This is a test'
>>> fd.close()

If an unexpected call is made to any part of the Mock an exception is thrown:

>>> fd = open('foo')
Traceback (most recent call last):
...
InvalidMockReplay: Unexpected Mock access.

Finally, we unpatch our mock:

>>> open = real_open
"""


UNDEFINED = object()


class Mock(object):
    def __init__(self, name=None):
        self._history = []
        self._recording = True
        self._name = name
        self._returns = UNDEFINED

    def replay(self):
        self._recording = False

    def __getattr__(self, key):
        mock = Mock()
        self._history.setdefault(key, [])
        self._history[key].append(mock)
        return mock

    def __setattr__(self, key, value):


    def _set_returns(self, value):
        self._returns = value

    def _get_returns(self):
        try:
            return self._returns
        except AttributeError:
            raise AttributeError('returns')

    returns = property(lambda s: s._get_returns(),
                       lambda s, v: s._set_returns(v))
