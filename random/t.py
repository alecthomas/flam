from adaption import *

class A(object): pass
class B(A): pass

adapts(A, str, str)

print adapt(A(), str)
print adapt(B(), str)
