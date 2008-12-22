from features import *
from statements import *


class ComponentMeta(type):
    def __new__(cls, name, bases, d):
        new_cls = type.__new__(cls, name, bases, d)
        if '__init__' in d:
            def maybe_init(self):
                print 'INIT'
                maybe_init._original(self)
            maybe_init._original = d['__init__']
            new_cls.__init__ = maybe_init
        return new_cls


class Component(object):
    __metaclass__ = ComponentMeta


@statement
def implements(cls, *args):
    print cls, args
    cls._implements = args


class A(Component):
    implements(1, 2)

    def __init__(self):
        print 'foo'

print A

A()
print A._implements
