# compile() must report compile-time SyntaxErrors itself (not only when
# the code object is later executed), and must not run any code.

sources = [
    "return 1",
    "class C:\n    return 1",
    "yield 1",
    "x = yield",
    "class C:\n    yield 1",
    "await x",
    "x = *a",
    "print(*a for a in b)",
    "*a = [1]",
    "*a, *b = [1, 2]",
    "a, *b, c, *d = range(9)",
    "def f():\n    async with x:\n        pass",
    "def f():\n    async for i in x:\n        pass",
    "def f():\n    return 1\nreturn 2",
    "def f():\n    def g():\n        return 1\nyield 3",
    # valid
    "def f():\n    return 1",
    "def f():\n    yield 1",
    "async def f():\n    await x",
    "a, *b = [1, 2]",
    "[*a, *b]",
]
for src in sources:
    try:
        code = compile(src, '<compile>', 'exec')
        stage = 'compiled'
    except SyntaxError:
        print(repr(src), 'compile: SyntaxError')
        continue
    try:
        exec(code, {'a': [], 'b': [], 'x': None})
        stage += ', executed'
    except SyntaxError:
        stage += ', exec: SyntaxError'
    except Exception as e:
        stage += ', exec: ' + type(e).__name__
    print(repr(src), stage)

for src in ['(yield)', '(await x)', '*a']:
    try:
        compile(src, '<compile>', 'eval')
        print(repr(src), 'eval-mode compiled')
    except SyntaxError:
        print(repr(src), 'eval-mode SyntaxError')
