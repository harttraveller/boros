# copy.copy / copy.deepcopy of interpreted instances: default behaviour,
# __copy__/__deepcopy__, __getstate__/__setstate__, __reduce__/__reduce_ex__,
# __slots__, cycles, and subclasses of host containers.
import copy


def show(label, f):
    try:
        print(label, '->', f())
    except Exception as e:
        print(label, '->', type(e).__name__ + ':', e)


class Pt:
    def __init__(self, x, tags):
        self.x = x
        self.tags = tags


p = Pt(1, ['a'])
c = copy.copy(p)
d = copy.deepcopy(p)
print(type(c).__name__, c is p, c.x, c.tags is p.tags, d.tags is p.tags, d.tags == p.tags)
c.x = 99
print(p.x, vars(c) == {'x': 99, 'tags': ['a']}, isinstance(d, Pt))


# cycles and shared references in deepcopy
class Node:
    def __init__(self, name):
        self.name = name
        self.next = None


a = Node('a')
b = Node('b')
a.next = b
b.next = a
a2 = copy.deepcopy(a)
print(a2.name, a2.next.name, a2.next.next is a2, a2 is not a)
shared = [Node('s')]
pair = copy.deepcopy([shared, shared])
print(pair[0] is pair[1], pair[0][0] is not shared[0])


# __copy__ / __deepcopy__
class Custom:
    def __init__(self, v):
        self.v = v

    def __copy__(self):
        print('__copy__ called')
        return Custom(self.v + 1)

    def __deepcopy__(self, memo):
        print('__deepcopy__ called', type(memo).__name__)
        return Custom(self.v * 10)


print(copy.copy(Custom(1)).v, copy.deepcopy(Custom(2)).v, copy.deepcopy([Custom(3)])[0].v)


# __getstate__ / __setstate__
class Stateful:
    def __init__(self):
        self.keep = 1
        self.drop = 'cache'

    def __getstate__(self):
        print('__getstate__')
        st = self.__dict__.copy()
        del st['drop']
        return st

    def __setstate__(self, st):
        print('__setstate__', sorted(st))
        self.__dict__.update(st)
        self.drop = 'rebuilt'


show('copy Stateful', lambda: sorted(vars(copy.copy(Stateful())).items()))
show('deepcopy Stateful', lambda: sorted(vars(copy.deepcopy(Stateful())).items()))


# __reduce__ controls copying
class Reduced:
    def __init__(self, a, b=0):
        self.a = a
        self.b = b

    def __reduce__(self):
        print('__reduce__')
        return (Reduced, (self.a * 2,))


show('copy Reduced', lambda: vars(copy.copy(Reduced(3, 4))))
show('deepcopy Reduced', lambda: vars(copy.deepcopy(Reduced(5, 6))))


class ReducedEx:
    def __reduce_ex__(self, proto):
        print('__reduce_ex__', proto)
        return (list, ([1, 2],))


show('copy ReducedEx', lambda: copy.copy(ReducedEx()))


# __slots__
class Slotted:
    __slots__ = ('x', 'y')

    def __init__(self):
        self.x = [1]


s = Slotted()
s2 = copy.copy(s)
s3 = copy.deepcopy(s)
print(s2.x is s.x, s3.x is s.x, s3.x, hasattr(s2, 'y'))


# subclasses of host containers
class MyList(list):
    def total(self):
        return sum(self)


ml = MyList([1, 2])
ml.extra = 'attr'
mc = copy.copy(ml)
show('copy MyList', lambda: (type(mc).__name__, mc.total(), mc.extra, mc is ml))
mc.append(3)
print('original after appending to copy:', list(ml), list(mc))
md = copy.deepcopy(ml)
md.append(4)
print('original after appending to deepcopy:', list(ml), list(md))


class MyDict(dict):
    pass


md0 = MyDict(k=[1])
md1 = copy.copy(md0)
md1['new'] = 2
print('dict original:', sorted(md0), 'copy:', sorted(md1), md1['k'] is md0['k'])
md2 = copy.deepcopy(md0)
print(md2['k'] is md0['k'], md2 == md0, type(md2).__name__)


# copy.replace (3.13) uses __replace__
class Rep:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __replace__(self, **changes):
        kw = {'a': self.a, 'b': self.b}
        kw.update(changes)
        return Rep(**kw)


show('copy.replace', lambda: vars(copy.replace(Rep(1, 2), b=5)))
show('copy.replace unsupported', lambda: copy.replace(Pt(1, []), x=2))


# copying classes, functions and bound methods (functions and classes are atomic)
def func():
    return 'f'


show('copy.copy(class) is class', lambda: copy.copy(Pt) is Pt)
show('copy.deepcopy(class) is class', lambda: copy.deepcopy(Pt) is Pt)
show('copy.copy(func) is func', lambda: copy.copy(func) is func)
show('copy.deepcopy(func) is func', lambda: copy.deepcopy(func) is func)
show('deepcopy([func, lambda])', lambda: [x is y for x, y in zip(copy.deepcopy([func, show]), [func, show])])
show('copy bound method', lambda: copy.copy(p.__init__).__self__ is p)


class Holder:
    def __init__(self):
        self.cb = func
        self.kind = Pt


show('deepcopy instance holding func/class', lambda: (lambda h: (h.cb is func, h.kind is Pt))(copy.deepcopy(Holder())))
