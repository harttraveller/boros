# compile() rejects invalid global / nonlocal / return / yield usage with
# CPython's messages.
sources = [
    'def f():\n    nonlocal x\n',
    'nonlocal x\n',
    'def f(x):\n    global x\n',
    'def f(x):\n    nonlocal x\n',
    'def f():\n    x = 1\n    global x\n',
    'def f():\n    print(x)\n    global x\n',
    'def f():\n    x = 1\n    def g():\n        global x\n        nonlocal x\n',
    'def f():\n    x = 1\n    def g():\n        x = 2\n        nonlocal x\n',
    'def f():\n    nonlocal y\n    y = 1\n',
    'class C:\n    nonlocal z\n',
    'return 1\n',
    'yield 1\n',
    'class C:\n    return 1\n',
    'class C:\n    yield 1\n',
    'def f():\n    x = 1\n    def g():\n        nonlocal x\n        x = 2\n    global q\n    return g\n',
]
for src in sources:
    try:
        compile(src, '<src>', 'exec')
        print('compiled OK:', repr(src))
    except SyntaxError as e:
        print('SyntaxError:', e.msg.split(' (<src>')[0])
