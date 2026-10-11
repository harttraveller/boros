# The __code__ attributes that programs commonly inspect.
import inspect


def f(a, b=2, /, c=3, *args, d, e=5, **kw):
    return a


def g(x, y):
    return x + y


def gen():
    yield 1


lam = lambda p, q=1: p


class K:
    def m(self, v):
        return v


co = f.__code__
print(co.co_name, co.co_qualname, co.co_argcount, co.co_posonlyargcount, co.co_kwonlyargcount)
print(co.co_varnames)
print(g.__code__.co_varnames, g.__code__.co_argcount, g.__code__.co_name)
print(lam.__code__.co_name, lam.__code__.co_argcount, lam.__code__.co_varnames)
print(K.m.__code__.co_qualname, K().m.__code__.co_varnames)
print(bool(co.co_flags & inspect.CO_VARARGS), bool(co.co_flags & inspect.CO_VARKEYWORDS))
print(bool(g.__code__.co_flags & inspect.CO_VARARGS), bool(gen.__code__.co_flags & inspect.CO_GENERATOR))
print(co.co_filename.endswith('func_code_object.py'), co.co_firstlineno, g.__code__.co_firstlineno)


# the classic "count required arguments" idiom
def required(fn):
    c = fn.__code__
    return c.co_argcount - len(fn.__defaults__ or ())


print(required(f), required(g), required(lam))
