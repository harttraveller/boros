"""Recursive generators: tree traversals via yield from, permutations,
flattening, mutual recursion and generator pipelines."""


class Node:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


def insert(root, v):
    if root is None:
        return Node(v)
    if v < root.value:
        root.left = insert(root.left, v)
    else:
        root.right = insert(root.right, v)
    return root


def inorder(n):
    if n is not None:
        yield from inorder(n.left)
        yield n.value
        yield from inorder(n.right)


def preorder(n):
    if n:
        yield n.value
        for child in (n.left, n.right):
            yield from preorder(child)


def postorder(n):
    if n is None:
        return
    yield from postorder(n.left)
    yield from postorder(n.right)
    yield n.value


def depth_first_with_depth(n, depth=0):
    if n is None:
        return 0
    yield (n.value, depth)
    a = yield from depth_first_with_depth(n.left, depth + 1)
    b = yield from depth_first_with_depth(n.right, depth + 1)
    return 1 + max(a, b)


root = None
for v in [50, 30, 70, 20, 40, 60, 80, 35, 45, 65]:
    root = insert(root, v)
print(list(inorder(root)))
print(list(preorder(root)))
print(list(postorder(root)))
g = depth_first_with_depth(root)
pairs = []
try:
    while True:
        pairs.append(next(g))
except StopIteration as e:
    print(pairs)
    print('height', e.value)

# a deep (degenerate) tree: recursion depth ~ 60 through yield from
deep = None
for v in range(60):
    deep = insert(deep, v)
print(sum(inorder(deep)), list(inorder(deep))[-3:])

# permutations / subsets / combinations
def permutations(items):
    if len(items) <= 1:
        yield list(items)
        return
    for i in range(len(items)):
        rest = items[:i] + items[i + 1:]
        for p in permutations(rest):
            yield [items[i]] + p


print([''.join(p) for p in permutations('abc')])
print(len(list(permutations([1, 2, 3, 4, 5]))))

def subsets(items):
    if not items:
        yield ()
        return
    first, rest = items[0], items[1:]
    for s in subsets(rest):
        yield s
        yield (first,) + s


print(sorted(subsets((1, 2, 3))))

def compositions(n, parts):
    if parts == 1:
        yield (n,)
        return
    for i in range(n + 1):
        for rest in compositions(n - i, parts - 1):
            yield (i,) + rest


print(list(compositions(3, 2)))

# flatten arbitrarily nested lists
def flatten(x):
    if isinstance(x, (list, tuple)):
        for item in x:
            yield from flatten(item)
    else:
        yield x


print(list(flatten([1, [2, [3, [4, (5, 6)]], 7], [[[]]], 8])))

# mutual recursion between generators
def evens(n):
    if n >= 0:
        yield ('even', n)
        yield from odds(n - 1)


def odds(n):
    if n >= 0:
        yield ('odd', n)
        yield from evens(n - 1)


print(list(evens(5)))

# hanoi
def hanoi(n, src='A', dst='C', via='B'):
    if n:
        yield from hanoi(n - 1, src, via, dst)
        yield (n, src, dst)
        yield from hanoi(n - 1, via, dst, src)


moves = list(hanoi(4))
print(len(moves), moves[:4])

# lazy prime sieve via a chain of filtering generators
def integers_from(n):
    while True:
        yield n
        n += 1


def sieve(gen):
    p = next(gen)
    yield p
    yield from sieve(x for x in gen if x % p)


primes = sieve(integers_from(2))
print([next(primes) for _ in range(15)])

# generator pipeline
def read_records():
    yield from ['alice,30', 'bob,x', 'carol,25', '', 'dave,41']


def parse(lines):
    for line in lines:
        if not line:
            continue
        name, _, age = line.partition(',')
        try:
            yield name, int(age)
        except ValueError:
            print('  skipping', repr(line))


def adults(records, min_age):
    for name, age in records:
        if age >= min_age:
            yield name


print(list(adults(parse(read_records()), 26)))

# recursive generator with send: a tiny tokenizer/evaluator coroutine
def tokens(s):
    num = ''
    for ch in s:
        if ch.isdigit():
            num += ch
        else:
            if num:
                yield int(num)
                num = ''
            if ch in '+-*()':
                yield ch
    if num:
        yield int(num)


def expr(toks):
    value = yield from term(toks)
    while toks and toks[0] in '+-':
        op = toks.pop(0)
        rhs = yield from term(toks)
        yield ('apply', op)
        value = value + rhs if op == '+' else value - rhs
    return value


def term(toks):
    value = yield from factor(toks)
    while toks and toks[0] == '*':
        toks.pop(0)
        rhs = yield from factor(toks)
        yield ('apply', '*')
        value *= rhs
    return value


def factor(toks):
    t = toks.pop(0)
    if t == '(':
        v = yield from expr(toks)
        toks.pop(0)
        return v
    yield ('push', t)
    return t


def evaluate(s):
    g = expr(list(tokens(s)))
    trace = []
    try:
        while True:
            trace.append(next(g))
    except StopIteration as e:
        return e.value, len(trace)


print(evaluate('2*(3+4)-5'), evaluate('1+2*3*4-(5-6)'))
