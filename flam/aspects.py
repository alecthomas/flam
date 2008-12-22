"""A simple Aspect-Oriented Programming API.

This API implements a clean, non-intrusive method of applying additional
behaviour to existing objects, classes and functions.

>>> class OrbitalLaser(object):
...   power = 11
...
...   def __init__(self, power=None):
...     self.power = power or OrbitalLaser.power
...
...   def aim(self, at):
...     self.target = at
...
...   def fire(self):
...     return self.target

Creating an Aspect is simple. Inherit from Aspect and define the methods to
intercept. To chain to the next aspect and finally the original object, call
self.next.<method>(...):

>>> class RedirectLaser(Aspect):
...   def fire(self):
...     real_target = self.next.target
...     self.next.target = 'Sun'
...     try:
...       result = self.next.fire()
...     finally:
...       self.next.target = real_target
...     return result

Then apply the aspect to the object:

>>> laser = OrbitalLaser()
>>> laser = RedirectLaser(laser)

Methods and attributes that are not intercepted are unaffected:

>>> hasattr(laser, 'fire')
True
>>> hasattr(laser, 'aim')
True
>>> hasattr(laser, 'target')
False
>>> laser.aim('Moon')
>>> laser.target
'Moon'
>>> hasattr(laser, 'target')
True
>>> laser.power
11
>>> laser.explode
Traceback (most recent call last):
...
AttributeError: 'OrbitalLaser' object has no attribute 'explode'

As are attribute assignments:

>>> laser.target = 'Jupiter'
>>> laser.target
'Jupiter'

Aspect methods are called as expected:

>>> laser.fire()
'Sun'
>>> laser.target
'Jupiter'

Aspects can also be applied to classes:

>>> RealOrbitalLaser = OrbitalLaser
>>> OrbitalLaser = RedirectLaser(OrbitalLaser)
>>> OrbitalLaser
<class '__main__.OrbitalLaser'>
>>> OrbitalLaser.power
11
>>> laser = OrbitalLaser(power=10)
>>> laser.aim('Moon')
>>> laser.fire()
'Sun'
>>> laser.power
10

Note: As with instances, applying aspects to classes does not modify the
original class. Due to this, aspect-decorated objects do not conform to "is-a"
relationship checks. That is, isinstance(decorated, cls) and
issubclass(decorated_cls, cls) will not work.

That being said, the "weave" function can be used to inject aspects into a
class directly (NOTE: Not yet implemented):

>>> OrbitalLaser = RealOrbitalLaser
>>> OrbitalLaser = weave(OrbitalLaser, RedirectLaser)
>>> issubclass(OrbitalLaser, RealOrbitalLaser)  # doctest: +SKIP
True
>>> laser = OrbitalLaser()
>>> laser.aim('Moon')
>>> laser.fire()  # doctest: +SKIP
'Sun'

To apply aspects to functions rather than objects or classes, intercept the
__call__ function:

>>> def fire_laser(at, power=11):
...   return 'Fired laser with power %i at %s' % (power, at)
>>> class DecreaseLaserPower(Aspect):
...   def __call__(self, at):
...     return self.next(at, power=5)

Then apply the aspect as usual:

>>> lower_powered_laser = DecreaseLaserPower(fire_laser)
>>> fire_laser('Moon')
'Fired laser with power 11 at Moon'
>>> lower_powered_laser('Moon')
'Fired laser with power 5 at Moon'

This doesn't have any real advantages over decorators, but it may be nice
for uniformity.
"""


from inspect import isclass, isroutine


def weave(cls, aspect, *args, **kwargs):
    """Weave an aspect into a class."""
    def __new__(cls, *args, **kwargs):
        # TODO Complete this.
#        aspects = getattr(cls, '__aspects__', None)
#        for aspect_cls in reversed(aspects):
#            aspect = aspect_
#            for method in aspect.__dict__:
        return object.__new__(cls, *args, **kwargs)

    cls.__new__ = classmethod(__new__)
    if not hasattr(cls, '__aspects__'):
        cls.__aspects__ = []
    cls.__aspects__.append((aspect, args, kwargs))
    return cls


class AspectBase(object):
    def __init__(self, next, **attributes):
        self.next = next
        self.__dict__.update(attributes)

    def __setattr__(self, key, value):
        if 'next' in self.__dict__:
            setattr(self.next, key, value)
        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, key):
        assert 'next' in self.__dict__, \
            'AspectBase(next) must be called before accessing aspect attributes'
        if key in self.__dict__:
            return object.__getattr__(self, key)
        next = getattr(self.next, key)
        if callable(next):
            def proxy_next_method(*args, **kwargs):
                return self.__callnext__(next, *args, **kwargs)
            return proxy_next_method
        else:
            return next

    def __callnext__(self, _method, *args, **kwargs):
        """Hook when an method is not explicitly intercepted by the aspect."""
        return _method(*args, **kwargs)

    def __repr__(self):
        return repr(self.next)

    def __str__(self):
        return str(self.next)



class DeferredAspect(AspectBase):
    """Wrap a class in an aspect.

    Call the resulting object to construct the real object and apply the
    aspect.
    """

    def __init__(self, aspect, next, *args, **kwargs):
        super(DeferredAspect, self).__init__(
            next, aspect=aspect, args=args, kwargs=kwargs,
            )

    def __call__(self, *args, **kwargs):
        next = self.next(*args, **kwargs)
        return self.aspect(next, *self.args, **self.kwargs)


class Aspect(AspectBase):
    def __new__(cls, next, *args, **kwargs):
        if isclass(next):
            return DeferredAspect(cls, next, *args, **kwargs)
        else:
            return super(Aspect, cls).__new__(cls, next, *args, **kwargs)



if __name__ == '__main__':
    import doctest
    doctest.testmod()
