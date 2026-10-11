# compile() modes and source handling: 'exec', 'eval', 'single', bytes
# sources, leading whitespace in eval, and code objects reused.

code = compile('a = 1\nb = a + 1\n', '<exec>', 'exec')
ns = {}
exec(code, ns)
print(ns['a'], ns['b'])
exec(code, ns)
print(eval(compile('a * 10 + b', '<eval>', 'eval'), ns))
print(eval(compile(b'2 ** 8', '<bytes>', 'eval')))
exec(compile(b'c = "from bytes"', '<bytes>', 'exec'), ns)
print(ns['c'])
print(eval('  1 + 1'), eval('\t3'), eval('4\n'), eval('(5\n+\n6)'), eval('\n\n7'))
print(eval('x', {'x': 'globals'}), eval('x', {'x': 1}, {'x': 'locals'}))
print(eval('[i for i in range(3)]'), eval('lambda q: q * 2')(4))
print(eval(' "string" '), eval("'''tri\nple'''"))
print(eval('1;') if False else 'skip')
for bad in ['1;', 'x = 1', 'def f(): pass', '', '   ', '1\n2']:
    try:
        eval(bad)
        print(repr(bad), 'evaluated')
    except SyntaxError:
        print(repr(bad), 'SyntaxError')
exec('')
exec('   \n\n  # only a comment\n')
exec('\n\n\nprint("after blank lines")\n\n')
exec('if True:\n    print("no trailing newline")')
exec('x = 1 \\\n + 2\nprint(x)')
try:
    compile('1', '<bad>', 'nonsense')
except ValueError as e:
    print('ValueError', e)
