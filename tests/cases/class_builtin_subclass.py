# Instances of classes deriving from builtins: list, dict, int, str, set, tuple.

class Stack(list):
    def push(self, x):
        self.append(x)
        return self

    def peek(self):
        return self[-1]

    @property
    def size(self):
        return len(self)


s = Stack([1, 2])
s.push(3).push(4)
print(s, len(s), s.peek(), s.size, s[0], s[1:3], list(s), sum(s))
print(isinstance(s, list), type(s).__name__, s == [1, 2, 3, 4], 3 in s)
s.extend([5]); s.sort(reverse=True)
print(s, sorted(s), [x * 2 for x in s])
s.tag = 'has dict'
print(s.tag)
print(type(s + [9]).__name__, type(s[:2]).__name__)


class LoudList(list):
    def append(self, x):
        print('append', x)
        super().append(x)

    def __getitem__(self, i):
        return 'item:' + str(super().__getitem__(i))

    def __len__(self):
        return super().__len__() * 10


ll = LoudList()
ll.append(1)
ll.append(2)
print(ll[0], len(ll), list.__len__(ll))


class DefaultDict(dict):
    def __init__(self, default, *a, **kw):
        super().__init__(*a, **kw)
        self.default = default

    def __missing__(self, key):
        return self.default


dd = DefaultDict(0, a=1)
print(dd['a'], dict(dd), len(dd), sorted(dd.items()), 'a' in dd)
dd['b'] = 2
print(sorted(dd.keys()), dd.get('c', 'dflt'), dd.default)


class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self[name] = value


ad = AttrDict(x=1)
ad.y = 2
print(ad.x, ad.y, sorted(ad.items()), isinstance(ad, dict))
try:
    ad.zz
except AttributeError as e:
    print('AttributeError:', e)


class Meters(int):
    def __repr__(self):
        return 'Meters(%d)' % int(self)

    def __add__(self, other):
        return Meters(int(self) + int(other))

    def double(self):
        return Meters(self * 2)


m = Meters(5)
print(m, m + 3, m + m, m.double(), m * 2, int(m), m == 5, m < 7, hash(m) == hash(5))
print(isinstance(m, int), type(m + 1).__name__, type(m * 2).__name__, m.real, m.bit_length())
print('%d' % m, f'{m:>4}', str(m), float(m))


class Upper(str):
    def __new__(cls, value):
        return super().__new__(cls, value.upper())

    def shout(self):
        return self + '!'


u = Upper('hello')
print(u, len(u), u.shout(), u.lower(), u[1:3], isinstance(u, str), type(u).__name__)
print(u == 'HELLO', u + ' world', u.startswith('HE'), '-'.join(u), {u: 1}['HELLO'])


class Pair(tuple):
    def __new__(cls, a, b):
        return super().__new__(cls, (a, b))

    @property
    def first(self):
        return self[0]

    def swap(self):
        return Pair(self[1], self[0])


pr = Pair(1, 2)
print(pr, pr.first, pr.swap(), len(pr), pr + (3,), isinstance(pr, tuple), pr == (1, 2))
a, b = pr
print(a, b)


class TagSet(set):
    def add_all(self, *items):
        for i in items:
            self.add(i)
        return self


ts = TagSet([1])
ts.add_all(2, 3)
print(sorted(ts), len(ts), 2 in ts, type(ts).__name__, isinstance(ts, set))


class MyFloat(float):
    def __str__(self):
        return 'MyFloat<%s>' % float.__repr__(self)


mf = MyFloat(1.5)
print(str(mf), mf * 2, round(mf), isinstance(mf, float))


# __init__ of a list subclass with extra arguments
class Named(list):
    def __init__(self, name, items):
        super().__init__(items)
        self.name = name


n = Named('nums', [3, 1])
print(n.name, n, n.count(3))

# bool() of builtin subclasses follows the builtin
print(bool(Stack()), bool(Stack([0])), bool(Meters(0)), bool(Upper('')))
