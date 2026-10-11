"""yield in less common syntactic positions: assignment / del / augmented
assignment targets, except clauses, match guards, default values of
nested functions and lambdas.  Each snippet is compiled separately (via
exec) so a failure in one position does not hide the others."""

SNIPPETS = {
    'store subscript target': '''
def g():
    x = [1, 2, 3]
    x[(yield 'index?')] = yield 'value?'
    yield x
it = g()
out = [next(it), it.send('V'), it.send(0)]
''',
    'store attribute target object': '''
class O:
    pass
o1, o2 = O(), O()
def g():
    (yield 'obj?').attr = yield 'value?'
    yield (getattr(o1, 'attr', None), getattr(o2, 'attr', None))
it = g()
out = [next(it), it.send('A'), it.send(o2)]
''',
    'tuple target with yield index': '''
def g():
    d = {}
    d[(yield 'k1')], d[(yield 'k2')] = yield 'pair?'
    yield sorted(d.items())
it = g()
out = [next(it), it.send((10, 20)), it.send('a'), it.send('b')]
''',
    'del subscript': '''
def g():
    d = {'a': 1, 'b': 2}
    del d[(yield 'key?')]
    yield d
it = g()
out = [next(it), it.send('a')]
''',
    'augmented subscript index': '''
def g():
    d = {'k': 1}
    d[(yield 'index?')] += 10
    yield d
it = g()
out = [next(it), it.send('k')]
''',
    'augmented attribute object': '''
class O:
    n = 1
o = O()
def g():
    (yield 'obj?').n *= 5
    yield o.n
it = g()
out = [next(it), it.send(o)]
''',
    'except clause type': '''
def g():
    try:
        raise KeyError('x')
    except (yield 'which?'):
        yield 'caught'
it = g()
out = [next(it), it.send(KeyError)]
''',
    'match guard': '''
def g():
    match (yield 'subject?'):
        case 1 if (yield 'guard?'):
            yield 'matched'
        case _:
            yield 'default'
it = g()
out = [next(it), it.send(1), it.send(True)]
''',
    'nested def default': '''
def g():
    def f(x=(yield 'default?')):
        return x
    yield f()
it = g()
out = [next(it), it.send(5)]
''',
    'lambda default': '''
def g():
    f = lambda x=(yield 'default?'): x * 2
    yield f()
it = g()
out = [next(it), it.send(6)]
''',
    'class keyword argument': '''
class Base:
    def __init_subclass__(cls, tag=None):
        cls.tag = tag
def g():
    class C(Base, tag=(yield 'tag?')):
        pass
    yield C.tag
it = g()
out = [next(it), it.send('T')]
''',
    'await in store subscript target': '''
import asyncio
async def k(x):
    await asyncio.sleep(0)
    return x
async def main():
    d = {}
    d[await k('key')] = await k('value')
    return d
out = asyncio.run(main())
''',
    'await in augmented subscript index': '''
import asyncio
async def k(x):
    await asyncio.sleep(0)
    return x
async def main():
    d = {'n': 1}
    d[await k('n')] += 1
    return d
out = asyncio.run(main())
''',
}

for label, src in SNIPPETS.items():
    ns = {}
    try:
        exec(src, ns)
        print('%-32s %r' % (label + ':', ns['out']))
    except Exception as e:
        print('%-32s %s: %s' % (label + ':', type(e).__name__, str(e).split(' (')[0]))
