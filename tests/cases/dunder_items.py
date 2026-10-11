# __getitem__ / __setitem__ / __delitem__ with ints, slices, tuples and
# Ellipsis; missing-method errors; subclasses of dict/list overriding them.


class Grid:
    def __init__(self):
        self.log = []
        self.data = {}

    def __getitem__(self, key):
        self.log.append(('get', key))
        if isinstance(key, slice):
            return ('slice', key.start, key.stop, key.step)
        if isinstance(key, tuple):
            return ('tuple', key)
        if key is Ellipsis:
            return 'ellipsis'
        return self.data[key]

    def __setitem__(self, key, value):
        self.log.append(('set', key, value))
        self.data[key if not isinstance(key, slice) else (key.start, key.stop, key.step)] = value

    def __delitem__(self, key):
        self.log.append(('del', key))
        del self.data[key]


g = Grid()
g[1] = 'one'
g['k'] = 'v'
print(g[1], g['k'])
print(g[1:2], g[:3], g[::2], g[:], g[1:2:3], g[::-1])
print(g[1, 2], g[1:2, ::3], g[...], g[..., 0], g[()], g[(1,)])
g[1:3] = [9, 9]
g[::2] = 'x'
del g[1]
try:
    del g['missing']
except KeyError as e:
    print('KeyError', e)
try:
    g[42]
except KeyError as e:
    print('KeyError', e)
for entry in g.log:
    print(entry)
print(sorted(g.data.items(), key=repr))

# chained / nested subscripts and augmented assignment
g2 = Grid()
g2['n'] = 10
g2['n'] += 5
g2['n'] *= 2
print(g2['n'], g2.log)


# slice objects: indices(), and passing explicit slice()
class SliceInfo:
    def __init__(self, n):
        self.n = n

    def __getitem__(self, s):
        return s.indices(self.n)

    def __len__(self):
        return self.n


print(SliceInfo(10)[2:-1], SliceInfo(10)[::-3], SliceInfo(5)[slice(None, None, 2)], SliceInfo(4)[-100:100])


# errors for missing methods
class NoItems:
    pass


class OnlyGet:
    def __getitem__(self, k):
        return k


def attempt(label, f):
    try:
        print(label, '->', f())
    except (TypeError, KeyError, IndexError) as e:
        print(label, '->', type(e).__name__ + ':', e)


def setit(o):
    o[0] = 1


def delit(o):
    del o[0]


def setslice(o):
    o[1:2] = []


def augit(o):
    o[0] += 1


attempt('NoItems()[0]', lambda: NoItems()[0])
attempt('NoItems()[1:2]', lambda: NoItems()[1:2])
attempt('NoItems()[0] = 1', lambda: setit(NoItems()))
attempt('del NoItems()[0]', lambda: delit(NoItems()))
attempt('OnlyGet()[0] = 1', lambda: setit(OnlyGet()))
attempt('del OnlyGet()[0]', lambda: delit(OnlyGet()))
attempt('OnlyGet()[1:2] = []', lambda: setslice(OnlyGet()))
attempt('OnlyGet()[0] += 1', lambda: augit(OnlyGet()))
attempt('NoItems class subscript', lambda: NoItems[0])


class Generic:
    def __class_getitem__(cls, item):
        return ('class_getitem', cls.__name__, item)


class SubGeneric(Generic):
    pass


attempt('Generic[int]', lambda: Generic[int])
attempt('SubGeneric[str, int]', lambda: SubGeneric[str, int])
attempt('Generic()[0]', lambda: Generic()[0])


# dict subclass with __missing__ and overridden methods
class Default(dict):
    def __missing__(self, key):
        print('missing', key)
        return key * 2


dd = Default(a=1)
print(dd['a'], dd.get('q', 'dflt'), len(dd))
attempt("dd['zz']", lambda: dd['zz'])
print('zz' in dd, len(dd))


class Counter(dict):
    def __missing__(self, key):
        return 0


def count():
    c = Counter()
    for ch in 'abracadabra':
        c[ch] += 1
    return sorted(c.items())


attempt('Counter-like __missing__', count)


class LowerDict(dict):
    def __setitem__(self, k, v):
        super().__setitem__(k.lower(), v)

    def __getitem__(self, k):
        return super().__getitem__(k.lower())


ld = LowerDict()
ld['HeLLo'] = 1
print(ld['HELLO'], dict(ld), list(ld.keys()))


class NoMissing(dict):
    pass


try:
    NoMissing()['x']
except KeyError as e:
    print('KeyError', e)


# list subclass overriding __getitem__ (used by subscripting, not by iteration)
class OneBased(list):
    def __getitem__(self, i):
        if isinstance(i, int):
            return list.__getitem__(self, i - 1)
        return list.__getitem__(self, i)


ob = OneBased([10, 20, 30])
print(ob[1], ob[3], ob[0:2], list(ob), len(ob), ob == [10, 20, 30])


# subscripting with an instance as the key (hash/eq) and as the container
class K:
    def __init__(self, v):
        self.v = v

    def __hash__(self):
        return hash(self.v)

    def __eq__(self, o):
        return isinstance(o, K) and o.v == self.v


m = {K(1): 'k1'}
print(m[K(1)], K(2) in m)
g3 = Grid()
g3[K(5)] = 'by K'
print(g3[K(5)])
