# Star-args in calls and displays; dict/set displays with unpacking.
def f(*args, **kwargs):
    return args, dict(sorted(kwargs.items()))


def g(a, b, c=3, *rest, d, e=5, **kw):
    return a, b, c, rest, d, e, kw


a = [1, 2]
t = (3, 4)
d1 = {"x": 1}
d2 = {"y": 2}
print(f(*a), f(*a, *t), f(0, *a, 9, *t, 10), f(*"ab", *range(2)))
print(f(**d1), f(**d1, **d2), f(z=0, **d1, w=9, **d2), f(*a, k=1, *t, **d1))
print(f(*[], **{}), f(*(), *[], *""), f(*iter([5, 6]), *{7: "x"}))
print(g(1, 2, d=4), g(*a, d=0), g(*a, 7, 8, 9, d=1, z=2), g(**{"a": 1, "b": 2, "d": 3}))
print(g(1, *[2], **{"d": 4, "q": 5}), g(*a, **d1, d=6), g(1, 2, 3, *t, **dict(d=7, e=8)))
print(f(*a, *a, *a), f(**{"k" + str(i): i for i in range(3)}))
print(f(*(i for i in range(3))), f(*map(str, range(3))))
print(max(*a, *t), min(*"zyx"), print(*a, sep="-", **{"end": "!\n"}))


class Mapping:
    def __init__(self, d):
        self.d = d

    def keys(self):
        return list(self.d)

    def __getitem__(self, k):
        return self.d[k] * 10


m = Mapping({"p": 1, "q": 2})
print(f(**m), {**m}, {**m, "p": 0}, {"q": -1, **m}, dict(**m))


class It:
    def __iter__(self):
        yield "i1"
        yield "i2"


print(f(*It()), [*It()], (*It(),), {*It()} == {"i1", "i2"})
# displays
print([*a, *t], [0, *a, 5, *t, 6], (*a,), (*a, *t), [*"hi", *range(3)])
print(sorted({*a, *t, 3}), sorted({*"aab"}), {*()} == set(), type({*()}).__name__)
print({**d1, **d2}, {**d1, "x": 99}, {"x": 99, **d1}, {**{}, **{}}, {"a": 1, **d1, "b": 2, **d2})
print({1: "a", True: "b", 1.0: "c"}, {**{1: "a"}, **{True: "b"}})
print([*[*[*a]]], [[*a], *[t]], {**{**d1}})
# evaluation order in displays and calls
log = []


def v(x):
    log.append(x)
    return x


f(v(1), *v([2]), v(3), k=v(4), **v({"j": 5}))
print(log)
log.clear()
_ = {v("k1"): v("v1"), **v({"k2": 0}), v("k3"): v("v3")}
print(log)
log.clear()
_ = [v(1), *v([2, 3]), v(4)]
print(log)
log.clear()
_ = {v(1), *v({2}), v(3)}
print(log)
log.clear()


def kwonly(*, a, b):
    return a - b


print(kwonly(**{"b": 1, "a": 5}), kwonly(b=2, **{"a": 3}))
# star in subscript / return / yield contexts
tup = (*a, 3)
print(tup)


def ret():
    return *a, *t


print(ret())


def gen():
    yield *a, 0


print(list(gen()))
for x in *a, *t:
    print(x, end=" ")
print()
print([x for x in (*a, 9)])
# str/bytes/dict as star sources
print([*"ab", *b"ab", *{"k": 1}, *{"k": 1}.values()])
