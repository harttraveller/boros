# compile(..., 'single') (interactive mode): expression statements are
# echoed through sys.displayhook; only one statement is allowed.
import sys

exec(compile('1 + 1', '<single>', 'single'))
exec(compile('None', '<single>', 'single'))
exec(compile('"text"', '<single>', 'single'))
exec(compile('x = 5', '<single>', 'single'))
exec(compile('for i in range(2): i\n', '<single>', 'single'))
exec(compile('if True:\n    7\n', '<single>', 'single'))
exec(compile('[1, 2]', '<single>', 'single'))
for bad in ['a = 1\nb = 2', 'x = 1; y = 2', '1\n2\n']:
    try:
        compile(bad, '<single>', 'single')
        print(repr(bad), 'compiled')
    except SyntaxError:
        print(repr(bad), 'SyntaxError')
exec(compile('print("side effect"); 8', '<single>', 'single'))
exec(compile('def f():\n    9\n', '<single>', 'single'))
f()
exec(compile('x = 3  # comment\n\n', '<single>', 'single'))
exec(compile('x\n', '<single>', 'single'), {'x': 'from globals'})
calls = []
sys.displayhook = lambda v: calls.append(v)
exec(compile('41 + 1', '<single>', 'single'))
sys.displayhook = sys.__displayhook__
print('displayhook got', calls)
exec(compile('"text"', '<single>', 'single'))
import builtins
print('underscore is', builtins._)
