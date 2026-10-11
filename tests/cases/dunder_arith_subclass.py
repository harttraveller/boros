# Reflected-operand priority for subclasses in binary operators.


class A:
    def __init__(self, n):
        self.n = n

    def __add__(self, o):
        print('A.__add__', self.n, o.n if isinstance(o, A) else o)
        return 'A+'

    def __radd__(self, o):
        print('A.__radd__', self.n)
        return 'A r+'

    def __mul__(self, o):
        print('A.__mul__')
        return NotImplemented

    def __rmul__(self, o):
        print('A.__rmul__')
        return NotImplemented


class B(A):
    def __radd__(self, o):
        print('B.__radd__', self.n)
        return 'B r+'

    def __rmul__(self, o):
        print('B.__rmul__')
        return 'B r*'


class C(A):
    # inherits __radd__ unchanged: no priority
    pass


class D(A):
    def __radd__(self, o):
        print('D.__radd__ -> NotImplemented')
        return NotImplemented


print(A(1) + B(2))   # B overrides __radd__: tried first
print(A(1) + C(2))   # C does not override: A.__add__ first
print(B(1) + A(2))   # left is subclass: normal order
print(A(1) * B(2))   # B.__rmul__ first
print(A(1) + D(2))   # D.__radd__ first, returns NotImplemented, then A.__add__


class E(A):
    def __add__(self, o):
        print('E.__add__')
        return NotImplemented

    def __radd__(self, o):
        print('E.__radd__')
        return NotImplemented


try:
    A(1) * E(2)
except TypeError as e:
    print('TypeError:', e)

try:
    print(E(1) + E(2))
except TypeError as e:
    print('TypeError:', e)


class F(A):
    def __mul__(self, o):
        print('F.__mul__')
        return NotImplemented

    def __rmul__(self, o):
        print('F.__rmul__')
        return NotImplemented


# both sides return NotImplemented: subclass reflected tried first, then
# the left operand, and the reflected method is not retried
try:
    A(1) * F(2)
except TypeError as e:
    print('TypeError:', e)


# a subclass that adds a reflected method its base does not have
class G:
    def __sub__(self, o):
        print('G.__sub__')
        return NotImplemented


class H(G):
    def __rsub__(self, o):
        print('H.__rsub__')
        return 'H r-'


print(G() - H())


# subclass priority with a host base type
class MyInt(int):
    def __radd__(self, o):
        print('MyInt.__radd__', o)
        return 'myint r+'

    def __rsub__(self, o):
        print('MyInt.__rsub__', o)
        return NotImplemented


print(5 + MyInt(3))
try:
    print(5 - MyInt(3))   # MyInt.__rsub__ declines, int.__sub__ succeeds
except TypeError as e:
    print('TypeError:', e)
print(MyInt(3) + 5)
print(MyInt(3) * 2, type(MyInt(3) * 2).__name__)


class MyFloat(float):
    def __rtruediv__(self, o):
        return ('rtruediv', o, float(self))


print(1.0 / MyFloat(2.0))
print(1 / MyFloat(4.0))
