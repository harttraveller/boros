# Recursion within CPython's default recursion limit.


def depth(n):
    if n == 0:
        return 0
    return 1 + depth(n - 1)


print(depth(900))


def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print([fib(i) for i in range(15)])


def ack(m, n):
    if m == 0:
        return n + 1
    if n == 0:
        return ack(m - 1, 1)
    return ack(m - 1, ack(m, n - 1))


print(ack(2, 3))


# mutual recursion
def is_even(n):
    return True if n == 0 else is_odd(n - 1)


def is_odd(n):
    return False if n == 0 else is_even(n - 1)


print(is_even(500), is_odd(501), is_odd(10))


# recursion with accumulating arguments and defaults
def flatten(x, out=None):
    if out is None:
        out = []
    if isinstance(x, list):
        for y in x:
            flatten(y, out)
    else:
        out.append(x)
    return out


print(flatten([1, [2, [3, [4, [5]]]], 6]))


# recursive generator
def tree(n):
    if n == 0:
        yield 0
        return
    yield n
    yield from tree(n - 1)


print(sum(tree(200)))


# permutations by recursion
def perms(s):
    if len(s) <= 1:
        return [s]
    out = []
    for i, c in enumerate(s):
        for p in perms(s[:i] + s[i + 1:]):
            out.append(c + p)
    return out


print(perms('abcd')[:6], len(perms('abcd')))


# recursive method and recursive lambda
class Node:
    def __init__(self, v, kids=()):
        self.v = v
        self.kids = list(kids)

    def total(self):
        return self.v + sum(k.total() for k in self.kids)


root = Node(1, [Node(2, [Node(4)]), Node(3)])
print(root.total())
fact = lambda n: 1 if n <= 1 else n * fact(n - 1)
print(fact(20))


# recursion through a closure
def hanoi(n):
    moves = []

    def move(k, a, b, c):
        if k:
            move(k - 1, a, c, b)
            moves.append((a, c))
            move(k - 1, b, a, c)
    move(n, 'A', 'B', 'C')
    return moves


print(len(hanoi(8)), hanoi(2))


# exceptions propagate through many recursive frames
def explode(n):
    if n == 0:
        raise ValueError('bottom')
    return explode(n - 1)


try:
    explode(300)
except ValueError as e:
    print('caught', e)


# deep recursion in a try/finally chain
order = []


def unwind(n):
    try:
        if n:
            unwind(n - 1)
    finally:
        order.append(n)


unwind(5)
print(order)
