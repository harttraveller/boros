# compile() rejects invalid parameter lists with CPython's messages.
sources = [
    'def f(a, a):\n    pass\n',
    'lambda a, a: 0\n',
    'def f(a, *, a):\n    pass\n',
    'def f(a=1, b):\n    pass\n',
    'lambda a=1, b: 0\n',
    'def f(*, **kw):\n    pass\n',
    'def f(*):\n    pass\n',
    'def f(**kw, a):\n    pass\n',
    'def f(*a, *b):\n    pass\n',
    'def f(/, a):\n    pass\n',
    'def f(a, /, b, /):\n    pass\n',
    'def f(*a, /):\n    pass\n',
    'def f(a, /, b=1, *c, d, **e):\n    pass\n',
]
for src in sources:
    try:
        compile(src, '<src>', 'exec')
        print('compiled OK:', repr(src))
    except SyntaxError as e:
        print('SyntaxError:', e.msg.split(' (<src>')[0])
