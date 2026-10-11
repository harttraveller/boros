# Errors raised while building the arguments of a call with * / ** name the
# called function as "<module>.<qualname>()" (or "<name>()" for builtins).


def check(label, thunk):
    try:
        thunk()
    except TypeError as e:
        print(label, '-> TypeError:', e)


def f2(a, b=2):
    return (a, b)


class A:
    def m(self, x=1):
        return x


def outer():
    def inner(**kw):
        return kw
    return inner


inner = outer()

check('* not iterable', lambda: f2(*1))
check('* None', lambda: f2(*None))
check('** not mapping', lambda: f2(**1))
check('** list', lambda: f2(**[1]))
check('dup via two **', lambda: f2(1, **{'b': 1}, **{'b': 2}))
check('dup kw then **', lambda: f2(b=1, **{'b': 2}))
check('dup ** then kw', lambda: f2(**{'b': 1}, b=2))
check('method * not iterable', lambda: A().m(*5))
check('method dup', lambda: A().m(**{'x': 1}, x=2))
check('unbound method *', lambda: A.m(*3))
check('nested function dup', lambda: inner(**{'a': 1}, **{'a': 2}))
check('builtin * not iterable', lambda: print(*5))
check('builtin ** not mapping', lambda: print(**5))
check('builtin dup', lambda: print(**{'sep': 1}, sep=2))
check('class call * not iterable', lambda: A(*7))


class NotIterable:
    pass


class BadIter:
    def __iter__(self):
        raise TypeError('custom iter failure')


check('* interpreted non-iterable', lambda: f2(*NotIterable()))
check('* iterator raising TypeError', lambda: f2(*BadIter()))
check('** interpreted non-mapping', lambda: f2(**NotIterable()))
