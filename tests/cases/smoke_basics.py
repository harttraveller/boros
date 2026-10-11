print("hello", 1 + 2)
x = [i * i for i in range(5)]
print(x, sum(x))


def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


print(fib(15))


class A:
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return f"A({self.v!r})"

    def __add__(self, o):
        return A(self.v + o.v)


print(A(1) + A(2), [A(3)])


def gen(n):
    for i in range(n):
        x = yield i
        if x:
            print("got", x)


g = gen(3)
print(next(g), g.send("hi"), list(g))
try:
    {}["k"]
except KeyError as e:
    print("caught", repr(e))


class E(Exception):
    pass


try:
    raise E("boom")
except Exception as e:
    print(type(e).__name__, e, isinstance(e, E), e.args)
