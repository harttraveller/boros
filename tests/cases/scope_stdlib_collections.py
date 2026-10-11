from collections import Counter, defaultdict, deque, namedtuple, OrderedDict, ChainMap


class Key:
    def __init__(self, k):
        self.k = k

    def __eq__(self, o):
        return isinstance(o, Key) and self.k == o.k

    def __hash__(self):
        return hash(self.k)

    def __repr__(self):
        return 'Key(%r)' % self.k


# Counter
c = Counter('abracadabra')
print(c.most_common(3), c['a'], c['zzz'], sorted(c.elements())[:4])
c.update(['a', 'z'])
c.subtract({'b': 1})
print(c['a'], c['z'], c['b'], len(c))
print(Counter([Key(1), Key(2), Key(1)]).most_common())
print(Counter(a=3, b=1) + Counter(a=1, c=2), Counter(a=3) - Counter(a=5), Counter(a=2) & Counter(a=1, b=1))
print(Counter(len(w) for w in 'the quick brown fox'.split()))
print(sorted(Counter({'x': 2, 'y': 1}).items()), Counter('aab').total())

# defaultdict with interpreted factories
dd = defaultdict(list)
for word in ['apple', 'avocado', 'banana', 'cherry', 'blueberry']:
    dd[word[0]].append(word)
print(dict(dd))
counts = defaultdict(lambda: 100)
counts['x'] += 1
print(counts['x'], counts['y'], sorted(counts.items()))


def make_default():
    return {'made': True}


d2 = defaultdict(make_default)
print(d2['k'], d2.default_factory is make_default)


class Box:
    instances = 0

    def __init__(self):
        Box.instances += 1
        self.items = []

    def __repr__(self):
        return 'Box(%r)' % self.items


d3 = defaultdict(Box)
d3['a'].items.append(1)
d3['a'].items.append(2)
d3['b']
print(dict(d3), Box.instances)
nested = defaultdict(lambda: defaultdict(int))
nested['x']['y'] += 5
print(nested['x']['y'], 'y' in nested['x'], 'z' in nested)
try:
    defaultdict(None)['missing']
except KeyError as e:
    print('KeyError:', e)

# deque
dq = deque([1, 2, 3], maxlen=4)
dq.append(4)
dq.append(5)
dq.appendleft(0)
print(dq, dq.maxlen, list(dq))
dq.rotate(2)
print(dq, dq.popleft(), dq.pop(), len(dq))
dq.extend([7, 8])
dq.extendleft('ab')
print(dq, dq.count(7), dq.index(7) if 7 in dq else -1)
print(deque(Key(i) for i in range(2)), deque(reversed('abc')))

# namedtuple
Point = namedtuple('Point', 'x y')
p = Point(1, y=2)
print(p, p.x, p[1], p._replace(x=9), p._asdict(), Point._fields, Point._make([5, 6]))
print(p == (1, 2), tuple(p), sum(p), isinstance(p, tuple), hash(p) == hash((1, 2)))
x, y = p
print(x, y)
P3 = namedtuple('P3', ['a', 'b', 'c'], defaults=[0, 0])
print(P3(1), P3(1, 2, 3), P3._field_defaults)

# OrderedDict / ChainMap
od = OrderedDict()
od['b'] = 1
od['a'] = 2
od.move_to_end('b')
print(list(od), od.popitem(last=False), od)
cm = ChainMap({'a': 1}, {'a': 2, 'b': 3})
print(cm['a'], cm['b'], sorted(cm), cm.new_child({'c': 4})['c'])
