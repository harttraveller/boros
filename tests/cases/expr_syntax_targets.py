# Invalid assignment / augmented-assignment / del / for targets and starred uses are rejected at compile time.
# Only detection is checked (SyntaxError vs ok), not the message.
srcs = [
    'a + 1 = 2',
    'f() = 1',
    'del f()',
    'a, *b, *c = d',
    '*a = b',
    'f() += 1',
    '(a, b) += 1',
    'True = 1',
    'None += 1',
    'x = 1 = 2',
    'del a + b',
    '[a, b] += 1',
    'lambda: x = 1',
    'del *a',
    'x = *a',
    'for x, *y, *z in w: pass',
    'for f() in x: pass',
    '[x for f() in y]',
    'def f(): x = yield = 1',
    '(*a)',
    'print((*a))',
    'x: int, y: int = 1, 2',
    'a, b: int',
    '1 if 2 else 3 = 4',
    '-x = 1',
    'not x = 1',
    'x == y = 1',
    'a and b = 1',
    'a if b',
    'x = 1 +',
    '(a, b) = c = 1',
    'del (a,)',
    'a.b, c[d], *e = f',
    'x[1:2] = y',
    'x[1:2:3, ...] = y',
    'a = b = *c,',
    '[*a] = b',
    '(x): int = 1',
    'x.y: int',
    'del x, (y, [z])',
    'del x[1:2], x.y',
    '*a, = b',
]
for s in srcs:
    try:
        compile(s, "<s>", "exec")
        print(repr(s), "ok")
    except SyntaxError:
        print(repr(s), "SyntaxError")
