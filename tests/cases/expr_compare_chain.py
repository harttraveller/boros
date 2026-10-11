# Chained comparisons: each operand evaluated at most once, short-circuit.
log = []


def v(x):
    log.append(x)
    return x


print(v(1) < v(2) < v(3), log)
log.clear()
print(v(1) < v(0) < v(3), log)
log.clear()
print(v(3) > v(2) > v(1) > v(0), log)
log.clear()
print(v(1) == v(1) != v(2) is not None, log)
log.clear()
print(v(1) < v(2) > v(5) < v(9), log)
log.clear()
print(v(2) in v([1, 2]) not in v([[1, 2]]), log)
log.clear()


class C:
    def __init__(self, n):
        self.n = n

    def __lt__(self, o):
        log.append(("lt", self.n, o.n))
        return "yes" if self.n < o.n else ""

    def __eq__(self, o):
        log.append(("eq", self.n, getattr(o, "n", o)))
        return self.n == getattr(o, "n", o)

    def __hash__(self):
        return self.n


a, b, c = C(1), C(2), C(3)
print(repr(a < b), repr(b < a))
print(repr(a < b < c), log)
log.clear()
print(repr(b < a < c), log)
log.clear()
r = a < b
print(type(r).__name__, r)
print(a == 1, 1 == a, a != 1, log)
log.clear()
print(C(5) in [1, 5], log)
log.clear()


# comparison returning non-bool in chain, last value returned
class R:
    def __gt__(self, o):
        return [o]


print(R() > 1, 0 < 1 and R() > 2, 0 < 1 < R() > 7)
x = 5
print(1 < x < 10, 1 < x > 10, x == 5 == 5.0 == 5 + 0j)
print([] == [] is not [], (1, 2) < (1, 3) <= (1, 3), "a" < "b" < "c")
print(None is None if False else True)
try:
    print(1 < "a")
except TypeError as e:
    print("TypeError:", e)
try:
    print([1] < (1,))
except TypeError as e:
    print("TypeError:", e)
try:
    print(a > 3)
except TypeError as e:
    print("TypeError:", e)
try:
    print(None < None)
except TypeError as e:
    print("TypeError:", e)
print(float("nan") == float("nan"), float("nan") != float("nan"))
n = float("nan")
print(n is n, [n] == [n], n in [n])
print(1 == 1.0 == True, 0 == False == 0.0 == -0.0 == 0j)
print((1, 2) == [1, 2], {1: 2} == {1: 2.0}, {1, 2} == frozenset([2, 1]))
print({1, 2} < {1, 2, 3}, {1, 2} <= {1, 2}, {3} > set(), {1} < {2})
