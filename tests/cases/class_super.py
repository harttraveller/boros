# zero-argument and two-argument super() in many positions.

class Base:
    def __init__(self, x):
        self.x = x
        self.log = ['Base.__init__']

    def describe(self):
        return 'Base(%s)' % self.x

    @classmethod
    def make(cls, x):
        return cls(x)

    @classmethod
    def kind(cls):
        return 'Base.kind for ' + cls.__name__

    @staticmethod
    def static_thing():
        return 'Base.static_thing'

    @property
    def prop(self):
        return 'Base.prop'


class Child(Base):
    def __init__(self, x, y):
        super().__init__(x)
        self.y = y
        self.log.append('Child.__init__')

    def describe(self):
        return 'Child[' + super().describe() + ']'

    @classmethod
    def kind(cls):
        return 'Child.kind > ' + super().kind()

    @staticmethod
    def static_thing():
        return 'Child > ' + super(Child, Child).static_thing()

    @property
    def prop(self):
        return 'Child.prop > ' + super().prop

    @classmethod
    def make(cls, x):
        obj = super().make.__func__(cls, x) if False else None
        return 'make via ' + cls.__name__


c = Child(1, 2)
print(c.x, c.y, c.log)
print(c.describe())
print(Child.kind())
print(c.kind())
print(Child.static_thing())
print(c.prop)
print(Child.make(5))


class GrandChild(Child):
    def describe(self):
        return 'GrandChild{' + super().describe() + '}'

    def two_arg(self):
        # skip Child.describe
        return super(Child, self).describe()


g = GrandChild(7, 8)
print(g.describe())
print(g.two_arg())
print(GrandChild.kind())


# cooperative multiple inheritance with keyword arguments
class Root:
    def __init__(self, **kw):
        self.order = ['Root']
        if kw:
            self.leftover = sorted(kw)


class Left(Root):
    def __init__(self, left=None, **kw):
        super().__init__(**kw)
        self.order.append('Left')
        self.left = left


class Right(Root):
    def __init__(self, right=None, **kw):
        super().__init__(**kw)
        self.order.append('Right')
        self.right = right


class Bottom(Left, Right):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.order.append('Bottom')


b = Bottom(left=1, right=2, extra=3)
print(b.order, b.left, b.right, b.leftover)
print([k.__name__ for k in Bottom.__mro__])


# cooperative method chain
class P:
    def chain(self):
        return ['P']


class Q(P):
    def chain(self):
        return ['Q'] + super().chain()


class R(P):
    def chain(self):
        return ['R'] + super().chain()


class S(Q, R):
    def chain(self):
        return ['S'] + super().chain()


print(S().chain())
print(super(Q, S()).chain())
print(super(R, S()).chain())


# super() inside a nested function / lambda / comprehension in a method
class N(Base):
    def describe(self):
        f = lambda: super(N, self).describe()
        return 'N:' + f()

    def comp(self):
        return [super().describe() for _ in range(2)]


n = N(3)
print(n.describe())
print(n.comp())


# super object attributes
s = super(Child, c)
print(type(s).__name__)
print(s.describe())

# super() errors
class E:
    def m(self):
        return super().nope

try:
    E().m()
except AttributeError as e:
    print('AttributeError:', e)



# super with __class__ reference
class K:
    def who(self):
        return __class__.__name__


class KK(K):
    pass


print(KK().who())


# super().__init__ to builtin object with args
class NoArgs:
    def __init__(self, a):
        super().__init__()
        self.a = a


print(NoArgs(4).a)


class TooMany:
    def __init__(self, a):
        super().__init__(a)


try:
    TooMany(1)
except TypeError as e:
    print('TypeError:', e)


# super in a generator method
class G(Base):
    def gen(self):
        yield super().describe()
        yield 'done'


print(list(G(9).gen()))


# super().__repr__ / __eq__ defaults through object
class Rep:
    def __repr__(self):
        r = super().__repr__()
        return 'Rep<' + str(r.startswith('<')) + '>'

    def __eq__(self, other):
        return super().__eq__(other)

    __hash__ = object.__hash__


r = Rep()
print(repr(r), r == r, r == 1, Rep.__eq__(r, 1))
