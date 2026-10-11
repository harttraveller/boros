# Invalid match patterns are rejected at compile time.
# Only detection is checked (SyntaxError vs ok), not the message.
srcs = [
    'match x:\n case y:\n  pass\n case 1:\n  pass',
    'match x:\n case _:\n  pass\n case 1:\n  pass',
    'match x:\n case [*a, *b]:\n  pass',
    "match x:\n case {'a': 1, 'a': 2}:\n  pass",
    'match x:\n case P(x=1, x=2):\n  pass',
    'match x:\n case [a, a]:\n  pass',
    'match x:\n case a | b:\n  pass',
    'match x:\n case [a] | [b]:\n  pass',
    'match x:\n case 1 + 1:\n  pass',
    'match x:\n case {**_}:\n  pass',
    "match x:\n case f'x':\n  pass",
    'match x:\n case -x:\n  pass',
    'match x:\n case (a as b) as a:\n  pass',
    "match x:\n case {'a': 1, **r, 'b': 2}:\n  pass",
    'match x:\n case 1:\n  pass\n case 2 if:\n  pass',
    'match x:\n case [a, *_, b] | (a, b):\n  pass',
    "match x:\n case {'a': 1, **r}:\n  pass",
    'match x:\n case -1 | -1.5 | 1 + 2j | -3 - 4j:\n  pass',
    'match x:\n case a.b.c | a.d():\n  pass',
    'match x:\n case y if y:\n  pass\n case 1:\n  pass',
    'match x:\n case (y):\n  pass\n case 2:\n  pass',
    'match x:\n case y as z:\n  pass\n case 2:\n  pass',
]
for s in srcs:
    try:
        compile(s, "<s>", "exec")
        print(repr(s), "ok")
    except SyntaxError:
        print(repr(s), "SyntaxError")
