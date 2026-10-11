# Lambdas: defaults, closures, nesting, every parameter kind.
k = 1
lam = lambda a, b=k: (a, b)
k = 2
print(lam(0), lam(0, 5))

curry = lambda a: lambda b: lambda c: a + b + c
print(curry(1)(2)(3))

full = lambda a, /, b=2, *args, c, d=4, **kw: (a, b, args, c, d, kw)
print(full(1, c=3), full(1, 2, 3, 4, c=5, e=6))

fact = lambda n: 1 if n <= 1 else n * fact(n - 1)
print(fact(10))


def make_adders():
    return [lambda x, n=n: x + n for n in range(3)]


def make_late():
    return [lambda x: x + n for n in range(3)]


print([f(10) for f in make_adders()], [f(10) for f in make_late()])

compose = lambda *fs: lambda x: [x := f(x) for f in fs][-1] if fs else x
print(compose(lambda v: v + 1, lambda v: v * 10)(2), compose()(7))

pairs = [(1, 'b'), (2, 'a'), (0, 'c')]
print(sorted(pairs, key=lambda p: p[1]), max(pairs, key=lambda p: p[0]))
print(list(map(lambda x: x ** 2, range(5))), list(filter(lambda s: s.isupper(), 'aBcD')))

# immediately invoked
print((lambda x, y: x * y)(6, 7), (lambda: 'no args')())

# lambda in a class body is a method
class C:
    double = lambda self, x: 2 * x
    name = (lambda: 'evaluated at class creation')()


print(C().double(21), C.name)

# conditional and boolean expressions in a lambda body
sign = lambda x: 'pos' if x > 0 else ('zero' if x == 0 else 'neg')
print([sign(v) for v in (-2, 0, 3)])
first_truthy = lambda *a: next((v for v in a if v), None)
print(first_truthy(0, '', 'x', 'y'), first_truthy())

# lambdas capture loop variables late; walrus inside lambda body is local
fs = []
for i in range(3):
    fs.append(lambda: i * 10)
print([f() for f in fs])
counter = lambda: (n := 5) + n
print(counter())

# errors raised inside lambdas
try:
    (lambda: 1 / 0)()
except ZeroDivisionError as e:
    print('ZeroDivisionError:', e)
try:
    (lambda x: x)()
except TypeError as e:
    print('TypeError:', e)
print((lambda: None).__name__, (lambda: None).__doc__)
