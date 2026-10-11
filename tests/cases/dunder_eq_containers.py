# User __eq__/__ne__/__hash__ used by host container methods: list.index,
# count, remove, tuple.index, dict/set lookups, ==/!= of containers holding
# instances, and explicit __ne__ with NotImplemented fallbacks.


class Name:
    calls = 0

    def __init__(self, s):
        self.s = s

    def __eq__(self, o):
        Name.calls += 1
        if isinstance(o, Name):
            return self.s.lower() == o.s.lower()
        if isinstance(o, str):
            return self.s.lower() == o.lower()
        return NotImplemented

    def __hash__(self):
        return hash(self.s.lower())

    def __repr__(self):
        return 'Name(%r)' % self.s


names = [Name('Ann'), Name('bob'), Name('ANN'), Name('cy')]
print(names.index(Name('BOB')), names.count(Name('ann')), names.count('ANN'), names.index('cy'))
names.remove(Name('ann'))
print(names)
print((Name('x'), Name('y')).index(Name('Y')), Name('q') in (Name('Q'),), 'bob' in names)
print([Name('a')] == [Name('A')], [Name('a')] != [Name('A')], (Name('a'),) == ('a',))
print({Name('k'): 1} == {Name('K'): 1}, {Name('a')} == {Name('A')}, {Name('a'), Name('A')})
d = {Name('Key'): 'v'}
print(d[Name('KEY')], d.get('key'), Name('kEy') in d, 'key' in d)
s = {Name('m'), Name('n')}
s.discard(Name('M'))
print(s, Name('N') in s, s - {Name('n')})
try:
    names.index(Name('zed'))
except ValueError as e:
    print('ValueError:', e)
try:
    names.remove('nobody')
except ValueError as e:
    print('ValueError:', e)
print('eq calls > 0:', Name.calls > 0)


# explicit __ne__
class Ne:
    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return 'eq'

    def __ne__(self, o):
        if isinstance(o, Ne):
            return self.v != o.v
        return NotImplemented


print(Ne(1) != Ne(2), Ne(1) != Ne(1), Ne(1) != 5, 5 != Ne(1), Ne(1) == 5)


class NeRefl:
    def __ne__(self, o):
        print('NeRefl.__ne__ reflected')
        return 'reflected ne'


print(Ne(1) != NeRefl())


# __eq__ on a subclass is tried first for ==
class Base:
    def __eq__(self, o):
        print('Base.__eq__')
        return NotImplemented


class Derived(Base):
    def __eq__(self, o):
        print('Derived.__eq__')
        return True


print(Base() == Derived())
print(Derived() == Base())


# list.__contains__ / count compare item == element (element on the left)
class Order:
    def __init__(self, tag):
        self.tag = tag

    def __eq__(self, o):
        print('eq', self.tag, getattr(o, 'tag', o))
        return False


print(Order('needle') in [Order('a'), Order('b')])
print([Order('x')].count(Order('y')))
