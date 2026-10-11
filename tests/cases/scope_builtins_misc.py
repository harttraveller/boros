import sys

# type() with three arguments
X = type('X', (object,), {'a': 1, 'double': lambda self: self.a * 2})
x = X()
print(X.__name__, x.a, x.double(), type(x) is X, isinstance(x, X))
Y = type('Y', (X,), {})
print(Y().double(), issubclass(Y, X), Y.__mro__ == (Y, X, object), Y.__bases__ == (X,))
print(type(1), type('s').__name__, type(None).__name__, type(X).__name__, type(type))

# isinstance / issubclass with tuples and unions
print(isinstance(1, (str, int)), isinstance('s', int | str), isinstance(x, (int, X)), issubclass(bool, int | str))
print(isinstance(x, object), issubclass(X, object), isinstance(X, type), isinstance(3, X))


# length / bool / hash / iter protocol errors
class BadLen:
    def __init__(self, v):
        self.v = v

    def __len__(self):
        return self.v


print(len(BadLen(3)), bool(BadLen(0)), bool(BadLen(2)))
for v in [-1, 'x', 2.5]:
    try:
        len(BadLen(v))
    except (TypeError, ValueError) as e:
        print(type(e).__name__ + ':', e)


class BadIter:
    def __iter__(self):
        return [1, 2]


try:
    iter(BadIter())
except TypeError as e:
    print('TypeError:', e)


class NotIter:
    pass


for f in (iter, next, len):
    try:
        f(NotIter())
    except TypeError as e:
        print('TypeError:', e)


class BadHash:
    def __hash__(self):
        return 'nope'


try:
    hash(BadHash())
except TypeError as e:
    print('TypeError:', e)


class Unhashable:
    __hash__ = None


try:
    {Unhashable(): 1}
except TypeError as e:
    print('TypeError:', e)
try:
    sorted([1, 'a'])
except TypeError as e:
    print('TypeError:', e)
try:
    sorted([X(), X()])
except TypeError as e:
    print('TypeError:', e)


# getattr / setattr / delattr / hasattr
class G:
    @property
    def boom(self):
        raise ValueError('property raised')


g = G()
setattr(g, 'dyn', 5)
print(getattr(g, 'dyn'), hasattr(g, 'dyn'), getattr(g, 'zzz', None))
delattr(g, 'dyn')
print(hasattr(g, 'dyn'))
try:
    getattr(g, 'boom', 'default')
except ValueError as e:
    print('ValueError:', e)
try:
    hasattr(g, 'boom')
except ValueError as e:
    print('ValueError:', e)
try:
    getattr(g, 5)
except TypeError as e:
    print('TypeError:', e)
try:
    delattr(g, 'never')
except AttributeError as e:
    print('AttributeError:', e)


# bytes / frozenset / slice / object
class B:
    def __bytes__(self):
        return b'raw'


print(bytes(B()), bytearray(b'ab') + b'c', frozenset([1, 1, 2]) == {1, 2}, slice(1, 5, 2).indices(10))
print([0, 1, 2, 3, 4, 5][slice(None, None, -2)], 'abcdef'[slice(1, 4)], type(object()).__name__)
print(callable(len), callable(X), callable(x), callable(lambda: 0), callable(3))
print(repr(None), repr(...), repr(NotImplemented), str(b'x'), ascii('ü'), repr('it\'s'))
print(list(reversed(range(3))), list(reversed([1, 2])), list(reversed('ab')), list(reversed((1, 2))))
print(int.from_bytes(b'\x01\x00', 'big'), (255).to_bytes(2, 'little'), (10).bit_length(), (3.5).is_integer())
print(sys.maxsize > 2 ** 31, isinstance(sys.version_info.major, int), sys.version_info >= (3, 13))
# input() at end of input
try:
    input('prompt> ')
except EOFError as e:
    print()
    print('EOFError:', e)
