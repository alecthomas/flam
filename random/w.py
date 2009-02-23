def decorate(a):
    def inner(f):
        def decorated(*args, **kwargs):
            return f(a, *args, **kwargs)
        return decorated
    return inner


@decorate(3)
def func(a, b, c):
    print a, b, c


func(1, 2)
