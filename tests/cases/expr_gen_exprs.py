# Expressions containing yield inside generator functions (evaluation order,
# short-circuiting, walrus, unpacking, calls, comprehensions' first iterable).
log = []


def v(x):
    log.append(x)
    return x


def drive(g, sends):
    out = []
    try:
        out.append(next(g))
        for s in sends:
            out.append(g.send(s))
    except StopIteration as e:
        out.append(("ret", e.value))
    return out


def f(*a, **k):
    return a, k


def g1():
    x = [v(1), (yield "y"), v(3)]
    return x


def g2():
    r = v(f)(v("arg1"), (yield "y"), k=v("kw"))
    return r


def g3():
    x = v(1) if (yield "c") else v(2)
    y = (yield "a") and v("and-rhs")
    z = (yield "o") or v("or-rhs")
    return x, y, z


def g4():
    loc = 1
    loc += yield
    return loc


def g5():
    s = f"{v('a')}-{(yield 'fs')}-{v('c')}"
    return s


def g6():
    x = {**v({"a": 1}), "b": (yield), **v({"c": 3})}
    return x


def g7():
    if (n := (yield "w")) > 2:
        return "big", n
    return "small", n


def g8():
    a, *b = yield "unpack"
    c, d = (yield "p1"), (yield "p2")
    return a, b, c, d


def g9():
    res = [x * 2 for x in (yield "iter")]
    return res


def g10():
    t = 0
    while (x := (yield t)) is not None:
        t += x
    return t


def g11():
    ok = v(1) < (yield "cmp") < v(10)
    return ok


def g12():
    r = (yield "a") + (yield "b") * (yield "c")
    return r


def g13():
    items = []
    for i in range(3):
        items.append((i, (yield i)))
    return items


def g14():
    m = (yield "m")
    match m:
        case [x, y]:
            got = (yield x + y)
            return "seq", got
        case {"k": val}:
            return "map", val
        case _:
            return "other"


def g15():
    x = yield from iter([1, 2])
    y = [*(yield "star"), 0]
    return x, y


def g16():
    return (yield "first") if (yield "cond") else "no"


cases = [(g1, ["two"]), (g2, ["sent"]), (g3, [True, 0, ""]), (g3, [False, 5, 6]), (g4, [41]), (g5, ["B"]),
         (g6, [2]), (g7, [5]), (g7, [1]), (g8, [[1, 2, 3], 4, 5]), (g9, [[1, 2]]), (g10, [1, 2, 3, None]),
         (g11, [5]), (g11, [50]), (g12, [1, 2, 3]), (g13, ["a", "b", "c"]), (g14, [[1, 2], "sum"]),
         (g14, [{"k": 9}]), (g14, [5]), (g15, [None, None, (7, 8)]), (g16, [1, "x"]), (g16, [0])]
for g, sends in cases:
    print(g.__name__, drive(g(), sends), [x if not callable(x) else "<fn>" for x in log])
    log.clear()
