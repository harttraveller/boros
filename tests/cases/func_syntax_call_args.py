# compile() rejects invalid call argument lists with CPython's messages.
sources = [
    'f(a=1, a=2)\n',
    'f(a=1, b)\n',
    'f(**k, *a)\n',
    'f(**k, b)\n',
    'f(x for x in y, 1)\n',
    'f(1, x for x in y)\n',
    'f(x for x in y)\n',
    'f(*a, b, c=1, *d, **e)\n',
]
for src in sources:
    try:
        compile(src, '<src>', 'exec')
        print('compiled OK:', repr(src))
    except SyntaxError as e:
        print('SyntaxError:', e.msg.split(' (<src>')[0])
