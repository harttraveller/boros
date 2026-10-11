# Class bodies: class variables are not visible inside methods or nested
# scopes (comprehensions, lambdas, nested classes); the first iterable of a
# comprehension is evaluated in the class body.
x = 'global x'


class A:
    x = 'class x'

    def m(self):
        return x
    y = x
    lst = [x for _ in range(2)]
    first = [i * 2 for i in range(len(x))][:2]
    gen = list(x for _ in range(1))
    lam = (lambda: x)()

    def default(self, d=x):
        return d


print(A().m(), A.y, A.lst, A.first, A.gen, A.lam, A().default())


class B:
    v = 3
    try:
        w = [v for _ in range(2)]
    except NameError as e:
        err = str(e)
    ok = [i for i in range(v)]
    d = {k: k for k in range(v)}
    xs = [1, 2]
    try:
        pairs = [(a, b) for a in xs for b in xs]
    except NameError as e:
        pairs = 'NameError: %s' % e
    ok2 = [(a, b) for a in xs for b in [3, 4]]
    try:
        cond = [a for a in range(3) if a in xs]
    except NameError as e:
        cond = 'NameError: %s' % e
    lam2 = lambda self, d=xs: d


print(B.err, B.ok, B.d, B.pairs, B.ok2, B.cond, B().lam2())


class E:
    n = 5

    def m(self):
        try:
            return n
        except NameError as e:
            return 'NameError: ' + str(e)

    def via_self(self):
        return self.n, type(self).n, E.n


print(E().m(), E().via_self())


# nested classes cannot see the enclosing class's attributes
class Outer:
    o = 10

    class Inner:
        try:
            i = o
        except NameError as e:
            i = 'NameError: ' + str(e)


print(Outer.Inner.i)


# class body inside a function: free names come from the function
def f():
    ys = [5]
    loc = 'func local'

    class C:
        comp = [y for y in ys]
        comp2 = [ys for _ in range(1)]
        a = loc

        def m(self):
            return ys, loc
    return C


C = f()
print(C.comp, C.comp2, C.a, C().m())


def g():
    val = 1

    class D:
        val = 2

        def m(self):
            return val
        comp = [val for _ in range(1)]
        here = val
    return D


D = g()
print(D().m(), D.comp, D.val, D.here)


# class body sees later module-level rebinding at execution time only
z = 1


class G:
    zz = z


z = 2
print(G.zz)


# names bound in a class body: loops, imports, defs, del
class H:
    for i in range(3):
        pass
    last = i
    import math as m
    fl = m.floor(2.5)
    tmp = 1
    del tmp

    def get(self):
        try:
            return m.floor(1.5)
        except NameError as e:
            return 'NameError: ' + str(e)


print(H.last, H.i, H.fl, hasattr(H, 'tmp'), H().get())


# a class attribute shadowing a builtin only inside the class body
class S:
    len = 5
    r = len

    def m(self):
        return len('abc')


print(S.r, S().m())


# methods reach class attributes through the class name
class Self:
    count = 0

    def inc(self):
        Self.count += 1
        return Self.count


Self().inc()
print(Self().inc())


# __class__ and super() work from a comprehension inside a method
class Base:
    def who(self):
        return 'base'


class Derived(Base):
    def names(self):
        return [__class__.__name__ for _ in range(2)], [super().who() for _ in range(1)]


print(Derived().names())
