# __qualname__ of functions created inside comprehensions (list/set/dict
# comprehensions are inlined since Python 3.12, generator expressions add
# "<genexpr>." without "<locals>") and of functions declared global.
print([lambda: 0 for _ in range(1)][0].__qualname__)
print({k: lambda: 0 for k in range(1)}[0].__qualname__)
print({(lambda: 0) for _ in range(1)}.pop().__qualname__)
print(next(lambda: 0 for _ in range(1)).__qualname__)


def f():
    return ([lambda: 0 for _ in range(1)][0].__qualname__,
            next(lambda: 0 for _ in range(1)).__qualname__)


print(f())


class C:
    fs = [lambda: 0 for _ in range(1)]

    def m(self):
        return [lambda: 0 for _ in range(1)][0]


print(C.fs[0].__qualname__, C().m().__qualname__)


def h():
    return [(lambda: (lambda: 0))() for _ in range(1)][0].__qualname__


print(h())


def gq():
    return (x for x in []).__qualname__, (x for x in []).__name__


print(gq(), (x for x in []).__qualname__)


def declares_global():
    global made_global

    def made_global():
        pass

    class GlobalClass:
        pass
    return made_global.__qualname__, GlobalClass.__qualname__


print(declares_global())
