# Errors raised by host operations: types and messages must match CPython.


def msg(f, *args):
    try:
        f(*args)
    except Exception as e:
        print(type(e).__name__ + ':', e)
    else:
        print('no error')


class A:
    x = 1

    def method(self, a):
        return a


class B:
    __slots__ = ('s',)


a = A()
msg(lambda: 1 / 0)
msg(lambda: 1 // 0)
msg(lambda: 1 % 0)
msg(lambda: 1.5 / 0)
msg(lambda: {}['missing'])
msg(lambda: {1: 2}[(1, 2)])
msg(lambda: [1, 2, 3][10])
msg(lambda: (1,)[-5])
msg(lambda: 'abc'[5])
msg(lambda: [].pop())
msg(lambda: {}.popitem())
msg(lambda: a.nope)
msg(lambda: A.nope)
msg(lambda: (1).nope)
msg(lambda: 'str'.nope)
msg(lambda: B().s)
msg(lambda: setattr(B(), 'other', 1))
msg(lambda: 1 + 'a')
msg(lambda: 'a' + 1)
msg(lambda: [1] + (2,))
msg(lambda: a + 1)
msg(lambda: 1 - a)
msg(lambda: a < a)
msg(lambda: a < 1)
msg(lambda: -a)
msg(lambda: ~'x')
msg(lambda: a())
five = 5
msg(lambda: five())
msg(lambda: len(a))
msg(lambda: len(5))
msg(lambda: iter(a))
msg(lambda: iter(5))
msg(lambda: next([]))
msg(lambda: a[0])
msg(lambda: hash([]))
msg(lambda: {[]: 1})
msg(lambda: {a, []})
msg(lambda: int('xyz'))
msg(lambda: int('12', 1))
msg(lambda: float('abc'))
msg(lambda: [1, 2].index(5))
msg(lambda: 'abc'.index('z'))
msg(lambda: [].remove(1))
msg(lambda: set().remove(1))
msg(lambda: a.method())
msg(lambda: a.method(1, 2))
msg(lambda: a.method(1, b=2))
msg(lambda: A.method(1))
msg(lambda: abs('x'))
msg(lambda: 2 ** 'x')
msg(lambda: 'x' * 'y')
msg(lambda: 'x' * 2.5)
l12 = [1, 2]
msg(lambda: l12[1.0])
abc = 'abc'
msg(lambda: abc['x'])
msg(lambda: sum(['a', 'b']))
msg(lambda: max([]))
msg(lambda: chr(-1))
msg(lambda: divmod(1, 0))
msg(lambda: (1, 2) < (1, 'a'))
msg(lambda: sorted([1, 'a']))
msg(lambda: dict([(1, 2, 3)]))
msg(lambda: ''.join([1]))
msg(lambda: '%d' % 'x')
msg(lambda: '{}{}'.format(1))
msg(lambda: getattr(a, 'zzz'))
msg(lambda: delattr(a, 'zzz'))
msg(lambda: isinstance(1, 1))
msg(lambda: issubclass(1, int))
msg(lambda: range(1, 2, 0))
msg(lambda: list(zip([1], [2], strict=True, x=1)))
msg(lambda: [].sort(key=1))
msg(lambda: open('/nonexistent/dir/file.txt'))
msg(lambda: __import__('no_such_module_xyz'))


def two(x, y):
    return x + y


def kwonly(*, k):
    return k


msg(two)
msg(two, 1)
msg(two, 1, 2, 3)
msg(lambda: two(1, x=2))
msg(lambda: two(1, z=2))
msg(kwonly, 1)
msg(kwonly)


def unbound():
    print(v)
    v = 1


msg(unbound)
msg(lambda: undefined_name)


def unpack():
    a, b = [1, 2, 3]


def unpack2():
    a, b, c = [1, 2]


def unpack3():
    a, b = 5


msg(unpack)
msg(unpack2)
msg(unpack3)

# integer conversion
msg(lambda: int(None))
msg(lambda: [][None:'x'])
msg(lambda: {}.fromkeys(1))
msg(lambda: 'abc'.split(1))
msg(lambda: int.from_bytes('x'))
