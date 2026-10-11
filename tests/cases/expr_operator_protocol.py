# Operator dispatch on user classes: forward, reflected, in-place, NotImplemented fallbacks.
log = []


class V:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return "V(%r)" % (self.v,)

    def __add__(self, o):
        log.append("add")
        if isinstance(o, V):
            return V(self.v + o.v)
        if isinstance(o, int):
            return V(self.v + o)
        return NotImplemented

    def __radd__(self, o):
        log.append("radd")
        if isinstance(o, int):
            return V(o + self.v)
        return NotImplemented

    def __sub__(self, o):
        return V(self.v - (o.v if isinstance(o, V) else o))

    def __rsub__(self, o):
        return V(o - self.v)

    def __mul__(self, o):
        return V(self.v * o)

    __rmul__ = __mul__

    def __truediv__(self, o):
        return V(self.v / o)

    def __floordiv__(self, o):
        return V(self.v // o)

    def __mod__(self, o):
        return V(self.v % o)

    def __divmod__(self, o):
        return (self // o, self % o)

    def __pow__(self, o, mod=None):
        return V(pow(self.v, o, mod))

    def __rpow__(self, o):
        return V(o ** self.v)

    def __matmul__(self, o):
        return "matmul"

    def __rmatmul__(self, o):
        return "rmatmul"

    def __lshift__(self, o):
        return V(self.v << o)

    def __rshift__(self, o):
        return V(self.v >> o)

    def __and__(self, o):
        return V(self.v & o)

    def __or__(self, o):
        return V(self.v | o)

    def __xor__(self, o):
        return V(self.v ^ o)

    def __rand__(self, o):
        return "rand"

    def __neg__(self):
        return V(-self.v)

    def __pos__(self):
        return V(+self.v)

    def __invert__(self):
        return V(~self.v)

    def __abs__(self):
        return V(abs(self.v))

    def __eq__(self, o):
        return isinstance(o, V) and self.v == o.v

    def __lt__(self, o):
        return self.v < (o.v if isinstance(o, V) else o)

    def __hash__(self):
        return hash(self.v)


a, b = V(5), V(3)
print(a + b, a + 1, 1 + a, a - b, a - 1, 10 - a, a * 2, 2 * a, a / 2, a // 2, a % 3, divmod(a, 2))
print(a ** 2, pow(a, 2, 3), 2 ** a, a @ b, 1 @ a, a << 1, a >> 1, a & 3, a | 8, a ^ 1, 1 & a)
print(-a, +a, ~a, abs(V(-4)), a == V(5), a != V(5), a != b, a < b, b < a, a > b, 1 > a, 9 > a, log)
log.clear()
try:
    a + "s"
except TypeError as e:
    print("TypeError:", e, log)
try:
    a <= b
except TypeError as e:
    print("TypeError:", e)


class W(V):
    def __radd__(self, o):
        log.append("W.radd")
        return "W.radd wins"


log.clear()
print(V(1) + W(2), log)
log.clear()


class W2(V):
    pass


print(V(1) + W2(2), log)
log.clear()


class Cmp:
    def __init__(self, n):
        self.n = n

    def __eq__(self, o):
        log.append(("eq", self.n))
        return NotImplemented

    def __gt__(self, o):
        log.append(("gt", self.n))
        return "gt-result"


c1, c2 = Cmp(1), Cmp(2)
print(c1 == c2, log)
log.clear()
print(c1 != c2, c1 == c1, log)
log.clear()
print(c1 < c2, log)
log.clear()
print(5 < c1, log)
log.clear()


class OnlyEq:
    def __init__(self, k):
        self.k = k

    def __eq__(self, o):
        return isinstance(o, OnlyEq) and o.k == self.k


print(OnlyEq(1) != OnlyEq(1), OnlyEq(1) != OnlyEq(2), OnlyEq(1) == 1, 1 != OnlyEq(1))
try:
    hash(OnlyEq(1))
except TypeError as e:
    print("TypeError:", e)


class Acc:
    def __init__(self):
        self.items = []

    def __iadd__(self, o):
        self.items.append(o)
        return self

    def __imul__(self, o):
        return NotImplemented

    def __mul__(self, o):
        return "mul fallback"

    def __ior__(self, o):
        return "ior result"


acc = Acc()
acc0 = acc
acc += 1
acc += 2
print(acc.items, acc is acc0)
acc *= 3
print(acc)
x = Acc()
x |= 5
print(x)
try:
    y = Acc()
    y -= 1
except TypeError as e:
    print("TypeError:", e)
try:
    y = Acc()
    y @= 1
except TypeError as e:
    print("TypeError:", e)
try:
    -Acc()
except TypeError as e:
    print("TypeError:", e)
try:
    ~Acc()
except TypeError as e:
    print("TypeError:", e)
try:
    abs(Acc())
except TypeError as e:
    print("TypeError:", e)
try:
    Acc() < Acc()
except TypeError as e:
    print("TypeError:", e)
try:
    Acc() ** 2
except TypeError as e:
    print("TypeError:", e)
try:
    divmod(Acc(), 1)
except TypeError as e:
    print("TypeError:", e)
print(Acc() == Acc(), Acc() != Acc(), acc == acc)


# __bool__ / __len__ in operators
class Z:
    def __len__(self):
        return 0


print(Z() or "fallback", not Z(), bool(Z()))
# operator module functions on instances
import operator

print(operator.add(a, b), operator.mul(2, a), operator.neg(a), operator.lt(b, a), operator.iadd([1], [2]))
print(sorted([V(3), V(1), V(2)]), max(V(3), V(7)), min([V(4), V(2)]))
print(sum([V(1), V(2)], V(0)), sum([V(1), V(2)]))
