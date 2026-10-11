# Errors that CPython's compiler reports as SyntaxError although the
# source tokenizes: control flow outside loops, bad global/nonlocal
# declarations, duplicate parameters, malformed call arguments and
# parameter lists, __future__ imports, walrus/async in comprehensions.
# Each snippet is exec()'d; nothing in it may run before the error.

groups = {
    'loop control': [
        "break",
        "continue",
        "if 1:\n    break",
        "def f():\n    break",
        "def f():\n    for x in []:\n        pass\n    continue",
        "for x in []:\n    def g():\n        break",
        "for x in []:\n    class C:\n        break",
        "while 0:\n    pass\nelse:\n    break",
    ],
    'global/nonlocal': [
        "nonlocal x",
        "class C:\n    nonlocal x",
        "def f():\n    nonlocal x",
        "def f():\n    x = 1\n    global x",
        "def f():\n    print(x)\n    global x",
        "def f(a):\n    global a",
        "def f(a):\n    nonlocal a",
        "def f():\n    global x\n    def g():\n        nonlocal x",
        "def f():\n    x = 1\n    def g():\n        x = 2\n        nonlocal x",
        "def f():\n    x: int = 1\n    global x",
        "x = 1\ndef f():\n    global x\n    nonlocal x",
    ],
    'parameters': [
        "def f(a, a): pass",
        "def f(a, *, a): pass",
        "def f(a, *a): pass",
        "def f(a, **a): pass",
        "def f(a, /, a): pass",
        "lambda a, a: 1",
        "def f(*): pass",
        "def f(*, **k): pass",
        "def f(**k, a): pass",
        "def f(**k, *a): pass",
        "def f(*a, *b): pass",
        "def f(**a, **b): pass",
        "def f(a=1, /, b): pass",
        "def f(/, a): pass",
        "def f(a, /, b, /): pass",
        "def f(*, a, /): pass",
    ],
    'call arguments': [
        "g(a=1, a=2)",
        "g(sep='', sep='')",
        "g(a=1, 2)",
        "g(**{}, 2)",
        "g(**{}, *[])",
        "g(x for x in [], 1)",
        "g(1, x for x in [])",
        "g(*x for x in [])",
    ],
    '__future__': [
        "from __future__ import braces",
        "from __future__ import nonexistent_feature",
        "x = 1\nfrom __future__ import annotations",
    ],
    'comprehensions': [
        "[i := 0 for i in range(3)]",
        "[[(j := 0) for j in range(2)] for i in range(2)]",
        "class C:\n    [(j := i) for i in range(3)]",
        "[(i := 1) for _ in range(3) for i in range(2)]",
        "[x for x in (y := [1, 2])]",
        "[i async for i in []]",
        "def f():\n    return [i async for i in []]",
        "def f():\n    return [await i for i in []]",
    ],
}
valid = [
    "def f():\n    global x\n    x = 1",
    "def f():\n    import os\n    global os",
    "def f():\n    from os import path\n    global path",
    "def f():\n    [x for z in []]\n    global x",
    "def f():\n    lambda: x\n    global x",
    "def f():\n    x = 1\n    def g():\n        nonlocal x\n        x = 2",
    "for x in []:\n    if x:\n        continue\n    break",
    "while 0:\n    try:\n        break\n    finally:\n        continue",
    "def f(a, /, b, *, c): pass",
    "def f(*, a): pass",
    "g(*[], **{})",
    "g(*[], sep='', *[])",
    "g(sep='', *[])",
    "g(x for x in [])",
    "from __future__ import annotations",
    "'''doc'''\nfrom __future__ import annotations",
    "[y := i for i in range(3)]",
    "async def f():\n    return [i async for i in x]",
]


def noop(*args, **kwargs):
    pass


for label, sources in groups.items():
    print('--', label)
    for src in sources:
        ran = []
        try:
            exec('ran.append(1)\n' + src, {'ran': ran, 'g': noop})
            result = 'no SyntaxError'
        except SyntaxError:
            result = 'SyntaxError'
        except Exception as e:
            result = 'no SyntaxError (%s)' % type(e).__name__
        print(repr(src), result, 'ran' if ran else '')
print('-- valid')
for src in valid:
    try:
        exec(src, {'g': noop})
        print(repr(src), 'ok')
    except SyntaxError:
        print(repr(src), 'SyntaxError')
