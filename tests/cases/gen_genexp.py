"""Generator expressions: laziness, early binding, scoping, errors."""


def noisy(tag, items):
    print('  iter', tag)
    for x in items:
        print('  produce', tag, x)
        yield x


# laziness: nothing runs until iteration (except evaluating the first iterable)
ge = (x * 2 for x in noisy('A', [1, 2]))
print('genexp created')
print(next(ge))
print(list(ge))

# the first iterable is evaluated immediately, later ones lazily
def make_list(tag):
    print('  evaluating', tag)
    return [1, 2]


ge = (a + b for a in make_list('outer') for b in make_list('inner'))
print('created nested')
print(list(ge))

# early binding of the first iterable
items = [1, 2, 3]
ge = (i for i in items)
items = ['replaced']
print(list(ge))

# ... but names in the element / conditions / inner iterables are late bound
factor = 10
ge = (i * factor for i in range(3))
factor = 100
print(list(ge))

limit = 1
ge = (i for i in range(5) if i > limit)
limit = 3
print(list(ge))

inner = [1]
ge = (i + j for i in range(2) for j in inner)
inner = [100, 200]
print(list(ge))

# errors in the first iterable surface at creation time
try:
    ge = (x for x in 42)
except TypeError as e:
    print('TypeError at creation:', e)

# errors in the element surface during iteration
ge = (1 / x for x in [1, 0])
print('created div genexp')
print(next(ge))
try:
    next(ge)
except ZeroDivisionError as e:
    print('ZeroDivisionError during iteration:', e)
print(next(ge, 'exhausted after error'))

# the loop variable does not leak
x = 'outer x'
total = sum(x for x in range(4))
print(total, x)

# genexp in a class body: first iterable sees the class scope, the rest do not
class Config:
    names = ['a', 'b']
    upper = list(n.upper() for n in names)
    try:
        bad = list(n + suffix for n in names)
    except NameError as e:
        error = str(e)
    suffix = '!'


print(Config.upper, Config.error)

def in_function():
    base = 5
    return list(base + i for i in range(3))


print(in_function())

# closure over loop variable of an enclosing function
def make_gens():
    gens = []
    for k in range(3):
        gens.append((k * i for i in range(2)))
    return gens


print([list(g) for g in make_gens()])

# genexp objects
ge = (i for i in range(3))
print(type(ge).__name__, ge.__name__, iter(ge) is ge)
print(ge.send(None), next(ge))
ge.close()
print(next(ge, 'closed'))

# genexp as sole argument and with other args
print(sum(i * i for i in range(5)), max((len(w), w) for w in ['aa', 'b', 'ccc']))
print(sorted((c for c in 'hello'), reverse=True))
print(' '.join(str(i) for i in range(3)), any(i > 3 for i in range(5)), all(i < 3 for i in range(5)))

# short-circuit: any/all stop consuming the genexp early
def watched():
    for i in range(10):
        print('  watched yields', i)
        yield i


print(any(i == 2 for i in watched()))

# nested genexps and conditions
matrix = [[1, 2, 3], [4, 5, 6]]
print(list(x for row in matrix for x in row if x % 2))
print(list(list(r * 10 for r in row) for row in matrix))
print(list((i, j) for i in range(3) if i for j in range(i) if j != 1))

# genexp with tuple unpacking target and walrus
pairs = [(1, 'a'), (2, 'b')]
print(list(f'{n}{s}' for n, s in pairs))
print(list((y := i * 2) for i in range(3)), y)

# genexp consumed partially by zip
ge = (i for i in range(10))
print(list(zip(ge, 'ab')), next(ge))

# genexp in a generator function referencing a local that changes
def changing():
    n = 1
    g = (n * i for i in range(3))
    n = 2
    yield list(g)


print(list(changing()))

# genexp passed through yield from
def gen_from_genexp():
    yield from (c.upper() for c in 'xyz')


print(list(gen_from_genexp()))

# genexp element that raises StopIteration -> RuntimeError
ge = (next(iter([])) for _ in range(1))
try:
    list(ge)
except RuntimeError as e:
    print('RuntimeError', e)
