# Self-documenting f-string expressions: {expr=} with whitespace,
# conversions and format specs.

x = 42
name = 'Ada'
pi = 3.14159
items = [1, 2]

print(f'{x=}')
print(f'{x = }')
print(f'{x= }')
print(f'{x =}')
print(f'{ x = }')
print(f'{x  =  }|')
print(f'{name=}')
print(f'{name=!s}')
print(f'{name=!r}')
print(f'{name=!a}')
print(f'{name=:>8}|')
print(f'{name = :*^9}|')
print(f'{pi=:.2f}')
print(f'{pi = :.3}')
print(f'{x=!r:>6}|')
print(f'{x=:x}')
w = 7
print(f'{x=:{w}}|')
print(f'{x + 1=}')
print(f'{x+1 = }')
print(f'{items[0]=} {items[-1] = }')
print(f'{len(items)=}')
print(f'{x == 42=}')
print(f'{x >= 1 = }')
print(f'{x<=1=}')
print(f'{name.upper()=}')
print(f'{"lit"=}')
print(f"{'lit'=}")
print(f'{dict(a=1)=}')
print(f'{(lambda: 7)()=}')
print(f'{x=}{x=}')
print(f'pre {x=} mid {name=} post')
print(f'{f"{x=}"=}')
print(f'''{
x
=}''')
print(f'{x=:}|')
print(f'{name=!s:}|')
print(f'{3.0=} {None=} {True=}')
print(f'{x*2=:05d}')
print(f'{-x=}')
