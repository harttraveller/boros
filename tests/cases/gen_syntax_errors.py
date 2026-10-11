"""Compile-time errors specific to generators and coroutines.  Each
snippet is compiled and run separately with exec(); the message is
printed without the "(file, line N)" location part."""

SNIPPETS = [
    ('unparenthesized genexp argument', '''
def f(y):
    return f(x for x in y, 1)
'''),
    ('yield at module level', '''
yield 1
'''),
    ('yield in class body', '''
class C:
    x = (yield)
'''),
    ('yield from in async def', '''
async def f():
    yield from [1]
'''),
    ('return value in async generator', '''
async def f():
    yield 1
    return 2
'''),
    ('yield in list comprehension', '''
def f():
    return [(yield) for x in range(3)]
'''),
    ('yield in generator expression', '''
def f():
    return list((yield x) for x in range(3))
'''),
    ('await in plain def', '''
def f():
    await g()
'''),
    ('async for in plain def', '''
def f():
    async for x in y:
        pass
'''),
    ('async with in plain generator', '''
def f():
    yield
    async with y:
        pass
'''),
    ('async comprehension in plain def', '''
def f():
    return [x async for x in y]
'''),
    ('valid: yield in lambda', '''
f = lambda: (yield 5)
result = list(f())
'''),
    ('valid: await in nested async def', '''
def outer():
    async def inner():
        return await g()
    return inner
result = outer().__name__
'''),
]

for label, src in SNIPPETS:
    ns = {}
    try:
        exec(src, ns)
        print('%-36s compiled, result=%r' % (label + ':', ns.get('result')))
    except SyntaxError as e:
        print('%-36s SyntaxError: %s' % (label + ':', str(e.msg).split(' (')[0]))
