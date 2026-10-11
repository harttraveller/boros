# Assignment-expression restrictions.
# Only detection is checked (SyntaxError vs ok), not the message.
srcs = [
    '[i := 0 for i in range(3)]',
    'x := 1',
    'f(a=n := 1)',
    'class C:\n [x := 1 for y in z]',
    '[x for x in range(3) if (x := 1)]',
    '(lambda: x := 1)',
    '[[(j := k) for k in range(2)] for j in range(2)]',
    'if (n := 1): pass',
    'f(n := 1)',
    'x[n := 1]',
    '[(j := 0) for i in range(3)]',
    'lambda: (y := 1)',
    '(x := 1)',
    'y = (x := 1)',
    'def f():\n [(z := i) for i in range(2)]',
]
for s in srcs:
    try:
        compile(s, "<s>", "exec")
        print(repr(s), "ok")
    except SyntaxError:
        print(repr(s), "SyntaxError")
