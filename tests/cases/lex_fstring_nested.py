# f-strings with nested quotes (PEP 701, Python 3.12+), nested f-strings,
# backslashes and strings containing braces/colons inside expressions.

x = 5
names = ['ann', 'bob']
d = {'k': 'v', 'a:b': 'colon', '}': 'brace'}

print(f"{'single inside double'}")
print(f'{"double inside single"}')
print(f'{'same quotes inside'}')
print(f"{"same double quotes"}")
print(f'{d['k']} {d["k"]}')
print(f"{', '.join(names)}")
print(f'{', '.join(names)}')
print(f'{d["a:b"]} {d["}"]} {d['}']}')
print(f'{"{"} {"}"} {"{}"} {"{{"}')
print(f'{":"} {"!r"} {"="} {"!="}')
print(f"{'\n'.join(names)!r}")
print(f'{'\t'.join(names)!r}')
print(f'{"\x41\N{BULLET}"}')
print(f'{f'{x}'}')
print(f"{f"{f"{x}"}"}")
print(f'{f'{f'{f'{x}'}'}'}')
print(f'{f"{x!r:>{x}}"}|')
print(f'''{f"""{x}"""}''')
print(f'{x:{f"{x}"}}|')
print(f'{"nested " + f"{x * 2}" + " end"}')
print(f"{[f'{n}!' for n in names]}")
print(f'{'a' 'b' "c"}')
print(f'{"\'"} {'\"'}')
print(f"""{'''triple in triple'''}""")
print(f'''{"""triple dq in triple sq"""} {'x'}''')
print(f'{x!r}' f"{x!r}" f'''{x!r}''')
print(f'{(lambda: "lam")()}')
print(f'{dict(a=1)}')
print(f'{ {"set"} }')
print(f'{x:>{len(f"{x}{x}")}}|')
print(rf'{"\d"}\d')
print(fr'{x}\{x}')
s = 'str'
print(f'{s!r:{s!r}^20}' if False else f'{s!r:*^20}')
