# In-place operators: __iadd__ & co, fallback to the binary method and to
# the reflected method, returning None/self, and error messages.


class Acc:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return 'Acc(%r)' % (self.v,)

    def __iadd__(self, o):
        print('iadd', o)
        self.v += o
        return self

    def __isub__(self, o):
        print('isub', o)
        return NotImplemented

    def __sub__(self, o):
        print('sub', o)
        return Acc(self.v - o)

    def __imul__(self, o):
        print('imul returns None')

    def __ipow__(self, o):
        return Acc(self.v ** o)

    def __imatmul__(self, o):
        return 'imatmul'

    def __ior__(self, o):
        return Acc(('ior', self.v, o))

    def __ilshift__(self, o):
        return Acc(self.v << o)


a = Acc(10)
orig = a
a += 5
print(a, a is orig)
a -= 3
print(a, a is orig)
a *= 2
print(a)
b = Acc(3)
b **= 2
print(b)
b @= 1
print(b)
c = Acc(1)
c |= 2
print(c)
c = Acc(1)
c <<= 4
print(c)


# fallback chain: no __iadd__ -> __add__ -> other's __radd__
class OnlyAdd:
    def __init__(self, v):
        self.v = v

    def __add__(self, o):
        print('OnlyAdd.__add__')
        return OnlyAdd(self.v + o)


x = OnlyAdd(1)
y = x
x += 10
print(x.v, y.v, x is y)


class OnlyRadd:
    def __radd__(self, o):
        print('OnlyRadd.__radd__', o)
        return 'radd result'


n = 5
n += OnlyRadd()
print(n)


# in-place on attributes and subscripts
class Box:
    pass


bx = Box()
bx.acc = Acc(1)
bx.acc += 1
print(bx.acc)
lst = [Acc(100)]
lst[0] += 1
print(lst)
d = {'k': Acc(0)}
d['k'] += 7
print(d)


# list += user iterable uses list.__iadd__ (extend)
class Count:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return iter(range(self.n))


L = [9]
L2 = L
try:
    L += Count(3)
except TypeError as e:
    print('TypeError:', e)
print(L, L is L2)


def local_list_iadd():
    m = [1]
    m2 = m
    m += Count(2)
    m *= 2
    return m, m is m2


try:
    print(local_list_iadd())
except TypeError as e:
    print('TypeError:', e)

ba = bytearray(b'x')
try:
    ba += Count(0)
except TypeError as e:
    print('TypeError:', e)


# error messages
class P:
    pass


def attempt(label, f):
    try:
        print(label, '->', f())
    except TypeError as e:
        print(label, '-> TypeError:', e)


def iadd_p():
    p = P()
    p += 1
    return p


def imul_str():
    s = 'ab'
    s *= P()
    return s


def ipow_p():
    p = P()
    p **= 2
    return p


def ifloordiv_p():
    p = P()
    p //= P()
    return p


def imatmul_p():
    p = P()
    p @= P()
    return p


attempt('p += 1', iadd_p)
attempt("s *= P()", imul_str)
attempt('p **= 2', ipow_p)
attempt('p //= P()', ifloordiv_p)
attempt('p @= P()', imatmul_p)


def isub_acc():
    a = Acc(1)
    a -= 'x'
    return a


attempt("Acc(1) -= 'x'", isub_acc)
