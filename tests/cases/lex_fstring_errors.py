# Malformed f-strings must raise SyntaxError from compile()/exec()
# (messages are not compared).

sources = [
    "f'{}'",
    "f'{ }'",
    "f'}'",
    "f'{'",
    "f'{x'",
    "f'{x!}'",
    "f'{x!z}'",
    "f'{x!r'",
    "f'{x:'",
    "f'{!r}'",
    "f'{:x}'",
    "f'{=}'",
    "f'{x}}'",
    "f'{{}'",
    "f'{a b}'",
    "f'{x!r=}'",
    "f'{lambda x: x}'",
    "f'{*x}'",
    "f'{x # comment}'",
    "f'{x:{y:{z}}}'",
    "f'{x! r}'",
    "f'''{x'''",
    "f'abc",
    "f'{x:\n>5}'",
    # valid ones, for contrast
    "f'{x}'",
    "f'{x!r:>{w}}'",
    "f'{{}}'",
    "f'{x:{w}}'",
]
for src in sources:
    try:
        compile(src, '<fstring>', 'eval')
        result = 'ok'
    except SyntaxError:
        result = 'SyntaxError'
    except Exception as e:
        result = 'wrong exception ' + type(e).__name__
    print(repr(src), result)

# also through exec() and eval() directly
for label, fn in (('exec', exec), ('eval', eval)):
    try:
        fn("f'{}'")
        print(label, 'no error')
    except SyntaxError:
        print(label, 'SyntaxError')
