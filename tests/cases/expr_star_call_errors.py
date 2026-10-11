# Error messages for bad * / ** arguments in calls name the callee.
def f(*a, **k):
    return a, k


def g(x, y=0):
    return x, y


class C:
    def meth(self, *a, **k):
        return a


tests = [
    lambda: f(*5),
    lambda: f(*None),
    lambda: print(*5),
    lambda: g(**5),
    lambda: f(**[1]),
    lambda: g(**{"x": 1}, x=2),
    lambda: g(x=1, **{"x": 2}),
    lambda: f(**{"a": 1}, **{"a": 2}),
    lambda: C().meth(*7),
    lambda: C.meth(C(), **3),
    lambda: len(*1),
    lambda: g(1, **{"x": 1}),
    lambda: g(**{1: 2}),
    lambda: g(*[1], **{"y": 2, "z": 3}),
]
for t in tests:
    try:
        t()
    except TypeError as e:
        print("TypeError:", e)
