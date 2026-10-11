# Raw string literals and string prefixes.

def show(label, s):
    print(label, repr(s), len(s))

show('r', r'\n\t\x41')
show('R', R'\d+\.\d*')
show('r_dq', r"C:\path\to\file")
show('r_quote', r'it\'s')
show('r_dquote', r"say \"hi\"")
show('r_bs_pair', r'\\')
show('r_bs_four', r'\\\\')
show('r_cont', r'a\
b')
show('r_triple', r'''raw \n triple ''' + r"""and \t double""")
show('r_triple_nl', r'''line1\
line2
line3''')
show('r_unicode', r'\u0041\N{BULLET}')
show('r_octal', r'\101')
show('r_empty', r'')
show('r_hash', r'# \# x')
for s in [r'\b', R'\b', '\b']:
    print(len(s), end=' ')
print()
import re
print(re.findall(r'\b\w+\b', 'hello raw world'))
print(re.sub(r'(\d+)', r'<\1>', 'a1b22c333'))
print(re.match(r'^\s*(\w+)\s*=\s*(\d+)$', '  x = 42').groups())
# u prefix is allowed (no-op), and case variants of every prefix
print(u'abc', U'abc')
print(rb'\x00', Rb'\n', rB'\t', RB'\\', br'\a', Br'\b', bR'\c', BR'\d')
x = 'X'
print(rf'{1+1}\n', Rf'{2}\t', rF'{3}\\', RF'{4}', fr'{5}\x', Fr'{6}', fR'{7}', FR'{8}\N{x}')
