# functools.wraps on interpreted functions (fails at level 2 when host
# functools writes __module__ etc. onto the inner interpreter's objects).
import functools


def deco(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        return f(*a, **kw) + 1
    return wrapper


@deco
def g(x):
    """g doc"""
    return x


class K:
    @deco
    def m(self, y):
        """m doc"""
        return y * 2


print(g(1), g.__name__, g.__doc__, g.__wrapped__(1), g.__qualname__)
print(K().m(3), K.m.__name__, K.m.__qualname__, K.m.__doc__)
