# SyntaxError objects raised by compile()/exec() carry the filename and
# line number of the offending source (messages are not compared).

cases = [
    ('<one>', 'x = (1,\n     2,\n     3 +)\n'),
    ('<two>', 'a = 1\nb = 2\nc = = 3\n'),
    ('<three>', 'def f():\n    return 1\n  x = 2\n'),
    ('<four>', 'x = 1\ny = "unterminated\n'),
    ('<five>', 'if True:\n    pass\n    $\n'),
    ('<six>', 'x = 1\ns = f"{}"\n'),
    ('<seven>', 'x = 1\nx = 0777\n'),
    # line counting after multi-line tokens
    ('<eight>', 'x = """a\nb\nc"""\ny = = 1\n'),
    ('<nine>', 'x = (1,\n2)\ny = \\\n3\nz = = 1\n'),
    ('<ten>', 'x = f"""{\n1\n}"""\nz = = 1\n'),
    ('<eleven>', "s = 'a\\\nb'\nz = = 1\n"),
]
for filename, src in cases:
    try:
        compile(src, filename, 'exec')
        print(filename, 'compiled')
    except SyntaxError as e:
        print(filename, 'lineno', e.lineno, 'filename', e.filename, type(e.msg).__name__)
try:
    exec('a = 1\n\nb = (')
except SyntaxError as e:
    print('exec', e.filename, type(e.lineno).__name__)
try:
    eval('1 +\n')
except SyntaxError as e:
    print('eval', e.filename, e.lineno)
