# A TypeError raised *while iterating* a starred operand must propagate unchanged.
def gen():
    yield 1
    raise TypeError("inner")


def f(*a):
    return a


for thunk in [lambda: f(*gen()), lambda: [*gen()], lambda: (*gen(),), lambda: {*gen()}]:
    try:
        thunk()
    except TypeError as e:
        print("TypeError:", e)
try:
    a, *b = gen()
except TypeError as e:
    print("TypeError:", e)
try:
    a, b = gen()
except TypeError as e:
    print("TypeError:", e)
try:
    for x, *y in [gen()]:
        pass
except TypeError as e:
    print("TypeError:", e)


class BadIter:
    def __iter__(self):
        raise TypeError("bad __iter__")


try:
    a, b = BadIter()
except TypeError as e:
    print("TypeError:", e)
try:
    a, *b = BadIter()
except TypeError as e:
    print("TypeError:", e)
try:
    f(*BadIter())
except TypeError as e:
    print("TypeError:", e)
