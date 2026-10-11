# Characters in an f-string *format spec* are literal text: '#' (alternate
# form), quote characters and brackets used as fill characters must not be
# treated as comments, nested strings or nesting brackets by the tokenizer.

x = 42
s = 'ab'
print(f'# literal hash {x} #')
print(f'{"#"} {"a#b".split("#")} {x!r}#')
print(f'{x:#x}')
print(f'{x=:#x} {x = :#o}')
print(f'{x:#o} {x:#b} {x:#010b} {x:#X}')
w = 12
print(f'[{x:#{w}x}] [{x:>#{w}b}]')
print(f'{3.0:#.0f} {3.0:#g}')
spec = '#x'
print(f'{x:{spec}}')
print(f'{s:"^10}|')
print(f"{s:'^10}|")
print(f'{s:(^10}|')
print(f'{s:[^10}|')
print(f'{s:)^10}|')
print(f'{s:]>6}| {s:=^8}| {s:!^8}| {s:%^8}|')
print(f'''{x:#x} and {s:"<5}|''')
