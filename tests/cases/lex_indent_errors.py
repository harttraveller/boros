# Indentation errors raised by compile(): the exception class matters
# (IndentationError and TabError are SyntaxError subclasses that programs
# catch separately).  Also form feeds in indentation.

cases = [
    ('unexpected indent at start', '  x = 1\n'),
    ('unexpected indent later', 'x = 1\n    y = 2\n'),
    ('expected indented block', 'if 1:\nx = 1\n'),
    ('expected block at EOF', 'if 1:\n'),
    ('expected block in def', 'def f():\nreturn 1\n'),
    ('unindent mismatch', 'if 1:\n    x = 1\n  y = 2\n'),
    ('tab then 8 spaces', 'if 1:\n\tx = 1\n        y = 2\n'),
    ('8 spaces then tab', 'if 1:\n        x = 1\n\ty = 2\n'),
    ('space+tab consistent', 'if 1:\n \tx = 1\n \ty = 2\n'),
    ('form feed resets column', 'if 1:\n\f    x = 3\n    x = x + 1\n'),
    ('form feed alone on a line', 'x = 0\nif 1:\n    x = 5\n\f\nx += 1\n'),
    ('plain syntax error', 'x = = 1\n'),
]
for label, src in cases:
    try:
        compile(src, '<indent>', 'exec')
        print(label, '-> ok')
    except SyntaxError as e:
        print(label, '->', type(e).__name__, isinstance(e, SyntaxError))

try:
    exec('if True:\n  a = 1\n b = 2\n')
except IndentationError:
    print('caught IndentationError')
except SyntaxError:
    print('caught only as SyntaxError')
print(issubclass(TabError, IndentationError), issubclass(IndentationError, SyntaxError))
