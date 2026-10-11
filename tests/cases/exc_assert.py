# assert statements and AssertionError details.


def check(cond, *msg):
    try:
        if msg:
            assert cond, msg[0]
        else:
            assert cond
    except AssertionError as e:
        return 'AssertionError(%r) args=%r' % (str(e), e.args)
    return 'ok'


print(check(True))
print(check(False))
print(check(0, 'zero'))
print(check([], ['list', 'msg']))
print(check(None, 42))
print(check(1, 'not evaluated'))

count = 0


def side():
    global count
    count += 1
    return 'side effect'


print(check(True, side()), count)


def lazy_message():
    try:
        assert True, undefined_name_never_evaluated
    except NameError:
        return 'evaluated!'
    return 'message not evaluated'


print(lazy_message())


class Val:
    def __init__(self, v):
        self.v = v

    def __bool__(self):
        return self.v > 0

    def __repr__(self):
        return 'Val(%d)' % self.v


print(check(Val(1), 'pos'), check(Val(-1), 'neg %r' % Val(-1)))


def f(x):
    assert isinstance(x, int), 'expected int, got %s' % type(x).__name__
    return x * 2


print(f(2))
try:
    f('a')
except AssertionError as e:
    print(e)

# AssertionError with no message has empty args and str
try:
    assert 1 == 2
except AssertionError as e:
    print(repr(e), e.args, str(e) == '')

# assert at the end: uncaught assertion with message
data = [1, 2, 3]
assert len(data) == 3, 'length ok'
assert sum(data) == 7, 'sum was %d' % sum(data)
