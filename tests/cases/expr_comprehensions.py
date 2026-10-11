# All comprehension kinds, nested loops/conditions, scoping rules.
print([x * x for x in range(6)], [x for x in range(20) if x % 2 if x % 3])
print([(x, y) for x in range(3) for y in range(x)], [c for w in ["ab", "cd"] for c in w])
print([[y for y in range(x)] for x in range(4)])
print({x % 3 for x in range(10)} == {0, 1, 2}, {x: x * x for x in range(4)})
print({k: v for k, v in zip("abc", range(3)) if v != 1}, {(a, b): a * b for a in range(2) for b in range(2)})
g = (x + 1 for x in range(3))
print(type(g).__name__, next(g), list(g), list(g))
print(sum(x for x in range(10)), max((len(w), w) for w in "a bbb cc".split()))
print([x for x in range(10) if x > 2 if x < 7 for y in range(2) if y], [(i, j) for i in "ab" for j in range(2) if j or i == "a"])
# loop variable does not leak
x = "outer"
lst = [x for x in range(3)]
print(x, lst)
y = "keep"
_ = {y: 0 for y in range(2)}
_ = {y for y in range(2)}
_ = list(y for y in range(2))
print(y)
try:
    [undefined_q for undefined_q in range(2)]
    print(undefined_q)
except NameError as e:
    print("NameError:", e)
# first iterable evaluated in enclosing scope, eagerly for genexps
log = []


def src(n):
    log.append(("src", n))
    return range(n)


gen = (a for a in src(3))
print(log)
log.clear()
gen2 = (a * b for a in src(2) for b in src(2))
print(log, list(gen2), log)
log.clear()
try:
    bad = (q for q in 5)
except TypeError as e:
    print("TypeError:", e)


# closures over comprehension variables
fs = [lambda: i for i in range(3)]
print([f() for f in fs])
fs = [lambda i=i: i for i in range(3)]
print([f() for f in fs])


# comprehension inside function referencing locals and args
def fn(n, m=2):
    k = 10
    return [i * m + k for i in range(n)], {i: [j for j in range(i) if j != m] for i in range(n)}


print(fn(4))


def nested_scope():
    a = 1

    def inner():
        return [a + b for b in range(3)]

    return inner()


print(nested_scope())


# comprehension in class body: only the first iterable sees class scope
class C:
    vals = [1, 2, 3]
    sq = [v * v for v in vals]
    pairs = [(v, w) for v in vals for w in range(v)]
    total = sum(v for v in vals)
    try:
        bad = [vals[0] + v for v in range(2)]
    except NameError as e:
        err = str(e)


print(C.sq, C.pairs, C.total, C.err)
try:
    class D:
        n = 3
        r = [n for _ in range(2)]
except NameError as e:
    print("NameError:", e)


class E:
    factor = 3
    m = {k: k for k in range(factor)}
    s = {k for k in range(factor)}


print(E.m, E.s)
# nested comprehension with variable shadowing
print([[x for x in range(x)] for x in range(4)])
print([x for x in [x for x in range(3)]])
# generator laziness and early exit
def counted():
    for i in range(100):
        log.append(i)
        yield i


log.clear()
print(next(v for v in counted() if v > 2), log)
log.clear()
print(any(v > 1 for v in counted()), log)
# generator expression as sole argument
print(sorted(v % 3 for v in range(7)), "".join(c.upper() for c in "abc"))
# dict comprehension key/value order of evaluation
log.clear()


def k(v):
    log.append(("k", v))
    return v


def val(v):
    log.append(("v", v))
    return v


_ = {k(i): val(i) for i in range(2)}
print(log)
# comprehension with tuple unpack and starred targets
print([a + sum(r) for a, *r in [(1, 2, 3), (4,)]], {a: b for (a, b), c in [((1, 2), 3)]})
# comprehension over dict mutation error
d = {1: 1}
try:
    [d.setdefault(i + 10, 0) for i in d]
except RuntimeError as e:
    print("RuntimeError:", e)
# async-free: generator expression with closure over later-changing variable
z = 1
ge = (z * v for v in range(3))
z = 10
print(list(ge))
# conditional expression inside comprehension
print([v if v % 2 else -v for v in range(5)], [v for v in range(5) if (v if v > 2 else 0)])
# comprehension result types
print(type([v for v in ()]).__name__, type({v for v in ()}).__name__, type({v: v for v in ()}).__name__)
print([(lambda q: q * v)(2) for v in range(3)])
print([[i, j] for i in range(2) for j in range(i, 3) if i != j])
