# Compile-time scoping errors (SyntaxError) for global / nonlocal misuse.
sources = [
    ('nonlocal at module level', 'nonlocal x\n'),
    ('nonlocal without binding', 'def f():\n    nonlocal q\n    q = 1\n'),
    ('nonlocal unused, no binding', 'def f():\n    def g():\n        nonlocal q\n'),
    ('nonlocal names a global', 'def f():\n    global z\n    def g():\n        nonlocal z\n        z = 1\n'),
    ('used before global', 'def f():\n    print(x)\n    global x\n'),
    ('assigned before global', 'def f():\n    x = 1\n    global x\n'),
    ('parameter and global', 'def f(x):\n    global x\n'),
    ('parameter and nonlocal', 'def f():\n    x = 1\n    def g(x):\n        nonlocal x\n'),
    ('assigned before nonlocal', 'def f():\n    x = 1\n    def g():\n        x = 2\n        nonlocal x\n'),
    ('nonlocal in class at module level', 'class C:\n    nonlocal y\n'),
    ('global and nonlocal', 'def f():\n    x = 1\n    def g():\n        global x\n        nonlocal x\n'),
]
for label, src in sources:
    try:
        compile(src, '<scope>', 'exec')
        print(label, '-> compiled')
    except SyntaxError as e:
        print(label, '->', e.msg, e.lineno)

# the error is raised when the module is compiled, before any code runs
try:
    exec('print("should not print")\ndef f():\n    nonlocal nothing\n')
except SyntaxError as e:
    print('exec ->', e.msg)
