# dict subclasses: d[key] calls __missing__ for absent keys.

class Default(dict):
    def __init__(self, default, *a, **kw):
        super().__init__(*a, **kw)
        self.default = default

    def __missing__(self, key):
        return self.default


dd = Default(0, a=1)
print(dd['a'], dd['zzz'], 'zzz' in dd, dd.get('zzz', 'get ignores __missing__'))


class Counter(dict):
    def __missing__(self, key):
        self[key] = 0
        return 0


c = Counter()
for ch in 'abracadabra':
    c[ch] += 1
print(sorted(c.items()))


class NoMissing(dict):
    pass


try:
    NoMissing()['k']
except KeyError as e:
    print('KeyError:', e)


class Raises(dict):
    def __missing__(self, key):
        raise LookupError('custom missing ' + key)


try:
    Raises()['q']
except LookupError as e:
    print(type(e).__name__, e)
