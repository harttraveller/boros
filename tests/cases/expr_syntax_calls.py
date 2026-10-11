# Invalid call argument orderings / repeated keywords / unparenthesized generators.
# Only detection is checked (SyntaxError vs ok), not the message.
srcs = [
    'f(a=1, a=2)',
    'f(**d, *a)',
    'f(a=1, b)',
    'f(**d, b)',
    'f(x for x in y, 1)',
    'print(1 2)',
    '{**a for a in b}',
    '[*a for a in b]',
    'print(*a, *b, **c, **d)',
    'f(*a, b=1, *c)',
    'f(b=1, *c)',
    '{1: 2, **a, 3: 4}',
    '{*a, *b}',
    '[*a]',
    'f(x for x in y)',
    'f(a, *b, c, d=1, **e)',
]
for s in srcs:
    try:
        compile(s, "<s>", "exec")
        print(repr(s), "ok")
    except SyntaxError:
        print(repr(s), "SyntaxError")
