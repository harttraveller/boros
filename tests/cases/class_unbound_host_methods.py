# Unbound methods of builtin base classes applied to instances of
# interpreted subclasses (list.__len__(x), dict.__getitem__(x, k), ...).

class L(list):
    def __len__(self):
        return list.__len__(self) + 100

    def append(self, v):
        list.append(self, v * 2)


class D(dict):
    def __getitem__(self, k):
        return 'D:' + str(dict.__getitem__(self, k))

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v + 1)


class S(str):
    def upper(self):
        return 'S:' + str.upper(self)


class I(int):
    def __add__(self, other):
        return I(int.__add__(self, other) * 10)

    def __repr__(self):
        return 'I(%s)' % int.__repr__(self)


l = L([1])
l.append(5)
print(len(l), list(l), list.__len__(l), list.__getitem__(l, 1), list.__contains__(l, 10))
d = D()
d['a'] = 1
print(d['a'], dict.__getitem__(d, 'a'), dict.get(d, 'a'), dict.__len__(d), dict.keys(d))
s = S('abc')
print(s.upper(), str.upper(s), str.__len__(s), str.startswith(s, 'ab'))
i = I(4)
print(i + 1, int.__add__(i, 1), int.__mul__(i, 3), int.__repr__(i), repr(i))
print(object.__repr__(l).startswith('<'), type(list.__dict__['__len__']).__name__)
