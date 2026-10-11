# Multi-line expressions inside f-string replacement fields, in triple-
# quoted f-strings and (since 3.12) in single-quoted ones; multi-line
# literal text; line continuations.

x = 3
names = ['a', 'b', 'c']

s = f'''first line {x}
second line {x * 2}
  third {
    x
    +
    10
} end'''
print(repr(s))

s = f"""{
    ', '.join(
        n.upper()
        for n in names
    )
}"""
print(repr(s))

s = f'''{x:>{
    5
}}|'''
print(repr(s))

s = f'''{
    {'key':
        'value'}['key']
}'''
print(repr(s))

s = f'''a {x
} b'''
print(repr(s))

s = f'{x +
1}'
print(repr(s))

s = f"{[n
       for n in names]}"
print(repr(s))

s = f'{
x
=}'
print(repr(s))

s = f'line one \
continued {x}'
print(repr(s))

s = (f'{x}'
     f'{x + 1}'
     '{x}')
print(repr(s))

s = f'''
{x}
'''
print(repr(s))

s = f'''{x}\
{x}'''
print(repr(s))

def fn():
    return f'''inside
    a function {
        x
    }'''
print(repr(fn()))

rows = [(1, 'one'), (22, 'twenty-two')]
table = '\n'.join(f'{n:>4} | {w:<12}|' for n, w in rows)
print(table)
print(f'''{'''nested triple
quoted'''}''')
