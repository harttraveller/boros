# Single / multiple inheritance, diamond MRO, MRO conflicts.

def names(c):
    return [k.__name__ for k in c.__mro__]


class A:
    def who(self):
        return 'A'

    def hello(self):
        return 'hello from A'


class B(A):
    def who(self):
        return 'B'


class C(A):
    def who(self):
        return 'C'

    def only_c(self):
        return 'only C'


class D(B, C):
    pass


print(names(A))
print(names(B))
print(names(D))
print([k.__name__ for k in D.mro()])
print(D().who(), D().only_c(), D().hello())
print([b.__name__ for b in D.__bases__])
print(D.__base__.__name__, A.__base__.__name__, object.__base__)
print(A.__bases__ == (object,))


# a deeper, classic C3 example
class O: pass
class F(O): pass
class E(O): pass
class Dd(O): pass
class Cc(Dd, F): pass
class Bb(Dd, E): pass
class Aa(Bb, Cc, E): pass

print(names(Aa))


# method resolution follows the MRO even for methods defined after the fact
def late(self):
    return 'late ' + type(self).__name__

C.late = late
print(D().late())
del C.late
print(hasattr(D(), 'late'))

# subclass overriding then calling base method explicitly
class Base:
    def greet(self, x):
        return 'Base.greet(%s)' % x


class Derived(Base):
    def greet(self, x):
        return 'Derived+' + Base.greet(self, x)


print(Derived().greet(3))

# inheritance from multiple unrelated classes with same attribute
class X:
    tag = 'X'
class Y:
    tag = 'Y'
class XY(X, Y):
    pass
class YX(Y, X):
    pass
print(XY.tag, YX.tag, XY().tag)

# inconsistent MRO
try:
    class Bad(A, B):
        pass
except TypeError as e:
    print('TypeError:', e)


# inheriting from a non-class
try:
    class Bad3(3):
        pass
except TypeError as e:
    print('TypeError:', type(e).__name__)

# issubclass across the diamond
print(issubclass(D, A), issubclass(D, (int, C)), issubclass(A, D))
print(isinstance(D(), B), isinstance(D(), C), isinstance(B(), C))
