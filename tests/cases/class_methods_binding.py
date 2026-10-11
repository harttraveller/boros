# Bound/unbound methods, method objects, special-method lookup on the type.

class Greeter:
    greeting = 'hi'

    def __init__(self, name):
        self.name = name

    def greet(self, punct='!'):
        return '%s %s%s' % (self.greeting, self.name, punct)


g = Greeter('ann')
m = g.greet
print(m(), m('?'), Greeter.greet(g), Greeter.greet(g, '.'))
print(m.__self__ is g, m.__func__ is Greeter.greet, m.__name__)
print(g.greet == g.greet, g.greet is g.greet, Greeter.greet is Greeter.greet)
print(g.greet == Greeter('bob').greet, hash(g.greet) == hash(g.greet))

# methods stored and called later
calls = [g.greet, Greeter('bob').greet]
print([c() for c in calls])

# functions added to the class later become methods for existing instances
def shout(self):
    return self.name.upper()


Greeter.shout = shout
print(g.shout())

# a function stored on an instance is not bound
g.helper = shout
try:
    g.helper()
except TypeError as e:
    print('TypeError:', e)
print(g.helper(g))

# special methods are looked up on the type, not the instance
class Sized:
    def __len__(self):
        return 3


s = Sized()
s.__len__ = lambda: 99
print(len(s), s.__len__())

# repr/str fallback
class OnlyRepr:
    def __repr__(self):
        return 'OnlyRepr()'


class OnlyStr:
    def __str__(self):
        return 'OnlyStr-str'


print(str(OnlyRepr()), repr(OnlyRepr()), '%s|%r' % (OnlyRepr(), OnlyRepr()), f'{OnlyRepr()}')
print(str(OnlyStr()), repr(OnlyStr()).startswith('<__main__.OnlyStr object at'))
print([OnlyRepr()], (OnlyRepr(),), {'k': OnlyRepr()})

# __repr__ returning a non-string
class BadRepr:
    def __repr__(self):
        return 5


try:
    repr(BadRepr())
except TypeError as e:
    print('TypeError:', e)

# __eq__ without __hash__ makes instances unhashable
class Eq:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return isinstance(other, Eq) and self.v == other.v


print(Eq(1) == Eq(1), Eq(1) != Eq(2), Eq.__hash__)
try:
    hash(Eq(1))
except TypeError as e:
    print('TypeError:', e)
try:
    {Eq(1)}
except TypeError as e:
    print('TypeError:', e)


class EqHash(Eq):
    def __hash__(self):
        return hash(self.v)


print(len({EqHash(1), EqHash(1), EqHash(2)}), EqHash(3) in {EqHash(3)})

# explicitly unhashable
class NoHash:
    __hash__ = None


try:
    hash(NoHash())
except TypeError as e:
    print('TypeError:', e)

# default equality is identity; default hash is consistent
class Ident:
    pass


i1, i2 = Ident(), Ident()
print(i1 == i1, i1 == i2, i1 != i2, hash(i1) == hash(i1), len({i1, i2, i1}))

# __bool__ and __len__ truthiness
class Falsy:
    def __bool__(self):
        return False


class Empty:
    def __len__(self):
        return 0


print(bool(Falsy()), bool(Empty()), bool(Ident()), 'yes' if Empty() else 'no', not Falsy())

# methods with *args/**kwargs and defaults referencing class attributes
class Conf:
    default = 10

    def get(self, key, default=None, *rest, **opts):
        return key, default, rest, sorted(opts.items())


print(Conf().get('a'), Conf().get('a', 1, 2, 3, x=4))

# calling a method via the class with an unrelated 'self' works (no type check)
class Duck:
    greeting = 'quack'
    name = 'duck'


print(Greeter.greet(Duck()))

# recursion through methods
class Tree:
    def __init__(self, v, *kids):
        self.v = v
        self.kids = kids

    def total(self):
        return self.v + sum(k.total() for k in self.kids)

    def depth(self):
        return 1 + max([k.depth() for k in self.kids], default=0)


t = Tree(1, Tree(2, Tree(3)), Tree(4))
print(t.total(), t.depth())

# method resolution with instance attribute lookups inside comprehensions
class Matrix:
    def __init__(self, rows):
        self.rows = rows

    def transpose(self):
        return Matrix([[r[i] for r in self.rows] for i in range(len(self.rows[0]))])

    def __repr__(self):
        return 'Matrix(%r)' % (self.rows,)


print(Matrix([[1, 2], [3, 4], [5, 6]]).transpose())
