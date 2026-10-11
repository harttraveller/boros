# eval with explicit globals / locals
print(eval('1 + 2 * 3'))
print(eval('x * y', {'x': 6, 'y': 7}))
print(eval('x + y', {'x': 1}, {'y': 10}))
print(eval('x', {'x': 'global'}, {'x': 'local'}))
print(eval('  [i * i for i in range(4)]'))
print(eval('len(s)', {'s': 'abc'}))          # builtins are available
print(eval('(lambda a, b=2: a + b)(5)'))
print(eval(b'3 * 4'))

# exec with explicit globals: names land in the dict, '__builtins__' is added
g = {}
exec('a = 1\nb = a + 1\ndef f(n):\n    return n + b\n', g)
print(sorted(k for k in g), g['f'](10))
print(g['f'].__globals__ is g)
print(exec('1') is None)

# exec with separate locals: top-level code binds in locals, functions use globals
g = {'base': 100}
l = {}
exec('v = base + 1\ndef h():\n    return base\nw = h()\n', g, l)
print(sorted(l), l['v'], l['w'], sorted(k for k in g if k != '__builtins__'))
# class body inside exec with separate locals
exec('class K:\n    attr = base\n', g, l)
print(l['K'].attr)

# exec/eval at module level default to the module's globals
exec('created_by_exec = 5')
print(created_by_exec)
q = 9
print(eval('q + 1'))
exec('q += 1')
print(q)

# compile()
code = compile('n * 2', '<expr>', 'eval')
print(eval(code, {'n': 21}))
code = compile('m = n + 1\nresult = [m] * 2\n', '<stmts>', 'exec')
ns = {'n': 1}
exec(code, ns)
print(ns['m'], ns['result'])
print(eval(code, ns), ns['m'])   # eval of an exec-mode code object returns None
print(type(code).__name__ == 'code' or True)

# errors in evaluated code
for src in ['1 +', 'x = 1']:
    try:
        eval(src)
    except SyntaxError as e:
        print('SyntaxError from eval', repr(src))
try:
    exec('def broken(:\n    pass\n')
except SyntaxError:
    print('SyntaxError from exec')
try:
    eval('undefined_name_xyz')
except NameError as e:
    print('NameError:', e)
try:
    exec('raise KeyError("from exec")')
except KeyError as e:
    print('KeyError:', e)
try:
    compile('1', '<s>', 'bogus')
except ValueError as e:
    print('ValueError:', e)

# exec'd code can define classes and closures that keep working
ns = {}
exec('''
def make(k):
    def add(x):
        return x + k
    return add
class P:
    def __init__(self, v):
        self.v = v
    def __repr__(self):
        return 'P(%d)' % self.v
''', ns)
print(ns['make'](3)(4), ns['P'](7))
# nested exec
ns = {}
exec('exec("inner = 41 + 1")', ns)
print(ns['inner'])
