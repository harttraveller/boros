# f-strings: conversions, format specs, nested replacement fields in specs,
# brace escapes.

x = 42
pi = 3.14159265
name = 'Ada'
uni = 'caf\xe9 \N{SNOWMAN}'
items = [1, 'two', 3.0]

print(f'{x}', f"{x}", f'''{x}''', f"""{x}""")
print(f'{name!r} {name!s} {name!a}')
print(f'{uni!r} {uni!s} {uni!a}')
print(f'{items!r} {items!s} {items!a}')
print(f'{x:5}|{x:<5}|{x:>5}|{x:^5}|{x:05}|{x:+}|{x: }|{-x:=6}|')
print(f'{x:x} {x:X} {x:o} {x:b} {x:c} {x:08b}')
# (format specs using '#' are tested in lex_fstring_hash.py)
print(f'{1234567:,} {1234567:_} {0xdeadbeef:_x} {1234567.891:,.2f}')
print(f'{pi:.2f} {pi:.3e} {pi:10.4f}| {pi:<10.1f}| {pi:%} {0.25:.0%} {pi:g} {1e20:g}')
print(f'{name:*^11} {name:->8} {name:.<8} {name:.2}')
w, p = 10, 3
print(f'[{pi:{w}.{p}f}] [{pi:{w}}] [{name:{"^"}{w}}] [{x:{w}d}]')
fill, align = '#', '>'
print(f'[{name:{fill}{align}{w}}]')
print(f'[{x!r:>{w}}] [{name!r:^{w}}] [{uni!a:<{w + 10}}]')
print(f'{{}} {{x}} {{{x}}} {{{{x}}}} }}{{ {x}}} {{{x}')
print(f'{x}{x}{x}', f'{x}-{x}', f'-{x}-', f'{""}', f'')
print(f'{x + 1} {x * 2 - 1} {x // 5} {x % 5} {x ** 2} {-x} {~x} {not x}')
print(f'{x if x > 40 else 0} {[i * 2 for i in range(3)]} {(lambda y: y + 1)(x)}')
print(f'{x == 42} {x != 41} {x >= 42} {x <= 41} {x < 43 < 44}')
print(f'{ x } {  x  :>4} {x	}')
d = {'key': 'value', 1: 'one'}
print(f'{d["key"]} {d[1]} {d.get("missing", "dflt")} { {"a": 1}["a"] }')
print(f'{(x, x)} {x, x} {x,}')
print(f'{x:{""}} {x:}')
import datetime
dt = datetime.date(2024, 3, 9)
print(f'{dt:%Y-%m-%d} {dt:%d/%m/%y} {dt!r}')

class Money:
    def __init__(self, v):
        self.v = v

    def __format__(self, spec):
        return '<' + spec + ':' + str(self.v) + '>'

    def __repr__(self):
        return 'Money(%r)' % self.v

    def __str__(self):
        return '$%s' % self.v

m = Money(5)
print(f'{m} {m:abc} {m!r} {m!s} {m:{w}x} {m!s:>6}')
print(f'{3+4j} {3+4j:.1f} {True} {None} {True:d} {b"bytes"} {...}')
print(f'{x}' f'{pi:.1f}' 'plain' f'{name}')
print(f'{f"{x}"}')
# format() of an int with string spec types
for spec in ['', 'd', '8', '<8', '+08', 'e', '.1f', ',']:
    print(repr(f'{x:{spec}}'), end=' ')
print()
try:
    print(f'{x:q}')
except ValueError as e:
    print('ValueError', e)
try:
    print(f'{name:d}')
except ValueError as e:
    print('ValueError', e)
