# Operators on instances of interpreted subclasses of host types (int,
# str, list, tuple, dict), with each other and mixed with plain host values,
# plus sequence concatenation/repetition with plain user objects.


def show(label, f):
    try:
        print(label, '->', f())
    except Exception as e:
        print(label, '->', type(e).__name__ + ':', e)


class ML(list):
    pass


class MD(dict):
    pass


class MS(str):
    pass


class MI(int):
    pass


class MT(tuple):
    pass


# same-kind subclass instances on both sides
show('ML == ML', lambda: ML([1]) == ML([1]))
show('ML != ML', lambda: ML([1]) != ML([2]))
show('ML < ML', lambda: ML([1]) < ML([2]))
show('ML + ML', lambda: ML([1]) + ML([2]))
show('MD == MD', lambda: MD(a=1) == MD(a=1))
show('MD | MD', lambda: MD(a=1) | MD(b=2))
show('MS + MS', lambda: MS('a') + MS('b'))
show('MS == MS', lambda: MS('a') == MS('a'))
show('MS < MS', lambda: MS('a') < MS('b'))
show('MS in MS', lambda: MS('a') in MS('abc'))
show('MS % MS', lambda: MS('<%s>') % MS('x'))
show('MI + MI', lambda: MI(1) + MI(2))
show('MI * MI', lambda: MI(3) * MI(4))
show('MI < MI', lambda: MI(1) < MI(2))
show('MI == MI', lambda: MI(1) == MI(1))
show('divmod(MI, MI)', lambda: divmod(MI(7), MI(2)))
show('MT + MT', lambda: MT((1,)) + MT((2,)))
show('MT == MT', lambda: MT((1,)) == MT((1,)))
show('sorted MI', lambda: sorted([MI(3), MI(1), 2]))
show('max MS', lambda: max(MS('a'), MS('b')))
show('set of MI', lambda: sorted({MI(1), MI(1), 1}))

# subclass instance on one side, plain host value on the other
show('[0] + ML', lambda: [0] + ML([2]))
show('ML + [0]', lambda: ML([2]) + [0])
show("'x' + MS", lambda: 'x' + MS('b'))
show("MS + 'x'", lambda: MS('b') + 'x')
show('(0,) + MT', lambda: (0,) + MT((1,)))
show('{} | MD', lambda: {'x': 0} | MD(b=2))
show('[0] * MI', lambda: [0] * MI(3))
show("'ab' * MI", lambda: 'ab' * MI(2))
show('5 - MI', lambda: 5 - MI(3))
show('2 ** MI', lambda: 2 ** MI(3))
show('[1] == ML', lambda: [1] == ML([1]))
show("'a' == MS", lambda: 'a' == MS('a'))
show("'a' in MS", lambda: 'a' in MS('abc'))
show('1 < MI', lambda: 1 < MI(2))
show('[1, 2] < ML', lambda: [1, 2] < ML([1, 3]))


# in-place operators on subclass instances
def iadd_ml():
    a = ML([1])
    b = a
    a += ML([2])
    a += [3]
    return a, a is b, type(a).__name__


def iadd_list_ml():
    a = [1]
    a += ML([2])
    return a


def iadd_ms():
    s = 'x'
    s += MS('y')
    return s


show('ML += ML', iadd_ml)
show('list += ML', iadd_list_ml)
show('str += MS', iadd_ms)


# plain user objects with host sequences
class P:
    pass


show('[] + P()', lambda: [] + P())
show("'s' + P()", lambda: 's' + P())
show('() + P()', lambda: () + P())
show("b'' + P()", lambda: b'' + P())
show('[1] * P()', lambda: [1] * P())
show("P() * 's'", lambda: P() * 's')
show('P() * [1]', lambda: P() * [1])
show("'%s' % P() works", lambda: type('%s' % P()).__name__)
