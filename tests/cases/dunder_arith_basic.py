# Binary arithmetic special methods on interpreted classes, reflected
# operands, mixing with ints, NotImplemented fallback and error messages.


class V:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return 'V(%r)' % (self.x,)

    def _v(self, o):
        return o.x if isinstance(o, V) else o

    def __add__(self, o): return V(self.x + self._v(o))
    def __sub__(self, o): return V(self.x - self._v(o))
    def __mul__(self, o): return V(self.x * self._v(o))
    def __truediv__(self, o): return V(self.x / self._v(o))
    def __floordiv__(self, o): return V(self.x // self._v(o))
    def __mod__(self, o): return V(self.x % self._v(o))
    def __pow__(self, o, mod=None):
        if mod is None:
            return V(self.x ** self._v(o))
        return V(pow(self.x, self._v(o), mod))
    def __lshift__(self, o): return V(self.x << self._v(o))
    def __rshift__(self, o): return V(self.x >> self._v(o))
    def __and__(self, o): return V(self.x & self._v(o))
    def __or__(self, o): return V(self.x | self._v(o))
    def __xor__(self, o): return V(self.x ^ self._v(o))
    def __matmul__(self, o): return ('matmul', self.x, self._v(o))
    def __divmod__(self, o): return ('divmod', divmod(self.x, self._v(o)))

    def __radd__(self, o): return ('radd', o, self.x)
    def __rsub__(self, o): return ('rsub', o, self.x)
    def __rmul__(self, o): return ('rmul', o, self.x)
    def __rtruediv__(self, o): return ('rtruediv', o, self.x)
    def __rfloordiv__(self, o): return ('rfloordiv', o, self.x)
    def __rmod__(self, o): return ('rmod', o, self.x)
    def __rpow__(self, o, mod=None): return ('rpow', o, self.x, mod)
    def __rlshift__(self, o): return ('rlshift', o, self.x)
    def __rrshift__(self, o): return ('rrshift', o, self.x)
    def __rand__(self, o): return ('rand', o, self.x)
    def __ror__(self, o): return ('ror', o, self.x)
    def __rxor__(self, o): return ('rxor', o, self.x)
    def __rmatmul__(self, o): return ('rmatmul', o, self.x)
    def __rdivmod__(self, o): return ('rdivmod', o, self.x)


a = V(13)
b = V(4)
print(a + b, a - b, a * b, a / b, a // b, a % b, a ** b)
print(a << 2, a >> 1, a & b, a | b, a ^ b, a @ b, divmod(a, b))
print(pow(a, 2), pow(a, 2, 5))
print(a + 1, a - 1, a * 2, a / 2, a // 2, a % 5, a ** 2)
print(1 + a, 1 - a, 2 * a, 2 / a, 2 // a, 5 % a, 2 ** a)
print(1 << a, 1 >> a, 1 & a, 1 | a, 1 ^ a, 1 @ a, divmod(7, a))
print(pow(2, a))
print(2.5 + a, 'x' * a, [1] + a, (1,) * a)

# operator module goes through the same protocol
import operator
print(operator.add(a, 1), operator.add(1, a), operator.mul(3, a), operator.matmul(a, b))


# NotImplemented fallback between two unrelated classes
class L:
    def __init__(self, tag):
        self.tag = tag

    def __add__(self, o):
        print('L.__add__', self.tag, type(o).__name__)
        return NotImplemented

    def __sub__(self, o):
        print('L.__sub__')
        return NotImplemented


class R:
    def __radd__(self, o):
        print('R.__radd__', type(o).__name__)
        return 'R-won'

    def __rsub__(self, o):
        print('R.__rsub__')
        return NotImplemented


print(L('l') + R())
try:
    L('l') - R()
except TypeError as e:
    print('TypeError:', e)


# same class: the reflected method is NOT tried
class Same:
    def __add__(self, o):
        print('Same.__add__')
        return NotImplemented

    def __radd__(self, o):
        print('Same.__radd__ (should not happen)')
        return 'bad'


try:
    Same() + Same()
except TypeError as e:
    print('TypeError:', e)


# plain classes and error messages
class P:
    pass


cases = [
    ('P() + 1', lambda: P() + 1),
    ('1 + P()', lambda: 1 + P()),
    ('P() - P()', lambda: P() - P()),
    ('P() * 2.0', lambda: P() * 2.0),
    ("P() % 's'", lambda: P() % 's'),
    ('P() / 1', lambda: P() / 1),
    ('P() // 1', lambda: P() // 1),
    ('P() ** 2', lambda: P() ** 2),
    ('2 ** P()', lambda: 2 ** P()),
    ('P() << 1', lambda: P() << 1),
    ('P() >> 1', lambda: P() >> 1),
    ('P() & 1', lambda: P() & 1),
    ('P() | 1', lambda: P() | 1),
    ('P() ^ 1', lambda: P() ^ 1),
    ('P() @ 1', lambda: P() @ 1),
    ('1 @ P()', lambda: 1 @ P()),
    ('divmod(P(), 1)', lambda: divmod(P(), 1)),
    ('divmod(1, P())', lambda: divmod(1, P())),
    ('pow(P(), 2, 3)', lambda: pow(P(), 2, 3)),
    ('-P()', lambda: -P()),
    ('+P()', lambda: +P()),
    ('~P()', lambda: ~P()),
    ('abs(P())', lambda: abs(P())),
    ("L(1) + 1", lambda: L(1) + 1),
    ('None + P()', lambda: None + P()),
    ('P() + None', lambda: P() + None),
    ('1.5 - P()', lambda: 1.5 - P()),
]
for label, f in cases:
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


# unary operators
class U:
    def __neg__(self): return 'neg'
    def __pos__(self): return 'pos'
    def __invert__(self): return 'inv'
    def __abs__(self): return 'abs'


u = U()
print(-u, +u, ~u, abs(u), operator.neg(u), operator.invert(u))

# special methods are looked up on the type, not the instance
p = P()
p.__add__ = lambda o: 'instance attr'
try:
    p + 1
except TypeError as e:
    print('TypeError:', e)
print(p.__add__(1))

# assigning a special method on the class after creation takes effect
P.__add__ = lambda self, o: ('late add', o)
print(P() + 5)
del P.__add__
try:
    P() + 5
except TypeError as e:
    print('TypeError:', e)
